import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from lxml import etree

# Import the XMLTransformer from its new location
from opensiddur.converters.util.transformer import XMLTransformer
from opensiddur.converters.util.validation import validate

# Define TEI namespace with 'tei' prefix
TEI_NS = "http://www.tei-c.org/ns/1.0"

class WLCIndexTransformer(XMLTransformer):
    def __init__(self):
        super().__init__()
        self._transforms = {
            (None, "coding"): self._skip_transform,
            (None, 'Tanach'): self._Tanach,
            (None, 'tanach'): self._tanach,
            (None, "teiHeader"): self._add_tei_namespace,
            (None, "fileDesc"): self._add_tei_namespace,
            (None, "titleStmt"): self._add_tei_namespace,
            (None, "editor"): self._add_tei_namespace,
            (None, "encodingDesc"): self._skip_transform,
            (None, "notesStmt"): self._skip_transform,
            (None, "publicationStmt"): self._add_tei_namespace,
            (None, "sourceDesc"): self._add_tei_namespace,
            (None, "biblItem"): self._biblItem,
        }
    
    def _add_tei_namespace(self, node: etree._Element, parameters: Dict[str, Any], 
                         tag_name: Optional[str] = None, **extra_attrs) -> etree._Element:
        """Helper method to add TEI namespace to an element and transform its children.
        
        Args:
            node: The source element to transform
            parameters: Transformation parameters
            tag_name: Optional new tag name (without namespace). If None, uses node's local name.
                   The element will use the TEI namespace.
            **extra_attrs: Additional attributes to add to the new element
            
        Returns:
            A new element with TEI namespace and transformed children
        """
        # Get the local name for the tag
        local_name = tag_name if tag_name is not None else etree.QName(node).localname
        
        # Create a new element with the TEI namespace
        nsmap = node.nsmap.copy()
        nsmap['tei'] = TEI_NS
        
        new_node = etree.Element(
            f"{{{TEI_NS}}}{local_name}",
            nsmap=nsmap,
            **{**node.attrib, **extra_attrs}
        )
        
        # Copy text and tail
        new_node.text = self._transform_text(node.text, parameters)
        new_node.tail = node.tail
        
        # Process and add all child nodes, preserving tails
        for child in node:
            transformed_child = self.transform_node(child, parameters)
            if transformed_child is not None:
                transformed_child.tail = child.tail
                new_node.append(transformed_child)
                
        return new_node
    
    def _Tanach(self, node: etree._Element, parameters: Dict[str, Any]) -> Optional[etree._Element]:
        """Transform the Tanach element to a TEI element with tei:TEI tag."""
        return self._add_tei_namespace(node, parameters, tag_name="TEI")
    
    def _tanach(self, node: etree._Element, parameters: Dict[str, Any]) -> Optional[etree._Element]:
        """Transform the Tanach element to a TEI element with tei:standOff[@type='notes'] tag."""
        return self._add_tei_namespace(node, parameters, tag_name="standOff", type="notes")

    def _biblItem(self, node: etree._Element, parameters: Dict[str, Any]) -> Optional[etree._Element]:
        """Transform a biblItem element to a tei:bibl element."""
        return self._add_tei_namespace(node, parameters, tag_name="bibl")

class WLCTransformer(XMLTransformer):
    def __init__(self):
        super().__init__()

def make_project_directory():
    """ Make the project/wlc directory if it doesn't exist """
    default_directory = Path(__file__).parent.parent.parent.parent / "project/wlc"
    default_directory.mkdir(parents=True, exist_ok=True)
    return default_directory

def get_source_directory() -> Path:
    return Path(__file__).parent.parent.parent.parent / "sources/wlc"

def xslt_transform(project_directory: Path, source_directory: Path, 
source_file: str, output_file: str, xslt_file: str):
    """ 
    Create the index.xml file with TEI header from TanachHeader.xml
    
    Args:
        project_directory: Path to the project directory
        source_directory: Path to the source directory containing Books/TanachHeader.xml
    """
    try:
        # Define input and output paths
        input_file = source_directory / "Books" / source_file
        output_file = project_directory / output_file
        
        # Get the directory containing the XSLT file
        xslt_file = Path(__file__).parent / xslt_file
        
        # Read the input XML
        with open(input_file, 'r', encoding='utf-8') as f:
            input_xml = f.read()
        
        # Perform the transformation
        from saxonche import PySaxonProcessor
        
        with PySaxonProcessor(license=False) as proc:
            # Create XSLT processor
            xslt_proc = proc.new_xslt30_processor()
            
            # Compile the stylesheet
            executable = xslt_proc.compile_stylesheet(stylesheet_file=str(xslt_file))
            if executable is None:
                raise ValueError(f"Failed to compile XSLT: {xslt_proc.error_message}")
            
            # Parse the input XML

            document = proc.parse_xml(xml_text=input_xml)
            
            # Transform the document
            result = executable.transform_to_string(xdm_node=document)
            
            # Write the result to the output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"Successfully created {output_file}")
            
    except Exception as e:
        print(f"Error in index function: {e}", file=sys.stderr)
        raise

def main():
    project_directory = make_project_directory()
    source_directory = get_source_directory()
    
    xslt_transform(project_directory, source_directory, "TanachHeader.xml", "index.xml", "transform_index.xslt")
    for book in os.listdir(source_directory / "Books"):
        if book not in ["TanachHeader.xml", "TanachIndex.xml"] and not book.endswith(".DH.xml"):
            print(f"Transforming {book}")
            xslt_transform(project_directory, source_directory, book, 
                book.lower(), "transform_book.xslt")

    for book in os.listdir(project_directory):
        if book.endswith(".xml"):
            print(f"Validating {book}")
            is_valid, errors = validate(project_directory / book)
            if not is_valid:
                print(f"Errors in {book}: {errors}")
    return 0

if __name__ == "__main__":
    sys.exit(main())