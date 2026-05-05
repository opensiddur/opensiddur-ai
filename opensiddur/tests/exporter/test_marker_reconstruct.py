"""Tests for flattened parallel marker reconstruction (Pass 1 before XeLaTeX)."""

import unittest

from lxml import etree

from opensiddur.common.xslt import xslt_transform_string
from opensiddur.exporter.external_compiler import PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.tex.marker_reconstruct import (
    doc_needs_marker_reconstruction,
    reconstruct_markered_document,
    substantive_content,
)
from opensiddur.exporter.tex.xelatex import XSLT_FILE

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

    def test_xslt_parallel_row_after_reconstruct(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}" xmlns:p="{P_NS}">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p>שלום</tei:p></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p>Hello</tei:p></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text></tei:TEI>"""
        root = etree.fromstring(xml.encode())
        reconstruct_markered_document(root)
        out = xslt_transform_string(
            XSLT_FILE,
            etree.tostring(root, encoding="unicode"),
            xslt_params={"additional-preamble": "", "additional-postamble": ""},
        )
        self.assertIn(r"\begin{minipage}", out)
        self.assertIn("שלום", out)
        self.assertIn("Hello", out)

    def test_substantive_content_milestone_tail(self):
        xml = f"""<tei:TEI xmlns:tei="{TEI_NS}">
          <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode())
        p = root.find(f".//{{{TEI_NS}}}p")
        self.assertTrue(substantive_content(p))
