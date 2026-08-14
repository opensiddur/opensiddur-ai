"""Tests for emitting a pair of parshiyot that are sometimes read together as one file.

The readings are synthetic, so the tests keep their meaning when MAM or hebcal is updated.
"""

import json
import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.importer.humash import build
from opensiddur.importer.humash.aliyot import CombinedParsha, Parsha
from opensiddur.importer.humash.readings import Passage
from opensiddur.importer.humash.refs import (
    UNIT_ALIYAH,
    UNIT_ALIYAH_COMBINED,
    UNIT_MAFTIR,
    ReadingSpan,
    VerseRef,
    triennial_unit,
)

TEI = "{http://www.tei-c.org/ns/1.0}"
J = "{http://jewishliturgy.org/ns/jlptei/2}"
XML = "{http://www.w3.org/XML/1998/namespace}"

PAIR = "tazria_metzora"
PATTERNS = {"TTS": "A", "TST": "B", "STT": "C"}


def _ref(chapter: int, verse: int) -> VerseRef:
    return VerseRef("leviticus", chapter, verse)


def _span(unit: str, label: str, start, end, owner=None) -> ReadingSpan:
    return ReadingSpan(
        unit=unit, label=label, start=_ref(*start), end=_ref(*end), owner=owner
    )


class TestPairFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        directory = self.root / "hebcal_leyning"
        directory.mkdir(parents=True)
        (directory / "numverses.json").write_text(
            json.dumps({name: [0] + [17] * 30 for name in
                        ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")}),
            encoding="utf-8",
        )

        self.tazria = Parsha(
            slug="tazria", hebrew_name="תזריע", book="leviticus",
            start=_ref(12, 1), end=_ref(13, 17),
            spans=[_span(UNIT_ALIYAH, "1", (12, 1), (13, 17))],
        )
        self.metzora = Parsha(
            slug="metzora", hebrew_name="מצֹרע", book="leviticus",
            start=_ref(14, 1), end=_ref(15, 17),
            spans=[_span(UNIT_ALIYAH, "1", (14, 1), (15, 17))],
        )
        self.pair = CombinedParsha(
            slug=PAIR, hebrew_name="תזריע–מצֹרע", book="leviticus",
            members=("tazria", "metzora"), start=_ref(12, 1), end=_ref(15, 17),
            spans=[
                # Runs from Tazria into Metzora, which is why the pair needs its own file.
                _span(UNIT_ALIYAH_COMBINED, "1", (12, 1), (14, 4)),
                _span(UNIT_ALIYAH_COMBINED, "2", (14, 5), (15, 17)),
            ],
        )
        self.divisions = {
            "tazria": {("A", 3): [_span(
                triennial_unit(3, variation="A", owner="tazria"), "A.3.1",
                (13, 1), (13, 17), owner="tazria",
            )]},
            "metzora": {("A", 3): [_span(
                triennial_unit(3, variation="A", owner="metzora"), "A.3.1",
                (14, 1), (14, 9), owner="metzora",
            )]},
            PAIR: {("combined", 1): [_span(
                triennial_unit(1, variation="combined"), "combined.1.1", (12, 1), (12, 9),
            )]},
        }
        name, document = build.pair_file(
            self.pair, [self.tazria, self.metzora], self.divisions, PATTERNS, self.root
        )
        self.name = name
        self.tree = etree.fromstring(document.encode("utf-8"))
        self.milestones = self.tree.iter(f"{TEI}milestone")

    def _by_unit(self) -> dict[str, list]:
        found: dict[str, list] = {}
        for milestone in self.tree.iter(f"{TEI}milestone"):
            found.setdefault(milestone.get("unit"), []).append(milestone)
        return found

    def test_the_file_is_named_and_addressed_for_the_pair(self):
        self.assertEqual(self.name, f"parashat_{PAIR}")
        div = self.tree.find(f".//{TEI}body/{TEI}div")
        self.assertEqual(
            div.get("corresp"), f"urn:x-opensiddur:text:bible:parsha/{PAIR}"
        )

    def test_each_parshah_keeps_its_own_urn(self):
        by_unit = self._by_unit()
        self.assertEqual(
            [m.get("corresp") for m in by_unit["parsha.annual"]],
            ["urn:x-opensiddur:text:bible:parsha/tazria",
             "urn:x-opensiddur:text:bible:parsha/metzora"],
        )
        self.assertEqual(
            by_unit["parsha.combined"][0].get("corresp"),
            f"urn:x-opensiddur:text:bible:parsha/{PAIR}",
        )
        # Both parshiyot have a first aliyah, so the two must not land on one URN.
        self.assertEqual(
            [m.get("corresp") for m in by_unit["aliyah.annual"]],
            ["urn:x-opensiddur:text:bible:parsha/tazria/aliyah_annual/1",
             "urn:x-opensiddur:text:bible:parsha/metzora/aliyah_annual/1"],
        )

    def test_a_variation_is_conditioned_on_the_patterns_that_select_it(self):
        conditionals = self.tree.findall(f".//{J}conditional")
        self.assertEqual(len(conditionals), 2)  # one per single's variation A
        strings = [
            element.text for element in conditionals[0].iter(f"{TEI}string")
        ]
        self.assertEqual(strings, ["TTS"])
        feature = conditionals[0].find(f".//{TEI}f")
        self.assertEqual(feature.get("name"), "triennial-pattern-tazria-metzora")
        self.assertEqual(
            len(self.tree.findall(f".//{J}endConditional")), len(conditionals)
        )

    def test_the_combined_divisions_are_unconditioned(self):
        """A volume carries the pair both ways, so its combined reading is always present."""
        # Each conditional wraps exactly the marker that follows it.
        conditioned = {
            next(conditional.itersiblings()).get("unit")
            for conditional in self.tree.findall(f".//{J}conditional")
        }
        by_unit = self._by_unit()
        self.assertIn("aliyah.combined", by_unit)
        self.assertIn("aliyah.triennial.combined.1", by_unit)
        self.assertNotIn("aliyah.combined", conditioned)
        self.assertNotIn("aliyah.triennial.combined.1", conditioned)

    def test_each_parshahs_variation_has_a_unit_space_of_its_own(self):
        by_unit = self._by_unit()
        self.assertIn("aliyah.triennial.tazria.A.3", by_unit)
        self.assertIn("aliyah.triennial.metzora.A.3", by_unit)

    def test_the_text_is_transcluded_once_end_to_end(self):
        targets = [
            element.get("target").rsplit(":", 1)[1]
            for element in self.tree.iter(f"{J}transclude")
        ]
        ranges = []
        for target in targets:
            start, _, end = target.partition("-")
            _, chapter, verse = start.split("/")
            end_chapter, end_verse = end.split("/")
            ranges.append(((int(chapter), int(verse)), (int(end_chapter), int(end_verse))))
        self.assertEqual(ranges[0][0], (12, 1))
        self.assertEqual(ranges[-1][1], (15, 17))
        for earlier, later in zip(ranges, ranges[1:]):
            self.assertGreater(later[0], earlier[1], "the text is emitted more than once")


def _passage(book: str, start, end, **kwargs) -> Passage:
    return Passage(
        key="test",
        spans=[ReadingSpan(
            unit="haftarah", label="1",
            start=VerseRef(book, *start), end=VerseRef(book, *end), **kwargs,
        )],
    )


class TestHaftarahFile(unittest.TestCase):
    """The annual haftarah and the triennial ones are alternatives for the same Shabbat."""

    ANNUAL = [_passage("isaiah", (42, 5), (43, 10))]

    def _tree(self, slug: str, triennial_passages=None):
        _, document = build.haftarah_file(slug, self.ANNUAL, triennial_passages)
        return etree.fromstring(document.encode("utf-8"))

    def _features(self, conditional) -> list[str]:
        """The reading-cycle features a conditional tests for, in order."""
        return [
            f.get("name") for f in conditional.iter(f"{TEI}f")
            if f.getparent().get("type") == "opensiddur:reading-cycle"
        ]

    def test_a_parshah_with_no_triennial_haftarah_is_unconditioned(self):
        """Devarim, Vaetchanan and Vezot Haberakhah keep the annual reading in every year."""
        tree = self._tree("devarim")
        self.assertEqual(tree.findall(f".//{J}conditional"), [])

    def test_each_year_becomes_a_headed_division_of_its_own(self):
        tree = self._tree("bereshit", {
            1: _passage("isaiah", (42, 5), (42, 21)),
            2: _passage("isaiah", (40, 25), (40, 31)),
            3: _passage("kings_2", (2, 1), (2, 13)),
        })
        divisions = [
            div for div in tree.iter(f"{TEI}div")
            if (div.get("n") or "").startswith("triennial_")
        ]
        self.assertEqual(
            [div.get("corresp") for div in divisions],
            [f"urn:x-opensiddur:text:bible:haftarah/bereshit/triennial/{year}"
             for year in (1, 2, 3)],
        )
        self.assertEqual(
            [div.find(f"{J}transclude").get("target") for div in divisions],
            ["urn:x-opensiddur:text:bible:isaiah/42/5-42/21",
             "urn:x-opensiddur:text:bible:isaiah/40/25-40/31",
             "urn:x-opensiddur:text:bible:kings_2/2/1-2/13"],
        )

    def test_a_triennial_reading_turns_on_one_decisive_feature(self):
        """Two tests would be undefined where one is false, and undefined keeps the text."""
        tree = self._tree("bereshit", {1: _passage("isaiah", (42, 5), (42, 21))})
        conditional = tree.findall(f".//{J}conditional")[-1]
        self.assertEqual(self._features(conditional), ["triennial-year-1"])
        self.assertEqual(
            [b.get("value") for b in conditional.iter(f"{TEI}binary")], ["true"]
        )

    def test_a_year_is_selected_independently_of_the_others(self):
        """A volume for a whole cycle turns on all three, so they cannot be one year number."""
        tree = self._tree("bereshit", {
            year: _passage("isaiah", (40, year), (40, year)) for year in (1, 2, 3)
        })
        triennial = tree.findall(f".//{J}conditional")[1:]
        self.assertEqual(
            [self._features(c) for c in triennial],
            [["triennial-year-1"], ["triennial-year-2"], ["triennial-year-3"]],
        )

    def test_the_annual_reading_stands_in_for_the_years_that_have_none(self):
        """Tazria is read alone in years 1 and 2 only, so year 3 falls back to the annual."""
        tree = self._tree("tazria", {
            1: _passage("isaiah", (46, 3), (46, 13)),
            2: _passage("jeremiah", (30, 1), (30, 9)),
        })
        annual = tree.findall(f".//{J}conditional")[0]
        self.assertEqual(annual.find(f"{J}any").tag, f"{J}any")
        self.assertEqual(self._features(annual), ["annual", "triennial-year-3"])

    def test_a_parshah_with_every_year_yields_the_annual_only_to_the_annual_feature(self):
        tree = self._tree("bereshit", {
            year: _passage("isaiah", (40, year), (40, year)) for year in (1, 2, 3)
        })
        annual = tree.findall(f".//{J}conditional")[0]
        self.assertEqual(self._features(annual), ["annual"])

    def test_every_conditional_is_closed(self):
        tree = self._tree("bereshit", {
            year: _passage("isaiah", (40, year), (40, year)) for year in (1, 2, 3)
        })
        opened = [c.get(f"{XML}id") for c in tree.findall(f".//{J}conditional")]
        closed = [
            c.get("target").lstrip("#") for c in tree.findall(f".//{J}endConditional")
        ]
        self.assertEqual(len(opened), 4)  # the annual one, and one per year
        self.assertEqual(sorted(opened), sorted(closed))

    def test_a_boundary_inside_a_verse_reads_the_whole_verse_and_says_where_to_stop(self):
        tree = self._tree("emor", {
            3: _passage("nahum", (2, 2), (2, 3), start_half="b", end_half="a"),
        })
        division = tree.findall(f".//{TEI}div[@n='triennial_3']")[0]
        self.assertEqual(
            [child.tag for child in division][1:],
            [f"{TEI}note", f"{J}transclude", f"{TEI}note"],
        )
        self.assertEqual(
            division.find(f"{J}transclude").get("target"),
            "urn:x-opensiddur:text:bible:nahum/2/2-2/3",
        )


class TestBookFile(unittest.TestCase):
    def test_a_pair_is_transcluded_once_by_the_pairs_urn(self):
        parshiyot = [
            Parsha(slug=slug, hebrew_name=slug, book="leviticus", start=_ref(1, 1))
            for slug in ("vayikra", "tazria", "metzora", "emor")
        ]
        _, document = build.book_file("leviticus", parshiyot)
        targets = [
            element.get("target")
            for element in etree.fromstring(document.encode("utf-8")).iter(f"{J}transclude")
        ]
        self.assertEqual(
            [target.rsplit("/", 1)[1] for target in targets],
            ["vayikra", PAIR, "emor"],
        )


class TestMaftirMilestoneTitle(unittest.TestCase):
    """Regression: Sukkot Chol HaMoed's per-day maftir labels ("maftir_day1", etc., after
    readings.festival_readings normalizes them) used to have no entry in ALIYAH_TITLES and
    so fell back to the raw label, which is Latin text with no place inside a Hebrew RTL
    milestone (it prints mirrored, as `readings.py`'s TRIENNIAL_YEARS comment warns).
    """

    def test_ordinary_maftir_is_unchanged(self):
        span = _span(UNIT_MAFTIR, "maftir", (1, 1), (1, 1))
        self.assertEqual(build._milestone_title(span), "מַפְטִיר")

    def test_a_days_maftir_gets_a_hebrew_day_qualified_title(self):
        span = _span(UNIT_MAFTIR, "maftir_day1", (1, 1), (1, 1))
        title = build._milestone_title(span)
        self.assertNotIn("day", title.lower())
        self.assertNotIn("1", title)
        self.assertIn("מַפְטִיר", title)

    def test_each_day_gets_a_distinct_title(self):
        titles = {
            build._milestone_title(_span(UNIT_MAFTIR, f"maftir_day{day}", (1, 1), (1, 1)))
            for day in (1, 2, 3, 4, 5)
        }
        self.assertEqual(len(titles), 5)


class TestHaftarahOrder(unittest.TestCase):
    """Haftarot follow the order the parshiyot are read, not the order of their slugs.

    The parshiyot here are synthetic, so this holds whatever MAM and hebcal say.
    """

    def _parshiyot(self, *slugs):
        return [
            Parsha(slug=slug, hebrew_name=slug, book="leviticus", start=_ref(1, 1))
            for slug in slugs
        ]

    def test_reading_order_is_kept_rather_than_alphabetical(self):
        parshiyot = self._parshiyot("vayikra", "tzav", "shmini", "emor")
        available = {slug: [] for slug in ("emor", "shmini", "tzav", "vayikra")}
        self.assertEqual(
            build.haftarah_order(parshiyot, available),
            ["vayikra", "tzav", "shmini", "emor"],
        )

    def test_a_pair_follows_both_of_its_members(self):
        parshiyot = self._parshiyot("vayikra", "tazria", "metzora", "emor")
        available = {slug: [] for slug in ("vayikra", "tazria", "metzora", PAIR, "emor")}
        self.assertEqual(
            build.haftarah_order(parshiyot, available),
            ["vayikra", "tazria", "metzora", PAIR, "emor"],
        )

    def test_a_parshah_with_no_haftarah_is_skipped(self):
        parshiyot = self._parshiyot("vayikra", "tzav", "shmini")
        self.assertEqual(
            build.haftarah_order(parshiyot, {"vayikra": [], "shmini": []}),
            ["vayikra", "shmini"],
        )

    def test_a_haftarah_belonging_to_no_parshah_is_kept_at_the_end(self):
        parshiyot = self._parshiyot("vayikra", "tzav")
        order = build.haftarah_order(parshiyot, {"tzav": [], "vayikra": [], "unknown": []})
        self.assertEqual(order, ["vayikra", "tzav", "unknown"])


class TestMegillahFile(unittest.TestCase):
    """A megillah is read whole, but must still name the verses it is made of.

    Asking for the book's own URN would take whichever project stands first in priority order
    and claims that book, whether or not that project has the text — and one that carries only
    the title exists. The verse counts here are synthetic.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        directory = self.root / "hebcal_leyning"
        directory.mkdir(parents=True)
        (directory / "numverses.json").write_text(
            json.dumps({"Esther": [0, 22, 23, 15], "Ruth": [0, 22, 23, 18, 22]}),
            encoding="utf-8",
        )

    def _targets(self, book: str, hebrew: str, holiday: str) -> list[str]:
        _, document = build.megillah_file(book, hebrew, holiday, self.root)
        return [
            element.get("target")
            for element in etree.fromstring(document.encode("utf-8")).iter(f"{J}transclude")
        ]

    def test_the_whole_book_is_transcluded_as_a_verse_range(self):
        targets = self._targets("esther", "אֶסְתֵּר", "purim")
        self.assertEqual(targets[0], f"{build.URN_PREFIX}:esther/1/1-3/15")

    def test_the_books_own_urn_is_not_used(self):
        targets = self._targets("esther", "אֶסְתֵּר", "purim")
        self.assertNotIn(f"{build.URN_PREFIX}:esther", targets)

    def test_the_range_ends_on_the_last_verse_of_the_last_chapter(self):
        targets = self._targets("ruth", "רוּת", "shavuot")
        self.assertEqual(targets[0], f"{build.URN_PREFIX}:ruth/1/1-4/22")
