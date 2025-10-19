"""Tests for the CompilerProcessor class."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from lxml import etree
from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.linear import LinearData, reset_linear_data, get_linear_data


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


if __name__ == '__main__':
    unittest.main()
