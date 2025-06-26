import unittest
from pathlib import Path
from lxml import etree
from typing import Dict, Any, Optional
import tempfile
import os
import sys

# Add the parent directory to the path so we can import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))

from opensiddur.converters.util.transformer import XMLTransformer


class TestTransformer(XMLTransformer):
    """Test transformer with custom element handlers."""
    
    def __init__(self):
        super().__init__()
        # Register transform functions for test elements
        self._transforms = {
            'test': self._transform_test,
            'uppercase': self._transform_uppercase
        }
    
    def _transform_test(self, node: etree._Element, parameters: Dict[str, Any]) -> etree._Element:
        """Add a 'transformed' attribute to test elements."""
        new_node = self._identity_transform(node, parameters)
        new_node.set('transformed', 'true')
        return new_node
    
    def _transform_uppercase(self, node: etree._Element, parameters: Dict[str, Any]) -> etree._Element:
        """Convert text content to uppercase."""
        new_node = self._identity_transform(node, parameters)
        if new_node.text:
            new_node.text = new_node.text.upper()
        return new_node


class TextTransformTestTransformer(TestTransformer):
    """Test transformer with custom text transformation."""
    
    def _transform_text(self, text: Optional[str], parameters: Dict[str, Any]) -> Optional[str]:
        """Transform text by adding a prefix and suffix."""
        if text is None:
            return None
        return f"[PREFIX]{text}[SUFFIX]"


class TestXMLTransformer(unittest.TestCase):    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.transformer = XMLTransformer()
        self.test_dir = Path(tempfile.mkdtemp())
    
    def test_transform_node_with_custom_transform(self):
        """Test transform with a custom element handler."""
        transformer = TestTransformer()
        
        # Create a test element
        elem = etree.Element("test", attrib={"id": "1"})
        elem.text = "test content"
        
        # Transform and verify
        result = transformer.transform_node(elem, {})
        
        self.assertEqual(result.tag, "test")
        self.assertEqual(result.get("id"), "1")
        self.assertEqual(result.get("transformed"), "true")
        self.assertEqual(result.text, "test content")
        self.assertIsNot(result, elem)  # Should be a deep copy
    
    def test_transform_node_with_uppercase_transform(self):
        """Test transform that modifies text content."""
        transformer = TestTransformer()
        
        # Create a test element
        elem = etree.Element("uppercase")
        elem.text = "make this uppercase"
        
        # Transform and verify
        result = transformer.transform_node(elem, {})
        
        self.assertEqual(result.text, "MAKE THIS UPPERCASE")
    
    def test_transform_node_with_nested_elements(self):
        """Test transform with nested elements and custom handlers."""
        transformer = TestTransformer()
        
        # Create a nested XML structure with elements that have custom transforms
        root = etree.Element("root")
        test_elem = etree.SubElement(root, "test", attrib={"id": "1"})
        test_elem.text = "test content"
        upper_elem = etree.SubElement(root, "uppercase")
        upper_elem.text = "make this uppercase"
        plain_elem = etree.SubElement(root, "plain")
        plain_elem.text = "this should stay the same"
        
        # Transform and verify
        result = transformer.transform_node(root, {})
        
        # Verify the structure was preserved
        self.assertEqual(len(result), 3)
        
        # Verify test element transform
        test_result = result[0]
        self.assertEqual(test_result.tag, "test")
        self.assertEqual(test_result.get("transformed"), "true")
        self.assertEqual(test_result.text, "test content")
        
        # Verify uppercase transform
        upper_result = result[1]
        self.assertEqual(upper_result.text, "MAKE THIS UPPERCASE")
        
        # Verify plain element (should use identity transform)
        plain_result = result[2]
        self.assertEqual(plain_result.text, "this should stay the same")
    
    def test_skip_transform(self):
        """Test that nodes can be skipped by returning None from a transform."""
        class SkipTransformer(TestTransformer):
            def __init__(self):
                super().__init__()
                # Override the test transform to sometimes skip
                self._transforms['test'] = self._conditional_skip
            
            def _conditional_skip(self, node: etree._Element, params: Dict[str, Any]) -> Optional[etree._Element]:
                # Skip if the node has skip="true"
                if node.get('skip') == 'true':
                    return self._skip_transform(node, params)
                return self._transform_test(node, params)
        
        transformer = SkipTransformer()
        
        # Create test XML with some nodes to skip
        root = etree.Element("root")
        etree.SubElement(root, "test", {"id": "1", "skip": "true"}).text = "skip me"
        etree.SubElement(root, "test", {"id": "2"}).text = "keep me"
        etree.SubElement(root, "test", {"id": "3", "skip": "true"}).text = "skip me too"
        etree.SubElement(root, "plain").text = "plain text"
        
        # Transform and verify
        result = transformer.transform_node(root, {})
        
        # Should have 2 children (one test node kept, one plain node)
        self.assertEqual(len(result), 2)
        
        # First child should be the non-skipped test node
        self.assertEqual(result[0].tag, "test")
        self.assertEqual(result[0].get("id"), "2")
        self.assertEqual(result[0].text, "keep me")
        self.assertEqual(result[0].get("transformed"), "true")
        
        # Second child should be the plain node
        self.assertEqual(result[1].tag, "plain")
        self.assertEqual(result[1].text, "plain text")
    
    def test_transform_with_parameters(self):
        """Test that parameters are passed to transform functions."""
        class ParamTransformer(XMLTransformer):
            def __init__(self):
                super().__init__()
                self._transforms = {
                    'param': self._transform_with_param
                }
            
            def _transform_with_param(self, node: etree._Element, params: Dict[str, Any]) -> etree._Element:
                new_node = self._identity_transform(node, params)
                if 'prefix' in params:
                    if new_node.text:
                        new_node.text = f"{params['prefix']}{new_node.text}"
                return new_node
        
        transformer = ParamTransformer()
        elem = etree.Element("param")
        elem.text = "value"
        
        # Test with parameter
        result = transformer.transform_node(elem, {"prefix": "prefixed_"})
        self.assertEqual(result.text, "prefixed_value")
        
        # Test without parameter
        result = transformer.transform_node(elem, {})
        self.assertEqual(result.text, "value")
    
    def test_transform_file(self):
        """Test transforming an XML file with custom transforms."""
        # Create a test XML file
        xml_content = """<?xml version="1.0"?>
        <root>
            <test id="1">test</test>
            <uppercase>make this uppercase</uppercase>
            <plain>this should stay the same</plain>
        </root>
        """
        input_file = self.test_dir / "test_input.xml"
        output_file = self.test_dir / "test_output.xml"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Test the transform with our test transformer
        transformer = TestTransformer()
        success = transformer.transform_file(input_file, output_file)
        
        self.assertTrue(success)
        self.assertTrue(output_file.exists())
        
        # Verify the output
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('<test id="1" transformed="true">test</test>', content)
            self.assertIn('<uppercase>MAKE THIS UPPERCASE</uppercase>', content)
            self.assertIn('<plain>this should stay the same</plain>', content)
    
    def test_transform_file_invalid_xml(self):
        """Test transforming an invalid XML file."""
        # Create an invalid XML file
        input_file = self.test_dir / "invalid.xml"
        output_file = self.test_dir / "output.xml"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write("<root><unclosed>")
        
        # Test the transform
        transformer = TestTransformer()
        success = transformer.transform_file(input_file, output_file)
        
        self.assertFalse(success)
        self.assertFalse(output_file.exists())
    
    def test_text_transform(self):
        """Test text transformation in elements and tails."""
        transformer = TextTransformTestTransformer()
        
        # Create test XML with text and tail content
        root = etree.Element("root")
        root.text = "root text"
        
        child1 = etree.SubElement(root, "test")
        child1.text = "child1 text"
        child1.tail = "tail1 text"
        
        child2 = etree.SubElement(root, "plain")
        child2.text = "child2 text"
        child2.tail = "tail2 text"
        
        # Transform and verify
        result = transformer.transform_node(root, {})
        
        # Check root text
        self.assertEqual(result.text, "[PREFIX]root text[SUFFIX]")
        
        # Check first child (test element with transform)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tag, "test")
        self.assertEqual(result[0].get("transformed"), "true")
        self.assertEqual(result[0].text, "[PREFIX]child1 text[SUFFIX]")
        self.assertEqual(result[0].tail, "[PREFIX]tail1 text[SUFFIX]")
        
        # Check second child (plain element with default transform)
        self.assertEqual(result[1].tag, "plain")
        self.assertEqual(result[1].text, "[PREFIX]child2 text[SUFFIX]")
        self.assertEqual(result[1].tail, "[PREFIX]tail2 text[SUFFIX]")
    
    def test_text_transform_none_removal(self):
        """Test that returning None from _transform_text removes the text."""
        class NoneTextTransformer(TextTransformTestTransformer):
            def _transform_text(self, text: Optional[str], parameters: Dict[str, Any]) -> Optional[str]:
                # Remove all text
                return None
        
        transformer = NoneTextTransformer()
        
        # Create test element with text and tail
        elem = etree.Element("test")
        elem.text = "this should be removed"
        elem.tail = "this should also be removed"
        
        # Transform and verify
        result = transformer.transform_node(elem, {})
        
        self.assertIsNone(result.text)
        self.assertIsNone(result.tail)


if __name__ == '__main__':
    unittest.main()
