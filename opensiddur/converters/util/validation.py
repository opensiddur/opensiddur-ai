from pathlib import Path
import re
from lxml import etree
from lxml.etree import _ElementTree
from typing import Tuple, List, Optional
import argparse
from saxonche import PySaxonProcessor


from opensiddur.converters.agent.common import SCHEMA_RNG_PATH, SCHEMA_SCH_PATH, SCHEMA_SCH_XSLT_PATH
from opensiddur.converters.util.xslt import xslt_transform

def validate(xml: Path | str, 
    schema_file: Optional[Path] = None,
    schema: str = None,
    schematron_xslt_file: Optional[Path] = None,
    schematron: str = None) -> Tuple[bool, List[str]]:
    """
    Validate an XML file against the RelaxNG schema or the Schematron schema
    One of schema_file or schema, and one of schematron_file or schematron must be provided.

    Args:
        xml_file: Path to the XML file to validate or XML content as a string
        schema_file: Optional path to the RelaxNG schema file. If not provided,
            will use the default schema at schema/jlptei.odd.xml.relaxng
        schema: Optional RelaxNG schema as a string.
        schematron_file: Optional path to the Schematron XSLT schema file. If not provided,
            will use the default schema at schema/jlptei.odd.xml.schematron.xslt
        schematron: Optional Schematron XSLT schema as a string.
                   
    Returns:
        Tuple of (is_valid, errors) where:
        - is_valid: Boolean indicating if the XML is valid
        - errors: List of error messages if validation fails, empty list if valid
    """
    try:
        # Load and parse the XML file
        if isinstance(xml, str):
            xml_str = xml
            xml_doc = etree.fromstring(xml)
        else:
            with open(xml, "r") as f:
                xml_str = f.read()
            xml_doc = etree.parse(str(xml))
        
        # Determine the schema file to use
        is_valid_relax, errors_relax = relaxng_validate(xml_doc, schema or schema_file)
        is_valid_sch, errors_sch = schematron_validate(xml_str, schematron or schematron_xslt_file)
        
    
        return is_valid_relax and is_valid_sch, errors_relax + errors_sch
    except etree.DocumentInvalid as e:
        # This catches validation errors that occur during parsing
        return False, [str(e)]
    except etree.XMLSyntaxError as e:
        # This catches XML syntax errors
        return False, [f"XML syntax error: {e.msg} at line {e.lineno}, column {e.position[0]}"]
    except Exception as e:
        # Catch any other exceptions
        return False, [f"Error during validation: {str(e)}"]

def schematron_validate(
    xml_doc: str, 
    schematron_xslt_file: Optional[str |Path] = None) -> Tuple[bool, List[str]]:
    schematron_xslt_file = schematron_xslt_file or SCHEMA_SCH_XSLT_PATH
    try:
        # Load and parse the Schematron schema
        with PySaxonProcessor(license=False) as proc:
            # Create XSLT processor
            xslt_proc = proc.new_xslt30_processor()
            
            # Compile the stylesheet
            executable = xslt_proc.compile_stylesheet(stylesheet_file=str(schematron_xslt_file))
            if executable is None:
                raise ValueError(f"Failed to compile XSLT: {xslt_proc.error_message}")
            
            # Parse the input XML
            document = proc.parse_xml(xml_text=xml_doc)
            
            # Transform the document
            result = executable.transform_to_string(xdm_node=document)

        result = re.sub(r'^<\?xml[^>]*\?>\s*', '', result)   
        schematron_result = etree.fromstring(result)
        failures = schematron_result.xpath(".//svrl:failed-assert|.//svrl:successful-report", namespaces=schematron_result.nsmap) 

        if len(failures) == 0:
            return True, []
        else:
            # Get validation errors
            errors = []
            for error in failures:
                # Get all text content from the error element and its children
                error_text = "".join(error.itertext()).strip()
                errors.append(f"{error.attrib.get('location')}: {error_text}")
            return False, errors       
    except Exception as e:
        # Catch any other exceptions
        return False, [f"Error during validation: {str(e)}"]
    

def relaxng_validate(
    xml_doc: _ElementTree, 
    schema_file: Optional[str |Path] = None) -> Tuple[bool, List[str]]:
    schema_file = schema_file or SCHEMA_RNG_PATH
    try:
        # Load and parse the RelaxNG schema
        if isinstance(schema_file, str):
            # Remove any XML declaration if it exists
            schema_file = re.sub(r'^<\?xml[^>]*\?>\s*', '', schema_file)
            relaxng_doc = etree.fromstring(schema_file)
        else:
            relaxng_doc = etree.parse(str(schema_file))
        relaxng = etree.RelaxNG(relaxng_doc)
        
        # Validate the XML against the schema
        is_valid = relaxng.validate(xml_doc)
        
        if is_valid:
            return True, []
        else:
            # Get validation errors
            error_log = relaxng.error_log
            errors = [
                f"Line {error.line}, Column {error.column}: {error.message}"
                for error in error_log
            ]
            return False, errors
            
    except Exception as e:
        # Catch any other exceptions
        return False, [f"Error during validation: {str(e)}"]


def main():
    parser = argparse.ArgumentParser(description='Validate an XML file against a RelaxNG schema.')
    parser.add_argument('xml_file', type=str, help='Path to the XML file to validate')
    parser.add_argument('--relaxng_file', type=str, help='Path to the RelaxNG schema file', default=None)
    parser.add_argument('--schematron_file', type=str, help='Path to the Schematron schema file', default=None)
    args = parser.parse_args()
    
    is_valid, errors = validate(Path(args.xml_file), 
                                Path(args.relaxng_file) if args.relaxng_file else None,
                                Path(args.schematron_file) if args.schematron_file else None)
    
    if is_valid:
        print(f"{args.xml_file} is valid.")
    else:
        print(f"{args.xml_file} is not valid.")
        for error in errors:
            print(error)
    
    return is_valid

if __name__ == "__main__":
    main()
        