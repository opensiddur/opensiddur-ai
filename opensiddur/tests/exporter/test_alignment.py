"""Tests for alignment/parallel text processing.

Covers compiler.py lines:
  163       - _lookup_alignment returns None when alignment_urn not found
  190-191   - _plan_alignment XPath lookup for ranged end element
  356-385   - _process_alignment_before (parallelBlock/parallelInternal creation)
  397-413   - _process_alignment_after (parallelBlock/parallelInternal end markers)

Desired output structure
------------------------
For a SINGLE-ELEMENT alignment (v1 is both start and end):

  <p:parallelBlock urn="urn:...">
    <p:parallelExternal>
      [compiled parallel text]
    </p:parallelExternal>
    <p:parallelInternal>
      <tei:ab xml:id="v1_...">verse one</tei:ab>   ← aligned primary verse
    </p:parallelInternal>
  </p:parallelBlock>
  <tei:ab xml:id="v2_...">verse two</tei:ab>        ← unaligned, outside block

For a RANGED alignment (v1 = start, v2 = end):

  <p:parallelBlock urn="urn:...">
    <p:parallelExternal>
      [compiled parallel text]
    </p:parallelExternal>
    <p:parallelInternal>
      <tei:ab xml:id="v1_...">verse one</tei:ab>
      <tei:ab xml:id="v2_...">verse two</tei:ab>   ← both verses inside
    </p:parallelInternal>
  </p:parallelBlock>

"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from lxml import etree

from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import reset_linear_data, get_linear_data
from opensiddur.exporter.refdb import ReferenceDatabase, UrnMapping

TEI_NS = 'http://www.tei-c.org/ns/1.0'
PROCESSING_NS = 'http://jewishliturgy.org/ns/processing'
NS = {'tei': TEI_NS, 'p': PROCESSING_NS}


def make_urn_mapping(*, urn, project, file_name, element_path, element_tag,
                     end_element_path=None, end_includes_tail=False):
    return UrnMapping(
        urn=urn,
        project=project,
        file_name=file_name,
        element_path=element_path,
        element_tag=element_tag,
        element_type=None,
        end_element_path=end_element_path or element_path,
        end_includes_tail=end_includes_tail,
    )


# Primary file: one aligned verse (v1) and one un-aligned verse (v2).
# The corresp element must be inside tei:text for _plan_alignment to find it.
PRIMARY_XML = b'''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:text xml:lang="he">
    <tei:body>
      <tei:ab xml:id="v1" corresp="urn:example:text/1">verse one</tei:ab>
      <tei:ab xml:id="v2">verse two</tei:ab>
    </tei:body>
  </tei:text>
</tei:TEI>'''

# Parallel file: one verse aligned to the primary's verse 1.
PARALLEL_XML = b'''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:text xml:lang="en">
    <tei:body>
      <tei:ab xml:id="pv1" corresp="urn:example:text/1">parallel one</tei:ab>
    </tei:body>
  </tei:text>
</tei:TEI>'''

# Hard-coded XPaths: deterministic for the XML above.
PRIMARY_V1_PATH = '/tei:TEI/tei:text/tei:body/tei:ab[1]'
PRIMARY_V2_PATH = '/tei:TEI/tei:text/tei:body/tei:ab[2]'
PARALLEL_PV1_PATH = '/tei:TEI/tei:text/tei:body/tei:ab[1]'


class _AlignmentTestBase(unittest.TestCase):
    """Common setUp for alignment tests using two projects."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        primary_dir = Path(self.temp_dir.name) / 'primary_project'
        parallel_dir = Path(self.temp_dir.name) / 'parallel_project'
        primary_dir.mkdir(parents=True)
        parallel_dir.mkdir(parents=True)
        (primary_dir / 'primary.xml').write_bytes(PRIMARY_XML)
        (parallel_dir / 'parallel.xml').write_bytes(PARALLEL_XML)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)
        self.linear_data.project_priority = ['primary_project']
        self.linear_data.alignment_priority = ['parallel_project']

        self.refdb = MagicMock(spec=ReferenceDatabase)
        self.refdb.get_references_to.return_value = []
        # urn:example:text/1 resolves to both projects (primary and parallel)
        self.refdb.get_urn_mappings.return_value = [
            make_urn_mapping(
                urn='urn:example:text/1',
                project='primary_project',
                file_name='primary.xml',
                element_path=PRIMARY_V1_PATH,
                element_tag=f'{{{TEI_NS}}}ab',
            ),
            make_urn_mapping(
                urn='urn:example:text/1',
                project='parallel_project',
                file_name='parallel.xml',
                element_path=PARALLEL_PV1_PATH,
                element_tag=f'{{{TEI_NS}}}ab',
            ),
        ]

    def _process_primary(self):
        processor = ExternalCompilerProcessor(
            'primary_project', 'primary.xml',
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        result = processor.process()
        self.assertEqual(len(result), 1)
        return result[0]


class TestAlignmentMarkersPresent(_AlignmentTestBase):
    """Tests for _process_alignment_before (lines 356-385) and _process_alignment_after (lines 397-413).

    Desired output for a single-element alignment:
      <p:parallelBlock urn="...">
        <p:parallelExternal>[parallel text]</p:parallelExternal>
        <p:parallelInternal>
          <tei:ab>verse one</tei:ab>   ← aligned verse INSIDE
        </p:parallelInternal>
      </p:parallelBlock>
      <tei:ab>verse two</tei:ab>       ← unaligned verse OUTSIDE
    """

    def test_parallel_block_present_in_output(self):
        """A p:parallelBlock element is produced for each aligned corresp element."""
        root = self._process_primary()
        blocks = root.xpath('.//p:parallelBlock', namespaces=NS)
        self.assertEqual(len(blocks), 1, "Expected exactly one parallelBlock")

    def test_parallel_block_has_urn_attribute(self):
        """The p:parallelBlock element carries a urn= attribute with the alignment URN."""
        root = self._process_primary()
        blocks = root.xpath('.//p:parallelBlock[@urn]', namespaces=NS)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].get('urn'), 'urn:example:text/1')

    def test_parallel_block_no_residual_start_end_attributes(self):
        """After unflattening, p:parallelBlock has no p:start or p:end attribute."""
        root = self._process_primary()
        blocks = root.xpath('.//p:parallelBlock', namespaces=NS)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertNotIn(f'{{{PROCESSING_NS}}}start', block.attrib)
        self.assertNotIn(f'{{{PROCESSING_NS}}}end', block.attrib)

    def test_parallel_external_present_inside_parallel_block(self):
        """A p:parallelExternal element is a direct child of p:parallelBlock."""
        root = self._process_primary()
        externals = root.xpath('.//p:parallelBlock/p:parallelExternal', namespaces=NS)
        self.assertEqual(len(externals), 1)

    def test_parallel_external_contains_parallel_text(self):
        """p:parallelExternal contains the parallel project's text content."""
        root = self._process_primary()
        externals = root.xpath('.//p:parallelExternal', namespaces=NS)
        self.assertEqual(len(externals), 1)
        self.assertIn('parallel one', etree.tostring(externals[0], encoding='unicode'))

    def test_parallel_internal_present_inside_parallel_block(self):
        """A p:parallelInternal element is produced inside p:parallelBlock."""
        root = self._process_primary()
        internals = root.xpath('.//p:parallelBlock/p:parallelInternal', namespaces=NS)
        self.assertEqual(len(internals), 1, "Expected one parallelInternal inside parallelBlock")

    # --- DESIRED BEHAVIOR (currently fails due to Bug 1) ---

    def test_parallel_internal_contains_aligned_verse(self):
        """DESIRED: p:parallelInternal contains the aligned primary verse (v1).

        Currently fails because _process_alignment_after fires before the element
        is appended to processed, so parallelInternal is closed immediately (empty)
        and v1 ends up outside the block.  (Bug 1)
        """
        root = self._process_primary()
        internals = root.xpath('.//p:parallelBlock/p:parallelInternal', namespaces=NS)
        self.assertEqual(len(internals), 1)
        internal_str = etree.tostring(internals[0], encoding='unicode')
        self.assertIn('verse one', internal_str,
                      "Aligned verse should be inside p:parallelInternal")

    def test_unaligned_verse_outside_parallel_block(self):
        """DESIRED: The unaligned verse (v2) is a sibling of p:parallelBlock, not inside it."""
        root = self._process_primary()
        # v2 should NOT appear inside parallelBlock
        block_str = etree.tostring(root.xpath('.//p:parallelBlock', namespaces=NS)[0],
                                   encoding='unicode')
        self.assertNotIn('verse two', block_str,
                         "Unaligned verse two should not be inside p:parallelBlock")
        # but it SHOULD appear in the document
        self.assertIn('verse two', etree.tostring(root, encoding='unicode'))

    # --- END DESIRED BEHAVIOR ---

    def test_primary_text_preserved(self):
        """Primary text content is present in the output alongside the parallel text."""
        root = self._process_primary()
        result_str = etree.tostring(root, encoding='unicode')
        self.assertIn('verse one', result_str)
        self.assertIn('verse two', result_str)

    def test_only_one_parallel_block_for_one_aligned_element(self):
        """Exactly one parallelBlock is produced (v2 has no corresp, so no second block)."""
        root = self._process_primary()
        blocks = root.xpath('.//p:parallelBlock', namespaces=NS)
        self.assertEqual(len(blocks), 1)


class TestAlignmentDisabled(_AlignmentTestBase):
    """Tests that verify no alignment occurs when configuration prevents it."""

    def test_no_markers_when_alignment_priority_empty(self):
        """No parallel markers when alignment_priority is empty."""
        self.linear_data.alignment_priority = []
        root = self._process_primary()
        result_str = etree.tostring(root, encoding='unicode')
        self.assertNotIn('parallelBlock', result_str)
        self.assertNotIn('parallelExternal', result_str)

    def test_no_markers_when_only_self_project_in_priority(self):
        """No parallel markers when alignment_priority only contains the source project (line 149)."""
        self.linear_data.alignment_priority = ['primary_project']
        root = self._process_primary()
        result_str = etree.tostring(root, encoding='unicode')
        self.assertNotIn('parallelBlock', result_str)
        self.assertNotIn('parallelExternal', result_str)


class TestLookupAlignmentNoMatch(unittest.TestCase):
    """Tests for line 163: _lookup_alignment returns None when alignment_urn not resolved."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        project_dir = Path(self.temp_dir.name) / 'primary_project'
        project_dir.mkdir(parents=True)
        (project_dir / 'primary.xml').write_bytes(PRIMARY_XML)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)
        self.linear_data.project_priority = ['primary_project']
        # The alignment priority targets a project that has no URN mapping
        self.linear_data.alignment_priority = ['nonexistent_project']

        self.refdb = MagicMock(spec=ReferenceDatabase)
        self.refdb.get_references_to.return_value = []
        # URN only resolves to primary_project, not to nonexistent_project
        self.refdb.get_urn_mappings.return_value = [
            make_urn_mapping(
                urn='urn:example:text/1',
                project='primary_project',
                file_name='primary.xml',
                element_path=PRIMARY_V1_PATH,
                element_tag=f'{{{TEI_NS}}}ab',
            ),
        ]

    def test_no_alignment_when_urn_not_in_alignment_project(self):
        """No parallel markers when the corresp URN doesn't resolve to any alignment_priority project
        (exercises the `return None` at line 163 of compiler.py)."""
        processor = ExternalCompilerProcessor(
            'primary_project', 'primary.xml',
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        result = processor.process()
        self.assertEqual(len(result), 1)
        result_str = etree.tostring(result[0], encoding='unicode')
        self.assertNotIn('parallelBlock', result_str)
        self.assertIn('verse one', result_str)


class TestAlignmentRangedEndElement(unittest.TestCase):
    """Tests for lines 190-191: _plan_alignment resolves end element via XPath when it differs from start.

    When self_urn.end_element_path != self_urn.element_path the compiler does an XPath lookup
    to find the actual end element (lines 190-191 of compiler.py).

    Desired output for a ranged alignment (v1=start, v2=end):
      <p:parallelBlock urn="...">
        <p:parallelExternal>[parallel text]</p:parallelExternal>
        <p:parallelInternal>
          <tei:ab>verse one</tei:ab>
          <tei:ab>verse two</tei:ab>   ← both inside
        </p:parallelInternal>
      </p:parallelBlock>
    """

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        primary_dir = Path(self.temp_dir.name) / 'primary_project'
        parallel_dir = Path(self.temp_dir.name) / 'parallel_project'
        primary_dir.mkdir(parents=True)
        parallel_dir.mkdir(parents=True)

        # Primary: corresp on v1, but the self_urn range covers v1 through v2
        primary_xml = b'''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:text xml:lang="he">
    <tei:body>
      <tei:ab xml:id="v1" corresp="urn:example:range/1">verse one</tei:ab>
      <tei:ab xml:id="v2">verse two</tei:ab>
    </tei:body>
  </tei:text>
</tei:TEI>'''
        # Parallel: a single element that corresponds to the whole range
        parallel_xml = b'''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:text xml:lang="en">
    <tei:body>
      <tei:ab xml:id="pv1" corresp="urn:example:range/1">parallel covering both</tei:ab>
    </tei:body>
  </tei:text>
</tei:TEI>'''

        (primary_dir / 'primary.xml').write_bytes(primary_xml)
        (parallel_dir / 'parallel.xml').write_bytes(parallel_xml)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)
        self.linear_data.project_priority = ['primary_project']
        self.linear_data.alignment_priority = ['parallel_project']

        self.refdb = MagicMock(spec=ReferenceDatabase)
        self.refdb.get_references_to.return_value = []

        self.refdb.get_urn_mappings.return_value = [
            # self_urn for primary: element_path=v1, end_element_path=v2 (a range).
            # When end_element_path != element_path, lines 190-191 execute an XPath
            # lookup to find the separate end element.
            make_urn_mapping(
                urn='urn:example:range/1',
                project='primary_project',
                file_name='primary.xml',
                element_path='/tei:TEI/tei:text/tei:body/tei:ab[1]',
                element_tag=f'{{{TEI_NS}}}ab',
                end_element_path='/tei:TEI/tei:text/tei:body/tei:ab[2]',
            ),
            # alignment_urn for parallel: single element
            make_urn_mapping(
                urn='urn:example:range/1',
                project='parallel_project',
                file_name='parallel.xml',
                element_path='/tei:TEI/tei:text/tei:body/tei:ab[1]',
                element_tag=f'{{{TEI_NS}}}ab',
            ),
        ]

    def _process_primary(self):
        processor = ExternalCompilerProcessor(
            'primary_project', 'primary.xml',
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        result = processor.process()
        self.assertEqual(len(result), 1)
        return result[0]

    def test_ranged_alignment_produces_parallel_block(self):
        """Ranged alignment (end_element_path != element_path) produces a parallelBlock
        (exercises the XPath end-element lookup at lines 190-191 of compiler.py)."""
        root = self._process_primary()
        blocks = root.xpath('.//p:parallelBlock', namespaces=NS)
        self.assertGreater(len(blocks), 0, "Expected at least one parallelBlock")

    def test_ranged_alignment_parallel_text_included(self):
        """The parallel text is included in the output for a ranged alignment."""
        root = self._process_primary()
        self.assertIn('parallel covering both',
                      etree.tostring(root, encoding='unicode'))

    def test_ranged_alignment_both_primary_verses_included(self):
        """Both primary verses (start and end of range) appear in the output."""
        root = self._process_primary()
        result_str = etree.tostring(root, encoding='unicode')
        self.assertIn('verse one', result_str)
        self.assertIn('verse two', result_str)

    def test_ranged_alignment_parallel_external_has_content(self):
        """p:parallelExternal contains the parallel verse text."""
        root = self._process_primary()
        externals = root.xpath('.//p:parallelExternal', namespaces=NS)
        self.assertEqual(len(externals), 1)
        self.assertIn('parallel covering both',
                      etree.tostring(externals[0], encoding='unicode'))

    # --- DESIRED BEHAVIOR (currently fails due to Bug 2) ---

    def test_ranged_alignment_no_residual_end_markers(self):
        """DESIRED: No p:end= attributes remain in the output after unflattening.

        Currently PASSES because lxml serializes the attribute as 'p:end=' and
        the unflattener does correctly remove the end-marker elements when the
        hashes match.  Kept as a regression guard.
        """
        root = self._process_primary()
        result_str = etree.tostring(root, encoding='unicode')
        self.assertNotIn('p:end=', result_str,
                         "No p:end attributes should survive unflattening")

    def test_ranged_alignment_both_verses_inside_parallel_internal(self):
        """DESIRED: Both primary verses appear inside a single p:parallelInternal.

        Currently fails because _process_alignment_after fires before v2 is
        appended to processed: the end markers close parallelInternal after v1
        only, and v2 ends up as a sibling of p:parallelBlock instead.
        """
        root = self._process_primary()
        internals = root.xpath('.//p:parallelBlock/p:parallelInternal', namespaces=NS)
        self.assertEqual(len(internals), 1,
                         "Expected exactly one parallelInternal inside parallelBlock")
        internal_str = etree.tostring(internals[0], encoding='unicode')
        self.assertIn('verse one', internal_str)
        self.assertIn('verse two', internal_str)
        # Nothing outside the two verses should be inside parallelInternal
        self.assertNotIn('p:end=', internal_str,
                         "No end markers should be inside parallelInternal")

    def test_ranged_alignment_nothing_after_parallel_block(self):
        """DESIRED: After a ranged alignment covering all body content, nothing appears
        after the p:parallelBlock in tei:body.

        Currently fails because the end marker fires before v2 is appended,
        so v2 ends up as a sibling of parallelBlock.
        """
        root = self._process_primary()
        body = root.xpath('.//tei:body', namespaces=NS)[0]
        # The only direct child of body should be the parallelBlock
        direct_children = list(body)
        self.assertEqual(len(direct_children), 1,
                         "tei:body should contain only p:parallelBlock when all verses are aligned")
        self.assertEqual(direct_children[0].tag, f'{{{PROCESSING_NS}}}parallelBlock')

    # --- END DESIRED BEHAVIOR ---


if __name__ == '__main__':
    unittest.main()
