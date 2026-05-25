#!/usr/bin/env python3
"""
JLPTEI to LuaLaTeX exporter (reledmac/reledpar pipeline).

This module is the Python driver for the reledmac.xslt stylesheet. It collects
license, credit, and source bibliographic metadata from all referenced source
files, then drives the XSLT transformation that produces a LuaLaTeX document
ready for ``latexmk -lualatex``.

Typography settings (font, paper, layout, fontsize) are pulled from the same
``settings.yaml`` the compiler uses; only the ``typography`` section is read
here. When no settings file is supplied, sensible defaults from
``TypographyConfig`` are used.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from lxml import etree
from pydantic import BaseModel

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from opensiddur.common.xslt import xslt_transform_string  # noqa: E402
from opensiddur.common.constants import PROJECT_DIRECTORY  # noqa: E402
from opensiddur.exporter.settings import TypographyConfig  # noqa: E402

XSLT_FILE = Path(__file__).parent / "reledmac.xslt"

# Default project root for resolving p:project/p:file_name references in compiled XML.
projects_source_root = PROJECT_DIRECTORY


class LicenseRecord(BaseModel):
    """Record of the license for a given file."""
    url: str  # License URL is required
    name: str


class CreditRecord(BaseModel):
    """Record of the credit for a given file."""
    role: str  # Role is required (e.g., "aut", "edt")
    resp_text: str
    ref: str  # Reference URI is required
    name_text: str
    namespace: str  # where the contributor did their work
    contributor: str  # contributor name at the source


def extract_licenses(
    xml_file_paths: list[Path],
    project_directory: Path | None = None,
) -> dict[Path, LicenseRecord]:
    """Extract license URLs and names from a list of JLPTEI XML files."""
    if project_directory is None:
        project_directory = projects_source_root
    project_directory = project_directory.resolve()
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    results: dict[Path, LicenseRecord] = {}

    for file_path in xml_file_paths:
        try:
            try:
                relative_path = file_path.absolute().relative_to(project_directory)
            except ValueError:
                print(
                    f"Warning: {file_path} is not a subdirectory of {project_directory}",
                    file=sys.stderr,
                )
                continue
            tree = etree.parse(file_path)
            root = tree.getroot()
            for licence in root.findall(".//tei:licence", ns):
                url = licence.attrib.get("target")
                name = (licence.text or "").strip()
                if url:
                    results[relative_path] = LicenseRecord(url=url, name=name)
                else:
                    print(
                        f"Error: No license URL found for {relative_path}",
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"Error: {file_path}: {e}", file=sys.stderr)

    return results


def group_licenses(licenses: dict[Path, LicenseRecord]) -> list[LicenseRecord]:
    """Group licenses by URL (deduplicated)."""
    seen: set[str] = set()
    grouped: list[LicenseRecord] = []
    for license_record in licenses.values():
        if license_record.url not in seen:
            seen.add(license_record.url)
            grouped.append(license_record)
    return grouped


def licenses_to_tex(licenses: list[LicenseRecord]) -> str:
    """Convert a list of LicenseRecord objects into a LaTeX section."""
    items = "\n".join(
        f"\\item {license.name} (\\url{{{license.url}}})" for license in licenses
    )
    return (
        "\\section*{Legal}\n"
        "This document includes copyrighted texts licensed under the following licenses.\n"
        "The full text of the licenses can be found at the given URLs:\n\n"
        "\\begin{itemize}\n"
        f"{items}\n"
        "\\end{itemize}\n"
    )


def extract_credits(xml_file_paths: list[Path]) -> dict[Path, list[CreditRecord]]:
    """Extract credits (respStmt entries) from a list of JLPTEI XML files."""
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    results: dict[Path, list[CreditRecord]] = {}

    for file_path in xml_file_paths:
        credits: list[CreditRecord] = []
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            for resp_stmt in root.findall(".//tei:respStmt", ns):
                resp = resp_stmt.find("tei:resp", ns)
                name = resp_stmt.find("tei:name", ns)

                if resp is None or name is None:
                    continue

                role = resp.attrib.get("key")
                ref = name.attrib.get("ref")

                if not role or not ref:
                    continue

                # Parse namespace and contributor from ref (urn:x-opensiddur:NAMESPACE/CONTRIBUTOR)
                tail = ref.split(":")[-1]
                if "/" not in tail:
                    continue
                namespace, contributor = tail.split("/", 1)

                credits.append(
                    CreditRecord(
                        role=role,
                        resp_text=(resp.text or "").strip(),
                        ref=ref,
                        name_text=(name.text or "").strip(),
                        namespace=namespace,
                        contributor=contributor,
                    )
                )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        results[file_path] = credits

    return results


def group_credits(
    credits: dict[Path, list[CreditRecord]],
) -> dict[str, dict[str, list[CreditRecord]]]:
    """Group credits by role -> namespace -> [CreditRecord], deduplicated by (role, ref)."""
    seen: set[tuple[str, str]] = set()
    grouped: dict[str, dict[str, list[CreditRecord]]] = {}
    for credit_list in credits.values():
        for credit in credit_list:
            key = (credit.role, credit.ref)
            if key in seen:
                continue
            seen.add(key)
            grouped.setdefault(credit.role, {}).setdefault(credit.namespace, []).append(credit)
    return grouped


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
    """Convert grouped credits into a LaTeX appendix section."""
    if not credits:
        return ""
    tex = "\\section*{Contributor credits}\n"
    for role, namespace_dict in credits.items():
        total = sum(len(c) for c in namespace_dict.values())
        role_name = contributor_keys_to_roles.get(role, role) + ("s" if total > 1 else "")
        tex += f"\\subsection*{{{role_name}}}\n"
        for namespace, namespace_credits in namespace_dict.items():
            sorted_credits = sorted(namespace_credits, key=lambda x: x.contributor)
            tex += f"\\subsubsection*{{From {namespace}}}\n"
            tex += "\\begin{itemize}\n"
            for credit in sorted_credits:
                tex += f"\\item {credit.name_text}\n"
            tex += "\\end{itemize}\n"
    return tex


def get_project_index(file_path: Path) -> Path:
    """Get the project index file for a given file path."""
    return file_path.parent / "index.xml"


def extract_sources(xml_file_paths: list[Path]) -> tuple[str, str]:
    """Extract bibliographic sources from index.xml files.

    Returns a (preamble_tex, postamble_tex) tuple. The preamble carries the
    embedded ``filecontents*`` block + ``\\addbibresource``, the postamble
    carries ``\\printbibliography``. Both are empty when there is no
    ``listBibl`` content.
    """
    index_files = set(get_project_index(fp) for fp in xml_file_paths)
    bibtex_records: list[str] = []
    seen: set[str] = set()
    for index_xml in index_files:
        try:
            index_xml_text = index_xml.read_text(encoding="utf-8")
            bib_xslt_path = Path(__file__).parent / "bibtex.xslt"
            bibtex_str = xslt_transform_string(bib_xslt_path, index_xml_text).strip()
            if bibtex_str and bibtex_str not in seen:
                seen.add(bibtex_str)
                bibtex_records.append(bibtex_str)
        except Exception as e:
            print(f"Could not extract bibtex from {index_xml}: {e}", file=sys.stderr)
            continue

    bibtex_blob = "\n\n".join(bibtex_records)
    if not bibtex_blob:
        return "", ""

    preamble_tex = (
        "\\begin{filecontents*}{job.bib}\n"
        f"{bibtex_blob}\n"
        "\\end{filecontents*}\n"
        "\\addbibresource{job.bib}\n"
    )
    postamble_tex = (
        "\n\\section*{Sources}\n"
        "\\begingroup\n"
        "\\nocite{*}\n"
        "\\printbibliography[heading=none]\n"
        "\\endgroup\n"
    )
    return preamble_tex, postamble_tex


def get_file_references(
    input_file: Path, project_directory: Path | None = None
) -> list[Path]:
    """Get all source file references from a compiled JLPTEI XML file.

    Includes the file itself, all transcluded files, and the ``index.xml``
    of every referenced project.
    """
    if project_directory is None:
        project_directory = projects_source_root
    project_directory = project_directory.resolve()
    ns = {
        "tei": "http://www.tei-c.org/ns/1.0",
        "p": "http://jewishliturgy.org/ns/processing",
    }
    tree = etree.parse(input_file)
    root = tree.getroot()
    elements_with_references = root.xpath(
        "(self::*|.//*) [@p:project and @p:file_name]", namespaces=ns
    )

    p_project = "{http://jewishliturgy.org/ns/processing}project"
    p_file_name = "{http://jewishliturgy.org/ns/processing}file_name"

    return list(
        set(
            [
                project_directory / element.attrib[p_project] / element.attrib[p_file_name]
                for element in elements_with_references
            ]
            + [
                project_directory / element.attrib[p_project] / "index.xml"
                for element in elements_with_references
            ]
        )
    )


def load_typography(settings_file: Optional[Path]) -> TypographyConfig:
    """Load only the ``typography`` section of a settings.yaml.

    Returns sensible defaults when the file is missing or has no typography
    section. We deliberately validate only the typography section and not
    the full SettingsYaml — the compiler stage already does that — so that
    the PDF stage can run even when the settings file references projects
    not present in this checkout.
    """
    if settings_file is None:
        return TypographyConfig()
    try:
        import yaml

        with open(settings_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return TypographyConfig.model_validate(data.get("typography", {}) or {})
    except Exception as e:
        print(
            f"Warning: could not load typography from {settings_file}: {e}; "
            "using defaults",
            file=sys.stderr,
        )
        return TypographyConfig()


def transform_xml_to_tex(
    input_file,
    xslt_file: Path = XSLT_FILE,
    output_file: Optional[str] = None,
    settings_file: Optional[Path] = None,
    typography: Optional[TypographyConfig] = None,
    project_directory: Path | None = None,
) -> str:
    """Transform a compiled JLPTEI XML file into a LuaLaTeX document.

    Args:
        input_file: Path to the compiled JLPTEI XML file.
        xslt_file: Path to ``reledmac.xslt`` (overridable for tests).
        output_file: If given, write to this path; otherwise return the string.
        settings_file: Optional path to a settings.yaml to read typography from.
        typography: Pre-loaded TypographyConfig (takes precedence over settings_file).
        project_directory: Base directory containing project subdirectories.

    Returns:
        The transformed LaTeX content as a string.
    """
    try:
        with open(input_file, "r", encoding="utf-8") as input_fd:
            input_xml = input_fd.read()

        if project_directory is None:
            project_directory = projects_source_root
        project_directory = project_directory.resolve()
        file_references = get_file_references(input_file, project_directory)

        licenses = extract_licenses(file_references, project_directory)
        licenses_tex = licenses_to_tex(group_licenses(licenses))
        credits = extract_credits(file_references)
        credits_tex = credits_to_tex(group_credits(credits))
        sources_preamble_tex, sources_postamble_tex = extract_sources(file_references)

        if typography is None:
            typography = load_typography(settings_file)

        result = xslt_transform_string(
            Path(xslt_file),
            input_xml,
            xslt_params={
                "additional-preamble": sources_preamble_tex,
                "additional-postamble": (
                    "\\par\\bigskip\n"
                    "\\hrule\\bigskip\n"
                    "\\section*{Metadata}\n"
                    + licenses_tex
                    + "\n"
                    + credits_tex
                    + "\n"
                    + sources_postamble_tex
                ),
                "hebrew-font": typography.hebrew_font,
                "latin-font": typography.latin_font,
                "layout": typography.layout.value,
                    "paper": typography.paper.value,
                "fontsize": typography.fontsize,
            },
        )

        if output_file:
            with open(output_file, "w", encoding="utf-8") as output_fd:
                output_fd.write(result)
            print(f"LuaLaTeX output written to: {output_file}", file=sys.stderr)
        else:
            sys.stdout.write(result)

        return result

    except Exception as e:
        print(f"Transformation error: {e}", file=sys.stderr)
        sys.exit(1)


def main():  # pragma: no cover
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Convert compiled JLPTEI XML files to LuaLaTeX (reledmac/reledpar)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml
  %(prog)s input.xml -o output.tex
  %(prog)s input.xml -s settings.yaml -o output.tex
        """,
    )

    parser.add_argument("input_file", help="Path to the input compiled JLPTEI XML file")
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="Path to the output .tex file (default: output to stdout)",
    )
    parser.add_argument(
        "-s",
        "--settings",
        dest="settings_file",
        type=Path,
        default=None,
        help=(
            "Path to a settings.yaml whose `typography` section drives "
            "fonts, layout, paper, and font size. Defaults are used when omitted."
        ),
    )
    parser.add_argument(
        "--xslt",
        dest="xslt_file",
        default=str(XSLT_FILE),
        help="Path to the XSLT file (default: reledmac.xslt next to this script)",
    )
    parser.add_argument(
        "--project-directory",
        type=Path,
        default=PROJECT_DIRECTORY,
        help="Base directory containing project subdirectories (default: <repo>/project).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.xslt_file):
        print(f"Error: XSLT file '{args.xslt_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    transform_xml_to_tex(
        args.input_file,
        xslt_file=Path(args.xslt_file),
        output_file=args.output_file,
        settings_file=args.settings_file,
        project_directory=args.project_directory,
    )


if __name__ == "__main__":
    main()
