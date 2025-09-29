"""
XML prettification utilities for formatting XML strings with proper indentation.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
import argparse


def prettify_xml(xml_string: str, 
                indent: int=2, 
                remove_xml_declaration: bool=False,
                encoding: str="utf-8") -> str:
    """
    Prettify an XML string with proper indentation and formatting.
    
    Args:
        xml_string (str): The XML string to prettify
        indent (int): The indentation string to use (default: 2 spaces)
        remove_xml_declaration (bool): Whether to remove the XML declaration (default: False)
        encoding (str): The encoding to use (default: utf-8)
    
    Returns:
        str: The prettified XML string
        
    Raises:
        ET.ParseError: If the XML string is not valid XML
    """
    try:
        # Parse the XML string
        root = ET.fromstring(xml_string)
        
        # Convert to string with proper formatting
        rough_string = ET.tostring(root, encoding=encoding)
        
        # Parse with minidom for pretty printing
        reparsed = minidom.parseString(rough_string)
        
        # Get pretty printed XML
        pretty_xml = reparsed.toprettyxml(indent=" " * indent, encoding=encoding)
        
        # Decode if we got bytes
        if isinstance(pretty_xml, bytes):
            pretty_xml = pretty_xml.decode(encoding)
        
        lines = pretty_xml.split('\n')
        
        if remove_xml_declaration:
            lines = [line for line in lines if not line.strip().startswith('<?xml')]
        else:
            lines = [line for line in lines if line.strip()]

        return '\n'.join(lines)
        
    except ET.ParseError as e:
        raise ET.ParseError(f"Invalid XML: {e}")


def main():
    """Main function to handle command-line arguments and prettify XML files."""
    parser = argparse.ArgumentParser(
        description="Prettify XML files with proper indentation and formatting"
    )
    parser.add_argument(
        "input_file",
        help="Input XML file to prettify"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "-i", "--indent",
        type=int,
        default=2,
        help="Number of spaces for indentation (default: 2)"
    )
    parser.add_argument(
        "--remove-declaration",
        action="store_true",
        help="Remove XML declaration from output"
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding (default: utf-8)"
    )
    
    args = parser.parse_args()
    
    try:
        # Read input file
        with open(args.input_file, 'r', encoding=args.encoding) as f:
            xml_content = f.read()
        
        # Prettify the XML
        prettified = prettify_xml(
            xml_content,
            indent=args.indent,
            remove_xml_declaration=args.remove_declaration,
            encoding=args.encoding
        )
        
        # Write output
        if args.output:
            with open(args.output, 'w', encoding=args.encoding) as f:
                f.write(prettified)
            print(f"Prettified XML written to {args.output}", file=sys.stderr)
        else:
            print(prettified)
            
    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Invalid XML in '{args.input_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
