"""Tests for turning overlapping reading divisions into a linear sequence.

These use synthetic spans rather than the real reading data, so they keep their meaning when
the sources are updated.
"""

import json
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.humash import model
from opensiddur.importer.humash.refs import (
    UNIT_ALIYAH,
    UNIT_MAFTIR,
    UNIT_WEEKDAY,
    ReadingSpan,
    VerseRef,
)


def _verse_counts(root: Path) -> None:
    directory = root / "hebcal_leyning"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "numverses.json").write_text(
        json.dumps({name: [0] + [31] * 40 for name in
                    ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")}),
        encoding="utf-8",
    )


def _span(unit: str, label: str, start: tuple[int, int], end: tuple[int, int]) -> ReadingSpan:
    return ReadingSpan(
        unit=unit, label=label,
        start=VerseRef("genesis", *start), end=VerseRef("genesis", *end),
    )


class TestSegmentation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        _verse_counts(self.root)

    def _ranges(self, segments) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        return [
            ((s.start.chapter, s.start.verse), (s.end.chapter, s.end.verse)) for s in segments
        ]

    def test_the_text_is_cut_at_every_boundary_and_emitted_once(self):
        spans = [
            _span(UNIT_ALIYAH, "1", (1, 1), (1, 10)),
            _span(UNIT_ALIYAH, "2", (1, 11), (1, 20)),
            _span(UNIT_WEEKDAY, "1", (1, 1), (1, 5)),
        ]
        segments = model.segment_reading(
            spans, VerseRef("genesis", 1, 1), VerseRef("genesis", 1, 20), self.root
        )
        # The weekday boundary at 1:5 cuts aliyah 1 in two; no verse is emitted twice.
        self.assertEqual(
            self._ranges(segments), [((1, 1), (1, 5)), ((1, 6), (1, 10)), ((1, 11), (1, 20))]
        )
        self.assertFalse(any(segment.duplicate for segment in segments))

    def test_a_maftir_inside_the_last_aliyah_splits_it_without_repeating_it(self):
        spans = [
            _span(UNIT_ALIYAH, "7", (1, 1), (1, 10)),
            _span(UNIT_MAFTIR, "maftir", (1, 8), (1, 10)),
        ]
        segments = model.segment_reading(
            spans, VerseRef("genesis", 1, 1), VerseRef("genesis", 1, 10), self.root
        )
        self.assertEqual(self._ranges(segments), [((1, 1), (1, 7)), ((1, 8), (1, 10))])
        # The maftir milestone opens the second segment; the aliyah still covers both.
        self.assertEqual([s.unit for s in segments[0].opening], [UNIT_ALIYAH])
        self.assertEqual([s.unit for s in segments[1].opening], [UNIT_MAFTIR])

    def test_segments_close_before_the_next_one_opens(self):
        """A span ending short of the next start must not swallow the gap between them."""
        spans = [
            _span(UNIT_WEEKDAY, "1", (1, 1), (1, 3)),
            _span(UNIT_ALIYAH, "1", (1, 1), (1, 10)),
        ]
        segments = model.segment_reading(
            spans, VerseRef("genesis", 1, 1), VerseRef("genesis", 1, 10), self.root
        )
        self.assertEqual(self._ranges(segments), [((1, 1), (1, 3)), ((1, 4), (1, 10))])

    def test_overlap_inside_one_unit_repeats_the_shared_verses(self):
        """Weekday Rosh Hodesh: kohen ends at 28:3 and levi begins there, so it is read twice."""
        spans = [
            _span(UNIT_WEEKDAY, "1", (28, 1), (28, 3)),
            _span(UNIT_WEEKDAY, "2", (28, 3), (28, 5)),
        ]
        segments = model.segment_reading(spans, sourcetexts_root=self.root)
        self.assertEqual(self._ranges(segments), [((28, 1), (28, 3)), ((28, 3), (28, 5))])
        self.assertFalse(segments[0].duplicate)
        self.assertTrue(segments[1].duplicate)

    def test_overlap_between_units_does_not_repeat_anything(self):
        """Only same-unit overlap means the text is read twice."""
        spans = [
            _span(UNIT_ALIYAH, "7", (1, 1), (1, 10)),
            _span(UNIT_MAFTIR, "maftir", (1, 8), (1, 10)),
        ]
        self.assertFalse(model.has_internal_overlap(spans))
        self.assertEqual(model.overlapping_units(spans), [])

    def test_duplication_can_be_refused_for_a_continuous_reading(self):
        """A parshah is emitted once even if one scheme overlaps itself somewhere in it."""
        spans = [
            _span(UNIT_ALIYAH, "1", (1, 1), (1, 10)),
            _span(UNIT_ALIYAH, "2", (1, 8), (1, 20)),
        ]
        self.assertTrue(model.has_internal_overlap(spans))
        segments = model.segment_reading(
            spans, VerseRef("genesis", 1, 1), VerseRef("genesis", 1, 20), self.root,
            allow_duplication=False,
        )
        self.assertFalse(any(segment.duplicate for segment in segments))
        emitted = sum(
            (s.end.verse - s.start.verse + 1) for s in segments
        )
        self.assertEqual(emitted, 20)

    def test_overlapping_units_names_the_scheme_at_fault(self):
        spans = [
            _span(UNIT_ALIYAH, "1", (1, 1), (1, 10)),
            _span(UNIT_ALIYAH, "2", (1, 8), (1, 20)),
            _span(UNIT_WEEKDAY, "1", (1, 1), (1, 5)),
        ]
        self.assertEqual(model.overlapping_units(spans), [UNIT_ALIYAH])

    def test_a_boundary_crossing_a_chapter_end_steps_into_the_next_chapter(self):
        spans = [
            _span(UNIT_ALIYAH, "1", (1, 1), (1, 31)),
            _span(UNIT_ALIYAH, "2", (2, 1), (2, 5)),
        ]
        segments = model.segment_reading(
            spans, VerseRef("genesis", 1, 1), VerseRef("genesis", 2, 5), self.root
        )
        self.assertEqual(self._ranges(segments), [((1, 1), (1, 31)), ((2, 1), (2, 5))])

    def test_no_spans_yields_no_segments(self):
        self.assertEqual(model.segment_reading([], sourcetexts_root=self.root), [])


if __name__ == "__main__":
    unittest.main()
