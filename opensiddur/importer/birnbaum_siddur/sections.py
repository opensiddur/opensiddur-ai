"""What becomes a file, and what each file is called.

The Birnbaum siddur's own table of contents already groups its units the way the book
does: seven groups, each divided into services. That grouping is the skeleton of the
JLPTEI project, so it is read out of the source rather than re-invented in a table here,
which is the one part of this importer that differs from the haggadah's hand-curated
``sections.py``. Where the haggadah had no machine-readable order, this book states its
own.

What still has to be decided by hand is the *boundary*: which of those units become
separately addressable files. This module reports the candidates for review — see
``specs/BIRNBAUM_UNITS.md`` — rather than settling it.

Two groups are excluded outright: the Rosh Hashanah and Yom Kippur machzorim are a
separate book, and the table of contents advertises far more of them than exists. So is
anything the 1949 printing does not paginate, which is the single test that also removes
the modern Israeli additions and the Passover haggadah, without a hand-maintained list.

Run as::

    uv run python -m opensiddur.importer.birnbaum_siddur.sections --report-units
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from opensiddur.importer.birnbaum_siddur.translit import transliterate, uncertain
from opensiddur.importer.util.pages import (
    birnbaum_siddur_correspondence_path,
    birnbaum_siddur_data_directory,
    birnbaum_siddur_source_text_directory,
    default_sourcetexts_root,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT_TITLE = "הסידור השלם (בירנבוים)"
RITE = "אשכנז"
TOC_PAGE = f"{RITE}.txt"

HEADING_RE = re.compile(r"^==\s*(.+?)\s*==$", re.MULTILINE)
BULLET_RE = re.compile(r"^\*\s*(.*)$", re.MULTILINE)
LINK_RE = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")
BOLD_LEAD_RE = re.compile(r"^'''(.+?):?'''")
PAGE_LABEL_RE = re.compile(r"עמוד\s+(\d+)")
NUSACH_RE = re.compile(r"\{\{\s*נוסח\s*\|")
INSTRUCTION_RE = re.compile(r"\{\{\s*(?:הסידור השלם|סידור בירנבוים)\s+הוראה\s*\|")
WIP_RE = re.compile(r"\{\{\s*בעבודה")

# The machzorim are a different book. Their two groups are dropped whole.
MACHZOR_GROUPS = ("רֹאשׁ הַשָּׁנָה", "הַכִּפּוּרִים")

# ToC group -> the `siddur:` occasion. Matched on a distinctive substring, since the
# headings are vocalised and numbered.
OCCASION_BY_GROUP = (
    ("חוֹל", "chol"),
    ("בְּרָכוֹת", "berakhot"),
    ("הַשַּׁבָּת", "shabbat"),
    ("מוֹעֲדִים", "moadim"),
    ("הוֹסָפוֹת", "hosafot"),
)

SERVICE_KEYWORDS = (
    ("שַׁחֲרִית", "shacharit"),
    ("מִנְחָה", "minchah"),
    ("עַרְבִית", "arvit"),
    ("מוּסָף", "musaf"),
)


@dataclass
class Unit:
    """One entry in the table of contents, with what the sources say about it."""

    title: str                      # wiki page title, without the root prefix
    display: str                    # vocalised title as the ToC prints it
    group: str
    subgroup: str | None
    occasion: str
    service: str | None
    exists: bool = False
    size: int = 0
    defines: int = 0
    transcludes: int = 0
    printed_pages: list[int] = field(default_factory=list)
    nusach: int = 0
    instructions: int = 0
    foundation_pages: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)

    @property
    def slug(self) -> str:
        return transliterate(self.display)

    @property
    def urn(self) -> str:
        path = [self.occasion]
        if self.service:
            path.append(self.service)
        path.append(self.slug)
        return "urn:x-opensiddur:text:siddur:" + "/".join(p for p in path if p)

    @property
    def page_range(self) -> str:
        """The printed pages, as runs.

        Min-to-max would be a lie for a unit whose pages are not contiguous: Birkat
        HaMazon carries pages in three separate places in the book, and "171-769" reads
        as six hundred pages of it.
        """
        if not self.printed_pages:
            return "—"
        runs: list[list[int]] = [[self.printed_pages[0], self.printed_pages[0]]]
        for page in self.printed_pages[1:]:
            if page - runs[-1][1] <= 2:      # Hebrew pages fall on every other leaf
                runs[-1][1] = page
            else:
                runs.append([page, page])
        rendered = ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs)
        return rendered if len(rendered) <= 40 else f"{rendered[:37]}…"

    @property
    def in_scope(self) -> bool:
        return self.exists and not ({"NOT-IN-1949", "STUB", "MACHZOR"} & self.flags)


def parse_toc(wikitext: str) -> list[Unit]:
    """Read the table of contents into an ordered list of units.

    The ToC is a run of `==group==` headings, each followed by bullets. A bullet either
    names a service in bold and then lists its units, or is a single bolded unit that is
    its own service.
    """
    units: list[Unit] = []
    positions = [(m.start(), m.group(1)) for m in HEADING_RE.finditer(wikitext)]

    for index, (start, group) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(wikitext)
        occasion = next((o for key, o in OCCASION_BY_GROUP if key in group), "hosafot")
        machzor = any(key in group for key in MACHZOR_GROUPS)

        # Every line, not only bulleted ones: four of the seven groups list their units
        # on plain lines, and the additions number theirs in bold instead.
        for line in wikitext[start:end].split("\n"):
            if not LINK_RE.search(line):
                continue
            body = line.lstrip("*").strip()
            lead = BOLD_LEAD_RE.match(body)
            subgroup = lead.group(1) if lead and not LINK_RE.search(lead.group(1)) else None
            service = next(
                (s for key, s in SERVICE_KEYWORDS if key in (subgroup or body)), None
            )
            for title, display in LINK_RE.findall(body):
                # The additions link out to other projects in the user namespace; those
                # are references, not units of this book.
                if not title.startswith(f"{ROOT_TITLE}/"):
                    continue
                unit = Unit(
                    title=title.replace(f"{ROOT_TITLE}/", ""),
                    display=re.sub(r"\s+", " ", display).strip(),
                    group=group,
                    subgroup=subgroup,
                    occasion=occasion,
                    service=service,
                )
                if machzor:
                    unit.flags.add("MACHZOR")
                units.append(unit)
    return units


def _dedupe(units: list[Unit]) -> list[Unit]:
    """Keep the first appearance of a unit, recording that it recurs.

    A handful of units are listed under more than one service -- eruvin appears before
    Shabbat and again before Rosh Hashanah -- and each is one file, not several.
    """
    seen: dict[str, Unit] = {}
    ordered: list[Unit] = []
    for unit in units:
        if unit.title in seen:
            seen[unit.title].flags.add("LISTED-TWICE")
            continue
        seen[unit.title] = unit
        ordered.append(unit)
    return ordered


def _units_missing_from_toc(structure: dict[str, Any], listed: set[str]) -> list[Unit]:
    """Unit pages that exist but the table of contents never links to.

    The ToC gives order and grouping; it does not give completeness. Four pages are
    absent from it, one of them Birkat HaMazon, which is unmistakably in the book. Taking
    the ToC as the whole inventory would drop them silently, so the two sources are
    unioned and the difference is flagged for hand placement.
    """
    prefix = f"{ROOT_TITLE}/{RITE}/"
    found = []
    for title, entry in structure.items():
        if not title.startswith(prefix) or title.count("/") != 2:
            continue
        name = title.split("/")[-1]
        if name in ("דפי יסוד", "עמודים") or entry.get("redirect_target"):
            continue
        if f"{RITE}/{name}" in listed:
            continue
        unit = Unit(
            title=f"{RITE}/{name}",
            display=name,
            group="(not in the table of contents)",
            subgroup=None,
            occasion="hosafot",
            service=None,
        )
        unit.flags.add("NOT-IN-TOC")
        found.append(unit)
    return sorted(found, key=lambda u: u.title)


def gather(sourcetexts_root: Path | None = None) -> list[Unit]:
    """Read the ToC and annotate every unit from the sources."""
    source_dir = birnbaum_siddur_source_text_directory(sourcetexts_root)
    toc_path = source_dir / TOC_PAGE
    if not toc_path.is_file():
        raise FileNotFoundError(f"No table of contents at {toc_path}")

    units = _dedupe(parse_toc(toc_path.read_text(encoding="utf-8")))

    structure_path = birnbaum_siddur_data_directory(sourcetexts_root) / "structure.json"
    structure = json.loads(structure_path.read_text(encoding="utf-8"))["pages"]

    units += _units_missing_from_toc(structure, {u.title for u in units})

    correspondence = json.loads(
        birnbaum_siddur_correspondence_path(sourcetexts_root).read_text(encoding="utf-8")
    )
    hebrew_pages = {
        int(p["printed_page"]): p
        for p in correspondence["pages"]
        if p["side"] == "he" and (p["printed_page"] or "").isdigit()
    }

    for unit in units:
        entry = structure.get(f"{ROOT_TITLE}/{unit.title}")
        path = source_dir / f"{unit.title}.txt"
        if entry is None or not path.is_file():
            unit.flags.add("STUB")
            continue

        unit.exists = True
        wikitext = path.read_text(encoding="utf-8")
        unit.size = len(wikitext.encode("utf-8"))
        unit.defines = len(entry.get("defines") or [])
        unit.transcludes = len(entry.get("transcludes") or [])
        unit.nusach = len(NUSACH_RE.findall(wikitext))
        unit.instructions = len(INSTRUCTION_RE.findall(wikitext))
        unit.foundation_pages = {
            t["title"].split("/")[-1]
            for t in (entry.get("transcludes") or [])
            if "דפי יסוד" in t.get("title", "")
        }
        unit.printed_pages = sorted({int(n) for n in PAGE_LABEL_RE.findall(wikitext)})

        if WIP_RE.search(wikitext):
            unit.flags.add("WIP")
        if not unit.printed_pages:
            # The single test for whether the 1949 book contains this at all.
            unit.flags.add("NOT-IN-1949")
        elif not any(p in hebrew_pages for p in unit.printed_pages):
            unit.flags.add("FOREIGN-PAGINATION")

    # A printed page carried by more than one unit is worth seeing: it means two files
    # will emit the same tei:pb.
    owners: dict[int, list[Unit]] = {}
    for unit in units:
        for page in unit.printed_pages:
            owners.setdefault(page, []).append(unit)
    shared_counts: dict[str, int] = {}
    for sharing in owners.values():
        if len(sharing) > 1:
            for unit in sharing:
                shared_counts[unit.title] = shared_counts.get(unit.title, 0) + 1
    for unit in units:
        # One shared page is a boundary touch: a unit ends on the page the next begins
        # on, which is how the book reads. Two or more means the units genuinely overlap
        # and the same tei:pb will be emitted twice from inside both.
        if shared_counts.get(unit.title, 0) > 1:
            unit.flags.add("OVERLAPPING-PAGES")

    return units


def _table(units: list[Unit]) -> Iterator[str]:
    yield ("| Group | Service | Title | Proposed `siddur:` URN | Pages | Size | Trans | "
           "Rubrics | Foundation | Flags |")
    yield "|---|---|---|---|---:|---:|---:|---:|---|---|"
    group = None
    for unit in units:
        shown = "" if unit.group == group else unit.group
        group = unit.group
        yield (
            f"| {shown} | {unit.service or ''} | {unit.display} | "
            f"`{unit.urn.split(':')[-1]}` | {unit.page_range} | "
            f"{unit.size or ''} | {unit.transcludes or ''} | "
            f"{unit.instructions or ''} | {' '.join(sorted(unit.foundation_pages))} | "
            f"{' '.join(sorted(unit.flags))} |"
        )


def report_units(units: list[Unit]) -> str:
    """The review document."""
    in_scope = [u for u in units if u.in_scope]
    excluded = [u for u in units if not u.in_scope]
    flagged = [u for u in in_scope if uncertain(u.display)]

    lines = [
        "# Birnbaum siddur — the unit list",
        "",
        "Generated by `birnbaum_siddur.sections --report-units`. **Regenerate rather than",
        "editing.** This is the review gate for file granularity: each row below is a",
        "candidate for its own JLPTEI file.",
        "",
        "The list comes from the book's own table of contents, which already groups its",
        "units the way the book does, so the order and the grouping are the source's",
        "rather than an editorial invention.",
        "",
        f"**{len(in_scope)} units in scope**, {len(excluded)} excluded.",
        "",
        "## What the columns mean",
        "",
        "- **Pages** — printed pages of the 1949 edition the unit carries.",
        "- **Trans** — how many labelled sections it transcludes; roughly how much",
        "  assembly it does.",
        "- **Rubrics** — instruction templates, which go to the Wikisource project.",
        "- **Foundation** — which shared text stores it draws on.",
        "",
        "There is no variant column: `{{נוסח}}` sites live in the foundation pages, not in",
        "the units, so they belong to the second review gate rather than this one.",
        "`OVERLAPPING-PAGES` marks a unit sharing two or more printed pages with another,",
        "which means the same `tei:pb` is emitted from two files. Sharing a single page is",
        "not flagged: that is just one unit ending where the next begins.",
        "",
        "Proposed URNs are **provisional**: the slug is mechanically transliterated and a",
        "settled English spelling should win over it. Names whose sheva reading had to be",
        "guessed are listed under *Names needing a second look*.",
        "",
        "## Units in scope",
        "",
    ]
    lines += list(_table(in_scope))
    lines += [
        "",
        "## Excluded",
        "",
        "Not omissions — each is out of scope for a stated reason, recorded here so the",
        "gaps are visible rather than silent.",
        "",
        "| Title | Group | Why |",
        "|---|---|---|",
    ]
    for unit in excluded:
        if "MACHZOR" in unit.flags:
            why = "machzor: a separate book"
        elif "STUB" in unit.flags:
            why = "advertised by the table of contents but never written"
        elif "NOT-IN-1949" in unit.flags:
            why = "no printed page in the 1949 edition"
        elif "FOREIGN-PAGINATION" in unit.flags:
            why = "paginated against a different book"
        else:
            why = " ".join(sorted(unit.flags)) or "—"
        lines.append(f"| {unit.display} | {unit.group} | {why} |")

    if flagged:
        lines += [
            "",
            "## Names needing a second look",
            "",
            "The transliterator could not tell whether a sheva was vocal, so these slugs",
            "are a guess. Everything else followed a rule.",
            "",
            "| Title | Proposed slug |",
            "|---|---|",
        ]
        lines += [f"| {u.display} | `{u.slug}` |" for u in flagged]

    return "\n".join(lines) + "\n"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report the Birnbaum siddur's units for review before conversion."
    )
    parser.add_argument(
        "--sourcetexts-root", type=Path, default=default_sourcetexts_root(),
        help="Root of the sourcetexts repository.",
    )
    parser.add_argument("--report-units", action="store_true",
                        help="Write specs/BIRNBAUM_UNITS.md.")
    parser.add_argument("--output", type=Path, default=Path("specs/BIRNBAUM_UNITS.md"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        units = gather(args.sourcetexts_root)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    in_scope = [u for u in units if u.in_scope]
    logger.info("%d unit(s) in the table of contents, %d in scope", len(units), len(in_scope))

    if args.report_units:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_units(units), encoding="utf-8")
        logger.info("Wrote %s", args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
