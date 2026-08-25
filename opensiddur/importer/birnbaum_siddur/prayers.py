"""What the shared text stores contain, and what each prayer should be called.

The 16 foundation pages hold nearly all the book's text as some three thousand labelled
sections, which the unit pages assemble in printed order. Those sections are the
addressing granularity of the whole project: a section is what a `prayer:` URN will name
and what a translation will align to.

They are not, however, one section per prayer. A single prayer is spread over several
sections that differ in *role* rather than in content -- its heading, its rubric, the
words themselves, a note about them, a page-turn chunk -- and the section names say which
is which. Grouping by the name with those role markers stripped recovers the prayer.

This reports the groups for review (see ``specs/BIRNBAUM_PRAYERS.md``) rather than
settling them. What needs human eyes is small: the groups that carry a heading, since a
heading is the name a reader would recognise, and the scriptural citations.

Run as::

    uv run python -m opensiddur.importer.birnbaum_siddur.prayers --report
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from opensiddur.importer.birnbaum_siddur.templates import classify_section_name
from opensiddur.importer.birnbaum_siddur.translit import transliterate, uncertain
from opensiddur.importer.util.hebrew import normalize_hebrew
from opensiddur.importer.util.pages import (
    birnbaum_siddur_source_text_directory,
    default_sourcetexts_root,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

FOUNDATION_DIR = "אשכנז/דפי יסוד"

SPAN_START_RE = re.compile(r"<קטע התחלה=([^/>]*)\s*/>")
SPAN_END_RE = re.compile(r"<קטע סוף=([^/>]*)\s*/>")
# Page labels, of this book and of the machzor it cross-references. Both are pagination
# rather than divisions of a prayer, and both cross prayer boundaries freely.
PAGE_SPAN_RE = re.compile(r"^(?:מחזור\s+)?עמוד\s+\d+(?:\s+\S.*)?$")

# Role markers, longest first so "כותרת ל…" is not eaten by "כותרת". Stripping these
# from a section name leaves the prayer the section belongs to.
ROLE_PREFIXES = ("כותרת ל", "כותרת", "הוראות ל", "הוראה לפני", "הוראה ל", "הוראות",
                 "הוראה", "הערה על", "הערה", "המשך", "מקור ל", "מקור")
ROLE_SUFFIXES = ("מילים", "הכל", "מקור", "הוראה", "הוראות", "הערה", "כותרת",
                 "חתימה", "פסוק")

# A trailing Arabic number is the edition's own division -- verified earlier: 62% of
# consecutive pairs have a page turn between them -- so it is not part of the name.
#
# A trailing Hebrew letter is *not* stripped, though 155 sections carry one, because the
# source uses it both ways: "פרק א" and "פרק ב" are different chapters, while other
# pairs are two halves of one blessing. Stripping it fused six chapters into a single
# group called "chapter". Under-grouping is the safe error here -- a reviewer can merge
# two rows, but cannot recover a row that silently swallowed six.
ORDINAL_SUFFIX_RE = re.compile(r"\s+\d+$")

#: Gershayim, geresh and ASCII quotes, which the source wraps a quoted incipit in.
QUOTE_MARKS = "\u05f4\u05f3\"'"

#: Hebrew points. A name without any is unvocalised, and transliterating it yields
#: consonants rather than a pronounceable word.
NIQQUD_RE = re.compile(r"[\u0591-\u05c7]")

#: How many words of a text to take as its incipit. Enough to identify a prayer, which
#: is all a name has to do.
INCIPIT_WORDS = 3

# Wiki markup to drop when reading a heading's text.
MARKUP_RE = re.compile(r"\{\{[^{}]*\}\}|\[\[[^\]]*\]\]|<[^>]+>|'''|''")

# A scriptural citation, as the source writes it: [[<book> <chapter>/טעמים|<display>]].
CITATION_RE = re.compile(r"\[\[([^\]|]+?)/טעמים(?:#[^\]|]*)?\|([^\]]+)\]\]")

# Hebrew numerals are written with or without gershayim, and a chapter may be given as
# "כ״ב" in one half of a citation and "כב" in the other. Neither is a disagreement.
GERSHAYIM_RE = re.compile(r"[\u05f3\u05f4'\"]")
HEBREW_NUMERAL_RE = re.compile(r"^[אבגדהוזחטיכלמנסעפצקרשת]+$")

#: Book names the source abbreviates. Only what is needed to compare a citation against
#: its own link; the full mapping belongs to whatever resolves them to bible: URNs.
BOOK_ABBREVIATIONS = {
    'דה"א': "דברי הימים א",
    'דה"ב': "דברי הימים ב",
    'שמו"א': "שמואל א",
    'שמו"ב': "שמואל ב",
}


def _book_and_chapter(text: str) -> tuple[str, str | None]:
    """The book and chapter numeral a citation states, normalised for comparison."""
    text = text.replace("־", " ").replace(",", " ").strip()
    for abbreviation, full in BOOK_ABBREVIATIONS.items():
        text = text.replace(abbreviation, full)
    book: list[str] = []
    for token in text.split():
        bare = GERSHAYIM_RE.sub("", token)
        if bare and HEBREW_NUMERAL_RE.match(bare) and book:
            return " ".join(book), bare
        book.append(token)
    return " ".join(book), None


def citation_disagrees(target: str, display: str) -> bool:
    """Whether a citation's link contradicts its visible text.

    **The visible text is the claim; the link is a cross-check.** The display carries
    book, chapter and verses, which is what a `bible:` URN needs, while the link carries
    only book and chapter. Where they differ it is the link that has gone wrong: in the
    one case in this source, a citation's link was copied from the line above and its
    chapter never updated, so deriving the URN from the link would have put the
    Decalogue paragraph of Kiddush in the wrong chapter of Exodus.

    Most differences between the two are formatting, not disagreement: the display
    usually omits the book, spells a numeral with gershayim, or gives verses the link
    cannot carry. A parsha link addresses a reading rather than a chapter and cannot be
    compared at all.
    """
    if target.strip().startswith("פרשת"):
        return False
    target_book, target_chapter = _book_and_chapter(target)
    display_book, display_chapter = _book_and_chapter(display)
    if display_chapter is None:
        return False                       # the display makes no chapter claim
    if display_book and display_book != target_book:
        return True
    return display_chapter != target_chapter


@dataclass
class Span:
    """One labelled section, with where it sits in the page."""

    name: str
    start: int
    end: int
    depth: int
    parent: str | None = None
    #: True when the source never closed this section and its end was guessed.
    end_inferred: bool = False


@dataclass
class Prayer:
    """The sections of one page that name the same thing."""

    page: str
    base: str
    spans: list[Span] = field(default_factory=list)
    roles: set[str] = field(default_factory=set)
    heading: str | None = None
    incipit: str | None = None
    citations: list[str] = field(default_factory=list)
    parent: str | None = None

    @property
    def display(self) -> str:
        """The name a reader would know it by.

        Section *labels* in this source are unvocalised -- 1,559 of 1,756 carry no
        points at all -- while the text inside them is fully pointed. Transliterating a
        label therefore produces consonants rather than a word: "ברכת ציצית" comes out
        "vrkht_tzytzyt". So a heading is preferred, then the opening words of the text,
        which is what the URN scheme means by naming a prayer by its incipit, and the
        label is a last resort that gets flagged rather than trusted.
        """
        return self.heading or self.incipit or self.base

    @property
    def vocalised(self) -> bool:
        """Whether the name it would be given is pointed, and so transliterable."""
        return bool(NIQQUD_RE.search(self.display))

    @property
    def slug(self) -> str:
        return transliterate(self.display)

    @property
    def needs_review(self) -> bool:
        """Whether a person has to look at this one.

        A heading is a name somebody chose, so it deserves confirming. A citation has to
        be checked against the verse it claims. Everything else derives mechanically.
        """
        return (
            bool(self.heading)
            or bool(self.citations)
            or not self.vocalised
            or uncertain(self.display)
        )

    @property
    def size(self) -> int:
        return sum(s.end - s.start for s in self.spans if s.end > s.start)


def strip_roles(name: str) -> str:
    """The prayer a section name belongs to, with its role marker removed."""
    # The source quotes an incipit it names a section after.
    stripped = ORDINAL_SUFFIX_RE.sub("", name.strip()).strip(QUOTE_MARKS)
    changed = True
    while changed:
        changed = False
        for prefix in ROLE_PREFIXES:
            # A prefix ending in a prepositional letter runs straight into the name
            # ("כותרת לפרק"), so it must not require a following space -- requiring one
            # left "לפרק" as the name.
            attached = prefix.endswith(("ל", "ב"))
            if stripped == prefix or stripped.startswith(prefix + ("" if attached else " ")):
                stripped = stripped[len(prefix):].strip()
                changed = True
                break
        for suffix in ROLE_SUFFIXES:
            if stripped.endswith(" " + suffix):
                stripped = stripped[: -len(suffix)].strip()
                changed = True
                break
        stripped = ORDINAL_SUFFIX_RE.sub("", stripped).strip(QUOTE_MARKS)
    return stripped or name.strip()


def load_boundary_fixes(path: Path | None = None) -> dict[tuple[str, str], str]:
    """Hand corrections to section ends, keyed by (foundation page, section)."""
    path = path or BOUNDARY_FIXES
    if not path.is_file():
        return {}
    fixes: dict[tuple[str, str], str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            fixes[(record["page"], record["section"])] = record["ends_after"]
        except (ValueError, KeyError) as exc:
            logger.warning("%s:%d: ignoring unreadable correction (%s)", path, number, exc)
    return fixes


def _apply_fix(wikitext: str, span: Span, ends_after: str) -> bool:
    """Close ``span`` just after ``ends_after``. Returns whether the words were found.

    Matched on the consonant skeleton, so a correction written from the printed page
    still lands when the source spells the same words with different pointing.
    """
    from opensiddur.importer.util.hebrew import normalize_with_offsets

    body = wikitext[span.start:]
    normalised, offsets = normalize_with_offsets(body)
    target = normalize_hebrew(ends_after)
    if not target:
        return False
    at = normalised.find(target)
    if at < 0 or at + len(target) > len(offsets):
        return False
    span.end = span.start + offsets[at + len(target) - 1] + 1
    span.end_inferred = False
    return True


def parse_spans(
    wikitext: str, fixes: dict[str, str] | None = None
) -> tuple[list[Span], list[str]]:
    """Read a page's labelled sections into a nesting, tolerantly.

    The sections are *almost* a tree: about one in sixty either overlaps a sibling or is
    never closed, and one stub page opens the same section eleven times. Page spans cross
    prayer boundaries by nature, since a page turn falls where it falls, so they are
    excluded here and handled as their own layer. Rather than fail on the rest, this
    recovers and reports what it could not nest, so a malformed source is visible instead
    of silently reshaping the hierarchy.
    """
    events = sorted(
        [(m.start(), m.end(), "s", m.group(1).strip()) for m in SPAN_START_RE.finditer(wikitext)]
        + [(m.start(), m.end(), "e", m.group(1).strip()) for m in SPAN_END_RE.finditer(wikitext)]
    )
    spans: dict[str, Span] = {}
    order: list[Span] = []
    stack: list[Span] = []
    problems: list[str] = []

    for start, finish, kind, name in events:
        if PAGE_SPAN_RE.match(name):
            continue
        if kind == "s":
            span = Span(name=name, start=finish, end=-1, depth=len(stack),
                        parent=stack[-1].name if stack else None)
            if name in spans:
                problems.append(f"{name}: opened again before it closed")
            spans[name] = span
            order.append(span)
            stack.append(span)
            continue
        if stack and stack[-1].name == name:
            stack.pop().end = start
        elif any(s.name == name for s in stack):
            # Overlapping rather than nested: close it where it says, and let whatever
            # it was interleaved with go on.
            span = next(s for s in stack if s.name == name)
            span.end = start
            stack.remove(span)
            problems.append(f"{name}: overlaps a sibling instead of nesting")
        else:
            problems.append(f"{name}: closed without being opened")

    # An unclosed span used to run to the end of the file, which is wildly wrong: one
    # unclosed note swallowed 78,590 characters of its page where the next section began
    # 290 characters later. Bound it at the next section instead and record that the end
    # was inferred. It is still a guess -- a genuinely nested parent would extend past
    # its children -- so the problem text says how much room the guess leaves.
    starts = sorted(
        m.end() for m in SPAN_START_RE.finditer(wikitext)
        if not PAGE_SPAN_RE.match(m.group(1).strip())
    )
    for span in stack:
        corrected = (fixes or {}).get(span.name)
        if corrected and _apply_fix(wikitext, span, corrected):
            continue
        if corrected:
            problems.append(f"{span.name}: correction text not found in the source")
        following = next((pos for pos in starts if pos > span.start), None)
        span.end = following if following is not None else len(wikitext)
        span.end_inferred = True
        problems.append(
            f"{span.name}: never closed; ended at the next section "
            f"({span.end - span.start} chars in, of {len(wikitext) - span.start} "
            "to the end of the page)"
        )
    return order, problems


def _plain_text(wikitext: str, span: Span) -> str:
    """A section's text with wiki markup removed."""
    return re.sub(r"\s+", " ", MARKUP_RE.sub("", wikitext[span.start : span.end])).strip()


def incipit_of(text: str) -> str | None:
    """The opening words of a pointed text, as a name for it.

    Returns None for text with no points: an unpointed incipit is no better as a name
    than the unpointed label it would replace.
    """
    words = [w for w in text.split() if NIQQUD_RE.search(w)]
    return " ".join(words[:INCIPIT_WORDS]) if words else None


def gather(sourcetexts_root: Path | None = None) -> tuple[list[Prayer], dict[str, list[str]]]:
    """Group every foundation page's sections into prayers."""
    directory = birnbaum_siddur_source_text_directory(sourcetexts_root) / FOUNDATION_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"No foundation pages at {directory}")

    all_fixes = load_boundary_fixes()
    prayers: list[Prayer] = []
    problems: dict[str, list[str]] = {}

    for path in sorted(directory.glob("*.txt")):
        page = path.stem
        wikitext = path.read_text(encoding="utf-8")
        spans, page_problems = parse_spans(
            wikitext, {s: e for (pg, s), e in all_fixes.items() if pg == page})
        if page_problems:
            problems[page] = page_problems

        grouped: dict[str, Prayer] = {}
        for span in spans:
            base = strip_roles(span.name)
            prayer = grouped.setdefault(base, Prayer(page=page, base=base))
            prayer.spans.append(span)
            prayer.roles.update(classify_section_name(span.name))
            if "heading" in classify_section_name(span.name) and not prayer.heading:
                text = _plain_text(wikitext, span)
                if text:
                    prayer.heading = text
            if prayer.incipit is None and "words" not in classify_section_name(span.name):
                prayer.incipit = incipit_of(_plain_text(wikitext, span))
            body = wikitext[span.start : span.end]
            for target, shown in CITATION_RE.findall(body):
                # The display is the citation; the link only corroborates it.
                note = (" **link contradicts it — use the text**"
                        if citation_disagrees(target, shown) else "")
                prayer.citations.append(f"{shown.strip()}{note}")

        # A prayer's parent is the prayer containing its outermost section.
        for prayer in grouped.values():
            outermost = min(prayer.spans, key=lambda s: s.depth)
            if outermost.parent:
                candidate = strip_roles(outermost.parent)
                if candidate != prayer.base:
                    prayer.parent = candidate
        prayers += list(grouped.values())

    return prayers, problems


def report(prayers: list[Prayer], problems: dict[str, list[str]]) -> str:
    review = [p for p in prayers if p.needs_review]
    headed = [p for p in prayers if p.heading]
    cited = [p for p in prayers if p.citations]

    lines = [
        "# Birnbaum siddur — the prayer names",
        "",
        "Generated by `birnbaum_siddur.prayers --report`. **Regenerate rather than",
        "editing.** This is the second review gate: what each shared text is called, and",
        "so what a `prayer:` URN will name.",
        "",
        f"The {len(prayers)} groups below come from grouping the foundation pages'",
        "labelled sections by name with their role markers stripped, since a prayer is",
        "spread over several sections that differ in role -- heading, rubric, the words,",
        "a note -- rather than in content.",
        "",
        f"**{len(review)} need a person to look at them.** The rest derive mechanically",
        "and are listed at the end for spot-checking.",
        "",
        "A name comes from the group's heading where it has one, otherwise from the",
        "opening words of its text -- which is what the URN scheme means by naming a",
        "prayer by its incipit. It does **not** come from the section label: 1,559 of the",
        "labels carry no pointing, and transliterating one yields consonants rather than",
        "a word.",
        "",
        "## Named by a heading in the source",
        "",
        f"{len(headed)} groups carry a heading section. **Many of these headings are not",
        "in the 1949 printing.** Like the rubrics, they are the Wikisource editors' own,",
        "so they belong to `he_wikisource_siddur_hashalem` and must not be emitted as a",
        "`tei:head` in the Birnbaum project, where they would assert that Birnbaum printed",
        "them.",
        "",
        "They are still the best source for a *name*, which is a different thing: a URN",
        "slug is something the corpus chooses, not a claim about the page. So the heading",
        "seeds the slug and is what needs confirming here, but which of these headings the",
        "print actually carries is a separate question, answerable against the English",
        "edition rather than this source.",
        "",
        "| Page | Heading | Proposed slug | Parts | Roles |",
        "|---|---|---|---:|---|",
    ]
    for prayer in sorted(headed, key=lambda p: (p.page, p.base)):
        lines.append(
            f"| {prayer.page} | {prayer.heading} | `{prayer.slug}` | "
            f"{len(prayer.spans)} | {' '.join(sorted(prayer.roles))} |"
        )

    lines += [
        "",
        "## Scriptural citations",
        "",
        f"{len(cited)} groups cite scripture, and each needs its `bible:` URN checked.",
        "",
        "The **visible text is the citation**; the wiki link beside it only corroborates.",
        "The text carries book, chapter and verses, which is what a URN needs, while the",
        "link carries book and chapter alone. Exactly one citation's link contradicts its",
        "text -- copied from the line above and never updated -- and is marked below.",
        "Formatting differences between the two, which are common, are not.",
        "",
        "| Page | Prayer | Cites |",
        "|---|---|---|",
    ]
    for prayer in sorted(cited, key=lambda p: (p.page, p.base)):
        lines.append(f"| {prayer.page} | {prayer.display} | {'; '.join(prayer.citations[:3])} |")

    if problems:
        total = sum(len(v) for v in problems.values())
        lines += [
            "",
            "## Malformed sections in the source",
            "",
            f"{total} sections across {len(problems)} pages either overlap a sibling or",
            "are never closed. Each is recovered rather than fatal, but the boundary is a",
            "guess, and these are worth fixing upstream on Wikisource.",
            "",
            "An unclosed section ends at the next section rather than at the end of the",
            "page. Both figures are given below, so the size of the guess is visible.",
            "Closing at the next *heading* would often be the truer answer, but the next",
            "heading is frequently thousands of characters away and in a third of these",
            "cases there is none at all, so the printed pagination or a person is what",
            "would settle it.",
            "",
            "| Page | Problem |",
            "|---|---|",
        ]
        for page, found in sorted(problems.items()):
            for problem in sorted(set(found)):
                lines.append(f"| {page} | {problem} |")

    unvocalised = [p for p in prayers if not p.vocalised]
    if unvocalised:
        rubrics = sum(1 for p in unvocalised if "instruction" in p.roles)
        lines += [
            "",
            "## Names that could not be derived",
            "",
            f"{len(unvocalised)} groups whose label and text both lack pointing, so",
            "there is nothing to transliterate into a pronounceable name and the slug",
            "below is consonants only.",
            "",
            f"{rubrics} of them are instruction sections, which belong to",
            "`he_wikisource_siddur_hashalem` and need no `prayer:` URN at all, so the",
            "real shortfall is smaller than the count suggests.",
            "",
            "| Page | Label | Consonant slug | Roles |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {u.page} | {u.base} | `{u.slug}` | {' '.join(sorted(u.roles))} |"
            for u in sorted(unvocalised, key=lambda u: (u.page, u.base))
        ]

    mechanical = [p for p in prayers if not p.needs_review]
    lines += [
        "",
        "## Derived mechanically",
        "",
        f"{len(mechanical)} groups with no heading and no citation. Their names come",
        "straight from the section name, and they are listed for spot-checking rather",
        "than review.",
        "",
        "| Page | Prayer | Proposed slug | Parts |",
        "|---|---|---|---:|",
    ]
    for prayer in sorted(mechanical, key=lambda p: (p.page, p.base)):
        lines.append(f"| {prayer.page} | {prayer.base} | `{prayer.slug}` | {len(prayer.spans)} |")

    return "\n".join(lines) + "\n"


#: Where hand corrections to section boundaries live. One JSON object per line:
#:
#:     {"page": "תפילת העמידה", "section": "ברכת אבות", "ends_after": "<a few words>"}
#:
#: `ends_after` is the last words the section should contain. The parser closes the
#: section immediately after them, so a correction survives the source being edited
#: around it -- the same reason the haggadah's page breaks are anchored to words rather
#: than to offsets.
BOUNDARY_FIXES = Path("specs/birnbaum_section_boundaries.jsonl")

ANCHOR_WORDS = 6


def _anchor(text: str, at: int, *, before: bool) -> str:
    """A few words of ``text`` on one side of ``at``, to locate a spot by eye."""
    window = text[max(0, at - 400): at] if before else text[at: at + 400]
    plain = re.sub(r"\s+", " ", MARKUP_RE.sub("", window)).strip()
    words = plain.split()
    chosen = words[-ANCHOR_WORDS:] if before else words[:ANCHOR_WORDS]
    return " ".join(chosen)


#: A labelled-section transclusion: {{#קטע:PAGE|SECTION}}.
TRANSCLUSION_RE = re.compile(r"\{\{#קטע:([^|}]+)\|([^}]+)\}\}")


def section_pages(sourcetexts_root: Path | None = None) -> dict[str, set[str]]:
    """Printed pages for each foundation section, via the units that transclude it.

    A foundation page carries almost no pagination of its own -- 506 of the 521 page
    spans are in the unit pages, because a page number belongs to where a text is
    *printed*, and a shared text is printed wherever a service uses it. So the page of a
    section is the page of the transclusion that pulls it in, and a section used by two
    services legitimately has two.

    Only units in the 1949 book are consulted, so a section reachable only from the
    unfinished machzor pages comes back with no page, which is the correct answer:
    it is not in this book.
    """
    from opensiddur.importer.birnbaum_siddur.sections import RITE, gather as gather_units

    in_scope = {u.title.split("/")[-1] for u in gather_units(sourcetexts_root) if u.in_scope}
    unit_dir = birnbaum_siddur_source_text_directory(sourcetexts_root) / RITE

    pages: dict[str, set[str]] = {}
    for path in sorted(unit_dir.glob("*.txt")):
        if path.stem not in in_scope:
            continue
        wikitext = path.read_text(encoding="utf-8")
        # Walk the file, tracking the page span in force, and attribute every
        # transclusion inside it to that page.
        boundaries = [
            (m.start(), re.search(r"\d+", m.group(1)).group(0))
            for m in SPAN_START_RE.finditer(wikitext)
            if PAGE_SPAN_RE.match(m.group(1).strip()) and re.search(r"\d+", m.group(1))
        ]
        for call in TRANSCLUSION_RE.finditer(wikitext):
            page = next(
                (number for offset, number in reversed(boundaries) if offset < call.start()),
                None,
            )
            if page:
                pages.setdefault(call.group(2).strip(), set()).add(page)
    return pages


def report_boundaries(sourcetexts_root: Path | None = None) -> str:
    """Every section whose end had to be guessed, with the page and words to check.

    A boundary cannot be settled from the wikitext -- that is what makes it a guess --
    so this gives the printed page it starts on and the words on either side of the
    guessed end, which is what a person needs to look it up and say where it really ends.
    """
    directory = birnbaum_siddur_source_text_directory(sourcetexts_root) / FOUNDATION_DIR
    pages = section_pages(sourcetexts_root)
    all_fixes = load_boundary_fixes()
    rows, out_of_scope = [], []
    for path in sorted(directory.glob("*.txt")):
        wikitext = path.read_text(encoding="utf-8")
        spans, _ = parse_spans(
            wikitext, {s: e for (pg, s), e in all_fixes.items() if pg == path.stem})
        for span in spans:
            if not span.end_inferred:
                continue
            # A wrapper section is often not transcluded itself -- a unit pulls in its
            # numbered parts instead -- so fall back to the pages of any section naming
            # the same prayer.
            group = strip_roles(span.name)
            printed = sorted(
                pages.get(span.name)
                or {page for other in spans if strip_roles(other.name) == group
                    for page in pages.get(other.name, ())},
                key=int,
            )
            if not printed:
                # No unit of the 1949 book pulls this in, so it is not in the book.
                out_of_scope.append((path.stem, span.name))
                continue
            rows.append({
                "page": path.stem,
                "section": span.name,
                "starts_on": ", ".join(printed),
                "opens": _anchor(wikitext, span.start, before=False),
                "ends_after": _anchor(wikitext, span.end, before=True),
                "then": _anchor(wikitext, span.end, before=False),
                "to_page_end": len(wikitext) - span.start,
                "to_guess": span.end - span.start,
            })

    lines = [
        "# Birnbaum siddur — section boundaries that need checking",
        "",
        "Generated by `birnbaum_siddur.prayers --report-boundaries`.",
        "",
        f"{len(rows)} sections are never closed in the Wikisource source. Each is bounded",
        "at the next section, which is a guess: the wikitext does not say where it ends.",
        "",
        f"A further {len(out_of_scope)} unclosed sections are reachable only from pages",
        "the 1949 edition does not contain -- the unfinished machzor, mostly -- and are",
        "out of scope, so they are not listed.",
        "",
        "## How to correct one",
        "",
        f"Add a line to `{BOUNDARY_FIXES}`:",
        "",
        "```json",
        '{"page": "תפילת העמידה", "section": "ברכת אבות", "ends_after": "the last few words"}',
        "```",
        "",
        "`ends_after` is the last words the section should contain; the parser closes it",
        "immediately after them. It is anchored to words rather than to a character",
        "offset so that a correction survives the source being edited around it. If the",
        "guess below is already right, no line is needed.",
        "",
        "Better still, fix it upstream on Wikisource by adding the missing closing tag,",
        "and this file can then be deleted a line at a time.",
        "",
        "## The sections",
        "",
    ]
    for row in rows:
        lines += [
            f"### {row['section']}",
            "",
            f"- **Foundation page** `{row['page']}`",
            f"- **Printed page** {row['starts_on']}",
            f"- **Opens**: {row['opens']}",
            f"- **Guessed end** {row['to_guess']} characters in, "
            f"of {row['to_page_end']} to the end of the source page",
            f"- **…ends after**: {row['ends_after']}",
            f"- **…then comes**: {row['then']}",
            "",
        ]
    return "\n".join(lines) + "\n"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report the Birnbaum siddur's shared prayers for review."
    )
    parser.add_argument("--sourcetexts-root", type=Path, default=default_sourcetexts_root())
    parser.add_argument("--report", action="store_true", help="Write the review document.")
    parser.add_argument("--report-boundaries", action="store_true",
                        help="Write the list of section ends that had to be guessed.")
    parser.add_argument("--boundaries-output", type=Path,
                        default=Path("specs/BIRNBAUM_SECTION_BOUNDARIES.md"))
    parser.add_argument("--output", type=Path, default=Path("specs/BIRNBAUM_PRAYERS.md"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        prayers, problems = gather(args.sourcetexts_root)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    logger.info(
        "%d prayer group(s); %d need review; %d malformed section(s)",
        len(prayers),
        sum(1 for p in prayers if p.needs_review),
        sum(len(v) for v in problems.values()),
    )
    if args.report:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report(prayers, problems), encoding="utf-8")
        logger.info("Wrote %s", args.output)
    if args.report_boundaries:
        args.boundaries_output.parent.mkdir(parents=True, exist_ok=True)
        args.boundaries_output.write_text(
            report_boundaries(args.sourcetexts_root), encoding="utf-8")
        logger.info("Wrote %s", args.boundaries_output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
