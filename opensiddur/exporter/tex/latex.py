#!/usr/bin/env python3
"""
JLPTEI to LuaLaTeX exporter (reledmac/reledpar pipeline).

This module is the Python driver for the reledmac.xslt stylesheet. It collects
license, credit, and source bibliographic metadata from all referenced source
files, then drives the XSLT transformation that produces a LuaLaTeX document
ready for ``lualatex`` (``pdf/pdf.py`` runs the passes).

Typography settings (font, paper, layout, fontsize, running heads) are pulled from the same
``settings.yaml`` the compiler uses; only the ``typography`` section is read
here. When no settings file is supplied, sensible defaults from
``TypographyConfig`` are used.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

from lxml import etree

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from opensiddur.common.xslt import xslt_transform_string  # noqa: E402
from opensiddur.common.constants import PROJECT_DIRECTORY  # noqa: E402
from opensiddur.exporter.typography import TypographyConfig  # noqa: E402
from opensiddur.exporter.tex.running_heads import (  # noqa: E402
    build_page_style_tex,
    escape_with_hebrew_runs,
)
from opensiddur.exporter.conditional_markers import mark_silent_scopes  # noqa: E402
from opensiddur.exporter.page_references import resolve_page_references  # noqa: E402
from opensiddur.exporter.tex.typography_tex import (  # noqa: E402
    build_typography_preamble,
    documentclass_options,
)

from opensiddur.exporter.metadata import (  # noqa: E402
    CreditRecord,
    LicenseRecord,
    role_name as _role_name,
    role_order as _role_order,
    extract_credits,
    group_credits,
    group_licenses,
    load_typography,
)
from opensiddur.exporter import metadata  # noqa: E402

XSLT_FILE = Path(__file__).parent / "reledmac.xslt"

# Default project root for resolving p:project/p:file_name references in compiled XML.
projects_source_root = PROJECT_DIRECTORY


def extract_licenses(
    xml_file_paths: list[Path],
    project_directory: Path | None = None,
) -> dict[Path, LicenseRecord]:
    """metadata.extract_licenses, relative to this stage's project root by default."""
    return metadata.extract_licenses(xml_file_paths, project_directory or projects_source_root)


def licenses_to_tex(licenses: list[LicenseRecord]) -> str:
    """Convert a list of LicenseRecord objects into a LaTeX section."""
    if not licenses:
        # An itemize with no items is a LaTeX error, and a Legal section listing nothing
        # would be misleading anyway. Matches credits_to_tex, which already guards.
        return ""
    # A licence's name is the source's own text, so it is escaped like any other; the
    # URL is not, because \url reads its argument verbatim.
    items = "\n".join(
        f"\\item {escape_with_hebrew_runs(license.name)} (\\url{{{license.url}}})"
        for license in licenses
    )
    return (
        "\\section*{Legal}\n"
        "This document includes copyrighted texts licensed under the following licenses.\n"
        "The full text of the licenses can be found at the given URLs:\n\n"
        "\\begin{itemize}\n"
        f"{items}\n"
        "\\end{itemize}\n"
    )


def credits_to_tex(credits: dict[str, dict[str, list[CreditRecord]]]) -> str:
    """Convert grouped credits into a LaTeX appendix section."""
    if not credits:
        return ""
    # Sorted, because the file order these were gathered in is not meaningful and a
    # credits list that reshuffles between two builds of the same document reads as though
    # something changed.
    tex = "\\section*{Contributor credits}\n"
    for role in sorted(credits, key=_role_order):
        namespace_dict = credits[role]
        total = sum(len(c) for c in namespace_dict.values())
        role_name = _role_name(role, namespace_dict) + ("s" if total > 1 else "")
        tex += f"\\subsection*{{{escape_with_hebrew_runs(role_name)}}}\n"
        for namespace in sorted(namespace_dict):
            sorted_credits = sorted(namespace_dict[namespace], key=lambda x: x.contributor)
            # A credit with no namespace is one whose reference could not be read. It is
            # still a person, so it is listed -- just under no heading claiming to know
            # where their name is meaningful.
            if namespace:
                tex += f"\\subsubsection*{{From {escape_with_hebrew_runs(namespace)}}}\n"
            tex += "\\begin{itemize}\n"
            for credit in sorted_credits:
                tex += f"\\item {escape_with_hebrew_runs(credit.name_text)}\n"
            tex += "\\end{itemize}\n"
    return tex


def get_project_index(file_path: Path) -> Path:
    """Get the project index file for a given file path."""
    return file_path.parent / "index.xml"


_CITE_KEY = re.compile(r"@\w+\{([^,]*),")
_ADDENDUM = re.compile(r"^  addendum = \{.*\},\n", re.M)


def _with_key(entry: str, key_match: re.Match, key: str) -> str:
    """``entry`` with the cite key ``key_match`` found in it replaced by ``key``."""
    return entry[: key_match.start(1)] + key + entry[key_match.end(1):]


def _without_addendum(entry: str) -> str:
    """A bibtex entry without its ``addendum`` line: the work it cites, not the remark."""
    return _ADDENDUM.sub("", entry + "\n").strip()


def extract_sources(xml_file_paths: list[Path]) -> tuple[str, str]:
    """Extract bibliographic sources from index.xml files.

    Returns a (preamble_tex, postamble_tex) tuple. The preamble carries the
    embedded ``filecontents*`` block + ``\\addbibresource``, the postamble
    carries ``\\printbibliography``. Both are empty when there is no
    ``listBibl`` content.
    """
    index_files = sorted(set(get_project_index(fp) for fp in xml_file_paths))
    bibtex_records: list[str] = []
    # Each listed entry with its key blanked and its addendum dropped: the work it cites.
    work_by_key: dict[str, str] = {}
    for index_xml in index_files:
        try:
            index_xml_text = index_xml.read_text(encoding="utf-8")
            bib_xslt_path = Path(__file__).parent / "bibtex.xslt"
            bibtex_str = xslt_transform_string(bib_xslt_path, index_xml_text).strip()
        except Exception as e:
            print(f"Could not extract bibtex from {index_xml}: {e}", file=sys.stderr)
            continue
        for entry in filter(None, (e.strip() for e in bibtex_str.split("\n\n"))):
            key_match = _CITE_KEY.match(entry)
            if key_match is None:
                print(f"Warning: {index_xml}: a source with no cite key; left out", file=sys.stderr)
                continue
            key = key_match.group(1)
            # Two projects of the same book cite it identically but for a note, so the
            # same key arrives twice; the book is listed once. A different work that
            # happens to share an author and a year is a source in its own right, and
            # BibTeX keeps only the first entry with a key, so it is given a key of its
            # own — unless an earlier rename already gave this same work one.
            work = _without_addendum(_with_key(entry, key_match, ""))
            candidate, suffix = key, 1
            while candidate in work_by_key:
                if work_by_key[candidate] == work:
                    break
                suffix += 1
                candidate = f"{key}-{suffix}"
            else:
                renamed = _with_key(entry, key_match, candidate)
                work_by_key[candidate] = work
                bibtex_records.append(renamed)

    bibtex_blob = "\n\n".join(bibtex_records)
    if not bibtex_blob:
        return "", ""

    # Named after the job, so two documents built in one directory do not share it, and
    # overwritten, because filecontents otherwise keeps a .bib it finds already there —
    # a reused build directory would print the previous build's sources.
    preamble_tex = (
        "\\begin{filecontents*}[overwrite]{\\jobname.bib}\n"
        f"{bibtex_blob}\n"
        "\\end{filecontents*}\n"
        "\\addbibresource{\\jobname.bib}\n"
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
    """metadata.get_file_references, relative to this stage's project root by default."""
    return metadata.get_file_references(input_file, project_directory or projects_source_root)


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

    Raises:
        pydantic.ValidationError: if the settings file's typography section is
            invalid.
        Exception: whatever the transformation raised; the command-line entry
            point reports it and exits non-zero, a caller decides for itself.
    """
    if typography is None:
        typography = load_typography(settings_file)

    if project_directory is None:
        project_directory = projects_source_root
    project_directory = project_directory.resolve()
    file_references = get_file_references(input_file, project_directory)

    licenses = extract_licenses(file_references, project_directory)
    licenses_tex = licenses_to_tex(group_licenses(licenses))
    # From the compiled document, not from the sources it was built out of: the
    # compiler gathers every contributing document's credits into it, so the file
    # printed from is the file that says who made it.
    credits = extract_credits([input_file])
    credits_tex = credits_to_tex(group_credits(credits))
    sources_preamble_tex, sources_postamble_tex = extract_sources(file_references)

    # Running-head slots that declare no language of their own follow the
    # document's, so their direction is right without being restated.
    parsed = etree.parse(input_file)
    root = parsed.getroot()
    resolve_page_references(root)
    # Whether a scope prints delimiters is decided here, on the whole document: the
    # stylesheet meets a scope's two markers in different streams, and in copies.
    mark_silent_scopes(root)
    input_xml = etree.tostring(root, encoding="unicode")
    root_language = root.get("{http://www.w3.org/XML/1998/namespace}lang")
    page_style_tex = build_page_style_tex(
        typography.page_header, typography.page_footer, root_language
    )
    # Several reledpar declarations do not exist unless the package is
    # loaded, and the stylesheet loads it only for a document with two
    # aligned streams. The typography block has to know which this is.
    has_parallel = (
        root.find(".//{http://jewishliturgy.org/ns/processing}parallel") is not None
    )
    typography_tex = build_typography_preamble(typography, has_parallel)

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
            "documentclass-options": documentclass_options(typography),
            "typography-preamble": typography_tex,
            "layout": typography.parallel.layout.value,
            "notes-placement": typography.notes.placement.value,
            "notes-mark": typography.notes.mark.value,
            "table-of-contents": typography.table_of_contents.enabled,
            "table-of-contents-depth": typography.table_of_contents.depth,
            "bookmarks-from": typography.bookmarks.from_.value,
            "headings-from": typography.headings.from_.value,
            "instructions-from": typography.instructions.from_.value,
            "page-style-preamble": page_style_tex,
        },
    )

    if output_file:
        with open(output_file, "w", encoding="utf-8") as output_fd:
            output_fd.write(result)
        print(f"LuaLaTeX output written to: {output_file}", file=sys.stderr)
    else:
        sys.stdout.write(result)

    return result


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
        help="Base directory containing project subdirectories (default: <repo>/opensiddur-projects/project).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.xslt_file):
        print(f"Error: XSLT file '{args.xslt_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    try:
        transform_xml_to_tex(
            args.input_file,
            xslt_file=Path(args.xslt_file),
            output_file=args.output_file,
            settings_file=args.settings_file,
            project_directory=args.project_directory,
        )
    except Exception as e:
        # The whole message: for a typography error it says which setting and why.
        print(f"Transformation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
