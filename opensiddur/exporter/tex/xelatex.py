#!/usr/bin/env python3
"""
JLPTEI to XeLaTeX Exporter

This script converts JLPTEI XML files to XeLaTeX format using XSLT transformation.
"""

import sys
import argparse
import os
from lxml import etree
from pathlib import Path

from pydantic import BaseModel

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
projects_source_root = project_root / "project"
sys.path.insert(0, str(project_root))

from opensiddur.common.xslt import xslt_transform, xslt_transform_string

XSLT_FILE = Path(__file__).parent / "xelatex.xslt"

class LicenseRecord(BaseModel):
    """ Record of the license for a given file. """
    url: str
    name: str

class CreditRecord(BaseModel):
    """ Record of the credit for a given file. """
    role: str
    resp_text: str
    ref: str
    name_text: str

def extract_licenses(xml_file_paths: list[Path]) -> dict[Path, LicenseRecord]:
    """
    Extract license URLs and names from a list of JLPTEI XML files.

    Args:
        xml_file_paths (list of Path): List of paths to JLPTEI XML files.

    Returns:
        dict: Mapping from file path to a list of LicenseRecord objects.
    """

    ns = {
        "tei": "http://www.tei-c.org/ns/1.0",
    }

    results = {}

    for file_path in xml_file_paths:
        try:
            relative_path = file_path.absolute().relative_to(projects_source_root)
            tree = etree.parse(file_path)
            root = tree.getroot()
            # Find all <tei:licence> elements anywhere in the document
            for licence in root.findall(".//tei:licence", ns):
                # Try to get the target attribute (URL)
                url = licence.attrib.get("target")
                # The text content is the license name
                name = (licence.text or "").strip()
                if url or name:
                    results[relative_path] = LicenseRecord(url=url, name=name)
                else:
                    print(f"Error: No license found for {relative_path}", file=sys.stderr)
        except Exception as e:
            # If there's a parse error or file error, skip and continue
            print(f"Error: {file_path}: {e}", file=sys.stderr)
            pass

    return results

def group_licenses(licenses: dict[Path, LicenseRecord]) -> list[LicenseRecord]:
    """
    Group licenses by URL.
    """
    license_urls = set()
    grouped_licenses = []
    for path, license in licenses.items():
        if license.url not in license_urls:
            license_urls.add(license.url)
            grouped_licenses.append(license)
    return grouped_licenses

def licenses_to_tex(licenses: list[LicenseRecord]) -> str:
    """
    Convert a list of LicenseRecord objects to a string of LaTeX code.
    """
    tex = f"""\\section{{Legal}}
This document includes copyrighted texts licensed under the following licenses.
The full text of the licenses can be found at the given URLs:

\\begin{{itemize}}
{'\n'.join([f"\\item {license.name} (\\url{{{license.url}}})" for license in licenses])}
\\end{{itemize}}

    """
    return tex

def extract_credits(xml_file_paths: list[Path]) -> dict[Path, list[dict]]:
    """
    Extract credits from a list of JLPTEI XML files.

    For each <tei:respStmt>, extract:
      - tei:resp/@key (as 'role')
      - tei:name/@ref (as 'ref')
      - tei:resp text (as 'resp_text')
      - tei:name text (as 'name_text')

    Args:
        xml_file_paths (list of Path): List of paths to JLPTEI XML files.

    Returns:
        dict: Mapping from file path to a list of credit dicts.
    """
    ns = {
        "tei": "http://www.tei-c.org/ns/1.0",
    }
    results = {}

    for file_path in xml_file_paths:
        credits = []
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            for resp_stmt in root.findall(".//tei:respStmt", ns):
                resp = resp_stmt.find("tei:resp", ns)
                name = resp_stmt.find("tei:name", ns)
                credit = {}
                if resp is not None:
                    credit["role"] = resp.attrib.get("key")
                    credit["resp_text"] = (resp.text or "").strip()
                else:
                    credit["role"] = None
                    credit["resp_text"] = ""
                if name is not None:
                    credit["ref"] = name.attrib.get("ref")
                    credit["name_text"] = (name.text or "").strip()
                else:
                    credit["ref"] = None
                    credit["name_text"] = ""
                credits.append(credit)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            pass
        results[file_path] = credits

    return results


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
        
        licenses = extract_licenses([Path(input_file)])
        licenses_tex = licenses_to_tex(group_licenses(licenses))
        
        # Use the string-based XSLT transformation function
        result = xslt_transform_string(Path(xslt_file), input_xml, 
            xslt_params={
                "additional-postamble": licenses_tex,
            })
        
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
