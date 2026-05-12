"""Post-conversion validation for resolvable URN references.

This validator is intentionally optional and is meant to be run after an entire
project/source has been converted and the reference DB has been populated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.exporter.refdb import INDEX_DB_FILE, ReferenceDatabase
from opensiddur.exporter.urn import UrnResolver


TEI_NS = "http://www.tei-c.org/ns/1.0"
JLPTEI_NS = "http://jewishliturgy.org/ns/jlptei/2"


@dataclass(frozen=True)
class UnresolvableUrnReference:
    project: str
    file_name: str
    element_path: str
    attribute_name: str
    urn: str


def _iter_project_xml_files(project_path: Path) -> Iterable[Path]:
    yield from sorted(project_path.glob("*.xml"))


def validate_project_urn_references(
    project: str,
    *,
    project_directory: Path = PROJECT_DIRECTORY,
    reference_db_path: Path = INDEX_DB_FILE,
    index_before_validate: bool = False,
) -> list[UnresolvableUrnReference]:
    """Validate that compilation-relevant URN references are resolvable via refdb.

    This checks URNs in:
    - tei:ptr/@target
    - tei:ref/@target
    - j:transclude/@target and j:transclude/@targetEnd
    """

    project_path = Path(project_directory) / project
    if not project_path.exists() or not project_path.is_dir():
        raise ValueError(f"Project directory does not exist: {project_path}")

    refdb = ReferenceDatabase(reference_db_path)
    try:
        if index_before_validate:
            refdb.index_project(project, project_directory=project_directory)

        resolver = UrnResolver(refdb)
        ns = {"tei": TEI_NS, "j": JLPTEI_NS}

        failures: list[UnresolvableUrnReference] = []
        for xml_file in _iter_project_xml_files(project_path):
            tree = etree.parse(str(xml_file))
            root = tree.getroot()

            # Only targets that are URNs participate in this validation.
            # Non-URN targets (e.g., local paths or URLs) are out of scope.
            ptrs = root.xpath("//tei:ptr[@target]", namespaces=ns)
            refs = root.xpath("//tei:ref[@target]", namespaces=ns)
            transcludes = root.xpath("//j:transclude[@target]", namespaces=ns)

            for el in [*ptrs, *refs]:
                urn = el.get("target")
                if not urn or not urn.startswith("urn:x-opensiddur:"):
                    continue
                if not resolver.resolve_range(urn):
                    failures.append(
                        UnresolvableUrnReference(
                            project=project,
                            file_name=xml_file.name,
                            element_path=tree.getpath(el),
                            attribute_name="target",
                            urn=urn,
                        )
                    )

            for el in transcludes:
                target = el.get("target")
                if target and target.startswith("urn:x-opensiddur:"):
                    start_candidates = resolver.resolve_range(target)
                    if not start_candidates:
                        failures.append(
                            UnresolvableUrnReference(
                                project=project,
                                file_name=xml_file.name,
                                element_path=tree.getpath(el),
                                attribute_name="target",
                                urn=target,
                            )
                        )
                        continue

                    # Prefer resolving the transclude within the current project when possible,
                    # since that's the common compilation expectation.
                    start = UrnResolver.prioritize_range(start_candidates, [project]) or start_candidates[0]

                    target_end = el.get("targetEnd")
                    if target_end and target_end.startswith("urn:x-opensiddur:"):
                        end_candidates = resolver.resolve_range(target_end)
                        if not end_candidates:
                            failures.append(
                                UnresolvableUrnReference(
                                    project=project,
                                    file_name=xml_file.name,
                                    element_path=tree.getpath(el),
                                    attribute_name="targetEnd",
                                    urn=target_end,
                                )
                            )
                            continue
                        if not UrnResolver.prioritize_range(end_candidates, [start.project]):
                            failures.append(
                                UnresolvableUrnReference(
                                    project=project,
                                    file_name=xml_file.name,
                                    element_path=tree.getpath(el),
                                    attribute_name="targetEnd",
                                    urn=target_end,
                                )
                            )
    finally:
        refdb.close()

    return failures


def _format_failure(f: UnresolvableUrnReference) -> str:
    return f"{f.project}/{f.file_name}: {f.element_path} @{f.attribute_name}={f.urn}"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that compilation-relevant URN references are resolvable using refdb (post-conversion)."
    )
    parser.add_argument("project", help="Project name under project/ (e.g., wlc, jps1917)")
    parser.add_argument(
        "--project-directory",
        default=str(PROJECT_DIRECTORY),
        help="Base project directory (defaults to repo project/)",
    )
    parser.add_argument(
        "--reference-db",
        default=str(INDEX_DB_FILE),
        help="Path to reference.db (defaults to opensiddur database/reference.db)",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="(Optional) index the project into refdb before validating",
    )

    args = parser.parse_args(argv)

    failures = validate_project_urn_references(
        args.project,
        project_directory=Path(args.project_directory),
        reference_db_path=Path(args.reference_db),
        index_before_validate=args.index,
    )
    if failures:
        for f in failures:
            print(_format_failure(f))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

