"""Compiling for an electronic book: the reader's settings are left for the reader's device.

`--destination electronic` (LinearData.defer_reader_settings) withholds the settings a reader
supplies -- from the settings file and from the static defaults -- so their conditions stay
undecided, and records on each retained conditional the values the compile did know.
"""

import json
import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor, main
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.client_settings import is_reader_supplied
from opensiddur.exporter.linear import get_linear_data, reset_linear_data
from opensiddur.exporter.settings import load_settings

J = JLPTEI_NAMESPACE
P = PROCESSING_NAMESPACE


def _document(body: str) -> bytes:
    return f'''<tei:TEI xmlns:tei="{TEI_NS}" xmlns:j="{J}" xml:lang="en">
  <tei:teiHeader><tei:fileDesc><tei:titleStmt><tei:title>T</tei:title></tei:titleStmt>
  </tei:fileDesc></tei:teiHeader>
  <tei:text><tei:body><tei:div>{body}</tei:div></tei:body></tei:text>
</tei:TEI>'''.encode()


OMIT_TAHANUN = '''
  <j:conditional xml:id="c"><tei:fs type="opensiddur:override">
    <tei:f name="omit-tahanun"><tei:binary value="true"/></tei:f></tei:fs></j:conditional>
  <tei:p>no tahanun today</tei:p>
  <j:endConditional target="#c"/>'''

MAARIV_SECTION = '''
  <j:declare xml:id="d"><tei:fs type="opensiddur:service-time">
    <tei:f name="maariv"><tei:binary value="true"/></tei:f></tei:fs></j:declare>
  <j:conditional xml:id="c"><j:any>
    <tei:fs type="opensiddur:recitation"><tei:f name="repetition"><tei:binary value="true"/></tei:f></tei:fs>
    <tei:fs type="opensiddur:quorum"><tei:f name="minyan"><tei:binary value="true"/></tei:f></tei:fs>
  </j:any></j:conditional>
  <tei:p>aloud, or in a minyan</tei:p>
  <j:endConditional target="#c"/>
  <j:endDeclare target="#d"/>'''


class _Compiling(unittest.TestCase):

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base = Path(self.temp_dir.name)
        (self.base / "proj").mkdir()
        get_linear_data().xml_cache.base_path = self.base

    def _compile(self, body: str, *, electronic: bool) -> etree.ElementBase:
        (self.base / "proj" / "doc.xml").write_bytes(_document(body))
        linear_data = get_linear_data()
        linear_data.defer_reader_settings = electronic
        CompilerProcessor.load_init_settings(linear_data, [])
        return CompilerProcessor("proj", "doc.xml").process()


class TestStaticDefaults(_Compiling):

    def test_print_compiles_the_static_default_in(self):
        root = self._compile(OMIT_TAHANUN, electronic=False)
        self.assertNotIn("no tahanun today", "".join(root.itertext()))
        self.assertIsNone(root.find(f".//{{{J}}}conditional"))

    def test_electronic_leaves_it_to_the_reader(self):
        root = self._compile(OMIT_TAHANUN, electronic=True)
        self.assertIn("no tahanun today", "".join(root.itertext()))
        self.assertIsNotNone(root.find(f".//{{{J}}}conditional"))
        self.assertIsNotNone(root.find(f".//{{{J}}}endConditional"))

    def test_calendar_settings_are_compiled_as_in_print(self):
        def stack(electronic):
            reset_linear_data()
            linear_data = get_linear_data()
            linear_data.defer_reader_settings = electronic
            CompilerProcessor.load_init_settings(linear_data, [])
            return {(e.fs_type, e.feature_name, repr(e.value))
                    for e in linear_data.conditional_settings}

        printed, electronic = stack(False), stack(True)
        self.assertEqual(
            {entry for entry in printed if is_reader_supplied(entry[0])} | electronic,
            printed)
        self.assertFalse(any(is_reader_supplied(entry[0]) for entry in electronic))
        self.assertIn("opensiddur:override", {entry[0] for entry in printed})


class TestPinnedValues(_Compiling):

    def test_declared_and_derived_values_are_pinned(self):
        """Ma'ariv, declared by the section, implies no repetition; the minyan is unknown.

        The condition is undecided, and the device needs what the compile knew to decide
        it once the reader says whether there is a minyan.
        """
        root = self._compile(MAARIV_SECTION, electronic=True)
        conditional = root.find(f".//{{{J}}}conditional")
        pinned = conditional.find(f"{{{P}}}pinned")
        self.assertIsNotNone(pinned)
        self.assertEqual(
            json.loads(pinned.text), {"opensiddur:recitation": {"repetition": False}})

    def test_print_pins_nothing(self):
        root = self._compile(MAARIV_SECTION, electronic=False)
        self.assertIsNotNone(root.find(f".//{{{J}}}conditional"))
        self.assertIsNone(root.find(f".//{{{P}}}pinned"))

    def test_nothing_known_pins_nothing(self):
        root = self._compile(OMIT_TAHANUN, electronic=True)
        self.assertIsNone(root.find(f".//{{{P}}}pinned"))


class TestSettingsFile(_Compiling):

    def _load(self, electronic: bool):
        settings = self.base / "settings.yaml"
        settings.write_text(
            "priority:\n  transclusion: [proj]\n"
            "declarations:\n"
            "  opensiddur:rite:\n    rite: ashkenaz\n"
            "  opensiddur:israel:\n    is-israel: true\n",
            encoding="utf-8")
        linear_data = get_linear_data()
        linear_data.defer_reader_settings = electronic
        load_settings(settings, linear_data=linear_data, project_directory=self.base)
        return {(e.fs_type, e.feature_name): e.value
                for e in linear_data.conditional_settings if e.source == "init"}

    def test_print_compiles_every_declaration(self):
        declared = self._load(electronic=False)
        self.assertEqual(declared[("opensiddur:rite", "rite")], "ashkenaz")
        self.assertIs(declared[("opensiddur:israel", "is-israel")], True)

    def test_electronic_compiles_only_the_calendar(self):
        declared = self._load(electronic=True)
        self.assertNotIn(("opensiddur:rite", "rite"), declared)
        self.assertIs(declared[("opensiddur:israel", "is-israel")], True)


class TestMain(_Compiling):

    def _main(self, *extra) -> etree.ElementBase:
        (self.base / "proj" / "doc.xml").write_bytes(_document(OMIT_TAHANUN))
        output = self.base / "out.xml"
        main(["-p", "proj", "-f", "doc.xml", "-o", str(output),
              "--project-directory", str(self.base), *extra])
        return etree.parse(str(output)).getroot()

    def test_electronic_output_says_so(self):
        root = self._main("--destination", "electronic")
        self.assertEqual(root.get(f"{{{P}}}destination"), "electronic")
        self.assertIsNotNone(root.find(f".//{{{J}}}conditional"))

    def test_print_is_the_default(self):
        root = self._main()
        self.assertIsNone(root.get(f"{{{P}}}destination"))
        self.assertIsNone(root.find(f".//{{{J}}}conditional"))


if __name__ == "__main__":
    unittest.main()
