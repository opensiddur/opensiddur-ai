#!/usr/bin/env python3
"""
JLPTEI to XeLaTeX Exporter

This script converts JLPTEI XML files to XeLaTeX format using XSLT transformation.
"""

import sys
import argparse
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from opensiddur.common.xslt import xslt_transform, xslt_transform_string

XSLT_FILE = Path(__file__).parent / "xelatex.xslt"


def transform_xml_to_tex(input_file, xslt_file=XSLT_FILE, output_file=None):
    """
    Transform a JLPTEI XML file to XeLaTeX using XSLT.
    
    Args:
        input_file (str): Path to the input TEI XML file
        xslt_file (str): Path to the XSLT transformation file
        output_file (str, optional): Path to the output .tex file. If None, output to stdout.
    
    Returns:
        str: The transformed XeLaTeX content
    """
    try:
        # Read the input XML
        with open(input_file, 'r', encoding='utf-8') as input_fd:
            input_xml = input_fd.read()
        
        # Use the string-based XSLT transformation function
        result = xslt_transform_string(Path(xslt_file), input_xml)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as output_fd:
                output_fd.write(result)
            print(f"XeLaTeX output written to: {output_file}", file=sys.stderr)
        else:
            sys.stdout.write(result)
        
    except Exception as e:
        print(f"Transformation error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to handle command line arguments and run the transformation."""
    parser = argparse.ArgumentParser(
        description="Convert JLPTEI XML files to XeLaTeX format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml
  %(prog)s input.xml -o output.tex
  %(prog)s input.xml --output output.tex
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to the input TEI XML file'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Path to the output .tex file (default: output to stdout)'
    )
    
    parser.add_argument(
        '--xslt',
        dest='xslt_file',
        default=os.path.join(os.path.dirname(__file__), 'xelatex.xslt'),
        help='Path to the XSLT transformation file (default: xelatex.xslt in the same directory)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Validate XSLT file exists
    if not os.path.exists(args.xslt_file):
        print(f"Error: XSLT file '{args.xslt_file}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Run the transformation
    transform_xml_to_tex(args.input_file, args.xslt_file, args.output_file)


if __name__ == '__main__':
    main()
