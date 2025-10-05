import unittest
from lxml import etree
from typing import Dict, Any, Optional

# Import the transformer to test
from opensiddur.importer.wlc.wlc import WLCIndexTransformer

class TestWLCIndexTransformer(unittest.TestCase):
    """Test cases for WLCIndexTransformer."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.transformer = WLCIndexTransformer()
        self.TEI_NS = "http://www.tei-c.org/ns/1.0"
        
    def test_add_tei_namespace_with_custom_tag(self):
        """Test _add_tei_namespace with a custom tag name."""
        # Create a test element with some attributes and children
        elem = etree.Element("TestElement", {"id": "test1", "class": "test"})
        etree.SubElement(elem, "Child", {"id": "child1"}).text = "Child 1"
        etree.SubElement(elem, "Child", {"id": "child2"}).text = "Child 2"
        
        # Call the method with a custom tag name
        result = self.transformer._add_tei_namespace(elem, {}, tag_name="CustomTag")
        
        # Verify the result
        self.assertEqual(result.tag, f"{{{self.TEI_NS}}}CustomTag")
        self.assertEqual(result.get("id"), "test1")
        self.assertEqual(result.get("class"), "test")
        self.assertIn("tei", result.nsmap)
        self.assertEqual(result.nsmap["tei"], self.TEI_NS)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tag, "Child")
        self.assertEqual(result[0].get("id"), "child1")
        self.assertEqual(result[0].text, "Child 1")
        self.assertEqual(result[1].tag, "Child")
        self.assertEqual(result[1].get("id"), "child2")
        self.assertEqual(result[1].text, "Child 2")
    
    def test_add_tei_namespace_default_tag(self):
        """Test _add_tei_namespace with default tag name (using original element's tag)."""
        # Create a test element with a namespaced tag
        elem = etree.Element("{http://example.com/ns}OriginalTag", {"id": "test2"})
        etree.SubElement(elem, "Child").text = "Test child"
        
        # Call the method without specifying a tag name
        result = self.transformer._add_tei_namespace(elem, {})
        
        # Verify the result uses the original local name but with TEI namespace
        self.assertEqual(result.tag, f"{{{self.TEI_NS}}}OriginalTag")
        self.assertEqual(result.get("id"), "test2")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tag, "Child")
        self.assertEqual(result[0].text, "Test child")
        
    def test_add_tei_namespace_with_extra_attrs(self):
        """Test _add_tei_namespace with extra attributes."""
        elem = etree.Element("TestElement", {"id": "test3"})
        
        # Call with extra attributes
        result = self.transformer._add_tei_namespace(
            elem, {}, 
            tag_name="TagWithAttrs",
            extra_attr1="value1",
            extra_attr2="value2"
        )
        
        self.assertEqual(result.tag, f"{{{self.TEI_NS}}}TagWithAttrs")
        self.assertEqual(result.get("id"), "test3")
        self.assertEqual(result.get("extra_attr1"), "value1")
        self.assertEqual(result.get("extra_attr2"), "value2")
    
    def test_tanach_transform(self):
        """Test that a Tanach element is transformed to a TEI element."""
        # Create a test Tanach element with some attributes and children
        tanach = etree.Element("Tanach", {"id": "test-id", "lang": "hbo"})
        etree.SubElement(tanach, "Book", {"id": "Gen"}).text = "Genesis"
        etree.SubElement(tanach, "Book", {"id": "Exod"}).text = "Exodus"
        
        # Transform the element
        result = self.transformer.transform_node(tanach, {})
        
        # Check the root element
        self.assertEqual(result.tag, f"{{{self.TEI_NS}}}TEI")
        self.assertEqual(result.get("id"), "test-id")
        self.assertEqual(result.get("lang"), "hbo")
        self.assertIn("tei", result.nsmap)
        self.assertEqual(result.nsmap["tei"], self.TEI_NS)
        
        # Check that children were processed and preserved
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tag, "Book")
        self.assertEqual(result[0].get("id"), "Gen")
        self.assertEqual(result[0].text, "Genesis")
        self.assertEqual(result[1].tag, "Book")
        self.assertEqual(result[1].get("id"), "Exod")
        self.assertEqual(result[1].text, "Exodus")
    
    def test_empty_tanach(self):
        """Test transformation of an empty Tanach element."""
        tanach = etree.Element("Tanach")
        result = self.transformer.transform_node(tanach, {})
        
        self.assertEqual(result.tag, f"{{{self.TEI_NS}}}TEI")
        self.assertEqual(len(result), 0)  # No children
    
    def test_tanach_with_attributes(self):
        """Test that Tanach attributes are preserved in the transformation."""
        attrs = {
            "id": "test-123",
            "version": "1.0",
            "custom-attr": "value"
        }
        tanach = etree.Element("Tanach", attrs)
        
        result = self.transformer.transform_node(tanach, {})
        
        for name, value in attrs.items():
            self.assertEqual(result.get(name), value)
    
    def test_namespace_handling(self):
        """Test that existing namespaces are preserved in the transformation."""
        # Create an element with a custom namespace
        nsmap = {"custom": "http://example.com/custom"}
        tanach = etree.Element("Tanach", nsmap=nsmap)
        etree.SubElement(tanach, "{http://example.com/custom}item").text = "test"
        
        result = self.transformer.transform_node(tanach, {})
        
        # Check that TEI namespace is registered with 'tei' prefix
        self.assertIn("tei", result.nsmap)
        self.assertEqual(result.nsmap["tei"], self.TEI_NS)
        
        # Check that custom namespace is preserved
        self.assertIn("custom", result.nsmap)
        self.assertEqual(result.nsmap["custom"], "http://example.com/custom")
        
        # Check that the namespaced child is preserved
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].tag.endswith("item"))
        self.assertEqual(result[0].text, "test")


if __name__ == "__main__":
    unittest.main()
