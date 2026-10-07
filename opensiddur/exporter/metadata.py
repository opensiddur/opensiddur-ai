"""Metadata a compiled book carries about its sources, whatever it is rendered into.

The licences and contributor credits of every file a compiled document drew on, and the
typography section of its settings file. Read by each output stage: the TeX/PDF stage
(tex/latex.py) and the electronic book (html/html.py).
"""

import sys
from pathlib import Path
from typing import Optional

from lxml import etree
from pydantic import BaseModel

from opensiddur.exporter.typography import TypographyConfig


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
    project_directory: Path,
) -> dict[Path, LicenseRecord]:
    """Extract license URLs and names from a list of JLPTEI XML files."""
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



def role_order(role: str) -> tuple[int, str]:
    """Roles in the order the schema lists them, then anything unrecognised."""
    keys = list(contributor_keys_to_roles)
    return (keys.index(role) if role in keys else len(keys), role)


def role_name(role: str, namespace_dict: dict[str, list[CreditRecord]]) -> str:
    """What to call this kind of contribution.

    A recognised MARC key has a name of its own. For anything else the document's own
    ``tei:resp`` wording says what the person did, and is a better heading than the raw
    three-letter code the reader would otherwise be shown.
    """
    if role in contributor_keys_to_roles:
        return contributor_keys_to_roles[role]
    said = [c.resp_text for group in namespace_dict.values() for c in group if c.resp_text]
    return said[0] if said else role



def get_file_references(input_file: Path, project_directory: Path) -> list[Path]:
    """Get all source file references from a compiled JLPTEI XML file.

    Includes the file itself, all transcluded files, and the ``index.xml``
    of every referenced project.
    """
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
