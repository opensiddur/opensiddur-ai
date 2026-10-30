"""Writing JLPTEI projects: the document skeleton, validate-then-write, and pruning.

Shared by importers that build their TEI as strings. Every file is validated against the
RelaxNG and Schematron before it is written and again on disk, so a project directory never
holds an invalid file.
"""

from __future__ import annotations

from pathlib import Path

from opensiddur.importer.util.prettify import prettify_xml
from opensiddur.importer.util.validation import validate

#: The ``xml:id`` of the ``tei:bibl`` in a project's index that every document cites as its
#: source. See ``schema/JLPTEI-3.md``.
PROJECT_SOURCE_BIBL_ID = "project_source_bibl"


def tei_document(
    header_xml: str,
    body_xml: str,
    *,
    lang: str,
    front_xml: str = "",
    standoff_xml: str = "",
) -> str:
    front = f"{front_xml}\n" if front_xml else ""
    standoff = f"\n{standoff_xml}" if standoff_xml else ""
    return f"""<tei:TEI xml:lang="{lang}" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
{header_xml}
<tei:text>
{front}{body_xml}
</tei:text>{standoff}
</tei:TEI>"""


def xml_id_ref(project_id: str, file_stem: str, fragment: str) -> str:
    """A project-root-relative pointer to one ``xml:id`` in one file: ``/{project}/{file}#{id}``.

    Use this, not a ``urn:x-opensiddur:`` URN, when the thing referenced is a single, constant
    position in a single file with no notion of "which variant" — e.g. the one specific
    ``tei:bibl`` entry a project's documents cite as their source, which will never be swapped
    for an alternate source. URNs are for the opposite case: referencing *a text* that may have
    several variant representations, where ``@project`` selects one of those possibilities.
    """
    return f"/{project_id}/{file_stem}#{fragment}"


def validate_and_write(
    tei_content: str, file_name: str, project_dir: Path, *, keep_blank_text: bool = False
) -> Path:
    """Validate, write, and validate again on disk. See :func:`prettify_xml` for
    ``keep_blank_text``."""
    out_path = project_dir / f"{file_name}.xml"
    pretty_xml = prettify_xml(tei_content, remove_xml_declaration=True, keep_blank_text=keep_blank_text)
    is_valid, errors = validate(pretty_xml)
    if not is_valid:
        raise RuntimeError(f"JLPTEI validation failed for {file_name}: {errors}")
    out_path.write_text(pretty_xml, encoding="utf-8")
    is_valid_on_disk, disk_errors = validate(out_path)
    if not is_valid_on_disk:
        raise RuntimeError(f"JLPTEI validation failed after write for {file_name}: {disk_errors}")
    return out_path


def validate_project_directory(project_dir: Path) -> None:
    """Validate every XML file in a project directory against RelaxNG and Schematron."""
    xml_files = sorted(project_dir.glob("*.xml"))
    if not xml_files:
        raise RuntimeError(f"No XML files found in {project_dir}")

    failures: dict[str, list[str]] = {}
    for path in xml_files:
        is_valid, errors = validate(path)
        if not is_valid:
            failures[path.name] = errors

    if failures:
        summary = "; ".join(
            f"{name}: {errs[0]}" for name, errs in sorted(failures.items())
        )
        raise RuntimeError(
            f"JLPTEI validation failed for {len(failures)} file(s) in {project_dir.name}: {summary}"
        )


def prune_stale_files(project_dir: Path, written: set[str]) -> list[Path]:
    """Delete generated files that this conversion no longer produces.

    A leftover file from an earlier run is not harmless: it still validates, still carries the
    URNs it was written with, and so quietly duplicates them across the project.
    """
    stale = [path for path in sorted(project_dir.glob("*.xml")) if path.stem not in written]
    for path in stale:
        path.unlink()
    return stale
