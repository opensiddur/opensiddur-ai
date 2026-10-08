"""The electronic book: html.xslt's rendering, and html.py's assembly of the page."""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.common.xslt import xslt_transform_string
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.html.css import typography_css, xslt_parameters
from opensiddur.exporter.client_settings import is_reader_supplied
from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.derived_settings import STATIC_DEFAULTS
from opensiddur.exporter.html.html import (
    XSLT_FILE,
    basic_controls,
    build_book,
    feature_words,
    settings_catalogue,
)
from opensiddur.exporter.html.markers import BookConditions, Feature, prepare
from opensiddur.exporter.linear import get_linear_data, reset_linear_data
from opensiddur.exporter import typography as typography_module
from opensiddur.exporter.typography import TypographyConfig
from opensiddur.tests.exporter.js_engine import require_node, run_js

J = JLPTEI_NAMESPACE
P = PROCESSING_NAMESPACE
H = "http://www.w3.org/1999/xhtml"
NS = {"h": H}


def _cond(xml_id: str, name: str, value: str = "true", rubric: str = "",
          fs: str = "opensiddur:override") -> str:
    note = f'<tei:note type="instruction">{rubric}</tei:note>' if rubric else ""
    return (f'<j:conditional xml:id="{xml_id}">{note}<tei:fs type="{fs}"><tei:f name="{name}">'
            f'<tei:binary value="{value}"/></tei:f></tei:fs></j:conditional>')


def _compiled(body: str, *, electronic: bool = True, lang: str = "en") -> bytes:
    destination = ' p:destination="electronic"' if electronic else ""
    return f'''<tei:TEI xmlns:tei="{TEI_NS}" xmlns:j="{J}" xmlns:p="{P}" xml:lang="{lang}"
    p:project="proj" p:file_name="index.xml"{destination}>
  <tei:teiHeader><tei:fileDesc><tei:titleStmt><tei:title>Header Title</tei:title>
  </tei:titleStmt></tei:fileDesc></tei:teiHeader>
  <tei:text><tei:body>{body}</tei:body></tei:text>
</tei:TEI>'''.encode()


def _render(body: str, **params) -> etree.ElementBase:
    root = etree.fromstring(_compiled(body))
    prepare(root)
    return etree.fromstring(xslt_transform_string(
        XSLT_FILE, etree.tostring(root, encoding="unicode"),
        xslt_params={**xslt_parameters(TypographyConfig()), **params}))


def _classes(element) -> list[str]:
    return (element.get("class") or "").split()


class TestConditionalRendering(unittest.TestCase):

    def test_block_scope(self):
        main = _render(_cond("a", "wedding", rubric="At a wedding:")
                       + "<tei:p>verse</tei:p><j:endConditional target=\"#a\"/>")
        opener, governed, closer = main.xpath("//h:section[@class='body']/*", namespaces=NS)
        self.assertEqual(opener.tag, f"{{{H}}}div")
        self.assertEqual(_classes(opener), ["cm", "cm-open", "m0", "cm-block"])
        self.assertEqual(opener.xpath("string(h:span[@class='rubric'])", namespaces=NS),
                         "At a wedding:")
        self.assertEqual(governed.tag, f"{{{H}}}p")
        self.assertEqual(_classes(governed), ["c0"])
        self.assertEqual(_classes(closer), ["cm", "cm-close", "m0", "cm-block"])
        self.assertEqual(closer.xpath("string(h:span[@class='cm-br'])", namespaces=NS), "")

    def test_inline_scope_is_bracketed(self):
        main = _render("<tei:p>before " + _cond("a", "wedding")
                       + "inside<j:endConditional target=\"#a\"/> after</tei:p>")
        paragraph = main.find(f".//{{{H}}}p")
        opener, words, closer = paragraph
        self.assertEqual(opener.tag, f"{{{H}}}span")
        self.assertEqual(_classes(opener), ["cm", "cm-open", "m0", "cm-inline", "cm-norubric"])
        self.assertEqual(opener.findtext(f"{{{H}}}span"), "[")
        self.assertEqual((words.text, _classes(words)), ("inside", ["c0"]))
        self.assertEqual(closer.findtext(f"{{{H}}}span"), "]")
        self.assertEqual("".join(paragraph.itertext()), "before [inside] after")

    def test_brackets_follow_the_settings(self):
        main = _render("<tei:p>" + _cond("a", "wedding") + "x<j:endConditional target=\"#a\"/></tei:p>",
                       **{"inline-open": "⟨", "inline-close": "⟩"})
        self.assertEqual("".join(main.find(f".//{{{H}}}p").itertext()), "⟨x⟩")

    def test_block_brackets_instead_of_a_rule(self):
        main = _render(_cond("a", "wedding") + "<tei:p>x</tei:p><j:endConditional target=\"#a\"/>",
                       block="brackets")
        closer = main.xpath("//h:div[contains(@class, 'cm-close')]", namespaces=NS)[0]
        self.assertEqual("".join(closer.itertext()), "]")

    def test_silent_scopes_are_marked(self):
        main = _render('<tei:div>' + _cond("a", "wedding")
                       + '<tei:milestone unit="aliyah.annual" n="first"/>'
                       + '<j:endConditional target="#a"/><tei:p>x</tei:p></tei:div>')
        markers = main.xpath("//*[contains(@class, 'cm ')]", namespaces=NS)
        self.assertEqual([("cm-silent" in _classes(m)) for m in markers], [True, True])
        self.assertEqual(_classes(main.xpath("//h:span[@class='aliyah c0']", namespaces=NS)[0]),
                         ["aliyah", "c0"])

    def test_conditions_are_not_text(self):
        main = _render(_cond("a", "wedding") + "<tei:p>x</tei:p><j:endConditional target=\"#a\"/>")
        self.assertNotIn("wedding", etree.tostring(main, encoding="unicode").replace('class="', ""))


class TestStructure(unittest.TestCase):

    def test_heading_levels(self):
        main = _render('<tei:div><tei:head p:heading-level="3">Three</tei:head></tei:div>'
                       '<tei:div><tei:head p:heading-level="9">Deep</tei:head></tei:div>'
                       '<tei:div><tei:head>Plain</tei:head></tei:div>')
        self.assertEqual([h.tag.split("}")[1] for h in main.iter(f"{{{H}}}h3", f"{{{H}}}h6",
                                                                  f"{{{H}}}h2")],
                         ["h3", "h6", "h2"])

    def test_only_the_first_copy_of_a_urn_is_its_id(self):
        main = _render('<tei:div corresp="urn:x:a"><tei:p>one</tei:p></tei:div>'
                       '<tei:div corresp="urn:x:a"><tei:p>two</tei:p></tei:div>')
        self.assertEqual(len(main.xpath("//*[@id='urn:x:a']")), 1)
        self.assertEqual(main.xpath("string(//*[@id='urn:x:a'])"), "one")

    def test_parallel_columns(self):
        main = _render('<p:parallel column-order="primary_first">'
                       '<p:parallelItem role="primary" xml:lang="he"><tei:p>א</tei:p></p:parallelItem>'
                       '<p:parallelItem role="parallel" xml:lang="en"><tei:p>a</tei:p></p:parallelItem>'
                       '</p:parallel>')
        row = main.xpath("//h:div[contains(@class, 'par')]", namespaces=NS)[0]
        self.assertEqual(_classes(row), ["par", "par-primary_first"])
        primary, parallel = row
        self.assertEqual((primary.get("lang"), primary.get("dir")), ("he", "rtl"))
        self.assertEqual((parallel.get("lang"), parallel.get("dir")), ("en", "ltr"))
        self.assertEqual(_classes(primary), ["col", "col-primary"])

    def test_notes_open_from_numbered_marks(self):
        main = _render('<tei:p>a<tei:note type="commentary">first</tei:note> b'
                       '<tei:note>second</tei:note></tei:p>')
        buttons = main.xpath("//h:button", namespaces=NS)
        self.assertEqual([b.text for b in buttons], ["1", "2"])
        for button in buttons:
            target = main.xpath(f"//*[@id='{button.get('popovertarget')}']")[0]
            self.assertIn("popover", target.attrib)
        self.assertIn("note-commentary", main.xpath("string(//*[@id='note-1']/@class)"))

    def test_verse_numbers(self):
        main = _render('<tei:p><tei:milestone unit="verse" n="3" corresp="urn:x:v3"/>words</tei:p>')
        verse = main.xpath("//h:span[@class='v']", namespaces=NS)[0]
        self.assertEqual((verse.text, verse.get("id")), ("3", "urn:x:v3"))

    def test_alternatives(self):
        main = _render('<tei:p><tei:choice><j:option>one</j:option><j:option>two</j:option>'
                       '</tei:choice></tei:p>')
        self.assertEqual(
            [(o.text, _classes(o)) for o in main.xpath("//h:span[contains(@class, 'option')]", namespaces=NS)],
            [("one", ["option"]), ("two", ["option", "option-alt"])])

    def test_unknown_elements_keep_their_words(self):
        main = _render('<tei:p><tei:unknownThing>kept</tei:unknownThing></tei:p>')
        self.assertEqual(main.xpath("string(//h:span[@class='tei-unknownThing'])", namespaces=NS),
                         "kept")


class TestBlocksInText(unittest.TestCase):
    """A block inside running text must not close the paragraph around it."""

    def _no_block_inside_p(self, main):
        blocks = main.xpath("//h:p//*[self::h:div or self::h:ul or self::h:li or self::h:section"
                            " or self::h:p or starts-with(local-name(), 'h') and"
                            " string-length(local-name()) = 2]", namespaces=NS)
        self.assertEqual(blocks, [])

    def test_a_list_in_a_paragraph(self):
        main = _render("<tei:p>a<tei:list><tei:item>i</tei:item></tei:list>b</tei:p>")
        self._no_block_inside_p(main)
        self.assertEqual(_classes(main.xpath("//h:span[contains(@class, 'list')]", namespaces=NS)[0]),
                         ["list"])

    def test_verse_in_a_note(self):
        main = _render("<tei:p>a<tei:note><tei:lg><tei:l>line</tei:l></tei:lg></tei:note>b</tei:p>")
        self._no_block_inside_p(main)


class TestLabelsReachEveryElement(unittest.TestCase):

    def test_a_line_break_in_a_scope(self):
        main = _render("<tei:p>one " + _cond("a", "wedding") + "two<tei:lb/>three"
                       "<j:endConditional target=\"#a\"/> four</tei:p>")
        self.assertEqual(_classes(main.find(f".//{{{H}}}br")), ["c0"])

    def test_an_alternative_in_a_scope(self):
        main = _render("<tei:p><tei:choice><j:option>one</j:option>"
                       + _cond("a", "wedding") + "<j:option>two</j:option>"
                       "<j:endConditional target=\"#a\"/></tei:choice></tei:p>")
        governed = main.xpath("//h:span[contains(@class, 'c0')]", namespaces=NS)
        self.assertEqual([("".join(g.itertext()), _classes(g)) for g in governed],
                         [("two", ["option", "option-alt", "c0"])])
        self.assertEqual(len(main.xpath("//*[contains(@class, 'm0')]")), 2)

    def test_a_rubric_is_the_first_note(self):
        """As the compiler keeps a true scope's rubric only when its first note is one."""
        main = _render('<j:conditional xml:id="a"><tei:note type="commentary">c</tei:note>'
                       '<tei:note type="instruction">Say:</tei:note><tei:fs type="t:x">'
                       '<tei:f name="a"><tei:binary value="true"/></tei:f></tei:fs></j:conditional>'
                       '<tei:p>x</tei:p><j:endConditional target="#a"/>')
        opener = main.xpath("//*[contains(@class, 'cm-open')]", namespaces=NS)[0]
        self.assertIn("cm-norubric", _classes(opener))


class TestCss(unittest.TestCase):

    def setUp(self):
        # Whether this machine has the fonts named is not what these tests are about.
        fontconfig = patch.object(typography_module, "_installed_font_families", return_value=None)
        fontconfig.start()
        self.addCleanup(fontconfig.stop)

    def test_font_chains(self):
        css = typography_css(TypographyConfig.model_validate(
            {"fonts": {"hebrew": ["Ezra SIL", 'Odd "Name"']}}))
        self.assertIn('--font-hebrew: "Ezra SIL", "Odd \\"Name\\"", serif;', css)

    def test_lengths_css_lacks_are_converted(self):
        css = typography_css(TypographyConfig.model_validate(
            {"markers": {"conditional": {"rule_thickness": "2bp"}}}))
        self.assertIn("--cond-rule-thickness: 2.0075pt;", css)

    def test_hidden_numbers(self):
        css = typography_css(TypographyConfig.model_validate(
            {"markers": {"verse_numbers": "hidden"}}))
        self.assertIn(".v { display: none; }", css)
        self.assertNotIn(".ch { display: none; }", css)


class TestSettingsCatalogue(unittest.TestCase):
    """Which settings reach the top of a book's panel, decided when it is built."""

    CONTROLS = [
        {"id": "both", "label": "Both", "features": [["t:x", "a"], ["t:x", "b"]],
         "options": [{"label": "On", "set": {"t:x": {"a": True, "b": True}}}]},
        {"id": "unread", "label": "Unread", "features": [["t:y", "z"]],
         "options": [{"label": "On", "set": {"t:y": {"z": True}}}]},
    ]

    @staticmethod
    def _book(chars: dict[str, int]) -> BookConditions:
        """One scope per feature, each reading its feature as true."""
        features = [Feature("t:x", name, [True], cids=[i]) for i, name in enumerate(chars)]
        expressions = [{"cond": {"fs": "t:x", "f": [{"name": name, "v": True}]}, "pinned": {}}
                       for name in chars]
        book = BookConditions(expressions=expressions, scopes=list(range(len(chars))),
                              features=features, scope_chars=list(chars.values()))
        book.conditional_chars = sum(book.scope_chars)
        return book

    @staticmethod
    def _names(entries):
        return [entry.get("label") or entry["name"] for entry in entries]

    def test_a_control_takes_the_text_of_all_its_features(self):
        book = self._book({"a": 30, "b": 30, "c": 50})
        self.assertEqual(self._names(settings_catalogue(book, self.CONTROLS)), ["Both", "c"])

    def test_a_feature_a_control_covers_is_not_offered_alone(self):
        book = self._book({"a": 10, "c": 50})
        self.assertNotIn("a", self._names(settings_catalogue(book, self.CONTROLS)))

    def test_a_control_the_book_has_no_use_for_is_left_out(self):
        book = self._book({"c": 50})
        self.assertEqual(self._names(settings_catalogue(book, self.CONTROLS)), ["c"])

    def test_at_most_six(self):
        book = self._book({name: 10 for name in "cdefghij"})
        self.assertEqual(len(settings_catalogue(book, [])), 6)

    def test_options_that_change_nothing_are_dropped(self):
        controls = [{"id": "c", "label": "C", "features": [["t:x", "a"], ["t:y", "z"]],
                     "options": [{"label": "Useful", "set": {"t:x": {"a": False}}},
                                 {"label": "Idle", "set": {"t:y": {"z": True}}}]}]
        entry = settings_catalogue(self._book({"a": 10}), controls)[0]
        self.assertEqual([option["label"] for option in entry["options"]], ["Useful"])

    def test_a_control_with_nothing_useful_is_dropped(self):
        controls = [{"id": "c", "label": "C", "features": [["t:x", "a"]],
                     "options": [{"label": "Idle", "set": {"t:y": {"z": True}}}]}]
        self.assertEqual(self._names(settings_catalogue(self._book({"a": 10}), controls)), ["a"])

    def test_the_books_default_is_still_an_option(self):
        """An option that repeats the book's default stays, so the reader can name it."""
        controls = [{"id": "c", "label": "C", "features": [["t:x", "a"]],
                     "options": [{"label": "Default", "set": {"t:x": {"a": True}}},
                                 {"label": "Other", "set": {"t:x": {"a": False}}}]}]
        entry = settings_catalogue(self._book({"a": 10}), controls)[0]
        self.assertEqual([option["label"] for option in entry["options"]], ["Default", "Other"])

    def test_too_little_text_stays_in_advanced(self):
        book = self._book({"c": 1000, "d": 9})
        self.assertEqual(self._names(settings_catalogue(book, [])), ["c"])


class TestBasicSettingsSpec(unittest.TestCase):
    """basic_settings.yaml names features the compiler really produces."""

    @classmethod
    def setUpClass(cls):
        reset_linear_data()
        linear_data = get_linear_data()
        CompilerProcessor.load_init_settings(linear_data, yaml_to_declaration_entries({
            "opensiddur:gregorian-date": {"year": 2026, "month": 4, "day": 6},
            "opensiddur:location": {"latitude": 31.78, "longitude": 35.22},
            "opensiddur:time": {"hour": 9, "minute": 0}}))
        cls.calendar = {(e.fs_type, e.feature_name) for e in linear_data.conditional_settings}
        cls.calendar |= {(fs, name) for fs, features in STATIC_DEFAULTS.items() for name in features}
        reset_linear_data()

    def _check(self, fs, name):
        if not is_reader_supplied(fs) or fs in STATIC_DEFAULTS:
            self.assertIn((fs, name), self.calendar, f"{fs} {name} is not a feature the compiler sets")
        self.assertRegex(fs, r"^[a-z]+:[a-z-]+$")

    def test_controls(self):
        controls = basic_controls()
        self.assertEqual(len({c["id"] for c in controls}), len(controls))
        for control in controls:
            with self.subTest(control=control["id"]):
                self.assertTrue(control["options"])
                for option in control["options"]:
                    for fs, features in option["set"].items():
                        for name, value in features.items():
                            self._check(fs, name)
                            self.assertIsInstance(value, (bool, int, str))

    def test_feature_words(self):
        for (fs, name), words in feature_words().items():
            with self.subTest(feature=(fs, name)):
                self._check(fs, name)
                self.assertTrue(words["label"])


SETTINGS = """\
book:
  project: proj
  file_name: index.xml
  title: The Settings Title
priority:
  transclusion: [proj]
typography:
  markers:
    conditional:
      inline_open: "⟨"
      inline_close: "⟩"
declarations:
  opensiddur:override:
    wedding: true
  opensiddur:israel:
    is-israel: true
"""

INDEX = f"""<tei:TEI xmlns:tei="{TEI_NS}" xml:lang="en"><tei:teiHeader><tei:fileDesc>
  <tei:titleStmt><tei:title>I</tei:title><tei:respStmt><tei:resp key="trc">Transcribed by</tei:resp>
  <tei:name ref="urn:x-opensiddur:contributor:opensiddur.org/some-one">Some One</tei:name>
  </tei:respStmt></tei:titleStmt>
  <tei:publicationStmt><tei:availability><tei:licence target="http://creativecommons.org/publicdomain/zero/1.0/">CC0</tei:licence>
  </tei:availability></tei:publicationStmt></tei:fileDesc></tei:teiHeader>
  <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text></tei:TEI>"""

BODY = (
    _cond("a", "wedding", rubric="At a wedding:") + "<tei:p>wedding words</tei:p>"
    "<j:endConditional target=\"#a\"/>"
    + _cond("b", "wedding", value="false") + "<tei:p>ordinary words</tei:p>"
    "<j:endConditional target=\"#b\"/>"
    + _cond("c", "minyan", fs="opensiddur:quorum") + "<tei:p>minyan words</tei:p>"
    "<j:endConditional target=\"#c\"/>"
    + '<j:conditional xml:id="d"><tei:fs type="t:x"><tei:f name="s"><tei:string>&lt;/script&gt;'
      '</tei:string></tei:f></tei:fs></j:conditional><tei:p>odd</tei:p>'
      '<j:endConditional target="#d"/>'
    + "<tei:p>" + _cond("e", "wedding") + "inline<j:endConditional target=\"#e\"/></tei:p>"
)


class TestBuildBook(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        (self.base / "proj").mkdir()
        (self.base / "proj" / "index.xml").write_text(INDEX, encoding="utf-8")
        self.settings = self.base / "settings.yaml"
        self.settings.write_text(SETTINGS, encoding="utf-8")
        self.compiled = self.base / "compiled.xml"

    def _build(self, *, electronic=True, settings=True) -> str:
        self.compiled.write_bytes(_compiled(BODY, electronic=electronic))
        return build_book(self.compiled, self.settings if settings else None, self.base)

    @staticmethod
    def _between(page: str, start: str, end: str) -> str:
        return page.split(start, 1)[1].split(end, 1)[0]

    def _book(self, page: str) -> dict:
        return json.loads(self._between(page, '<script type="application/json" id="os-book">',
                                        "</script>"))

    def test_page_is_self_contained(self):
        page = self._build()
        self.assertNotRegex(page, r'<(script|link)[^>]*\b(src|href)=')
        self.assertIn("OSCond", page)
        self.assertIn('<main xmlns="http://www.w3.org/1999/xhtml" class="os-book"', page)

    def test_title_from_the_settings(self):
        self.assertIn("<title>The Settings Title</title>", self._build())

    def test_title_from_the_header_without_settings(self):
        self.assertIn("<title>Header Title</title>", self._build(settings=False))

    def test_defaults_are_the_readers_declarations_and_static_defaults(self):
        defaults = self._book(self._build())["defaults"]
        self.assertIs(defaults["opensiddur:override"]["wedding"], True)
        self.assertIs(defaults["opensiddur:override"]["brit-milah"], False)
        self.assertNotIn("opensiddur:israel", defaults)

    def test_without_scripts_the_page_is_the_printed_book(self):
        """The settings file says it is a wedding: the not-a-wedding passage is hidden, the
        wedding passage keeps its rubric and drops its rule, and the minyan is undecided."""
        page = self._build()
        css = self._between(page, '<style id="os-cond-default">', "</style>").strip()
        self.assertEqual(css.splitlines(), [
            ".c1,.m1{display:none}",
            ".m0.cm-close,.m0.cm-norubric,.m0 .cm-br,.m4.cm-close,.m4.cm-norubric,.m4 .cm-br"
            "{display:none}",
        ])

    def test_the_panel_is_decided_when_the_book_is_built(self):
        spec = self.base / "basic.yaml"
        spec.write_text(
            "controls:\n"
            "  - id: celebration\n"
            "    label: Celebration\n"
            "    note: A note.\n"
            "    options:\n"
            "      - {label: A wedding, set: {opensiddur:override: {wedding: true}}}\n"
            "      - {label: No wedding, set: {opensiddur:override: {wedding: false}}}\n"
            "features:\n"
            "  opensiddur:quorum:\n"
            "    minyan: {label: Ten present, values: {true: Yes, false: No}}\n",
            encoding="utf-8")
        self.compiled.write_bytes(_compiled(BODY))
        book = self._book(build_book(self.compiled, self.settings, self.base, spec))
        minyan = next(f for f in book["features"] if f["name"] == "minyan")
        self.assertEqual((minyan["kind"], minyan["calendar"], minyan["label"]),
                         ("binary", False, "Ten present"))
        self.assertEqual(
            [(e["type"], e.get("label") or e.get("name")) for e in book["basic"]],
            [("control", "Celebration"), ("feature", "minyan"), ("feature", "s")])
        celebration = book["basic"][0]
        self.assertEqual(celebration["note"], "A note.")
        self.assertEqual([o["label"] for o in celebration["options"]], ["A wedding", "No wedding"])

    def test_script_text_cannot_close_the_script(self):
        page = self._build()
        data = self._between(page, '<script type="application/json" id="os-book">', "</script>")
        self.assertNotIn("<", data)
        self.assertIn("\\u003c/script>", data)
        self.assertEqual(self._book(page)["expressions"][3]["cond"]["f"][0]["v"], "</script>")

    def test_bracket_settings_reach_the_text(self):
        self.assertRegex(self._build(), r'<span class="cm-br" aria-hidden="true">⟨</span>')

    def test_colophon(self):
        page = self._build()
        about = self._between(page, '<footer class="os-about">', "</footer>")
        self.assertIn("Some One", about)
        self.assertIn('href="http://creativecommons.org/publicdomain/zero/1.0/"', about)

    def test_book_id_is_stable(self):
        self.assertEqual(self._book(self._build())["id"], self._book(self._build())["id"])

    def test_a_print_compile_is_warned_about(self):
        with self.assertLogs("opensiddur.exporter.html.html", level="WARNING") as logs:
            self._build(electronic=False)
        self.assertIn("--destination electronic", logs.output[0])

    def test_the_device_writes_the_same_rules(self):
        node = require_node(self)
        page = self._build()
        book = self._book(page)
        css = self._between(page, '<style id="os-cond-default">', "</style>").strip()
        result = run_js(node, "return OSCond.scopeCss(args, {}, args.defaults);", book)
        self.assertEqual(result["css"].strip(), css)

    def test_the_device_follows_the_reader(self):
        node = require_node(self)
        book = self._book(self._build())
        result = run_js(
            node,
            "return OSCond.scopeCss(args, {'opensiddur:quorum': {minyan: false},"
            " 'opensiddur:override': {wedding: false}}, args.defaults).css;",
            book)
        hidden = re.findall(r"^(.*)\{display:none\}$", result, re.MULTILINE)[0].split(",")
        self.assertEqual(sorted(hidden), [".c0", ".c2", ".c4", ".m0", ".m2", ".m4"])


if __name__ == "__main__":
    unittest.main()
