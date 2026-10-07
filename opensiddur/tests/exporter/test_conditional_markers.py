"""Tests for the pairing of retained conditional markers.

An undecided `j:conditional` reaches the compiled document with its `j:endConditional`, and
every later stage finds the scope by pairing the two. These tests cover the checker itself,
and the compile of a range whose bounds cut through a scope.
"""

import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_markers import (
    CLOSER_FIRST,
    CROSS_STREAM,
    DUPLICATE,
    ORPHAN,
    UNCLOSED,
    check_pairing,
)
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import get_linear_data, reset_linear_data

J = JLPTEI_NAMESPACE
P = PROCESSING_NAMESPACE
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"


def _tree(body: str) -> etree.ElementBase:
    return etree.fromstring(
        f'<root xmlns:tei="{TEI_NS}" xmlns:j="{J}" xmlns:p="{P}">{body}</root>')


def _kinds(root) -> list[tuple[str, str]]:
    return [(problem.kind, problem.xml_id) for problem in check_pairing(root)]


class TestCheckPairing(unittest.TestCase):

    def test_paired_scope_is_fine(self):
        root = _tree('<j:conditional xml:id="a"/><tei:p>x</tei:p><j:endConditional target="#a"/>')
        self.assertEqual(check_pairing(root), [])

    def test_crossing_scopes_are_fine(self):
        root = _tree(
            '<j:conditional xml:id="a"/>x<j:conditional xml:id="b"/>y'
            '<j:endConditional target="#a"/>z<j:endConditional target="#b"/>')
        self.assertEqual(check_pairing(root), [])

    def test_opener_without_closer(self):
        root = _tree('<j:conditional xml:id="a"/><tei:p>x</tei:p>')
        self.assertEqual(_kinds(root), [(UNCLOSED, "a")])

    def test_closer_without_opener(self):
        root = _tree('<tei:p>x</tei:p><j:endConditional target="#a"/>')
        self.assertEqual(_kinds(root), [(ORPHAN, "a")])

    def test_second_closer_is_an_orphan(self):
        root = _tree(
            '<j:conditional xml:id="a"/>x<j:endConditional target="#a"/>'
            '<j:endConditional target="#a"/>')
        self.assertEqual(_kinds(root), [(ORPHAN, "a")])

    def test_closer_before_opener(self):
        root = _tree('<j:endConditional target="#a"/>x<j:conditional xml:id="a"/>')
        self.assertEqual(_kinds(root), [(CLOSER_FIRST, "a")])

    def test_duplicate_opener(self):
        # A parser refuses a repeated xml:id; the compiler builds its trees, so it can't.
        root = _tree(
            '<j:conditional xml:id="a"/><j:conditional xml:id="b"/>x'
            '<j:endConditional target="#a"/>')
        root[1].set(XML_ID, "a")
        self.assertEqual(_kinds(root), [(DUPLICATE, "a")])

    def test_one_column_across_rows_is_one_stream(self):
        """A scope may open in one row's primary column and close in a later row's."""
        root = _tree(
            '<p:parallel><p:parallelItem role="primary"><j:conditional xml:id="a"/>x'
            '</p:parallelItem><p:parallelItem role="parallel">y</p:parallelItem></p:parallel>'
            '<p:parallel><p:parallelItem role="primary">z<j:endConditional target="#a"/>'
            '</p:parallelItem><p:parallelItem role="parallel">w</p:parallelItem></p:parallel>')
        self.assertEqual(check_pairing(root), [])

    def test_pair_across_columns(self):
        root = _tree(
            '<p:parallel><p:parallelItem role="primary"><j:conditional xml:id="a"/>x'
            '</p:parallelItem><p:parallelItem role="parallel">y<j:endConditional target="#a"/>'
            '</p:parallelItem></p:parallel>')
        self.assertEqual(_kinds(root), [(CROSS_STREAM, "a")])

    def test_pair_between_column_and_main_flow(self):
        root = _tree(
            '<p:parallel><p:parallelItem role="primary"><j:conditional xml:id="a"/>x'
            '</p:parallelItem></p:parallel><j:endConditional target="#a"/>')
        self.assertEqual(_kinds(root), [(CROSS_STREAM, "a")])

    def test_problem_names_its_line(self):
        root = etree.fromstring(
            f'<root xmlns:j="{J}">\n\n<j:conditional xml:id="a"/></root>'.encode())
        self.assertEqual(str(check_pairing(root)[0]), "unclosed: a (line 3)")


def _document(body: str) -> bytes:
    return f'''<tei:TEI xmlns:tei="{TEI_NS}" xmlns:j="{J}">
  <tei:text>
    <tei:body>
      <tei:div>
        {body}
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>'''.encode()


def _scope(xml_id: str, rubric: str = "") -> str:
    note = f'<tei:note type="instruction">{rubric}</tei:note>' if rubric else ""
    return (f'<j:conditional xml:id="{xml_id}">{note}'
            f'<tei:fs type="t:x"><tei:f name="{xml_id}"><tei:binary value="true"/></tei:f>'
            f'</tei:fs></j:conditional>')


class TestRangeCutsConditionalScope(unittest.TestCase):
    """A range transcluded out of a file keeps exactly the scopes that overlap it.

    None of the conditions below is declared, so each scope is undecided and its markers are
    retained -- unless a test declares it true.
    """

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        (Path(self.temp_dir.name) / "proj").mkdir()
        get_linear_data().xml_cache.base_path = Path(self.temp_dir.name)

    def _compile(self, body: str, start: str, end: str, *, include_tail: bool = False):
        xml = _document(body)
        (Path(self.temp_dir.name) / "proj" / "doc.xml").write_bytes(xml)
        tree = etree.fromstring(xml).getroottree()

        def path(identifier):
            return tree.getpath(tree.xpath(
                "//*[@corresp=$i or @xml:id=$i]", i=identifier)[0])

        processor = ExternalCompilerProcessor(
            "proj", "doc.xml", path(start), path(end), include_tail_after_end=include_tail)
        holder = etree.Element("holder")
        holder.extend(processor.process())
        return holder

    @staticmethod
    def _events(holder) -> list[str]:
        """Markers, rubrics and words in document order, ids shorn of their hashes."""
        events = []

        def words(text):
            if text and text.strip():
                events.append(text.strip())

        def walk(node):
            if node.tag == f"{{{J}}}conditional":
                events.append("open " + node.get(XML_ID).split("_")[0])
            elif node.tag == f"{{{J}}}endConditional":
                events.append("close " + node.get("target")[1:].split("_")[0])
            elif node.tag == f"{{{TEI_NS}}}note":
                events.append("rubric " + node.text)
            else:
                words(node.text)
            if node.tag != f"{{{TEI_NS}}}note":
                for child in node:
                    walk(child)
            words(node.tail)

        walk(holder)
        return events

    def test_scope_wholly_before_the_start_is_not_emitted(self):
        holder = self._compile(
            _scope("a", "Before:") + '<tei:p>excluded</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:s">inside</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(self._events(holder), ["inside"])

    def test_true_rubric_before_the_start_is_not_emitted(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            _scope("a", "Before:") + '<tei:p>excluded</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:s">inside</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(self._events(holder), ["inside"])

    def test_true_rubric_of_a_scope_open_at_the_start_is_emitted_once(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            _scope("a", "Say:") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><j:endConditional target="#a"/>',
            "urn:s", "urn:s")
        self.assertEqual(self._events(holder), ["rubric Say:", "inside"])

    def test_scope_open_at_the_start_opens_there(self):
        holder = self._compile(
            _scope("a", "Say:") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><tei:p corresp="urn:e">last</tei:p>'
            '<j:endConditional target="#a"/><tei:p>after</tei:p>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            self._events(holder), ["open a", "rubric Say:", "inside", "last", "close a"])

    def test_scope_enclosing_a_whole_element_range(self):
        """The start is also the end: the scope opens before the element and closes after.

        The humash's megillot: a holiday condition around the div that is transcluded.
        """
        holder = self._compile(
            _scope("a") + '<tei:p corresp="urn:s"><tei:hi>inside</tei:hi></tei:p>'
            '<j:endConditional target="#a"/><tei:p>after</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "inside", "close a"])

    def test_scope_opening_before_and_closing_inside(self):
        holder = self._compile(
            _scope("a") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:e">last</tei:p>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "inside", "close a", "last"])

    def test_range_ending_inside_a_scope_closes_it_at_the_end(self):
        holder = self._compile(
            '<tei:p corresp="urn:s">inside</tei:p>' + _scope("a")
            + '<tei:p corresp="urn:e">last</tei:p><tei:p>excluded</tei:p>'
            '<j:endConditional target="#a"/>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["inside", "open a", "last", "close a"])

    def test_nested_scopes_cut_by_the_end_close_innermost_first(self):
        holder = self._compile(
            '<tei:p corresp="urn:s">inside</tei:p>' + _scope("a") + _scope("b")
            + '<tei:p corresp="urn:e">last</tei:p>'
            '<j:endConditional target="#b"/><j:endConditional target="#a"/>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            self._events(holder), ["inside", "open a", "open b", "last", "close b", "close a"])

    def test_inline_range_ending_inside_a_scope(self):
        """A milestone range keeps the end element's tail, and the closer follows it."""
        holder = self._compile(
            '<tei:p><tei:milestone unit="part" corresp="urn:s"/>one '
            + _scope("a") + 'two<tei:seg xml:id="e"/>three '
            '<tei:milestone unit="part"/>excluded <j:endConditional target="#a"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["one", "open a", "two", "three", "close a"])

    def test_closer_that_is_the_end_element_is_not_doubled(self):
        """A milestone range ends on the last element before the next milestone -- which
        can be the scope's own closer. It closes the scope once."""
        holder = self._compile(
            '<tei:p><tei:milestone unit="part" corresp="urn:s"/>one '
            + _scope("a") + 'two <j:endConditional xml:id="e" target="#a"/>three'
            '<tei:milestone unit="part"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["one", "open a", "two", "close a", "three"])

    def test_scope_enclosing_an_inline_range(self):
        holder = self._compile(
            '<tei:p>excluded ' + _scope("a") + 'excluded too '
            '<tei:milestone unit="part" corresp="urn:s"/>one<tei:seg xml:id="e"/>two '
            '<tei:milestone unit="part"/>excluded <j:endConditional target="#a"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "one", "two", "close a"])

    def test_ids_carry_one_hash(self):
        """Every level between the file's root and the range used to append the hash again."""
        holder = self._compile(
            '<tei:p corresp="urn:s">inside</tei:p>' + _scope("a")
            + '<tei:p corresp="urn:e">last</tei:p><j:endConditional target="#a"/>',
            "urn:s", "urn:e")
        opener = holder.find(f".//{{{J}}}conditional")
        self.assertRegex(opener.get(XML_ID), r"^a_[0-9a-f]{8}$")
        closer = holder.find(f".//{{{J}}}endConditional")
        self.assertEqual(closer.get("target"), "#" + opener.get(XML_ID))


if __name__ == "__main__":
    unittest.main()
