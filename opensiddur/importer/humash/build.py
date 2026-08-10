"""Emit the humash project: structure over text transcluded from the Tanakh projects.

Every word of Torah, haftarah and megillah text is transcluded by URN. The only original
content is the headings and the reading instructions, so nothing here duplicates a text that
already exists in another project.

Targets carry no ``@project`` suffix, so which edition supplies the text is decided at compile
time by ``priority.transclusion``. The exception is the four chapters the editions divide into
verses differently, where one range cannot serve them all; those are emitted once per
numbering under ``opensiddur:verse-numbering``, defaulting to MAM's division.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from opensiddur.importer.feinstein_haggadah.tei_builder import validate_and_write
from opensiddur.importer.humash import model
from opensiddur.importer.humash.aliyot import CombinedParsha, Parsha, parse_readings
from opensiddur.importer.humash.names import (
    PAIR_FOR_MEMBER,
    SLUG_TO_HEBREW,
    slugify_reading_name,
)
from opensiddur.importer.humash.readings import (
    REPEATED_VERSE_INSTRUCTION,
    Passage,
    festival_readings,
    haftarot,
    triennial,
    triennial_haftarot,
    triennial_patterns,
)
from opensiddur.importer.humash.refs import (
    DEFAULT_NUMBERING,
    DIVERGENT_CHAPTER_VERSES,
    MEGILLOT,
    NUMBERINGS,
    SLUG_TO_HEBREW_BOOK,
    TORAH_BOOKS,
    UNIT_ALIYAH,
    UNIT_ALIYAH_COMBINED,
    UNIT_MAFTIR,
    UNIT_MAFTIR_COMBINED,
    UNIT_PARSHA,
    UNIT_PARSHA_COMBINED,
    UNIT_TRIENNIAL,
    UNIT_WEEKDAY,
    UNIT_WEEKDAY_COMBINED,
    VARIATION_COMBINED,
    ReadingSpan,
    VerseRef,
)

logger = logging.getLogger(__name__)

PROJECT = "humash"
URN_PREFIX = "urn:x-opensiddur:text:bible"

TEI_NS = "http://www.tei-c.org/ns/1.0"
J_NS = "http://jewishliturgy.org/ns/jlptei/2"

# What each unit-space is called in the margin.
UNIT_TITLES = {
    UNIT_ALIYAH: "עלייה",
    UNIT_WEEKDAY: "עליית חול",
    UNIT_MAFTIR: "מפטיר",
    UNIT_TRIENNIAL: "מחזור תלת־שנתי",
    UNIT_ALIYAH_COMBINED: "עלייה (מחוברות)",
    UNIT_WEEKDAY_COMBINED: "עליית חול (מחוברות)",
    UNIT_MAFTIR_COMBINED: "מפטיר (מחוברות)",
}

ALIYAH_TITLES = {
    "1": "רִאשׁוֹן", "2": "שֵׁנִי", "3": "שְׁלִישִׁי", "4": "רְבִיעִי",
    "5": "חֲמִישִׁי", "6": "שִׁשִּׁי", "7": "שְׁבִיעִי", "maftir": "מַפְטִיר",
    "מפטיר": "מַפְטִיר",
}

WEEKDAY_TITLES = {"1": "כֹּהֵן", "2": "לֵוִי", "3": "יִשְׂרָאֵל"}

# Sukkot's Chol HaMoed Shabbat maftir varies by which intermediate day it falls on
# ("maftir_day1".."maftir_day5"). Latin/digits here would be reversed when set in the
# surrounding right-to-left text, same as TRIENNIAL_YEARS below, so days are spelled out
# as Hebrew letters rather than left as the raw source label.
MAFTIR_DAY_LETTERS = {1: "א׳", 2: "ב׳", 3: "ג׳", 4: "ד׳", 5: "ה׳"}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _header(title_he: str, title_en: str, urn_suffix: str) -> str:
    """A leaf header, deferring version and source information to the project index."""
    index_urn = f"{URN_PREFIX}:humash@{PROJECT}"
    return f"""<tei:teiHeader>
  <tei:fileDesc>
    <tei:titleStmt>
      <tei:title type="main" xml:lang="he">{_escape(title_he)}</tei:title>
      <tei:title type="alt" xml:lang="en">{_escape(title_en)}</tei:title>
    </tei:titleStmt>
    <tei:editionStmt>
      <tei:p>See <tei:ref target="{index_urn}">the humash project header for version information</tei:ref>.</tei:p>
    </tei:editionStmt>
    <tei:publicationStmt>
      <tei:distributor>
        <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
      </tei:distributor>
      <tei:idno type="urn">{URN_PREFIX}:{urn_suffix}@{PROJECT}</tei:idno>
      <tei:availability status="free">
        <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero Public Domain Declaration (CC0)</tei:licence>
      </tei:availability>
    </tei:publicationStmt>
    <tei:sourceDesc>
      <tei:p>See <tei:ref target="{index_urn}">the humash project header for source information</tei:ref>.</tei:p>
    </tei:sourceDesc>
  </tei:fileDesc>
</tei:teiHeader>"""


def _document(header: str, body: str, lang: str = "he") -> str:
    return (
        f'<tei:TEI xmlns:tei="{TEI_NS}" xmlns:j="{J_NS}" xml:lang="{lang}">'
        f"{header}<tei:text xml:lang=\"{lang}\"><tei:body>{body}</tei:body></tei:text></tei:TEI>"
    )


# Cycle years, as the marker names them. Latin or digits here would be reversed when set in
# the surrounding right-to-left text, which is how "1.maftir" comes out as "ritfam.1".
TRIENNIAL_YEARS = {1: "א׳", 2: "ב׳", 3: "ג׳"}

# What the margin says of a division that belongs to the pair read together, so that it is not
# mistaken for the same-numbered aliyah of either single, which is beside it in the same file.
COMBINED_SUFFIX = "מְחֻבָּרוֹת"


def _triennial_title(label: str) -> str:
    """The margin text of a triennial marker.

    Labels are "<year>.<aliyah>", or "<variation>.<year>.<aliyah>" for a parshah that is
    sometimes read combined. A variation letter is dropped: only one variation is ever read in
    a given cycle, so naming it would say nothing to a reader of the volume it survives in.
    The combined reading is called out, because it sits beside the singles in the same file.
    """
    parts = label.split(".")
    variation = parts[0] if len(parts) == 3 else None
    year, aliyah = parts[-2], parts[-1]
    title = f"{TRIENNIAL_YEARS.get(int(year), year)} {ALIYAH_TITLES.get(aliyah, aliyah)}"
    if variation == VARIATION_COMBINED:
        return f"{title} ({COMBINED_SUFFIX})"
    return title


def _milestone_title(span: ReadingSpan) -> str:
    label = span.label
    if span.unit == UNIT_ALIYAH:
        return ALIYAH_TITLES.get(label, label)
    if span.unit == UNIT_WEEKDAY:
        return WEEKDAY_TITLES.get(label, label)
    if span.unit == UNIT_MAFTIR:
        if label.startswith("maftir_day"):
            day = int(label[len("maftir_day"):])
            return f"{ALIYAH_TITLES['maftir']} לְיוֹם {MAFTIR_DAY_LETTERS[day]}"
        return ALIYAH_TITLES["maftir"]
    if span.unit in (UNIT_PARSHA, UNIT_PARSHA_COMBINED):
        return SLUG_TO_HEBREW.get(label, label)
    if span.unit == UNIT_ALIYAH_COMBINED:
        return f"{ALIYAH_TITLES.get(label, label)} ({COMBINED_SUFFIX})"
    if span.unit == UNIT_WEEKDAY_COMBINED:
        return f"{WEEKDAY_TITLES.get(label, label)} ({COMBINED_SUFFIX})"
    if span.unit == UNIT_MAFTIR_COMBINED:
        return f"{ALIYAH_TITLES['maftir']} ({COMBINED_SUFFIX})"
    if span.unit.startswith("aliyah.triennial") or span.unit.startswith("maftir.triennial"):
        # Labels arrive as "<year>.<aliyah>" or "<variation>.<year>.<aliyah>".
        return _triennial_title(label)
    return label


def _milestone(span: ReadingSpan, urn_base: str) -> str:
    """The marker that opens a reading division. Its scope runs to the next of the same unit."""
    title = _milestone_title(span)
    if span.unit in (UNIT_PARSHA, UNIT_PARSHA_COMBINED):
        # A parshah's own URN, not one below the file's: inside a combined file the marker for
        # each single is what makes urn:...:parsha/<slug> resolve to that single's text.
        urn = f"{URN_PREFIX}:parsha/{span.label}"
    else:
        base = f"{URN_PREFIX}:parsha/{span.owner}" if span.owner else urn_base
        urn = f"{base}/{span.unit.replace('.', '_')}/{slugify_reading_name(span.label)}"
    return (
        f'<tei:milestone unit="{span.unit}" n="{_escape(title)}" corresp="{urn}"/>'
    )


def _transclude(target: str) -> str:
    return f'<j:transclude type="external" target="{target}"/>'


def _instruction(text: str) -> str:
    return f'<tei:note type="instruction" xml:lang="he">{_escape(text)}</tei:note>'


_CONDITION_INDEX = {"value": 0}


def _condition_id(prefix: str) -> str:
    _CONDITION_INDEX["value"] += 1
    return f"{prefix}_{_CONDITION_INDEX['value']}"


def _conditional(feature_type: str, feature: str, content: str, prefix: str) -> str:
    """Wrap `content` in a condition on one binary feature being true."""
    identifier = _condition_id(prefix)
    return (
        f'<j:conditional xml:id="{identifier}">'
        f'<tei:fs type="{feature_type}"><tei:f name="{feature}">'
        f'<tei:binary value="true"/></tei:f></tei:fs>'
        f"</j:conditional>{content}"
        f'<j:endConditional target="#{identifier}"/>'
    )


TRIENNIAL_PATTERN_FEATURE = "triennial-pattern-{pair}"


def _pattern_conditional(pair_slug: str, patterns: list[str], content: str) -> str:
    """Wrap `content` so it survives only in a cycle with one of these combine/separate patterns.

    ``opensiddur:torah-reading`` carries one pattern feature per pair, derived from the date.
    With no date declared the feature is undefined and every variation is kept, the way
    leaving ``opensiddur:rite`` unset keeps every rite's haftarah.
    """
    identifier = _condition_id("triennial")
    feature = TRIENNIAL_PATTERN_FEATURE.format(pair=pair_slug.replace("_", "-"))
    alternatives = "".join(
        f'<tei:fs type="opensiddur:torah-reading"><tei:f name="{feature}">'
        f"<tei:string>{pattern}</tei:string></tei:f></tei:fs>"
        for pattern in sorted(patterns)
    )
    return (
        f'<j:conditional xml:id="{identifier}"><j:any>{alternatives}</j:any></j:conditional>'
        f"{content}"
        f'<j:endConditional target="#{identifier}"/>'
    )


# Which readings the volume carries: `annual`, and one feature per year of the triennial cycle.
# All are false by default but `annual`, and several may be true at once, so one volume may be
# for a single Shabbat and another for a whole cycle. See exporter/calendar/compute.py.
CYCLE_FS = "opensiddur:reading-cycle"
ANNUAL_FEATURE = "annual"
CYCLE_YEARS = tuple(TRIENNIAL_YEARS)


def _cycle_condition(feature: str) -> str:
    """The test for one reading-cycle feature being true.

    Always a single feature, so that the answer is decisive. ``j:all`` over a false test and an
    undefined one is undefined per the truth tables, and undefined keeps the text it guards —
    which for readings that are alternatives to one another would print several at once.
    """
    return (
        f'<tei:fs type="{CYCLE_FS}"><tei:f name="{feature}">'
        f'<tei:binary value="true"/></tei:f></tei:fs>'
    )


def _triennial_year_feature(year: int) -> str:
    return f"triennial-year-{year}"


def _default_numbering_conditional(content: str) -> str:
    """Wrap `content` so it is used unless another numbering is explicitly selected.

    ``j:none`` over the other numberings is false as soon as one of them is true, and
    undefined while none is set — which keeps MAM's division as the default.
    """
    identifier = _condition_id("numbering_default")
    others = "".join(
        f'<tei:fs type="opensiddur:verse-numbering"><tei:f name="{numbering}">'
        f'<tei:binary value="true"/></tei:f></tei:fs>'
        for numbering in NUMBERINGS
        if numbering != DEFAULT_NUMBERING
    )
    return (
        f'<j:conditional xml:id="{identifier}"><j:none>{others}</j:none></j:conditional>'
        f"{content}"
        f'<j:endConditional target="#{identifier}"/>'
    )


Conditions = dict[str, tuple[str, list[str]]]


def _segment_xml(
    segment: model.Segment,
    urn_base: str,
    sourcetexts_root: Path | None,
    conditions: Conditions | None = None,
) -> str:
    """Milestones opening at this segment, then the text itself.

    `conditions` maps a unit-space to the pair and patterns its markers depend on. Each marker
    is wrapped on its own rather than the whole division at once, since the markers of a
    division are spread through the text they divide.
    """
    parts: list[str] = []
    for span in segment.opening:
        marker = _milestone(span, urn_base)
        condition = (conditions or {}).get(span.unit)
        parts.append(
            _pattern_conditional(condition[0], condition[1], marker)
            if condition is not None else marker
        )
    if segment.duplicate:
        parts.append(_instruction("חוזרים על הפסוק"))
    parts.append(_transclude(segment.start.range_urn(segment.end)))
    return "".join(parts)


def _numbered_variants(
    spans: list[ReadingSpan],
    start: VerseRef,
    end: VerseRef,
    urn_base: str,
    sourcetexts_root: Path | None,
    conditions: Conditions | None = None,
) -> str:
    """Emit one variant of a reading per verse numbering, under conditional control.

    Only reached for readings touching Exodus 20, Numbers 10, Numbers 25 or Deuteronomy 5.
    Everywhere else a single range resolves in every edition and no variant is needed.
    """
    parts: list[str] = []
    for numbering in NUMBERINGS:
        segments = model.segment_reading(
            _restated(spans, numbering), start, end, sourcetexts_root, numbering,
            allow_duplication=False,
        )
        content = "".join(
            _segment_xml(s, urn_base, sourcetexts_root, conditions) for s in segments
        )
        if numbering == DEFAULT_NUMBERING:
            parts.append(_default_numbering_conditional(content))
        else:
            parts.append(_conditional(
                "opensiddur:verse-numbering", numbering, content, f"numbering_{numbering}"
            ))
    return "".join(parts)


def _restated(spans: list[ReadingSpan], numbering: str) -> list[ReadingSpan]:
    """The spans as the given edition numbers them.

    Only the ends that fall on the last verse of a divergent chapter move: those are stated as
    "to the end of the chapter", and each edition ends the chapter at a different verse. A
    boundary inside such a chapter cannot be restated without a verse-by-verse alignment of the
    editions, so it is left alone and the reading keeps the numbering it was recorded in.
    """
    restated: list[ReadingSpan] = []
    for span in spans:
        end = span.end
        counts = DIVERGENT_CHAPTER_VERSES.get((end.book, end.chapter))
        if counts is not None and end.verse == counts[span.numbering]:
            end = VerseRef(end.book, end.chapter, counts[numbering])
        restated.append(ReadingSpan(
            unit=span.unit, label=span.label, start=span.start, end=end,
            note=span.note, numbering=numbering, owner=span.owner,
        ))
    return restated


TriennialDivisions = dict[tuple[str | None, int], list[ReadingSpan]]


def _reading_document(
    slug: str,
    hebrew: str,
    spans: list[ReadingSpan],
    start: VerseRef,
    end: VerseRef,
    conditions: Conditions | None,
    sourcetexts_root: Path | None,
) -> tuple[str, str]:
    """A parshah file: its heading, its reading divisions, and the text between them."""
    urn_base = f"{URN_PREFIX}:parsha/{slug}"

    # A parshah is one continuous reading, so it is always emitted once; see segment_reading.
    overlapping = model.overlapping_units(spans)
    if overlapping:
        logger.info(
            "%s: %s overlap themselves, so those milestones scope to the next marker rather "
            "than to their recorded end", slug, ", ".join(sorted(overlapping)),
        )

    needs_variants = any(span.crosses_divergent_chapter for span in spans)
    if needs_variants:
        body_inner = _numbered_variants(
            spans, start, end, urn_base, sourcetexts_root, conditions
        )
    else:
        segments = model.segment_reading(
            spans, start, end, sourcetexts_root, DEFAULT_NUMBERING,
            allow_duplication=False,
        )
        body_inner = "".join(
            _segment_xml(s, urn_base, sourcetexts_root, conditions) for s in segments
        )

    body = (
        f'<tei:div corresp="{urn_base}" n="{slug}">'
        f"<tei:head>{_escape(hebrew)}</tei:head>{body_inner}</tei:div>"
    )
    header = _header(hebrew, slug.replace("_", " ").title(), f"parsha/{slug}")
    return f"parashat_{slug}", _document(header, body)


def parsha_file(
    parsha: Parsha,
    triennial_divisions: TriennialDivisions,
    sourcetexts_root: Path | None = None,
) -> tuple[str, str]:
    """One weekly parshah, read on its own week."""
    spans = [parsha.parsha_span, *parsha.spans]
    for division in triennial_divisions.values():
        spans.extend(division)
    hebrew = SLUG_TO_HEBREW.get(parsha.slug, parsha.hebrew_name)
    return _reading_document(
        parsha.slug, hebrew, spans, parsha.start, parsha.end, None, sourcetexts_root
    )


def pair_file(
    pair: CombinedParsha,
    members: list[Parsha],
    triennial_divisions: dict[str, TriennialDivisions],
    patterns: dict[str, str],
    sourcetexts_root: Path | None = None,
) -> tuple[str, str]:
    """A pair that may be read together, holding both singles and the combined reading.

    The two are alternatives, not a whole and its parts, so they are separate unit-spaces over
    one copy of the text: the combined fourth aliyah runs through the point where the second
    parshah begins, and would be cut there if it were scoped by ``parsha.annual``.

    The combined divisions are unconditioned, so a volume carries the pair both ways. Each
    single's triennial divisions are not: which of them applies depends on how the pair fell
    in that cycle, and the condition says which cycles each is for.
    """
    spans = [pair.parsha_span]
    conditions: Conditions = {}
    for member in members:
        spans.append(member.parsha_span)
        # The singles' divisions keep their own URN space: both parshiyot have a first aliyah.
        spans.extend(replace(span, owner=member.slug) for span in member.spans)
        for (variation, _year), division in triennial_divisions.get(member.slug, {}).items():
            matching = sorted(
                pattern for pattern, name in patterns.items() if name == variation
            )
            if variation is not None and not matching:
                logger.warning(
                    "%s: no cycle pattern selects triennial variation %s, so its markers are "
                    "emitted unconditionally", member.slug, variation,
                )
            for span in division:
                if variation is not None and matching:
                    conditions[span.unit] = (pair.slug, matching)
            spans.extend(division)

    spans.extend(pair.spans)
    for division in triennial_divisions.get(pair.slug, {}).values():
        spans.extend(division)

    return _reading_document(
        pair.slug, SLUG_TO_HEBREW.get(pair.slug, pair.hebrew_name), spans,
        pair.start, pair.end, conditions, sourcetexts_root,
    )


# hebcal states a few boundaries inside a verse — Emor's third year names Nachum 2:2b-2:3a —
# and a URN reaches no further than a whole verse. Every such reference in the data today is on
# an anchor verse that readings.triennial_haftarot drops, so nothing emits these yet; they are
# here because the alternative, if hebcal moves one into a span that is read, is to silently
# read half a verse too much.
HALF_VERSE_START_INSTRUCTION = "מתחילים מאמצע הפסוק"
HALF_VERSE_END_INSTRUCTION = "מסיימים באמצע הפסוק"


def _passage_xml(passage: Passage, urn_base: str) -> str:
    """A haftarah or megillah: its spans in order, then any repeated closing verse."""
    parts: list[str] = []
    for span in passage.spans:
        if span.start_half == "b":
            parts.append(_instruction(HALF_VERSE_START_INSTRUCTION))
        parts.append(_transclude(span.start.range_urn(span.end)))
        if span.end_half == "a":
            parts.append(_instruction(HALF_VERSE_END_INSTRUCTION))
    if passage.repeated is not None:
        parts.append(_instruction(REPEATED_VERSE_INSTRUCTION))
        parts.append(_transclude(
            passage.repeated.start.range_urn(passage.repeated.end)
        ))
    return "".join(parts)


# The heading over a triennial haftarah. Unlike the triennial Torah divisions, which are
# markers in the margin of the annual text, these are whole alternative readings.
TRIENNIAL_HAFTARAH_TITLE = "מַחֲזוֹר תְּלַת־שְׁנָתִי, שָׁנָה {year}"


def haftarah_file(
    slug: str,
    passages: list[Passage],
    triennial_passages: dict[int, Passage] | None = None,
) -> tuple[str, str]:
    """The haftarah of one parshah: the annual reading, and the triennial ones as alternatives.

    The annual haftarah has a division per rite where the rites differ. The triennial readings
    have none — hebcal records a single reading per cycle year — so each is one headed division
    conditioned on the volume reading that year of the cycle.

    They are alternatives for the same Shabbat, so the annual reading is kept when the volume
    asks for it and also whenever the volume's cycle year has nothing to put in its place.
    Tazria, Achrei Mot and Behar are read alone only in years 1 and 2 and so have no reading
    for year 3; a parshah with no triennial reading at all is unconditional, as are the pairs,
    which have no triennial haftarah of their own.

    This is the one place the humash decides rather than keeping every variant. A volume that
    asks for nothing gets the annual reading, not all four: they belong to one week, and
    printing four haftarot for it would be wrong however they were headed.
    """
    urn_base = f"{URN_PREFIX}:haftarah/{slug}"
    hebrew = SLUG_TO_HEBREW.get(slug, slug)
    title = f"הַפְטָרַת {hebrew}"

    annual: list[str] = []
    for passage in passages:
        content = _passage_xml(passage, urn_base)
        if passage.rite is None:
            annual.append(content)
            continue
        variant = (
            f'<tei:div corresp="{urn_base}/{passage.rite}" n="{passage.rite}">'
            f"<tei:head>{_escape(passage.title or passage.rite)}</tei:head>"
            f"{content}</tei:div>"
        )
        annual.append(_conditional("opensiddur:rite", passage.rite, variant, "rite"))

    years = sorted(triennial_passages or {})
    inner = "".join(annual)
    if years:
        # The annual reading also stands in for the cycle years this parshah has none of, so a
        # triennial volume is never left with no haftarah at all for the week.
        missing = [year for year in CYCLE_YEARS if year not in years]
        identifier = _condition_id("annual_haftarah")
        alternatives = "".join(
            _cycle_condition(feature) for feature in
            [ANNUAL_FEATURE, *(_triennial_year_feature(year) for year in missing)]
        )
        inner = (
            f'<j:conditional xml:id="{identifier}"><j:any>{alternatives}</j:any>'
            f"</j:conditional>{inner}"
            f'<j:endConditional target="#{identifier}"/>'
        )
    for year in years:
        identifier = _condition_id("triennial_haftarah")
        year_title = TRIENNIAL_HAFTARAH_TITLE.format(year=TRIENNIAL_YEARS.get(year, year))
        division = (
            f'<tei:div corresp="{urn_base}/triennial/{year}" n="triennial_{year}">'
            f"<tei:head>{_escape(year_title)}</tei:head>"
            f"{_passage_xml(triennial_passages[year], urn_base)}</tei:div>"
        )
        inner += (
            f'<j:conditional xml:id="{identifier}">'
            f"{_cycle_condition(_triennial_year_feature(year))}</j:conditional>"
            f"{division}"
            f'<j:endConditional target="#{identifier}"/>'
        )

    body = (
        f'<tei:div corresp="{urn_base}" n="haftarah_{slug}">'
        f"<tei:head>{_escape(title)}</tei:head>{inner}</tei:div>"
    )
    header = _header(title, f"Haftarah for {slug.replace('_', ' ').title()}", f"haftarah/{slug}")
    return f"haftarat_{slug}", _document(header, body)


def megillah_file(book: str, hebrew: str, holiday: str) -> tuple[str, str]:
    """One of the five megillot, read whole on its festival."""
    from opensiddur.importer.humash.readings import REPEATED_CLOSING_VERSES

    urn_base = f"{URN_PREFIX}:megillah/{book}"
    parts = [_transclude(f"{URN_PREFIX}:{book}")]
    repeat = REPEATED_CLOSING_VERSES.get((f"megillah:{book}", book))
    if repeat is not None:
        chapter, verse = repeat
        ref = VerseRef(book, chapter, verse)
        parts.append(_instruction(REPEATED_VERSE_INSTRUCTION))
        parts.append(_transclude(ref.range_urn(ref)))

    content = (
        f'<tei:div corresp="{urn_base}" n="megillah_{book}">'
        f"<tei:head>{_escape(hebrew)}</tei:head>{''.join(parts)}</tei:div>"
    )
    body = _conditional("opensiddur:holiday", holiday, content, "megillah")
    header = _header(hebrew, book.replace("_", " ").title(), f"megillah/{book}")
    return f"megillat_{book}", _document(header, body)


def festival_file(
    slug: str,
    reading: dict,
    sourcetexts_root: Path | None = None,
) -> tuple[str, str]:
    """One festival or special-Shabbat reading, with its haftarah."""
    urn_base = f"{URN_PREFIX}:reading/{slug}"
    name = reading["name"]
    parts: list[str] = []

    spans = reading["aliyot"]
    if spans:
        by_book: dict[str, list[ReadingSpan]] = {}
        for span in spans:
            by_book.setdefault(span.book, []).append(span)
        for book_spans in by_book.values():
            ordered = sorted(book_spans, key=lambda span: (span.start, span.end))
            segments = model.segment_reading(
                ordered, sourcetexts_root=sourcetexts_root, numbering=ordered[0].numbering
            )
            parts.extend(_segment_xml(s, urn_base, sourcetexts_root) for s in segments)

    for passage in reading["haftarot"]:
        content = _passage_xml(passage, urn_base)
        if passage.rite is None:
            parts.append(content)
        else:
            variant = (
                f'<tei:div corresp="{urn_base}/{passage.rite}" n="{passage.rite}">'
                f"<tei:head>{_escape(passage.title or passage.rite)}</tei:head>"
                f"{content}</tei:div>"
            )
            parts.append(_conditional("opensiddur:rite", passage.rite, variant, "rite"))

    body = (
        f'<tei:div corresp="{urn_base}" n="reading_{slug}">'
        f'<tei:head xml:lang="en">{_escape(name)}</tei:head>{"".join(parts)}</tei:div>'
    )
    header = _header(name, name, f"reading/{slug}")
    return f"reading_{slug}", _document(header, body, lang="he")


def book_file(book: str, parshiyot: list[Parsha]) -> tuple[str, str]:
    """One of the five books, transcluding its parshiyot in order.

    A pair is transcluded once, by the pair's own URN: its file holds both singles, so
    transcluding the members as well would print their text twice.
    """
    urn_base = f"{URN_PREFIX}:humash/{book}"
    hebrew = SLUG_TO_HEBREW_BOOK[book]
    targets: list[str] = []
    for parsha in parshiyot:
        slug = PAIR_FOR_MEMBER.get(parsha.slug, parsha.slug)
        if not targets or targets[-1] != slug:
            targets.append(slug)
    inner = "".join(_transclude(f"{URN_PREFIX}:parsha/{slug}") for slug in targets)
    body = (
        f'<tei:div type="book" corresp="{urn_base}" n="{book}">'
        f"<tei:head>{_escape(hebrew)}</tei:head>{inner}</tei:div>"
    )
    header = _header(hebrew, book.title(), f"humash/{book}")
    return book, _document(header, body)


def index_file(extra_urns: list[str]) -> tuple[str, str]:
    """The project entry point, holding the bibliography and transcluding everything."""
    urn = f"{URN_PREFIX}:humash"
    inner = "".join(
        _transclude(f"{URN_PREFIX}:humash/{slug}") for _, slug, _ in TORAH_BOOKS
    ) + "".join(_transclude(target) for target in extra_urns)
    body = (
        f'<tei:div corresp="{urn}" n="humash">'
        f"<tei:head>{_escape('חֻמָּשׁ')}</tei:head>{inner}</tei:div>"
    )
    header = f"""<tei:teiHeader>
  <tei:fileDesc>
    <tei:titleStmt>
      <tei:title type="main" xml:lang="he">חֻמָּשׁ</tei:title>
      <tei:title type="alt" xml:lang="en">Humash</tei:title>
      <tei:respStmt>
        <tei:resp key="mrk">Markup</tei:resp>
        <tei:name ref="urn:x-opensiddur:opensiddur.org/efraim-feinstein">Efraim Feinstein</tei:name>
      </tei:respStmt>
    </tei:titleStmt>
    <tei:editionStmt>
      <tei:p>The Torah arranged by liturgical reading. This project holds no text of its own:
        every reading is transcluded by URN from a Tanakh project, and only the headings and
        instructions originate here.</tei:p>
    </tei:editionStmt>
    <tei:publicationStmt>
      <tei:distributor>
        <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
      </tei:distributor>
      <tei:idno type="urn">{urn}@{PROJECT}</tei:idno>
      <tei:availability status="free">
        <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero Public Domain Declaration (CC0)</tei:licence>
      </tei:availability>
    </tei:publicationStmt>
    <tei:sourceDesc>
      <tei:bibl xml:id="source_mam">
        <tei:title>Miqra al pi ha-Masorah</tei:title>
        <tei:ptr target="{URN_PREFIX}:index@miqra_al_pi_hamasorah"/>
        <tei:note>Source of the weekly parshah, aliyah and maftir divisions.</tei:note>
      </tei:bibl>
      <tei:bibl xml:id="source_hebcal">
        <tei:title>hebcal leyning</tei:title>
        <tei:ptr target="https://github.com/hebcal/hebcal-leyning"/>
        <tei:note>Source of the haftarot, the festival readings and the triennial cycle.</tei:note>
      </tei:bibl>
    </tei:sourceDesc>
  </tei:fileDesc>
</tei:teiHeader>"""
    return "index", _document(header, body)


def build(
    project_directory: Path,
    sourcetexts_root: Path | None = None,
    validate: bool = True,
) -> list[Path]:
    """Generate the whole humash project. Returns the files written."""
    project_dir = project_directory / PROJECT
    project_dir.mkdir(parents=True, exist_ok=True)

    parshiyot, pairs = parse_readings(sourcetexts_root)
    all_haftarot = haftarot(sourcetexts_root)
    all_triennial_haftarot = triennial_haftarot(sourcetexts_root)
    all_triennial = triennial(sourcetexts_root)
    all_patterns = triennial_patterns(sourcetexts_root)
    festivals = festival_readings(sourcetexts_root)

    documents: list[tuple[str, str]] = []
    by_slug = {parsha.slug: parsha for parsha in parshiyot}
    for parsha in parshiyot:
        # The fourteen that have a partner are emitted inside their pair's file instead.
        if parsha.slug in PAIR_FOR_MEMBER:
            continue
        documents.append(parsha_file(
            parsha, all_triennial.get(parsha.slug, {}), sourcetexts_root
        ))
    for pair in pairs:
        documents.append(pair_file(
            pair, [by_slug[slug] for slug in pair.members], all_triennial,
            all_patterns.get(pair.slug, {}), sourcetexts_root,
        ))

    by_book: dict[str, list[Parsha]] = {}
    for parsha in parshiyot:
        by_book.setdefault(parsha.book, []).append(parsha)
    for _, book, _ in TORAH_BOOKS:
        documents.append(book_file(book, by_book.get(book, [])))

    extra_urns: list[str] = []
    for slug, passages in sorted(all_haftarot.items()):
        documents.append(
            haftarah_file(slug, passages, all_triennial_haftarot.get(slug, {}))
        )
        extra_urns.append(f"{URN_PREFIX}:haftarah/{slug}")

    unplaced = sorted(set(all_triennial_haftarot) - set(all_haftarot))
    if unplaced:
        # Nothing to hang them off: a parshah with a triennial haftarah but no annual one would
        # have no file of its own, so say so rather than dropping it silently.
        logger.warning(
            "No haftarah file for %s, so their triennial haftarot were not emitted",
            ", ".join(unplaced),
        )
    for book, hebrew, holiday in MEGILLOT:
        documents.append(megillah_file(book, hebrew, holiday))
        extra_urns.append(f"{URN_PREFIX}:megillah/{book}")
    for slug, reading in sorted(festivals.items()):
        documents.append(festival_file(slug, reading, sourcetexts_root))
        extra_urns.append(f"{URN_PREFIX}:reading/{slug}")

    documents.append(index_file(extra_urns))

    written: list[Path] = []
    for file_name, content in documents:
        if validate:
            written.append(validate_and_write(content, file_name, project_dir))
        else:
            path = project_dir / f"{file_name}.xml"
            path.write_text(content, encoding="utf-8")
            written.append(path)
    logger.info("Wrote %d files to %s", len(written), project_dir)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--sourcetexts-root", type=Path, default=None)
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip RelaxNG/Schematron validation (requires the compiled schema otherwise).",
    )
    args = parser.parse_args(argv)
    build(args.project_dir, args.sourcetexts_root, validate=not args.no_validate)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
