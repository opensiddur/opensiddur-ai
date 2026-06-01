"""Tests for conditional setting declaration tracking."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_settings import (
    INIT_DECLARE_ID,
    yaml_to_declaration_entries,
    parse_declare_element,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import (
    ConditionalSettingEntry,
    NumericValue,
    Undefined,
    get_linear_data,
    reset_linear_data,
)
from opensiddur.exporter.settings import load_settings

TEI = TEI_NS
J = JLPTEI_NAMESPACE

MINIMAL_XML = b'<root xmlns:tei="http://www.tei-c.org/ns/1.0"/>'


def _declare_xml(body: str) -> bytes:
    return f'''<root xmlns:tei="{TEI}" xmlns:j="{J}">
    <tei:text>
        {body}
    </tei:text>
</root>'''.encode()


class TestParseConditionalSettings(unittest.TestCase):
    """Unit tests for tei:fs parsing and value types."""

    def _parse_fs(self, fs_inner: str, declare_id: str = "d1") -> list[ConditionalSettingEntry]:
        xml = f'<j:declare xmlns:tei="{TEI}" xmlns:j="{J}" xml:id="x"><tei:fs type="opensiddur:holiday">{fs_inner}</tei:fs></j:declare>'
        el = etree.fromstring(xml.encode())
        return parse_declare_element(el, declare_id)

    def test_numeric_and_binary(self):
        entries = self._parse_fs(
            '<tei:f name="pesah"><tei:numeric value="8"/></tei:f>'
            '<tei:f name="omit"><tei:binary value="true"/></tei:f>'
        )
        self.assertEqual(len(entries), 2)
        self.assertIsInstance(entries[0].value, NumericValue)
        self.assertEqual(entries[0].value.value, 8)
        self.assertEqual(entries[1].value, True)

    def test_numeric_with_max(self):
        entries = self._parse_fs('<tei:f name="n"><tei:numeric value="1" max="5"/></tei:f>')
        self.assertEqual(entries[0].value.max_value, 5)

    def test_string(self):
        entries = self._parse_fs('<tei:f name="label"><tei:string>hello</tei:string></tei:f>')
        self.assertEqual(entries[0].value, "hello")

    def test_symbol_non_undefined_as_string(self):
        entries = self._parse_fs('<tei:f name="x"><tei:symbol value="foo"/></tei:f>')
        self.assertEqual(entries[0].value, "foo")

    def test_symbol_undefined_and_default(self):
        for inner in ('<tei:symbol value="undefined"/>', '<tei:default/>'):
            entries = self._parse_fs(f'<tei:f name="x">{inner}</tei:f>')
            self.assertIs(entries[0].value, Undefined)


class TestStackOperations(unittest.TestCase):
    """Unit tests for push/end_declare, lookup, and dependency index."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base
        (self.project_dir / "minimal.xml").write_bytes(MINIMAL_XML)
        self.proc = CompilerProcessor("test_project", "minimal.xml")

    def _entry(self, declare_id: str, fs_type: str, feature: str, value, source: str = "declared"):
        return ConditionalSettingEntry(
            declare_id=declare_id,
            fs_type=fs_type,
            feature_name=feature,
            value=value,
            source=source,
        )

    def test_push_and_end_declare(self):
        self.proc._push_declare("A", [self._entry("A", "opensiddur:holiday", "pesah", 0)])
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "pesah"), 0)
        self.proc._end_declare("A")
        self.assertIsNone(self.proc.get_active_setting("opensiddur:holiday", "pesah"))

    def test_cross_boundary_end(self):
        self.proc._push_declare("A", [self._entry("A", "opensiddur:holiday", "pesah", 0)])
        self.proc._push_declare("B", [self._entry("B", "opensiddur:holiday", "rosh-hashana", 2)])
        self.proc._end_declare("A")
        self.assertIsNone(self.proc.get_active_setting("opensiddur:holiday", "pesah"))
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "rosh-hashana"), 2)

    def test_partial_fs_redeclare(self):
        self.proc._push_declare(
            "D1",
            [
                self._entry("D1", "opensiddur:holiday", "pesah", 0),
                self._entry("D1", "opensiddur:holiday", "omer", 10),
            ],
        )
        self.proc._push_declare("D2", [self._entry("D2", "opensiddur:holiday", "pesah", 8)])
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "pesah"), 8)
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "omer"), 10)
        self.proc._end_declare("D2")
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "pesah"), 0)
        self.assertEqual(self.proc.get_active_setting("opensiddur:holiday", "omer"), 10)

    def test_get_active_fs_settings_merged(self):
        self.proc._push_declare(
            "D1",
            [
                self._entry("D1", "t:fs", "a", 1),
                self._entry("D1", "t:fs", "b", 2),
            ],
        )
        self.proc._push_declare("D2", [self._entry("D2", "t:fs", "a", 9)])
        self.assertEqual(self.proc.get_active_fs_settings("t:fs"), {"a": 9, "b": 2})

    def test_end_declare_missing_raises(self):
        with self.assertRaises(ValueError):
            self.proc._end_declare("nonexistent")

    @patch("opensiddur.exporter.compiler.recalculate_derived_settings")
    def test_push_and_end_call_derivation_hook(self, mock_recalc):
        from opensiddur.exporter.derived_settings import SettingChangeTrigger

        self.proc._push_declare("A", [self._entry("A", "t:fs", "x", 1)])
        mock_recalc.assert_called_with(
            self.proc.linear_data, trigger=SettingChangeTrigger.DECLARE, declare_id="A"
        )
        self.proc._end_declare("A")
        mock_recalc.assert_called_with(
            self.proc.linear_data, trigger=SettingChangeTrigger.END_DECLARE, declare_id="A"
        )

    def test_derived_contributor_removal_and_index(self):
        derived = ConditionalSettingEntry(
            declare_id="__derived__1",
            fs_type="opensiddur:holiday",
            feature_name="rosh-hashana",
            value=1,
            source="derived",
            contributors={"A", INIT_DECLARE_ID},
        )
        self.proc._register_derived_entry(derived)
        self.assertIn(0, self.proc.linear_data.derived_dependency_index["A"])
        self.proc._remove_derived_entries_for_contributor("A")
        self.assertEqual(len(self.proc.linear_data.conditional_settings), 0)
        self.assertEqual(self.proc.linear_data.derived_dependency_index, {})

    def test_checkpoint_truncation_rebuilds_index(self):
        with self.proc._conditional_settings_checkpoint():
            self.proc._register_derived_entry(
                ConditionalSettingEntry(
                    declare_id="__derived__1",
                    fs_type="t",
                    feature_name="f",
                    value=1,
                    source="derived",
                    contributors={"X"},
                ),
            )
            self.proc._push_declare("file", [self._entry("file", "t", "f", 2)])
        self.assertEqual(len(self.proc.linear_data.conditional_settings), 0)
        self.assertEqual(self.proc.linear_data.derived_dependency_index, {})


class TestYamlDeclarations(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_dir = Path(self.temp_dir.name)
        (self.project_dir / "proj-a").mkdir()
        (self.project_dir / "proj-a" / "minimal.xml").write_bytes(MINIMAL_XML)

    def test_yaml_declarations_load(self):
        path = Path(self.temp_dir.name) / "settings.yaml"
        with open(path, "w") as f:
            yaml.dump({
                "priority": {"transclusion": ["proj-a"], "instructions": ["proj-a"]},
                "declarations": {
                    "opensiddur:gregorian-date": {"year": 2024, "month": 10},
                },
            }, f)
        load_settings(path, project_directory=self.project_dir)
        proc = CompilerProcessor("proj-a", "minimal.xml")
        self.assertEqual(len(proc.linear_data.conditional_settings), 2)
        self.assertEqual(proc.linear_data.conditional_settings[0].source, "init")
        self.assertEqual(proc.get_active_setting("opensiddur:gregorian-date", "year"), 2024)

    def test_yaml_null_is_undefined(self):
        entries = yaml_to_declaration_entries({"t:fs": {"f": None}})
        self.assertIs(entries[0].value, Undefined)


class TestCompilerDeclareIntegration(unittest.TestCase):
    """Integration tests with CompilerProcessor and transclusion."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _write(self, name: str, content: str) -> tuple[str, str]:
        path = self.project_dir / name
        path.write_bytes(content.encode())
        return "test_project", name

    def test_declare_stripped_from_output(self):
        body = '''
        <j:declare xml:id="s">
            <tei:fs type="opensiddur:holiday">
                <tei:f name="pesah"><tei:numeric value="0"/></tei:f>
            </tei:fs>
        </j:declare>
        <tei:p>content</tei:p>
        <j:endDeclare target="#s"/>
        '''
        _, fn = self._write("d.xml", _declare_xml(body).decode())
        proc = CompilerProcessor("test_project", fn)
        result = proc.process()
        out = etree.tostring(result, encoding="unicode")
        self.assertNotIn("declare", out)
        self.assertNotIn("endDeclare", out)
        self.assertIn("content", out)

    def test_declare_scope_during_process(self):
        body = '''
        <j:declare xml:id="s">
            <tei:fs type="opensiddur:holiday">
                <tei:f name="pesah"><tei:numeric value="8"/></tei:f>
            </tei:fs>
        </j:declare>
        <j:endDeclare target="#s"/>
        '''
        _, fn = self._write("d.xml", _declare_xml(body).decode())
        proc = CompilerProcessor("test_project", fn)
        proc.process()
        self.assertIsNone(proc.get_active_setting("opensiddur:holiday", "pesah"))

    def test_init_survives_checkpoint_xml_does_not(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(),
            yaml_to_declaration_entries({"opensiddur:holiday": {"pesah": 0}}),
        )
        body = '''
        <j:declare xml:id="s">
            <tei:fs type="opensiddur:holiday">
                <tei:f name="pesah"><tei:numeric value="8"/></tei:f>
            </tei:fs>
        </j:declare>
        <j:endDeclare target="#s"/>
        '''
        _, fn = self._write("d.xml", _declare_xml(body).decode())
        proc = CompilerProcessor("test_project", fn)
        proc.process()
        self.assertEqual(proc.get_active_setting("opensiddur:holiday", "pesah"), 0)

    def test_scoped_declare_id_differs_by_path(self):
        xml_id = "setting_start"
        body = f'''
        <j:declare xml:id="{xml_id}">
            <tei:fs type="t:fs"><tei:f name="x"><tei:numeric value="1"/></tei:f></tei:fs>
        </j:declare>
        '''
        _, fn = self._write("inner.xml", _declare_xml(body).decode())

        proc = CompilerProcessor("test_project", fn)
        declare_el = proc.root_tree.find(f".//{{{J}}}declare")
        self.assertIsNotNone(declare_el)

        id_at_depth_0 = proc._scoped_declare_id(xml_id, declare_el)

        proc.linear_data.processing_context.append({
            "project": "other_project",
            "file_name": "other.xml",
        })
        id_at_depth_1 = proc._scoped_declare_id(xml_id, declare_el)
        proc.linear_data.processing_context.pop()

        self.assertNotEqual(id_at_depth_0, id_at_depth_1)


class TestExternalCompilerDeclareIntegration(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        self.project_dir = self.base / "test_project"
        self.project_dir.mkdir(parents=True)
        get_linear_data().xml_cache.base_path = self.base

    def _write(self, name: str, content: str) -> None:
        (self.project_dir / name).write_bytes(content.encode())

    def test_file_rollback_on_process_return(self):
        body = '''
        <j:declare xml:id="s">
            <tei:fs type="t:fs"><tei:f name="x"><tei:numeric value="1"/></tei:f></tei:fs>
        </j:declare>
        <tei:p>text</tei:p>
        '''
        self._write("e.xml", _declare_xml(body).decode())
        proc = ExternalCompilerProcessor("test_project", "e.xml")
        proc.process()
        self.assertIsNone(proc.get_active_setting("t:fs", "x"))


if __name__ == "__main__":
    unittest.main()
