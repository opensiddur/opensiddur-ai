import unittest

from opensiddur.importer.miqra_al_pi_hamasorah.miqra_wikitext import (
    _escape_outside_tags,
    _preprocess_column_c,
    _preprocess_miqra_tags,
    _wikitext_basic_markup_to_xml,
    _xml_escape,
    link_target_to_uri,
    normalize_template_name,
    reset_processor,
    wikitext_to_intermediate_xml,
)


class TestNormalizeTemplateName(unittest.TestCase):
    def test_strips_whitespace(self):
        self.assertEqual(normalize_template_name("  פפ  "), "פפ")

    def test_strips_tevnit_prefix(self):
        self.assertEqual(normalize_template_name("תבנית:מ:טעם"), "מ:טעם")
        self.assertEqual(normalize_template_name("תבנית:נוסח"), "נוסח")

    def test_normalizes_quotes(self):
        self.assertEqual(normalize_template_name("מ:כו''ק"), 'מ:כו"ק')
        self.assertEqual(
            normalize_template_name("מ:קו״כ"),
            'מ:קו"כ',
        )


class TestLinkTargetToUri(unittest.TestCase):
    def test_empty_target(self):
        self.assertEqual(link_target_to_uri(""), "")
        self.assertEqual(link_target_to_uri("   "), "")

    def test_protocol_relative_url(self):
        self.assertEqual(
            link_target_to_uri("//cdn.example.com/x.pdf"),
            "https://cdn.example.com/x.pdf",
        )

    def test_fragment_preserved(self):
        uri = link_target_to_uri("דף#פרק")
        self.assertIn("#", uri)
        self.assertTrue(uri.startswith("https://he.wikisource.org/wiki/"))


class TestPreprocessors(unittest.TestCase):
    def test_column_c_double_underscore(self):
        self.assertEqual(_preprocess_column_c("a__b"), "a b")

    def test_column_c_line_break(self):
        self.assertEqual(
            _preprocess_column_c("http://host/path"),
            "http://host/path",
        )
        self.assertEqual(
            _preprocess_column_c("https://host/path"),
            "https://host/path",
        )
        self.assertIn("<miqra:lb/>", _preprocess_column_c("שורה//המשך"))

    def test_miqra_keteg_tags(self):
        s = "<קטע התחלה=foo/>text<קטע סוף=foo/>"
        out = _preprocess_miqra_tags(s)
        self.assertIn('<miqra:segment type="start" name="foo"/>', out)
        self.assertIn('<miqra:segment type="end" name="foo"/>', out)


class TestMarkupAndEscape(unittest.TestCase):
    def test_xml_escape(self):
        self.assertEqual(
            _xml_escape('a & b <c> "d" \'e\''),
            "a &amp; b &lt;c&gt; &quot;d&quot; &apos;e&apos;",
        )

    def test_wikitext_bold_italic(self):
        self.assertEqual(
            _wikitext_basic_markup_to_xml("plain '''bold''' ''italic''"),
            'plain <mw:hi rend="bold">bold</mw:hi> <mw:hi rend="italic">italic</mw:hi>',
        )

    def test_wikitext_bold_italic_combined(self):
        self.assertIn(
            'rend="bold-italic"',
            _wikitext_basic_markup_to_xml("'''''both'''''"),
        )

    def test_escape_outside_tags_preserves_miqra_elements(self):
        inner = _escape_outside_tags(
            "plain <miqra:hi rend=\"large\">א</miqra:hi> '''bold'''"
        )
        self.assertIn("<miqra:hi rend=\"large\">", inner)
        self.assertIn("א", inner)
        self.assertIn('rend="bold"', inner)

    def test_wikitext_markup_in_verse_via_integration(self):
        frag = wikitext_to_intermediate_xml("'''דבר'''")
        self.assertIn('<mw:hi rend="bold">', frag)
        self.assertIn("דבר", frag)


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

    def test_ketiv_only_and_qeri_only(self):
        k = wikitext_to_intermediate_xml("{{כתיב ולא קרי|כתיב}}")
        q = wikitext_to_intermediate_xml("{{קרי ולא כתיב|קְרִי}}")
        self.assertIn("<miqra:ketiv-only>(כתיב)</miqra:ketiv-only>", k)
        self.assertIn("<miqra:qeri-only>[קְרִי]</miqra:qeri-only>", q)

    def test_qok_if_matres(self):
        frag = wikitext_to_intermediate_xml(
            '{{מ:קו"כ-אם-2|display|כתיב|קְרִי}}'
        )
        self.assertIn("display", frag)
        self.assertIn("<miqra:kq-matres>", frag)
        self.assertIn("<miqra:ketiv>כתיב</miqra:ketiv>", frag)
        self.assertIn("<miqra:qeri>קְרִי</miqra:qeri>", frag)

    def test_qok_two_qeri_words(self):
        frag = wikitext_to_intermediate_xml(
            '{{מ:קו"כ קרי שונה מהכתיב בשתי מילים|כתיב|ק1|ק2}}'
        )
        self.assertIn('type="split-qeri"', frag)
        self.assertIn("<miqra:bracketed>ק1</miqra:bracketed>", frag)
        self.assertIn("<miqra:qeri>ק2</miqra:qeri>", frag)
        self.assertIn("<miqra:ketiv>כתיב</miqra:ketiv>", frag)

    def test_parashah_variants(self):
        cases = [
            ("{{פפפ}}", 'type="open-line"'),
            ("{{סס}}", 'type="close"'),
            ("{{ססס}}", 'type="close-inline"'),
            ("{{סס2}}", 'type="close-narrow"'),
            ("{{מ:ששש}}", 'type="shirah"'),
        ]
        for wikitext, expected in cases:
            with self.subTest(wikitext=wikitext):
                self.assertIn(expected, wikitext_to_intermediate_xml(wikitext))

    def test_parashah_mid_verse_attribute(self):
        frag = wikitext_to_intermediate_xml("{{פפ|פסקא באמצע פסוק}}")
        self.assertIn('midVerse="true"', frag)

    def test_poetic_levels(self):
        for level, template in enumerate(("ר0", "ר1", "ר2", "ר3", "ר4")):
            frag = wikitext_to_intermediate_xml(f"{{{{{template}}}}}")
            self.assertIn(f'<miqra:poetic level="{level}"/>', frag)

    def test_centered_title(self):
        frag = wikitext_to_intermediate_xml("{{פרשה-מרכז|כותרת}}")
        self.assertIn("<miqra:centered>כותרת</miqra:centered>", frag)

    def test_letter_formatting(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:אות-ק|ק}}{{מ:אות תלויה|ת}}{{מ:אות מנוקדת|מ}}{{מ:נו\"ן הפוכה|ן}}"
        )
        self.assertIn('rend="small"', frag)
        self.assertIn('rend="raised"', frag)
        self.assertIn("<miqra:dotted>", frag)
        self.assertIn("<miqra:inverted-nun>", frag)

    def test_yerushalem_variants(self):
        y = wikitext_to_intermediate_xml("{{מ:ירושלם|v|a}}")
        ya = wikitext_to_intermediate_xml("{{מ:ירושלמה|v|a}}")
        self.assertIn('<miqra:yerushalem vowel="v" accent="a"/>', y)
        self.assertIn('<miqra:yerushalema vowel="v" accent="a"/>', ya)

    def test_standalone_accents(self):
        frag = wikitext_to_intermediate_xml(
            "{{ירח בן יומו}}{{גלגל}}{{אתנח הפוך}}"
        )
        self.assertIn('type="yerah-ben-yomo"', frag)
        self.assertIn('type="galgal"', frag)
        self.assertIn('type="etnah-hafukh"', frag)

    def test_taam_handlers(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:טעם ומתג באות אחת|א}}"
            "{{שני טעמים באות אחת}}"
            "{{מ:גרש ותלישא גדולה}}"
            "{{מ:גרשיים ותלישא גדולה}}"
        )
        self.assertIn("א", frag)
        self.assertIn('type="geresh-telisha-gedola"', frag)
        self.assertIn('type="gershayim-telisha-gedola"', frag)

    def test_qamats_named_params(self):
        frag = wikitext_to_intermediate_xml("{{מ:קמץ|ד=דָּ}}")
        self.assertIn("דָּ", frag)

    def test_taam_dummy_strips_leading_marker(self):
        frag = wikitext_to_intermediate_xml("{{מ:טעם|Xאות}}")
        self.assertIn("אות", frag)
        self.assertNotIn("Xאות", frag)

    def test_qupo_accent(self):
        frag = wikitext_to_intermediate_xml(
            "{{שני טעמים באות אחת קמץ-תחתון-פתח-עליון|עליו=א}}"
        )
        self.assertIn('<miqra:qupo-accent above="א"/>', frag)

    def test_punctuation_and_maqaf(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:לגרמיה-2}}{{מ:פסק}}{{מ:מקף אפור}}"
        )
        self.assertIn('type="legarmeh"', frag)
        self.assertIn('type="paseq"', frag)
        self.assertIn('rend="grey"', frag)

    def test_kol_qamats_default(self):
        self.assertIn("כָּל", wikitext_to_intermediate_xml("{{מ:כל קמץ קטן מרכא}}"))

    def test_notes_and_anchors(self):
        frag = wikitext_to_intermediate_xml(
            "{{מ:הערה|גוף הערה}}{{עוגן בשורה|label}}"
            "{{מ:סיום בטוב|סוף טוב}}"
        )
        self.assertIn("<miqra:note", frag)
        self.assertIn("גוף הערה", frag)
        self.assertIn('<miqra:line-anchor target="label"/>', frag)
        self.assertIn("<miqra:good-ending>סוף טוב</miqra:good-ending>", frag)

    def test_dual_trope_and_accent(self):
        frag = wikitext_to_intermediate_xml(
            "{{קק|target}}"
            "{{מ:כפול|כפול=ד|א=א|ב=ב}}"
        )
        self.assertIn("<miqra:dual-trope-link>target</miqra:dual-trope-link>", frag)
        self.assertIn('<miqra:dual-accent dual="ד">', frag)
        self.assertIn('role="א"', frag)
        self.assertIn('role="ב"', frag)

    def test_emphasis_and_footnote_mark(self):
        frag = wikitext_to_intermediate_xml("{{מודגש|חשוב}}{{ש}}")
        self.assertIn('<mw:hi rend="bold">חשוב</mw:hi>', frag)
        self.assertIn("<miqra:fn-mark/>", frag)

    def test_wikilink(self):
        frag = wikitext_to_intermediate_xml("[[דף]] and [[דף|תווית]]")
        self.assertIn('<mw:link target="https://he.wikisource.org/wiki/', frag)
        self.assertIn("תווית", frag)

    def test_noinclude_stripped(self):
        frag = wikitext_to_intermediate_xml(
            "visible<noinclude>hidden</noinclude>still"
        )
        self.assertIn("visible", frag)
        self.assertIn("still", frag)
        self.assertNotIn("hidden", frag)

    def test_keteg_segments_in_wikitext(self):
        frag = wikitext_to_intermediate_xml("<קטע התחלה=seg/>")
        self.assertIn('<miqra:segment type="start" name="seg"/>', frag)

    def test_column_c_line_break_integration(self):
        frag = wikitext_to_intermediate_xml("א//ב", column_c=True)
        self.assertIn("<miqra:lb/>", frag)

    def test_nosach_without_note(self):
        frag = wikitext_to_intermediate_xml("{{נוסח|טקסט}}")
        self.assertEqual(frag, "טקסט")
        self.assertNotIn("<miqra:variant", frag)

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
