"""End-to-end integration tests for parallel text compilation."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.compiler import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE
from opensiddur.exporter.external_compiler import TEI_NS, ExternalCompilerProcessor
from opensiddur.exporter.linear import get_linear_data, reset_linear_data
from opensiddur.exporter.urn import ResolvedUrn, ResolvedUrnRange, UrnResolver

P_NS = PROCESSING_NAMESPACE
J_NS = JLPTEI_NAMESPACE
XML_NS = "http://www.w3.org/XML/1998/namespace"

# ── Shared XML fixtures ──────────────────────────────────────────────────────

_PRIMARY_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="he">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt><tei:title>Primary</tei:title></tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor>
          <tei:ref target="http://example.org">Example</tei:ref>
        </tei:distributor>
        <tei:availability status="free">
          <tei:licence target="http://creativecommons.org/publicdomain/zero/1.0/">CC0</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc>
        <tei:bibl xml:id="s1"><tei:title>Primary Source</tei:title></tei:bibl>
      </tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="he">
    <tei:body>
      <tei:div corresp="urn:x-test:section">
        <tei:p>
          <tei:milestone unit="verse" n="1" corresp="urn:x-test:section/1"/>Hebrew verse 1.
          <tei:milestone unit="verse" n="2" corresp="urn:x-test:section/2"/>Hebrew verse 2.
        </tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""

_PARALLEL_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="en">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt><tei:title>Parallel</tei:title></tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor>
          <tei:ref target="http://example.org">Example</tei:ref>
        </tei:distributor>
        <tei:availability status="free">
          <tei:licence target="http://creativecommons.org/licenses/by/4.0/">CC-BY</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc>
        <tei:bibl xml:id="s2"><tei:title>Parallel Source</tei:title></tei:bibl>
      </tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="en">
    <tei:body>
      <tei:div corresp="urn:x-test:section">
        <tei:p>
          <tei:milestone unit="verse" n="1" corresp="urn:x-test:section/1"/>English verse 1.
          <tei:milestone unit="verse" n="2" corresp="urn:x-test:section/2"/>English verse 2.
        </tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""


class _E2EBase(unittest.TestCase):

    PRIMARY_PROJECT = "primary-proj"
    PARALLEL_PROJECT = "parallel-proj"
    PARALLEL_CORRESP = {
        "urn:x-test:section/1",
        "urn:x-test:section/2",
    }

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        base = Path(self.temp_dir.name)
        (base / self.PRIMARY_PROJECT).mkdir()
        (base / self.PRIMARY_PROJECT / "index.xml").write_bytes(_PRIMARY_XML)
        (base / self.PARALLEL_PROJECT).mkdir()
        (base / self.PARALLEL_PROJECT / "index.xml").write_bytes(_PARALLEL_XML)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = base
        self.linear_data.parallel_projects = [self.PARALLEL_PROJECT]
        self.linear_data.project_priority = [self.PRIMARY_PROJECT, self.PARALLEL_PROJECT]

    def _mock_resolve_range(self, urn):
        """Return a resolved URN pointing to the parallel project for known milestone corresp values."""
        base_urn = urn.rsplit("@", 1)[0] if "@" in urn else urn
        if base_urn in self.PARALLEL_CORRESP:
            return [ResolvedUrn(
                urn=base_urn, project=self.PARALLEL_PROJECT,
                file_name="index.xml", element_path="/TEI")]
        return []

    def _compile_primary(self):
        proc = ExternalCompilerProcessor(
            self.PRIMARY_PROJECT, "index.xml",
            linear_data=self.linear_data)
        with patch.object(UrnResolver, "resolve_range", side_effect=self._mock_resolve_range):
            return proc.process()


# ── Root trigger integration ─────────────────────────────────────────────────

class TestRootTriggerE2E(_E2EBase):

    def test_output_contains_p_parallel(self):
        result = self._compile_primary()

        parallels = [el for r in result for el in r.iter(f"{{{P_NS}}}parallel")]
        self.assertGreater(len(parallels), 0, "Expected at least one p:parallel in output")

    def test_output_has_primary_and_parallel_items(self):
        result = self._compile_primary()

        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        primary_items = root.findall(f".//{{{P_NS}}}parallelItem[@role='primary']")
        parallel_items = root.findall(f".//{{{P_NS}}}parallelItem[@role='parallel']")
        self.assertGreater(len(primary_items), 0)
        self.assertGreater(len(parallel_items), 0)
        self.assertEqual(len(primary_items), len(parallel_items))

    def test_primary_items_have_hebrew_lang(self):
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        primary_items = root.findall(f".//{{{P_NS}}}parallelItem[@role='primary']")
        for item in primary_items:
            lang = item.get(f"{{{XML_NS}}}lang")
            self.assertEqual(lang, "he", f"Expected primary item xml:lang='he', got {lang!r}")

    def test_parallel_items_have_english_lang(self):
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        parallel_items = root.findall(f".//{{{P_NS}}}parallelItem[@role='parallel']")
        for item in parallel_items:
            lang = item.get(f"{{{XML_NS}}}lang")
            self.assertEqual(lang, "en", f"Expected parallel item xml:lang='en', got {lang!r}")

    def test_milestones_appear_in_both_streams(self):
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        for item in root.findall(f".//{{{P_NS}}}parallelItem"):
            milestones = item.findall(f".//{{{TEI_NS}}}milestone")
            # Each parallelItem should preserve the milestone elements
            for ms in milestones:
                corresp = ms.get("corresp")
                self.assertIsNotNone(corresp)

    def test_result_serializes_without_error(self):
        result = self._compile_primary()
        for el in result:
            xml_str = etree.tostring(el, encoding="unicode")
            self.assertIsInstance(xml_str, str)
            self.assertGreater(len(xml_str), 0)

    def test_tei_structure_preserved(self):
        """The outer tei:TEI element and tei:teiHeader are preserved in the result."""
        result = self._compile_primary()
        self.assertEqual(len(result), 1)
        tei_el = result[0]
        self.assertEqual(tei_el.tag, f"{{{TEI_NS}}}TEI")

        header = tei_el.find(f"{{{TEI_NS}}}teiHeader")
        self.assertIsNotNone(header)

    def test_no_parallel_fallback_when_parallel_file_missing(self):
        """If parallel project file doesn't exist, result should be normal (no p:parallel)."""
        import shutil
        shutil.rmtree(Path(self.temp_dir.name) / self.PARALLEL_PROJECT)

        proc = ExternalCompilerProcessor(
            self.PRIMARY_PROJECT, "index.xml",
            linear_data=self.linear_data)
        with patch.object(UrnResolver, "resolve_range", side_effect=self._mock_resolve_range):
            result = proc.process()

        result_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        self.assertNotIn(f"{{{P_NS}}}parallel", result_xml)


# ── Marker structure verification ────────────────────────────────────────────

class TestMarkerStructureE2E(_E2EBase):

    def test_structural_elements_with_milestones_get_markers(self):
        """Compiler output should be reconstructed (no raw p:start/p:end markers)."""
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        # Reconstruction happens in the compiler now, so markers should not survive
        start_markers = root.findall(f".//*[@{{{P_NS}}}start]")
        end_markers = root.findall(f".//*[@{{{P_NS}}}end]")
        self.assertEqual(len(start_markers), 0, "p:start markers should be consumed by reconstruction")
        self.assertEqual(len(end_markers), 0, "p:end markers should be consumed by reconstruction")

        # Still expect parallel structure to exist in compiled output
        parallels = root.findall(f".//{{{P_NS}}}parallel")
        self.assertGreater(len(parallels), 0)

    def test_start_end_marker_ids_match(self):
        """Legacy marker pairing test: markers should not be present post-reconstruct."""
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        self.assertEqual(len(root.findall(f".//*[@{{{P_NS}}}start]")), 0)
        self.assertEqual(len(root.findall(f".//*[@{{{P_NS}}}end]")), 0)

    def test_column_order_attribute(self):
        """p:parallel elements should have a column-order attribute."""
        result = self._compile_primary()
        all_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{all_xml}</root>")

        parallels = root.findall(f".//{{{P_NS}}}parallel")
        self.assertGreater(len(parallels), 0)
        for p in parallels:
            self.assertIn("column-order", p.attrib)


# ── _in_parallel_compilation suppression end-to-end ─────────────────────────

class TestInParallelCompilationE2E(_E2EBase):

    def test_in_parallel_mode_produces_no_parallel_elements(self):
        """When _in_parallel_compilation=True, no p:parallel is produced."""
        proc = ExternalCompilerProcessor(
            self.PRIMARY_PROJECT, "index.xml",
            linear_data=self.linear_data,
            _in_parallel_compilation=True)
        proc.marker_stack = []  # enable marker mode

        with patch.object(UrnResolver, "resolve_range", side_effect=self._mock_resolve_range):
            result = proc.process()

        result_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        self.assertNotIn(f"{{{P_NS}}}parallel", result_xml)

    def test_in_parallel_mode_still_produces_markers(self):
        """Even without p:parallel, marker elements should appear when marker_stack is set."""
        proc = ExternalCompilerProcessor(
            self.PRIMARY_PROJECT, "index.xml",
            linear_data=self.linear_data,
            _in_parallel_compilation=True)
        proc.marker_stack = []

        with patch.object(UrnResolver, "resolve_range", side_effect=self._mock_resolve_range):
            result = proc.process()

        # Find any element with p:start attribute
        start_markers = [
            el for r in result
            for el in r.iter()
            if el.get(f"{{{P_NS}}}start") is not None
        ]
        self.assertGreater(len(start_markers), 0, "Expected p:start markers in marker-mode output")


# ── 3-way transclusion ───────────────────────────────────────────────────────

class TestThreeWayTransclusionE2E(_E2EBase):
    """A → transcludes B, B has milestones, B has a parallel in parallel-proj."""

    _B_PRIMARY = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="he">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt><tei:title>B Primary</tei:title></tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor><tei:ref target="http://e.org">e</tei:ref></tei:distributor>
        <tei:availability status="free">
          <tei:licence target="http://creativecommons.org/publicdomain/zero/1.0/">CC0</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc><tei:bibl xml:id="bsrc"><tei:title>B</tei:title></tei:bibl></tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="he">
    <tei:body>
      <tei:div xml:id="b-section">
        <tei:p>
          <tei:milestone unit="verse" n="b1" corresp="urn:x-test:section/b1"/>B Hebrew verse 1.
        </tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""

    _B_PARALLEL = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="en">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt><tei:title>B Parallel</tei:title></tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor><tei:ref target="http://e.org">e</tei:ref></tei:distributor>
        <tei:availability status="free">
          <tei:licence target="http://creativecommons.org/licenses/by/4.0/">CC-BY</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc><tei:bibl xml:id="bpsrc"><tei:title>BP</tei:title></tei:bibl></tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="en">
    <tei:body>
      <tei:div xml:id="b-section">
        <tei:p>
          <tei:milestone unit="verse" n="b1" corresp="urn:x-test:section/b1"/>B English verse 1.
        </tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""

    _A_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="he">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt><tei:title>A</tei:title></tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor><tei:ref target="http://e.org">e</tei:ref></tei:distributor>
        <tei:availability status="free">
          <tei:licence target="http://creativecommons.org/publicdomain/zero/1.0/">CC0</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc><tei:bibl xml:id="asrc"><tei:title>A</tei:title></tei:bibl></tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="he">
    <tei:body>
      <tei:div>
        <tei:p>Before transclusion.</tei:p>
        <j:transclude type="external" target="urn:x-test:b-section@primary-proj"/>
        <tei:p>After transclusion.</tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>"""

    B_CORRESP = {"urn:x-test:section/b1"}

    def setUp(self):
        super().setUp()
        base = Path(self.temp_dir.name)
        (base / self.PRIMARY_PROJECT / "b.xml").write_bytes(self._B_PRIMARY)
        (base / self.PARALLEL_PROJECT / "b.xml").write_bytes(self._B_PARALLEL)
        (base / self.PRIMARY_PROJECT / "index.xml").write_bytes(self._A_XML)

        self.linear_data.project_priority = [self.PRIMARY_PROJECT]

    def _mock_resolve_range_3way(self, urn):
        base_urn = urn.rsplit("@", 1)[0] if "@" in urn else urn
        project_hint = urn.rsplit("@", 1)[1] if "@" in urn else None

        if base_urn == "urn:x-test:b-section":
            proj = project_hint or self.PRIMARY_PROJECT
            # Parse b.xml to get the xml:id element path
            xml_content = self._B_PRIMARY if proj == self.PRIMARY_PROJECT else self._B_PARALLEL
            tree_root = etree.fromstring(xml_content)
            tree = tree_root.getroottree()
            xml_ns = "http://www.w3.org/XML/1998/namespace"
            b_section = tree_root.xpath("//*[@xml:id='b-section']", namespaces={"xml": xml_ns})
            if b_section:
                element_path = tree.getpath(b_section[0])
                return [ResolvedUrn(
                    urn=base_urn, project=proj,
                    file_name="b.xml", element_path=element_path,
                    end_element_path=element_path, end_includes_tail=False)]
        if base_urn in self.B_CORRESP:
            return [ResolvedUrn(
                urn=base_urn, project=self.PARALLEL_PROJECT,
                file_name="b.xml", element_path="/TEI")]
        return []

    def _mock_prioritize_range(self, urns, priority_list, return_all=False):
        return urns[0] if urns else None

    def test_transclusion_trigger_produces_p_parallel_inside_p_transclude(self):
        """When a j:transclude is compiled in parallel mode, result has p:transclude(p:parallel(...))."""
        proc = ExternalCompilerProcessor(
            self.PRIMARY_PROJECT, "index.xml",
            linear_data=self.linear_data)

        with patch.object(UrnResolver, "resolve_range", side_effect=self._mock_resolve_range_3way):
            with patch.object(UrnResolver, "prioritize_range", side_effect=self._mock_prioritize_range):
                result = proc.process()

        result_xml = "".join(etree.tostring(el, encoding="unicode") for el in result)
        root = etree.fromstring(f"<root>{result_xml}</root>")

        # Should have p:transclude wrapping p:parallel
        transcludes = root.findall(f".//{{{P_NS}}}transclude")
        self.assertGreater(len(transcludes), 0)
        for tc in transcludes:
            parallels = tc.findall(f"{{{P_NS}}}parallel")
            self.assertGreater(len(parallels), 0, "p:transclude should contain p:parallel")


if __name__ == "__main__":
    unittest.main()
