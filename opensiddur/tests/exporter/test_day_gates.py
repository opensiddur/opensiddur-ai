"""A section that says what kind of day it is for is shown only on such a day (day_gates)."""

import json
import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.day_gates import GATE_SUFFIX, gate_kind_of_day_declarations
from opensiddur.exporter.linear import get_linear_data, reset_linear_data

J = JLPTEI_NAMESPACE
P = PROCESSING_NAMESPACE
NS = {"tei": TEI_NS, "j": J, "p": P}

WEEKDAY = '''<j:declare xml:id="weekday"><tei:fs type="opensiddur:holiday-aggregate">
    <tei:f name="shabbat"><tei:binary value="false"/></tei:f>
    <tei:f name="yom-tov"><tei:binary value="false"/></tei:f></tei:fs>
  <tei:fs type="opensiddur:service-time"><tei:f name="shaharit"><tei:binary value="true"/></tei:f></tei:fs></j:declare>
  <tei:p>weekday words</tei:p>
  <j:endDeclare target="#weekday"/> after'''


def _body(body: str) -> etree.ElementBase:
    return etree.fromstring(
        f'<tei:div xmlns:tei="{TEI_NS}" xmlns:j="{J}">{body}</tei:div>')


def _document(body: str) -> bytes:
    return f'''<tei:TEI xmlns:tei="{TEI_NS}" xmlns:j="{J}" xml:lang="en">
  <tei:teiHeader><tei:fileDesc><tei:titleStmt><tei:title>T</tei:title></tei:titleStmt>
  </tei:fileDesc></tei:teiHeader>
  <tei:text><tei:body><tei:div><tei:p>always</tei:p>{body}</tei:div></tei:body></tei:text>
</tei:TEI>'''.encode()


class TestGates(unittest.TestCase):

    def test_a_kind_of_day_declaration_is_gated_on_its_own_kind_of_day(self):
        div = _body(WEEKDAY)
        gate_kind_of_day_declarations(div)
        gate, declare = div[0], div[1]
        self.assertEqual(gate.tag, f"{{{J}}}conditional")
        self.assertEqual(gate.get("{http://www.w3.org/XML/1998/namespace}id"), "weekday" + GATE_SUFFIX)
        # Only the kind of day: the service the section declares is not what it is for.
        conditions = gate.xpath("tei:fs/@type", namespaces=NS)
        self.assertEqual(conditions, ["opensiddur:holiday-aggregate"])
        self.assertEqual(declare.tag, f"{{{J}}}declare")
        closer = div.xpath("j:endConditional", namespaces=NS)[0]
        self.assertEqual(closer.get("target"), "#weekday" + GATE_SUFFIX)
        self.assertEqual(closer.getprevious().tag, f"{{{J}}}endDeclare")
        self.assertEqual(closer.tail.strip(), "after")

    def test_one_structure_needs_no_all(self):
        div = _body('<j:declare xml:id="d"><tei:fs type="opensiddur:holiday-aggregate">'
                    '<tei:f name="yom-tov"><tei:binary value="true"/></tei:f></tei:fs></j:declare>'
                    '<j:endDeclare target="#d"/>')
        gate_kind_of_day_declarations(div)
        self.assertEqual(div[0][0].tag, f"{{{TEI_NS}}}fs")

    def test_other_declarations_are_not_gated(self):
        div = _body('<j:declare xml:id="d"><tei:fs type="opensiddur:service-time">'
                    '<tei:f name="maariv"><tei:binary value="true"/></tei:f></tei:fs></j:declare>'
                    '<j:endDeclare target="#d"/>')
        gate_kind_of_day_declarations(div)
        self.assertEqual([e.tag for e in div], [f"{{{J}}}declare", f"{{{J}}}endDeclare"])

    def test_a_declaration_the_running_order_already_gates_is_left(self):
        condition = ('<tei:fs type="opensiddur:holiday-aggregate"><tei:f name="aseret-ymei-tshuva">'
                     '<tei:binary value="true"/></tei:f></tei:fs>')
        div = _body(f'<j:conditional xml:id="c">{condition}</j:conditional>'
                    f'<j:declare xml:id="d">{condition}</j:declare><j:endDeclare target="#d"/>'
                    '<j:endConditional target="#c"/>')
        gate_kind_of_day_declarations(div)
        self.assertEqual(len(div.xpath("j:conditional", namespaces=NS)), 1)

    def test_a_declaration_to_the_end_of_the_text_is_gated_to_the_end(self):
        div = _body('<j:declare xml:id="d"><tei:fs type="opensiddur:holiday-aggregate">'
                    '<tei:f name="yom-tov"><tei:binary value="true"/></tei:f></tei:fs></j:declare>'
                    '<tei:p>festival</tei:p>')
        gate_kind_of_day_declarations(div)
        self.assertEqual(div[0].tag, f"{{{J}}}conditional")
        self.assertEqual(div.xpath("j:endConditional", namespaces=NS), [])


class TestCompiling(unittest.TestCase):
    """A weekday section, compiled for a date, a Shabbat, and no day at all."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        base = Path(self.temp_dir.name)
        (base / "proj").mkdir()
        (base / "proj" / "doc.xml").write_bytes(_document(WEEKDAY))
        get_linear_data().xml_cache.base_path = base

    def _compile(self, declarations: dict, *, electronic: bool = False) -> etree.ElementBase:
        linear_data = get_linear_data()
        linear_data.defer_reader_settings = electronic
        CompilerProcessor.load_init_settings(linear_data, yaml_to_declaration_entries(declarations))
        return CompilerProcessor("proj", "doc.xml").process()

    @staticmethod
    def _text(root) -> str:
        return " ".join("".join(root.itertext()).split())

    def test_a_weekday_shows_the_weekday_section(self):
        text = self._text(self._compile({"opensiddur:holiday-aggregate": {"shabbat": False,
                                                                           "yom-tov": False}}))
        self.assertIn("weekday words", text)

    def test_a_volume_s_declaration_is_overridden_not_contradicted(self):
        """What the volume declares is context the section's own declaration overrides, as a
        selichot volume for the Ten Days has a first day that is not one of them. Only the day
        -- a date -- leaves a section out."""
        text = self._text(self._compile({"opensiddur:holiday-aggregate": {"shabbat": True}}))
        self.assertIn("weekday words", text)
        self.assertIn("always", text)

    def test_an_electronic_gate_does_not_pin_what_the_volume_declares(self):
        root = self._compile({"opensiddur:holiday-aggregate": {"shabbat": True}}, electronic=True)
        gate = root.find(f".//{{{J}}}conditional")
        self.assertIsNotNone(gate)
        pinned = gate.find(f"{{{P}}}pinned")
        self.assertTrue(pinned is None or "holiday-aggregate" not in json.loads(pinned.text))

    def test_a_dated_shabbat_leaves_it_out(self):
        text = self._text(self._compile({
            "opensiddur:gregorian-date": {"year": 2026, "month": 1, "day": 3},
            "opensiddur:location": {"latitude": 40.71, "longitude": -74.01},
            "opensiddur:time": {"hour": 9, "minute": 0}}))
        self.assertNotIn("weekday words", text)

    def test_print_with_no_day_keeps_it_and_leaves_no_trace(self):
        root = self._compile({})
        self.assertIn("weekday words", self._text(root))
        self.assertIsNone(root.find(f".//{{{J}}}conditional"))

    def test_electronic_with_no_day_keeps_the_gate_for_the_device(self):
        root = self._compile({}, electronic=True)
        self.assertIn("weekday words", self._text(root))
        gate = root.find(f".//{{{J}}}conditional")
        self.assertIsNotNone(gate, "an undecided gate is retained, for the reader's device")
        self.assertIsNone(gate.find(f"{{{TEI_NS}}}note"))

    def test_an_electronic_gate_pins_nothing_of_the_section(self):
        """The gate is evaluated outside the section's own declaration: what it pins is the
        enclosing settings', not the weekday it declares."""
        root = self._compile({}, electronic=True)
        gate = root.find(f".//{{{J}}}conditional")
        pinned = gate.find(f"{{{P}}}pinned")
        self.assertTrue(pinned is None or "holiday-aggregate" not in json.loads(pinned.text))


if __name__ == "__main__":
    unittest.main()
