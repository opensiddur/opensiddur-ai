"""Parse Open Siddur haggadah compilation JSON into section content."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Literal

from opensiddur.importer.feinstein_haggadah.sections import (
    H3_SLUGS,
    INDEX_NODES,
    MAGID_SUBSECTION_PREFIXES,
    NIRTZAH_SUBSECTION_PREFIXES,
    SectionContent,
    TextBlock,
    match_subsection_slug,
)
from opensiddur.importer.util.pages import feinstein_haggadah_data_directory

_PARENTHETICAL = re.compile(r"\(([^)]*)\)")


@dataclass
class CompilationRow:
    hebrew: str
    english: str
    h3_title: str | None = None
    h3_boundary: bool = False


def _clean_html_cell(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\s*jQuery\([^)]*\)\.tooltip\(\{.*?\}\)\s*;?", "", text, flags=re.DOTALL)
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln and ln != "\xa0")


def _first_line(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line and line != "\xa0":
            return line
    return ""


def _non_empty_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.split("\n") if ln.strip() and ln.strip() != "\xa0"]


def load_compilation_json(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = feinstein_haggadah_data_directory() / "compilation.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parse_rows(compilation: dict[str, Any]) -> list[CompilationRow]:
    html = compilation["content"]
    pairs = re.findall(
        r'<tr>\s*<td[^>]*>\s*<div class="liturgy"[^>]*>(.*?)</div>\s*</td>\s*'
        r'<td[^>]*>\s*<div class="english"[^>]*>(.*?)</div>',
        html,
        re.DOTALL,
    )
    rows: list[CompilationRow] = []
    current_h3: str | None = None
    for he_raw, en_raw in pairs:
        h3_boundary = False
        if "<h3>" in en_raw:
            match = re.search(r"<h3>([^<]+)</h3>", en_raw)
            if match:
                current_h3 = match.group(1)
                h3_boundary = True
        rows.append(
            CompilationRow(
                hebrew=_clean_html_cell(he_raw),
                english=_clean_html_cell(en_raw),
                h3_title=current_h3,
                h3_boundary=h3_boundary,
            )
        )
    return rows


def _is_section_heading_row(row: CompilationRow) -> bool:
    """True for a short section title in its own table cell at an h3 boundary."""
    hebrew = row.hebrew.strip()
    if not hebrew or "\n" in hebrew or len(hebrew) > 40:
        return False
    if not row.h3_boundary:
        return False
    if len(hebrew.split()) > 6:
        return False
    return True


def split_parenthetical_instructions(
    text: str,
) -> list[tuple[Literal["paragraph", "instruction"], str]]:
    """Split English text into liturgical paragraphs and parenthetical instructions."""
    parts: list[tuple[Literal["paragraph", "instruction"], str]] = []
    pos = 0
    for match in _PARENTHETICAL.finditer(text):
        before = text[pos : match.start()].strip()
        if before:
            parts.append(("paragraph", before))
        instruction = match.group(1).strip()
        if instruction:
            parts.append(("instruction", instruction))
        pos = match.end()
    tail = text[pos:].strip()
    if tail:
        parts.append(("paragraph", tail))
    if not parts and text.strip():
        parts.append(("paragraph", text.strip()))
    return parts


def _append_english_segments(
    section: SectionContent,
    text: str,
    *,
    starts_paragraph: bool,
) -> None:
    first_in_row = starts_paragraph
    for kind, segment in split_parenthetical_instructions(text):
        block = TextBlock(
            kind=kind,
            english=segment,
            starts_paragraph=first_in_row,
        )
        first_in_row = False
        section.blocks.append(block)


def _append_body_row(section: SectionContent, row: CompilationRow) -> None:
    hebrew = row.hebrew.strip()
    english = row.english.strip()
    if hebrew:
        section.blocks.append(
            TextBlock(
                kind="paragraph",
                hebrew=hebrew,
                starts_paragraph=True,
            )
        )
    if english:
        _append_english_segments(section, english, starts_paragraph=True)


def _resolve_slug(
    h3_parent: str | None,
    first_line: str,
    *,
    nirtzah_mode: bool,
) -> tuple[str | None, bool]:
    if first_line:
        for prefixes, nirtzah_only in (
            (NIRTZAH_SUBSECTION_PREFIXES, True),
            (MAGID_SUBSECTION_PREFIXES, False),
        ):
            slug = match_subsection_slug(first_line, prefixes)
            if slug and (not nirtzah_only or nirtzah_mode or slug in ("echad_mi_yodea", "chad_gadya")):
                if nirtzah_only:
                    return slug, True
                if h3_parent == "magid":
                    return slug, nirtzah_mode

    if h3_parent == "magid":
        return None, nirtzah_mode
    if h3_parent == "nirtzah" or nirtzah_mode:
        return None, True
    if h3_parent:
        return h3_parent, False
    return None, nirtzah_mode


def _get_section(contents: dict[str, SectionContent], slug: str) -> SectionContent:
    if slug not in contents:
        contents[slug] = SectionContent(slug=slug)
    return contents[slug]


def build_section_contents(rows: list[CompilationRow]) -> dict[str, SectionContent]:
    contents: dict[str, SectionContent] = {}
    h3_parent: str | None = None
    current_slug: str | None = None
    nirtzah_mode = False

    for row in rows:
        if row.h3_title and row.h3_title in H3_SLUGS:
            h3_parent = H3_SLUGS[row.h3_title]
            if h3_parent in INDEX_NODES:
                current_slug = h3_parent
                nirtzah_mode = h3_parent == "nirtzah"
            else:
                current_slug = h3_parent
                nirtzah_mode = False

        first_he = _first_line(row.hebrew)
        resolved, nirtzah_mode = _resolve_slug(
            h3_parent, first_he, nirtzah_mode=nirtzah_mode
        )
        if resolved:
            current_slug = resolved

        if not current_slug or not (row.hebrew.strip() or row.english.strip()):
            continue

        section = _get_section(contents, current_slug)

        if _is_section_heading_row(row):
            en_lines = _non_empty_lines(row.english)
            head_en = en_lines[0] if en_lines else row.english.strip()
            section.blocks.append(
                TextBlock(
                    kind="head",
                    hebrew=row.hebrew.strip(),
                    english=head_en,
                )
            )
            for extra in en_lines[1:]:
                _append_english_segments(section, extra, starts_paragraph=False)
            continue

        _append_body_row(section, row)

    return contents
