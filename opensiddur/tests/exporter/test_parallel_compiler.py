"""Unit tests for parallel compiler functionality in ExternalCompilerProcessor."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from lxml import etree

from opensiddur.exporter.compiler import (
    JLPTEI_NAMESPACE,
    PROCESSING_NAMESPACE,
    _ProcessingCommand,
    _ProcessingContext,
)
from opensiddur.exporter.external_compiler import (
    STRUCTURAL_BLOCKS,
    TEI_NS,
    ExternalCompilerProcessor,
)
from opensiddur.exporter.linear import (
    LinearData,
    ParallelColumnOrder,
    get_linear_data,
    reset_linear_data,
)
from opensiddur.exporter.urn import ResolvedUrn, ResolvedUrnRange

P_NS = PROCESSING_NAMESPACE
J_NS = JLPTEI_NAMESPACE
XML_NS = "http://www.w3.org/XML/1998/namespace"

# Minimal valid JLPTEI document used by multiple tests
_MINIMAL_TEI = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="he">
  <tei:text xml:lang="he">
    <tei:body>
      <tei:div corresp="urn:x-test:body">
        <tei:p>Body text</tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""


# ── _build_parallel_urn ─────────────────────────────────────────────────────

class TestBuildParallelUrn(unittest.TestCase):

    def test_appends_project_when_no_suffix(self):
        r = ExternalCompilerProcessor._build_parallel_urn("urn:x-opensiddur:foo", "trans")
        self.assertEqual(r, "urn:x-opensiddur:foo@trans")

    def test_replaces_existing_suffix(self):
        r = ExternalCompilerProcessor._build_parallel_urn("urn:x-opensiddur:foo@orig", "trans")
        self.assertEqual(r, "urn:x-opensiddur:foo@trans")

    def test_preserves_path_components(self):
        r = ExternalCompilerProcessor._build_parallel_urn("urn:x-opensiddur:foo/bar@orig", "trans")
        self.assertEqual(r, "urn:x-opensiddur:foo/bar@trans")

    def test_hyphenated_project_name(self):
        r = ExternalCompilerProcessor._build_parallel_urn("urn:foo@original-example", "translation-example")
        self.assertEqual(r, "urn:foo@translation-example")


# ── _assemble_parallel_streams ──────────────────────────────────────────────

class TestAssembleParallelStreams(unittest.TestCase):

    def setUp(self):
        self.ns = {"p": P_NS, "tei": TEI_NS}

    def _div(self, text="x"):
        el = etree.Element(f"{{{TEI_NS}}}div", nsmap=self.ns)
        el.text = text
        return el

    def _transclude(self, target="urn:test@orig"):
        el = etree.Element(f"{{{P_NS}}}transclude", nsmap=self.ns)
        el.set("target", target)
        child = self._div("inner")
        el.append(child)
        return el

    def _assemble(self, prim, par, column_order="primary_first"):
        return ExternalCompilerProcessor._assemble_parallel_streams(
            prim, "he", "proj-a", "a.xml",
            par, "en", "proj-b", "b.xml",
            column_order, self.ns,
        )

    def test_no_transcludes_produces_one_parallel(self):
        result = self._assemble([self._div("p")], [self._div("q")])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tag, f"{{{P_NS}}}parallel")
        items = list(result[0])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].get("role"), "primary")
        self.assertEqual(items[1].get("role"), "parallel")

    def test_column_order_attribute_set(self):
        result = self._assemble([self._div()], [self._div()], column_order="primary_last")
        self.assertEqual(result[0].get("column-order"), "primary_last")

    def test_xml_lang_and_project_on_parallelItem(self):
        result = self._assemble([self._div()], [self._div()])
        prim_item = list(result[0])[0]
        par_item = list(result[0])[1]
        self.assertEqual(prim_item.get(f"{{{XML_NS}}}lang"), "he")
        self.assertEqual(prim_item.get(f"{{{P_NS}}}project"), "proj-a")
        self.assertEqual(par_item.get(f"{{{XML_NS}}}lang"), "en")
        self.assertEqual(par_item.get(f"{{{P_NS}}}project"), "proj-b")

    def test_one_transclude_produces_three_elements(self):
        t1 = self._transclude("urn:t@orig")
        t2 = self._transclude("urn:t@trans")
        prim = [self._div("before"), t1, self._div("after")]
        par = [self._div("par-before"), t2, self._div("par-after")]
        result = self._assemble(prim, par)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].tag, f"{{{P_NS}}}parallel")
        self.assertEqual(result[1].tag, f"{{{P_NS}}}transclude")
        self.assertEqual(result[2].tag, f"{{{P_NS}}}parallel")

        # Inner p:parallel inside the combined p:transclude
        inner_children = list(result[1])
        self.assertEqual(len(inner_children), 1)
        inner_par = inner_children[0]
        self.assertEqual(inner_par.tag, f"{{{P_NS}}}parallel")
        inner_items = list(inner_par)
        self.assertEqual(inner_items[0].get("role"), "primary")
        self.assertEqual(inner_items[1].get("role"), "parallel")

    def test_mismatched_transclude_counts(self):
        t1 = self._transclude()
        prim = [self._div("a"), t1, self._div("b")]  # 1 transclude
        par = [self._div("c")]                        # 0 transcludes
        # Should not raise
        result = self._assemble(prim, par)
        self.assertGreaterEqual(len(result), 2)
        tags = [el.tag for el in result]
        self.assertIn(f"{{{P_NS}}}parallel", tags)


# ── Base for tests that need a real processor ───────────────────────────────

class _ProcessorBase(unittest.TestCase):

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.project = "test-proj"
        proj_dir = Path(self.temp_dir.name) / self.project
        proj_dir.mkdir(parents=True)
        (proj_dir / "index.xml").write_bytes(_MINIMAL_TEI)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)

    def _make_processor(self, _in_parallel_compilation=False):
        return ExternalCompilerProcessor(
            self.project, "index.xml",
            linear_data=self.linear_data,
            _in_parallel_compilation=_in_parallel_compilation,
        )


# ── _split_at_milestones ────────────────────────────────────────────────────

class TestSplitAtMilestones(unittest.TestCase):

    def setUp(self):
        self.ns = {"p": P_NS, "tei": TEI_NS}

    def _ms(self, corresp, tail=None):
        el = etree.Element(f"{{{TEI_NS}}}milestone", nsmap=self.ns)
        el.set("unit", "verse")
        el.set("corresp", corresp)
        if tail:
            el.tail = tail
        return el

    def _start(self, tag, p_id):
        el = etree.Element(f"{{{TEI_NS}}}{tag}", nsmap=self.ns)
        el.set(f"{{{P_NS}}}start", p_id)
        return el

    def _end(self, tag, p_id):
        el = etree.Element(f"{{{TEI_NS}}}{tag}", nsmap=self.ns)
        el.set(f"{{{P_NS}}}end", p_id)
        return el

    def _split(self, elements):
        return ExternalCompilerProcessor._split_at_milestones(elements, self.ns)

    def test_no_milestones_returns_single_preamble(self):
        div = etree.Element(f"{{{TEI_NS}}}div", nsmap=self.ns)
        result = self._split([div])
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0][0])
        self.assertEqual(len(result[0][1]), 1)

    def test_empty_input_returns_single_empty_preamble(self):
        result = self._split([])
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0][0])

    def test_one_milestone_splits_into_milestone_sub_segment(self):
        result = self._split([self._ms("urn:x-test:1")])
        corresps = [c for c, _ in result]
        self.assertIn("urn:x-test:1", corresps)
        # Empty preamble is filtered out
        self.assertNotIn(None, corresps)

    def test_milestone_in_preamble_creates_split(self):
        """Milestones always start a new sub-segment."""
        elements = [
            self._start("p", "p1"),
            self._ms("urn:x-test:1", "verse 1 text"),
            self._ms("urn:x-test:2", "verse 2 text"),
            self._end("p", "p1"),
        ]
        result = self._split(elements)
        corresps = [c for c, _ in result]
        self.assertIn("urn:x-test:1", corresps)
        self.assertIn("urn:x-test:2", corresps)

    def test_open_elements_get_suspend_and_resume(self):
        """Elements open at a milestone boundary get suspend/resume markers."""
        elements = [
            self._start("div", "d1"),
            self._start("p", "p1"),
            self._ms("urn:x-test:1"),
            self._end("p", "p1"),
            self._end("div", "d1"),
        ]
        result = self._split(elements)
        # preamble should have d1 and p1 suspends (LIFO: p1 first, then d1)
        preamble_els = result[0][1]
        suspend_ids = [el.get(f"{{{P_NS}}}suspend") for el in preamble_els if el.get(f"{{{P_NS}}}suspend")]
        self.assertEqual(suspend_ids, ["p1", "d1"])  # LIFO

        # milestone sub-segment should have d1 and p1 resumes (FIFO: d1 first, then p1)
        ms_els = result[1][1]
        resume_ids = [el.get(f"{{{P_NS}}}resume") for el in ms_els if el.get(f"{{{P_NS}}}resume")]
        self.assertEqual(resume_ids, ["d1", "p1"])  # FIFO

    def test_milestone_tail_preserved(self):
        elements = [self._ms("urn:x-test:1", "verse text")]
        result = self._split(elements)
        ms_sub = next(els for c, els in result if c == "urn:x-test:1")
        milestone = next(el for el in ms_sub if el.tag == f"{{{TEI_NS}}}milestone")
        self.assertEqual(milestone.tail, "verse text")

    def test_multiple_milestones_each_get_own_sub_segment(self):
        elements = [
            self._ms("urn:x-test:1", "v1"),
            self._ms("urn:x-test:2", "v2"),
            self._ms("urn:x-test:3", "v3"),
        ]
        result = self._split(elements)
        corresps = [c for c, _ in result if c is not None]
        self.assertEqual(corresps, ["urn:x-test:1", "urn:x-test:2", "urn:x-test:3"])

    def test_p_resume_pushed_to_open_stack(self):
        """p:resume markers are treated as element-open for milestone splitting."""
        resume = etree.Element(f"{{{TEI_NS}}}div", nsmap=self.ns)
        resume.set(f"{{{P_NS}}}resume", "d1")
        ms = self._ms("urn:x-test:1")
        end = etree.Element(f"{{{TEI_NS}}}div", nsmap=self.ns)
        end.set(f"{{{P_NS}}}end", "d1")

        result = self._split([resume, ms, end])
        preamble_els = result[0][1]
        suspend_ids = [el.get(f"{{{P_NS}}}suspend") for el in preamble_els if el.get(f"{{{P_NS}}}suspend")]
        self.assertIn("d1", suspend_ids)


# ── _process_element_as_marker ──────────────────────────────────────────────

class TestProcessElementAsMarker(_ProcessorBase):

    def _push_context(self, proc):
        """Push a minimal processing context so _get_path_hash works."""
        proc.linear_data.processing_context.append(_ProcessingContext(
            project=proc.project,
            file_name=proc.file_name,
            element_path=None,
            from_start=None,
            to_end=None,
            before_start=False,
            after_end=False,
            include_tail_after_end=False,
            inside_deepest_common_ancestor=False,
            command=_ProcessingCommand.COPY_AND_RECURSE,
        ))

    def _pop_context(self, proc):
        proc.linear_data.processing_context.pop()

    def test_text_becomes_start_marker_tail(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.Element(f"{{{TEI_NS}}}p")
            tei_p.text = "before text"
            tei_p.tail = "after tail"
            result = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        self.assertGreater(len(result), 0)
        start_marker = result[0]
        self.assertEqual(start_marker.get(f"{{{P_NS}}}start") is not None, True)
        self.assertEqual(start_marker.tail, "before text")

    def test_tail_becomes_end_marker_tail(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.Element(f"{{{TEI_NS}}}p")
            tei_p.text = "text"
            tei_p.tail = " after element"
            result = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        end_marker = result[-1]
        self.assertIsNotNone(end_marker.get(f"{{{P_NS}}}end"))
        self.assertEqual(end_marker.tail, " after element")

    def test_start_and_end_markers_same_id(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.Element(f"{{{TEI_NS}}}p")
            result = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        start_id = result[0].get(f"{{{P_NS}}}start")
        end_id = result[-1].get(f"{{{P_NS}}}end")
        self.assertIsNotNone(start_id)
        self.assertEqual(start_id, end_id)

    def test_milestone_child_preserved_in_output(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.Element(f"{{{TEI_NS}}}p")
            ms = etree.SubElement(tei_p, f"{{{TEI_NS}}}milestone")
            ms.set("unit", "verse")
            ms.set("n", "1")
            ms.tail = "verse text"
            result = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        # Should be: [start_marker, milestone, end_marker]
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1].tag, f"{{{TEI_NS}}}milestone")
        self.assertEqual(result[1].get("unit"), "verse")
        self.assertIn("verse text", result[1].tail or "")

    def test_external_transclude_child_produces_suspend_and_resume(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.Element(f"{{{TEI_NS}}}p")
            transclude = etree.SubElement(tei_p, f"{{{J_NS}}}transclude")
            transclude.set("type", "external")
            transclude.set("target", "urn:x-test:nonexistent")
            transclude.tail = " post-transclude"
            # Mock _transclude to return None (unresolvable URN fallback)
            with patch.object(proc, "_transclude", return_value=None):
                result = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        p_start_markers = [el for el in result if el.get(f"{{{P_NS}}}start")]
        p_suspend_markers = [el for el in result if el.get(f"{{{P_NS}}}suspend")]
        p_resume_markers = [el for el in result if el.get(f"{{{P_NS}}}resume")]
        p_end_markers = [el for el in result if el.get(f"{{{P_NS}}}end")]

        self.assertEqual(len(p_start_markers), 1)
        self.assertEqual(len(p_suspend_markers), 1)
        self.assertEqual(len(p_resume_markers), 1)
        self.assertEqual(len(p_end_markers), 1)

        # All markers use the same element tag (tei:p)
        for marker in p_start_markers + p_suspend_markers + p_resume_markers + p_end_markers:
            self.assertEqual(marker.tag, f"{{{TEI_NS}}}p")

    def test_hash_reproducible_for_same_element(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            tei_p = etree.fromstring(b'<tei:p xmlns:tei="http://www.tei-c.org/ns/1.0">text</tei:p>')
            result1 = proc._process_element_as_marker(tei_p)
            proc.marker_stack = []  # reset for second call
            result2 = proc._process_element_as_marker(tei_p)
        finally:
            self._pop_context(proc)

        id1 = result1[0].get(f"{{{P_NS}}}start")
        id2 = result2[0].get(f"{{{P_NS}}}start")
        self.assertEqual(id1, id2)

    def test_nested_structural_element_gets_own_markers(self):
        proc = self._make_processor()
        proc.marker_stack = []
        self._push_context(proc)
        try:
            outer = etree.fromstring(
                b'<tei:div xmlns:tei="http://www.tei-c.org/ns/1.0"'
                b'         xmlns:j="http://jewishliturgy.org/ns/jlptei/2">'
                b'  <j:transclude type="external" target="urn:x-test:nope"/>'
                b'</tei:div>')
            # Mock _transclude to avoid URN resolution failure
            with patch.object(proc, "_transclude", return_value=None):
                result = proc._process_element_as_marker(outer)
        finally:
            self._pop_context(proc)

        # outer div markers
        div_starts = [el for el in result if el.tag == f"{{{TEI_NS}}}div" and el.get(f"{{{P_NS}}}start")]
        div_ends = [el for el in result if el.tag == f"{{{TEI_NS}}}div" and el.get(f"{{{P_NS}}}end")]
        self.assertEqual(len(div_starts), 1)
        self.assertEqual(len(div_ends), 1)


# ── _in_parallel_compilation flag ───────────────────────────────────────────

class TestParallelCompilationFlag(_ProcessorBase):

    def test_in_parallel_compilation_suppresses_root_trigger(self):
        """_in_parallel_compilation=True means process() skips _process_parallel_root."""
        self.linear_data.parallel_projects = ["some-proj"]
        proc = self._make_processor(_in_parallel_compilation=True)

        with patch.object(proc, "_process_parallel_root") as mock_root:
            proc.process()
            mock_root.assert_not_called()

    def test_in_parallel_compilation_false_triggers_root(self):
        """Without the flag, parallel_projects causes _process_parallel_root to be called."""
        self.linear_data.parallel_projects = ["some-proj"]
        proc = self._make_processor(_in_parallel_compilation=False)

        with patch.object(proc, "_process_parallel_root", return_value=[]) as mock_root:
            proc.process()
            mock_root.assert_called_once()

    def test_structural_elements_always_get_markers_in_marker_mode(self):
        """In marker mode, all structural elements get start/end marker pairs."""
        proc = self._make_processor(_in_parallel_compilation=True)
        proc.marker_stack = []
        self.linear_data.parallel_projects = ["par-proj"]

        result = proc.process()

        result_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        self.assertIn(":start=", result_xml)


if __name__ == "__main__":
    unittest.main()
