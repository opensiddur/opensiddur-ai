"""Rolling the Keep a Changelog `[Unreleased]` section into a released version."""

import re
from dataclasses import dataclass

from opensiddur.release.version import Version

UNRELEASED_HEADING = "## [Unreleased]"
SECTION_HEADING_RE = re.compile(r"^## ", re.MULTILINE)

PINNED_HEADING = "### Pinned sources"


class ChangelogError(ValueError):
    """The changelog is not in a state a release can be cut from."""


@dataclass(frozen=True)
class RolledChangelog:
    text: str
    """The whole changelog, with an emptied `[Unreleased]` above the new version section."""

    notes: str
    """The body of the new version section: the release notes, without the heading."""


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    """Line indexes of the heading and of the section heading that follows it (or EOF)."""
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise ChangelogError(f"No {heading!r} heading in the changelog.") from None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return start, end


def pinned_sources_note(pinned: dict[str, str]) -> str:
    """The block recording which submodule commits this release was cut against."""
    lines = [PINNED_HEADING, ""]
    lines += [f"- `{path}`: {commit}" for path, commit in sorted(pinned.items())]
    return "\n".join(lines)


def roll(text: str, version: Version, date: str, pinned: dict[str, str] | None = None) -> RolledChangelog:
    """Move the `[Unreleased]` entries into a `## [version] - date` section beneath it.

    `pinned` maps a submodule path to the commit this release pins it to; it is appended to
    the new section so the changelog says what the tag was built against.
    """
    lines = text.splitlines()
    start, end = _section_bounds(lines, UNRELEASED_HEADING)

    body = "\n".join(lines[start + 1 : end]).strip("\n")
    if not body.strip():
        raise ChangelogError(
            "The [Unreleased] section is empty; there is nothing to release."
        )

    notes = body
    if pinned:
        notes = f"{notes}\n\n{pinned_sources_note(pinned)}"

    released = [f"## [{version}] - {date}", "", notes, ""]
    rolled = lines[: start + 1] + [""] + released + lines[end:]
    return RolledChangelog(text="\n".join(rolled).rstrip("\n") + "\n", notes=notes)
