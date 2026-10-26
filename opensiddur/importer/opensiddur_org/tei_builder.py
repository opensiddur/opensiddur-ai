"""Build the JLPTEI of one opensiddur.org post in one language.

Each post and language is a project, ``osp-<post_id>-<lang>``, of two files:

- ``index.xml``: the full header, with the source ``tei:bibl``; the post's introduction and
  notes as front matter, in the project whose language they are written in; and a body that
  transcludes the text.
- ``<slug>.xml``: the text, one ``tei:div`` whose ``corresp`` is the post's URN. Each table
  row opens a ``tei:milestone`` whose ``corresp`` is the same in every language of the post,
  which is what sets the languages side by side.

The output depends only on its input, never on the clock, so converting an unchanged post
again gives identical files.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from opensiddur.importer.opensiddur_org.contributors import Credit, Credits
from opensiddur.importer.opensiddur_org.languages import DEFAULT_SCRIPT, ISO639_1
from opensiddur.importer.opensiddur_org.licences import LicenceDecision
from opensiddur.importer.opensiddur_org.parse_post import (
    Block,
    Column,
    FootnoteRef,
    Line,
    Node,
    Post,
    Span,
    Text,
    node_text,
)
from opensiddur.importer.opensiddur_org.scope import column_mode, is_heading_row
from opensiddur.importer.opensiddur_org.urns import PostUrns
from opensiddur.importer.util.tei_project import PROJECT_SOURCE_BIBL_ID, tei_document, xml_id_ref

SITE_URL = "https://opensiddur.org"
SITE_NAME = "Open Siddur Project"
UPSTREAM_REPOSITORY = "https://github.com/aharonium/opensiddur.org"

#: Inline span kinds -> (opening tag, closing tag).
SPAN_MARKUP: dict[str, tuple[str, str]] = {
    "divine": ("<j:divineName>", "</j:divineName>"),
    "instruction": ('<tei:note type="instruction">', "</tei:note>"),
    "acrostic": ('<tei:seg type="acrostic">', "</tei:seg>"),
    "citation": ("<tei:bibl>", "</tei:bibl>"),
    "italic": ('<tei:hi rend="italic">', "</tei:hi>"),
    "bold": ('<tei:hi rend="bold">', "</tei:hi>"),
    "superscript": ('<tei:hi rend="superscript">', "</tei:hi>"),
    "subscript": ('<tei:hi rend="subscript">', "</tei:hi>"),
}

#: Span kinds that may not nest inside themselves or a note, and are dropped there.
_NOTE_UNSAFE = frozenset({"instruction"})


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def attr(text: str) -> str:
    return html.escape(text, quote=True)


def project_id(post_id: int, lang: str) -> str:
    return f"osp-{post_id}-{lang.lower()}"


def text_file_stem(post: Post) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", post.slug.lower()).strip("-")[:80].strip("-")
    return stem or f"post-{post.post_id}"


#: Scripts a title part may be written in, other than Latin, and the tag it is given. The
#: site sets titles "Hebrew | English"; a part in another script names no language we can
#: tell, only its script.
TITLE_SCRIPTS: tuple[tuple[str, str], ...] = (
    ("[\u0590-\u05FF]", "he"),
    ("[\u0600-\u06FF]", "und-Arab"),
    ("[\u0400-\u04FF]", "und-Cyrl"),
    ("[\u0370-\u03FF]", "und-Grek"),
)


def _script_language(text: str) -> str:
    """The language a title part is taken to be in: "he" in Hebrew letters, "en" in Latin."""
    for pattern, lang in TITLE_SCRIPTS:
        if re.search(pattern, text):
            return lang
    return "en"


def _is_latin(lang: str) -> bool:
    primary, *subtags = lang.split("-")
    if subtags:
        return "Latn" in subtags
    iso639_3 = next((k for k, v in ISO639_1.items() if v == primary), primary)
    return DEFAULT_SCRIPT.get(iso639_3, "Latn") == "Latn"


def titles_by_language(post: Post) -> list[tuple[str, str]]:
    """The title's parts with the language each is written in."""
    return [(_script_language(title), title) for title in post.titles]


# --------------------------------------------------------------------------------------------
# Inline content
# --------------------------------------------------------------------------------------------


@dataclass
class _Notes:
    """The footnotes a document anchors, collected while its text is rendered."""

    entries: list[tuple[int, tuple[Node, ...]]]

    def anchor(self, ref: FootnoteRef) -> str:
        self.entries.append((ref.number, ref.note))
        return f'<tei:anchor xml:id="note_{ref.number}"/>'


def render_inline(nodes: tuple[Node, ...] | Line, notes: _Notes | None, *, in_note: bool = False) -> str:
    out: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            out.append(esc(node.text))
        elif isinstance(node, FootnoteRef):
            if notes is not None and not in_note:
                out.append(notes.anchor(node))
        elif isinstance(node, Span):
            inner = render_inline(node.children, notes, in_note=in_note or node.kind == "instruction")
            if in_note and node.kind in _NOTE_UNSAFE:
                out.append(inner)
                continue
            opening, closing = SPAN_MARKUP[node.kind]
            out.append(f"{opening}{inner}{closing}")
            if node.kind == "instruction" and notes is not None and not in_note:
                # A note cannot hold an anchor for another note; it follows the instruction.
                out.extend(notes.anchor(ref) for ref in _footnote_refs(node.children))
    return "".join(out)


def _footnote_refs(nodes: tuple[Node, ...]) -> list[FootnoteRef]:
    found: list[FootnoteRef] = []
    for node in nodes:
        if isinstance(node, FootnoteRef):
            found.append(node)
        elif isinstance(node, Span):
            found.extend(_footnote_refs(node.children))
    return found


def _lang_attr(cell_lang: str | None, document_lang: str) -> str:
    if cell_lang and cell_lang != document_lang and cell_lang.split("-")[0] != "und":
        return f' xml:lang="{attr(cell_lang)}"'
    return ""


def render_block(block: Block, notes: _Notes, lang_attr: str = "") -> str:
    if block.kind == "stanza":
        lines = "".join(f"<tei:l>{render_inline(line, notes)}</tei:l>" for line in block.lines)
        return f"<tei:lg{lang_attr}>{lines}</tei:lg>"
    if block.kind == "paragraph":
        body = "<tei:lb/>".join(render_inline(line, notes) for line in block.lines)
        return f"<tei:p{lang_attr}>{body}</tei:p>"
    raise ValueError(f"a {block.kind} block is not rendered as text")


# --------------------------------------------------------------------------------------------
# The text document
# --------------------------------------------------------------------------------------------


def row_numbers(post: Post) -> dict[int, int]:
    """Row index -> its number in the URNs: rows are numbered from 1, headings skipped."""
    numbers: dict[int, int] = {}
    n = 0
    for index in range(len(post.rows)):
        if is_heading_row(post, index):
            continue
        n += 1
        numbers[index] = n
    return numbers


def text_body(post: Post, column_index: int, column: Column, urns: PostUrns) -> tuple[str, str]:
    """The body ``tei:div`` of one column, and its ``tei:standOff`` (or "")."""
    notes = _Notes([])
    unit = "paragraph" if column_mode(post, column_index) == {"paragraph"} else "stanza"
    numbers = row_numbers(post)
    parts: list[str] = [f'<tei:div corresp="{attr(urns.urn)}">']
    head = next((title for lang, title in titles_by_language(post) if lang == column.lang), "")
    if head:
        parts.append(f"<tei:head>{esc(head)}</tei:head>")
    in_section = False
    for index, row in enumerate(post.rows):
        cell = row.cells[column_index]
        if index not in numbers:
            # A heading row opens a section; the next heading row closes it.
            if in_section:
                parts.append("</tei:div>")
            parts.append("<tei:div>")
            in_section = True
            if not cell.is_empty:
                heading = "<tei:lb/>".join(render_inline(line, notes) for line in cell.blocks[0].lines)
                parts.append(f"<tei:head{_lang_attr(cell.lang, column.lang)}>{heading}</tei:head>")
            continue
        if cell.is_empty:
            continue
        row_urn = urns.row_urn(numbers[index])
        if row_urn:
            parts.append(f'<tei:milestone unit="{unit}" corresp="{attr(row_urn)}"/>')
        lang_attr = _lang_attr(cell.lang, column.lang)
        parts.extend(render_block(block, notes, lang_attr) for block in cell.blocks)
    if in_section:
        parts.append("</tei:div>")
    parts.append("</tei:div>")
    return f"<tei:body>{''.join(parts)}</tei:body>", standoff(notes, column.lang)


def standoff(notes: _Notes, lang: str) -> str:
    if not notes.entries:
        return ""
    entries = "".join(
        f'<tei:note type="commentary" n="{number}" target="#note_{number}">'
        f"<tei:p>{render_inline(note, None, in_note=True)}</tei:p></tei:note>"
        for number, note in notes.entries
    )
    return f'<tei:standOff type="notes">{entries}</tei:standOff>'


# --------------------------------------------------------------------------------------------
# Headers
# --------------------------------------------------------------------------------------------


def _titles(post: Post, lang: str) -> str:
    titles = titles_by_language(post)
    main_index = next((i for i, (title_lang, _) in enumerate(titles) if title_lang == lang), 0)
    out = []
    for index, (title_lang, title) in enumerate(titles):
        kind = "main" if index == main_index else "alt"
        out.append(f'<tei:title type="{kind}" xml:lang="{title_lang}">{esc(title)}</tei:title>')
    return "".join(out)


def _resp_statements(credits: tuple[Credit, ...]) -> str:
    return "".join(
        "<tei:respStmt>"
        f'<tei:resp key="{credit.key}">{esc(credit.resp)}</tei:resp>'
        f'<tei:name ref="{attr(credit.urn)}">{esc(credit.name)}</tei:name>'
        "</tei:respStmt>"
        for credit in credits
    )


def _publication(licence: LicenceDecision) -> str:
    assert licence.licence is not None, "only an allowed licence is written"
    basis = f"<tei:p>{esc(licence.basis)}</tei:p>" if licence.basis else ""
    return (
        "<tei:publicationStmt>"
        f'<tei:distributor><tei:ref target="{SITE_URL}">{SITE_NAME}</tei:ref></tei:distributor>'
        '<tei:availability status="free">'
        f'<tei:licence target="{attr(licence.licence.url)}">{esc(licence.licence.name)}</tei:licence>'
        f"{basis}</tei:availability>"
        "</tei:publicationStmt>"
    )


def iso_date(value: str) -> str:
    """The site's partial dates as ISO: ``1440-00-00`` is the year 1440, ``1834-05-00`` May 1834."""
    match = re.match(r"^(-?\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", value.strip())
    if not match:
        return ""
    year, month, day = match.groups()
    if not month or month == "00":
        return year
    if not day or day == "00":
        return f"{year}-{month}"
    return f"{year}-{month}-{day}"


def _date_of_original(post: Post) -> str:
    start, end = iso_date(post.date_src_start), iso_date(post.date_src_end)
    if not start and not end:
        return ""
    if start and end and start != end:
        return f'<tei:date from="{attr(start)}" to="{attr(end)}">{esc(start)} – {esc(end)}</tei:date>'
    when = start or end
    return f'<tei:date when="{attr(when)}">{esc(when)}</tei:date>'


def source_bibl(
    post: Post, credits: Credits, *, upstream_commit: str, upstream_commit_date: str
) -> str:
    titles = "".join(
        f'<tei:title xml:lang="{lang}">{esc(title)}</tei:title>' for lang, title in titles_by_language(post)
    )
    authors = "".join(f"<tei:author>{esc(name)}</tei:author>" for name in credits.authors)
    authors += "".join(
        f'<tei:respStmt><tei:resp key="{credit.key}">{esc(credit.resp)}</tei:resp>'
        f"<tei:name>{esc(credit.name)}</tei:name></tei:respStmt>"
        for credit in credits.source_responsibilities
    )
    sources = "".join(
        f'<tei:note>Source: {esc(source.caption) + " " if source.caption else ""}'
        f'<tei:ref target="{attr(source.url)}">{esc(source.url)}</tei:ref></tei:note>'
        for source in post.sources
    )
    return (
        f'<tei:bibl xml:id="{PROJECT_SOURCE_BIBL_ID}">'
        f"{titles}{authors}"
        f'<tei:distributor><tei:ref target="{SITE_URL}">{SITE_NAME}</tei:ref></tei:distributor>'
        f"{_date_of_original(post)}"
        f'<tei:date type="accessed" when="{attr(upstream_commit_date)}">{esc(upstream_commit_date)}</tei:date>'
        f'<tei:idno type="url">{esc(post.permalink)}</tei:idno>'
        f'<tei:idno type="opensiddur.org">{post.post_id}</tei:idno>'
        f"{sources}"
        '<tei:note type="encoding">Converted from the export of opensiddur.org at '
        f'<tei:ref target="{UPSTREAM_REPOSITORY}/tree/{attr(upstream_commit)}">{esc(upstream_commit[:10])}</tei:ref>.'
        "</tei:note>"
        "</tei:bibl>"
    )


def header(
    post: Post,
    *,
    lang: str,
    credits: tuple[Credit, ...],
    licence: LicenceDecision,
    source_desc: str,
) -> str:
    return (
        "<tei:teiHeader><tei:fileDesc>"
        f"<tei:titleStmt>{_titles(post, lang)}{_resp_statements(credits)}</tei:titleStmt>"
        f"{_publication(licence)}"
        f"<tei:sourceDesc>{source_desc}</tei:sourceDesc>"
        "</tei:fileDesc></tei:teiHeader>"
    )


# --------------------------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------------------------


def front(post: Post, lang: str, id_prefix: str) -> tuple[str, str]:
    """The introduction and notes, as paratext, and the standOff of their footnotes. They are
    set in the project whose language they are written in (see :func:`front_language`)."""
    notes = _Notes([])
    sections = []
    for name, lines in (("introduction", post.intro), ("notes", post.notes)):
        if not lines:
            continue
        paragraphs = "".join(f"<tei:p>{render_inline(line, notes)}</tei:p>" for line in lines)
        cond_id = f"{id_prefix}_{name}"
        sections.append(
            f'<j:conditional xml:id="{cond_id}"><tei:fs type="opensiddur:paratext">'
            '<tei:f name="include"><tei:binary value="true"/></tei:f></tei:fs></j:conditional>'
            f'<tei:div type="{name}">{paragraphs}</tei:div>'
            f'<j:endConditional target="#{cond_id}"/>'
        )
    if not sections:
        return "", ""
    return f"<tei:front>{''.join(sections)}</tei:front>", standoff(notes, lang)


def front_language(post: Post, languages: list[str]) -> str | None:
    """The project the front matter goes in: the one whose language it is written in, else
    English, else the first."""
    text = " ".join(node_text(line) for line in post.intro + post.notes)
    if not text.strip():
        return None
    if re.search(r"[A-Za-z]", text):
        latin = [lang for lang in languages if _is_latin(lang) and not lang.endswith("-Latn")]
        candidates = (["en"] if "en" in latin else []) + latin
    else:
        candidates = [_script_language(text)]
    for candidate in candidates:
        if candidate in languages:
            return candidate
    return languages[0] if languages else None


# --------------------------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectFiles:
    project_id: str
    lang: str
    files: dict[str, str]


def build_project(
    post: Post,
    column_index: int,
    column: Column,
    *,
    urns: PostUrns,
    credits: Credits,
    licence: LicenceDecision,
    upstream_commit: str,
    upstream_commit_date: str,
    with_front: bool,
) -> ProjectFiles:
    lang = column.lang
    pid = project_id(post.post_id, lang)
    stem = text_file_stem(post)
    column_credits = credits.for_column_role(column.role)

    body, notes = text_body(post, column_index, column, urns)
    text_header = header(
        post, lang=lang, credits=column_credits, licence=licence,
        source_desc=f'<tei:bibl><tei:ptr target="{xml_id_ref(pid, "index", PROJECT_SOURCE_BIBL_ID)}"/></tei:bibl>',
    )
    text_document = tei_document(text_header, body, lang=lang, standoff_xml=notes)

    index_header = header(
        post, lang=lang, credits=column_credits, licence=licence,
        source_desc=source_bibl(
            post, credits, upstream_commit=upstream_commit, upstream_commit_date=upstream_commit_date
        ),
    )
    index_body = (
        f'<tei:body><tei:div><j:transclude type="external" target="{attr(urns.urn)}"/></tei:div></tei:body>'
    )
    front_xml, front_notes = front(post, lang, f"osp_{post.post_id}") if with_front else ("", "")
    index_document = tei_document(
        index_header, index_body, lang=lang, front_xml=front_xml, standoff_xml=front_notes
    )
    return ProjectFiles(pid, lang, {"index": index_document, stem: text_document})
