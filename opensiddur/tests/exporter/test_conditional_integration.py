"""Integration tests for j:conditional compilation."""

import re
import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor, join_split_paragraphs
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.linear import get_linear_data, reset_linear_data

TEI = TEI_NS
J = JLPTEI_NAMESPACE

MINIMAL_XML = b'<root xmlns:tei="http://www.tei-c.org/ns/1.0"/>'


def _text_xml(body: str) -> bytes:
    return f'''<root xmlns:tei="{TEI}" xmlns:j="{J}">
    <tei:text>
        {body}
    </tei:text>
</root>'''.encode()


class TestConditionalIntegration(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _write(self, name: str, body: str) -> str:
        path = self.project_dir / name
        path.write_bytes(_text_xml(body))
        return name

    def _compile(self, filename: str) -> str:
        proc = CompilerProcessor("test_project", filename)
        result = proc.process()
        return etree.tostring(result, encoding="unicode")

    def test_true_includes_content_strips_markers(self):
        fn = self._write(
            "true.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>included</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        out = self._compile(fn)
        self.assertIn("included", out)
        self.assertNotIn("conditional", out)
        self.assertNotIn("endConditional", out)

    def test_fractional_coordinates_declare_and_derive(self):
        """Coordinates are not whole degrees; the parser must accept a fractional @value."""
        fn = self._write(
            "coords.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="opensiddur:location">
                    <tei:f name="latitude"><tei:numeric value="40.71"/></tei:f>
                    <tei:f name="longitude"><tei:numeric value="-74.01"/></tei:f>
                </tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="opensiddur:israel">
                    <tei:f name="is-israel"><tei:binary value="false"/></tei:f>
                </tei:fs>
            </j:conditional>
            <tei:p>diaspora</tei:p>
            <j:endConditional target="#c"/>
            <j:conditional xml:id="c2">
                <tei:fs type="opensiddur:location">
                    <tei:f name="latitude"><tei:numeric value="40.71"/></tei:f>
                </tei:fs>
            </j:conditional>
            <tei:p>new-york</tei:p>
            <j:endConditional target="#c2"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        out = self._compile(fn)
        self.assertIn("diaspora", out)
        self.assertIn("new-york", out)

    def test_fractional_coordinates_place_a_location_in_israel(self):
        """One degree of latitude can move a location across the Israel/diaspora boundary."""
        fn = self._write(
            "jerusalem.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="opensiddur:location">
                    <tei:f name="latitude"><tei:numeric value="31.78"/></tei:f>
                    <tei:f name="longitude"><tei:numeric value="35.22"/></tei:f>
                </tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="opensiddur:israel">
                    <tei:f name="is-israel"><tei:binary value="true"/></tei:f>
                </tei:fs>
            </j:conditional>
            <tei:p>israel</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        self.assertIn("israel", self._compile(fn))

    def test_false_excludes_content_strips_markers(self):
        fn = self._write(
            "false.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="false"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>excluded</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        out = self._compile(fn)
        self.assertNotIn("excluded", out)
        self.assertNotIn("conditional", out)

    def test_undefined_includes_content_and_markers(self):
        fn = self._write(
            "undef.xml",
            '''
            <j:conditional xml:id="c">
                <tei:note type="instruction">Choose one</tei:note>
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>maybe</tei:p>
            <j:endConditional target="#c"/>
            ''',
        )
        out = self._compile(fn)
        self.assertIn("maybe", out)
        self.assertIn("Choose one", out)
        self.assertIn("conditional", out)
        self.assertIn("endConditional", out)

    def _noted(self, name: str, value: str) -> str:
        return self._write(
            name,
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="%s"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:note type="instruction">Say this here</tei:note>
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>the passage</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''' % value,
        )

    def test_true_keeps_the_instruction_note(self):
        # The instruction outlives the condition that carried it: it is the rubric the
        # edition prints over the passage, so it is set wherever the passage is.
        out = self._compile(self._noted("note_true.xml", "true"))
        self.assertIn("the passage", out)
        self.assertIn("Say this here", out)

    def test_false_takes_the_instruction_note_with_it(self):
        # Nothing is said here at all, so nothing tells the reader to say it.
        out = self._compile(self._noted("note_false.xml", "false"))
        self.assertNotIn("the passage", out)
        self.assertNotIn("Say this here", out)

    def _split(self, name: str, value: str) -> str:
        return self._write(
            name,
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="%s"/></tei:f></tei:fs>
            </j:declare>
            <tei:div><tei:p>before</tei:p></tei:div>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:div corresp="urn:x-opensiddur:text:prayer:x"><tei:p>inserted</tei:p></tei:div>
            <j:endConditional target="#c"/>
            <tei:div><tei:p>after</tei:p></tei:div>
            <j:endDeclare target="#d"/>
            ''' % value,
        )

    def _joined(self, name: str, value: str) -> str:
        proc = CompilerProcessor("test_project", self._split(name, value))
        result = proc.process()
        join_split_paragraphs(result)
        return re.sub(r"\s+", " ", etree.tostring(result, encoding="unicode"))

    def test_a_false_scope_leaves_no_paragraph_split(self):
        # A conditional between two runs of words forces each into a division of its own,
        # a division not being able to hold words and subdivisions side by side. When the
        # condition goes, what the edition prints as one paragraph must not stay as two.
        out = self._joined("split_false.xml", "false")
        self.assertNotIn("inserted", out)
        self.assertIn("before after", out)

    def test_a_true_scope_keeps_the_divisions_apart(self):
        # Nothing has gone, so nothing closes up: the inserted passage still divides them.
        out = self._joined("split_true.xml", "true")
        self.assertIn("inserted", out)
        self.assertNotIn("before after", out)

    def test_a_named_division_is_never_joined(self):
        # One unnamed division carries no address, so nothing refers to it and nothing is
        # lost by its going. A division the source named keeps its own paragraph.
        self.assertIn("urn:x-opensiddur:text:prayer:x",
                      self._joined("split_true.xml", "true"))

    def test_declare_inside_false_conditional_still_updates_stack(self):
        fn = self._write(
            "declare_in_false.xml",
            '''
            <j:declare xml:id="outer">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="false"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <j:declare xml:id="inner">
                <tei:fs type="t:fs"><tei:f name="y"><tei:binary value="true"/></tei:f></tei:fs>
            </j:declare>
            <tei:p>hidden</tei:p>
            <j:endDeclare target="#inner"/>
            <j:endConditional target="#c"/>
            <j:conditional xml:id="after">
                <tei:fs type="t:fs"><tei:f name="y"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>visible</tei:p>
            <j:endConditional target="#after"/>
            <j:endDeclare target="#outer"/>
            ''',
        )
        out = self._compile(fn)
        self.assertNotIn("hidden", out)
        self.assertIn("visible", out)

    def test_nested_false_inside_true(self):
        fn = self._write(
            "nested.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="outer"><tei:binary value="true"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="outer_c">
                <tei:fs type="t:fs"><tei:f name="outer"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>outer</tei:p>
            <j:conditional xml:id="inner_c">
                <tei:fs type="t:fs"><tei:f name="inner"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>inner hidden</tei:p>
            <j:endConditional target="#inner_c"/>
            <j:endConditional target="#outer_c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        CompilerProcessor.load_init_settings(
            get_linear_data(),
            yaml_to_declaration_entries({"t:fs": {"inner": False}}),
        )
        out = self._compile(fn)
        self.assertIn("outer", out)
        self.assertNotIn("inner hidden", out)

    def test_checkpoint_clears_scope_stack(self):
        fn = self._write(
            "scope.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>x</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        proc = CompilerProcessor("test_project", fn)
        proc.process()
        self.assertEqual(proc.linear_data.conditional_scope_stack, [])


class TestInlineConditionalTails(unittest.TestCase):
    """Text around a mid-paragraph conditional lives in the markers' tails.

    The markers are stripped from the output, so unless their tails are carried over the
    running text around them disappears — the words on either side of the conditional, not
    just the conditional text itself.
    """

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _compile_paragraph(self, declared: str) -> str:
        """Compile 'before |conditional| after' with the setting declared as given."""
        body = f'''
            {declared}
            <tei:p>before <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>conditional<j:endConditional target="#c"/> after</tei:p>
        '''
        path = self.project_dir / "inline.xml"
        path.write_bytes(_text_xml(body))
        proc = CompilerProcessor("test_project", "inline.xml")
        return etree.tostring(proc.process(), encoding="unicode")

    @staticmethod
    def _declare(value: str) -> str:
        return f'''<j:declare xml:id="d">
            <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="{value}"/></tei:f></tei:fs>
        </j:declare>'''

    def test_true_keeps_surrounding_text_and_conditional_text(self):
        out = self._compile_paragraph(self._declare("true"))
        self.assertIn("before ", out)
        self.assertIn("conditional", out)
        self.assertIn(" after", out)

    def test_false_drops_only_the_conditional_text(self):
        out = self._compile_paragraph(self._declare("false"))
        self.assertIn("before ", out)
        self.assertIn(" after", out)
        self.assertNotIn(">conditional", out)
        self.assertNotIn("conditional<", out)

    def test_undefined_retains_markers_and_all_text(self):
        out = self._compile_paragraph("")
        self.assertIn("before ", out)
        self.assertIn("conditional", out)
        self.assertIn(" after", out)
        self.assertIn("conditional", out)
        self.assertIn("endConditional", out)

    def test_false_scope_spanning_paragraphs_keeps_text_after_the_end(self):
        body = f'''
            {self._declare("false")}
            <tei:p>kept before</tei:p>
            <j:conditional xml:id="c">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>dropped</tei:p>
            <j:endConditional target="#c"/>
            <tei:p>kept after</tei:p>
        '''
        path = self.project_dir / "block.xml"
        path.write_bytes(_text_xml(body))
        proc = CompilerProcessor("test_project", "block.xml")
        out = etree.tostring(proc.process(), encoding="unicode")
        self.assertIn("kept before", out)
        self.assertIn("kept after", out)
        self.assertNotIn("dropped", out)


class TestRiteConditions(unittest.TestCase):
    """The opensiddur:rite feature structure, as used by haftarah rite variants.

    Rites are one independently settable binary feature each rather than a single
    enumerated value, so that a comparative edition can select several at once and get
    every selected variant. See schema/JLPTEI-3.md, "Rite".
    """

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _variant(self, rite: str, heading: str, text: str) -> str:
        return f'''
            <j:conditional xml:id="rite_{rite}">
                <tei:fs type="opensiddur:rite">
                    <tei:f name="{rite}"><tei:binary value="true"/></tei:f>
                </tei:fs>
            </j:conditional>
            <tei:div><tei:head>{heading}</tei:head><tei:p>{text}</tei:p></tei:div>
            <j:endConditional target="#rite_{rite}"/>
        '''

    def _compile_with_rites(self, **rites: bool) -> str:
        """Write a haftarah with three rite variants and compile it under the given rites."""
        body = (
            self._variant("ashkenaz", "מנהג אשכנז", "ashkenazi haftarah")
            + self._variant("sepharad", "מנהג ספרד", "sephardi haftarah")
            + self._variant("teimani_baladi", "מנהג תימן בלדי", "teimani haftarah")
        )
        path = self.project_dir / "haftarah.xml"
        path.write_bytes(_text_xml(body))
        if rites:
            CompilerProcessor.load_init_settings(
                get_linear_data(),
                yaml_to_declaration_entries({"opensiddur:rite": dict(rites)}),
            )
        return etree.tostring(
            CompilerProcessor("test_project", "haftarah.xml").process(), encoding="unicode"
        )

    def test_unset_rite_keeps_every_variant_with_its_heading(self):
        """The default for a printed humash: no rite chosen, so all variants stay.

        An undefined feature evaluates to UNDEFINED rather than false, which keeps the
        passage together with the heading that says whose custom it is.
        """
        out = self._compile_with_rites()
        for text in ("ashkenazi haftarah", "sephardi haftarah", "teimani haftarah"):
            self.assertIn(text, out)
        for heading in ("מנהג אשכנז", "מנהג ספרד", "מנהג תימן בלדי"):
            self.assertIn(heading, out)

    def test_single_rite_selects_only_that_variant(self):
        out = self._compile_with_rites(ashkenaz=True, sepharad=False, teimani_baladi=False)
        self.assertIn("ashkenazi haftarah", out)
        self.assertNotIn("sephardi haftarah", out)
        self.assertNotIn("teimani haftarah", out)

    def test_two_rites_true_at_once_keep_both_variants(self):
        """The reason rites are per-rite binaries: a comparative edition wants several."""
        out = self._compile_with_rites(ashkenaz=True, sepharad=False, teimani_baladi=True)
        self.assertIn("ashkenazi haftarah", out)
        self.assertIn("teimani haftarah", out)
        self.assertNotIn("sephardi haftarah", out)

    def test_unlisted_rite_name_is_accepted(self):
        """The rite list is open: a rite absent from the documented set still works."""
        path = self.project_dir / "romaniote.xml"
        path.write_bytes(_text_xml(self._variant("romaniote", "מנהג רומניוט", "romaniote haftarah")))
        CompilerProcessor.load_init_settings(
            get_linear_data(),
            yaml_to_declaration_entries({"opensiddur:rite": {"romaniote": True}}),
        )
        out = etree.tostring(
            CompilerProcessor("test_project", "romaniote.xml").process(), encoding="unicode"
        )
        self.assertIn("romaniote haftarah", out)


if __name__ == "__main__":
    unittest.main()
