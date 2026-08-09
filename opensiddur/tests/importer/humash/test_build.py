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
from opensiddur.importer.humash.refs import (
    UNIT_ALIYAH,
    UNIT_ALIYAH_COMBINED,
    ReadingSpan,
    VerseRef,
    triennial_unit,
)

TEI = "{http://www.tei-c.org/ns/1.0}"
J = "{http://jewishliturgy.org/ns/jlptei/2}"

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
