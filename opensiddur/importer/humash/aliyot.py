"""Read the weekly parshiyot and their aliyot out of Miqra al pi ha-Masorah.

MAM marks the *start* of every reading division inline in the verse scaffolding of
``sheets/torah.tsv``, in a ``{{מ:עלייה}}`` template nested inside the ``{{מ:פסוק}}`` that
opens the verse:

    {{מ:פסוק|בראשית|א|א|סדר=א|עלייה={{מ:עלייה|א=בראשית|ב0=בראשית|ב1=ראשון|ב2=כהן}}}}

The parameters are:

==== ================================================================================
א    the label as printed in the margin
ב0   the weekly parshah this reading belongs to
ב1   the Shabbat aliyah — ראשון through שביעי
ב2   the weekday honour — כהן, לוי, ישראל, or ע"כ ישראל
ב3   מפטיר
ג0   the parshah name when this week is combined with the next, e.g. ויקהל–פקודי
ג1/ג3 the Shabbat aliyah or maftir of that combined reading
==== ================================================================================

Ends are not marked and must be inferred, separately within each unit-space, from the next
start in that same space — which is why the maftir, whose start falls inside the seventh
aliyah, does not shorten it. The one explicit end marker is ``ע"כ ישראל`` (עד כאן ישראל,
"thus far Yisrael"), which closes the weekday reading rather than opening a fourth aliyah.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from opensiddur.importer.miqra_al_pi_hamasorah.convert_tsv import _hebrew_numeral_to_int
from opensiddur.importer.humash.names import slug_for_hebrew
from opensiddur.importer.humash.refs import (
    HEBREW_BOOK_TO_SLUG,
    UNIT_ALIYAH,
    UNIT_MAFTIR,
    UNIT_PARSHA,
    UNIT_WEEKDAY,
    ReadingSpan,
    VerseRef,
    chapters_in_book,
    previous_verse,
    verses_in_chapter,
)
from opensiddur.importer.util.pages import miqra_al_pi_hamasorah_data_directory

logger = logging.getLogger(__name__)

# The seven Shabbat aliyot, in order, as MAM spells them.
SHABBAT_ALIYOT = ("ראשון", "שני", "שלישי", "רביעי", "חמישי", "ששי", "שביעי")
ALIYAH_NUMBER = {name: str(index + 1) for index, name in enumerate(SHABBAT_ALIYOT)}

# The weekday honours. ע"כ ישראל closes the reading instead of opening an aliyah.
WEEKDAY_HONOURS = ("כהן", "לוי", "ישראל")
WEEKDAY_END = 'ע"כ ישראל'
WEEKDAY_NUMBER = {name: str(index + 1) for index, name in enumerate(WEEKDAY_HONOURS)}

MAFTIR = "מפטיר"

_VERSE_TEMPLATE = re.compile(r"\{\{מ:פסוק\|([^{}]*?)(?=\||\}\})")
_ALIYAH_TEMPLATE = re.compile(r"\{\{מ:עלייה\|([^{}]*)\}\}")


@dataclass
class Parsha:
    """One weekly reading, with every division that begins inside it."""

    slug: str
    hebrew_name: str
    book: str
    start: VerseRef
    end: VerseRef | None = None
    spans: list[ReadingSpan] = field(default_factory=list)

    @property
    def parsha_span(self) -> ReadingSpan:
        return ReadingSpan(UNIT_PARSHA, self.slug, self.start, self.end)

    def spans_in(self, unit: str) -> list[ReadingSpan]:
        return [span for span in self.spans if span.unit == unit]


@dataclass
class _Marker:
    """One ``{{מ:עלייה}}`` occurrence, before ends have been worked out."""

    ref: VerseRef
    params: dict[str, str]


def _parse_template_params(body: str) -> dict[str, str]:
    """Split ``a=1|b=2`` into a dict, ignoring positional parameters."""
    params: dict[str, str] = {}
    for part in body.split("|"):
        key, sep, value = part.partition("=")
        if sep:
            params[key.strip()] = value.strip()
    return params


def _parse_verse_position(scaffold: str) -> VerseRef | None:
    """Read the book, chapter and verse out of the ``{{מ:פסוק}}`` that opens a row."""
    match = re.search(r"\{\{מ:פסוק\|([^|]+)\|([^|]+)\|([^|}]+)", scaffold)
    if not match:
        return None
    book = HEBREW_BOOK_TO_SLUG.get(match.group(1).strip())
    if book is None:
        return None
    chapter = _hebrew_numeral_to_int(match.group(2))
    verse = _hebrew_numeral_to_int(match.group(3))
    if chapter is None or verse is None:
        return None
    return VerseRef(book, chapter, verse)


def read_markers(sourcetexts_root: Path | None = None) -> list[_Marker]:
    """Every aliyah marker in torah.tsv, in reading order."""
    path = miqra_al_pi_hamasorah_data_directory(sourcetexts_root) / "sheets" / "torah.tsv"
    markers: list[_Marker] = []
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) < 4:
                continue
            scaffold = row[3]
            if "מ:עלייה" not in scaffold:
                continue
            ref = _parse_verse_position(scaffold)
            if ref is None:
                logger.warning("Could not locate the verse for an aliyah marker: %s", scaffold[:80])
                continue
            for body in _ALIYAH_TEMPLATE.findall(scaffold):
                markers.append(_Marker(ref=ref, params=_parse_template_params(body)))
    return markers


def _end_of_book(book: str, sourcetexts_root: Path | None) -> VerseRef:
    last_chapter = chapters_in_book(book, sourcetexts_root)
    return VerseRef(book, last_chapter, verses_in_chapter(book, last_chapter, sourcetexts_root))


def _close_spans(
    starts: list[tuple[str, VerseRef, str | None]],
    unit: str,
    final_end: VerseRef,
    sourcetexts_root: Path | None,
) -> list[ReadingSpan]:
    """Turn a unit-space's start points into spans, each ending before the next start.

    Only starts within the same unit-space are considered, so that a division belonging to
    another space cannot cut one of these short.
    """
    spans: list[ReadingSpan] = []
    for index, (label, start, note) in enumerate(starts):
        if index + 1 < len(starts):
            end = previous_verse(starts[index + 1][1], sourcetexts_root)
        else:
            end = final_end
        spans.append(ReadingSpan(unit=unit, label=label, start=start, end=end, note=note))
    return spans


def parse_parshiyot(sourcetexts_root: Path | None = None) -> list[Parsha]:
    """Build the 54 weekly parshiyot, each with its aliyot, weekday aliyot and maftir."""
    markers = read_markers(sourcetexts_root)

    # Group markers by parshah, in the order the parshiyot appear.
    parshiyot: list[Parsha] = []
    by_slug: dict[str, Parsha] = {}
    grouped: dict[str, list[_Marker]] = {}
    for marker in markers:
        name = marker.params.get("ב0")
        if not name:
            continue
        slug = slug_for_hebrew(name)
        parsha = by_slug.get(slug)
        if parsha is None:
            parsha = Parsha(slug=slug, hebrew_name=name, book=marker.ref.book, start=marker.ref)
            by_slug[slug] = parsha
            parshiyot.append(parsha)
            grouped[slug] = []
        grouped[slug].append(marker)

    # A parshah runs to the verse before the next one starts, or to the end of its book.
    for index, parsha in enumerate(parshiyot):
        following = parshiyot[index + 1] if index + 1 < len(parshiyot) else None
        if following is not None and following.book == parsha.book:
            parsha.end = previous_verse(following.start, sourcetexts_root)
        else:
            parsha.end = _end_of_book(parsha.book, sourcetexts_root)

    for parsha in parshiyot:
        parsha.spans = _spans_for(grouped[parsha.slug], parsha, sourcetexts_root)
    return parshiyot


def _spans_for(
    markers: list[_Marker],
    parsha: Parsha,
    sourcetexts_root: Path | None,
) -> list[ReadingSpan]:
    """Close each unit-space's markers into spans independently of the others."""
    aliyah_starts: list[tuple[str, VerseRef, str | None]] = []
    weekday_starts: list[tuple[str, VerseRef, str | None]] = []
    weekday_end: VerseRef | None = None
    maftir_start: VerseRef | None = None

    for marker in markers:
        params = marker.params
        aliyah = params.get("ב1")
        if aliyah in ALIYAH_NUMBER:
            aliyah_starts.append((ALIYAH_NUMBER[aliyah], marker.ref, None))
        honour = params.get("ב2")
        if honour in WEEKDAY_NUMBER:
            weekday_starts.append((WEEKDAY_NUMBER[honour], marker.ref, None))
        elif honour == WEEKDAY_END:
            # "Thus far Yisrael" marks where the weekday reading stops, so the last weekday
            # aliyah ends at the preceding verse rather than running on to the parshah's end.
            weekday_end = previous_verse(marker.ref, sourcetexts_root)
        if params.get("ב3") == MAFTIR:
            maftir_start = marker.ref

    spans = _close_spans(aliyah_starts, UNIT_ALIYAH, parsha.end, sourcetexts_root)
    spans += _close_spans(
        weekday_starts, UNIT_WEEKDAY, weekday_end or parsha.end, sourcetexts_root
    )
    if maftir_start is not None:
        # The maftir runs to the end of the parshah, overlapping the seventh aliyah.
        spans.append(
            ReadingSpan(UNIT_MAFTIR, MAFTIR, maftir_start, parsha.end)
        )
    return spans
