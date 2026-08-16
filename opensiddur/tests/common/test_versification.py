"""Tests for canonical verse numbering.

The expected values are the alignments verified against the raw sources -- MAM's TSV against
the WLC XML, verse by verse -- not against the generated projects, which is where the
mapping came from in the first place.
"""

import unittest

from opensiddur.common.versification import (
    CANONICAL_NUMBERING,
    NUMBERING_COMMON,
    NUMBERING_LENINGRAD,
    NUMBERING_MASORAH,
    ChapterVersification,
    UnknownVerse,
    VerseRef,
    divergent_chapters,
    edition_verse_count,
    from_canonical,
    to_canonical,
)


class TestCanonicalNumberingIsIdentity(unittest.TestCase):
    """The Leningrad numbering *is* the canonical one, so it never needs mapping."""

    def test_to_canonical_is_identity(self):
        self.assertEqual(
            to_canonical(NUMBERING_LENINGRAD, "exodus", 20, 13),
            (VerseRef(20, 13), VerseRef(20, 13)),
        )

    def test_from_canonical_is_identity(self):
        self.assertEqual(from_canonical(CANONICAL_NUMBERING, "exodus", 20, 13), VerseRef(20, 13))

    def test_undivergent_chapter_round_trips(self):
        for numbering in (NUMBERING_MASORAH, NUMBERING_COMMON):
            with self.subTest(numbering=numbering):
                self.assertEqual(
                    to_canonical(numbering, "genesis", 1, 5),
                    (VerseRef(1, 5), VerseRef(1, 5)),
                )
                self.assertEqual(from_canonical(numbering, "genesis", 1, 5), VerseRef(1, 5))


class TestDecalogue(unittest.TestCase):
    """Exodus 20 has 26 canonical verses; MAM reads 22 of them and JPS 23."""

    def test_masorah_merges_anokhi_with_lo_yihyeh(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "exodus", 20, 2),
            (VerseRef(20, 2), VerseRef(20, 3)),
        )

    def test_masorah_merges_the_four_short_commandments(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "exodus", 20, 12),
            (VerseRef(20, 13), VerseRef(20, 16)),
        )

    def test_masorah_tail_of_chapter_is_offset_by_four(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "exodus", 20, 22),
            (VerseRef(20, 26), VerseRef(20, 26)),
        )

    def test_common_splits_anokhi_but_merges_the_four(self):
        self.assertEqual(
            to_canonical(NUMBERING_COMMON, "exodus", 20, 2),
            (VerseRef(20, 2), VerseRef(20, 2)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_COMMON, "exodus", 20, 13),
            (VerseRef(20, 13), VerseRef(20, 16)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_COMMON, "exodus", 20, 23),
            (VerseRef(20, 26), VerseRef(20, 26)),
        )

    def test_every_canonical_verse_maps_back_into_each_edition(self):
        for numbering, expected_count in (
            (NUMBERING_MASORAH, 22),
            (NUMBERING_COMMON, 23),
        ):
            with self.subTest(numbering=numbering):
                mapped = {
                    from_canonical(numbering, "exodus", 20, verse) for verse in range(1, 27)
                }
                self.assertEqual(len(mapped), expected_count)

    def test_all_four_short_commandments_map_to_one_masorah_verse(self):
        for canonical in (13, 14, 15, 16):
            with self.subTest(canonical=canonical):
                self.assertEqual(
                    from_canonical(NUMBERING_MASORAH, "exodus", 20, canonical),
                    VerseRef(20, 12),
                )

    def test_deuteronomy_five_follows_the_same_pattern(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "deuteronomy", 5, 6),
            (VerseRef(5, 6), VerseRef(5, 7)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "deuteronomy", 5, 16),
            (VerseRef(5, 17), VerseRef(5, 20)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "deuteronomy", 5, 29),
            (VerseRef(5, 33), VerseRef(5, 33)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_COMMON, "deuteronomy", 5, 30),
            (VerseRef(5, 33), VerseRef(5, 33)),
        )

    def test_verse_counts(self):
        cases = [
            (NUMBERING_MASORAH, "exodus", 20, 26, 22),
            (NUMBERING_COMMON, "exodus", 20, 26, 23),
            (NUMBERING_MASORAH, "deuteronomy", 5, 33, 29),
            (NUMBERING_COMMON, "deuteronomy", 5, 33, 30),
        ]
        for numbering, book, chapter, canonical, expected in cases:
            with self.subTest(numbering=numbering, book=book):
                self.assertEqual(
                    edition_verse_count(numbering, book, chapter, canonical), expected
                )


class TestChapterBoundaryShift(unittest.TestCase):
    """MAM ends Jeremiah 30 and 1 Samuel 23 one verse later than the Leningrad Codex."""

    def test_absorbed_verse_belongs_to_the_previous_chapter(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "jeremiah", 30, 25),
            (VerseRef(31, 1), VerseRef(31, 1)),
        )
        self.assertEqual(from_canonical(NUMBERING_MASORAH, "jeremiah", 31, 1), VerseRef(30, 25))

    def test_following_chapter_is_renumbered_throughout(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "jeremiah", 31, 1),
            (VerseRef(31, 2), VerseRef(31, 2)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "jeremiah", 31, 39),
            (VerseRef(31, 40), VerseRef(31, 40)),
        )
        self.assertEqual(from_canonical(NUMBERING_MASORAH, "jeremiah", 31, 40), VerseRef(31, 39))

    def test_samuel(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "samuel_1", 23, 29),
            (VerseRef(24, 1), VerseRef(24, 1)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "samuel_1", 24, 22),
            (VerseRef(24, 23), VerseRef(24, 23)),
        )

    def test_chapter_lengths(self):
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "jeremiah", 30, 24), 25)
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "jeremiah", 31, 40), 39)
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "samuel_1", 23, 28), 29)
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "samuel_1", 24, 23), 22)


class TestCrossChapterMerge(unittest.TestCase):
    """MAM reads canonical Numbers 25:19 as the head of its own 26:1."""

    def test_the_merged_verse_spans_two_chapters(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "numbers", 26, 1),
            (VerseRef(25, 19), VerseRef(26, 1)),
        )

    def test_both_halves_map_back_to_the_same_verse(self):
        self.assertEqual(from_canonical(NUMBERING_MASORAH, "numbers", 25, 19), VerseRef(26, 1))
        self.assertEqual(from_canonical(NUMBERING_MASORAH, "numbers", 26, 1), VerseRef(26, 1))

    def test_the_shortened_chapter_stops_early(self):
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "numbers", 25, 19), 18)
        with self.assertRaises(UnknownVerse):
            to_canonical(NUMBERING_MASORAH, "numbers", 25, 19)

    def test_the_rest_of_the_chapter_is_unshifted(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "numbers", 26, 2),
            (VerseRef(26, 2), VerseRef(26, 2)),
        )
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "numbers", 26, 65), 65)


class TestOmittedVerses(unittest.TestCase):
    """Joshua 21:36-37 are absent from MAM entirely."""

    def test_omitted_verses_have_no_edition_counterpart(self):
        for canonical in (36, 37):
            with self.subTest(canonical=canonical):
                with self.assertRaises(UnknownVerse):
                    from_canonical(NUMBERING_MASORAH, "joshua", 21, canonical)

    def test_numbering_resumes_two_short(self):
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "joshua", 21, 35),
            (VerseRef(21, 35), VerseRef(21, 35)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "joshua", 21, 36),
            (VerseRef(21, 38), VerseRef(21, 38)),
        )
        self.assertEqual(
            to_canonical(NUMBERING_MASORAH, "joshua", 21, 43),
            (VerseRef(21, 45), VerseRef(21, 45)),
        )
        self.assertEqual(edition_verse_count(NUMBERING_MASORAH, "joshua", 21, 45), 43)


class TestRoundTrip(unittest.TestCase):
    def test_every_edition_verse_of_every_divergent_chapter_round_trips(self):
        for numbering in (NUMBERING_MASORAH, NUMBERING_COMMON):
            for book, chapter in divergent_chapters(numbering):
                canonical_total = max(
                    to_canonical(numbering, book, chapter, verse)[1].verse
                    for verse in range(1, 200)
                    if _exists(numbering, book, chapter, verse)
                )
                self.assertGreater(canonical_total, 0)
                for verse in range(1, 200):
                    if not _exists(numbering, book, chapter, verse):
                        break
                    first, last = to_canonical(numbering, book, chapter, verse)
                    with self.subTest(numbering=numbering, ref=f"{book} {chapter}:{verse}"):
                        self.assertEqual(
                            from_canonical(numbering, book, first.chapter, first.verse),
                            VerseRef(chapter, verse),
                        )
                        self.assertEqual(
                            from_canonical(numbering, book, last.chapter, last.verse),
                            VerseRef(chapter, verse),
                        )


def _exists(numbering: str, book: str, chapter: int, verse: int) -> bool:
    try:
        to_canonical(numbering, book, chapter, verse)
    except UnknownVerse:
        return False
    return True


class TestChapterVersificationValidation(unittest.TestCase):
    def test_overlapping_merges_are_rejected(self):
        with self.assertRaises(ValueError):
            ChapterVersification(26, merges=((2, 4), (3, 5)))

    def test_reversed_merge_is_rejected(self):
        with self.assertRaises(ValueError):
            ChapterVersification(26, merges=((5, 2),))

    def test_a_verse_cannot_be_merged_and_omitted(self):
        with self.assertRaises(ValueError):
            ChapterVersification(26, merges=((2, 3),), omits=(3,))


if __name__ == "__main__":
    unittest.main()
