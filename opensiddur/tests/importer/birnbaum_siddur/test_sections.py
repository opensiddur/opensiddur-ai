"""Tests for the Birnbaum unit inventory.

The table of contents, structure index and page table are all synthesised here. Nothing
reads the real sources, so these keep meaning as Wikisource is edited.
"""

import json
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.birnbaum_siddur.sections import (
    ROOT_TITLE,
    Unit,
    gather,
    main,
    parse_toc,
    report_units,
)
from opensiddur.importer.util.pages import (
    birnbaum_siddur_correspondence_path,
    birnbaum_siddur_data_directory,
    birnbaum_siddur_source_text_directory,
)

R = ROOT_TITLE


def link(name, display):
    return f"[[{R}/אשכנז/{name}|{display}]]"


TOC = f"""{{{{כותרת לסידור השלם}}}}

==א. סֵֽדֶר הַתְּפִלָּה בִּימֵי חוֹל==

*'''תְּפִלַּת שַׁחֲרִית:''' {link("עמידה", "עֲמִידָה")} · {link("תחנון", "תַּחֲנוּן")}
*'''{link("מנחה", "מִנְחָה")}'''

==ב. סֵֽדֶר בְּרָכוֹת==

{link("ברכות", "בְּרָכוֹת")} · {link("חסר", "חָסֵר")}

==ה. הַמַּחֲזוֹר הַשָּׁלֵם לְרֹאשׁ הַשָּׁנָה==

*'''יוֹם רֹאשׁ הַשָּׁנָה:''' {link("שופר", "שׁוֹפָר")}

==הוֹסָפוֹת==

'''ז. [[משתמש:Dovi/מקרא|מִקְרָא]]'''
"""


class ParseTocTestCase(unittest.TestCase):
    def setUp(self):
        self.units = parse_toc(TOC)
        self.by_title = {u.title.split("/")[-1]: u for u in self.units}

    def test_bulleted_and_unbulleted_groups_are_both_read(self):
        # Four of the seven real groups list their units on plain lines rather than
        # bullets; reading only bullets silently dropped them.
        self.assertIn("עמידה", self.by_title)
        self.assertIn("ברכות", self.by_title)

    def test_the_group_supplies_the_occasion(self):
        self.assertEqual(self.by_title["עמידה"].occasion, "chol")
        self.assertEqual(self.by_title["ברכות"].occasion, "berakhot")

    def test_the_subgroup_supplies_the_service(self):
        self.assertEqual(self.by_title["עמידה"].service, "shacharit")
        self.assertIsNone(self.by_title["ברכות"].service)

    def test_a_bolded_link_is_its_own_service(self):
        self.assertEqual(self.by_title["מנחה"].service, "minchah")

    def test_machzor_units_are_marked(self):
        self.assertIn("MACHZOR", self.by_title["שופר"].flags)

    def test_links_outside_the_siddur_are_not_units(self):
        # The additions link out to other projects; those are references, not units.
        self.assertFalse(any("משתמש" in u.title for u in self.units))


class GatherTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        source = birnbaum_siddur_source_text_directory(self.root)
        (source / "אשכנז").mkdir(parents=True, exist_ok=True)
        (source / "אשכנז.txt").write_text(TOC, encoding="utf-8")

        # Two units share pages 3 and 5; two others touch only at page 9.
        bodies = {
            "עמידה": "<קטע התחלה=עמוד 1/>x<קטע סוף=עמוד 1/>"
                     "<קטע התחלה=עמוד 3/>x<קטע סוף=עמוד 3/>"
                     "<קטע התחלה=עמוד 5/>x<קטע סוף=עמוד 5/>"
                     "{{הסידור השלם הוראה|r}}",
            "תחנון": "<קטע התחלה=עמוד 3/>x<קטע סוף=עמוד 3/>"
                     "<קטע התחלה=עמוד 5/>x<קטע סוף=עמוד 5/>",
            "מנחה": "<קטע התחלה=עמוד 7/>x<קטע סוף=עמוד 7/>"
                    "<קטע התחלה=עמוד 9/>x<קטע סוף=עמוד 9/>",
            "ברכות": "<קטע התחלה=עמוד 9/>x<קטע סוף=עמוד 9/>",
            "שופר": "<קטע התחלה=עמוד 11/>x<קטע סוף=עמוד 11/>",
            "מודרני": "no page markers at all",
            "בעבודה": "{{בעבודה}}<קטע התחלה=עמוד 13/>x<קטע סוף=עמוד 13/>"
                       "<קטע התחלה=עמוד 25/>x<קטע סוף=עמוד 25/>",
        }
        for name, body in bodies.items():
            (source / "אשכנז" / f"{name}.txt").write_text(body, encoding="utf-8")

        structure = {"pages": {
            f"{R}/אשכנז/{name}": {"defines": [], "transcludes": [
                {"title": f"{R}/אשכנז/דפי יסוד/תפילת העמידה", "section": "s"}
            ], "redirect_target": None, "path": ""}
            for name in bodies
        }}
        birnbaum_siddur_data_directory(self.root).mkdir(parents=True, exist_ok=True)
        (birnbaum_siddur_data_directory(self.root) / "structure.json").write_text(
            json.dumps(structure, ensure_ascii=False), encoding="utf-8")

        birnbaum_siddur_correspondence_path(self.root).write_text(json.dumps({
            "pages": [{"scan_page": n + 25, "printed_page": str(n), "side": "he"}
                      for n in range(1, 31)]
        }), encoding="utf-8")

        self.units = gather(self.root)
        self.by = {u.title.split("/")[-1]: u for u in self.units}

    def test_a_unit_the_toc_does_not_list_is_still_found(self):
        # The ToC gives order, not completeness. Birkat HaMazon is absent from the real
        # one; taking the ToC as the inventory would drop it silently.
        self.assertIn("מודרני", self.by)
        self.assertIn("NOT-IN-TOC", self.by["מודרני"].flags)

    def test_a_unit_with_no_printed_page_is_out_of_scope(self):
        # The single test for whether the 1949 book contains it.
        self.assertIn("NOT-IN-1949", self.by["מודרני"].flags)
        self.assertFalse(self.by["מודרני"].in_scope)

    def test_a_missing_page_is_a_stub(self):
        self.assertIn("STUB", self.by["חסר"].flags)
        self.assertFalse(self.by["חסר"].in_scope)

    def test_machzor_units_are_out_of_scope(self):
        self.assertFalse(self.by["שופר"].in_scope)

    def test_work_in_progress_is_marked_but_stays_in_scope(self):
        self.assertIn("WIP", self.by["בעבודה"].flags)
        self.assertTrue(self.by["בעבודה"].in_scope)

    def test_two_units_overlapping_by_several_pages_are_flagged(self):
        self.assertIn("OVERLAPPING-PAGES", self.by["עמידה"].flags)
        self.assertIn("OVERLAPPING-PAGES", self.by["תחנון"].flags)

    def test_units_touching_at_one_page_are_not_flagged(self):
        # A unit ending where the next begins is how the book reads, not a problem.
        self.assertNotIn("OVERLAPPING-PAGES", self.by["מנחה"].flags)
        self.assertNotIn("OVERLAPPING-PAGES", self.by["ברכות"].flags)

    def test_statistics_are_collected(self):
        unit = self.by["עמידה"]
        self.assertEqual(unit.instructions, 1)
        self.assertEqual(unit.transcludes, 1)
        self.assertEqual(unit.foundation_pages, {"תפילת העמידה"})

    def test_a_urn_is_proposed_from_group_service_and_title(self):
        self.assertTrue(self.by["עמידה"].urn.endswith("chol/shacharit/amidah"))

    def test_non_contiguous_pages_are_shown_as_runs(self):
        # Min-to-max would read as one long span the unit does not occupy.
        self.assertEqual(self.by["מנחה"].page_range, "7–9")
        self.assertEqual(self.by["בעבודה"].page_range, "13, 25")

    def test_a_missing_table_of_contents_is_reported(self):
        (birnbaum_siddur_source_text_directory(self.root) / "אשכנז.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            gather(self.root)


class ReportTestCase(GatherTestCase):
    def test_the_report_separates_scope_from_exclusions(self):
        text = report_units(self.units)
        self.assertIn("## Units in scope", text)
        self.assertIn("## Excluded", text)
        self.assertIn("machzor: a separate book", text)
        self.assertIn("no printed page in the 1949 edition", text)

    def test_the_report_has_no_variant_column(self):
        # Variant sites live in the foundation pages, so the column would be empty.
        self.assertNotIn("Nusach", report_units(self.units))

    def test_main_writes_the_report(self):
        out = self.root / "BIRNBAUM_UNITS.md"
        self.assertEqual(main(["--sourcetexts-root", str(self.root),
                               "--report-units", "--output", str(out)]), 0)
        self.assertTrue(out.is_file())

    def test_main_reports_a_missing_source_tree(self):
        self.assertEqual(main(["--sourcetexts-root", str(self.root / "nowhere")]), 1)


if __name__ == "__main__":
    unittest.main()
