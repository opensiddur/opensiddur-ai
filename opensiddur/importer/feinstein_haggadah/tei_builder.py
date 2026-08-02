"""TEI XML builders for haggadah projects."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from opensiddur.importer.feinstein_haggadah.page_breaks import (
    PageBreak,
    PageBreakError,
    find_break_offset,
)
from opensiddur.importer.feinstein_haggadah.sections import (
    INDEX_CHILDREN,
    SectionContent,
    TextBlock,
    urn_for_section,
)
from opensiddur.importer.feinstein_haggadah.versify import BiblicalSection, PrintedPsalm
from opensiddur.importer.util.prettify import prettify_xml
from opensiddur.importer.util.validation import validate

#: Edition designator carried on every tei:pb, distinguishing the 1822 foliation from the
#: page numbering the HebrewBooks scan adds.
PAGE_EDITION = "1822"


def _xml_escape(text: str) -> str:
    return html.escape(text, quote=False)


def _pb(page: str) -> str:
    return f'<tei:pb n="{page}" ed="{PAGE_EDITION}"/>'


def tei_document(
    header_xml: str,
    body_xml: str,
    *,
    lang: str,
) -> str:
    return f"""<tei:TEI xml:lang="{lang}" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
{header_xml}
<tei:text>
{body_xml}
</tei:text>
</tei:TEI>
"""


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Return the (start, end) span in ``text`` of each rendered paragraph."""
    spans: list[tuple[int, int]] = []
    position = 0
    for part in text.split("\n\n"):
        stripped = part.strip()
        if stripped:
            lead = len(part) - len(part.lstrip())
            spans.append((position + lead, position + lead + len(stripped)))
        position += len(part) + 2
    return spans


def _splice(text: str, insertions: list[tuple[int, str]]) -> str:
    """Escape ``text`` and splice markup in at the given offsets.

    Escaping is applied per fragment so that the offsets, which index the unescaped
    string, stay meaningful.
    """
    out: list[str] = []
    cursor = 0
    for offset, markup in sorted(insertions):
        out.append(_xml_escape(text[cursor:offset]))
        out.append(markup)
        cursor = offset
    out.append(_xml_escape(text[cursor:]))
    return "".join(out).replace("\n", " ")


def _paragraph_xml(text: str, breaks: list[tuple[int, str]] | None = None) -> str:
    """Render ``text`` as tei:p elements, placing page breaks at the given offsets.

    ``tei:pb`` belongs to ``tei_model.global`` and so is valid inside ``tei:p``: a page
    turn falling mid-paragraph is marked in place rather than splitting the paragraph.

    A break always attaches to the text that follows it, since that is the text the new
    page carries. One that falls on a paragraph boundary, or in the whitespace between
    paragraphs, therefore opens the next paragraph rather than trailing the previous one.
    Only a break past the end of all text is emitted as a sibling.
    """
    breaks = sorted(breaks or [])
    spans = _paragraph_spans(text)
    if not spans and text.strip():
        spans = [(0, len(text))]

    assigned: dict[int, list[tuple[int, str]]] = {}
    trailing: list[str] = []
    for offset, markup in breaks:
        index = next((i for i, (_, end) in enumerate(spans) if offset < end), None)
        if index is None:
            trailing.append(markup)
            continue
        start, _ = spans[index]
        assigned.setdefault(index, []).append((max(0, offset - start), markup))

    parts = [
        f"<tei:p>{_splice(text[start:end], assigned.get(index, []))}</tei:p>"
        for index, (start, end) in enumerate(spans)
    ]
    parts.extend(trailing)
    return "\n".join(parts)


def _block_texts(blocks: list[TextBlock], *, lang: str) -> list[str]:
    text_attr = "hebrew" if lang == "he" else "english"
    return [getattr(block, text_attr).strip() for block in blocks]


@dataclass(frozen=True)
class InlineAnchor:
    """An element to splice into a section's text at a point located by its wording.

    Page breaks and verse milestones are the same problem — a marker belonging at an exact
    spot in a run of text — so they share one mechanism. ``before_text``/``after_text`` are
    the words on either side of the point; both ``None`` means the very start of the section.
    ``label`` names the anchor in error messages.
    """

    markup: str
    label: str
    before_text: str | None = None
    after_text: str | None = None

    @property
    def at_section_start(self) -> bool:
        return self.before_text is None and self.after_text is None


def verse_anchors(section: BiblicalSection) -> list[InlineAnchor]:
    """Chapter and verse milestones for a section that is a complete biblical unit.

    The canonical URNs go on the milestones, not on ``tei:div/@corresp``, exactly as
    ``project/wlc/psalms.xml`` does: the div keeps its haggadah identity for transclusion while
    the milestones are what alignment against WLC and JPS1917 keys off.
    """
    reference = f"{section.book} {section.chapter}"
    anchors = [
        InlineAnchor(
            markup=(
                f'<tei:milestone unit="chapter" n="{section.chapter}" '
                f'corresp="{section.chapter_urn()}"/>'
            ),
            label=reference,
        )
    ]
    anchors.extend(
        InlineAnchor(
            markup=(
                f'<tei:milestone unit="verse" n="{verse.n}" '
                f'corresp="{section.verse_urn(verse.n)}"/>'
            ),
            label=f"{reference}:{verse.n}",
            before_text=verse.before_text,
            after_text=verse.after_text,
        )
        for verse in section.verses
    )
    return anchors


def page_break_anchors(breaks: list[PageBreak]) -> list[InlineAnchor]:
    return [
        InlineAnchor(
            markup=_pb(entry.page),
            label=f"page {entry.page}",
            before_text=entry.before_text,
            after_text=entry.after_text,
        )
        for entry in breaks
    ]


def _resolve_insertions(
    slug: str,
    texts: list[str],
    anchors: list[InlineAnchor],
) -> dict[int, list[tuple[int, str]]]:
    """Map each anchored insertion to (block index -> [(offset, markup)]).

    The section's blocks are matched as one continuous run of text, so an anchor is found
    even when it falls exactly on a boundary between two blocks.
    """
    if not anchors:
        return {}

    joined = "".join(texts)
    starts: list[int] = []
    position = 0
    for text in texts:
        starts.append(position)
        position += len(text)

    resolved: dict[int, list[tuple[int, str]]] = {}
    for anchor in anchors:
        try:
            offset = find_break_offset(joined, anchor.before_text or "", anchor.after_text or "")
        except PageBreakError as error:
            raise PageBreakError(f"{anchor.label} in section {slug}: {error}") from error
        index = max(i for i, start in enumerate(starts) if start <= offset)
        resolved.setdefault(index, []).append((offset - starts[index], anchor.markup))
    return resolved


def _render_blocks(
    slug: str,
    blocks: list[TextBlock],
    *,
    lang: str,
    anchors: list[InlineAnchor] | None = None,
    children_markup: str = "",
    children_at: int | None = None,
    number_paragraphs: bool = True,
) -> str:
    parts: list[str] = []
    paragraph_number = 0
    texts = _block_texts(blocks, lang=lang)
    resolved = _resolve_insertions(slug, texts, anchors or [])
    if children_at is None and children_markup:
        children_at = len(blocks)
    for index, (block, text) in enumerate(zip(blocks, texts)):
        if index == children_at and children_markup:
            parts.append(children_markup)
        block_breaks = resolved.get(index, [])
        if block.kind == "head":
            if text:
                parts.append(f"<tei:head>{_splice(text, block_breaks)}</tei:head>")
            continue
        if not text:
            parts.extend(markup for _, markup in sorted(block_breaks))
            continue
        if block.starts_paragraph and number_paragraphs:
            paragraph_number += 1
            urn = urn_for_section(slug, paragraph=paragraph_number)
            parts.append(
                f'<tei:milestone unit="paragraph" n="{paragraph_number}" corresp="{urn}"/>'
            )
        if block.kind == "instruction":
            parts.append(
                f'<tei:note type="instruction">{_splice(text, block_breaks)}</tei:note>'
            )
            continue
        parts.append(_paragraph_xml(text, block_breaks))
    if children_markup and children_at is not None and children_at >= len(blocks):
        parts.append(children_markup)
    return "\n".join(parts)


def section_body(
    slug: str,
    section: SectionContent | None,
    *,
    lang: str,
    anchors: list[InlineAnchor] | None = None,
    child_slugs: list[str] | None = None,
    number_paragraphs: bool = True,
) -> str:
    """Render one section's ``tei:body``.

    Transclusions go where the extracted material stood in the source, taken from
    ``section.children_at``, so a section can hold text both before and after its children —
    Birkat HaMazon transcludes Psalm 126 and then continues for another thirty paragraphs.
    """
    urn = urn_for_section(slug)
    anchors = anchors or []
    opening = [anchor for anchor in anchors if anchor.at_section_start]
    anchored = [anchor for anchor in anchors if not anchor.at_section_start]
    leading = "".join(f"    {anchor.markup}\n" for anchor in opening)

    def _indent(rendered: str) -> str:
        return f"    {rendered.replace(chr(10), chr(10) + '    ')}\n" if rendered else ""

    transcludes = "\n".join(
        f'<j:transclude type="external" target="{urn_for_section(child)}"/>'
        for child in child_slugs or []
    )

    if section and section.blocks:
        content = _indent(
            _render_blocks(
                slug,
                section.blocks,
                lang=lang,
                anchors=anchored,
                children_markup=transcludes,
                children_at=section.children_at,
                number_paragraphs=number_paragraphs,
            )
        )
    else:
        if anchored:
            raise PageBreakError(
                f"section {slug} has anchored insertions but no content: "
                + ", ".join(anchor.label for anchor in anchored)
            )
        content = _indent(transcludes)

    return f"""<tei:body>
  <tei:div corresp="{urn}">
{leading}{content}  </tei:div>
</tei:body>"""


def printed_verse_body(psalm: PrintedPsalm) -> str:
    """Render the ``tei:body`` of a psalm transcribed from the 1822 print.

    Same shape as :func:`section_body` produces for these sections — the div keeps its haggadah
    ``@corresp`` for transclusion while the canonical biblical URNs sit on the milestones — but
    the verse divisions come from the transcription itself, so nothing has to be matched against
    the text. The verse fragments are emitted unescaped: they are checked-in markup, not source
    text, and may contain only ``j:divineName`` and ``tei:pb``.
    """
    verses = dict(sorted(psalm.verses.items()))
    first = min(verses)

    def _verse(n: int) -> str:
        return f'<tei:milestone unit="verse" n="{n}" corresp="{psalm.verse_urn(n)}"/>'

    # Markers that precede the psalm's first word stand as siblings of the paragraph, matching
    # what the anchor-driven path emits for a section-opening anchor. A folio opening the psalm
    # comes first, so the page turn is marked before the chapter it begins.
    leading = []
    opening_pb = re.match(r"<tei:pb [^>]*/>", verses[first])
    if opening_pb:
        leading.append(opening_pb.group())
        verses[first] = verses[first][opening_pb.end() :]
    leading.append(
        f'<tei:milestone unit="chapter" n="{psalm.chapter}" corresp="{psalm.chapter_urn()}"/>'
    )
    leading.append(_verse(first))

    body = verses.pop(first) + "".join(
        f" {_verse(n)}{text}" for n, text in verses.items()
    )
    prefix = "".join(f"    {markup}\n" for markup in leading)
    return f"""<tei:body>
  <tei:div corresp="{urn_for_section(psalm.section)}">
{prefix}    <tei:p>{body}</tei:p>
  </tei:div>
</tei:body>"""


def content_body(
    slug: str,
    section: SectionContent | None,
    *,
    lang: str,
    anchors: list[InlineAnchor] | None = None,
    number_paragraphs: bool = True,
) -> str:
    return section_body(
        slug, section, lang=lang, anchors=anchors, number_paragraphs=number_paragraphs
    )


def index_body(
    index_slug: str,
    child_slugs: list[str],
    section: SectionContent | None = None,
    *,
    lang: str,
    anchors: list[InlineAnchor] | None = None,
) -> str:
    return section_body(
        index_slug,
        section,
        lang=lang,
        anchors=anchors,
        child_slugs=child_slugs,
    )


def validate_and_write(tei_content: str, file_name: str, project_dir: Path) -> Path:
    out_path = project_dir / f"{file_name}.xml"
    pretty_xml = prettify_xml(tei_content, remove_xml_declaration=True)
    is_valid, errors = validate(pretty_xml)
    if not is_valid:
        raise RuntimeError(f"JLPTEI validation failed for {file_name}: {errors}")
    out_path.write_text(pretty_xml, encoding="utf-8")
    is_valid_on_disk, disk_errors = validate(out_path)
    if not is_valid_on_disk:
        raise RuntimeError(f"JLPTEI validation failed after write for {file_name}: {disk_errors}")
    return out_path


def validate_project_directory(project_dir: Path) -> None:
    """Validate every XML file in a project directory against RelaxNG and Schematron."""
    xml_files = sorted(project_dir.glob("*.xml"))
    if not xml_files:
        raise RuntimeError(f"No XML files found in {project_dir}")

    failures: dict[str, list[str]] = {}
    for path in xml_files:
        is_valid, errors = validate(path)
        if not is_valid:
            failures[path.name] = errors

    if failures:
        summary = "; ".join(
            f"{name}: {errs[0]}" for name, errs in sorted(failures.items())
        )
        raise RuntimeError(
            f"JLPTEI validation failed for {len(failures)} file(s) in {project_dir.name}: {summary}"
        )


def validate_header_stub(stub_name: str, *, lang: str) -> None:
    """Validate a header stub as part of a well-formed TEI document."""
    header = read_header_stub(stub_name)
    sample = tei_document(header, index_body("index", ["pre_seder"], lang=lang), lang=lang)
    is_valid, errors = validate(sample)
    if not is_valid:
        raise RuntimeError(f"JLPTEI validation failed for header stub {stub_name}: {errors}")


def read_header_stub(stub_name: str) -> str:
    stub_path = Path(__file__).parent / stub_name
    return stub_path.read_text(encoding="utf-8").strip()


def citation_bibl(project_id: str, from_page: str, to_page: str) -> str:
    """A per-document citation pointing at the project bibliography, scoped to its pages.

    See ``schema/JLPTEI-3.md``: the pointer is the index document's URN plus the
    ``project_source_bibl`` fragment.
    """
    target = f"urn:x-opensiddur:text:haggadah:haggadah@{project_id}#project_source_bibl"
    return (
        "<tei:bibl>"
        f'<tei:ptr target="{target}"/>'
        f'<tei:biblScope unit="pages" from="{from_page}" to="{to_page}"/>'
        "</tei:bibl>"
    )


def transcription_bibl(section: BiblicalSection) -> str:
    """Record that a biblical section's pointed text came from WLC, not the 1822 print.

    The 1822 edition is still the source this document represents — it supplies the wording's
    place, its pagination and its page range — but the vocalized text was taken from the
    Westminster Leningrad Codex, and a reader collating against the facsimile needs to know that.

    This is now true of ``psalm_126`` alone. The psalms the 1822 haggadah actually prints are
    transcribed from the facsimile (see ``heidenheim_psalms_1822.json``) and cite only the print,
    so ``convert_project`` does not emit this bibl for them.
    """
    return (
        "<tei:bibl>"
        f'<tei:ptr target="urn:x-opensiddur:text:bible:{section.book}@wlc"/>'
        f'<tei:biblScope unit="chapter" from="{section.chapter}" to="{section.chapter}"/>'
        "</tei:bibl>"
    )


def header_with_bibls(header_xml: str, bibls: list[str]) -> str:
    """Append bibls to a header's sourceDesc.

    Indentation is left to ``prettify_xml``, which reformats the whole document on write.
    """
    closing = "</tei:sourceDesc>"
    if closing not in header_xml:
        raise ValueError("header has no tei:sourceDesc to add a bibl to")
    return header_xml.replace(closing, "".join(bibls) + closing, 1)


def header_with_page_scope(
    header_xml: str,
    *,
    project_id: str,
    from_page: str,
    to_page: str,
) -> str:
    """Append a page-scoped citation bibl to a header's sourceDesc."""
    return header_with_bibls(header_xml, [citation_bibl(project_id, from_page, to_page)])


def minimal_index_header(
    title: str,
    *,
    project_id: str,
    urn_suffix: str,
    lang: str = "he",
    from_page: str | None = None,
    to_page: str | None = None,
) -> str:
    if from_page and to_page:
        bibl = citation_bibl(project_id, from_page, to_page)
    else:
        bibl = (
            "<tei:bibl>"
            f'<tei:ptr target="urn:x-opensiddur:text:haggadah:haggadah@{project_id}"/>'
            "</tei:bibl>"
        )
    return f"""<tei:teiHeader xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:fileDesc>
    <tei:titleStmt>
      <tei:title type="main" xml:lang="{lang}">{_xml_escape(title)}</tei:title>
    </tei:titleStmt>
    <tei:publicationStmt>
      <tei:distributor>
        <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
      </tei:distributor>
      <tei:idno type="urn">urn:x-opensiddur:text:haggadah:{urn_suffix}@{project_id}</tei:idno>
    </tei:publicationStmt>
    <tei:sourceDesc>
      {bibl}
    </tei:sourceDesc>
  </tei:fileDesc>
</tei:teiHeader>"""
