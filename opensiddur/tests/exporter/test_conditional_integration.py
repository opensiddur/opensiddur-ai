"""Integration tests for j:conditional compilation."""

import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor
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

    def test_true_excludes_instruction_note(self):
        fn = self._write(
            "note.xml",
            '''
            <j:declare xml:id="d">
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:declare>
            <j:conditional xml:id="c">
                <tei:note type="instruction">Should not appear</tei:note>
                <tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>
            </j:conditional>
            <tei:p>text</tei:p>
            <j:endConditional target="#c"/>
            <j:endDeclare target="#d"/>
            ''',
        )
        out = self._compile(fn)
        self.assertIn("text", out)
        self.assertNotIn("Should not appear", out)

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


if __name__ == "__main__":
    unittest.main()
