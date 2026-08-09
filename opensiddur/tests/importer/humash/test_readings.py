"""Tests for reading the triennial cycle out of the hebcal data.

These use a synthetic triennial.json rather than the downloaded one, so that they keep their
meaning when hebcal updates its data. The fixture keeps hebcal's shape: a parshah that always
divides the same way holds "years", one that is sometimes read combined with its partner holds
"variations" keyed by variation and cycle year, and the pair itself holds both the combined
division and the table saying which variation each cycle pattern selects.
"""

import json
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.humash.readings import triennial, triennial_patterns


def _aliyot(chapter: int) -> dict[str, list[str]]:
    """A whole year's aliyot inside one chapter, so the fixture stays short."""
    return {
        str(index): [f"{chapter}:{index}", f"{chapter}:{index}"] for index in range(1, 8)
    } | {"M": [f"{chapter}:7", f"{chapter}:7"]}


TRIENNIAL_FIXTURE = {
    "Bereshit": {"book": 1, "years": {f"Y.{year}": _aliyot(year) for year in (1, 2, 3)}},
    "Tazria": {
        "book": 3,
        "variations": {
            "A.3": _aliyot(11),
            "B.2": _aliyot(12),
            # An alias: variation C's third year divides exactly as A's does.
            "C.3": "A.3",
        },
    },
    "Metzora": {"book": 3, "variations": {"A.3": _aliyot(21)}},
    "Tazria-Metzora": {
        "book": 3,
        "years": {f"Y.{year}": _aliyot(year) for year in (1, 2, 3)},
        "patterns": {"TTS": "A", "TST": "B", "STT": "C"},
    },
    # Hyphenated, but one parshah rather than a pair, so it has no patterns to read.
    "Lech-Lecha": {"book": 1, "years": {"Y.1": _aliyot(4)}},
}


class TestTriennial(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        directory = self.root / "hebcal_leyning"
        directory.mkdir(parents=True)
        (directory / "triennial.json").write_text(
            json.dumps(TRIENNIAL_FIXTURE), encoding="utf-8"
        )
        # triennial() caches by file name and root, so each test gets a fresh directory.
        self.divisions = triennial(self.root)

    def test_a_parshah_with_no_variation_is_keyed_by_cycle_year_alone(self):
        self.assertEqual(
            sorted(self.divisions["bereshit"]), [(None, 1), (None, 2), (None, 3)]
        )
        spans = self.divisions["bereshit"][(None, 2)]
        self.assertEqual([span.unit for span in spans][:1], ["aliyah.triennial.2"])
        self.assertEqual(spans[-1].unit, "maftir.triennial.2")

    def test_a_variation_is_keyed_by_variation_and_year(self):
        """The twelve that are sometimes doubled were skipped entirely before."""
        self.assertEqual(
            sorted(self.divisions["tazria"]), [("A", 3), ("B", 2), ("C", 3)]
        )

    def test_an_aliased_variation_resolves_to_the_division_it_names(self):
        aliased = self.divisions["tazria"][("C", 3)]
        named = self.divisions["tazria"][("A", 3)]
        self.assertEqual(
            [(str(span.start), str(span.end)) for span in aliased],
            [(str(span.start), str(span.end)) for span in named],
        )

    def test_a_variation_names_its_parshah_in_its_unit_space(self):
        """Both parshiyot of a pair share a file, and their variations may cover one verse."""
        tazria = self.divisions["tazria"][("A", 3)][0]
        metzora = self.divisions["metzora"][("A", 3)][0]
        self.assertEqual(tazria.unit, "aliyah.triennial.tazria.A.3")
        self.assertEqual(metzora.unit, "aliyah.triennial.metzora.A.3")
        self.assertEqual(tazria.owner, "tazria")

    def test_the_combined_reading_is_keyed_by_the_pairs_slug(self):
        pair = self.divisions["tazria_metzora"]
        self.assertEqual(
            sorted(pair), [("combined", 1), ("combined", 2), ("combined", 3)]
        )
        span = pair[("combined", 1)][0]
        self.assertEqual(span.unit, "aliyah.triennial.combined.1")
        # The combined reading owns the file it is emitted in, so it names no owner.
        self.assertIsNone(span.owner)


class TestTriennialPatterns(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        directory = self.root / "hebcal_leyning"
        directory.mkdir(parents=True)
        (directory / "triennial.json").write_text(
            json.dumps(TRIENNIAL_FIXTURE), encoding="utf-8"
        )
        self.patterns = triennial_patterns(self.root)

    def test_patterns_are_read_from_the_pair(self):
        self.assertEqual(
            self.patterns["tazria_metzora"], {"TTS": "A", "TST": "B", "STT": "C"}
        )

    def test_a_hyphenated_single_parshah_is_not_taken_for_a_pair(self):
        self.assertNotIn("lech_lecha", self.patterns)
