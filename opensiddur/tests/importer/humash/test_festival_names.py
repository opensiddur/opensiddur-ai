"""Tests for the Hebrew titles of the festival readings.

The names given here are hebcal's own naming conventions rather than a copy of its data, so
these keep their meaning when hebcal adds or renames a reading.
"""

import logging
import unittest

from opensiddur.importer.humash.festival_names import hebrew_name


class TestHebrewName(unittest.TestCase):
    def test_a_plain_occasion(self):
        self.assertEqual(hebrew_name("Shabbat Shekalim"), "שַׁבָּת שְׁקָלִים")

    def test_a_qualifier_becomes_a_hebrew_parenthetical(self):
        self.assertEqual(hebrew_name("Yom Kippur (Mincha)"), "יוֹם הַכִּפּוּרִים (מִנְחָה)")

    def test_a_roman_numeral_becomes_a_hebrew_letter(self):
        self.assertEqual(hebrew_name("Pesach VII"), "פֶּסַח ז׳")

    def test_a_numeral_and_a_qualifier_together(self):
        self.assertEqual(hebrew_name("Sukkot I (on Shabbat)"), "סֻכּוֹת א׳ (בְּשַׁבָּת)")

    def test_a_numbered_day(self):
        self.assertEqual(hebrew_name("Chanukah Day 3"), "חֲנֻכָּה יוֹם ג׳")

    def test_the_longer_occasion_wins_over_the_shorter_one(self):
        """"Shabbat Rosh Chodesh Chanukah" is its own reading, not Rosh Chodesh."""
        self.assertEqual(
            hebrew_name("Shabbat Rosh Chodesh Chanukah"), "שַׁבָּת רֹאשׁ חֹדֶשׁ חֲנֻכָּה"
        )

    def test_a_month_is_not_read_as_an_ordinal(self):
        """Adar II is the second Adar, not the second Rosh Chodesh Adar."""
        self.assertEqual(hebrew_name("Rosh Chodesh Adar II"), "רֹאשׁ חֹדֶשׁ אֲדָר ב׳")

    def test_a_reading_named_by_its_parshah(self):
        self.assertEqual(
            hebrew_name("Masei on Shabbat Rosh Chodesh"), "מַסְעֵי (בְּשַׁבָּת רֹאשׁ חֹדֶשׁ)"
        )

    def test_a_parshah_named_inside_a_qualifier(self):
        self.assertEqual(hebrew_name("Shabbat Shuva (with Ha'azinu)"), "שַׁבָּת שׁוּבָה (עִם הַאֲזִינוּ)")

    def test_an_unknown_occasion_keeps_its_english_and_warns(self):
        with self.assertLogs("opensiddur.importer.humash.festival_names", logging.WARNING):
            self.assertEqual(hebrew_name("Feast of Something"), "Feast of Something")

    def test_an_unknown_qualifier_keeps_its_english_and_warns(self):
        with self.assertLogs("opensiddur.importer.humash.festival_names", logging.WARNING):
            self.assertEqual(hebrew_name("Purim (in a leap year)"), "פּוּרִים (in a leap year)")

    def test_no_hebrew_title_contains_latin_letters(self):
        for name in (
            "Pesach Chol ha-Moed Day 2 on Sunday",
            "Sukkot Final Day (Hoshana Raba)",
            "Ta'anit Esther (Mincha)",
            "Rosh Chodesh Sh'vat",
            "Fast Day (Morning)",
        ):
            with self.subTest(name=name):
                self.assertFalse(
                    any(c.isascii() and c.isalpha() for c in hebrew_name(name)),
                    hebrew_name(name),
                )
