"""Tests for the pairing of retained conditional markers.

An undecided `j:conditional` reaches the compiled document with its `j:endConditional`, and
every later stage finds the scope by pairing the two. These tests cover the checker itself,
and the compile of a range whose bounds cut through a scope.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.compiler import CompilerProcessor, _AnnotationCommand
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
from opensiddur.exporter.inline_compiler import InlineCompilerProcessor
from opensiddur.exporter.linear import get_linear_data, reset_linear_data
from opensiddur.exporter.marker_reconstruct import reconstruct_markered_document

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


def _stub_transclude(self, element, type_override=None):
    """Stand in for resolving a transclusion: its text is its own @target."""
    if element.tag != f"{{{J}}}transclude":
        return None
    stub = etree.Element(f"{{{P}}}transclude")
    stub.text = element.get("target")
    return stub


def _scope(xml_id: str, rubric: str = "") -> str:
    note = f'<tei:note type="instruction">{rubric}</tei:note>' if rubric else ""
    return (f'<j:conditional xml:id="{xml_id}">{note}'
            f'<tei:fs type="t:x"><tei:f name="{xml_id}"><tei:binary value="true"/></tei:f>'
            f'</tei:fs></j:conditional>')


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

    #: Whether the processor runs in marker mode, as it does for a book with parallel text.
    MARKER_MODE = False

    def _compile(self, body: str, start: str, end: str, *, include_tail: bool = False):
        xml = _document(body)
        (Path(self.temp_dir.name) / "proj" / "doc.xml").write_bytes(xml)
        tree = etree.fromstring(xml).getroottree()

        def path(identifier):
            return tree.getpath(tree.xpath(
                "//*[@corresp=$i or @xml:id=$i]", i=identifier)[0])

        processor = ExternalCompilerProcessor(
            "proj", "doc.xml", path(start), path(end), include_tail_after_end=include_tail)
        if self.MARKER_MODE:
            processor.marker_stack = []
        holder = etree.Element("holder")
        with patch.object(ExternalCompilerProcessor, "_transclude", _stub_transclude):
            holder.extend(processor.process())
        if self.MARKER_MODE:
            reconstruct_markered_document(holder)
        return holder

    def test_scope_wholly_before_the_start_is_not_emitted(self):
        holder = self._compile(
            _scope("a", "Before:") + '<tei:p>excluded</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:s">inside</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(_events(holder), ["inside"])

    def test_true_rubric_before_the_start_is_not_emitted(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            _scope("a", "Before:") + '<tei:p>excluded</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:s">inside</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(_events(holder), ["inside"])

    def test_true_rubric_of_a_scope_open_at_the_start_is_emitted_once(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            _scope("a", "Say:") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><j:endConditional target="#a"/>',
            "urn:s", "urn:s")
        self.assertEqual(_events(holder), ["rubric Say:", "inside"])

    def test_scope_open_at_the_start_opens_there(self):
        holder = self._compile(
            _scope("a", "Say:") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><tei:p corresp="urn:e">last</tei:p>'
            '<j:endConditional target="#a"/><tei:p>after</tei:p>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            _events(holder), ["open a", "rubric Say:", "inside", "last", "close a"])

    def test_scope_enclosing_a_whole_element_range(self):
        """The start is also the end: the scope opens before the element and closes after.

        The humash's megillot: a holiday condition around the div that is transcluded.
        """
        holder = self._compile(
            _scope("a") + '<tei:p corresp="urn:s"><tei:hi>inside</tei:hi></tei:p>'
            '<j:endConditional target="#a"/><tei:p>after</tei:p>',
            "urn:s", "urn:s")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["open a", "inside", "close a"])

    def test_scope_opening_before_and_closing_inside(self):
        holder = self._compile(
            _scope("a") + '<tei:p>excluded</tei:p>'
            '<tei:p corresp="urn:s">inside</tei:p><j:endConditional target="#a"/>'
            '<tei:p corresp="urn:e">last</tei:p>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["open a", "inside", "close a", "last"])

    def test_range_ending_inside_a_scope_closes_it_at_the_end(self):
        holder = self._compile(
            '<tei:p corresp="urn:s">inside</tei:p>' + _scope("a")
            + '<tei:p corresp="urn:e">last</tei:p><tei:p>excluded</tei:p>'
            '<j:endConditional target="#a"/>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["inside", "open a", "last", "close a"])

    def test_nested_scopes_cut_by_the_end_close_innermost_first(self):
        holder = self._compile(
            '<tei:p corresp="urn:s">inside</tei:p>' + _scope("a") + _scope("b")
            + '<tei:p corresp="urn:e">last</tei:p>'
            '<j:endConditional target="#b"/><j:endConditional target="#a"/>',
            "urn:s", "urn:e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            _events(holder), ["inside", "open a", "open b", "last", "close b", "close a"])

    def test_inline_range_ending_inside_a_scope(self):
        """A milestone range keeps the end element's tail, and the closer follows it."""
        holder = self._compile(
            '<tei:p><tei:milestone unit="part" corresp="urn:s"/>one '
            + _scope("a") + 'two<tei:seg xml:id="e"/>three '
            '<tei:milestone unit="part"/>excluded <j:endConditional target="#a"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["one", "open a", "two", "three", "close a"])

    def test_closer_that_is_the_end_element_is_not_doubled(self):
        """A milestone range ends on the last element before the next milestone -- which
        can be the scope's own closer. It closes the scope once."""
        holder = self._compile(
            '<tei:p><tei:milestone unit="part" corresp="urn:s"/>one '
            + _scope("a") + 'two <j:endConditional xml:id="e" target="#a"/>three'
            '<tei:milestone unit="part"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["one", "open a", "two", "close a", "three"])

    def test_scope_enclosing_an_inline_range(self):
        holder = self._compile(
            '<tei:p>excluded ' + _scope("a") + 'excluded too '
            '<tei:milestone unit="part" corresp="urn:s"/>one<tei:seg xml:id="e"/>two '
            '<tei:milestone unit="part"/>excluded <j:endConditional target="#a"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(_events(holder), ["open a", "one", "two", "close a"])

    def test_range_starting_inside_a_false_scope_keeps_its_text_out(self):
        """The undecided scope around it opens at the start; the false one's text stays out.

        The opener put before the start element's (empty) output must not become the place
        the start's tail -- still inside the false scope -- is attached to.
        """
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"b": False}}))
        holder = self._compile(
            '<tei:p>' + _scope("a") + 'excluded ' + _scope("b") + 'false '
            '<tei:milestone unit="part" corresp="urn:s"/>secret <j:endConditional target="#b"/>'
            'said <tei:seg xml:id="e"/>end <tei:milestone unit="part"/>after'
            '<j:endConditional target="#a"/></tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        events = _events(holder)
        self.assertNotIn("secret", " ".join(events))
        self.assertEqual(events[0], "open a")
        self.assertEqual(events[-2:], ["end", "close a"])

    def test_range_ending_on_a_transclusion_ends_there(self):
        """A milestone range can end on a j:transclude -- the last element before the next
        milestone. The range ends there, and closes the scope it ends inside."""
        holder = self._compile(
            '<tei:p><tei:milestone unit="part" corresp="urn:s"/>one ' + _scope("a")
            + 'two <j:transclude xml:id="e" target="urn:t"/>three '
            '<tei:milestone unit="part"/>excluded <j:endConditional target="#a"/>more</tei:p>',
            "urn:s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            _events(holder), ["one", "open a", "two", "urn:t", "three", "close a"])

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

    def test_pointer_and_anchor_at_different_depths_still_pair(self):
        holder = self._compile(
            '<tei:p corresp="urn:s"><tei:hi><tei:anchor xml:id="x"/>inside</tei:hi></tei:p>'
            '<tei:p corresp="urn:e"><tei:ptr target="#x"/>last</tei:p>',
            "urn:s", "urn:e")
        anchor = holder.find(f".//{{{TEI_NS}}}anchor")
        self.assertRegex(anchor.get(XML_ID), r"^x_[0-9a-f]{8}$")
        self.assertEqual(
            holder.find(f".//{{{TEI_NS}}}ptr").get("target"), "#" + anchor.get(XML_ID))


class TestRangeCutsConditionalScopeInMarkerMode(TestRangeCutsConditionalScope):
    """The same, with structural elements flattened to markers as for a parallel book."""

    MARKER_MODE = True


class TestInlineRangeCutsConditionalScope(unittest.TestCase):
    """An inline range keeps exactly the scopes that overlap it, as an external range does.

    The inline processor builds a p:transcludeInline of text rather than a list of elements,
    so its markers sit among that text: an opener in front of the start's text, a closer
    after the end element's tail.
    """

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        (Path(self.temp_dir.name) / "proj").mkdir()
        get_linear_data().xml_cache.base_path = Path(self.temp_dir.name)

    def _compile(self, body: str, start: str, end: str, *, include_tail: bool = False,
                 transclude=_stub_transclude):
        xml = _document(body)
        (Path(self.temp_dir.name) / "proj" / "doc.xml").write_bytes(xml)
        tree = etree.fromstring(xml).getroottree()

        def path(identifier):
            return tree.getpath(tree.xpath("//*[@xml:id=$i]", i=identifier)[0])

        processor = InlineCompilerProcessor(
            "proj", "doc.xml", path(start), path(end), include_tail_after_end=include_tail)
        holder = etree.Element("holder")
        with patch.object(InlineCompilerProcessor, "_transclude", transclude):
            holder.append(processor.process())
        return holder

    @staticmethod
    def _events(holder) -> list[str]:
        """As _events, with runs of spaces collapsed: joining tails can double them."""
        return [" ".join(event.split()) for event in _events(holder)]

    def test_issue_example(self):
        """#221: a scope closed before the start is left out; one cut by the end is closed."""
        holder = self._compile(
            '<tei:p>' + _scope("a") + 'before <j:endConditional target="#a"/>'
            '<tei:seg xml:id="s"/>inside ' + _scope("b") + 'also inside '
            '<tei:seg xml:id="e"/>after<j:endConditional target="#b"/></tei:p>',
            "s", "e")
        self.assertEqual(check_pairing(holder), [])
        # An inline range always keeps its end element's tail.
        self.assertEqual(
            self._events(holder), ["inside", "open b", "also inside after", "close b"])

    def test_scope_wholly_before_the_start_is_not_emitted(self):
        holder = self._compile(
            '<tei:p>' + _scope("a", "Before:") + 'excluded <j:endConditional target="#a"/>'
            '<tei:seg xml:id="s"/>inside <tei:seg xml:id="e"/></tei:p>',
            "s", "e")
        self.assertEqual(self._events(holder), ["inside"])

    def test_true_rubric_before_the_start_is_not_emitted(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            '<tei:p>' + _scope("a", "Before:") + 'excluded <j:endConditional target="#a"/>'
            '<tei:seg xml:id="s"/>inside <tei:seg xml:id="e"/></tei:p>',
            "s", "e")
        self.assertEqual(self._events(holder), ["inside"])

    def test_true_rubric_of_a_scope_open_at_the_start_is_emitted_once(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"a": True}}))
        holder = self._compile(
            '<tei:p>' + _scope("a", "Say:") + 'excluded '
            '<tei:seg xml:id="s"/>inside <tei:seg xml:id="e"/><j:endConditional target="#a"/>'
            '</tei:p>',
            "s", "e")
        self.assertEqual(self._events(holder), ["rubric Say:", "inside"])

    def test_scope_open_at_the_start_opens_before_its_text(self):
        """The start's own text, and nested text after it, follow the opener."""
        holder = self._compile(
            '<tei:p>' + _scope("a") + 'excluded '
            '<tei:seg xml:id="s">first</tei:seg> then <tei:hi>nested</tei:hi> last '
            '<tei:seg xml:id="e"/><j:endConditional target="#a"/>after</tei:p>',
            "s", "e")
        self.assertEqual(check_pairing(holder), [])
        events = self._events(holder)
        self.assertEqual(events[0], "open a")
        self.assertEqual(events[-1], "close a")
        text = " ".join(events[1:-1])
        self.assertLess(text.index("first"), text.index("then"))
        self.assertLess(text.index("then"), text.index("nested"))
        self.assertLess(text.index("nested"), text.index("last"))

    def test_range_ending_inside_a_scope_closes_it_after_the_end_tail(self):
        holder = self._compile(
            '<tei:p><tei:seg xml:id="s"/>one ' + _scope("a") + 'two '
            '<tei:seg xml:id="e"/>three <tei:seg/>excluded <j:endConditional target="#a"/>'
            '</tei:p>',
            "s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["one", "open a", "two three", "close a"])

    def test_nested_scopes_cut_by_the_end_close_innermost_first(self):
        holder = self._compile(
            '<tei:p><tei:seg xml:id="s"/>one ' + _scope("a") + _scope("b")
            + 'two <tei:seg xml:id="e"/><j:endConditional target="#b"/>'
            '<j:endConditional target="#a"/></tei:p>',
            "s", "e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            self._events(holder), ["one", "open a", "open b", "two", "close b", "close a"])

    def test_closer_that_is_the_end_element_is_not_doubled(self):
        holder = self._compile(
            '<tei:p><tei:seg xml:id="s"/>one ' + _scope("a")
            + 'two <j:endConditional xml:id="e" target="#a"/>three <tei:seg/></tei:p>',
            "s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["one", "open a", "two", "close a", "three"])

    def test_scope_enclosing_the_range(self):
        holder = self._compile(
            '<tei:p>excluded ' + _scope("a") + 'excluded too '
            '<tei:seg xml:id="s"/>one <tei:seg xml:id="e"/>two '
            '<tei:seg/>excluded <j:endConditional target="#a"/></tei:p>',
            "s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "one two", "close a"])

    def test_scope_enclosing_a_single_element_range(self):
        """The start is also the end: the scope opens before its text and closes after."""
        holder = self._compile(
            '<tei:p>' + _scope("a") + '<tei:seg xml:id="s">inside</tei:seg>'
            '<j:endConditional target="#a"/>after</tei:p>',
            "s", "s")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "inside", "close a"])

    def test_range_starting_inside_a_false_scope_keeps_its_text_out(self):
        CompilerProcessor.load_init_settings(
            get_linear_data(), yaml_to_declaration_entries({"t:x": {"b": False}}))
        holder = self._compile(
            '<tei:p>' + _scope("a") + 'excluded ' + _scope("b") + 'false '
            '<tei:seg xml:id="s"/>secret <j:endConditional target="#b"/>'
            'said <tei:seg xml:id="e"/>end <tei:seg/>after'
            '<j:endConditional target="#a"/></tei:p>',
            "s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        events = self._events(holder)
        self.assertNotIn("secret", " ".join(events))
        self.assertEqual(events, ["open a", "said end", "close a"])

    def test_range_starting_on_a_transclusion_inside_a_scope(self):
        """A start whose output is not a p:transcludeInline still gets the opener first."""
        holder = self._compile(
            '<tei:p>' + _scope("a") + 'excluded <j:transclude xml:id="s" target="urn:t"/>'
            'one <tei:seg xml:id="e"/><j:endConditional target="#a"/></tei:p>',
            "s", "e")
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(self._events(holder), ["open a", "urn:t", "one", "close a"])

    def test_range_ending_on_a_transclusion_ends_there(self):
        holder = self._compile(
            '<tei:p><tei:seg xml:id="s"/>one ' + _scope("a")
            + 'two <j:transclude xml:id="e" target="urn:t"/>three '
            '<tei:seg/>excluded <j:endConditional target="#a"/>more</tei:p>',
            "s", "e", include_tail=True)
        self.assertEqual(check_pairing(holder), [])
        self.assertEqual(
            self._events(holder), ["one", "open a", "two", "urn:t", "three", "close a"])

    def test_ids_carry_one_hash(self):
        holder = self._compile(
            '<tei:p><tei:seg xml:id="s"/>one ' + _scope("a")
            + 'two <tei:seg xml:id="e"/><j:endConditional target="#a"/></tei:p>',
            "s", "e")
        opener = holder.find(f".//{{{J}}}conditional")
        self.assertRegex(opener.get(XML_ID), r"^a_[0-9a-f]{8}$")
        closer = holder.find(f".//{{{J}}}endConditional")
        self.assertEqual(closer.get("target"), "#" + opener.get(XML_ID))

    # Transclusions and annotations before the start are never resolved (#53).

    def test_transclusion_before_the_start_is_not_emitted(self):
        holder = self._compile(
            '<tei:p><j:transclude target="urn:before"/>excluded '
            '<tei:seg xml:id="s"/>inside <tei:seg xml:id="e"/></tei:p>',
            "s", "e")
        self.assertEqual(self._events(holder), ["inside"])

    def test_unresolvable_transclusion_before_the_start_does_not_raise(self):
        def transclude(processor, element, type_override=None):
            if element.get("target") == "urn:missing":
                raise ValueError("unresolvable")
            return _stub_transclude(processor, element, type_override)

        holder = self._compile(
            '<tei:p><j:transclude target="urn:missing"/>excluded '
            '<tei:seg xml:id="s"/>inside <tei:seg xml:id="e"/></tei:p>',
            "s", "e", transclude=transclude)
        self.assertEqual(self._events(holder), ["inside"])

    def test_elements_before_the_start_are_not_annotated(self):
        annotated = []

        def annotate(processor, element, root=None):
            annotated.append(element.get(XML_ID) or element.tag)
            return [], _AnnotationCommand.NONE

        with patch.object(InlineCompilerProcessor, "_annotate", annotate):
            self._compile(
                '<tei:p xml:id="p"><tei:hi xml:id="before">excluded</tei:hi>'
                '<tei:seg xml:id="s"/>inside <tei:hi xml:id="within">x</tei:hi>'
                '<tei:seg xml:id="e"/><tei:hi xml:id="after">y</tei:hi></tei:p>',
                "s", "e")
        self.assertEqual(annotated, ["s", "within", "e"])


if __name__ == "__main__":
    unittest.main()
