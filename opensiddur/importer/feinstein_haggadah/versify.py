"""Verse milestones for the complete biblical units in the haggadah.

Several sections of the haggadah are complete psalms. For those transcribed from the 1822 print
the transcription is already divided into verses — see :func:`load_printed_psalms` and
``heidenheim_psalms_1822.json`` — and nothing here applies to them.

The rest keep the Open Siddur compilation's wording, which is close enough to the Westminster
Leningrad Codex that their verse boundaries are recoverable: align the section text against
``project/wlc/psalms.xml`` and record, for each verse, the words on either side of its opening.
``psalm_126`` is the only such section left, the 1822 print having no Shir haMaalot before
Birkat haMazon.

The recorded anchors are checked in as ``verse_anchors.json`` and resolved at conversion time by
the same :func:`~opensiddur.importer.feinstein_haggadah.page_breaks.find_break_offset` the page
breaks use, so conversion never has to read another project and the data can be reviewed and
tested. Regenerate with::

    uv run python -m opensiddur.importer.feinstein_haggadah.versify --regenerate

Anchors have to be two-sided: Psalms 118:1 and 118:29 are word-for-word identical, and every verse
of Psalm 136 ends alike, so an incipit alone would be ambiguous.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.importer.feinstein_haggadah.page_breaks import normalize_pb_markup
from opensiddur.importer.util.hebrew import normalize_hebrew, normalize_with_offsets

TEI = "{http://www.tei-c.org/ns/1.0}"
VERSE_ANCHORS_FILE = Path(__file__).parent / "verse_anchors.json"
PRINTED_PSALMS_FILE = Path(__file__).parent / "heidenheim_psalms_1822.json"

#: How many consonants to put on each side of a verse boundary. Long enough that the pair is
#: unique within its psalm, short enough to stay readable.
ANCHOR_LENGTH = 18


@dataclass(frozen=True)
class Verse:
    n: int
    before_text: str | None
    after_text: str | None

    @property
    def at_section_start(self) -> bool:
        return self.before_text is None and self.after_text is None


@dataclass(frozen=True)
class BiblicalSection:
    section: str
    book: str
    chapter: int
    verses: list[Verse]

    def chapter_urn(self) -> str:
        return f"urn:x-opensiddur:text:bible:{self.book}/{self.chapter}"

    def verse_urn(self, n: int) -> str:
        return f"{self.chapter_urn()}/{n}"


def load_verse_anchors(path: Path | None = None) -> dict[str, BiblicalSection]:
    """Load the curated table, keyed by section slug."""
    data = json.loads((path or VERSE_ANCHORS_FILE).read_text(encoding="utf-8"))
    sections = {}
    for entry in data["sections"]:
        sections[entry["section"]] = BiblicalSection(
            section=entry["section"],
            book=entry["book"],
            chapter=entry["chapter"],
            verses=[
                Verse(
                    n=verse["n"],
                    before_text=verse.get("before_text"),
                    after_text=verse.get("after_text"),
                )
                for verse in entry["verses"]
            ],
        )
    return sections


@dataclass(frozen=True)
class PrintedPsalm:
    """A psalm transcribed from the 1822 print, already divided into verses.

    ``verses`` maps verse number to a trusted XML fragment: it is emitted without escaping, so it
    may contain only ``j:divineName`` and ``tei:pb``. Because the transcription arrives already
    versified, these sections need no anchor matching — neither for verses nor for page breaks.
    """

    section: str
    book: str
    chapter: int
    verses: dict[int, str]

    def chapter_urn(self) -> str:
        return f"urn:x-opensiddur:text:bible:{self.book}/{self.chapter}"

    def verse_urn(self, n: int) -> str:
        return f"{self.chapter_urn()}/{n}"


def load_printed_psalms(path: Path | None = None) -> dict[str, PrintedPsalm]:
    """Load the diplomatic transcription of the psalms as the 1822 haggadah prints them.

    Keyed by section slug. Sections listed here are transcribed from the facsimile and take
    precedence over the Open Siddur compilation text; every other section, ``psalm_126`` included,
    still comes from the compilation by way of :func:`load_verse_anchors`.

    The curated transcription records page breaks with ``@n`` alone; ``normalize_pb_markup``
    rebuilds them so they carry the same ``@facs`` facsimile link as the page breaks the
    converter inserts, without that computed URL having to live in the curated data.
    """
    data = json.loads((path or PRINTED_PSALMS_FILE).read_text(encoding="utf-8"))
    return {
        section: PrintedPsalm(
            section=section,
            book=entry["book"],
            chapter=entry["chapter"],
            verses={
                int(n): normalize_pb_markup(text) for n, text in entry["verses"].items()
            },
        )
        for section, entry in data.items()
        if not section.startswith("_")
    }


def read_wlc_chapter(book_path: Path, chapter: int) -> list[tuple[int, str]]:
    """Return (verse number, text) for one chapter of a WLC book.

    Walks element text as well as tails, so kri/ktiv pairs inside ``tei:choice`` are not
    dropped — a tail-only walk silently loses those words.
    """
    tree = etree.parse(str(book_path))
    verses: list[tuple[int, list[str]]] = []
    current: list[str] | None = None
    for element in tree.iter():
        if etree.QName(element).localname == "milestone" and element.get("unit") == "verse":
            urn = element.get("corresp", "")
            _, _, reference = urn.partition("text:bible:")
            parts = reference.split("/")
            if len(parts) == 3 and parts[1] == str(chapter):
                current = []
                verses.append((int(parts[2]), current))
            else:
                current = None
            if current is not None and element.tail:
                current.append(element.tail)
            continue
        if current is None:
            continue
        if element.text:
            current.append(element.text)
        if element.tail:
            current.append(element.tail)
    return [(n, "".join(parts)) for n, parts in verses]


def verse_offsets(section_text: str, wlc_verses: list[tuple[int, str]]) -> dict[int, int]:
    """Map verse number -> offset in ``section_text`` where that verse begins.

    The haggadah text is WLC with at most a letter or two of orthographic drift, so a character
    diff over the consonant skeletons transfers the WLC verse boundaries exactly.
    """
    normalized, offsets = normalize_with_offsets(section_text)
    wlc_normalized = ""
    boundaries: dict[int, int] = {}
    for n, text in wlc_verses:
        boundaries[n] = len(wlc_normalized)
        wlc_normalized += normalize_hebrew(text)

    matcher = difflib.SequenceMatcher(None, wlc_normalized, normalized, autojunk=False)
    mapping: dict[int, int] = {}
    for wlc_start, section_start, size in matcher.get_matching_blocks():
        for n, boundary in boundaries.items():
            if wlc_start <= boundary < wlc_start + size and n not in mapping:
                mapping[n] = section_start + (boundary - wlc_start)

    missing = sorted(set(boundaries) - set(mapping))
    if missing:
        raise ValueError(f"could not locate verses {missing}")
    return {n: offsets[position] for n, position in sorted(mapping.items())}


def build_section(
    section: str,
    book: str,
    chapter: int,
    section_text: str,
    wlc_verses: list[tuple[int, str]],
) -> BiblicalSection:
    starts = verse_offsets(section_text, wlc_verses)
    normalized, offsets = normalize_with_offsets(section_text)
    position_of = {offset: index for index, offset in enumerate(offsets)}

    verses: list[Verse] = []
    for n, offset in starts.items():
        index = position_of[offset]
        if index == 0:
            verses.append(Verse(n=n, before_text=None, after_text=None))
            continue
        verses.append(
            Verse(
                n=n,
                before_text=normalized[max(0, index - ANCHOR_LENGTH) : index],
                after_text=normalized[index : index + ANCHOR_LENGTH],
            )
        )
    return BiblicalSection(section=section, book=book, chapter=chapter, verses=verses)


def section_texts() -> dict[str, str]:
    """Hebrew text per section, straight from the compilation.

    Read from the source rather than from generated files, both because regeneration must not
    depend on a conversion having already run and because this is the very text the converter
    will splice the milestones into.
    """
    from opensiddur.importer.feinstein_haggadah.parse_compilation import (
        build_section_contents,
        load_compilation_json,
        parse_rows,
    )

    contents = build_section_contents(parse_rows(load_compilation_json()))
    return {
        slug: "".join(
            block.hebrew.strip() for block in section.blocks if block.hebrew.strip()
        )
        for slug, section in contents.items()
    }


def regenerate(project_dir: Path, targets: dict[str, int]) -> list[BiblicalSection]:
    """Recompute anchors for the sections that still take them.

    Sections transcribed from the 1822 print are skipped, and their existing entries are carried
    through untouched. Anchors are meaningless for them — the transcription is already versified —
    and recomputing would corrupt the table, since the print writes the Divine Name as two letters
    where the codex writes four and the consonant skeletons no longer align.
    """
    wlc = project_dir / "wlc" / "psalms.xml"
    if not wlc.is_file():
        raise SystemExit(f"needs the WLC project to regenerate: {wlc} not found")
    printed = load_printed_psalms()
    existing = load_verse_anchors()
    texts = section_texts()
    sections = []
    for slug, chapter in targets.items():
        if slug in printed:
            if slug in existing:
                sections.append(existing[slug])
            continue
        if slug not in texts:
            raise SystemExit(f"no section {slug} in the compilation")
        sections.append(
            build_section(slug, "psalms", chapter, texts[slug], read_wlc_chapter(wlc, chapter))
        )
    return sections


def write_verse_anchors(sections: list[BiblicalSection], path: Path | None = None) -> Path:
    target = path or VERSE_ANCHORS_FILE
    payload = {
        "_comment": [
            "Verse boundaries for the complete biblical units in the haggadah, derived from",
            "project/wlc/psalms.xml, whose text these transcriptions were taken from.",
            "",
            "Anchors are two-sided and written as bare consonants, matched by",
            "page_breaks.find_break_offset. Verse 1 has no anchor: it opens its section.",
            "",
            "Regenerate with: python -m opensiddur.importer.feinstein_haggadah.versify --regenerate",
        ],
        "sections": [
            {
                "section": section.section,
                "book": section.book,
                "chapter": section.chapter,
                "verses": [
                    {"n": verse.n, "before_text": verse.before_text, "after_text": verse.after_text}
                    for verse in section.verses
                ],
            }
            for section in sections
        ],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


#: Section slug -> psalm number, for every complete biblical unit in the project. Established by
#: scanning every paragraph against every WLC chapter; these are the only complete ones.
BIBLICAL_SECTIONS: dict[str, int] = {
    "psalm_113": 113,
    "psalm_114": 114,
    "psalm_115": 115,
    "psalm_116": 116,
    "psalm_117": 117,
    "psalm_118": 118,
    "psalm_126": 126,
    "psalm_136": 136,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--project-dir", type=Path, default=PROJECT_DIRECTORY)
    args = parser.parse_args(argv)
    if not args.regenerate:
        parser.error("nothing to do; pass --regenerate")
    sections = regenerate(args.project_dir, BIBLICAL_SECTIONS)
    path = write_verse_anchors(sections)
    total = sum(len(section.verses) for section in sections)
    print(f"wrote {len(sections)} sections, {total} verses to {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
