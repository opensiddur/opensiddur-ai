"""Verse references and reading spans — the vocabulary the whole humash importer shares.

A *reading span* is a named, explicitly bounded stretch of text belonging to one *unit-space*.
Ends are always stored, never inferred from the next span, because reading divisions overlap:
the maftir re-reads the close of the seventh aliyah, and the weekday aliyot subdivide the
Shabbat ones. See ``model.py`` for how overlapping spans are emitted.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path

from opensiddur.importer.util.pages import hebcal_leyning_data_directory

# Unit-spaces. These become tei:milestone/@unit, and refdb.UNIT_CONTAINED_BY decides which of
# them may terminate which; they are deliberately distinct so that they do not truncate one
# another.
UNIT_PARSHA = "parsha.annual"
UNIT_ALIYAH = "aliyah.annual"
UNIT_WEEKDAY = "aliyah.weekday"
UNIT_MAFTIR = "maftir.annual"
UNIT_TRIENNIAL = "aliyah.triennial"

# The five books, in order, as MAM names them in Hebrew.
TORAH_BOOKS: tuple[tuple[str, str, str], ...] = (
    # (MAM Hebrew name, opensiddur slug, hebcal English name)
    ("בראשית", "genesis", "Genesis"),
    ("שמות", "exodus", "Exodus"),
    ("ויקרא", "leviticus", "Leviticus"),
    ("במדבר", "numbers", "Numbers"),
    ("דברים", "deuteronomy", "Deuteronomy"),
)

HEBREW_BOOK_TO_SLUG = {hebrew: slug for hebrew, slug, _ in TORAH_BOOKS}
SLUG_TO_HEBREW_BOOK = {slug: hebrew for hebrew, slug, _ in TORAH_BOOKS}
SLUG_TO_HEBCAL_BOOK = {slug: english for _, slug, english in TORAH_BOOKS}
HEBCAL_BOOK_TO_SLUG = {english: slug for _, slug, english in TORAH_BOOKS}


@dataclass(frozen=True, order=True)
class VerseRef:
    """One verse, identified the way the Tanakh projects' URNs identify it."""

    book: str  # opensiddur slug, e.g. "genesis"
    chapter: int
    verse: int

    def __str__(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"

    @property
    def urn(self) -> str:
        """The unsuffixed verse URN, which resolves in whichever project has priority."""
        return f"urn:x-opensiddur:text:bible:{self.book}/{self.chapter}/{self.verse}"

    def range_urn(self, end: "VerseRef") -> str:
        """A ranged transclusion target from this verse to `end`.

        The range syntax replaces the trailing components of the start, so the end is written
        as ``chapter/verse`` — see UrnResolver.resolve_range.
        """
        if end.book != self.book:
            raise ValueError(f"A range may not cross books: {self} to {end}")
        return f"{self.urn}-{end.chapter}/{end.verse}"


@dataclass(frozen=True)
class ReadingSpan:
    """A named span of one unit-space, with both ends given explicitly."""

    unit: str
    label: str
    start: VerseRef
    end: VerseRef
    # Free text from the source noting that other traditions divide differently.
    note: str | None = None

    def __post_init__(self):
        if self.start.book != self.end.book:
            raise ValueError(f"{self.unit} {self.label} crosses books: {self.start}-{self.end}")
        if self.end < self.start:
            raise ValueError(f"{self.unit} {self.label} ends before it starts: {self.start}-{self.end}")


# Verse numbering conventions, and the project that follows each.
#
# Four Torah chapters are divided into verses differently by different editions, because the
# Decalogue and a few other passages can be grouped by the upper cantillation (ta'am elyon) or
# the lower (ta'am tachton). The humash therefore emits a variant range per numbering, under
# conditional control; see model.py. MAM's division is the default, since the aliyah
# boundaries come from MAM.
NUMBERING_MASORAH = "masorah"       # Miqra al pi ha-Masorah
NUMBERING_LENINGRAD = "leningrad"   # Westminster Leningrad Codex
NUMBERING_COMMON = "common"         # common printed editions, which hebcal and jps1917 follow

NUMBERINGS = (NUMBERING_MASORAH, NUMBERING_LENINGRAD, NUMBERING_COMMON)
DEFAULT_NUMBERING = NUMBERING_MASORAH

NUMBERING_PROJECT = {
    NUMBERING_MASORAH: "miqra_al_pi_hamasorah",
    NUMBERING_LENINGRAD: "wlc",
    NUMBERING_COMMON: "jps1917",
}

# Chapters whose verse count depends on the numbering. Everywhere else the three agree, so
# hebcal's counts are used directly. Verified against the three projects' own milestones.
DIVERGENT_CHAPTER_VERSES: dict[tuple[str, int], dict[str, int]] = {
    ("exodus", 20): {NUMBERING_MASORAH: 22, NUMBERING_LENINGRAD: 26, NUMBERING_COMMON: 23},
    ("numbers", 10): {NUMBERING_MASORAH: 34, NUMBERING_LENINGRAD: 36, NUMBERING_COMMON: 36},
    ("numbers", 25): {NUMBERING_MASORAH: 18, NUMBERING_LENINGRAD: 19, NUMBERING_COMMON: 19},
    ("deuteronomy", 5): {NUMBERING_MASORAH: 29, NUMBERING_LENINGRAD: 33, NUMBERING_COMMON: 30},
}


@functools.cache
def _verse_counts(sourcetexts_root: Path | None = None) -> dict[str, list[int]]:
    """Verses per chapter, by hebcal book name. Index 0 is a placeholder, so chapters are 1-based."""
    path = hebcal_leyning_data_directory(sourcetexts_root) / "numverses.json"
    return json.loads(path.read_text(encoding="utf-8"))


def verses_in_chapter(
    book: str,
    chapter: int,
    sourcetexts_root: Path | None = None,
    numbering: str = DEFAULT_NUMBERING,
) -> int:
    """How many verses chapter `chapter` of `book` (an opensiddur slug) has.

    hebcal's counts follow the common printed editions, so the four chapters where the
    editions disagree are looked up separately — using hebcal's count for a MAM-numbered span
    would run the span past the end of the chapter as MAM divides it.
    """
    divergent = DIVERGENT_CHAPTER_VERSES.get((book, chapter))
    if divergent is not None:
        return divergent[numbering]
    counts = _verse_counts(sourcetexts_root)[SLUG_TO_HEBCAL_BOOK[book]]
    if not 1 <= chapter < len(counts):
        raise ValueError(f"{book} has no chapter {chapter}")
    return counts[chapter]


def chapters_in_book(book: str, sourcetexts_root: Path | None = None) -> int:
    return len(_verse_counts(sourcetexts_root)[SLUG_TO_HEBCAL_BOOK[book]]) - 1


def previous_verse(
    ref: VerseRef,
    sourcetexts_root: Path | None = None,
    numbering: str = DEFAULT_NUMBERING,
) -> VerseRef:
    """The verse before `ref`, stepping back over a chapter boundary when needed.

    Used to close a span at the verse before the next span begins, since the sources mark
    where each reading starts and leave the end implied.
    """
    if ref.verse > 1:
        return VerseRef(ref.book, ref.chapter, ref.verse - 1)
    if ref.chapter <= 1:
        raise ValueError(f"No verse precedes {ref}")
    chapter = ref.chapter - 1
    return VerseRef(
        ref.book, chapter, verses_in_chapter(ref.book, chapter, sourcetexts_root, numbering)
    )


def parse_hebcal_ref(book: str, spec: str) -> VerseRef:
    """Parse hebcal's ``"chapter:verse"`` form against an opensiddur book slug."""
    chapter, _, verse = spec.partition(":")
    return VerseRef(book, int(chapter), int(verse))
