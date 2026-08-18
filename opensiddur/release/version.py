"""Version parsing and bumping.

Below 1.0.0 every release bumps the minor version and backwards compatibility is not
promised. From 1.0.0 on the project follows semantic versioning strictly, so the bump
level must be chosen deliberately rather than defaulted.
"""

import re
from dataclasses import dataclass
from typing import Literal

BumpLevel = Literal["major", "minor", "patch"]

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

#: `[project] version = "..."` in pyproject.toml. Anchored to the line so that a version
#: pin inside a dependency specifier cannot match.
PYPROJECT_VERSION_RE = re.compile(r'^version = "(\d+\.\d+\.\d+)"$', re.MULTILINE)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def tag(self) -> str:
        return f"v{self}"

    @classmethod
    def parse(cls, text: str) -> "Version":
        match = VERSION_RE.match(text.strip())
        if match is None:
            raise ValueError(f"Not a major.minor.patch version: {text!r}")
        return cls(*(int(g) for g in match.groups()))

    def bump(self, level: BumpLevel) -> "Version":
        if level == "major":
            return Version(self.major + 1, 0, 0)
        if level == "minor":
            return Version(self.major, self.minor + 1, 0)
        if level == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"Unknown bump level: {level!r}")


def next_version(
    current: Version,
    level: BumpLevel | None = None,
    explicit: Version | None = None,
) -> Version:
    """The version to release, given the current one and what the caller asked for.

    With no level and no explicit version, a 0.x series bumps the minor version. At 1.0.0
    and above there is no safe default: the caller must say which level semver calls for.
    """
    if explicit is not None:
        if level is not None:
            raise ValueError("Give a bump level or an explicit version, not both.")
        if explicit <= current:
            raise ValueError(f"{explicit} is not later than the current version {current}.")
        return explicit
    if level is None:
        if current.major >= 1:
            raise ValueError(
                f"The current version is {current}; at 1.0.0 and above the bump level must be "
                "given explicitly (--major, --minor, or --patch)."
            )
        level = "minor"
    return current.bump(level)


def read_pyproject_version(text: str) -> Version:
    """The project version declared in the text of a pyproject.toml."""
    match = PYPROJECT_VERSION_RE.search(text)
    if match is None:
        raise ValueError("No `version = \"X.Y.Z\"` line found in pyproject.toml.")
    return Version.parse(match.group(1))


def write_pyproject_version(text: str, version: Version) -> str:
    """The text of a pyproject.toml with its project version replaced. Nothing else moves."""
    new_text, count = PYPROJECT_VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise ValueError("No `version = \"X.Y.Z\"` line found in pyproject.toml.")
    return new_text
