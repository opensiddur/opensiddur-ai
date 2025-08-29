from pathlib import Path
from lxml import etree
from typing import Tuple, List, Optional
import argparse

def validate(xml: Path | str, schema_file: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validate an XML file against a RelaxNG schema.
    
    Args:
        xml_file: Path to the XML file to validate or XML content as a string
        schema_file: Optional path to the RelaxNG schema file. If not provided,
            will use the default schema at schema/jlptei.odd.xml.relaxng
                   
    Returns:
        Tuple of (is_valid, errors) where:
        - is_valid: Boolean indicating if the XML is valid
        - errors: List of error messages if validation fails, empty list if valid
    """
    try:
        # Load and parse the XML file
        if isinstance(xml, str):
            xml_doc = etree.fromstring(xml)
        else:
            xml_doc = etree.parse(str(xml))
        
        # Determine the schema file to use
        if schema_file is None:
            # Default to the project's main schema
            project_root = Path(__file__).parent.parent.parent.parent
            schema_file = project_root / 'schema' / 'jlptei.odd.xml.relaxng'
    
        # Load and parse the RelaxNG schema
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
            
    except etree.DocumentInvalid as e:
        # This catches validation errors that occur during parsing
        return False, [str(e)]
    except etree.XMLSyntaxError as e:
        # This catches XML syntax errors
        return False, [f"XML syntax error: {e.msg} at line {e.lineno}, column {e.position[0]}"]
    except Exception as e:
        # Catch any other exceptions
        return False, [f"Error during validation: {str(e)}"]
    
def main():
    parser = argparse.ArgumentParser(description='Validate an XML file against a RelaxNG schema.')
    parser.add_argument('xml_file', type=str, help='Path to the XML file to validate')
    parser.add_argument('--schema_file', type=str, help='Path to the RelaxNG schema file', default=None)
    args = parser.parse_args()
    
    is_valid, errors = validate(Path(args.xml_file), 
                                Path(args.schema_file) if args.schema_file else None)
    
    if is_valid:
        print(f"{args.xml_file} is valid.")
    else:
        print(f"{args.xml_file} is not valid.")
        for error in errors:
            print(error)
    
    return is_valid

if __name__ == "__main__":
    main()
        