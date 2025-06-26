import sys
from pathlib import Path
from typing import Any, Dict, Optional
from lxml import etree


class XMLTransformer:
    """
    A class for transforming XML documents with support for element-specific transforms.
    
    This class provides a framework for performing transforms on XML documents.
    It looks up element names in the _transforms dictionary and calls the
    corresponding transform function if found, otherwise performs an identity transform.
    """
    
    def __init__(self):
        """Initialize the XML transformer with a default parser configuration."""
        self.parser = etree.XMLParser(remove_blank_text=True)
        # Dictionary mapping (namespace, tag) tuples to transform functions
        # Format: {(namespace_uri, tag_name): transform_function}
        # Use (None, tag_name) for elements without a namespace
        self._transforms = {}
    
    def transform_node(self, node: etree._Element, parameters: Dict[str, Any] = None) -> Optional[etree._Element]:
        """
        Transform an XML node using the appropriate transform function.
        
        Args:
            node: An lxml.etree._Element node to transform
            parameters: A dictionary of parameters that can be used during transformation
            
        Returns:
            The transformed lxml.etree._Element node or None if the node should be skipped
        """
        parameters = parameters or {}
            
        # Get the namespace URI for the node's tag
        if '}' in node.tag:
            # Tag has a namespace (format: {namespace}tag)
            namespace_uri, tag_name = node.tag[1:].split('}', 1)
        else:
            # No namespace
            namespace_uri = None
            tag_name = node.tag
        
        # Find a transform with the exact namespace and tag name
        transform_func = self._transforms.get((namespace_uri, tag_name), self._identity_transform)
            
        # Call the transform function with the node and parameters
        result = transform_func(node, parameters)
            
        return result
    
    def _skip_transform(self, node: etree._Element, parameters: Dict[str, Any]) -> None:
        """
        Skip this node by returning None. This will cause the node to be excluded from the output.
        
        Args:
            node: The node to skip (unused)
            parameters: Dictionary of parameters (unused)
            
        Returns:
            None to indicate the node should be skipped
        """
        return None
    
    def _transform_text(self, text: Optional[str], parameters: Dict[str, Any]) -> Optional[str]:
        """
        Transform a text node. Override this method in subclasses to implement custom text transformations.
        
        Args:
            text: The text content to transform, or None if there is no text
            parameters: Dictionary of parameters that can be used during transformation
            
        Returns:
            The transformed text, or None to remove the text
        """
        # Default implementation returns the text unchanged
        return text
        
    def _identity_transform(self, node: etree._Element, parameters: Dict[str, Any]) -> etree._Element:
        """
        Default identity transform that preserves the node structure.
        
        Args:
            node: The node to transform
            parameters: Dictionary of parameters (unused in identity transform)
            
        Returns:
            A new node with the same structure as the input
        """
        # Create a deep copy of the node to avoid modifying the original
        new_node = etree.Element(node.tag, attrib=node.attrib)
        
        # Transform the text content if it exists
        new_node.text = self._transform_text(node.text, parameters)
        
        # Note: Tail text is transformed when the parent processes its children
        
        # Recursively process child nodes, skipping any that return None
        for child in node:
            transformed_child = self.transform_node(child, parameters)
            if transformed_child is not None:
                # If this child has a tail, transform it using our transform_text method
                transformed_tail = self._transform_text(child.tail, parameters)
                transformed_child.tail = transformed_tail
                new_node.append(transformed_child)
            
        return new_node
    
    def transform_file(self, input_file: Path, output_file: Path) -> bool:
        """
        Transform an XML file and write the result to output file.
        
        Args:
            input_file: Path to the input XML file
            output_file: Path where to write the transformed XML
            
        Returns:
            bool: True if transformation was successful, False otherwise
        """
        try:
            # Parse the input XML
            tree = etree.parse(str(input_file), self.parser)
            root = tree.getroot()
            
            # Apply transformation with empty parameters
            transformed_root = self.transform_node(root, {})
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a new tree and write to file with pretty printing
            result_tree = etree.ElementTree(transformed_root)
            result_tree.write(
                str(output_file),
                pretty_print=True,
                xml_declaration=True,
                encoding='UTF-8'
            )
            return True
            
        except etree.XMLSyntaxError as e:
            print(f"XML syntax error in {input_file}: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error processing {input_file}: {e}", file=sys.stderr)
            return False
