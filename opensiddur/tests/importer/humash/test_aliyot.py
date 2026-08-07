"""Tests for the MAM aliyah parse.

The conversion logic is tested against synthetic TSV rows rather than the real torah.tsv, so
that the tests do not change meaning when the source data is updated.
"""

import json
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.humash import aliyot
from opensiddur.importer.humash.names import slug_for_hebrew
from opensiddur.importer.humash.refs import (
    UNIT_ALIYAH,
    UNIT_MAFTIR,
    UNIT_WEEKDAY,
    ReadingSpan,
    VerseRef,
    verses_in_chapter,
)

HEBREW_NUMERALS = {
    1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
    11: "יא", 12: "יב", 13: "יג", 14: "יד", 19: "יט", 20: "כ", 22: "כב", 25: "כה", 26: "כו",
    31: "לא", 32: "לב",
}


def _row(book: str, chapter: int, verse: int, **params: str) -> str:
    """One torah.tsv scaffolding cell carrying an aliyah marker."""
    body = "|".join(f"{key}={value}" for key, value in params.items())
    return (
        f"{{{{מ:פסוק|{book}|{HEBREW_NUMERALS[chapter]}|{HEBREW_NUMERALS[verse]}"
        f"|עלייה={{{{מ:עלייה|{body}}}}}}}}}"
    )


def _write_verse_counts(root: Path) -> None:
    """A synthetic numverses.json, so the tests do not depend on the downloaded data.

    Index 0 is a placeholder because hebcal numbers chapters from 1. Only the chapters the
    tests reach need to be right.
    """
    genesis = [0] + [31, 25, 24, 26, 32, 22, 24, 22, 29, 32] + [30] * 40
    directory = root / "hebcal_leyning"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "numverses.json").write_text(
        json.dumps({
            "Genesis": genesis,
            "Exodus": [0] + [22] * 40,
            "Leviticus": [0] + [17] * 27,
            "Numbers": [0] + [23] * 36,
            "Deuteronomy": [0] + [22] * 34,
        }),
        encoding="utf-8",
    )


class TestParseParshiyot(unittest.TestCase):
    """Parse a synthetic torah.tsv holding two short parshiyot of Genesis."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        sheets = self.root / "miqra_al_pi_hamasorah" / "sheets"
        sheets.mkdir(parents=True)
        self.tsv = sheets / "torah.tsv"
        _write_verse_counts(self.root)

    def _write(self, scaffolds: list[str]) -> None:
        lines = ["\t".join(["page", "id", "", scaffold, "text"]) for scaffold in scaffolds]
        self.tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _parse(self):
        return aliyot.parse_parshiyot(self.root)

    def test_shabbat_aliyot_end_where_the_next_one_starts(self):
        self._write([
            _row("בראשית", 1, 1, ב0="בראשית", ב1="ראשון"),
            _row("בראשית", 2, 4, ב0="בראשית", ב1="שני"),
            _row("בראשית", 6, 9, ב0="נֹח", ב1="ראשון"),
        ])
        parshiyot = self._parse()
        self.assertEqual([p.slug for p in parshiyot], ["bereshit", "noach"])
        bereshit = parshiyot[0]
        first, second = bereshit.spans_in(UNIT_ALIYAH)
        self.assertEqual(first.start, VerseRef("genesis", 1, 1))
        self.assertEqual(first.end, VerseRef("genesis", 2, 3))
        self.assertEqual(second.start, VerseRef("genesis", 2, 4))
        # The last aliyah runs to the end of the parshah, which ends before Noach begins.
        self.assertEqual(second.end, VerseRef("genesis", 6, 8))
        self.assertEqual(bereshit.end, VerseRef("genesis", 6, 8))

    def test_a_span_ending_at_a_chapter_boundary_uses_that_chapters_verse_count(self):
        """Closing a span means stepping back a verse, which may cross into the chapter before."""
        self._write([
            _row("בראשית", 1, 1, ב0="בראשית", ב1="ראשון"),
            _row("בראשית", 2, 1, ב0="בראשית", ב1="שני"),
            _row("בראשית", 6, 9, ב0="נֹח", ב1="ראשון"),
        ])
        first = self._parse()[0].spans_in(UNIT_ALIYAH)[0]
        # Genesis 1 has 31 verses in the fixture, so stepping back from 2:1 lands on 1:31.
        self.assertEqual(first.end, VerseRef("genesis", 1, 31))

    def test_maftir_overlaps_the_seventh_aliyah_instead_of_ending_it(self):
        """The maftir re-reads the close of the parshah, so both run to the same last verse."""
        self._write([
            _row("בראשית", 5, 25, ב0="בראשית", ב1="שביעי"),
            _row("בראשית", 6, 5, ב0="בראשית", ב3="מפטיר"),
            _row("בראשית", 6, 9, ב0="נֹח", ב1="ראשון"),
        ])
        bereshit = self._parse()[0]
        seventh = bereshit.spans_in(UNIT_ALIYAH)[0]
        maftir = bereshit.spans_in(UNIT_MAFTIR)[0]
        self.assertEqual(seventh.start, VerseRef("genesis", 5, 25))
        self.assertEqual(seventh.end, VerseRef("genesis", 6, 8))
        self.assertEqual(maftir.start, VerseRef("genesis", 6, 5))
        self.assertEqual(maftir.end, VerseRef("genesis", 6, 8))
        # The maftir begins inside the seventh aliyah and does not shorten it.
        self.assertGreater(maftir.start, seventh.start)
        self.assertEqual(maftir.end, seventh.end)

    def test_weekday_reading_stops_at_the_end_marker(self):
        """ע"כ ישראל closes the weekday reading rather than opening a fourth aliyah."""
        self._write([
            _row("בראשית", 1, 1, ב0="בראשית", ב1="ראשון", ב2="כהן"),
            _row("בראשית", 1, 6, ב0="בראשית", ב2="לוי"),
            _row("בראשית", 1, 9, ב0="בראשית", ב2="ישראל"),
            _row("בראשית", 1, 14, ב0="בראשית", ב2='ע"כ ישראל'),
            _row("בראשית", 6, 9, ב0="נֹח", ב1="ראשון"),
        ])
        weekday = self._parse()[0].spans_in(UNIT_WEEKDAY)
        self.assertEqual([span.label for span in weekday], ["1", "2", "3"])
        self.assertEqual(weekday[0].start, VerseRef("genesis", 1, 1))
        self.assertEqual(weekday[0].end, VerseRef("genesis", 1, 5))
        self.assertEqual(weekday[2].start, VerseRef("genesis", 1, 9))
        # Ends at 1:13, the verse before the marker — not at the end of the parshah.
        self.assertEqual(weekday[2].end, VerseRef("genesis", 1, 13))

    def test_weekday_and_shabbat_aliyot_do_not_truncate_each_other(self):
        """The two schemes are closed independently, so a weekday start stays inside aliyah 1."""
        self._write([
            _row("בראשית", 1, 1, ב0="בראשית", ב1="ראשון", ב2="כהן"),
            _row("בראשית", 1, 6, ב0="בראשית", ב2="לוי"),
            _row("בראשית", 2, 4, ב0="בראשית", ב1="שני"),
            _row("בראשית", 6, 9, ב0="נֹח", ב1="ראשון"),
        ])
        bereshit = self._parse()[0]
        first_aliyah = bereshit.spans_in(UNIT_ALIYAH)[0]
        self.assertEqual(first_aliyah.end, VerseRef("genesis", 2, 3))
        self.assertEqual(bereshit.spans_in(UNIT_WEEKDAY)[0].end, VerseRef("genesis", 1, 5))

    def test_pointing_and_maqaf_survive_the_name_lookup(self):
        """MAM points its names and writes לך־לך with a maqaf; neither may change the slug."""
        self.assertEqual(slug_for_hebrew("נֹח"), "noach")
        self.assertEqual(slug_for_hebrew("נח"), "noach")
        self.assertEqual(slug_for_hebrew("לך־לך"), "lech_lecha")
        self.assertEqual(slug_for_hebrew("בחֻקֹתי"), "bechukotai")

    def test_unknown_parsha_name_is_rejected_rather_than_guessed(self):
        with self.assertRaises(KeyError):
            slug_for_hebrew("פרשה שאינה קיימת")


class TestReadingSpan(unittest.TestCase):
    def test_a_span_may_not_cross_books(self):
        with self.assertRaises(ValueError):
            ReadingSpan(UNIT_ALIYAH, "1", VerseRef("genesis", 50, 1), VerseRef("exodus", 1, 1))

    def test_a_span_may_not_end_before_it_starts(self):
        with self.assertRaises(ValueError):
            ReadingSpan(UNIT_ALIYAH, "1", VerseRef("genesis", 2, 1), VerseRef("genesis", 1, 1))

    def test_range_urn_is_unsuffixed_and_abbreviates_the_end(self):
        start, end = VerseRef("genesis", 1, 1), VerseRef("genesis", 6, 8)
        self.assertEqual(
            start.range_urn(end), "urn:x-opensiddur:text:bible:genesis/1/1-6/8"
        )

    def test_range_urn_refuses_to_cross_books(self):
        with self.assertRaises(ValueError):
            VerseRef("genesis", 50, 26).range_urn(VerseRef("exodus", 1, 1))


class TestNumbering(unittest.TestCase):
    """The four chapters the editions divide differently."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        _write_verse_counts(self.root)

    def test_divergent_chapters_depend_on_the_numbering(self):
        """These four are looked up from a table, so they need no source file at all."""
        self.assertEqual(verses_in_chapter("exodus", 20, self.root, "masorah"), 22)
        self.assertEqual(verses_in_chapter("exodus", 20, self.root, "leningrad"), 26)
        self.assertEqual(verses_in_chapter("exodus", 20, self.root, "common"), 23)

    def test_other_chapters_are_the_same_in_every_numbering(self):
        for numbering in ("masorah", "leningrad", "common"):
            with self.subTest(numbering=numbering):
                self.assertEqual(verses_in_chapter("genesis", 1, self.root, numbering), 31)


if __name__ == "__main__":
    unittest.main()
