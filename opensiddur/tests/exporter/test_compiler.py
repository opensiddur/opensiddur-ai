"""Tests for the CompilerProcessor class."""

import unittest
from lxml import etree
from opensiddur.exporter.compiler import CompilerProcessor


class TestCompilerProcessorIdentityTransform(unittest.TestCase):
    """Test that CompilerProcessor acts as an identity transform for XML input."""

    def test_simple_element_with_text(self):
        """Test processing a simple element with text content."""
        xml_input = '<root>Hello World</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        # Convert result to string for comparison
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_empty_element(self):
        """Test processing an empty element."""
        xml_input = '<root/>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_element_with_attributes(self):
        """Test processing an element with attributes."""
        xml_input = '<root attr1="value1" attr2="value2">Content</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_nested_elements(self):
        """Test processing nested elements."""
        xml_input = '<root><child1>Text1</child1><child2>Text2</child2></root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_element_with_tail(self):
        """Test processing an element with tail text."""
        xml_input = '<root><child>Content</child>Tail text</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_multiple_tails(self):
        """Test processing multiple elements with tail text."""
        xml_input = '<root><child1>Content1</child1>Tail1<child2>Content2</child2>Tail2</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_deeply_nested_structure(self):
        """Test processing a deeply nested XML structure."""
        xml_input = '''<root>
            <level1 attr="value">
                <level2>Text content</level2>
                <level2>More text</level2>
            </level1>
            <level1>Another branch</level1>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_mixed_content_with_tails(self):
        """Test processing mixed content with various tail scenarios."""
        xml_input = '''<root>
            Text before
            <child1>Child content</child1>
            Tail after child1
            <child2 attr="test">Child2 content</child2>
            Final tail
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_empty_elements_with_tails(self):
        """Test processing empty elements with tail text."""
        xml_input = '<root><empty1/>Tail1<empty2/>Tail2<empty3/></root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_self_closing_elements(self):
        """Test processing self-closing elements."""
        xml_input = '<root><br/><hr/><img src="test.jpg"/></root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_whitespace_preservation(self):
        """Test that whitespace is preserved correctly."""
        xml_input = '<root>  \n  <child>  Content  </child>  \n  </root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_special_characters(self):
        """Test processing elements with special characters."""
        xml_input = '<root attr="&lt;&gt;&amp;">Content with &lt;tags&gt; &amp; entities</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_namespace_elements(self):
        """Test processing elements with namespaces."""
        xml_input = '<root xmlns:tei="http://www.tei-c.org/ns/1.0"><tei:div>Content</tei:div></root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # lxml may change namespace prefixes, so we check for the namespace URI and content
        self.assertIn('xmlns:', result_str)
        self.assertIn('http://www.tei-c.org/ns/1.0', result_str)
        self.assertIn('Content', result_str)
        self.assertIn('div', result_str)

    def test_complex_structure_with_all_features(self):
        """Test a complex structure with all features: attributes, text, tails, nesting."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" id="main">
            Root text
            <tei:div type="chapter" n="1">
                Chapter content
                <tei:p>Paragraph text</tei:p>
                Paragraph tail
                <tei:note>Note content</tei:note>
                Note tail
            </tei:div>
            Chapter tail
            <tei:div type="chapter" n="2"/>
            Empty chapter tail
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Check that all the key content is preserved, even if namespace prefixes change
        self.assertIn('id="main"', result_str)
        self.assertIn('Root text', result_str)
        self.assertIn('Chapter content', result_str)
        self.assertIn('Paragraph text', result_str)
        self.assertIn('Paragraph tail', result_str)
        self.assertIn('Note content', result_str)
        self.assertIn('Note tail', result_str)
        self.assertIn('Chapter tail', result_str)
        self.assertIn('Empty chapter tail', result_str)
        self.assertIn('type="chapter"', result_str)
        self.assertIn('n="1"', result_str)
        self.assertIn('n="2"', result_str)
        self.assertIn('http://www.tei-c.org/ns/1.0', result_str)

    def test_process_with_specific_root(self):
        """Test processing with a specific root element passed to process()."""
        xml_input = '<root><child1>Content1</child1><child2>Content2</child2></root>'
        processor = CompilerProcessor(xml_input)
        
        # Get the child1 element and process it specifically
        child1 = processor.root_tree.find('child1')
        result = processor.process(child1)
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, '<child1>Content1</child1>')

    def test_process_with_none_root_uses_default(self):
        """Test that process() with None uses the default root_tree."""
        xml_input = '<root>Default content</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process(None)
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_unicode_content(self):
        """Test processing elements with Unicode content."""
        xml_input = '<root>Hello 世界 🌍</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)

    def test_unicode_attributes(self):
        """Test processing elements with Unicode attributes."""
        xml_input = '<root attr="测试">Content with 中文</root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        self.assertEqual(result_str, xml_input)


class TestCompilerProcessorNamespacePreservation(unittest.TestCase):
    """Test that CompilerProcessor preserves original namespace prefixes."""

    def test_single_namespace_prefix_preservation(self):
        """Test that a single namespace prefix is preserved exactly."""
        xml_input = '<root xmlns:tei="http://www.tei-c.org/ns/1.0"><tei:div>Content</tei:div></root>'
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve the exact 'tei:' prefix
        self.assertEqual(result_str, xml_input)

    def test_multiple_namespace_prefixes_preservation(self):
        """Test that multiple namespace prefixes are preserved exactly."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>
                <j:transclude>Content</j:transclude>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve both 'tei:' and 'j:' prefixes
        self.assertEqual(result_str, xml_input)

    def test_nested_namespace_prefixes_preservation(self):
        """Test that namespace prefixes are preserved in deeply nested structures."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:text>
                <tei:body>
                    <tei:div type="chapter">
                        <tei:p>Paragraph content</tei:p>
                        <j:transclude>Transclusion</j:transclude>
                    </tei:div>
                </tei:body>
            </tei:text>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve all namespace prefixes throughout the hierarchy
        self.assertEqual(result_str, xml_input)

    def test_namespace_prefixes_with_attributes(self):
        """Test that namespace prefixes are preserved when elements have attributes."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div type="chapter" n="1" xml:id="ch1">
                <tei:p rend="italic">Italic text</tei:p>
                <j:transclude target="urn:example">Reference</j:transclude>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes even with complex attributes
        self.assertEqual(result_str, xml_input)

    def test_namespace_prefixes_with_tail_text(self):
        """Test that namespace prefixes are preserved when elements have tail text."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>Content</tei:div>Tail text
            <j:transclude>More content</j:transclude>More tail
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with tail text
        self.assertEqual(result_str, xml_input)

    def test_default_namespace_preservation(self):
        """Test that default namespaces (no prefix) are preserved."""
        xml_input = '''<root xmlns="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <div type="chapter">
                <p>Paragraph in default namespace</p>
                <j:transclude>Transclusion in prefixed namespace</j:transclude>
            </div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve default namespace and prefixed namespace
        self.assertEqual(result_str, xml_input)

    def test_mixed_namespace_scenarios(self):
        """Test complex scenarios with mixed namespace usage."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2" xmlns="http://example.org/ns">
            <tei:teiHeader>
                <tei:fileDesc>
                    <tei:titleStmt>
                        <tei:title>Title</tei:title>
                    </tei:titleStmt>
                </tei:fileDesc>
            </tei:teiHeader>
            <text>
                <body>
                    <div type="chapter">
                        <p>Content in default namespace</p>
                        <tei:note>Note in TEI namespace</tei:note>
                        <j:transclude>Transclusion in J namespace</j:transclude>
                    </div>
                </body>
            </text>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve all three namespaces (default, tei:, j:)
        # Check that all namespace prefixes are preserved
        self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result_str)
        self.assertIn('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"', result_str)
        self.assertIn('xmlns="http://example.org/ns"', result_str)
        self.assertIn('<tei:teiHeader>', result_str)
        self.assertIn('<tei:fileDesc>', result_str)
        self.assertIn('<tei:titleStmt>', result_str)
        self.assertIn('<tei:title>', result_str)
        self.assertIn('<tei:note>', result_str)
        self.assertIn('<j:transclude>', result_str)
        self.assertIn('Title', result_str)
        self.assertIn('Content in default namespace', result_str)
        self.assertIn('Note in TEI namespace', result_str)
        self.assertIn('Transclusion in J namespace', result_str)

    def test_namespace_prefixes_with_special_characters(self):
        """Test that namespace prefixes are preserved with special characters in content."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>Content with &lt;special&gt; &amp; characters</tei:div>
            <j:transclude>More &quot;quoted&quot; content</j:transclude>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with special characters
        # Check that namespace prefixes are preserved
        self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result_str)
        self.assertIn('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"', result_str)
        self.assertIn('<tei:div>', result_str)
        self.assertIn('<j:transclude>', result_str)
        # Check that content is preserved (lxml may normalize entity encoding)
        self.assertIn('Content with', result_str)
        self.assertIn('characters', result_str)
        self.assertIn('More', result_str)
        self.assertIn('content', result_str)

    def test_namespace_prefixes_with_unicode_content(self):
        """Test that namespace prefixes are preserved with Unicode content."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>Content with 中文 and עברית</tei:div>
            <j:transclude>Transclusion with 🌍 emoji</j:transclude>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with Unicode content
        self.assertEqual(result_str, xml_input)

    def test_namespace_prefixes_with_empty_elements(self):
        """Test that namespace prefixes are preserved with empty elements."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div/>
            <j:transclude/>
            <tei:br/>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with empty elements
        self.assertEqual(result_str, xml_input)

    def test_namespace_prefixes_with_self_closing_elements(self):
        """Test that namespace prefixes are preserved with self-closing elements."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:br/>
            <tei:pb n="1"/>
            <j:milestone unit="chapter"/>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with self-closing elements
        self.assertEqual(result_str, xml_input)

    def test_namespace_prefixes_with_complex_attributes(self):
        """Test that namespace prefixes are preserved with complex attribute scenarios."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2" xmlns:xml="http://www.w3.org/XML/1998/namespace">
            <tei:div type="chapter" n="1" xml:id="ch1" corresp="urn:example">
                <tei:p rend="italic" xml:lang="en">English text</tei:p>
                <j:transclude target="urn:example" xml:lang="he">עברית</j:transclude>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with xml: attributes
        # Check that namespace prefixes are preserved
        self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result_str)
        self.assertIn('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"', result_str)
        self.assertIn('<tei:div', result_str)
        self.assertIn('<tei:p', result_str)
        self.assertIn('<j:transclude', result_str)
        # Check that attributes are preserved
        self.assertIn('type="chapter"', result_str)
        self.assertIn('n="1"', result_str)
        self.assertIn('xml:id="ch1"', result_str)
        self.assertIn('corresp="urn:example"', result_str)
        self.assertIn('rend="italic"', result_str)
        self.assertIn('xml:lang="en"', result_str)
        self.assertIn('target="urn:example"', result_str)
        self.assertIn('xml:lang="he"', result_str)
        # Check that content is preserved
        self.assertIn('English text', result_str)
        self.assertIn('עברית', result_str)

    def test_namespace_prefixes_with_whitespace_preservation(self):
        """Test that namespace prefixes are preserved with whitespace handling."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>
                <tei:p>  Content with   spaces  </tei:p>
                <j:transclude>  Transclusion  </j:transclude>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        # Should preserve namespace prefixes with whitespace
        self.assertEqual(result_str, xml_input)

    def test_namespace_declarations_only_at_root(self):
        """Test that namespace declarations are only present at the root element, not duplicated."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div>
                <tei:p>Content</tei:p>
                <j:transclude>Transclusion</j:transclude>
            </tei:div>
            <tei:div>
                <tei:note>Note</tei:note>
                <j:milestone unit="chapter"/>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        
        # Should have exactly one of each namespace declaration
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        
        # Verify that namespace declarations are at the root element
        self.assertIn('<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">', result_str)
        
        # Verify that child elements don't have namespace declarations
        self.assertNotIn('<tei:div xmlns:', result_str)
        self.assertNotIn('<tei:p xmlns:', result_str)
        self.assertNotIn('<j:transclude xmlns:', result_str)
        self.assertNotIn('<tei:note xmlns:', result_str)
        self.assertNotIn('<j:milestone xmlns:', result_str)

    def test_namespace_declarations_not_duplicated_in_nested_elements(self):
        """Test that deeply nested elements don't get duplicate namespace declarations."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:text>
                <tei:body>
                    <tei:div type="chapter">
                        <tei:div type="section">
                            <tei:p>Deep content</tei:p>
                            <j:transclude>Deep transclusion</j:transclude>
                        </tei:div>
                    </tei:div>
                </tei:body>
            </tei:text>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        
        # Should have exactly one of each namespace declaration
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        
        # Verify that deeply nested elements don't have namespace declarations
        self.assertNotIn('<tei:text xmlns:', result_str)
        self.assertNotIn('<tei:body xmlns:', result_str)
        self.assertNotIn('<tei:div xmlns:', result_str)
        self.assertNotIn('<tei:p xmlns:', result_str)
        self.assertNotIn('<j:transclude xmlns:', result_str)

    def test_namespace_declarations_with_mixed_namespaces(self):
        """Test that multiple namespaces are declared only once at root, not duplicated."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" 
                              xmlns:j="http://jewishliturgy.org/ns/jlptei/2" 
                              xmlns="http://example.org/ns">
            <tei:teiHeader>
                <tei:fileDesc>
                    <tei:titleStmt>
                        <tei:title>Title</tei:title>
                    </tei:titleStmt>
                </tei:fileDesc>
            </tei:teiHeader>
            <text>
                <body>
                    <div type="chapter">
                        <p>Content in default namespace</p>
                        <tei:note>Note in TEI namespace</tei:note>
                        <j:transclude>Transclusion in J namespace</j:transclude>
                    </div>
                </body>
            </text>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        default_ns_count = result_str.count('xmlns="http://example.org/ns"')
        
        # Should have exactly one of each namespace declaration
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        self.assertEqual(default_ns_count, 1, f"Expected exactly 1 default namespace declaration, found {default_ns_count}")
        
        # Verify that child elements don't have namespace declarations
        self.assertNotIn('<tei:teiHeader xmlns:', result_str)
        self.assertNotIn('<tei:fileDesc xmlns:', result_str)
        self.assertNotIn('<tei:titleStmt xmlns:', result_str)
        self.assertNotIn('<tei:title xmlns:', result_str)
        self.assertNotIn('<text xmlns:', result_str)
        self.assertNotIn('<body xmlns:', result_str)
        self.assertNotIn('<div xmlns:', result_str)
        self.assertNotIn('<p xmlns:', result_str)
        self.assertNotIn('<tei:note xmlns:', result_str)
        self.assertNotIn('<j:transclude xmlns:', result_str)

    def test_namespace_declarations_with_attributes(self):
        """Test that elements with attributes don't get duplicate namespace declarations."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:div type="chapter" n="1" xml:id="ch1">
                <tei:p rend="italic" xml:lang="en">English text</tei:p>
                <j:transclude target="urn:example" xml:lang="he">עברית</j:transclude>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        
        # Should have exactly one of each namespace declaration
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        
        # Verify that elements with attributes don't have namespace declarations
        self.assertNotIn('<tei:div xmlns:', result_str)
        self.assertNotIn('<tei:p xmlns:', result_str)
        self.assertNotIn('<j:transclude xmlns:', result_str)

    def test_namespace_declarations_with_self_closing_elements(self):
        """Test that self-closing elements don't get duplicate namespace declarations."""
        xml_input = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
            <tei:br/>
            <tei:pb n="1"/>
            <j:milestone unit="chapter"/>
            <tei:div>
                <tei:pb n="2"/>
                <j:milestone unit="verse"/>
            </tei:div>
        </root>'''
        processor = CompilerProcessor(xml_input)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        
        # Should have exactly one of each namespace declaration
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        
        # Verify that self-closing elements don't have namespace declarations
        self.assertNotIn('<tei:br xmlns:', result_str)
        self.assertNotIn('<tei:pb xmlns:', result_str)
        self.assertNotIn('<j:milestone xmlns:', result_str)
        self.assertNotIn('<tei:div xmlns:', result_str)


if __name__ == '__main__':
    unittest.main()
