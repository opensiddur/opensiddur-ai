"""Skip helpers for tests that need data this repository does not carry.

The haggadah sources live in ``opensiddur/sourcetexts`` and the compiled projects in
``opensiddur/projects``; neither is checked out in CI. A test that reads either is checking
that a curated table still matches real data, not that the code is correct, so it skips when
the data is absent rather than failing.

Tests of the conversion *logic* must not come through here at all — they supply their own
input, as :mod:`test_parse_compilation` does, and run everywhere.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from opensiddur.importer.util.pages import feinstein_haggadah_data_directory

#: Parsed once; ``build_section_contents`` over the whole compilation is slow enough that the
#: curation tests were spending most of their time re-doing it.
_SECTIONS: dict | None = None


def compilation_path() -> Path:
    return feinstein_haggadah_data_directory() / "compilation.json"


def require_path(path: Path, reason: str) -> Path:
    """Return ``path``, or skip the calling test when it does not exist."""
    if not path.exists():
        raise unittest.SkipTest(f"{reason}: {path} not available")
    return path


def compilation_sections() -> dict:
    """Section contents parsed from the real compilation, or skip.

    Returns the shared cache. Tests must treat it as read-only.
    """
    global _SECTIONS

    require_path(compilation_path(), "haggadah compilation not checked out")
    if _SECTIONS is None:
        from opensiddur.importer.feinstein_haggadah.parse_compilation import (
            build_section_contents,
            load_compilation_json,
            parse_rows,
        )

        _SECTIONS = build_section_contents(parse_rows(load_compilation_json()))
    return _SECTIONS


def compilation_section_texts() -> dict[str, str]:
    """Hebrew text per section from the real compilation, or skip."""
    from opensiddur.importer.feinstein_haggadah.versify import section_texts

    require_path(compilation_path(), "haggadah compilation not checked out")
    return section_texts()
