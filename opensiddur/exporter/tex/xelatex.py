#!/usr/bin/env python3
"""
JLPTEI to XeLaTeX Exporter

This script converts JLPTEI XML files to XeLaTeX format using XSLT transformation.
"""

import sys
import argparse
import os
from typing import Optional
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
    url: str  # License URL is required
    name: str

class CreditRecord(BaseModel):
    """ Record of the credit for a given file. """
    role: str  # Role is required (e.g., "aut", "edt")
    resp_text: str
    ref: str  # Reference URI is required
    name_text: str
    namespace: str  # where the contributor did their work
    contributor: str  # contirbutor name at the source

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
            try:
                relative_path = file_path.absolute().relative_to(projects_source_root)
            except ValueError:
                print(f"Warning: {file_path} is not a subdirectory of {projects_source_root}", file=sys.stderr)
                continue
            tree = etree.parse(file_path)
            root = tree.getroot()
            # Find all <tei:licence> elements anywhere in the document
            for licence in root.findall(".//tei:licence", ns):
                # Try to get the target attribute (URL)
                url = licence.attrib.get("target")
                # The text content is the license name
                name = (licence.text or "").strip()
                if url:  # License must have a URL
                    results[relative_path] = LicenseRecord(url=url, name=name)
                else:
                    print(f"Error: No license URL found for {relative_path}", file=sys.stderr)
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
    tex = f"""\\chapter{{Legal}}
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
                
                # Skip if required elements are missing
                if resp is None or name is None:
                    continue
                
                role = resp.attrib.get("key")
                ref = name.attrib.get("ref")
                
                # Skip if required attributes are missing
                if not role or not ref:
                    continue
                
                credit = {
                    "role": role,
                    "resp_text": (resp.text or "").strip(),
                    "ref": ref,
                    "name_text": (name.text or "").strip(),
                }
                
                # Parse namespace and contributor from ref
                namespace, contributor = ref.split(":")[-1].split("/")
                credit["namespace"] = namespace
                credit["contributor"] = contributor
                
                credits.append(CreditRecord.model_validate(credit))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            pass
        results[file_path] = credits

    return results


def group_credits(credits: dict[Path, list[dict]]) -> dict[str, dict[str, list[CreditRecord]]]:
    """
    Group credits by role -> namespace -> contributor.
    Each credit record will appear once per role.
    """
    credit_refs = set() # avoid duplicates of (role, ref)
    grouped_credits = {}
    for _, credit_list in credits.items():
        for credit in credit_list:
            if (credit.role, credit.ref) not in credit_refs:
                role = credit.role
                ref = credit.ref
                namespace = credit.namespace
                credit_refs.add((role, ref))
                if role not in grouped_credits:
                    grouped_credits[role] = {}
                if namespace not in grouped_credits[role]:
                    grouped_credits[role][namespace] = []
                grouped_credits[role][namespace].append(credit)
            
    return grouped_credits

contributor_keys_to_roles = {
    "ann": "Annotator",
    "aut": "Author",
    "edt": "Editor",
    "fac": "Facsimilist",
    "fnd": "Funder",
    "mrk": "Markup editor",
    "pfr": "Proofreader",
    "spn": "Sponsor",
    "trl": "Translator",
    "trc": "Transcriptionist",
}

def credits_to_tex(credits: dict[str, dict[str, list[CreditRecord]]]) -> str:
    """
    Convert role -> namespace -> list of CreditRecord objects to a string of LaTeX code.
    """
    tex = f"""\\chapter{{Contributor credits}}\n"""
    for role, namespace_dict in credits.items():
        total_credits = sum(len(credits) for credits in namespace_dict.values())
        role_name = contributor_keys_to_roles[role] + ("s" if total_credits > 1 else "")
        tex += f"""\\section{{{role_name}}}\n"""
        for namespace, credits in namespace_dict.items():
            sorted_credits = sorted(credits, key=lambda x: x.contributor)
            tex += f"""\\subsection{{From {namespace}}}\n"""
            tex += f"""\\begin{{itemize}}\n"""
            for credit in sorted_credits:
                tex += f"""\\item {credit.name_text}\n"""
            tex += f"""\\end{{itemize}}\n"""
    return tex

def get_project_index(file_path: Path) -> Path:
    """
    Get the project index file for a given file path.
    """
    return file_path.parent / "index.xml"

def extract_sources(xml_file_paths: list[Path]) -> tuple[str, str]:
    """
    Extract sources from a list of JLPTEI XML files.
    Returns:
        tuple: (preamble_tex, postamble_tex) for the bibliography
    """
    index_files = set(get_project_index(fp) for fp in xml_file_paths)
    bibtex_records_all = []
    unique_bibtex_records = set()
    for index_xml in index_files:
        try:
            # Convert the index xml to .bib using bibtex.xslt
            index_xml_text = index_xml.read_text(encoding="utf-8")
            bib_xslt_path = Path(__file__).parent / "bibtex.xslt"
            bibtex_str = xslt_transform_string(bib_xslt_path, index_xml_text)
            bibtex_str = bibtex_str.strip()
            if bibtex_str and bibtex_str not in unique_bibtex_records:
                unique_bibtex_records.add(bibtex_str)
                bibtex_records_all.append(bibtex_str)
        except Exception as e:
            print(f"Could not extract bibtex from {index_xml}: {e}", file=sys.stderr)
            continue
    bibtex_blob = "\n\n".join(bibtex_records_all)
    preamble_tex = ""
    postamble_tex = ""
    if bibtex_blob:
        preamble_tex = f"""\\begin{{filecontents*}}{{job.bib}}
{bibtex_blob}
\\end{{filecontents*}}
\\addbibresource{{job.bib}}
"""
        postamble_tex = f"""
\\begingroup
\\renewcommand{{\\refname}}{{Sources}}
\\nocite{{*}}
\\printbibliography
\\endgroup
"""
    return preamble_tex, postamble_tex


def get_file_references(input_file: Path, project_directory: Path = projects_source_root) -> list[Path]:
    """
    Get the file references from a compiled JLPTEI XML file.
    The file references include 
    the file itself, all files that are transcluded by the file, and the index file for all projects.
    Args:
        input_file (Path): Path to the input compiled JLPTEI XML file.
        project_directory (Path): Path to the project directory.
    Returns:
        list[Path]: List of paths to the file references.
    """
    ns = {
        "tei": "http://www.tei-c.org/ns/1.0",
        "p": "http://jewishliturgy.org/ns/processing",
    }
    tree = etree.parse(input_file)
    root = tree.getroot()
    # Use xpath() instead of findall() for complex predicates
    # Include root element (self) and all descendants
    elements_with_references = root.xpath("(self::*|.//*) [@p:project and @p:file_name]", namespaces=ns)
    
    # Use Clark notation for attribute access
    p_project = "{http://jewishliturgy.org/ns/processing}project"
    p_file_name = "{http://jewishliturgy.org/ns/processing}file_name"
    
    return list(set([
        project_directory / element.attrib[p_project] / element.attrib[p_file_name]
        for element in elements_with_references
    ] + [
        project_directory / element.attrib[p_project] / "index.xml"
        for element in elements_with_references
    ]))

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
        
        file_references = [Path(input_file)] + get_file_references(input_file)

        licenses = extract_licenses(file_references)
        licenses_tex = licenses_to_tex(group_licenses(licenses))
        credits = extract_credits(file_references)
        credits_tex = credits_to_tex(group_credits(credits))
        sources_preamble_tex, sources_postamble_tex = extract_sources(file_references)
        # Use the string-based XSLT transformation function
        result = xslt_transform_string(Path(xslt_file), input_xml, 
            xslt_params={
                "additional-preamble": sources_preamble_tex,
                "additional-postamble": (
                    "\\part{Metadata}\n" + 
                    licenses_tex + "\n" + 
                    credits_tex + "\n" + 
                    sources_postamble_tex
                ),
            })
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as output_fd:
                output_fd.write(result)
            print(f"XeLaTeX output written to: {output_file}", file=sys.stderr)
        else:
            sys.stdout.write(result)
        
        return result
        
    except Exception as e:
        print(f"Transformation error: {e}", file=sys.stderr)
        sys.exit(1)


def main():  # pragma: no cover
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
