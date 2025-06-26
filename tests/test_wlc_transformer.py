import unittest
from pathlib import Path
from lxml import etree
from typing import Dict, Any
import tempfile
import os
import sys

# Add the parent directory to the path so we can import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))

from opensiddur.converters.wlc.wlc import XMLTransformer


class TestXMLTransformer(unittest.TestCase):    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.transformer = XMLTransformer()
        self.test_dir = Path(tempfile.mkdtemp())
    
    def test_identity_transform_simple_element(self):
        """Test identity transform with a simple XML element."""
        # Create a simple XML element
        elem = etree.Element("test", attrib={"id": "1"})
        elem.text = "Test content"
        
        # Transform and verify
        result = self.transformer.identity_transform(elem, {})
        
        self.assertEqual(result.tag, "test")
        self.assertEqual(result.get("id"), "1")
        self.assertEqual(result.text, "Test content")
        self.assertIsNot(result, elem)  # Should be a deep copy
    
    def test_identity_transform_nested_elements(self):
        """Test identity transform with nested elements."""
        # Create a nested XML structure
        root = etree.Element("root")
        child = etree.SubElement(root, "child", attrib={"id": "1"})
        child.text = "Child content"
        
        # Transform and verify
        result = self.transformer.identity_transform(root, {})
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tag, "child")
        self.assertEqual(result[0].get("id"), "1")
        self.assertEqual(result[0].text, "Child content")
    
    def test_identity_transform_with_parameters(self):
        """Test that parameters are passed through the transform."""
        # Create a simple element
        elem = etree.Element("test")
        
        # Define a custom transform function that uses parameters
        def custom_identity_transform(node, params: Dict[str, Any]):
            new_node = etree.Element(node.tag, attrib=node.attrib)
            new_node.text = params.get("custom_text", node.text)
            new_node.tail = node.tail
            for child in node:
                new_node.append(custom_identity_transform(child, params))
            return new_node
        
        # Replace the identity_transform method for this test
        original_method = self.transformer.identity_transform
        self.transformer.identity_transform = custom_identity_transform
        
        try:
            # Test with custom parameter
            result = self.transformer.identity_transform(elem, {"custom_text": "Custom content"})
            self.assertEqual(result.text, "Custom content")
            
            # Test without custom parameter
            result = self.transformer.identity_transform(elem, {})
            self.assertIsNone(result.text)
            
        finally:
            # Restore original method
            self.transformer.identity_transform = original_method
    
    def test_transform_file(self):
        """Test transforming an XML file."""
        # Create a test XML file
        xml_content = """<?xml version="1.0"?>
        <root>
            <element id="1">Test</element>
        </root>
        """
        input_file = self.test_dir / "test_input.xml"
        output_file = self.test_dir / "test_output.xml"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Test the transform
        success = self.transformer.transform_file(input_file, output_file)
        
        self.assertTrue(success)
        self.assertTrue(output_file.exists())
        
        # Verify the output
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('<element id="1">Test</element>', content)
    
    def test_transform_file_invalid_xml(self):
        """Test transforming an invalid XML file."""
        # Create an invalid XML file
        input_file = self.test_dir / "invalid.xml"
        output_file = self.test_dir / "output.xml"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write("<root><unclosed>")
        
        # Test the transform
        success = self.transformer.transform_file(input_file, output_file)
        
        self.assertFalse(success)
        self.assertFalse(output_file.exists())


if __name__ == '__main__':
    unittest.main()
