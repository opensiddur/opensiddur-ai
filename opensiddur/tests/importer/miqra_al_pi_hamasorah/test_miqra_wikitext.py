import unittest

from opensiddur.importer.miqra_al_pi_hamasorah.miqra_wikitext import (
    link_target_to_uri,
    normalize_template_name,
    reset_processor,
    wikitext_to_intermediate_xml,
)


class TestMiqraWikitext(unittest.TestCase):
    def setUp(self):
        reset_processor()

    def test_nosach_nested_large_letter(self):
        frag = wikitext_to_intermediate_xml(
            '{{נוסח|{{מ:אות-ג|בְּ}}רֵאשִׁ֖ית|2=note text}}'
        )
        self.assertIn("<miqra:variant", frag)
        self.assertIn('<miqra:hi rend="large">', frag)
        self.assertIn("בְּ", frag)
        self.assertIn("<miqra:note", frag)
        self.assertIn("note text", frag)

    def test_ketiv_qeri(self):
        frag = wikitext_to_intermediate_xml('{{כו"ק|כתיב|קְרִי}}')
        self.assertIn('<miqra:kq order="ketiv-first">', frag)
        self.assertIn("<miqra:ketiv>כתיב</miqra:ketiv>", frag)
        self.assertIn("<miqra:qeri>קְרִי</miqra:qeri>", frag)

    def test_qeri_ketiv(self):
        frag = wikitext_to_intermediate_xml('{{קו"כ|כתיב|קְרִי}}')
        self.assertIn('order="qeri-first"', frag)

    def test_parashah_open(self):
        frag = wikitext_to_intermediate_xml("{{פפ}}")
        self.assertIn('<miqra:parashah type="open"', frag)

    def test_strip_pasuk(self):
        frag = wikitext_to_intermediate_xml("{{מ:פסוק|בראשית|1|1}}")
        self.assertEqual(frag, "")

    def test_note_link_named_numeric_params(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:קישור בהערה|1=http://www.example.com/doc.pdf|2=label}}"
        )
        self.assertIn('target="http://www.example.com/doc.pdf"', frag)
        self.assertNotIn("1=http", frag)
        self.assertIn("label", frag)

    def test_internal_note_link_to_wikisource_uri(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:קישור פנימי בהערה|ויקיטקסט:מבוא|פרק שני}}"
        )
        self.assertIn('target="https://he.wikisource.org/wiki/', frag)
        self.assertNotIn("ויקיטקסט:מבוא", frag)
        self.assertIn("פרק שני", frag)

    def test_link_target_to_uri(self):
        self.assertEqual(
            link_target_to_uri("http://example.com/x"),
            "http://example.com/x",
        )
        uri = link_target_to_uri("ויקיטקסט:מבוא")
        self.assertTrue(uri.startswith("https://he.wikisource.org/wiki/"))

    def test_column_c_double_underscore(self):
        frag = wikitext_to_intermediate_xml("word__word", column_c=True)
        self.assertIn("word word", frag)

    def test_dechi_shows_first_parameter_only(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:דחי|חַ֭טָּאִים|חַ֭טָּאִ֭ים}}"
        )
        self.assertIn("חַ֭טָּאִים", frag)
        self.assertNotIn("חַ֭טָּאִ֭ים", frag)
        self.assertNotIn("{{מ:דחי", frag)

    def test_tzinor_shows_first_parameter_only(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:צינור|בָטַחְתִּי֮|בָטַ֮חְתִּי֮}}"
        )
        self.assertIn("בָטַחְתִּי֮", frag)
        self.assertNotIn("בָטַ֮חְתִּי֮", frag)
        self.assertNotIn("{{מ:צינור", frag)

    def test_galgal2_shows_first_parameter_only(self):
        frag = wikitext_to_intermediate_xml("{{גלגל-2|אֵ֪ין|אֵ֪֪ין}}")
        self.assertIn("אֵ֪ין", frag)
        self.assertNotIn("אֵ֪֪ין", frag)
        self.assertNotIn("{{גלגל-2", frag)

    def test_yerah_ben_yomo2_shows_first_parameter_only(self):
        frag = wikitext_to_intermediate_xml(
            "{{ירח בן יומו-2|אַלְפַּ֪יִם|אַלְפַּ֪֪יִם}}"
        )
        self.assertIn("אַלְפַּ֪יִם", frag)
        self.assertNotIn("אַלְפַּ֪֪יִם", frag)
        self.assertNotIn("{{ירח בן יומו-2", frag)

    def test_all_templates_from_doc_have_handlers(self):
        """Every template name in templates.tsv examples is recognized."""
        from pathlib import Path
        import csv
        import re

        path = Path(__file__).resolve().parents[4] / "sources" / "miqra_al_pi_hamasorah" / "sheets" / "templates.tsv"
        if not path.exists():
            self.skipTest("templates.tsv not in workspace")

        names: set[str] = set()
        for row in csv.reader(path.open(encoding="utf-8"), delimiter="\t"):
            for cell in row:
                for m in re.finditer(r"\{\{([^}|#][^}|#]*?)(?:\|[^}]*)?\}\}", cell):
                    n = normalize_template_name(m.group(1))
                    if n and n not in ("documentation", "name", "template", "תבנית"):
                        names.add(n)

        from opensiddur.importer.miqra_al_pi_hamasorah.miqra_wikitext import (
            MiqraWikiTextProcessor,
            _STRIP_TEMPLATES,
        )

        proc = MiqraWikiTextProcessor()
        missing = []
        for n in sorted(names):
            if n in _STRIP_TEMPLATES or n in proc.template_handlers:
                continue
            if proc._lookup_handler(n) is not None:
                continue
            missing.append(n)
        self.assertEqual(missing, [], f"Unhandled templates: {missing}")


if __name__ == "__main__":
    unittest.main()
