"""Verse references and reading spans — the vocabulary the whole humash importer shares.

A *reading span* is a named, explicitly bounded stretch of text belonging to one *unit-space*.
Ends are always stored, never inferred from the next span, because reading divisions overlap:
the maftir re-reads the close of the seventh aliyah, and the weekday aliyot subdivide the
Shabbat ones. See ``model.py`` for how overlapping spans are emitted.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from pathlib import Path

from opensiddur.common import versification
from opensiddur.common.versification import NUMBERING_COMMON, NUMBERING_MASORAH
from opensiddur.importer.util.pages import hebcal_leyning_data_directory

# Unit-spaces. These become tei:milestone/@unit, and refdb.UNIT_CONTAINED_BY decides which of
# them may terminate which; they are deliberately distinct so that they do not truncate one
# another.
UNIT_PARSHA = "parsha.annual"
UNIT_ALIYAH = "aliyah.annual"
UNIT_WEEKDAY = "aliyah.weekday"
UNIT_MAFTIR = "maftir.annual"

# The divisions of a week on which two parshiyot are read together. They are a separate
# division of the same text, not a subdivision of either single: the fourth aliyah of the
# combined Vayakhel-Pekudei is Exodus 38:1-39:1, which runs straight through the point where
# Pekudei begins. So they are contained by parsha.combined and not by parsha.annual, which
# would cut them at that boundary.
UNIT_PARSHA_COMBINED = "parsha.combined"
UNIT_ALIYAH_COMBINED = "aliyah.combined"
UNIT_WEEKDAY_COMBINED = "aliyah.weekday.combined"
UNIT_MAFTIR_COMBINED = "maftir.combined"

# Each year of the triennial cycle is its own division of the same text, and consecutive
# years deliberately overlap — in Beshalach, year 1's fifth aliyah and year 2's first are the
# same verses — so each year needs a unit-space of its own.
UNIT_TRIENNIAL = "aliyah.triennial"
UNIT_TRIENNIAL_MAFTIR = "maftir.triennial"

# The variation of a parshah that is sometimes read combined: how it divides depends on
# whether it was read alone or with its partner in each year of the cycle, so its unit-space
# carries the variation as well as the year. See readings.triennial.
VARIATION_COMBINED = "combined"


def triennial_unit(
    year: int,
    maftir: bool = False,
    variation: str | None = None,
    owner: str | None = None,
) -> str:
    """The unit-space of one year of one triennial division.

    A parshah that shares a file with its partner names itself as the owner, because the two
    divide the same file and may cover the same verses: in the cycle hebcal calls IL3, Behar
    read alone in year 2 is Leviticus 25:39-26:46, which runs well into Bechukotai. Sharing a
    unit-space would cut one of them short at the other's first marker.
    """
    base = UNIT_TRIENNIAL_MAFTIR if maftir else UNIT_TRIENNIAL
    parts = [base, owner, variation, str(year)]
    return ".".join(part for part in parts if part)

# The five books, in order, as MAM names them in Hebrew.
TORAH_BOOKS: tuple[tuple[str, str, str], ...] = (
    # (MAM Hebrew name, opensiddur slug, hebcal English name)
    ("בראשית", "genesis", "Genesis"),
    ("שמות", "exodus", "Exodus"),
    ("ויקרא", "leviticus", "Leviticus"),
    ("במדבר", "numbers", "Numbers"),
    ("דברים", "deuteronomy", "Deuteronomy"),
)

# The prophetic books the haftarot draw on, plus the five megillot. hebcal names them the way
# the left column does; the projects file them under the slug in the right.
OTHER_BOOKS: tuple[tuple[str, str], ...] = (
    ("Joshua", "joshua"),
    ("Judges", "judges"),
    ("I Samuel", "samuel_1"),
    ("II Samuel", "samuel_2"),
    ("I Kings", "kings_1"),
    ("II Kings", "kings_2"),
    ("Isaiah", "isaiah"),
    ("Jeremiah", "jeremiah"),
    ("Ezekiel", "ezekiel"),
    ("Hosea", "hosea"),
    ("Joel", "joel"),
    ("Amos", "amos"),
    ("Obadiah", "obadiah"),
    ("Jonah", "jonah"),
    ("Micah", "micah"),
    ("Nachum", "nahum"),
    ("Habakkuk", "habakkuk"),
    ("Zephaniah", "zephaniah"),
    ("Haggai", "haggai"),
    ("Zechariah", "zechariah"),
    ("Malachi", "malachi"),
    ("Song of Songs", "song_of_songs"),
    ("Ruth", "ruth"),
    ("Lamentations", "lamentations"),
    ("Ecclesiastes", "ecclesiastes"),
    ("Esther", "esther"),
)

# Unvocalized Hebrew names for the books a haftarah or megillah is drawn from, for citations.
# Matches the forms miqra_al_pi_hamasorah.convert_tsv.TANAKH_INDEX uses for the same books.
SLUG_TO_HEBREW_OTHER_BOOK: dict[str, str] = {
    "joshua": "יהושע",
    "judges": "שופטים",
    "samuel_1": "שמואל א",
    "samuel_2": "שמואל ב",
    "kings_1": "מלכים א",
    "kings_2": "מלכים ב",
    "isaiah": "ישעיהו",
    "jeremiah": "ירמיהו",
    "ezekiel": "יחזקאל",
    "hosea": "הושע",
    "joel": "יואל",
    "amos": "עמוס",
    "obadiah": "עבדיה",
    "jonah": "יונה",
    "micah": "מיכה",
    "nahum": "נחום",
    "habakkuk": "חבקוק",
    "zephaniah": "צפניה",
    "haggai": "חגי",
    "zechariah": "זכריה",
    "malachi": "מלאכי",
    "song_of_songs": "שיר השירים",
    "ruth": "רות",
    "lamentations": "איכה",
    "ecclesiastes": "קהלת",
    "esther": "אסתר",
}

# The five megillot, each with the occasion it is read on and its Hebrew title. The occasion
# names are features of the existing opensiddur:holiday feature structure.
MEGILLOT: tuple[tuple[str, str, str], ...] = (
    # (book slug, Hebrew title, opensiddur:holiday feature)
    ("song_of_songs", "שִׁיר הַשִּׁירִים", "pesah"),
    ("ruth", "רוּת", "shavuot"),
    ("lamentations", "אֵיכָה", "tisha-bav"),
    ("ecclesiastes", "קֹהֶלֶת", "sukkot"),
    ("esther", "אֶסְתֵּר", "purim"),
)

# The book names pointed, for headings. As with the parshah names, the table above holds the
# form to match MAM's text against; a title on the page wants vowels. test_build asserts these
# differ from it by vowels alone.
SLUG_TO_VOCALIZED_BOOK: dict[str, str] = {
    "genesis": "בְּרֵאשִׁית",
    "exodus": "שְׁמוֹת",
    "leviticus": "וַיִּקְרָא",
    "numbers": "בְּמִדְבַּר",
    "deuteronomy": "דְּבָרִים",
}

HEBREW_BOOK_TO_SLUG = {hebrew: slug for hebrew, slug, _ in TORAH_BOOKS}
SLUG_TO_HEBREW_BOOK = {slug: hebrew for hebrew, slug, _ in TORAH_BOOKS}

# Every book the humash reads from, Torah or not, for citations (build._citation).
SLUG_TO_HEBREW_ANY_BOOK: dict[str, str] = {**SLUG_TO_HEBREW_BOOK, **SLUG_TO_HEBREW_OTHER_BOOK}

SLUG_TO_HEBCAL_BOOK = {slug: english for _, slug, english in TORAH_BOOKS}
HEBCAL_BOOK_TO_SLUG = {english: slug for _, slug, english in TORAH_BOOKS}
HEBCAL_BOOK_TO_SLUG.update(dict(OTHER_BOOKS))
# Every book the humash reads from, not only the Torah: a megillah is transcluded as a range
# over its whole book, which needs that book's verse counts.
SLUG_TO_HEBCAL_BOOK.update({slug: english for english, slug in OTHER_BOOKS})

# hebcal numbers the Torah books 1-5 in the festival readings.
BOOK_NUMBER_TO_SLUG = {number: slug for number, (_, slug, _) in enumerate(TORAH_BOOKS, start=1)}


# The bible URN space has one canonical verse division (opensiddur.common.versification), so
# every range here is stated in it. The sources are not: MAM gives the weekly aliyot in its own
# numbering and hebcal gives everything else in the common printed editions', and in the
# Decalogue and a handful of other chapters those differ from canonical. Each reference is
# converted where it is read, by _parse_verse_position for MAM and parse_hebcal_ref for hebcal,
# so that nothing downstream has to carry a numbering at all.


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
    # The reading this span's URN hangs off, where that is not the file it is emitted in. Set
    # for the two parshiyot of a pair, which share a file but keep their own URN spaces:
    # without it their identically numbered aliyot would both be .../vayakhel_pekudei/1.
    owner: str | None = None
    # Where the span really begins or ends, when that is inside a verse rather than at its
    # edge: "b" on `start_half` means it begins at the second half of `start`, and "a" on
    # `end_half` that it ends at the first half of `end`. The whole verse is transcluded either
    # way — a URN addresses no less than a verse — and the reading says where to stop.
    start_half: str | None = None
    end_half: str | None = None

    @property
    def book(self) -> str:
        """The book this span lies in. Both ends are always in the same one."""
        return self.start.book

    def __post_init__(self):
        if self.start.book != self.end.book:
            raise ValueError(f"{self.unit} {self.label} crosses books: {self.start}-{self.end}")
        if self.end < self.start:
            raise ValueError(f"{self.unit} {self.label} ends before it starts: {self.start}-{self.end}")


@functools.cache
def _verse_counts(sourcetexts_root: Path | None = None) -> dict[str, list[int]]:
    """Verses per chapter, by hebcal book name. Index 0 is a placeholder, so chapters are 1-based."""
    path = hebcal_leyning_data_directory(sourcetexts_root) / "numverses.json"
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_ref(numbering: str, ref: VerseRef, at_end: bool = False) -> VerseRef:
    """`ref`, stated in `numbering`, as a verse of the canonical division.

    An edition verse may cover several canonical ones — MAM reads the four short commandments
    as a single verse where the canonical division has four — so a reference that opens a
    reading takes the first of them and one that closes it takes the last.
    """
    first, last = versification.to_canonical(numbering, ref.book, ref.chapter, ref.verse)
    chosen = last if at_end else first
    return VerseRef(ref.book, chosen.chapter, chosen.verse)


def verses_in_chapter(
    book: str,
    chapter: int,
    sourcetexts_root: Path | None = None,
) -> int:
    """How many verses chapter `chapter` of `book` (an opensiddur slug) has, canonically.

    hebcal's counts follow the common printed editions, which in a few chapters are coarser
    than the canonical division: taking hebcal's count for canonical Exodus 20 would end the
    chapter three verses early.
    """
    canonical = versification.CANONICAL_VERSE_COUNTS.get((book, chapter))
    if canonical is not None:
        return canonical
    counts = _verse_counts(sourcetexts_root)[SLUG_TO_HEBCAL_BOOK[book]]
    if not 1 <= chapter < len(counts):
        raise ValueError(f"{book} has no chapter {chapter}")
    return counts[chapter]


def chapters_in_book(book: str, sourcetexts_root: Path | None = None) -> int:
    return len(_verse_counts(sourcetexts_root)[SLUG_TO_HEBCAL_BOOK[book]]) - 1


def previous_verse(
    ref: VerseRef,
    sourcetexts_root: Path | None = None,
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
        ref.book, chapter, verses_in_chapter(ref.book, chapter, sourcetexts_root)
    )


def next_verse(
    ref: VerseRef,
    sourcetexts_root: Path | None = None,
) -> VerseRef:
    """The verse after `ref`, stepping over a chapter boundary when needed.

    Used to tell whether one reading span continues directly into the next, or whether the
    reading skips or backtracks between them.
    """
    if ref.verse < verses_in_chapter(ref.book, ref.chapter, sourcetexts_root):
        return VerseRef(ref.book, ref.chapter, ref.verse + 1)
    if ref.chapter >= chapters_in_book(ref.book, sourcetexts_root):
        raise ValueError(f"No verse follows {ref}")
    return VerseRef(ref.book, ref.chapter + 1, 1)


# hebcal writes a boundary that falls inside a verse as a letter after the verse number: the
# triennial haftarah of Emor in year 3 runs from Nachum 2:2b to 2:3a, the second half of one
# verse to the first half of the next. Three references in the data are of this form.
_HEBCAL_REF = re.compile(r"\s*(\d+)\s*:\s*(\d+)\s*([ab]?)\s*\Z")


def parse_hebcal_ref(book: str, spec: str, at_end: bool = False) -> VerseRef:
    """Parse hebcal's ``"chapter:verse"`` form against an opensiddur book slug.

    hebcal numbers by the common printed editions, so the result is converted to the canonical
    division the URN space uses. A half-verse marker is read as the whole verse containing it,
    since a URN addresses whole verses; ``hebcal_ref_half`` recovers which half was meant so
    the reading can say so.
    """
    match = _HEBCAL_REF.match(spec)
    if match is None:
        raise ValueError(f"Unparseable hebcal reference {spec!r} in {book}")
    return canonical_ref(
        NUMBERING_COMMON, VerseRef(book, int(match.group(1)), int(match.group(2))), at_end
    )


def hebcal_ref_half(spec: str) -> str | None:
    """Which half of the verse a reference names — ``"a"``, ``"b"``, or None for the whole."""
    match = _HEBCAL_REF.match(spec)
    if match is None:
        raise ValueError(f"Unparseable hebcal reference {spec!r}")
    return match.group(3) or None
