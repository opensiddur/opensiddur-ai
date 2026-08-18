"""Rolling [Unreleased] into a released version section."""

import unittest

from opensiddur.release.changelog import ChangelogError, roll
from opensiddur.release.version import Version

CHANGELOG = """\
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- A new synthetic feature, for testing.

### Fixed
- A synthetic bug.

## [0.1.0] - 2026-05-26

Initial public release.
"""

EMPTY_UNRELEASED = """\
# Changelog

## [Unreleased]

## [0.1.0] - 2026-05-26

Initial public release.
"""

NO_UNRELEASED = """\
# Changelog

## [0.1.0] - 2026-05-26

Initial public release.
"""


class TestRoll(unittest.TestCase):
    def test_entries_move_under_the_new_version(self):
        rolled = roll(CHANGELOG, Version(0, 2, 0), "2026-08-17")
        self.assertIn("## [0.2.0] - 2026-08-17", rolled.text)
        self.assertIn("A new synthetic feature, for testing.", rolled.notes)
        self.assertIn("A synthetic bug.", rolled.notes)

    def test_new_section_precedes_the_old_release(self):
        rolled = roll(CHANGELOG, Version(0, 2, 0), "2026-08-17")
        self.assertLess(
            rolled.text.index("## [0.2.0]"), rolled.text.index("## [0.1.0]")
        )

    def test_unreleased_section_is_left_empty(self):
        rolled = roll(CHANGELOG, Version(0, 2, 0), "2026-08-17")
        unreleased_start = rolled.text.index("## [Unreleased]")
        next_start = rolled.text.index("## [0.2.0]")
        between = rolled.text[unreleased_start + len("## [Unreleased]") : next_start]
        self.assertEqual(between.strip(), "")

    def test_empty_unreleased_raises(self):
        with self.assertRaises(ChangelogError):
            roll(EMPTY_UNRELEASED, Version(0, 2, 0), "2026-08-17")

    def test_missing_unreleased_heading_raises(self):
        with self.assertRaises(ChangelogError):
            roll(NO_UNRELEASED, Version(0, 2, 0), "2026-08-17")

    def test_pinned_sources_are_recorded(self):
        rolled = roll(
            CHANGELOG,
            Version(0, 2, 0),
            "2026-08-17",
            pinned={
                "sourcetexts": "abc1234",
                "opensiddur-projects": "def5678",
            },
        )
        self.assertIn("### Pinned sources", rolled.notes)
        self.assertIn("`opensiddur-projects`: def5678", rolled.notes)
        self.assertIn("`sourcetexts`: abc1234", rolled.notes)

    def test_no_pinned_sources_omits_the_section(self):
        rolled = roll(CHANGELOG, Version(0, 2, 0), "2026-08-17")
        self.assertNotIn("Pinned sources", rolled.notes)


if __name__ == "__main__":
    unittest.main()
