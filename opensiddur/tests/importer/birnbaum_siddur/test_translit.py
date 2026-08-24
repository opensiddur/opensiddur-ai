"""Tests for the Hebrew-to-Latin transliterator used to seed URN names.

Fixtures are short vocalised words chosen for the rule each exercises, not passages of
liturgy.
"""

import unittest

from opensiddur.importer.birnbaum_siddur.translit import transliterate, uncertain


class ConsonantTestCase(unittest.TestCase):
    def test_alef_and_ayin_are_silent(self):
        # The table gives neither a letter; the vowel carries the sound.
        self.assertEqual(transliterate("אָב"), "av")
        self.assertEqual(transliterate("עָם"), "am")

    def test_dagesh_distinguishes_bet_from_vet(self):
        self.assertTrue(transliterate("בָּא").startswith("b"))
        self.assertTrue(transliterate("אָב").endswith("v"))

    def test_shin_and_sin_are_distinguished_by_their_dot(self):
        self.assertTrue(transliterate("שָׁם").startswith("sh"))
        self.assertTrue(transliterate("שָׂם").startswith("s"))
        self.assertFalse(transliterate("שָׂם").startswith("sh"))

    def test_final_forms_match_their_medial_letters(self):
        self.assertEqual(transliterate("מָם"), transliterate("מָמ"))


class MatresLectionisTestCase(unittest.TestCase):
    """Vav and yod spelling a vowel rather than sounding as consonants."""

    def test_holam_male_does_not_add_a_v(self):
        # Without this "אָבוֹת" transliterates as "avvot".
        self.assertEqual(transliterate("אָבוֹת"), "avot")

    def test_hiriq_male_does_not_add_a_y(self):
        # Without this "עֲמִידָה" transliterates as "amiydah".
        self.assertEqual(transliterate("עֲמִידָה"), "amidah")

    def test_shuruq_is_a_vowel(self):
        self.assertEqual(transliterate("תַּחֲנוּן"), "tachanun")

    def test_a_consonantal_vav_is_still_a_v(self):
        self.assertIn("v", transliterate("וָו"))


class ShevaTestCase(unittest.TestCase):
    """Which sheva is vocal is not marked, so the guesses are reported."""

    def test_a_word_initial_sheva_is_vocal_and_certain(self):
        self.assertEqual(transliterate("זְמִירוֹת"), "zemirot")
        self.assertFalse(uncertain("זְמִירוֹת"))

    def test_a_sheva_after_a_short_vowel_is_silent_and_flagged(self):
        # The ambiguous case. Silent is the commoner reading, but the pointing does not
        # say, so the name is offered for review rather than asserted.
        self.assertEqual(transliterate("הַבְדָּלָה"), "havdalah")
        self.assertTrue(uncertain("הַבְדָּלָה"))

    def test_a_dagesh_qal_in_the_previous_letter_does_not_make_a_sheva_vocal(self):
        # The dagesh in an initial bet says nothing about the next letter's sheva.
        # Reading it as dagesh chazaq gave "birekhot" instead of "birkhot".
        self.assertEqual(transliterate("בִּרְכוֹת"), "birkhot")

    def test_a_sheva_after_a_long_vowel_is_vocal(self):
        self.assertFalse(uncertain("שׁוֹמְרִים"))


class NameShapeTestCase(unittest.TestCase):
    def test_words_are_joined_with_underscores(self):
        self.assertEqual(transliterate("קַבָּלַת שַׁבָּת"), "qabalat_shabat")

    def test_maqaf_separates_words(self):
        self.assertIn("_", transliterate("כׇּל־הָעָם"))

    def test_output_is_urn_safe(self):
        # A name may not contain '-', which marks a range, nor any URN delimiter.
        for text in ("תְּפִלַּת הָעֲמִידָה", 'שָׁ"ץ', "כׇּל־הָעָם", "(פִּרְקֵי אָבוֹת)"):
            with self.subTest(text=text):
                name = transliterate(text)
                self.assertRegex(name, r"^[a-z0-9_]+$")

    def test_cantillation_is_ignored(self):
        self.assertEqual(transliterate("בְּרֵאשִׁ֖ית"), transliterate("בְּרֵאשִׁית"))

    def test_empty_input_gives_an_empty_name(self):
        self.assertEqual(transliterate(""), "")
        self.assertEqual(transliterate("   "), "")


if __name__ == "__main__":
    unittest.main()
