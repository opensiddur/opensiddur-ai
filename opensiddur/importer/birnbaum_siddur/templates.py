"""Inventory the wikitext vocabulary of the Birnbaum siddur before converting any of it.

A converter for MediaWiki source is only as complete as its list of templates, and the
way that list is normally discovered is by conversion failing. This module discovers it
first: every template, every tag, and every shape of labelled-section name, with counts
and examples, so the handlers can be written against a known vocabulary and the
intermediate-to-TEI stylesheet can safely refuse to match anything unexpected.

Three things are counted, because the Birnbaum source encodes meaning in all three:

* **Templates** — the presentation and apparatus vocabulary. Their *argument shapes*
  matter as much as their names: ``{{נוסח}}`` means opposite things depending on whether
  a parameter is named or empty-named, and reading it the wrong way round silently
  inverts a textual variant.
* **Tags** — dominated by ``<קטע>``, the Hebrew labelled-section transclusion that holds
  the entire text store together.
* **Section-name roles** — the names given to labelled sections are not arbitrary. They
  follow a grammar (`… הוראה`, `כותרת ל…`, `… מקור`, `… 1`) that says what *kind* of
  thing the section is, and that grammar is what decides which TEI element it becomes.

Run as::

    uv run python -m opensiddur.importer.birnbaum_siddur.templates --report
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import mwparserfromhell

from opensiddur.importer.util.pages import (
    birnbaum_siddur_external_text_directory,
    birnbaum_siddur_source_text_directory,
    default_sourcetexts_root,
    relative_path_to_title,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The Hebrew localisation of <section begin=…/> and <section end=…/>. Written with an
# XML-ish syntax that mwparserfromhell does not recognise as a tag, so it is matched
# directly rather than parsed.
SECTION_START_RE = re.compile(r"<קטע התחלה=([^/>]*)\s*/>")
SECTION_END_RE = re.compile(r"<קטע סוף=([^/>]*)\s*/>")

# Any tag-like construct, so the inventory notices markup nobody has thought about yet.
TAG_RE = re.compile(r"<\s*(/?)([^\s/>=!]+)")

# The labelled-section name grammar. Order matters: the longest, most specific prefixes
# must be tried first, or `כותרת` would swallow `כותרת ל…`.
ROLE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction", re.compile(r"(^|\s)הורא(ה|ות)(\s|$)")),
    ("note", re.compile(r"(^|\s)הערה(\s|$)")),
    ("heading", re.compile(r"(^|\s)כותרת(\s|ל|$)")),
    ("words", re.compile(r"(^|\s)מילים(\s|$)")),
    ("whole", re.compile(r"(^|\s)הכל(\s|$)")),
    ("source", re.compile(r"(^|\s)מקור(\s|$)")),
    ("continuation", re.compile(r"(^|\s)המשך(\s|$)")),
    ("verse", re.compile(r"(^|\s)פסוק(\s|$)")),
    ("closing", re.compile(r"(^|\s)חתימה(\s|$)")),
    ("page", re.compile(r"^עמוד\s+\d+$")),
    ("chunk", re.compile(r"\s\d+$")),
)

# Attributions in {{נוסח}}, including the four misspellings of Birnbaum's name that
# appear in the source. Matching them loosely is deliberate: a typo must not silently
# reclassify a variant.
BIRNBAUM_RE = re.compile(r"ב[ירנובם]{5,8}")

MAX_EXAMPLES = 3


@dataclass
class Use:
    """How one template, tag or role is used across the corpus."""

    name: str
    count: int = 0
    pages: set[str] = field(default_factory=set)
    shapes: Counter = field(default_factory=Counter)
    examples: list[str] = field(default_factory=list)

    def record(self, page: str, shape: str | None = None, example: str | None = None) -> None:
        self.count += 1
        self.pages.add(page)
        if shape is not None:
            self.shapes[shape] += 1
        if example is not None and len(self.examples) < MAX_EXAMPLES:
            self.examples.append(example)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "pages": len(self.pages),
            "shapes": dict(self.shapes.most_common(8)),
            "examples": self.examples,
        }


@dataclass
class Inventory:
    """Everything one pass over the source pages found."""

    templates: dict[str, Use] = field(default_factory=dict)
    tags: dict[str, Use] = field(default_factory=dict)
    roles: dict[str, Use] = field(default_factory=dict)
    nusach: Counter = field(default_factory=Counter)
    section_names: Counter = field(default_factory=Counter)
    pages_read: int = 0
    unnormalised: list[str] = field(default_factory=list)

    def _bucket(self, table: dict[str, Use], name: str) -> Use:
        return table.setdefault(name, Use(name=name))

    def as_dict(self) -> dict[str, Any]:
        return {
            "pages_read": self.pages_read,
            "distinct_templates": len(self.templates),
            "distinct_tags": len(self.tags),
            "section_names": sum(self.section_names.values()),
            "distinct_section_names": len(self.section_names),
            "nusach": dict(self.nusach),
            "unnormalised_pages": self.unnormalised,
            "templates": [u.as_dict() for u in _by_count(self.templates)],
            "tags": [u.as_dict() for u in _by_count(self.tags)],
            "roles": [u.as_dict() for u in _by_count(self.roles)],
        }


def _by_count(table: dict[str, Use]) -> list[Use]:
    return sorted(table.values(), key=lambda u: (-u.count, u.name))


def iter_source_pages(sourcetexts_root: Path | None = None) -> Iterator[tuple[str, str]]:
    """Yield ``(wiki title, wikitext)`` for every mainspace page of the siddur.

    Covers the siddur's own subtree and the pages it references from outside it. The
    ``עמוד:`` scan pages are deliberately excluded: they are a second assembly of the
    same material, and counting them would double every template.
    """
    for directory in (
        birnbaum_siddur_source_text_directory(sourcetexts_root),
        birnbaum_siddur_external_text_directory(sourcetexts_root),
    ):
        if not directory.is_dir():
            logger.warning("No such directory: %s", directory)
            continue
        for path in sorted(directory.rglob("*.txt")):
            title = relative_path_to_title(path.relative_to(directory))
            yield title, path.read_text(encoding="utf-8")


def classify_section_name(name: str) -> list[str]:
    """Which roles a labelled-section name carries.

    A name may carry more than one — ``זכרנו לחיים הוראה`` is an instruction *belonging
    to* a named prayer — so this returns every match rather than the first. A name with
    no role marker is the prayer text itself and returns ``["plain"]``.
    """
    roles = [role for role, pattern in ROLE_PATTERNS if pattern.search(name)]
    # A page label is "עמוד 81", which also ends in a digit and so matches the chunk
    # pattern. It is a pagination marker, not a division of a prayer, and counting it
    # as both would overstate the chunks by the number of pages in the book.
    if "page" in roles and "chunk" in roles:
        roles.remove("chunk")
    return roles or ["plain"]


def classify_nusach(template: mwparserfromhell.nodes.Template) -> str:
    """Which of the five shapes of ``{{נוסח}}`` this is.

    The template is a variant apparatus, and its direction depends on where the
    attribution sits:

    ``{{נוסח|reading|=בירנבוים}}``      the running text is Birnbaum's -> ``attributed``
    ``{{נוסח|reading|בירנבוים=other}}`` Birnbaum reads *other* -> ``swap``
    ``{{נוסח|reading|other=alt}}``      someone else reads alt -> ``other``
    ``{{נוסח|reading|alt}}``            an unattributed alternative -> ``unlabelled``

    Reading a ``swap`` as an ``attributed`` would leave the wrong reading in the text,
    which is the failure this whole classification exists to prevent.
    """
    named = [p for p in template.params if not str(p.name).strip().isdigit()]
    running_is_birnbaum = any(
        BIRNBAUM_RE.search(str(p.value).strip())
        for p in named
        if not str(p.name).strip()
    )
    alternative_is_birnbaum = any(
        BIRNBAUM_RE.search(str(p.name).strip()) for p in named if str(p.name).strip()
    )
    labelled = any(str(p.name).strip() for p in named)

    if running_is_birnbaum and alternative_is_birnbaum:
        return "ambiguous"
    if alternative_is_birnbaum:
        return "swap"
    if running_is_birnbaum:
        return "attributed"
    if labelled:
        return "other"
    return "unlabelled"


def _template_shape(template: mwparserfromhell.nodes.Template) -> str:
    """A compact signature of a template's parameters, e.g. ``1|2|בירנבוים``."""
    return "|".join(str(p.name).strip() or "«empty»" for p in template.params) or "«none»"


def inventory(sourcetexts_root: Path | None = None) -> Inventory:
    """Read every source page and count what is in it."""
    found = Inventory()

    for title, wikitext in iter_source_pages(sourcetexts_root):
        found.pages_read += 1

        # The schema requires NFKD. Flag pages that are not already normalised, since
        # comparing a Birnbaum reading against a wiki one depends on it.
        if unicodedata.normalize("NFKD", wikitext) != wikitext:
            found.unnormalised.append(title)

        for template in mwparserfromhell.parse(wikitext).filter_templates():
            name = str(template.name).strip()
            # Labelled-section transclusions are parser functions whose "name" embeds
            # the target page. Collapse them so the inventory shows one entry, not 34.
            if name.startswith("#קטע:"):
                use = found._bucket(found.templates, "#קטע: (labelled section)")
                use.record(title, shape=name.split(":", 1)[1])
                continue
            use = found._bucket(found.templates, name)
            use.record(title, shape=_template_shape(template), example=str(template)[:160])
            if name == "נוסח":
                found.nusach[classify_nusach(template)] += 1

        for closing, tag in TAG_RE.findall(wikitext):
            if closing:
                continue
            found._bucket(found.tags, tag).record(title)

        for match in SECTION_START_RE.finditer(wikitext):
            name = match.group(1).strip()
            found.section_names[name] += 1
            for role in classify_section_name(name):
                found._bucket(found.roles, role).record(title, example=name)

    return found


def report(found: Inventory) -> Iterator[str]:
    """A human-readable summary, ordered by how much work each item implies."""
    yield f"Read {found.pages_read} source pages."
    yield ""
    yield f"Templates: {len(found.templates)} distinct, {sum(u.count for u in found.templates.values())} uses"
    for use in _by_count(found.templates):
        yield f"  {use.count:6d}  {use.name}"
    yield ""
    yield f"Tags: {len(found.tags)} distinct"
    for use in _by_count(found.tags):
        yield f"  {use.count:6d}  {use.name}"
    yield ""
    yield (
        f"Labelled sections: {sum(found.section_names.values())} uses, "
        f"{len(found.section_names)} distinct names"
    )
    for use in _by_count(found.roles):
        yield f"  {use.count:6d}  {use.name}"
    yield ""
    yield "{{נוסח}} by shape:"
    for shape, count in found.nusach.most_common():
        yield f"  {count:6d}  {shape}"
    if found.unnormalised:
        yield ""
        yield f"NOT NFKD-normalised: {len(found.unnormalised)} page(s)"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory every template, tag and labelled-section role in the Birnbaum "
            "siddur's Hebrew Wikisource source, so the converter can be written "
            "against a known vocabulary."
        )
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=default_sourcetexts_root(),
        help="Root of the sourcetexts repository (default: <repo>/sourcetexts/sources).",
    )
    parser.add_argument("--report", action="store_true", help="Print the summary.")
    parser.add_argument(
        "--json", type=Path, default=None, help="Also write the full inventory here."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    found = inventory(args.sourcetexts_root)

    if args.report or args.json is None:
        for line in report(found):
            print(line)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(found.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Wrote %s", args.json)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
