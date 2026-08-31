"""Schema-validate the XML of one or more projects, as a CI gate.

``opensiddur.importer.util.validation`` validates a single file and its ``main`` returns a
bool without ever exiting non-zero -- fine for a one-off check, unusable as a required
status check. This module runs RelaxNG + Schematron (well-formedness comes with the
RelaxNG pass) over every ``*.xml`` in a set of projects, prints a per-file report, and
exits non-zero if anything failed.

It is deliberately a sibling of :mod:`opensiddur.exporter.validate_urn_references` and
:mod:`opensiddur.exporter.validate_versification`: same ``--project-directory`` default,
same "raise SystemExit(code)" shape. Exit ``1`` on any invalid or malformed file, ``0``
otherwise (``validate_urn_references`` uses ``2``, ``validate_versification`` uses ``1``).

Typical CI use, validating every file in the projects a PR touched::

    python -m opensiddur.exporter.validate_schema \\
        --project-directory "$GITHUB_WORKSPACE/projects/project" \\
        --repo-root "$GITHUB_WORKSPACE" --github-annotations \\
        --project humash --project wlc

With no ``--project`` and no ``--files-from`` every project under ``--project-directory``
is validated.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.importer.util.validation import relaxng_validate, schematron_validate

#: A cleaned Jing line: ``XML:<line>:<col>: <level>: <message>`` (the temp path is replaced
#: with the literal ``XML`` by ``relaxng_validate``).
_JING_LINE = re.compile(r"^XML:(?P<line>\d+):(?P<col>\d+):\s*(?P<message>.*)$")
#: The lxml well-formedness message shape produced below.
_SYNTAX_LINE = re.compile(r"at line (?P<line>\d+), column (?P<col>\d+)$")


@dataclass(frozen=True)
class FileResult:
    """The outcome for one file. ``ok`` is true only when there are no errors."""

    path: Path
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class SchemaReport:
    results: list[FileResult] = field(default_factory=list)
    #: Project names passed via ``--project`` whose directory does not exist. Not an error:
    #: a PR may delete a project.
    skipped_projects: list[str] = field(default_factory=list)

    @property
    def failures(self) -> list[FileResult]:
        return [r for r in self.results if not r.ok]

    @property
    def ok(self) -> bool:
        return not self.failures


def iter_target_files(
    *,
    project_directory: Path = PROJECT_DIRECTORY,
    projects: Optional[list[str]] = None,
    files_from: Optional[list[Path]] = None,
) -> tuple[list[Path], list[str]]:
    """Resolve what to validate.

    Returns ``(files, skipped_projects)``. ``files_from`` (explicit paths, absolute or
    relative to ``project_directory``) and ``projects`` (every top-level ``*.xml`` in each,
    matching every other project iterator in this package) are unioned. With neither, every
    project directory under ``project_directory`` is used.
    """
    project_directory = Path(project_directory)
    files: list[Path] = []
    seen: set[Path] = set()
    skipped: list[str] = []

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(path)

    for raw in files_from or []:
        path = Path(raw)
        if not path.is_absolute():
            path = project_directory / path
        add(path)

    names = projects
    if names is None and not files_from:
        names = sorted(p.name for p in project_directory.iterdir() if p.is_dir())
    for name in names or []:
        project_path = project_directory / name
        if not project_path.is_dir():
            skipped.append(name)
            continue
        for xml_file in sorted(project_path.glob("*.xml")):
            add(xml_file)

    return files, skipped


def validate_file(path: Path) -> FileResult:
    """RelaxNG + Schematron for one file, well-formedness first.

    The raw file text is handed to the validators (not a re-serialised tree) so Jing's line
    numbers point at the source.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return FileResult(Path(path), (f"cannot read file: {exc}",))

    try:
        etree.fromstring(text.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        return FileResult(
            Path(path),
            (f"XML syntax error: {exc.msg} at line {exc.lineno}, column {exc.position[0]}",),
        )

    ok_rng, errors_rng = relaxng_validate(text)
    ok_sch, errors_sch = schematron_validate(text)
    if ok_rng and ok_sch:
        return FileResult(Path(path))
    return FileResult(Path(path), tuple(errors_rng) + tuple(errors_sch))


def validate_files(paths: list[Path]) -> list[FileResult]:
    return [validate_file(path) for path in paths]


def format_annotation(file_path: str, error: str) -> str:
    """A GitHub ``::error`` workflow command for one error line.

    Jing and lxml errors carry ``line``/``col``; Schematron errors carry only an XPath
    location, which goes in the message.
    """
    jing = _JING_LINE.match(error)
    if jing:
        return (
            f"::error file={file_path},line={jing['line']},col={jing['col']}::"
            f"{jing['message']}"
        )
    syntax = _SYNTAX_LINE.search(error)
    if syntax:
        return (
            f"::error file={file_path},line={syntax['line']},col={syntax['col']}::{error}"
        )
    return f"::error file={file_path}::{error}"


def validate_schema(
    *,
    project_directory: Path = PROJECT_DIRECTORY,
    projects: Optional[list[str]] = None,
    files_from: Optional[list[Path]] = None,
) -> SchemaReport:
    files, skipped = iter_target_files(
        project_directory=project_directory, projects=projects, files_from=files_from
    )
    return SchemaReport(results=validate_files(files), skipped_projects=skipped)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--project-directory",
        type=Path,
        default=PROJECT_DIRECTORY,
        help="Base project directory (defaults to repo project/).",
    )
    parser.add_argument(
        "--project",
        action="append",
        dest="projects",
        help="Project to validate; repeatable. Every *.xml in it is checked. "
        "Defaults to every project under --project-directory.",
    )
    parser.add_argument(
        "--files-from",
        type=Path,
        help="File of newline-delimited XML paths to validate (absolute, or relative to "
        "--project-directory). Unioned with --project.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Root that --github-annotations file paths are made relative to.",
    )
    parser.add_argument(
        "--github-annotations",
        action="store_true",
        help="Also emit ::error file=...,line=...:: workflow commands.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Also list files that passed.")
    args = parser.parse_args(argv)

    files_from: Optional[list[Path]] = None
    if args.files_from:
        files_from = [
            Path(line.strip())
            for line in Path(args.files_from).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    report = validate_schema(
        project_directory=args.project_directory,
        projects=args.projects,
        files_from=files_from,
    )

    def rel(path: Path) -> str:
        try:
            return os.path.relpath(Path(path).resolve(), Path(args.repo_root).resolve())
        except ValueError:  # different drive on Windows
            return str(path)

    for name in report.skipped_projects:
        print(f"SKIP  {name} (no such project directory)")

    for result in report.results:
        if result.ok:
            if args.verbose:
                print(f"OK    {rel(result.path)}")
            continue
        print(f"FAIL  {rel(result.path)}")
        for error in result.errors:
            print(f"      {error}")
            if args.github_annotations:
                print(format_annotation(rel(result.path), error))

    checked = len(report.results)
    if report.ok:
        print(f"OK: {checked} file(s) valid")
        return 0
    print(f"FAILED: {len(report.failures)} of {checked} file(s) invalid")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
