#!/usr/bin/env python3
"""
JLPTEI to LuaLaTeX exporter (reledmac/reledpar pipeline).

This module is the Python driver for the reledmac.xslt stylesheet. It collects
license, credit, and source bibliographic metadata from all referenced source
files, then drives the XSLT transformation that produces a LuaLaTeX document
ready for ``latexmk -lualatex``.

Typography settings (font, paper, layout, fontsize, running heads) are pulled from the same
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
from opensiddur.exporter.typography import TypographyConfig  # noqa: E402
from opensiddur.exporter.tex.running_heads import build_page_style_tex  # noqa: E402
from opensiddur.exporter.tex.typography_tex import (  # noqa: E402
    build_typography_preamble,
    documentclass_options,
)

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
    if not licenses:
        # An itemize with no items is a LaTeX error, and a Legal section listing nothing
        # would be misleading anyway. Matches credits_to_tex, which already guards.
        return ""
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


#: The contributor URN form: the scheme, the ``contributor`` type, then the namespace the
#: identifier is meaningful in and the identifier itself. See ``schema/JLPTEI-3.md``.
CONTRIBUTOR_URN = "urn:x-opensiddur:contributor:"


def _contributor_of(ref: str | None, name_text: str, file_path: Path) -> tuple[str, str]:
    """The namespace a contributor's identifier belongs to, and the identifier.

    A reference that is not a contributor URN is reported rather than guessed at. Reading
    one as a URN anyway is what printed a heading of "From " with nothing after it: the
    last colon-delimited piece of ``https://he.wikisource.org/`` is not a namespace.
    """
    if not ref:
        print(f"Warning: {file_path}: {name_text or 'a contributor'} is credited with no "
              "reference; listed without one", file=sys.stderr)
        return "", name_text
    tail = ref.removeprefix(CONTRIBUTOR_URN)
    if tail == ref or "/" not in tail:
        print(f"Warning: {file_path}: {ref!r} is not a contributor URN "
              f"({CONTRIBUTOR_URN}<namespace>/<identifier>); listed without a namespace",
              file=sys.stderr)
        return "", name_text or ref
    namespace, contributor = tail.split("/", 1)
    return namespace, contributor


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
                # itertext, not .text: a name may carry markup, and .text stops at the
                # first child element.
                name_text = "".join(name.itertext()).strip()

                if not role:
                    print(f"Warning: {file_path}: a credit for {name_text or 'someone'} "
                          "has no resp/@key saying what they did; not listed",
                          file=sys.stderr)
                    continue
                # A credit with no reference is not silently dropped: a respStmt records
                # who digitised a text, and one without a reference is malformed data
                # rather than a person to leave out. It is listed under no namespace.
                namespace, contributor = _contributor_of(ref, name_text, file_path)

                credits.append(
                    CreditRecord(
                        role=role,
                        resp_text="".join(resp.itertext()).strip(),
                        ref=ref or name_text,
                        name_text=name_text,
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
    # Sorted, because the file order these were gathered in is not meaningful and a
    # credits list that reshuffles between two builds of the same document reads as though
    # something changed.
    tex = "\\section*{Contributor credits}\n"
    for role in sorted(credits, key=_role_order):
        namespace_dict = credits[role]
        total = sum(len(c) for c in namespace_dict.values())
        role_name = _role_name(role, namespace_dict) + ("s" if total > 1 else "")
        tex += f"\\subsection*{{{role_name}}}\n"
        for namespace in sorted(namespace_dict):
            sorted_credits = sorted(namespace_dict[namespace], key=lambda x: x.contributor)
            # A credit with no namespace is one whose reference could not be read. It is
            # still a person, so it is listed -- just under no heading claiming to know
            # where their name is meaningful.
            if namespace:
                tex += f"\\subsubsection*{{From {namespace}}}\n"
            tex += "\\begin{itemize}\n"
            for credit in sorted_credits:
                tex += f"\\item {credit.name_text}\n"
            tex += "\\end{itemize}\n"
    return tex


def _role_order(role: str) -> tuple[int, str]:
    """Roles in the order the schema lists them, then anything unrecognised."""
    keys = list(contributor_keys_to_roles)
    return (keys.index(role) if role in keys else len(keys), role)


def _role_name(role: str, namespace_dict: dict[str, list[CreditRecord]]) -> str:
    """What to call this kind of contribution.

    A recognised MARC key has a name of its own. For anything else the document's own
    ``tei:resp`` wording says what the person did, and is a better heading than the raw
    three-letter code the reader would otherwise be shown.
    """
    if role in contributor_keys_to_roles:
        return contributor_keys_to_roles[role]
    said = [c.resp_text for group in namespace_dict.values() for c in group if c.resp_text]
    return said[0] if said else role


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

    A typography section that is present but invalid is an error, not a
    fallback: silently substituting defaults for, say, a mistyped running-head
    code would produce a PDF that is simply missing what was asked for, with
    nothing but a warning to say why. Only being unable to read or parse the
    file at all falls back to defaults.
    """
    if settings_file is None:
        return TypographyConfig()
    import yaml

    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as e:
        print(
            f"Warning: could not load typography from {settings_file}: {e}; "
            "using defaults",
            file=sys.stderr,
        )
        return TypographyConfig()
    if not isinstance(data, dict):
        return TypographyConfig()
    return TypographyConfig.model_validate(data.get("typography") or {})


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
            invalid. Deliberately outside the catch-all below, whose one-line
            report would throw away the part of the message that says which
            setting is wrong and why.
    """
    if typography is None:
        typography = load_typography(settings_file)

    try:
        with open(input_file, "r", encoding="utf-8") as input_fd:
            input_xml = input_fd.read()

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
        help="Base directory containing project subdirectories (default: <repo>/opensiddur-projects/project).",
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


if __name__ == "__main__":  # pragma: no cover
    main()
