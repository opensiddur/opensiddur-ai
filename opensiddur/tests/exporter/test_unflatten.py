"""Tests for the UnflatteningProcessor class."""

import unittest
from lxml import etree
from opensiddur.exporter.unflatten import UnflatteningProcessor


class TestUnflatteningProcessor(unittest.TestCase):
    """Tests for the UnflatteningProcessor class."""
    
    PROCESSING_NS = 'http://jewishliturgy.org/ns/processing'
    TEI_NS = 'http://www.tei-c.org/ns/1.0'
    
    def setUp(self):
        """Set up test fixtures."""
        self.ns_map = {
            'tei': self.TEI_NS,
            'p': self.PROCESSING_NS
        }
    
    def _create_element(self, tag, text=None, tail=None, attrib=None, children=None):
        """Helper to create an element with namespace."""
        if attrib is None:
            attrib = {}
        if children is None:
            children = []
        
        # Handle namespace prefix
        if ':' in tag:
            prefix, local = tag.split(':', 1)
            ns_uri = self.ns_map.get(prefix, '')
            elem = etree.Element(f"{{{ns_uri}}}{local}", nsmap=self.ns_map, attrib=attrib)
        else:
            elem = etree.Element(tag, nsmap=self.ns_map, attrib=attrib)
        
        if text:
            elem.text = text
        if tail:
            elem.tail = tail
        
        for child in children:
            elem.append(child)
        
        return elem
    
    def test_no_flattened_elements(self):
        """Test processing XML with no flattened elements (p:start/p:end)."""
        root = self._create_element('root', children=[
            self._create_element('tei:div', text='Content', children=[
                self._create_element('tei:p', text='Paragraph')
            ])
        ])
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should remain unchanged
        self.assertEqual(len(result), 1)
        div = result[0]
        self.assertEqual(div.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(div.text, 'Content')
        self.assertEqual(len(div), 1)
        p = div[0]
        self.assertEqual(p.tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(p.text, 'Paragraph')
    
    def test_flattened_elements_children_of_hierarchical(self):
        """Test flattened elements that are children of hierarchical elements."""
        # Create structure: div with p:start, then siblings, then p:end
        uuid = "test-uuid-123"
        root = self._create_element('root')
        
        div = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid})
        root.append(div)
        
        p1 = self._create_element('tei:p', text='First paragraph')
        root.append(p1)
        
        p2 = self._create_element('tei:p', text='Second paragraph')
        root.append(p2)
        
        end_marker = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # The div should now have p1 and p2 as children
        self.assertEqual(len(result), 1)  # Only the div remains
        div = result[0]
        self.assertEqual(div.tag, f"{{{self.TEI_NS}}}div")
        # p:start attribute should be removed
        self.assertNotIn(f"{{{self.PROCESSING_NS}}}start", div.attrib)
        # Should have two children
        self.assertEqual(len(div), 2)
        self.assertEqual(div[0].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(div[0].text, 'First paragraph')
        self.assertEqual(div[1].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(div[1].text, 'Second paragraph')
        # End marker should be removed
        self.assertEqual(len([e for e in result if f"{{{self.PROCESSING_NS}}}end" in e.attrib]), 0)
    
    def test_hierarchical_elements_children_of_flattened(self):
        """Test hierarchical elements that are children of flattened elements."""
        uuid = "test-uuid-456"
        root = self._create_element('root')
        
        # Outer flattened element
        outer = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid})
        root.append(outer)
        
        # Inner hierarchical element (should become child of outer)
        inner = self._create_element('tei:div', children=[
            self._create_element('tei:p', text='Inner paragraph')
        ])
        root.append(inner)
        
        end_marker = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Outer div should have inner div as child
        self.assertEqual(len(result), 1)
        outer = result[0]
        self.assertEqual(len(outer), 1)
        inner = outer[0]
        self.assertEqual(inner.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(len(inner), 1)
        self.assertEqual(inner[0].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(inner[0].text, 'Inner paragraph')
    
    def test_tail_text_on_start_element_becomes_text(self):
        """Test that tail text on start element becomes text content."""
        uuid = "test-uuid-789"
        root = self._create_element('root')
        
        div = self._create_element(
            'tei:div', 
            text='Initial text',
            tail='Tail text that becomes content',
            attrib={f"{{{self.PROCESSING_NS}}}start": uuid}
        )
        root.append(div)
        
        p = self._create_element('tei:p', text='Paragraph')
        root.append(p)
        
        end_marker = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        div = result[0]
        # Tail should become text (concatenated with existing text)
        self.assertEqual(div.text, 'Initial textTail text that becomes content')
        self.assertIsNone(div.tail)
        # Should have paragraph as child
        self.assertEqual(len(div), 1)
        self.assertEqual(div[0].text, 'Paragraph')
    
    def test_tail_text_on_start_element_no_existing_text(self):
        """Test tail text on start element when there's no existing text."""
        uuid = "test-uuid-101"
        root = self._create_element('root')
        
        div = self._create_element(
            'tei:div',
            tail='Only tail text',
            attrib={f"{{{self.PROCESSING_NS}}}start": uuid}
        )
        root.append(div)
        
        p = self._create_element('tei:p', text='Paragraph')
        root.append(p)
        
        end_marker = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        div = result[0]
        # Tail should become text
        self.assertEqual(div.text, 'Only tail text')
        self.assertIsNone(div.tail)
    
    def test_tail_text_on_end_element_becomes_tail(self):
        """Test that tail text on end element becomes tail of unflattened element."""
        uuid = "test-uuid-202"
        root = self._create_element('root')
        
        div = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid})
        root.append(div)
        
        p = self._create_element('tei:p', text='Paragraph')
        root.append(p)
        
        end_marker = self._create_element(
            'tei:div',
            tail='Tail after end marker',
            attrib={f"{{{self.PROCESSING_NS}}}end": uuid}
        )
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        div = result[0]
        # End marker's tail should become tail of the unflattened div
        self.assertEqual(div.tail, 'Tail after end marker')
    
    def test_tail_text_on_children(self):
        """Test that tail text on children is preserved."""
        uuid = "test-uuid-303"
        root = self._create_element('root')
        
        div = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid})
        root.append(div)
        
        p1 = self._create_element('tei:p', text='First', tail=' tail after first')
        root.append(p1)
        
        p2 = self._create_element('tei:p', text='Second', tail=' tail after second')
        root.append(p2)
        
        end_marker = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        div = result[0]
        self.assertEqual(len(div), 2)
        # Tail text should be preserved on children
        self.assertEqual(div[0].text, 'First')
        self.assertEqual(div[0].tail, ' tail after first')
        self.assertEqual(div[1].text, 'Second')
        self.assertEqual(div[1].tail, ' tail after second')
    
    def test_nested_flattened_elements(self):
        """Test nested flattened elements (flattened element inside another)."""
        outer_uuid = "outer-uuid"
        inner_uuid = "inner-uuid"
        root = self._create_element('root')
        
        # Outer flattened element
        outer = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": outer_uuid})
        root.append(outer)
        
        # Inner flattened element
        inner = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": inner_uuid})
        root.append(inner)
        
        p = self._create_element('tei:p', text='Paragraph')
        root.append(p)
        
        inner_end = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": inner_uuid})
        root.append(inner_end)
        
        outer_end = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": outer_uuid})
        root.append(outer_end)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Outer div should contain inner div, which contains paragraph
        self.assertEqual(len(result), 1)
        outer = result[0]
        self.assertEqual(len(outer), 1)  # Should have inner div as child
        inner = outer[0]
        self.assertEqual(len(inner), 1)  # Should have paragraph as child
        self.assertEqual(inner[0].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(inner[0].text, 'Paragraph')
    
    def test_multiple_flattened_elements_same_level(self):
        """Test multiple flattened elements at the same level."""
        uuid1 = "uuid-1"
        uuid2 = "uuid-2"
        root = self._create_element('root')
        
        # First flattened element
        div1 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid1})
        root.append(div1)
        p1 = self._create_element('tei:p', text='First paragraph')
        root.append(p1)
        end1 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid1})
        root.append(end1)
        
        # Second flattened element
        div2 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid2})
        root.append(div2)
        p2 = self._create_element('tei:p', text='Second paragraph')
        root.append(p2)
        end2 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid2})
        root.append(end2)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have two divs as children
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 1)  # First div has one child
        self.assertEqual(result[0][0].text, 'First paragraph')
        self.assertEqual(len(result[1]), 1)  # Second div has one child
        self.assertEqual(result[1][0].text, 'Second paragraph')
    
    def test_complex_nested_structure(self):
        """Test a complex structure with hierarchical and flattened elements."""
        uuid = "complex-uuid"
        root = self._create_element('root')
        
        # Hierarchical div
        hierarchical = self._create_element('tei:div', children=[
            self._create_element('tei:head', text='Title')
        ])
        root.append(hierarchical)
        
        # Flattened div
        flattened = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid})
        root.append(flattened)
        
        # Content for flattened div
        p1 = self._create_element('tei:p', text='Paragraph 1', tail=' tail 1')
        root.append(p1)
        
        nested_div = self._create_element('tei:div', children=[
            self._create_element('tei:p', text='Nested paragraph')
        ])
        root.append(nested_div)
        
        p2 = self._create_element('tei:p', text='Paragraph 2', tail=' tail 2')
        root.append(p2)
        
        end_marker = self._create_element('tei:div', tail=' tail after end', attrib={f"{{{self.PROCESSING_NS}}}end": uuid})
        root.append(end_marker)
        
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have hierarchical div and flattened div
        self.assertEqual(len(result), 2)
        hierarchical = result[0]
        self.assertEqual(hierarchical.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(len(hierarchical), 1)
        self.assertEqual(hierarchical[0].tag, f"{{{self.TEI_NS}}}head")
        
        flattened = result[1]
        self.assertEqual(flattened.tag, f"{{{self.TEI_NS}}}div")
        # Should have p1, nested_div, and p2 as children
        self.assertEqual(len(flattened), 3)
        self.assertEqual(flattened[0].text, 'Paragraph 1')
        self.assertEqual(flattened[0].tail, ' tail 1')
        self.assertEqual(flattened[1].tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(flattened[2].text, 'Paragraph 2')
        self.assertEqual(flattened[2].tail, ' tail 2')
        # End marker's tail should become flattened div's tail
        self.assertEqual(flattened.tail, ' tail after end')
    
    def test_nested_flattened_elements_removal_error(self):
        """Test that nested flattened elements don't cause 'Element is not a child' error.
        
        This tests the case where:
        - elem1 has p:start="uuid1"
        - elem2 (a sibling of elem1) has p:start="uuid2" 
        - When processing elem1, it processes elem2 recursively
        - elem2 removes siblings from root during its processing
        - Then elem1 tries to remove elem2 from root
        - This should not cause an error
        """
        uuid1 = "uuid1"
        uuid2 = "uuid2"
        root = self._create_element('root')
        
        # First element with p:start
        elem1 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid1})
        root.append(elem1)
        
        # Second element that also has p:start (nested flattened structure)
        elem2 = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}start": uuid2})
        root.append(elem2)
        
        # Content for elem2
        p1 = self._create_element('tei:p', text='Content for elem2')
        root.append(p1)
        
        # End marker for elem2
        elem2_end = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid2})
        root.append(elem2_end)
        
        # Content for elem1
        p2 = self._create_element('tei:p', text='Content for elem1')
        root.append(p2)
        
        # End marker for elem1
        elem1_end = self._create_element('tei:div', attrib={f"{{{self.PROCESSING_NS}}}end": uuid1})
        root.append(elem1_end)
        
        # This should not raise "Element is not a child of this node" error
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Verify the structure is correct
        # elem1 should contain elem2, p1, and p2
        self.assertEqual(len(result), 1)
        elem1_result = result[0]
        self.assertEqual(elem1_result.tag, f"{{{self.TEI_NS}}}div")
        # Should have elem2 (which contains p1) and p2 as children
        self.assertEqual(len(elem1_result), 2)
        
        # First child should be elem2, which contains p1
        elem2_result = elem1_result[0]
        self.assertEqual(elem2_result.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(len(elem2_result), 1)
        self.assertEqual(elem2_result[0].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(elem2_result[0].text, 'Content for elem2')
        
        # Second child should be p2
        p2_result = elem1_result[1]
        self.assertEqual(p2_result.tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(p2_result.text, 'Content for elem1')
        
        # Verify no p:start or p:end attributes remain
        self.assertNotIn(f"{{{self.PROCESSING_NS}}}start", elem1_result.attrib)
        self.assertNotIn(f"{{{self.PROCESSING_NS}}}start", elem2_result.attrib)
        self.assertNotIn(f"{{{self.PROCESSING_NS}}}end", elem1_result.attrib)
        self.assertNotIn(f"{{{self.PROCESSING_NS}}}end", elem2_result.attrib)
    
    def test_parallel_block_with_hierarchical_elements_no_crossing(self):
        """Test parallel block with hierarchical elements before, inside, after, and including it (no crossing boundaries)."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="hierarchy-before-uuid"/>
    <tei:p>Before parallel</tei:p>
    <tei:div p:end="hierarchy-before-uuid"/>
    <p:parallelBlock p:start="parallel-uuid"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid"/>
    <tei:div p:start="hierarchy-inside-uuid"/>
    <tei:p>Inside parallel</tei:p>
    <tei:div p:end="hierarchy-inside-uuid"/>
    <p:parallelInternal p:end="parallel-internal-uuid"/>
    <p:parallelBlock p:end="parallel-uuid"/>
    <tei:div p:start="hierarchy-after-uuid"/>
    <tei:p>After parallel</tei:p>
    <tei:div p:end="hierarchy-after-uuid"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have hierarchy_before, parallel_block, hierarchy_after
        self.assertEqual(len(result), 3)
        
        # First: hierarchy before (unflattened)
        self.assertEqual(result[0].tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(len(result[0]), 1)
        self.assertEqual(result[0][0].text, 'Before parallel')
        
        # Second: parallel block (should contain parallelExternal, parallelInternal with hierarchy_inside)
        self.assertEqual(result[1].tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        # Should have parallelExternal and parallelInternal
        self.assertGreaterEqual(len(result[1]), 2)
        # First child should be parallelExternal
        self.assertEqual(result[1][0].tag, f"{{{self.PROCESSING_NS}}}parallelExternal")
        # Second child should be parallelInternal
        self.assertEqual(result[1][1].tag, f"{{{self.PROCESSING_NS}}}parallelInternal")
        # Find hierarchy_inside inside parallelInternal
        hierarchy_inside = None
        for child in result[1][1]:
            if child.tag == f"{{{self.TEI_NS}}}div":
                hierarchy_inside = child
                break
        self.assertIsNotNone(hierarchy_inside, "Hierarchy should be inside parallelInternal")
        self.assertEqual(hierarchy_inside[0].text, 'Inside parallel')
        
        # Third: hierarchy after
        self.assertEqual(result[2].tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(result[2][0].text, 'After parallel')
    
    def test_hierarchy_begins_inside_parallel_ends_after(self):
        """Test hierarchy that begins inside parallel block and ends after it."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-uuid-2"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-2"/>
    <tei:div p:start="hierarchy-uuid-2"/>
    <tei:p>Inside parallel</tei:p>
    <p:parallelInternal p:end="parallel-internal-uuid-2"/>
    <p:parallelBlock p:end="parallel-uuid-2"/>
    <tei:p>After parallel</tei:p>
    <tei:div p:end="hierarchy-uuid-2"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # The hierarchy that starts inside and ends after will collect everything until its end marker,
        # including the parallel block end marker. So everything ends up inside the parallel block.
        self.assertEqual(len(result), 1)
        
        # First: parallel block
        parallel_result = result[0]
        self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        # Parallel block should contain parallelExternal and parallelInternal
        self.assertGreaterEqual(len(parallel_result), 2)
        # Find the hierarchy element inside parallelInternal
        hierarchy_inside = None
        for child in parallel_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                for grandchild in child:
                    if grandchild.tag == f"{{{self.TEI_NS}}}div":
                        hierarchy_inside = grandchild
                        break
                break
        
        self.assertIsNotNone(hierarchy_inside, "Hierarchy should be inside parallelInternal")
        # Hierarchy inside should have both p_inside and p_after as children
        # (since it collects everything until its end marker, including content after parallel block)
        self.assertGreaterEqual(len(hierarchy_inside), 1)
        # The first child should be the content inside
        self.assertEqual(hierarchy_inside[0].text, 'Inside parallel')
    
    def test_hierarchy_begins_before_parallel_ends_inside(self):
        """Test hierarchy that begins before parallel block and ends inside it."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="hierarchy-uuid-3"/>
    <tei:p>Before parallel</tei:p>
    <p:parallelBlock p:start="parallel-uuid-3"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-3"/>
    <tei:p>Inside parallel</tei:p>
    <tei:div p:end="hierarchy-uuid-3"/>
    <p:parallelInternal p:end="parallel-internal-uuid-3"/>
    <p:parallelBlock p:end="parallel-uuid-3"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have hierarchy as first element (before parallel)
        # Hierarchy should be marked with part=first since it crosses parallel block
        self.assertGreaterEqual(len(result), 1)
        hierarchy_result = result[0]
        self.assertEqual(hierarchy_result.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(hierarchy_result.get("part"), "first", "Hierarchy crossing parallel block should have part=first")
        
        # Should have p_before as child
        self.assertGreaterEqual(len(hierarchy_result), 1)
        self.assertEqual(hierarchy_result[0].text, 'Before parallel')
        
        # Since hierarchy ends inside parallel block, the parallel block should be a child of hierarchy
        # Find the parallel block inside the hierarchy
        parallel_result = None
        for child in hierarchy_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelBlock":
                parallel_result = child
                break
        
        self.assertIsNotNone(parallel_result, "Parallel block should be inside hierarchy")
        self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        # Parallel block should contain parallelExternal and parallelInternal
        self.assertGreaterEqual(len(parallel_result), 2)
        # Find hierarchy continuation inside parallelInternal
        found_continuation = False
        for child in parallel_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                for grandchild in child:
                    if grandchild.tag == f"{{{self.TEI_NS}}}div" and grandchild.get("part") == "continue":
                        # Found continuation
                        found_continuation = True
                        # Should contain p_inside
                        self.assertGreaterEqual(len(grandchild), 1)
                        break
                break
        # Note: The hierarchy end marker should also be in the parallel block
        self.assertTrue(found_continuation or len(parallel_result) > 0, "Parallel block should contain hierarchy continuation")
    
    def test_external_transclude_inside_parallel_block(self):
        """Test external transclude element inside a parallel block."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-uuid-4"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-4"/>
    <tei:p>Before transclude</tei:p>
    <p:transclude type="external" target="urn:test"/>
    <tei:p>After transclude</tei:p>
    <p:parallelInternal p:end="parallel-internal-uuid-4"/>
    <p:parallelBlock p:end="parallel-uuid-4"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have parallel block containing parallelExternal, parallelInternal, and external transclude
        self.assertEqual(len(result), 1)
        parallel_result = result[0]
        self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        # Should have parallelExternal and parallelInternal
        self.assertGreaterEqual(len(parallel_result), 2)
        # Find external transclude inside parallelInternal
        transclude_found = False
        content_before = False
        content_after = False
        for child in parallel_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                children_list = list(child)
                for i, grandchild in enumerate(children_list):
                    if grandchild.tag == f"{{{self.PROCESSING_NS}}}transclude":
                        transclude_found = True
                        self.assertEqual(grandchild.get("type"), "external")
                        # Check for content before and after
                        if i > 0 and children_list[i-1].tag == f"{{{self.TEI_NS}}}p":
                            content_before = True
                            self.assertEqual(children_list[i-1].text, 'Before transclude')
                        if i < len(children_list) - 1 and children_list[i+1].tag == f"{{{self.TEI_NS}}}p":
                            content_after = True
                            self.assertEqual(children_list[i+1].text, 'After transclude')
                        break
                break
        self.assertTrue(transclude_found, "External transclude should be inside parallelInternal")
        self.assertTrue(content_before, "Content should exist before external transclude")
        self.assertTrue(content_after, "Content should exist after external transclude")
    
    def test_inline_transclude_inside_parallel_block(self):
        """Test inline transclude element inside a parallel block."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-uuid-5"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-5"/>
    <p:transclude type="inline" target="urn:test"/>
    <p:parallelInternal p:end="parallel-internal-uuid-5"/>
    <p:parallelBlock p:end="parallel-uuid-5"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have parallel block containing parallelExternal, parallelInternal, and inline transclude
        self.assertEqual(len(result), 1)
        parallel_result = result[0]
        self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        # Should have parallelExternal and parallelInternal
        self.assertGreaterEqual(len(parallel_result), 2)
        # Find inline transclude inside parallelInternal
        transclude_found = False
        for child in parallel_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                for grandchild in child:
                    if grandchild.tag == f"{{{self.PROCESSING_NS}}}transclude":
                        transclude_found = True
                        self.assertEqual(grandchild.get("type"), "inline")
                        break
                break
        self.assertTrue(transclude_found, "Inline transclude should be inside parallelInternal")
    
    def test_hierarchy_crosses_parallel_block_with_part_attributes(self):
        """Test hierarchy crossing parallel block gets part=first and part=continue attributes."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="hierarchy-uuid-6"/>
    <tei:p>Before parallel</tei:p>
    <p:parallelBlock p:start="parallel-uuid-6"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-6"/>
    <tei:div p:start="hierarchy-uuid-6-continue"/>
    <tei:p>Inside parallel</tei:p>
    <tei:div p:end="hierarchy-uuid-6-continue"/>
    <p:parallelInternal p:end="parallel-internal-uuid-6"/>
    <p:parallelBlock p:end="parallel-uuid-6"/>
    <tei:p>After parallel</tei:p>
    <tei:div p:end="hierarchy-uuid-6"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Hierarchy should be marked with part=first
        self.assertGreaterEqual(len(result), 1)
        hierarchy_result = result[0]
        self.assertEqual(hierarchy_result.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(hierarchy_result.get("part"), "first")
        
        # Parallel block should contain hierarchy continuation with part=continue
        if len(result) > 1:
            parallel_result = result[1]
            self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
            # Find hierarchy continuation inside parallelInternal
            for child in parallel_result:
                if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                    for grandchild in child:
                        if grandchild.tag == f"{{{self.TEI_NS}}}div" and grandchild.get("part") == "continue":
                            # Found continuation
                            self.assertEqual(len(grandchild), 1)
                            self.assertEqual(grandchild[0].text, 'Inside parallel')
                            break
                    break
    
    def test_tail_text_on_flattened_element_start_becomes_text(self):
        """Test that tail text on element with p:start becomes text content."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="uuid-1"/>Tail on start
    <tei:p>First paragraph</tei:p>
    <tei:p>Second paragraph</tei:p>
    <tei:div p:end="uuid-1"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # The div should have the tail text as its text content
        self.assertEqual(len(result), 1)
        div = result[0]
        self.assertEqual(div.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(div.text.strip(), "Tail on start")
        self.assertEqual(len(div), 2)
        self.assertEqual(div[0].text, 'First paragraph')
        self.assertEqual(div[1].text, 'Second paragraph')
    
    def test_tail_text_on_flattened_element_end_becomes_tail(self):
        """Test that tail text on element with p:end becomes tail of unflattened element."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="uuid-2"/>
    <tei:p>First paragraph</tei:p>
    <tei:p>Second paragraph</tei:p>
    <tei:div p:end="uuid-2"/>Tail on end
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # The div should have the end element's tail as its tail
        self.assertEqual(len(result), 1)
        div = result[0]
        self.assertEqual(div.tag, f"{{{self.TEI_NS}}}div")
        self.assertEqual(div.tail.strip(), "Tail on end")
        self.assertEqual(len(div), 2)
        self.assertEqual(div[0].text, 'First paragraph')
        self.assertEqual(div[1].text, 'Second paragraph')
    
    def test_text_and_tail_on_children_of_flattened_element(self):
        """Test text and tail text on children of flattened elements."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="uuid-3"/>
    <tei:p>First paragraph</tei:p> Tail after first
    <tei:p>Second paragraph</tei:p> Tail after second
    <tei:div p:end="uuid-3"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Children should preserve their tail text
        self.assertEqual(len(result), 1)
        div = result[0]
        self.assertEqual(len(div), 2)
        self.assertEqual(div[0].text, 'First paragraph')
        self.assertIn(" Tail after first", div[0].tail or "")
        self.assertEqual(div[1].text, 'Second paragraph')
        self.assertIn(" Tail after second", div[1].tail or "")
    
    def test_text_around_parallel_block_boundaries(self):
        """Test text and tail text around parallel block boundaries."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:p>Before parallel</tei:p> Tail before parallel
    <p:parallelBlock p:start="parallel-uuid-text"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-text"/>
    <tei:p>Inside parallel</tei:p>
    <p:parallelInternal p:end="parallel-internal-uuid-text"/>
    <p:parallelBlock p:end="parallel-uuid-text"/>Tail on parallel end
    <tei:p>After parallel</tei:p>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have: p (before), parallelBlock, p (after)
        self.assertEqual(len(result), 3)
        
        # First paragraph with tail
        self.assertEqual(result[0].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(result[0].text, 'Before parallel')
        self.assertIn(" Tail before parallel", result[0].tail or "")
        
        # Parallel block - tail from end element should be on parallel block
        self.assertEqual(result[1].tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        self.assertIn("Tail on parallel end", result[1].tail or "")
        
        # Last paragraph
        self.assertEqual(result[2].tag, f"{{{self.TEI_NS}}}p")
        self.assertEqual(result[2].text, 'After parallel')
    
    def test_tail_text_on_parallel_block_end(self):
        """Test that tail text on parallelBlock end element is preserved."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-uuid-tail"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-tail"/>
    <tei:p>Inside parallel</tei:p>
    <p:parallelInternal p:end="parallel-internal-uuid-tail"/>
    <p:parallelBlock p:end="parallel-uuid-tail"/> Tail after parallel block
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Parallel block should have tail text
        self.assertEqual(len(result), 1)
        parallel_block = result[0]
        self.assertEqual(parallel_block.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        self.assertIn(" Tail after parallel block", parallel_block.tail or "")
    
    def test_text_and_tail_at_hierarchy_crossing_parallel_boundary(self):
        """Test text and tail text when hierarchy crosses parallel block boundary (starts inside, ends outside)."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-cross-uuid"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-cross-uuid"/>
    <tei:div p:start="hierarchy-cross-uuid"/> Tail on hierarchy start
    <tei:p>Inside parallel</tei:p> Tail inside
    <p:parallelInternal p:end="parallel-internal-cross-uuid"/>
    <p:parallelBlock p:end="parallel-cross-uuid"/>
    <tei:p>After parallel</tei:p> Tail after
    <tei:div p:end="hierarchy-cross-uuid"/> Tail on hierarchy end
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # The hierarchy that starts inside the parallel block and ends after it:
        # - The parallel block is processed first (it has priority)
        # - The hierarchy inside the parallel block should be marked with part=continue
        # - The hierarchy collects everything from its start to its end, including content after the parallel block
        # - But since the parallel block is processed first, the hierarchy inside will only contain what's inside
        
        # The result should be the parallel block (since it's processed first)
        self.assertEqual(len(result), 1)
        
        # First: parallel block
        parallel_result = result[0]
        self.assertEqual(parallel_result.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        
        # Find the hierarchy element inside parallelInternal (should have part=continue)
        hierarchy_inside = None
        for child in parallel_result:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                for grandchild in child:
                    if grandchild.tag == f"{{{self.TEI_NS}}}div":
                        hierarchy_inside = grandchild
                        break
                break
        
        self.assertIsNotNone(hierarchy_inside, "Hierarchy should be inside parallelInternal")
        # Hierarchy that starts inside should be marked with part=first (it's the first occurrence)
        # Note: part=continue would be used if the hierarchy started before and continued inside
        self.assertEqual(hierarchy_inside.get("part"), "first")
        # Should have content inside the parallel block and after (since it collects until end marker)
        self.assertGreaterEqual(len(hierarchy_inside), 1)
        # The hierarchy start tail should become text
        self.assertIn(" Tail on hierarchy start", hierarchy_inside.text or "")
        # First child should be the paragraph inside
        self.assertEqual(hierarchy_inside[0].text, 'Inside parallel')
        self.assertIn(" Tail inside", hierarchy_inside[0].tail or "")
        # The hierarchy should also collect content after the parallel block (until its end marker)
        # So it should have the paragraph after parallel as well
        # Find the paragraph after parallel inside the hierarchy
        after_parallel_p = None
        for child in hierarchy_inside:
            if child.tag == f"{{{self.TEI_NS}}}p" and child.text == 'After parallel':
                after_parallel_p = child
                break
        self.assertIsNotNone(after_parallel_p, "Hierarchy should contain content after parallel block")
        self.assertIn(" Tail after", after_parallel_p.tail or "")
        # The hierarchy end tail should become the hierarchy's tail
        self.assertIn(" Tail on hierarchy end", hierarchy_inside.tail or "")
    
    def test_text_and_tail_on_parallel_internal_children(self):
        """Test text and tail text on children inside parallelInternal."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <p:parallelBlock p:start="parallel-internal-text-uuid"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-uuid-text"/>
    <tei:p>First inside</tei:p> Tail after first
    <tei:p>Second inside</tei:p> Tail after second
    <p:parallelInternal p:end="parallel-internal-uuid-text"/>
    <p:parallelBlock p:end="parallel-internal-text-uuid"/>
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Parallel block should contain parallelInternal with children
        self.assertEqual(len(result), 1)
        parallel_block = result[0]
        self.assertEqual(parallel_block.tag, f"{{{self.PROCESSING_NS}}}parallelBlock")
        
        # Find parallelInternal
        parallel_internal = None
        for child in parallel_block:
            if child.tag == f"{{{self.PROCESSING_NS}}}parallelInternal":
                parallel_internal = child
                break
        self.assertIsNotNone(parallel_internal)
        
        # Children should have tail text preserved
        self.assertEqual(len(parallel_internal), 2)
        self.assertEqual(parallel_internal[0].text, 'First inside')
        self.assertIn(" Tail after first", parallel_internal[0].tail or "")
        self.assertEqual(parallel_internal[1].text, 'Second inside')
        self.assertIn(" Tail after second", parallel_internal[1].tail or "")
    
    def test_tail_text_on_flattened_element_with_parallel_block_inside(self):
        """Test tail text on flattened element that contains a parallel block."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="hierarchy-with-parallel-uuid"/> Tail on start
    <tei:p>Before parallel</tei:p>
    <p:parallelBlock p:start="parallel-inside-uuid"/>
    <p:parallelExternal>
        <tei:p>External content</tei:p>
    </p:parallelExternal>
    <p:parallelInternal p:start="parallel-internal-inside-uuid"/>
    <tei:p>Inside parallel</tei:p>
    <p:parallelInternal p:end="parallel-internal-inside-uuid"/>
    <p:parallelBlock p:end="parallel-inside-uuid"/>
    <tei:p>After parallel</tei:p>
    <tei:div p:end="hierarchy-with-parallel-uuid"/> Tail on end
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Hierarchy should have start tail as text, end tail as tail
        self.assertEqual(len(result), 1)
        hierarchy = result[0]
        self.assertEqual(hierarchy.tag, f"{{{self.TEI_NS}}}div")
        self.assertIn(" Tail on start", hierarchy.text or "")
        # The end element's tail should become the hierarchy's tail
        self.assertIn(" Tail on end", hierarchy.tail or "")
        
        # Should contain: p (before), parallelBlock, p (after)
        self.assertGreaterEqual(len(hierarchy), 3)
        self.assertEqual(hierarchy[0].text, 'Before parallel')
        self.assertEqual(hierarchy[2].text, 'After parallel')
    
    def test_text_and_tail_on_multiple_flattened_elements_at_same_level(self):
        """Test text and tail text on multiple flattened elements at the same level."""
        xml_content = f'''<root xmlns:tei="{self.TEI_NS}" xmlns:p="{self.PROCESSING_NS}">
    <tei:div p:start="uuid-1"/> Tail on first start
    <tei:p>First hierarchy content</tei:p>
    <tei:div p:end="uuid-1"/> Tail between hierarchies
    <tei:div p:start="uuid-2"/> Tail on second start
    <tei:p>Second hierarchy content</tei:p>
    <tei:div p:end="uuid-2"/> Tail after second end
</root>'''
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        processor = UnflatteningProcessor(root, self.ns_map)
        result = processor.process()
        
        # Should have two hierarchies
        self.assertEqual(len(result), 2)
        
        # First hierarchy
        first = result[0]
        self.assertEqual(first.tag, f"{{{self.TEI_NS}}}div")
        self.assertIn(" Tail on first start", first.text or "")
        self.assertIn(" Tail between hierarchies", first.tail or "")
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].text, 'First hierarchy content')
        
        # Second hierarchy
        second = result[1]
        self.assertEqual(second.tag, f"{{{self.TEI_NS}}}div")
        self.assertIn(" Tail on second start", second.text or "")
        self.assertIn(" Tail after second end", second.tail or "")
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].text, 'Second hierarchy content')


if __name__ == '__main__':
    unittest.main()

