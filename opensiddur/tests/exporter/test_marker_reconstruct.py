"""Tests for flattened parallel marker reconstruction (compiler output stage)."""

import unittest
import unittest.mock

from lxml import etree

from opensiddur.exporter.external_compiler import PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.marker_reconstruct import (
    doc_needs_marker_reconstruction,
    reconstruct_markered_document,
    reconstruct_parallel_item,
    substantive_content,
)
from opensiddur.exporter import marker_reconstruct as mr

P_NS = PROCESSING_NAMESPACE


class TestMarkerReconstruct(unittest.TestCase):

    def test_doc_needs_parallel(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body><p:parallel><p:parallelItem role="primary"/>
          </p:parallel></tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        self.assertTrue(doc_needs_marker_reconstruction(root))

    def test_legacy_body_no_reconstruct_flag(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}"><tei:text><tei:body>
          <tei:div><tei:p>Hello</tei:p></tei:div>
        </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        self.assertFalse(doc_needs_marker_reconstruction(root))

    def test_whole_start_to_end_has_no_p_part(self):
        ns = {"tei": TEI_NS, "p": P_NS}
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <p:parallel><p:parallelItem role="primary" xml:lang="he">
              <tei:div p:start="x" n="a"/>
              <tei:head>H</tei:head>
              <tei:p p:start="y"><tei:hi>in</tei:hi></tei:p>
              <tei:p p:end="y"/>
              <tei:div p:end="x"/>
            </p:parallelItem><p:parallelItem role="parallel" xml:lang="en">
              <tei:div p:start="x2" n="a"/>
              <tei:head>E</tei:head>
              <tei:p p:start="y2">en</tei:p>
              <tei:p p:end="y2"/>
              <tei:div p:end="x2"/>
            </p:parallelItem></p:parallel>
          </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        reconstruct_markered_document(root)
        divs = root.xpath("//tei:div[@n='a']", namespaces=ns)
        self.assertEqual(len(divs), 2)
        for d in divs:
            self.assertIsNone(d.get(f"{{{P_NS}}}part"))
            self.assertIsNone(d.get(f"{{{P_NS}}}start"))

    def test_split_segments_get_p_part(self):
        ns = {"tei": TEI_NS, "p": P_NS}
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <p:parallel><p:parallelItem role="primary">
              <tei:p p:start="a">A</tei:p>
              <tei:p p:suspend="a"/>
            </p:parallelItem></p:parallel>
            <p:parallel><p:parallelItem role="primary">
              <tei:p p:resume="a">B</tei:p>
              <tei:p p:end="a"/>
            </p:parallelItem></p:parallel>
          </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        reconstruct_markered_document(root)
        parts = [
            el.get(f"{{{P_NS}}}part")
            for el in root.xpath("//tei:p", namespaces=ns)
            if el.get(f"{{{P_NS}}}part")
        ]
        self.assertEqual(parts, ["first", "last"])

    def test_empty_segment_dropped_and_relabeled(self):
        ns = {"tei": TEI_NS, "p": P_NS}
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <p:parallel><p:parallelItem role="primary">
              <tei:p p:start="a"/>
              <tei:p p:suspend="a"/>
            </p:parallelItem></p:parallel>
            <p:parallel><p:parallelItem role="primary">
              <tei:p p:resume="a">Only</tei:p>
              <tei:p p:end="a"/>
            </p:parallelItem></p:parallel>
          </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        reconstruct_markered_document(root)
        ps = root.xpath("//tei:p", namespaces=ns)
        self.assertEqual(len(ps), 1)
        self.assertIsNone(ps[0].get(f"{{{P_NS}}}part"))
        self.assertIn("Only", "".join(ps[0].itertext()))

    def test_substantive_content_milestone_tail(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}">
          <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode())
        p = root.find(f".//{{{TEI_NS}}}p")
        self.assertTrue(substantive_content(p))

    def test_substantive_content_nested_child_text(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}">
          <tei:p><tei:hi><tei:seg>deep</tei:seg></tei:hi></tei:p>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode())
        p = root.find(f".//{{{TEI_NS}}}p")
        self.assertTrue(substantive_content(p))

    def test_reconstruct_parallel_item_raises_on_unclosed_stack(self):
        xml = f"""<p:parallelItem xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:div p:start="x">dangling</tei:div>
        </p:parallelItem>"""
        pi = etree.fromstring(xml.encode())
        with self.assertRaises(ValueError):
            reconstruct_parallel_item(pi, mr.defaultdict(dict))

    def test_close_open_segment_validates_stack_and_pid(self):
        stack: list[mr._Frame] = []
        fragments: list[etree.ElementBase] = []
        pid_state: dict[str, dict] = {}

        with self.assertRaises(ValueError):
            mr._close_open_segment(stack, fragments, pid_state, pid="x", kind="end")

        stack.append(mr._Frame("a", f"{{{TEI_NS}}}div", {}, []))
        with self.assertRaises(ValueError):
            mr._close_open_segment(stack, fragments, pid_state, pid="b", kind="end")

        stack.append(mr._Frame("c", f"{{{TEI_NS}}}div", {}, []))
        with self.assertRaises(ValueError):
            mr._close_open_segment(stack, fragments, pid_state, pid="c", kind="bogus")

    def test_new_wrapped_segment_strips_processing_markers(self):
        child = etree.Element(f"{{{TEI_NS}}}p", nsmap={"tei": TEI_NS, "p": P_NS})
        el = mr._new_wrapped_segment(
            f"{{{TEI_NS}}}div",
            {
                mr._P_START: "s",
                mr._P_END: "e",
                mr._P_SUSPEND: "su",
                mr._P_RESUME: "r",
                mr._P_LOGICAL: "lid",
                mr._P_PART: "first",
            },
            [child],
            logical_id=None,
            leading_text_chunks=[],
        )
        for mk in (mr._P_START, mr._P_END, mr._P_SUSPEND, mr._P_RESUME, mr._P_LOGICAL, mr._P_PART):
            self.assertIsNone(el.get(mk))

    def test_normalize_segment_parts_strips_stray_markers_and_sets_middle(self):
        ns = {"tei": TEI_NS, "p": P_NS}
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <tei:p p:logical-id="a" p:start="x">one</tei:p>
            <tei:p p:logical-id="a" p:part="ignored">two</tei:p>
            <tei:p p:logical-id="a" p:end="x">three</tei:p>
          </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        mr.normalize_segment_parts(root)

        ps = root.xpath("//tei:p", namespaces=ns)
        self.assertEqual([p.get(f"{{{P_NS}}}part") for p in ps], ["first", "middle", "last"])
        for p in ps:
            self.assertIsNone(p.get(f"{{{P_NS}}}logical-id"))
            self.assertIsNone(p.get(f"{{{P_NS}}}start"))
            self.assertIsNone(p.get(f"{{{P_NS}}}end"))

    def test_strip_processing_markers_from_header(self):
        ns = {"tei": TEI_NS, "p": P_NS}
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:teiHeader>
            <tei:fileDesc>
              <tei:titleStmt>
                <tei:title p:start="x" p:logical-id="lid">T</tei:title>
              </tei:titleStmt>
            </tei:fileDesc>
          </tei:teiHeader>
          <tei:text><tei:body>
            <p:parallel><p:parallelItem role="primary">
              <tei:p p:start="a">A</tei:p><tei:p p:end="a"/>
            </p:parallelItem></p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode())
        header = root.xpath("//tei:teiHeader", namespaces=ns)[0]
        title = root.xpath("//tei:title", namespaces=ns)[0]
        self.assertIn(f"{{{P_NS}}}start", title.attrib)
        self.assertIn(f"{{{P_NS}}}logical-id", title.attrib)
        reconstruct_markered_document(root)
        self.assertIsNone(title.get(f"{{{P_NS}}}start"))
        self.assertIsNone(title.get(f"{{{P_NS}}}logical-id"))

        # Also cover the helper directly to ensure marker stripping is executed.
        title.set(f"{{{P_NS}}}start", "x2")
        mr._strip_stray_processing_markers_under(header)
        self.assertIsNone(title.get(f"{{{P_NS}}}start"))

    def test_doc_needs_marker_reconstruction_structural_marker(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <tei:div p:start="x"><tei:p>Hi</tei:p></tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode())
        self.assertTrue(doc_needs_marker_reconstruction(root))

    def test_reconstruct_parallel_item_moves_structural_with_unknown_marker(self):
        # _structural_marker_map normally only returns start/end/suspend/resume.
        # Patch it to simulate a future/unknown marker key so we hit the fallback move path.
        xml = f"""<p:parallelItem xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:div p:start="x"/><tei:div p:end="x"/>
        </p:parallelItem>"""
        pi = etree.fromstring(xml.encode())
        with unittest.mock.patch.object(mr, "_structural_marker_map", return_value={"unknown": "z"}):
            reconstruct_parallel_item(pi, mr.defaultdict(dict))
        self.assertEqual(len(pi), 2)
