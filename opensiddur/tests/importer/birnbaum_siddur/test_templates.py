"""Tests for the Birnbaum wikitext inventory.

Every fixture is a hand-written page built in the test. Nothing reads the real source
tree, so these keep meaning when Hebrew Wikisource is edited.
"""

import tempfile
import unittest
from pathlib import Path

import mwparserfromhell

from opensiddur.importer.birnbaum_siddur.templates import (
    classify_nusach,
    classify_section_name,
    inventory,
    iter_source_pages,
    main,
)
from opensiddur.importer.util.pages import (
    birnbaum_siddur_external_text_directory,
    birnbaum_siddur_source_text_directory,
)


def nusach(wikitext: str):
    return classify_nusach(mwparserfromhell.parse(wikitext).filter_templates()[0])


class NusachDirectionTestCase(unittest.TestCase):
    """Which reading is Birnbaum's depends on where the attribution sits.

    This is the distinction the converter turns on: a `swap` means the running text is
    *not* Birnbaum's and the labelled alternative is, so leaving it alone would publish
    the wrong reading under his name.
    """

    def test_a_labelled_alternative_means_the_running_text_is_not_birnbaums(self):
        self.assertEqual(nusach("{{נוסח|אלף|בירנבוים=בית}}"), "swap")

    def test_an_empty_named_attribution_means_the_running_text_is_birnbaums(self):
        self.assertEqual(nusach("{{נוסח|אלף|=בירנבוים}}"), "attributed")

    def test_the_two_shapes_differ_only_by_which_side_of_the_equals(self):
        # Reading one as the other inverts the variant. Pinned side by side so the
        # difference cannot be optimised away by accident.
        self.assertNotEqual(
            nusach("{{נוסח|אלף|בירנבוים=בית}}"),
            nusach("{{נוסח|אלף|=בירנבוים}}"),
        )

    def test_both_attributions_present_is_ambiguous(self):
        self.assertEqual(nusach("{{נוסח|אלף|=בירנבוים|בירנבוים=בית}}"), "ambiguous")

    def test_another_editions_attribution_is_not_a_swap(self):
        self.assertEqual(nusach('{{נוסח|אלף|עבו"י=בית}}'), "other")

    def test_a_positional_alternative_is_unlabelled(self):
        self.assertEqual(nusach("{{נוסח|אלף|בית}}"), "unlabelled")

    def test_misspellings_of_birnbaum_still_count(self):
        # Four spellings occur in the source. A typo must not silently reclassify a
        # variant as somebody else's reading.
        for spelling in ("בירנבוים", "בינרבוים", "בירנובים", "ברינבוים"):
            with self.subTest(spelling=spelling):
                self.assertEqual(nusach(f"{{{{נוסח|אלף|{spelling}=בית}}}}"), "swap")


class SectionNameRoleTestCase(unittest.TestCase):
    def test_role_markers_are_recognised(self):
        cases = {
            "ברכת אבות הוראה": "instruction",
            "הערה על מוריד הטל": "note",
            "כותרת לתפילת העמידה": "heading",
            "מילים מוריד הטל": "words",
            "זכרנו לחיים הכל": "whole",
            "פרשת שמע מקור": "source",
            "המשך ברכת אבות": "continuation",
            "פסוק שמע ישראל": "verse",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertIn(expected, classify_section_name(name))

    def test_a_name_may_carry_two_roles(self):
        # An instruction belonging to a named prayer is both.
        roles = classify_section_name("זכרנו לחיים הוראה 2")
        self.assertIn("instruction", roles)
        self.assertIn("chunk", roles)

    def test_a_page_label_is_not_also_a_chunk(self):
        # "עמוד 81" ends in a digit, so it matches the chunk pattern too. It is a
        # pagination marker, and double-counting it would overstate the chunks by the
        # number of pages in the book.
        roles = classify_section_name("עמוד 81")
        self.assertEqual(roles, ["page"])

    def test_a_real_chunk_is_still_a_chunk(self):
        self.assertIn("chunk", classify_section_name("ברכת אבות 2"))

    def test_a_bare_prayer_name_is_plain(self):
        self.assertEqual(classify_section_name("מגן אברהם"), ["plain"])


class InventoryTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        source = birnbaum_siddur_source_text_directory(self.root)
        (source / "אשכנז" / "דפי יסוד").mkdir(parents=True, exist_ok=True)
        (source / "אשכנז" / "דפי יסוד" / "תפילת העמידה.txt").write_text(
            "<קטע התחלה=כותרת לתפילת העמידה/>{{כותרת לסידור השלם|העמידה}}"
            "<קטע סוף=כותרת לתפילת העמידה/>\n"
            "<קטע התחלה=עמוד 81/>{{ש}}<קטע סוף=עמוד 81/>\n"
            "<קטע התחלה=ברכת אבות 1/>{{נוסח|אלף|בירנבוים=בית}}<קטע סוף=ברכת אבות 1/>\n",
            encoding="utf-8",
        )
        (source / "אשכנז" / "הלל.txt").write_text(
            "{{#קטע:הסידור השלם (בירנבוים)/אשכנז/דפי יסוד/הלל|מזמור קי\"ג}}\n"
            "{{הסידור השלם הוראה|קהל:}}\n",
            encoding="utf-8",
        )

        external = birnbaum_siddur_external_text_directory(self.root)
        external.mkdir(parents=True, exist_ok=True)
        (external / "עשרת הדברות.txt").write_text(
            "<קטע התחלה=דברות/>{{ש}}<קטע סוף=דברות/>\n", encoding="utf-8"
        )

    def test_source_and_external_pages_are_both_read(self):
        titles = [title for title, _ in iter_source_pages(self.root)]
        self.assertEqual(len(titles), 3)
        self.assertIn("עשרת הדברות", titles)

    def test_scan_pages_are_not_counted(self):
        # text/NNN.txt is a second assembly of the same material; counting it would
        # double every template.
        (self.root / "birnbaum_siddur" / "text").mkdir(parents=True, exist_ok=True)
        (self.root / "birnbaum_siddur" / "text" / "100.txt").write_text(
            "{{ש}}{{ש}}{{ש}}", encoding="utf-8"
        )
        self.assertEqual(inventory(self.root).templates["ש"].count, 2)

    def test_labelled_section_transclusions_collapse_to_one_entry(self):
        # Their "name" embeds the target page, so left alone every target would look
        # like a different template.
        found = inventory(self.root)
        self.assertIn("#קטע: (labelled section)", found.templates)
        self.assertNotIn("ש", found.templates["#קטע: (labelled section)"].shapes)

    def test_templates_tags_and_roles_are_counted(self):
        found = inventory(self.root)
        self.assertEqual(found.pages_read, 3)
        self.assertEqual(found.templates["ש"].count, 2)
        self.assertEqual(found.tags["קטע"].count, 8)
        self.assertEqual(found.roles["heading"].count, 1)
        self.assertEqual(found.roles["page"].count, 1)
        self.assertEqual(found.nusach["swap"], 1)

    def test_pages_that_are_not_nfkd_are_flagged(self):
        # The schema requires NFKD, and the Birnbaum-vs-wiki reading comparison depends
        # on it: the same word in two normalisations compares unequal.
        source = birnbaum_siddur_source_text_directory(self.root)
        (source / "composed.txt").write_text("ששׁ", encoding="utf-8")
        self.assertIn("composed", inventory(self.root).unnormalised)

    def test_a_missing_tree_is_reported_not_crashed_on(self):
        self.assertEqual(inventory(self.root / "nowhere").pages_read, 0)


class MainTestCase(InventoryTestCase):
    def test_report_runs(self):
        self.assertEqual(main(["--sourcetexts-root", str(self.root), "--report"]), 0)

    def test_json_is_written(self):
        out = self.root / "out" / "inventory.json"
        self.assertEqual(
            main(["--sourcetexts-root", str(self.root), "--json", str(out)]), 0
        )
        self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
