"""Resolve ``/{project}/{file}#{fragment}`` pointers to a single ``xml:id`` in one file.

Distinct from ``urn.py``'s ``UrnResolver``: a URN addresses *a text*, which may have several
variant representations, and ``@project`` selects one of those possibilities. A file/fragment
pointer addresses one constant position in one file with no notion of "which variant" — so
resolving it needs no reference database, just the file itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

_FILE_FRAGMENT_RE = re.compile(r"^/(?P<project>[^/#]+)/(?P<file_stem>[^/#]+)#(?P<fragment>[^/#]+)$")


@dataclass(frozen=True)
class FileFragmentRef:
    project: str
    file_stem: str
    fragment: str


def parse_file_fragment_ref(target: str) -> FileFragmentRef | None:
    """Parse a ``/{project}/{file}#{fragment}`` target, or return ``None`` if it isn't one."""
    match = _FILE_FRAGMENT_RE.match(target)
    if not match:
        return None
    return FileFragmentRef(**match.groupdict())


def resolve_file_fragment_ref(project_directory: Path, ref: FileFragmentRef) -> bool:
    """Whether ``ref`` names an element that actually exists.

    ``xml:id`` is unique per file, so this is a direct lookup against the referenced file — no
    index or database is needed, unlike URN range resolution.
    """
    xml_path = Path(project_directory) / ref.project / f"{ref.file_stem}.xml"
    if not xml_path.is_file():
        return False
    tree = etree.parse(str(xml_path))
    return bool(
        tree.getroot().xpath(
            "boolean(//*[@xml:id=$fragment])",
            fragment=ref.fragment,
        )
    )
