# -*- coding: utf-8 -*-
"""Tests for resolving the Wikisource foundation text to what the 1949 print reads.

Every fixture here is synthetic. Asserting on the committed transcription would test the
data rather than the code, and CI does not initialise the submodule that holds it.
"""

import unittest

from opensiddur.importer.birnbaum_scan import transcription


class TestVariantResolution(unittest.TestCase):
    def test_a_named_birnbaum_parameter_is_the_reading(self):
        r = transcription.resolve("{{נוסח|אָבוֹא|בירנבוים=אָבֹא}}")
        self.assertEqual(r.text, "אָבֹא")
        self.assertEqual(r.substitutions, [("אָבוֹא", "אָבֹא")])

    def test_an_attribution_to_someone_else_still_defers_to_birnbaum(self):
        """`|=מסורה` says the positional is the Masorah's, not this book's."""
        r = transcription.resolve("{{נוסח|מְּאֹד|=מסורה|בירנבוים=מְאֹד}}")
        self.assertEqual(r.text, "מְאֹד")

    def test_an_attribution_to_birnbaum_makes_the_positional_the_reading(self):
        """The convention inverts here, and preferring a named parameter would take the
        variant. `אחרים=` is everyone who is *not* this book."""
        r = transcription.resolve("{{נוסח|הַרְהוֹר|=בירנבוים|אחרים=הִרְהוּר}}")
        self.assertEqual(r.text, "הַרְהוֹר")

    def test_an_attribution_naming_birnbaum_among_others_reads_the_same_way(self):
        r = transcription.resolve('{{נוסח|לְהַנִּֽיחַ|=בירנבוים ועבו"י|אחרים=לְהָנִֽיחַ}}')
        self.assertEqual(r.text, "לְהַנִּֽיחַ")

    def test_a_prose_note_is_not_substituted_into_the_text(self):
        """One of these is a sentence about how he sets two Torah portions. Substituting
        it would put a paragraph of Hebrew prose into the middle of a prayer, and the
        comparison would report it as the print's own words."""
        note = "בלי חלוקה בין שתי הפרשות, ואילו בתרגום האנגלי המקביל חילק ביניהן"
        r = transcription.resolve("{{נוסח|וְהָיָה|בירנבוים=" + note + "}}")
        self.assertEqual(r.text, "וְהָיָה")
        self.assertEqual(len(r.comments), 1)

    def test_a_template_with_no_birnbaum_parameter_keeps_its_positional(self):
        r = transcription.resolve("{{נוסח|שָׁלוֹם|אחרים=שָׁלֹם}}")
        self.assertEqual(r.text, "שָׁלוֹם")

    def test_text_outside_a_template_is_untouched(self):
        r = transcription.resolve("אַ {{נוסח|בּ|בירנבוים=גּ}} דּ")
        self.assertEqual(r.text, "אַ גּ דּ")


class TestMarkupStripping(unittest.TestCase):
    def test_nothing_but_text_and_separators_survives(self):
        """`compare` tokenises whatever it is handed, so a surviving brace is a word."""
        out = transcription.strip_markup(
            "{{#קטע:א/ב|ג}} [[תהלים לו/טעמים#לו ח|תהלים לו]] '''בּ''' <קטע התחלה=x/>")
        self.assertNotIn("{", out)
        self.assertNotIn("[", out)
        self.assertNotIn("<", out)
        self.assertNotIn("'", out)

    def test_a_piped_link_keeps_what_was_displayed(self):
        self.assertEqual(transcription.strip_markup("[[a/b#c|תהלים לו]]"), "תהלים לו")


class TestSectionExtraction(unittest.TestCase):
    def test_a_named_span_is_taken_whole(self):
        page = "x<קטע התחלה=מה טובו/>מַה טֹּֽבוּ<קטע סוף=מה טובו/>y"
        self.assertEqual(transcription.section(page, "מה טובו"), "מַה טֹּֽבוּ")

    def test_a_span_that_is_not_there_is_reported_as_missing(self):
        self.assertIsNone(transcription.section("x", "לא קיים"))


if __name__ == "__main__":
    unittest.main()
