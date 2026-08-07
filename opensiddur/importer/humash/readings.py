"""Haftarot, festival readings and the modern triennial cycle, read from the hebcal data.

MAM records no haftarot and no festival readings at all, so these come from hebcal. Each is
modelled as a *passage*: an ordered list of spans, because a haftarah is frequently
discontinuous and occasionally moves backwards through its book — Mishpatim reads Jeremiah
34:8-22 and then 33:25-26 — and because two of them bridge books.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path

from opensiddur.importer.humash.names import HEBCAL_TO_SLUG, slugify_reading_name
from opensiddur.importer.humash.refs import (
    BOOK_NUMBER_TO_SLUG,
    NUMBERING_COMMON,
    HEBCAL_BOOK_TO_SLUG,
    UNIT_ALIYAH,
    UNIT_MAFTIR,
    triennial_unit,
    ReadingSpan,
    VerseRef,
    parse_hebcal_ref,
)
from opensiddur.importer.util.pages import hebcal_leyning_data_directory

# The rites hebcal distinguishes. "haft" is what it gives without qualification, which is the
# Ashkenazi reading; "seph" is the Sephardi one. Other rites are not in this data.
RITE_ASHKENAZ = "ashkenaz"
RITE_SEPHARAD = "sepharad"
HEBCAL_RITE_KEYS = {"haft": RITE_ASHKENAZ, "seph": RITE_SEPHARAD}

RITE_TITLES = {
    RITE_ASHKENAZ: "מִנְהַג אַשְׁכְּנַז",
    RITE_SEPHARAD: "מִנְהַג סְפָרַד",
}

# Readings that repeat an earlier verse after the last one, so as not to end on a verse of
# rebuke or calamity. hebcal does not record this, and it is invisible in the output if
# forgotten, so it is listed here explicitly.
#
# Keyed by (reading key, book slug) -> the verse to repeat at the end.
REPEATED_CLOSING_VERSES: dict[tuple[str, str], tuple[int, int]] = {
    # Isaiah 66:24 ends "their worm shall not die"; 66:23 is read again after it.
    ("Shabbat Rosh Chodesh", "isaiah"): (66, 23),
    # Malachi 3:24 ends with a curse, so 3:23 is repeated after it.
    ("Shabbat HaGadol", "malachi"): (3, 23),
    # The last verse of Lamentations is a lament; 5:21 is repeated after 5:22.
    ("megillah:lamentations", "lamentations"): (5, 21),
    # Ecclesiastes 12:13 is repeated after 12:14.
    ("megillah:ecclesiastes", "ecclesiastes"): (12, 13),
}

REPEATED_VERSE_INSTRUCTION = "חוזרים ואומרים את הפסוק הקודם"


@dataclass
class Passage:
    """One reading: an ordered list of spans, possibly discontinuous or across books."""

    key: str
    spans: list[ReadingSpan] = field(default_factory=list)
    rite: str | None = None
    title: str | None = None
    note: str | None = None
    # A verse repeated after the end so the reading does not close on a hard verse.
    repeated: ReadingSpan | None = None

    @property
    def books(self) -> list[str]:
        seen: list[str] = []
        for span in self.spans:
            if span.book not in seen:
                seen.append(span.book)
        return seen


@functools.cache
def _load(name: str, sourcetexts_root: Path | None = None) -> dict:
    path = hebcal_leyning_data_directory(sourcetexts_root) / name
    return json.loads(path.read_text(encoding="utf-8"))


def _haftarah_spans(raw, unit: str = "haftarah") -> list[ReadingSpan]:
    """Turn hebcal's haftarah value — one object or a list of them — into spans."""
    parts = raw if isinstance(raw, list) else [raw]
    spans: list[ReadingSpan] = []
    for index, part in enumerate(parts, start=1):
        book = HEBCAL_BOOK_TO_SLUG[part["k"]]
        spans.append(ReadingSpan(
            unit=unit,
            label=str(index),
            start=parse_hebcal_ref(book, part["b"]),
            end=parse_hebcal_ref(book, part["e"]),
            note=part.get("note"),
            numbering=NUMBERING_COMMON,
        ))
    return spans


def _repeated_span(key: str, spans: list[ReadingSpan]) -> ReadingSpan | None:
    """The closing verse to repeat, if this reading has one."""
    if not spans:
        return None
    book = spans[-1].end.book
    repeat = REPEATED_CLOSING_VERSES.get((key, book))
    if repeat is None:
        return None
    chapter, verse = repeat
    ref = VerseRef(book, chapter, verse)
    return ReadingSpan(unit="haftarah.repeated", label="repeated", start=ref, end=ref)


def haftarot(sourcetexts_root: Path | None = None) -> dict[str, list[Passage]]:
    """The haftarah of each weekly parshah, by slug, one Passage per rite."""
    data = _load("aliyot.json", sourcetexts_root)
    result: dict[str, list[Passage]] = {}
    for name, entry in data.items():
        slug = HEBCAL_TO_SLUG.get(name)
        if slug is None:
            continue
        passages: list[Passage] = []
        for hebcal_key, rite in HEBCAL_RITE_KEYS.items():
            if hebcal_key not in entry:
                continue
            spans = _haftarah_spans(entry[hebcal_key])
            passages.append(Passage(
                key=name,
                spans=spans,
                rite=rite,
                title=RITE_TITLES[rite],
                repeated=_repeated_span(name, spans),
            ))
        if passages:
            # A parshah with only one recorded haftarah has no rite variation to show.
            if len(passages) == 1:
                passages[0].rite = None
                passages[0].title = None
            result[slug] = passages
    return result


def festival_readings(sourcetexts_root: Path | None = None) -> dict[str, dict]:
    """Every festival and special-Shabbat reading, keyed by hebcal's name for the occasion.

    Each value holds the Torah spans (``aliyot``) and one Passage per rite (``haftarot``).
    The Torah reading of a festival is drawn from wherever in the Torah it belongs, so unlike
    the weekly parshiyot these spans may come from any book.
    """
    data = _load("holiday-readings.json", sourcetexts_root)
    result: dict[str, dict] = {}
    for name, entry in data.items():
        aliyot_spans: list[ReadingSpan] = []
        for label, value in entry.get("fullkriyah", {}).items():
            book = BOOK_NUMBER_TO_SLUG[value["k"]]
            unit = UNIT_MAFTIR if label == "M" else UNIT_ALIYAH
            aliyot_spans.append(ReadingSpan(
                unit=unit,
                label="maftir" if label == "M" else label,
                start=parse_hebcal_ref(book, value["b"]),
                end=parse_hebcal_ref(book, value["e"]),
                numbering=NUMBERING_COMMON,
            ))
        passages: list[Passage] = []
        for hebcal_key, rite in HEBCAL_RITE_KEYS.items():
            if hebcal_key not in entry:
                continue
            spans = _haftarah_spans(entry[hebcal_key])
            passages.append(Passage(
                key=name, spans=spans, rite=rite, title=RITE_TITLES[rite],
                repeated=_repeated_span(name, spans),
            ))
        if len(passages) == 1:
            passages[0].rite = None
            passages[0].title = None
        result[slugify_reading_name(name)] = {
            "name": name,
            "aliyot": sorted(aliyot_spans, key=lambda span: (span.unit, span.label)),
            "haftarot": passages,
        }
    return result


def triennial(sourcetexts_root: Path | None = None) -> dict[str, dict[int, list[ReadingSpan]]]:
    """The modern triennial division of each parshah, by slug then cycle year (1-3)."""
    data = _load("triennial.json", sourcetexts_root)
    result: dict[str, dict[int, list[ReadingSpan]]] = {}
    for name, entry in data.items():
        slug = HEBCAL_TO_SLUG.get(name)
        if slug is None:
            continue
        book = BOOK_NUMBER_TO_SLUG[entry["book"]]
        years: dict[int, list[ReadingSpan]] = {}
        # Most entries hold the three years under "years". Those whose division depends on
        # whether the parshah is read alone or combined that year use "variations" instead,
        # keyed either "Y.n" — the same fixed three years — or by a year-pattern name such as
        # "C.2", which cannot be reduced to a cycle year and is skipped.
        divisions = entry.get("years") or entry.get("variations") or {}
        for year_key, aliyot in divisions.items():
            if not year_key.startswith("Y.") or not isinstance(aliyot, dict):
                continue
            year = int(year_key.split(".", 1)[1])
            spans: list[ReadingSpan] = []
            for label, value in (aliyot or {}).items():
                if not isinstance(value, list) or len(value) < 2:
                    continue
                # The maftir re-reads the close of that year's seventh aliyah, so like the
                # annual maftir it needs a unit-space of its own or it would cut the aliyah
                # short; and each cycle year needs one because the years overlap each other.
                spans.append(ReadingSpan(
                    unit=triennial_unit(year, maftir=label == "M"),
                    label=f"{year}.{'maftir' if label == 'M' else label}",
                    start=parse_hebcal_ref(book, value[0]),
                    end=parse_hebcal_ref(book, value[1]),
                    numbering=NUMBERING_COMMON,
                ))
            if spans:
                years[year] = spans
        if years:
            result[slug] = years
    return result


def triennial_haftarot(sourcetexts_root: Path | None = None) -> dict[str, dict[int, Passage]]:
    """The triennial haftarah of each parshah, by slug then cycle year."""
    data = _load("triennial-haft.json", sourcetexts_root)
    result: dict[str, dict[int, Passage]] = {}
    for name, entry in data.items():
        slug = HEBCAL_TO_SLUG.get(name)
        if slug is None:
            continue
        years: dict[int, Passage] = {}
        for year_key, value in entry.items():
            if not year_key.isdigit() or not isinstance(value, dict) or "k" not in value:
                continue
            years[int(year_key)] = Passage(
                key=f"{name}:triennial:{year_key}",
                spans=_haftarah_spans(value),
                note=value.get("note"),
            )
        if years:
            result[slug] = years
    return result
