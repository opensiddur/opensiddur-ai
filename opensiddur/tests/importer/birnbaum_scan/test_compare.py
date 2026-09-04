"""Tests for classifying the differences between two readings of one page.

Every string here is built by hand, small enough to reason about, and none of it comes
from the sources: the point of the buckets is that a different word never counts as a
different vowel, and that is provable on three words.
"""

import unittest

from opensiddur.importer.birnbaum_scan import compare


BARUKH = "בָּרוּךְ"
ATAH = "אַתָּה"
ADONAI = "יְיָ"


class WordsTestCase(unittest.TestCase):
    def test_splits_on_whitespace_and_maqqef(self):
        self.assertEqual(
            ["שֶׁ", "בְּכָל", "הַלֵּילוֹת"],
            compare.words("שֶׁ־בְּכָל הַלֵּילוֹת"),
        )

    def test_drops_empty_tokens(self):
        self.assertEqual([ATAH], compare.words(f"\n\n  {ATAH}  \n"))


class SeparatorsTestCase(unittest.TestCase):
    def test_a_paragraph_break_is_not_a_line_break_is_not_a_space(self):
        self.assertEqual(
            [" ", "\n", "\n\n", compare.MAQQEF],
            compare.separators("a b\nc\n\nd־e"),
        )

    def test_a_run_of_spaces_is_one_space(self):
        self.assertEqual([" "], compare.separators("a     b"))


class BucketTestCase(unittest.TestCase):
    def test_a_dropped_word_is_consonantal(self):
        result = compare.compare(f"{BARUKH} {ATAH} {ADONAI}", f"{BARUKH} {ADONAI}")
        self.assertEqual(
            [compare.CONSONANTS], [d.bucket for d in result.differences]
        )
        self.assertEqual(ATAH, result.differences[0].ours)
        self.assertEqual("", result.differences[0].theirs)

    def test_a_qamats_read_as_a_patach_is_a_vowel(self):
        result = compare.compare("בָּרוּךְ", "בַּרוּךְ")
        self.assertEqual([compare.VOWELS], [d.bucket for d in result.differences])

    def test_a_maqqef_where_a_space_stood_is_whitespace(self):
        result = compare.compare(f"{BARUKH} {ATAH}", f"{BARUKH}־{ATAH}")
        self.assertEqual(
            [compare.WHITESPACE], [d.bucket for d in result.differences]
        )
        self.assertIn(BARUKH, result.differences[0].note)

    def test_a_different_word_is_never_counted_as_a_different_vowel(self):
        """The whole point of comparing skeletons first."""
        result = compare.compare("מוֹרִיד הַטָּל", "מוֹרִיד הַגֶּשֶׁם")
        self.assertEqual(
            [compare.CONSONANTS], [d.bucket for d in result.differences]
        )

    def test_identical_text_has_no_differences(self):
        text = f"{BARUKH} {ATAH} {ADONAI}"
        self.assertEqual([], compare.compare(text, text).differences)

    def test_pointing_dropped_altogether_is_a_vowel_difference(self):
        result = compare.compare(BARUKH, "ברוך")
        self.assertEqual([compare.VOWELS], [d.bucket for d in result.differences])

    def test_a_paragraph_run_together_is_whitespace(self):
        result = compare.compare(f"{BARUKH}\n\n{ATAH}", f"{BARUKH}\n{ATAH}")
        self.assertEqual(
            [compare.WHITESPACE], [d.bucket for d in result.differences]
        )


class SizeTestCase(unittest.TestCase):
    def test_a_vowel_difference_is_sized_in_marks(self):
        """Two points wrong in one word is worse than one, and counts as two."""
        one = compare.compare("בָּרוּךְ", "בַּרוּךְ").differences[0]
        self.assertEqual(1, one.size)

    def test_a_consonantal_difference_is_sized_in_words(self):
        result = compare.compare(
            f"{BARUKH} {ATAH} {ADONAI}", BARUKH
        )
        self.assertEqual(2, result.differences[0].size)

    def test_word_count_is_recorded_so_a_count_can_be_read_as_a_proportion(self):
        result = compare.compare(f"{BARUKH} {ATAH} {ADONAI}", BARUKH)
        self.assertEqual(3, result.word_count)


class VerdictTestCase(unittest.TestCase):
    def setUp(self):
        self.result = compare.compare(f"{BARUKH} {ATAH}", f"{BARUKH} {ADONAI}")

    def test_a_difference_starts_unresolved(self):
        self.assertEqual(compare.UNRESOLVED, self.result.differences[0].verdict)

    def test_a_verdict_is_recorded_against_a_stable_key(self):
        key = self.result.differences[0].key
        self.assertEqual([], self.result.apply_verdicts({key: compare.PRINT}))
        self.assertEqual(compare.PRINT, self.result.differences[0].verdict)

    def test_a_verdict_matching_nothing_is_returned_not_ignored(self):
        """A reading gets edited; a verdict quietly doing nothing loses the work."""
        self.assertEqual(
            ["consonants:99:x|y"],
            self.result.apply_verdicts({"consonants:99:x|y": compare.PRINT}),
        )

    def test_an_unknown_verdict_is_refused(self):
        with self.assertRaises(ValueError):
            self.result.apply_verdicts({self.result.differences[0].key: "maybe"})

    def test_the_tally_splits_the_buckets_by_verdict(self):
        self.result.apply_verdicts({self.result.differences[0].key: compare.READING})
        table = self.result.tally()
        self.assertEqual(1, table[compare.CONSONANTS]["total"])
        self.assertEqual(1, table[compare.CONSONANTS][compare.READING])
        self.assertEqual(0, table[compare.CONSONANTS][compare.PRINT])
        self.assertEqual(0, table[compare.VOWELS]["total"])


class MixedTestCase(unittest.TestCase):
    def test_the_three_buckets_are_counted_separately_in_one_page(self):
        ours = f"{BARUKH} {ATAH} {ADONAI} אֱלֹהֵֽינוּ"
        theirs = f"בַּרוּךְ {ATAH}־{ADONAI} אֱלֹהֵי"
        result = compare.compare(ours, theirs)
        buckets = sorted(d.bucket for d in result.differences)
        self.assertEqual(
            [compare.CONSONANTS, compare.VOWELS, compare.WHITESPACE], buckets
        )

    def test_format_tally_names_every_bucket(self):
        rendered = compare.format_tally(compare.compare(BARUKH, "ברוך"))
        for bucket in compare.BUCKETS:
            self.assertIn(bucket, rendered)
        self.assertIn("1 words read", rendered)


if __name__ == "__main__":
    unittest.main()
