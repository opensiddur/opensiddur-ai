import unittest

from opensiddur.importer.opensiddur_org.languages import (
    bcp47,
    language_from_header,
    language_from_lang_attribute,
    same_language,
)


class TestBcp47(unittest.TestCase):
    def test_usual_script_is_dropped(self) -> None:
        self.assertEqual(language_from_lang_attribute("heb-Hebr"), "he")
        self.assertEqual(language_from_lang_attribute("eng-Latn"), "en")
        self.assertEqual(language_from_lang_attribute("lad-Hebr"), "lad")

    def test_unusual_script_is_kept(self) -> None:
        self.assertEqual(language_from_lang_attribute("heb-Latn"), "he-Latn")
        self.assertEqual(language_from_lang_attribute("lad-Latn"), "lad-Latn")
        self.assertEqual(language_from_lang_attribute("yid-Latn"), "yi-Latn")

    def test_language_without_two_letter_code_keeps_three(self) -> None:
        self.assertEqual(bcp47("jpa", "Hebr"), "jpa")
        self.assertEqual(bcp47("sdt", "Latn"), "sdt-Latn")

    def test_empty_attribute(self) -> None:
        self.assertIsNone(language_from_lang_attribute(""))


class TestHeaders(unittest.TestCase):
    def test_role_and_language(self) -> None:
        self.assertEqual(language_from_header("Source (Hebrew)"), ("source", "he"))
        self.assertEqual(language_from_header("Translation (English)"), ("translation", "en"))

    def test_romanized_language_is_latin_script(self) -> None:
        self.assertEqual(language_from_header("Transliteration (romanized Hebrew)"), ("transliteration", "he-Latn"))

    def test_transliteration_is_latin_whatever_the_header_says(self) -> None:
        self.assertEqual(language_from_header("Transliteration (Ge’ez)"), ("transliteration", "gez-Latn"))

    def test_transliteration_headed_english_names_no_language(self) -> None:
        self.assertEqual(language_from_header("Transliteration (English)"), ("transliteration", ""))

    def test_reversed_header(self) -> None:
        self.assertEqual(language_from_header("Yiddish (source)"), ("source", "yi"))

    def test_bare_language_is_the_source(self) -> None:
        self.assertEqual(language_from_header("Hebrew"), ("source", "he"))

    def test_typos_in_the_role(self) -> None:
        self.assertEqual(language_from_header("Souce (Hebrew)"), ("source", "he"))
        self.assertEqual(language_from_header("Tranlsation (English)"), ("translation", "en"))

    def test_contribute_column(self) -> None:
        self.assertEqual(language_from_header("Contribute a translation"), ("contribute", ""))


class TestSameLanguage(unittest.TestCase):
    def test_script_subtag_of_the_usual_script(self) -> None:
        self.assertTrue(same_language("he", "he-Hebr"))

    def test_transliteration_is_not_the_same(self) -> None:
        self.assertFalse(same_language("he", "he-Latn"))

    def test_language_families(self) -> None:
        self.assertTrue(same_language("arc", "jpa"))
        self.assertTrue(same_language("el", "grc"))
        self.assertFalse(same_language("arc", "he"))


if __name__ == "__main__":
    unittest.main()
