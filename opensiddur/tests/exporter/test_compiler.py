"""Tests for the CompilerProcessor class."""

import re
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from lxml import etree
from opensiddur.exporter.compiler import CompilerProcessor, InlineCompilerProcessor
from opensiddur.exporter.linear import LinearData, reset_linear_data, get_linear_data
from opensiddur.exporter.urn import ResolvedUrn


class TestCompilerProcessorWithFiles(unittest.TestCase):
    """Test CompilerProcessor with file-based input (no transclusions, no start/end)."""

    def setUp(self):
        """Set up test fixtures and reset linear data."""
        reset_linear_data()
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name) / "test_project"
        self.test_project_dir.mkdir(parents=True)
        
        # Patch the xml_cache base_path to use our temp directory
        linear_data = get_linear_data()
        linear_data.xml_cache.base_path = Path(self.temp_dir.name)

    def _create_test_file(self, file_name: str, content: bytes) -> tuple[str, str]:
        """Create a test XML file and return (project, file_name) tuple."""
        file_path = self.test_project_dir / file_name
        with open(file_path, 'wb') as f:
            f.write(content)
        return "test_project", file_name

    def test_process_simple_xml_file(self):
        """Test processing a simple XML file with no transclusions."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:p>Simple text content</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("simple.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        # Convert to string for comparison
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve namespace prefixes
        self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result_str)
        self.assertIn('<tei:div>', result_str)
        self.assertIn('<tei:p>', result_str)
        self.assertIn('Simple text content', result_str)
        
        # Should add processing namespace
        self.assertIn('xmlns:p="http://jewishliturgy.org/ns/processing"', result_str)
        
        # Verify structure is preserved
        self.assertIn('<tei:div>', result_str)
        self.assertIn('</tei:div>', result_str)

    def test_process_preserves_multiple_namespaces(self):
        """Test that processing preserves multiple namespace prefixes."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:text>
        <tei:body>
            <tei:div>
                <tei:p>TEI content</tei:p>
                <j:milestone unit="verse"/>
            </tei:div>
        </tei:body>
    </tei:text>
</root>'''
        
        project, file_name = self._create_test_file("multi_ns.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve both namespace prefixes
        self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result_str)
        self.assertIn('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"', result_str)
        self.assertIn('<tei:text>', result_str)
        self.assertIn('<tei:body>', result_str)
        self.assertIn('<j:milestone', result_str)
        
        # Verify content is preserved
        self.assertIn('TEI content', result_str)

    def test_process_preserves_attributes(self):
        """Test that processing preserves element attributes."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div type="chapter" n="1" xml:id="ch1">
        <tei:p rend="italic">Italic text</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("attributes.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve all attributes
        self.assertIn('type="chapter"', result_str)
        self.assertIn('n="1"', result_str)
        self.assertIn('xml:id="ch1"', result_str)
        self.assertIn('rend="italic"', result_str)

    def test_process_preserves_tail_text(self):
        """Test that processing preserves tail text."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>Content</tei:div>Tail text after div
    <tei:p>Paragraph</tei:p>More tail
</root>'''
        
        project, file_name = self._create_test_file("tail.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve tail text
        self.assertIn('Tail text after div', result_str)
        self.assertIn('More tail', result_str)

    def test_process_empty_elements(self):
        """Test that processing preserves empty elements."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div/>
    <tei:pb n="1"/>
    <tei:br/>
</root>'''
        
        project, file_name = self._create_test_file("empty.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve empty/self-closing elements
        self.assertIn('<tei:div/>', result_str)
        self.assertIn('<tei:pb', result_str)
        self.assertIn('n="1"', result_str)
        self.assertIn('<tei:br/>', result_str)

    def test_process_complex_structure(self):
        """Test processing a complex XML structure."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:title>Test Document</tei:title>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:text>
        <tei:body>
            <tei:div type="chapter" n="1">
                <tei:p>First paragraph</tei:p>
                <j:milestone unit="verse" n="1"/>
                <tei:p>Second paragraph</tei:p>
            </tei:div>
        </tei:body>
    </tei:text>
</root>'''
        
        project, file_name = self._create_test_file("complex.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve all structure
        self.assertIn('<tei:teiHeader>', result_str)
        self.assertIn('<tei:fileDesc>', result_str)
        self.assertIn('<tei:titleStmt>', result_str)
        self.assertIn('<tei:title>', result_str)
        self.assertIn('Test Document', result_str)
        self.assertIn('<tei:text>', result_str)
        self.assertIn('<tei:body>', result_str)
        self.assertIn('<tei:div', result_str)
        self.assertIn('type="chapter"', result_str)
        self.assertIn('<j:milestone', result_str)
        self.assertIn('unit="verse"', result_str)
        self.assertIn('First paragraph', result_str)
        self.assertIn('Second paragraph', result_str)

    def test_process_namespace_declarations_only_at_root(self):
        """Test that namespace declarations are only at root, not duplicated."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:div>
        <tei:p>Content</tei:p>
        <j:milestone unit="verse"/>
    </tei:div>
    <tei:div>
        <tei:note>Note</tei:note>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("ns_decl.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Count namespace declarations - should only be at root
        tei_ns_count = result_str.count('xmlns:tei="http://www.tei-c.org/ns/1.0"')
        j_ns_count = result_str.count('xmlns:j="http://jewishliturgy.org/ns/jlptei/2"')
        
        self.assertEqual(tei_ns_count, 1, f"Expected exactly 1 TEI namespace declaration, found {tei_ns_count}")
        self.assertEqual(j_ns_count, 1, f"Expected exactly 1 J namespace declaration, found {j_ns_count}")
        
        # Verify child elements don't have namespace declarations
        self.assertNotIn('<tei:div xmlns:', result_str)
        self.assertNotIn('<tei:p xmlns:', result_str)
        self.assertNotIn('<j:milestone xmlns:', result_str)

    def test_process_with_unicode_content(self):
        """Test processing XML with Unicode content."""
        xml_content = '''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div xml:lang="he">
        <tei:p>עברית Hebrew text</tei:p>
    </tei:div>
    <tei:div xml:lang="zh">
        <tei:p>中文 Chinese text</tei:p>
    </tei:div>
</root>'''.encode('utf-8')
        
        project, file_name = self._create_test_file("unicode.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should preserve Unicode content
        self.assertIn('עברית', result_str)
        self.assertIn('中文', result_str)
        self.assertIn('Hebrew text', result_str)
        self.assertIn('Chinese text', result_str)

    def test_process_adds_processing_namespace(self):
        """Test that processing adds the processing namespace to root."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:p>Content</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("processing_ns.xml", xml_content)
        
        processor = CompilerProcessor(project, file_name)
        result = processor.process()
        
        result_str = etree.tostring(result, encoding='unicode')
        
        # Should add processing namespace
        self.assertIn('xmlns:p="http://jewishliturgy.org/ns/processing"', result_str)


class TestInlineCompilerProcessor(unittest.TestCase):
    """Test InlineCompilerProcessor for extracting text content between start and end markers."""

    def setUp(self):
        """Set up test fixtures and reset linear data."""
        reset_linear_data()
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name) / "test_project"
        self.test_project_dir.mkdir(parents=True)
        
        # Patch the xml_cache base_path to use our temp directory
        linear_data = get_linear_data()
        linear_data.xml_cache.base_path = Path(self.temp_dir.name)

    def _create_test_file(self, file_name: str, content: bytes) -> tuple[str, str]:
        """Create a test XML file and return (project, file_name) tuple."""
        file_path = self.test_project_dir / file_name
        with open(file_path, 'wb') as f:
            f.write(content)
        return "test_project", file_name

    def test_start_and_end_are_siblings(self):
        """Test when start and end are sibling elements at the same level."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:p corresp="urn:start">First paragraph</tei:p>
        <tei:p>Middle paragraph</tei:p>
        <tei:p corresp="urn:end">Last paragraph</tei:p>
        <tei:p>After end paragraph</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("siblings.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        # Result should be a p:transcludeInline element with the extracted text
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        result_text = result.text
        
        # Should include ONLY text from start, middle, and end paragraphs with whitespace between them
        pattern = r'^\s*First paragraph\s+Middle paragraph\s+Last paragraph\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL), 
                             f"Result text should match pattern. Got: {result_text!r}")
        
        # Should NOT include text after end
        self.assertNotIn("After end paragraph", result_text)

    def test_start_is_ancestor_of_end(self):
        """Test when start element is an ancestor of the end element."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div corresp="urn:start">
        <tei:p>Outer start text</tei:p>
        <tei:div>
            <tei:p>Nested middle text</tei:p>
            <tei:p corresp="urn:end">Nested end text</tei:p>
            <tei:p>After end text</tei:p>
        </tei:div>
        <tei:p>After nested div</tei:p>
    </tei:div>
    <tei:div>
        <tei:p>After start div</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("ancestor.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        result_text = result.text
        
        # Should include ONLY text from start element and up to end
        pattern = r'^\s*Outer start text\s+Nested middle text\s+Nested end text\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL),
                             f"Result text should match pattern. Got: {result_text!r}")
        
        # Should NOT include text after end
        self.assertNotIn("After end text", result_text)
        self.assertNotIn("After nested div", result_text)
        self.assertNotIn("After start div", result_text)

    def test_start_deeper_than_end(self):
        """Test when start is 3 levels deep and end is 2 levels deep."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:div>
            <tei:div>
                <tei:p corresp="urn:start">Start at level 3</tei:p>
                <tei:p>Also level 3</tei:p>
            </tei:div>
            <tei:p>Back to level 2</tei:p>
        </tei:div>
        <tei:p corresp="urn:end">End at level 2</tei:p>
        <tei:p>After end at level 2</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("depth_diff.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        result_text = result.text
        
        # Should include ONLY text from start through end
        pattern = r'^\s*Start at level 3\s+Also level 3\s+Back to level 2\s+End at level 2\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL),
                             f"Result text should match pattern. Got: {result_text!r}")
        
        # Should NOT include text after end
        self.assertNotIn("After end at level 2", result_text)

    def test_start_and_end_descendants_of_different_siblings(self):
        """Test when start and end are descendants of different sibling elements."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:div type="first">
            <tei:p>Before start in first div</tei:p>
            <tei:p corresp="urn:start">Start in first div</tei:p>
            <tei:p>After start in first div</tei:p>
        </tei:div>
        <tei:div type="second">
            <tei:p>Content in second div</tei:p>
            <tei:p corresp="urn:end">End in second div</tei:p>
            <tei:p>After end in second div</tei:p>
        </tei:div>
        <tei:div type="third">
            <tei:p>Content in third div (after end)</tei:p>
        </tei:div>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("diff_siblings.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        result_text = result.text
        
        # Should include ONLY text from start through end across different sibling divs
        pattern = r'^\s*Start in first div\s+After start in first div\s+Content in second div\s+End in second div\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL),
                             f"Result text should match pattern. Got: {result_text!r}")
        
        # Should NOT include text before start or after end
        self.assertNotIn("Before start in first div", result_text)
        self.assertNotIn("After end in second div", result_text)
        self.assertNotIn("Content in third div", result_text)

    def test_result_is_text_element(self):
        """Test that InlineCompilerProcessor returns a p:transcludeInline element."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:p corresp="urn:start">Start</tei:p>
    <tei:p corresp="urn:end">End</tei:p>
</root>'''
        
        project, file_name = self._create_test_file("text_elem.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        # Should be a p:transcludeInline element
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        self.assertIsInstance(result, etree._Element)
        
        # Should have text content
        self.assertIsNotNone(result.text)
        self.assertIn("Start", result.text)
        self.assertIn("End", result.text)

    def test_text_extraction_preserves_whitespace(self):
        """Test that whitespace in text is preserved."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:p corresp="urn:start">  Start with spaces  </tei:p>
    <tei:p>  Middle  with  spaces  </tei:p>
    <tei:p corresp="urn:end">  End with spaces  </tei:p>
</root>'''
        
        project, file_name = self._create_test_file("whitespace.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        result_text = result.text
        
        # Whitespace should be preserved in the extracted text
        self.assertIn("Start with spaces", result_text)
        self.assertIn("Middle", result_text)
        self.assertIn("spaces", result_text)
        self.assertIn("End with spaces", result_text)

    def test_using_xml_id_instead_of_corresp(self):
        """Test that xml:id can be used with #id notation for start/end."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:p xml:id="start_id">Start with xml:id</tei:p>
    <tei:p>Middle content</tei:p>
    <tei:p xml:id="end_id">End with xml:id</tei:p>
    <tei:p>After end</tei:p>
</root>'''
        
        project, file_name = self._create_test_file("xmlid.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "#start_id", "#end_id")
        result = processor.process()
        
        result_text = result.text
        
        # Should extract text using xml:id
        self.assertIn("Start with xml:id", result_text)
        self.assertIn("Middle content", result_text)
        self.assertIn("End with xml:id", result_text)
        
        # Should NOT include text after end
        self.assertNotIn("After end", result_text)

    def test_mixed_corresp_and_xml_id(self):
        """Test using corresp for start and xml:id for end."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:p corresp="urn:start">Start with corresp</tei:p>
    <tei:p>Middle content</tei:p>
    <tei:p xml:id="end_id">End with xml:id</tei:p>
</root>'''
        
        project, file_name = self._create_test_file("mixed.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "#end_id")
        result = processor.process()
        
        result_text = result.text
        
        # Should work with mixed identifier types
        self.assertIn("Start with corresp", result_text)
        self.assertIn("Middle content", result_text)
        self.assertIn("End with xml:id", result_text)

    def test_single_element_start_equals_end(self):
        """Test when start and end are the same element."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:p>Before</tei:p>
    <tei:p corresp="urn:target">Target content</tei:p>
    <tei:p>After</tei:p>
</root>'''
        
        project, file_name = self._create_test_file("single.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:target", "urn:target")
        result = processor.process()
        
        result_text = result.text
        
        # Should extract ONLY the target element's text
        pattern = r'^\s*Target content\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL),
                             f"Result text should match pattern. Got: {result_text!r}")

    def test_start_and_end_both_2_levels_deep(self):
        """Test when start and end are both at the same depth (2 levels) as siblings."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:div>
            <tei:p>Content before start</tei:p>
            <tei:p corresp="urn:start">Start at level 2</tei:p>
            <tei:p>Middle content at level 2</tei:p>
            <tei:p corresp="urn:end">End at level 2</tei:p>
            <tei:p>Content after end</tei:p>
        </tei:div>
        <tei:p>Content outside nested div</tei:p>
    </tei:div>
</root>'''
        
        project, file_name = self._create_test_file("both_level2.xml", xml_content)
        
        processor = InlineCompilerProcessor(project, file_name, "urn:start", "urn:end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        result_text = result.text
        
        # Should include ONLY text from start through end at level 2
        pattern = r'^\s*Start at level 2\s+Middle content at level 2\s+End at level 2\s*$'
        self.assertIsNotNone(re.match(pattern, result_text, re.DOTALL),
                             f"Result text should match pattern. Got: {result_text!r}")

    @patch('opensiddur.exporter.urn.UrnResolver.resolve_range')
    @patch('opensiddur.exporter.urn.UrnResolver.prioritize_range')
    def test_inline_transclusion(self, mock_prioritize, mock_resolve_range):
        """Test InlineCompilerProcessor with a transclusion element."""
        # Create main file with transclusion element
        # Include text before start, after end, and tail text on elements
        main_xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:p>Text before start (excluded)</tei:p> Also before start.
    <tei:p corresp="urn:main-start">Text before transclusion</tei:p> tail after start element
    <j:transclude target="urn:other:start" targetEnd="urn:other:end" type="inline"/> tail after transclude
    <tei:p corresp="urn:main-end">Text after transclusion</tei:p> tail after end element
    <tei:p>Text after end (excluded)</tei:p>
</root>'''
        
        # Create transcluded file with tail text before start, between elements, and after end
        transcluded_xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:p>Before transcluded start (excluded)</tei:p> Tail before start (excluded)
        <tei:p corresp="urn:other:start">Transcluded start</tei:p> Tail after transcluded start
        <tei:p>Transcluded middle</tei:p> Tail after transcluded middle
        <tei:p corresp="urn:other:end">Transcluded end</tei:p> Tail of end element (included)
        <tei:p>After transcluded end (excluded)</tei:p>
    </tei:div>
</root>'''
        
        # Set up files
        main_project, main_file = self._create_test_file("main.xml", main_xml_content)
        trans_project, trans_file = self._create_test_file("transcluded.xml", transcluded_xml_content)
        
        # Mock URN resolution to return the transcluded file location
        mock_resolve_range.side_effect = [
            [ResolvedUrn(project=trans_project, file_name=trans_file, urn="urn:other:start")],
            [ResolvedUrn(project=trans_project, file_name=trans_file, urn="urn:other:end")]
        ]
        mock_prioritize.side_effect = [
            ResolvedUrn(project=trans_project, file_name=trans_file, urn="urn:other:start"),
            ResolvedUrn(project=trans_project, file_name=trans_file, urn="urn:other:end")
        ]
        
        # Process the main file
        processor = InlineCompilerProcessor(main_project, main_file, "urn:main-start", "urn:main-end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        
        # The result should include main text directly
        self.assertIn("Text before transclusion", result.text)
        self.assertIn("Text after transclusion", result.text)
        
        # Should include tail text from start element
        self.assertIn("tail after start element", result.text)
        
        # Should NOT include text before start or after end
        self.assertNotIn("Text before start (excluded)", result.text)
        self.assertNotIn("Also before start", result.text)
        self.assertNotIn("Text after end (excluded)", result.text)
        self.assertNotIn("tail after end element", result.text)
        
        # Verify that resolve_range was called with correct URNs
        mock_resolve_range.assert_any_call("urn:other:start")
        mock_resolve_range.assert_any_call("urn:other:end")
        
        # Verify the result contains a p:transclude element as a child
        # p:transclude elements are retained as children in InlineCompilerProcessor
        transclude_children = result.findall(".//{http://jewishliturgy.org/ns/processing}transclude")
        self.assertEqual(len(transclude_children), 1)
        
        transclude_elem = transclude_children[0]
        self.assertEqual(transclude_elem.get('target'), 'urn:other:start')
        self.assertEqual(transclude_elem.get('targetEnd'), 'urn:other:end')
        self.assertEqual(transclude_elem.get('type'), 'inline')
        
        # The transcluded text should be in the p:transclude element
        self.assertIn("Transcluded start", transclude_elem.text)
        self.assertIn("Transcluded middle", transclude_elem.text)
        self.assertIn("Transcluded end", transclude_elem.text)
        
        # Should include tail text from within the transcluded content
        self.assertIn("Tail after transcluded start", transclude_elem.text)
        self.assertIn("Tail after transcluded middle", transclude_elem.text)
        # The tail of the end element is also included (it's part of the range)
        self.assertIn("Tail of end element (included)", transclude_elem.text)
        
        # Should NOT include text/tails before start or after the end element's tail
        self.assertNotIn("Before transcluded start (excluded)", transclude_elem.text)
        self.assertNotIn("Tail before start (excluded)", transclude_elem.text)
        self.assertNotIn("After transcluded end (excluded)", transclude_elem.text)
        
        # The p:transclude element should have the tail text from the main file
        self.assertIsNotNone(transclude_elem.tail)
        self.assertIn("tail after transclude", transclude_elem.tail)

    @patch('opensiddur.exporter.urn.UrnResolver.resolve_range')
    @patch('opensiddur.exporter.urn.UrnResolver.prioritize_range')
    def test_nested_transclusion(self, mock_prioritize, mock_resolve_range):
        """Test InlineCompilerProcessor with nested transclusions (transcluded file has its own transclusion)."""
        # Create main file with transclusion element
        main_xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:p corresp="urn:main-start">Text before transclusion</tei:p>
    <j:transclude target="urn:level1:start" targetEnd="urn:level1:end" type="inline"/>
    <tei:p corresp="urn:main-end">Text after transclusion</tei:p>
</root>'''
        
        # Create first level transcluded file that itself has a transclusion (type=external)
        level1_xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:div>
        <tei:p corresp="urn:level1:start">Level 1 start</tei:p>
        <j:transclude target="urn:level2:start" targetEnd="urn:level2:end" type="external"/>
        <tei:p corresp="urn:level1:end">Level 1 end</tei:p>
    </tei:div>
</root>'''
        
        # Create second level transcluded file
        level2_xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:div>
        <tei:p corresp="urn:level2:start">Level 2 start</tei:p>
        <tei:p>Level 2 middle</tei:p>
        <tei:p corresp="urn:level2:end">Level 2 end</tei:p>
    </tei:div>
</root>'''
        
        # Set up files
        main_project, main_file = self._create_test_file("main.xml", main_xml_content)
        level1_project, level1_file = self._create_test_file("level1.xml", level1_xml_content)
        level2_project, level2_file = self._create_test_file("level2.xml", level2_xml_content)
        
        # Mock URN resolution for multiple levels
        # First two calls are for the main file's transclusion
        # Next two calls are for the level1 file's transclusion
        mock_resolve_range.side_effect = [
            [ResolvedUrn(project=level1_project, file_name=level1_file, urn="urn:level1:start")],
            [ResolvedUrn(project=level1_project, file_name=level1_file, urn="urn:level1:end")],
            [ResolvedUrn(project=level2_project, file_name=level2_file, urn="urn:level2:start")],
            [ResolvedUrn(project=level2_project, file_name=level2_file, urn="urn:level2:end")]
        ]
        mock_prioritize.side_effect = [
            ResolvedUrn(project=level1_project, file_name=level1_file, urn="urn:level1:start"),
            ResolvedUrn(project=level1_project, file_name=level1_file, urn="urn:level1:end"),
            ResolvedUrn(project=level2_project, file_name=level2_file, urn="urn:level2:start"),
            ResolvedUrn(project=level2_project, file_name=level2_file, urn="urn:level2:end")
        ]
        
        # Process the main file
        processor = InlineCompilerProcessor(main_project, main_file, "urn:main-start", "urn:main-end")
        result = processor.process()
        
        self.assertEqual(result.tag, "{http://jewishliturgy.org/ns/processing}transcludeInline")
        
        # The result should include main text directly
        self.assertIn("Text before transclusion", result.text)
        self.assertIn("Text after transclusion", result.text)
        
        # Find the top-level p:transclude element (from main file's transclusion)
        top_transclude = result.findall(".//{http://jewishliturgy.org/ns/processing}transclude")
        self.assertEqual(len(top_transclude), 2)  # One from level1, one nested from level2
        
        # The first p:transclude should be from the main file's transclusion to level1
        level1_transclude = top_transclude[0]
        self.assertEqual(level1_transclude.get('target'), 'urn:level1:start')
        self.assertEqual(level1_transclude.get('targetEnd'), 'urn:level1:end')
        self.assertEqual(level1_transclude.get('type'), 'inline')
        
        # Level 1 text should be in the first p:transclude element
        self.assertIn("Level 1 start", level1_transclude.text)
        self.assertIn("Level 1 end", level1_transclude.text)
        
        # The nested p:transclude (from level1's transclusion to level2) should also be present
        # Find it as a child of the first transclude
        nested_transclude = level1_transclude.findall(".//{http://jewishliturgy.org/ns/processing}transclude")
        self.assertEqual(len(nested_transclude), 1)
        
        level2_transclude = nested_transclude[0]
        self.assertEqual(level2_transclude.get('target'), 'urn:level2:start')
        self.assertEqual(level2_transclude.get('targetEnd'), 'urn:level2:end')
        # Even though the original j:transclude was type="external", InlineCompilerProcessor
        # should convert it to type="inline" because of the type_override
        self.assertEqual(level2_transclude.get('type'), 'inline')
        
        # Level 2 text should be in the nested p:transclude element
        self.assertIn("Level 2 start", level2_transclude.text)
        self.assertIn("Level 2 middle", level2_transclude.text)
        self.assertIn("Level 2 end", level2_transclude.text)


if __name__ == '__main__':
    unittest.main()
