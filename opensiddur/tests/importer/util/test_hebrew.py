"""Tests for the shared Hebrew normalizers.

Fixtures here are individual characters named by codepoint rather than passages of
text, so what each case asserts is legible without reading Hebrew.
"""

import unittest

from opensiddur.importer.util.hebrew import (
    STORAGE_FORM,
    describe_normalization,
    is_nfkd,
    normalize_hebrew,
    normalize_latin,
    strip_marks,
    to_nfkd,
)

ALEF = "א"
LAMED = "ל"
SHIN = "ש"
BET = "ב"
SHIN_DOT = "ׁ"
DAGESH = "ּ"
QAMATS = "ָ"
QAMATS_QATAN = "ׇ"
HOLAM = "ֹ"
HOLAM_HASER_FOR_VAV = "ֺ"
PATAH = "ַ"

# Presentation-block precomposed forms, which a scraped source mixes with the
# decomposed spellings of the same letters.
SHIN_WITH_SHIN_DOT = "שׁ"
LIGATURE_ALEF_LAMED = "ﭏ"

EM_SPACE = " "


class StorageFormTestCase(unittest.TestCase):
    """`to_nfkd` is what text is written in; it must be loss-free."""

    def test_the_storage_form_is_what_the_schema_asks_for(self):
        self.assertEqual(STORAGE_FORM, "NFKD")

    def test_presentation_forms_decompose(self):
        self.assertEqual(to_nfkd(SHIN_WITH_SHIN_DOT), SHIN + SHIN_DOT)
        self.assertEqual(to_nfkd(LIGATURE_ALEF_LAMED), ALEF + LAMED)

    def test_combining_marks_are_put_in_canonical_order(self):
        # Dagesh and a vowel typed in either order are the same word, and must compare
        # equal once normalized or every reading comparison is unreliable.
        one = BET + DAGESH + QAMATS
        other = BET + QAMATS + DAGESH
        self.assertNotEqual(one, other)
        self.assertEqual(to_nfkd(one), to_nfkd(other))

    def test_normalization_is_idempotent(self):
        for text in (SHIN_WITH_SHIN_DOT, BET + QAMATS + DAGESH, LIGATURE_ALEF_LAMED):
            with self.subTest(text=text):
                self.assertEqual(to_nfkd(to_nfkd(text)), to_nfkd(text))

    def test_lookalike_vowels_are_not_folded(self):
        # Qamats and qamats qatan are different vowels, as are holam and holam haser
        # for vav. Folding them would silently rewrite the text rather than normalize
        # its encoding.
        self.assertEqual(to_nfkd(QAMATS_QATAN), QAMATS_QATAN)
        self.assertNotEqual(to_nfkd(QAMATS), to_nfkd(QAMATS_QATAN))
        self.assertNotEqual(to_nfkd(HOLAM), to_nfkd(HOLAM_HASER_FOR_VAV))

    def test_ordinary_pointed_text_is_left_alone(self):
        already = BET + PATAH + ALEF
        self.assertEqual(to_nfkd(already), already)
        self.assertTrue(is_nfkd(already))

    def test_is_nfkd_detects_what_to_nfkd_would_change(self):
        self.assertFalse(is_nfkd(SHIN_WITH_SHIN_DOT))
        self.assertTrue(is_nfkd(to_nfkd(SHIN_WITH_SHIN_DOT)))


class DescribeNormalizationTestCase(unittest.TestCase):
    def test_each_rewritten_character_is_named(self):
        described = describe_normalization(SHIN_WITH_SHIN_DOT + ALEF)
        self.assertEqual(len(described), 1)
        self.assertIn("FB2A", described[0])
        self.assertIn("05E9", described[0])

    def test_unchanged_text_describes_nothing(self):
        self.assertEqual(describe_normalization(BET + PATAH), [])

    def test_a_repeated_character_is_reported_once(self):
        # The useful question about a source is which spellings it mixes, not how many
        # times each occurs.
        self.assertEqual(len(describe_normalization(EM_SPACE * 5)), 1)


class ComparisonFormTestCase(unittest.TestCase):
    """The other job in this module: lossy forms, for matching only."""

    def test_marks_are_dropped(self):
        self.assertEqual(strip_marks(BET + DAGESH + QAMATS), BET)

    def test_the_consonant_skeleton_drops_everything_else(self):
        self.assertEqual(normalize_hebrew(BET + QAMATS + " " + ALEF + "!"), BET + ALEF)

    def test_latin_is_folded_to_alphanumerics(self):
        self.assertEqual(normalize_latin("Blessed “are” You!"), "blessedareyou")

    def test_comparison_forms_are_not_storage_forms(self):
        # Guards the distinction the module docstring draws: these throw text away and
        # must never be what gets written to a project file.
        pointed = BET + QAMATS
        self.assertNotEqual(normalize_hebrew(pointed), to_nfkd(pointed))


if __name__ == "__main__":
    unittest.main()
