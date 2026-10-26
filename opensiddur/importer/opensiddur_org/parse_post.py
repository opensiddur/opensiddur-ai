"""Parse one opensiddur.org post, as exported to JSON, into columns, rows and metadata.

The post's ``content`` is the HTML WordPress rendered. A prayer is set in a
``table.toggleable-table``: each ``<th>`` names a column's role and language ("Source
(Hebrew)", "Translation (English)", "Transliteration (romanized Hebrew)"), and each ``<tr>``
is one stanza or block, with one ``td > div[lang]`` per column. Lines are separated by
``<br>``, and a line holding only a non-breaking space marks a stanza gap.

The parser keeps what the TEI needs and nothing else:

- inline spans with a meaning (``divine-referent``, ``instruction``, ``acrostic``,
  ``citation``), emphasis, and footnotes, whose text is taken from the plugin's inline
  tooltip;
- the HTML before the table (the introduction) and after it (notes), as paragraphs;
- the captions and links of the ``Source(s)`` section, which are recorded but never fetched.

Everything else the site renders around a post (scripts, styles, the iframe plugin's
boilerplate) is dropped. See ``specs/OPENSIDDUR_ORG_IMPORT.md``.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Union

import lxml.html
from lxml.html import HtmlElement

from opensiddur.importer.opensiddur_org.languages import (
    UNKNOWN_LANGUAGE,
    language_from_header,
    language_from_lang_attribute,
    same_language,
)
from opensiddur.importer.util.hebrew import to_nfkd

POST_ID_RE = re.compile(r"_\((\d+)\)\.json$")

#: Span classes the site uses with a meaning the TEI keeps. Every other span is transparent.
SEMANTIC_SPANS: dict[str, str] = {
    "divine-referent": "divine",
    "instruction": "instruction",
    "acrostic": "acrostic",
    "citation": "citation",
}

#: Inline formatting kept as ``tei:hi``.
FORMATTING_TAGS: dict[str, str] = {
    "em": "italic",
    "i": "italic",
    "strong": "bold",
    "b": "bold",
    "sup": "superscript",
    "sub": "subscript",
}

#: Elements dropped with everything inside them.
DROPPED_TAGS = frozenset({"script", "style", "noscript", "iframe", "audio", "video", "img"})

HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

NBSP = "\xa0"


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Span:
    """An inline span. ``kind`` is one of the values of :data:`SEMANTIC_SPANS` or
    :data:`FORMATTING_TAGS`."""

    kind: str
    children: tuple["Node", ...]


@dataclass(frozen=True)
class FootnoteRef:
    """A footnote marker. ``number`` counts footnotes through the whole post, in order."""

    number: int
    note: tuple["Node", ...]


Node = Union[Text, Span, FootnoteRef]
Line = tuple[Node, ...]


@dataclass(frozen=True)
class Block:
    """A stanza of lines, a prose paragraph, or a heading."""

    kind: Literal["stanza", "paragraph", "heading"]
    lines: tuple[Line, ...]


@dataclass
class Cell:
    lang: str | None
    css_class: str | None
    blocks: list[Block]

    @property
    def is_empty(self) -> bool:
        return not self.blocks


@dataclass
class Column:
    header: str
    role: str
    lang: str
    #: Why the column's language was read the way it was, when the ``<th>`` and the
    #: ``div@lang`` disagree; empty when they agree.
    mismatch: str = ""


@dataclass
class Row:
    cells: list[Cell]


@dataclass(frozen=True)
class SourceRef:
    caption: str
    url: str


@dataclass(frozen=True)
class Coauthor:
    name: str
    profile_slug: str
    qualifier: str


@dataclass
class Post:
    post_id: int
    title: str
    slug: str
    permalink: str
    source_link: str
    date: str
    last_updated: str
    coauthors: list[Coauthor]
    categories: list[str]
    tags: list[str]
    licence_html: str
    licence_url: str
    languages: list[str]
    date_src_start: str
    date_src_end: str
    columns: list[Column] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)
    table_count: int = 0
    intro: list[Line] = field(default_factory=list)
    notes: list[Line] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    #: Body ``div[lang]`` blocks set outside any table: the prose-only layout.
    loose_cells: list[Cell] = field(default_factory=list)
    has_colour_alignment: bool = False
    file_links: list[str] = field(default_factory=list)
    embeds: list[str] = field(default_factory=list)

    @property
    def titles(self) -> list[str]:
        return split_title(self.title)


# --------------------------------------------------------------------------------------------
# Small text helpers
# --------------------------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿︎️‍]"
)
_WS_RE = re.compile(r"[ \t\r\n\f\v]+")


def clean_text(text: str) -> str:
    """Decode entities, drop emoji, and normalize to the storage form (NFKD)."""
    text = html.unescape(text)
    text = _EMOJI_RE.sub("", text)
    return to_nfkd(text)


def split_title(title: str) -> list[str]:
    """The post title's parts. Titles are set "Hebrew | English"."""
    parts = [_WS_RE.sub(" ", clean_text(part)).strip() for part in title.split("|")]
    return [part for part in parts if part]


def licence_url(licence_html: str) -> str:
    """The URL a licence's ``<a href>`` names, or "" when it names none."""
    match = re.search(r"href=['\"]([^'\"]+)['\"]", licence_html)
    if not match:
        return ""
    url = html.unescape(match.group(1)).strip()
    if url.startswith("//"):
        url = "https:" + url
    return url


def _first(values: Any) -> str:
    if isinstance(values, list):
        return str(values[0]) if values else ""
    return str(values or "")


def _languages_meta(custom_fields: dict[str, Any]) -> list[str]:
    try:
        entries = json.loads(_first(custom_fields.get("languages_meta")) or "[]")
    except json.JSONDecodeError:
        return []
    return [entry.get("code", "") for entry in entries if isinstance(entry, dict)]


_QUALIFIER_RE = re.compile(r"\s*\(([^()]*)\)\s*$")


def parse_coauthor(entry: dict[str, Any]) -> Coauthor:
    name = html.unescape(entry.get("name", "")).strip()
    qualifier = ""
    match = _QUALIFIER_RE.search(name)
    if match:
        qualifier = match.group(1).strip()
        name = name[: match.start()].strip()
    profile = entry.get("profile_link", "") or ""
    slug = profile.rstrip("/").rsplit("/", 1)[-1] if profile else ""
    return Coauthor(name=to_nfkd(name), profile_slug=slug, qualifier=qualifier)


def post_id_from_path(path: str) -> int | None:
    match = POST_ID_RE.search(path)
    return int(match.group(1)) if match else None


# --------------------------------------------------------------------------------------------
# Inline content
# --------------------------------------------------------------------------------------------


class _Footnotes:
    """Numbers footnotes through a post in the order they appear."""

    def __init__(self) -> None:
        self.count = 0

    def next(self) -> int:
        self.count += 1
        return self.count


def _classes(element: HtmlElement) -> set[str]:
    return set((element.get("class") or "").split())


def _inline_nodes(element: HtmlElement, footnotes: _Footnotes) -> list[Node | str]:
    """The inline content of ``element``. Line breaks come back as the string ``"\\n"``."""
    out: list[Node | str] = []
    if element.text:
        out.append(Text(element.text))
    for child in element:
        out.extend(_child_nodes(child, footnotes))
        if child.tail:
            out.append(Text(child.tail))
    return out


def _child_nodes(child: HtmlElement, footnotes: _Footnotes) -> list[Node | str]:
    tag = child.tag if isinstance(child.tag, str) else ""
    if not tag or tag in DROPPED_TAGS:
        return []
    if tag == "br":
        return ["\n"]
    classes = _classes(child)
    if tag == "span" and "footnote_referrer" in classes:
        tooltip = child.xpath('.//span[contains(@class, "footnote_tooltip")]')
        note: list[Node | str] = _inline_nodes(tooltip[0], footnotes) if tooltip else []
        return [FootnoteRef(footnotes.next(), _join_inline(note))]
    if tag == "span":
        kind = next((SEMANTIC_SPANS[c] for c in sorted(classes) if c in SEMANTIC_SPANS), None)
        inner = _inline_nodes(child, footnotes)
        if kind is None:
            return inner
        return _wrap(kind, inner)
    if tag in FORMATTING_TAGS:
        return _wrap(FORMATTING_TAGS[tag], _inline_nodes(child, footnotes))
    if tag in ("p", "div", "li", "blockquote"):
        # A block inside inline content ends the line it is on.
        return ["\n", *_inline_nodes(child, footnotes), "\n"]
    return _inline_nodes(child, footnotes)


def _wrap(kind: str, inner: list[Node | str]) -> list[Node | str]:
    """Wrap ``inner`` in a span, splitting it at line breaks so that no span crosses one."""
    out: list[Node | str] = []
    segment: list[Node | str] = []

    def flush() -> None:
        children = _join_inline(segment)
        if children:
            out.append(Span(kind, children))
        segment.clear()

    for node in inner:
        if node == "\n":
            flush()
            out.append("\n")
        else:
            segment.append(node)
    flush()
    return out


def _join_inline(nodes: list[Node | str]) -> tuple[Node, ...]:
    """Merge adjacent text, collapse whitespace, and trim. Line breaks become spaces."""
    merged: list[Node] = []
    for node in nodes:
        if isinstance(node, str):
            node = Text(" ")
        if isinstance(node, Text):
            text = clean_text(node.text)
            if merged and isinstance(merged[-1], Text):
                merged[-1] = Text(merged[-1].text + text)
            else:
                merged.append(Text(text))
        else:
            merged.append(node)
    collapsed = [
        Text(_WS_RE.sub(" ", n.text.replace(NBSP, " "))) if isinstance(n, Text) else n
        for n in merged
    ]
    return _trim(tuple(n for n in collapsed if not (isinstance(n, Text) and not n.text)))


def _trim(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    items = list(nodes)
    while items and isinstance(items[0], Text) and not items[0].text.strip():
        items.pop(0)
    while items and isinstance(items[-1], Text) and not items[-1].text.strip():
        items.pop()
    if items and isinstance(items[0], Text):
        items[0] = Text(items[0].text.lstrip())
    if items and isinstance(items[-1], Text):
        items[-1] = Text(items[-1].text.rstrip())
    return tuple(items)


def node_text(nodes: tuple[Node, ...] | list[Node]) -> str:
    """Plain text of inline nodes, without footnote text."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.text)
        elif isinstance(node, Span):
            parts.append(node_text(node.children))
    return "".join(parts)


def _split_lines(nodes: list[Node | str]) -> list[tuple[Line, bool]]:
    """Split inline content at line breaks. Each line comes with whether it is a gap: a line
    that held only (non-breaking) whitespace, which is how the site marks a stanza break."""
    lines: list[tuple[Line, bool]] = []
    current: list[Node | str] = []

    def flush() -> None:
        raw = "".join(n.text for n in current if isinstance(n, Text))
        has_content = any(not isinstance(n, Text) for n in current) or raw.strip(" \t\r\n\f\v" + NBSP)
        if has_content:
            lines.append((_join_inline(current), False))
        elif NBSP in raw:
            lines.append(((), True))
        current.clear()

    for node in nodes:
        if node == "\n":
            flush()
        else:
            current.append(node)
    flush()
    return lines


def _stanzas(nodes: list[Node | str]) -> list[Block]:
    blocks: list[Block] = []
    current: list[Line] = []
    for line, gap in _split_lines(nodes):
        if gap:
            if current:
                blocks.append(Block("stanza", tuple(current)))
                current = []
        elif line:
            current.append(line)
    if current:
        blocks.append(Block("stanza", tuple(current)))
    return blocks


def _cell_blocks(div: HtmlElement, footnotes: _Footnotes) -> list[Block]:
    """A cell's blocks. Children that are paragraphs or headings make the cell prose."""
    block_children = [
        c for c in div if isinstance(c.tag, str) and (c.tag == "p" or c.tag in HEADING_TAGS)
    ]
    if not block_children:
        return _stanzas(_inline_nodes(div, footnotes))

    blocks: list[Block] = []
    loose: list[Node | str] = [Text(div.text)] if div.text else []

    def flush_loose() -> None:
        for line, _gap in _split_lines(loose):
            if line:
                blocks.append(Block("paragraph", (line,)))
        loose.clear()

    for child in div:
        if not isinstance(child.tag, str):
            continue
        if child.tag in HEADING_TAGS:
            flush_loose()
            heading = _join_inline(_inline_nodes(child, footnotes))
            if heading:
                blocks.append(Block("heading", (heading,)))
        elif child.tag == "p":
            flush_loose()
            lines = [line for line, _gap in _split_lines(_inline_nodes(child, footnotes)) if line]
            if lines:
                blocks.append(Block("paragraph", tuple(lines)))
        else:
            loose.extend(_child_nodes(child, footnotes))
        if child.tail:
            loose.append(Text(child.tail))
    flush_loose()
    return blocks


# --------------------------------------------------------------------------------------------
# The post
# --------------------------------------------------------------------------------------------


def _strip_noise(root: HtmlElement) -> None:
    for element in root.xpath("//script|//style|//noscript"):
        tail = element.tail
        parent = element.getparent()
        if parent is None:
            continue
        if tail:
            previous = element.getprevious()
            if previous is not None:
                previous.tail = (previous.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail
        parent.remove(element)


def _cell(td: HtmlElement, footnotes: _Footnotes) -> Cell:
    divs = [c for c in td if isinstance(c.tag, str) and c.tag == "div" and c.get("lang")]
    if not divs:
        blocks = _cell_blocks(td, footnotes)
        return Cell(lang=None, css_class=None, blocks=blocks)
    blocks: list[Block] = []
    for div in divs:
        blocks.extend(_cell_blocks(div, footnotes))
    first = divs[0]
    return Cell(
        lang=language_from_lang_attribute(first.get("lang", "")),
        css_class=(first.get("class") or "").strip() or None,
        blocks=blocks,
    )


def _column_language(header: str, cells: list[Cell]) -> tuple[str, str, str]:
    """A column's role and language, and why, when the header and the markup disagree.

    The header is what a reader sees, so when the ``<th>`` names a language that the
    ``div@lang`` contradicts, the header wins: post 68472 marks its English as
    ``romanized-transliteration``/``heb-Latn``, and "Transliteration (romanized Hebrew)" is
    often marked ``eng-Latn``.
    """
    role, header_lang = language_from_header(header)
    counts: dict[str, int] = {}
    for cell in cells:
        if cell.lang and not cell.is_empty:
            counts[cell.lang] = counts.get(cell.lang, 0) + 1
    markup_lang = max(sorted(counts), key=lambda k: counts[k]) if counts else ""
    if (
        role == "transliteration"
        and header_lang.endswith("-Latn")
        and markup_lang
        and same_language(header_lang, f"{markup_lang.split('-')[0]}-Latn")
    ):
        # The markup names the language but not the script; a transliteration is Latin.
        return role, header_lang, ""
    if header_lang and markup_lang and not same_language(header_lang, markup_lang):
        return role, header_lang, f"header says {header_lang}, markup says {markup_lang}"
    # Where they agree the markup is the more precise of the two (a dialect, a script).
    lang = markup_lang or header_lang or UNKNOWN_LANGUAGE
    return role, lang, ""


def _paragraph_lines(elements: list[HtmlElement], footnotes: _Footnotes) -> list[Line]:
    lines: list[Line] = []
    for element in elements:
        if not isinstance(element.tag, str) or element.tag in DROPPED_TAGS:
            continue
        if element.tag in ("hr",):
            continue
        for line, _gap in _split_lines(_inline_nodes(element, footnotes)):
            if line:
                lines.append(line)
    return lines


def _source_refs(elements: list[HtmlElement]) -> list[SourceRef]:
    refs: list[SourceRef] = []
    seen: set[str] = set()
    for element in elements:
        if not isinstance(element.tag, str):
            continue
        for caption_div in element.xpath('descendant-or-self::div[contains(@class, "wp-caption")]'):
            links = caption_div.xpath(".//a/@href")
            caption = " ".join(caption_div.xpath('.//*[contains(@class, "wp-caption-text")]//text()'))
            if links and links[0] not in seen:
                seen.add(links[0])
                refs.append(SourceRef(_WS_RE.sub(" ", clean_text(caption)).strip(), links[0]))
        for url in element.xpath("descendant-or-self::iframe/@src | descendant-or-self::a[contains(@class, 'mtli_')]/@href"):
            if url not in seen:
                seen.add(url)
                refs.append(SourceRef("", url))
    return refs


def _top_level(root: HtmlElement) -> list[HtmlElement]:
    return [child for child in root if isinstance(child.tag, str)]


def parse_post(data: dict[str, Any]) -> Post:
    custom_fields = data.get("custom_fields") or {}
    licence_html = _first(custom_fields.get("open_content_license"))
    post = Post(
        post_id=int(data["post_id"]),
        title=data.get("title", ""),
        slug=data.get("slug", ""),
        permalink=data.get("permalink", ""),
        source_link=data.get("source_link", ""),
        date=data.get("date", ""),
        last_updated=data.get("last_updated", ""),
        coauthors=[parse_coauthor(c) for c in data.get("coauthors") or []],
        categories=[html.unescape(c) for c in data.get("categories") or []],
        tags=[html.unescape(t) for t in data.get("tags") or []],
        licence_html=licence_html,
        licence_url=licence_url(licence_html),
        languages=_languages_meta(custom_fields),
        date_src_start=_first(custom_fields.get("date_src_start")),
        date_src_end=_first(custom_fields.get("date_src_end")),
    )
    content = data.get("content") or ""
    if not content.strip():
        return post

    root = lxml.html.fromstring(f"<div>{content}</div>")
    post.file_links = list(root.xpath("//a[contains(@class, 'mtli_')]/@href"))
    post.embeds = list(root.xpath("//iframe/@src"))
    post.has_colour_alignment = bool(
        root.xpath('//table[contains(@class, "toggleable-table")]//*[contains(@style, "color")]')
    )
    _strip_noise(root)
    footnotes = _Footnotes()

    top = _top_level(root)
    tables = root.xpath('//table[contains(@class, "toggleable-table")]')
    post.table_count = len(tables)
    sources_at = next(
        (i for i, el in enumerate(top) if el.tag in HEADING_TAGS and "source" in el.text_content().lower()),
        len(top),
    )

    if tables:
        table = tables[0]
        table_top = table
        while table_top.getparent() is not None and table_top.getparent() is not root:
            table_top = table_top.getparent()
        table_at = top.index(table_top) if table_top in top else 0
        post.intro = _paragraph_lines(top[:table_at], footnotes)
        _parse_table(post, table, footnotes)
        post.notes = _paragraph_lines(top[table_at + 1 : sources_at], footnotes)
    else:
        loose = root.xpath("//div[@lang]")
        post.loose_cells = [
            Cell(
                lang=language_from_lang_attribute(div.get("lang", "")),
                css_class=(div.get("class") or "").strip() or None,
                blocks=_cell_blocks(div, footnotes),
            )
            for div in loose
            if div.getparent() is not None and not div.getparent().xpath("ancestor-or-self::div[@lang]")
        ]
        first_loose = next((i for i, el in enumerate(top) if el.xpath("descendant-or-self::div[@lang]")), sources_at)
        post.intro = _paragraph_lines(top[:first_loose], footnotes)
    post.sources = _source_refs(top[sources_at:])
    return post


def _parse_table(post: Post, table: HtmlElement, footnotes: _Footnotes) -> None:
    headers = [
        _WS_RE.sub(" ", clean_text(th.text_content()).replace(NBSP, " ")).strip()
        for th in table.xpath("./thead//th | ./tr[1][th]/th")
    ]
    body_rows = table.xpath("./tbody/tr[td] | ./tr[td]")
    rows = [Row([_cell(td, footnotes) for td in tr.xpath("./td")]) for tr in body_rows]
    width = max([len(headers)] + [len(r.cells) for r in rows]) if rows or headers else 0
    for row in rows:
        while len(row.cells) < width:
            row.cells.append(Cell(lang=None, css_class=None, blocks=[]))
    headers += [""] * (width - len(headers))
    columns = []
    for index, header in enumerate(headers):
        cells = [row.cells[index] for row in rows]
        role, lang, mismatch = _column_language(header, cells)
        if role == "contribute" and any(not cell.is_empty for cell in cells):
            # The placeholder column is sometimes used for the original of quoted verses.
            role = "source"
        columns.append(Column(header=header, role=role, lang=lang, mismatch=mismatch))
    post.columns = columns
    post.rows = rows


def load_post(path: Path) -> Post:
    return parse_post(json.loads(path.read_text(encoding="utf-8")))


def normalize_key(text: str) -> str:
    """A comparison key: NFKD, marks dropped, case-folded, letters and digits only."""
    stripped = "".join(c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]+", " ", stripped.casefold()).strip()
