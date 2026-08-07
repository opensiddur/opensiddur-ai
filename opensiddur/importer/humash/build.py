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
from pathlib import Path

from opensiddur.importer.feinstein_haggadah.tei_builder import validate_and_write
from opensiddur.importer.humash import model
from opensiddur.importer.humash.aliyot import Parsha, parse_parshiyot
from opensiddur.importer.humash.names import SLUG_TO_HEBREW, slugify_reading_name
from opensiddur.importer.humash.readings import (
    REPEATED_VERSE_INSTRUCTION,
    Passage,
    festival_readings,
    haftarot,
    triennial,
    triennial_haftarot,
)
from opensiddur.importer.humash.refs import (
    DEFAULT_NUMBERING,
    DIVERGENT_CHAPTER_VERSES,
    MEGILLOT,
    NUMBERINGS,
    SLUG_TO_HEBREW_BOOK,
    TORAH_BOOKS,
    UNIT_ALIYAH,
    UNIT_MAFTIR,
    UNIT_PARSHA,
    UNIT_TRIENNIAL,
    UNIT_WEEKDAY,
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
}

ALIYAH_TITLES = {
    "1": "רִאשׁוֹן", "2": "שֵׁנִי", "3": "שְׁלִישִׁי", "4": "רְבִיעִי",
    "5": "חֲמִישִׁי", "6": "שִׁשִּׁי", "7": "שְׁבִיעִי", "maftir": "מַפְטִיר",
    "מפטיר": "מַפְטִיר",
}

WEEKDAY_TITLES = {"1": "כֹּהֵן", "2": "לֵוִי", "3": "יִשְׂרָאֵל"}


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


def _milestone(span: ReadingSpan, urn_base: str) -> str:
    """The marker that opens a reading division. Its scope runs to the next of the same unit."""
    label = span.label
    title = ""
    if span.unit == UNIT_ALIYAH:
        title = ALIYAH_TITLES.get(label, label)
    elif span.unit == UNIT_WEEKDAY:
        title = WEEKDAY_TITLES.get(label, label)
    elif span.unit == UNIT_MAFTIR:
        title = ALIYAH_TITLES["maftir"]
    else:
        title = label
    urn = f"{urn_base}/{span.unit.replace('.', '_')}/{slugify_reading_name(label)}"
    return (
        f'<tei:milestone unit="{span.unit}" n="{_escape(title)}" corresp="{urn}"/>'
    )


def _transclude(target: str) -> str:
    return f'<j:transclude type="external" target="{target}"/>'


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


def _segment_xml(
    segment: model.Segment,
    urn_base: str,
    sourcetexts_root: Path | None,
) -> str:
    """Milestones opening at this segment, then the text itself."""
    parts = [_milestone(span, urn_base) for span in segment.opening]
    if segment.duplicate:
        parts.append(
            f'<tei:note type="instruction" xml:lang="he">{_escape("חוזרים על הפסוק")}</tei:note>'
        )
    parts.append(_transclude(segment.start.range_urn(segment.end)))
    return "".join(parts)


def _numbered_variants(
    spans: list[ReadingSpan],
    start: VerseRef,
    end: VerseRef,
    urn_base: str,
    sourcetexts_root: Path | None,
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
        content = "".join(_segment_xml(s, urn_base, sourcetexts_root) for s in segments)
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
            note=span.note, numbering=numbering,
        ))
    return restated


def parsha_file(
    parsha: Parsha,
    triennial_spans: dict[int, list[ReadingSpan]],
    sourcetexts_root: Path | None = None,
) -> tuple[str, str]:
    """One weekly parshah: its heading, its reading divisions, and the text between them."""
    urn_base = f"{URN_PREFIX}:parsha/{parsha.slug}"
    spans = list(parsha.spans)
    for year_spans in triennial_spans.values():
        spans.extend(year_spans)

    # A parshah is one continuous reading, so it is always emitted once; see segment_reading.
    overlapping = model.overlapping_units(spans)
    if overlapping:
        logger.info(
            "%s: %s overlap themselves, so those milestones scope to the next marker rather "
            "than to their recorded end", parsha.slug, ", ".join(sorted(overlapping)),
        )

    needs_variants = any(span.crosses_divergent_chapter for span in spans)
    if needs_variants:
        body_inner = _numbered_variants(
            spans, parsha.start, parsha.end, urn_base, sourcetexts_root
        )
    else:
        segments = model.segment_reading(
            spans, parsha.start, parsha.end, sourcetexts_root, DEFAULT_NUMBERING,
            allow_duplication=False,
        )
        body_inner = "".join(_segment_xml(s, urn_base, sourcetexts_root) for s in segments)

    hebrew = SLUG_TO_HEBREW.get(parsha.slug, parsha.hebrew_name)
    body = (
        f'<tei:div corresp="{urn_base}" n="{parsha.slug}">'
        f"<tei:head>{_escape(hebrew)}</tei:head>"
        f'<tei:milestone unit="{UNIT_PARSHA}" n="{_escape(hebrew)}" corresp="{urn_base}"/>'
        f"{body_inner}</tei:div>"
    )
    header = _header(hebrew, parsha.slug.replace("_", " ").title(), f"parsha/{parsha.slug}")
    return f"parashat_{parsha.slug}", _document(header, body)


def _passage_xml(passage: Passage, urn_base: str) -> str:
    """A haftarah or megillah: its spans in order, then any repeated closing verse."""
    parts: list[str] = []
    for span in passage.spans:
        parts.append(_transclude(span.start.range_urn(span.end)))
    if passage.repeated is not None:
        parts.append(
            f'<tei:note type="instruction" xml:lang="he">'
            f"{_escape(REPEATED_VERSE_INSTRUCTION)}</tei:note>"
        )
        parts.append(_transclude(
            passage.repeated.start.range_urn(passage.repeated.end)
        ))
    return "".join(parts)


def haftarah_file(slug: str, passages: list[Passage]) -> tuple[str, str]:
    """The haftarah of one parshah, with a division per rite where the rites differ."""
    urn_base = f"{URN_PREFIX}:haftarah/{slug}"
    hebrew = SLUG_TO_HEBREW.get(slug, slug)
    title = f"הַפְטָרַת {hebrew}"

    inner: list[str] = []
    for passage in passages:
        content = _passage_xml(passage, urn_base)
        if passage.rite is None:
            inner.append(content)
            continue
        variant = (
            f'<tei:div corresp="{urn_base}/{passage.rite}" n="{passage.rite}">'
            f"<tei:head>{_escape(passage.title or passage.rite)}</tei:head>"
            f"{content}</tei:div>"
        )
        inner.append(_conditional("opensiddur:rite", passage.rite, variant, "rite"))

    body = (
        f'<tei:div corresp="{urn_base}" n="haftarah_{slug}">'
        f"<tei:head>{_escape(title)}</tei:head>{''.join(inner)}</tei:div>"
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
        parts.append(
            f'<tei:note type="instruction" xml:lang="he">'
            f"{_escape(REPEATED_VERSE_INSTRUCTION)}</tei:note>"
        )
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
    """One of the five books, transcluding its parshiyot in order."""
    urn_base = f"{URN_PREFIX}:humash/{book}"
    hebrew = SLUG_TO_HEBREW_BOOK[book]
    inner = "".join(
        _transclude(f"{URN_PREFIX}:parsha/{parsha.slug}") for parsha in parshiyot
    )
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
        <tei:ptr target="{URN_PREFIX}:tanakh@miqra_al_pi_hamasorah"/>
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

    parshiyot = parse_parshiyot(sourcetexts_root)
    all_haftarot = haftarot(sourcetexts_root)
    all_triennial = triennial(sourcetexts_root)
    festivals = festival_readings(sourcetexts_root)

    documents: list[tuple[str, str]] = []
    for parsha in parshiyot:
        documents.append(parsha_file(
            parsha, all_triennial.get(parsha.slug, {}), sourcetexts_root
        ))

    by_book: dict[str, list[Parsha]] = {}
    for parsha in parshiyot:
        by_book.setdefault(parsha.book, []).append(parsha)
    for _, book, _ in TORAH_BOOKS:
        documents.append(book_file(book, by_book.get(book, [])))

    extra_urns: list[str] = []
    for slug, passages in sorted(all_haftarot.items()):
        documents.append(haftarah_file(slug, passages))
        extra_urns.append(f"{URN_PREFIX}:haftarah/{slug}")
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
