"""Version parsing, the 0.x bump policy, and the pyproject.toml rewrite."""

import unittest

from opensiddur.release.version import (
    Version,
    next_version,
    read_pyproject_version,
    write_pyproject_version,
)

PYPROJECT = """\
[project]
name = "opensiddur-ai"
version = "0.1.0"
description = "A synthetic pyproject for tests"
dependencies = [
    "requests>=2.32.4",
]

[tool.hatch.build.targets.wheel]
packages = ["opensiddur"]
"""


class TestVersion(unittest.TestCase):
    def test_parse_and_str(self):
        self.assertEqual(Version.parse("1.2.3"), Version(1, 2, 3))
        self.assertEqual(str(Version(1, 2, 3)), "1.2.3")
        self.assertEqual(Version(1, 2, 3).tag, "v1.2.3")

    def test_parse_rejects_non_versions(self):
        for text in ("1.2", "v1.2.3", "1.2.3-rc1", "", "one.two.three"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                Version.parse(text)

    def test_ordering(self):
        self.assertLess(Version(0, 9, 9), Version(1, 0, 0))
        self.assertLess(Version(0, 1, 0), Version(0, 2, 0))

    def test_bump(self):
        version = Version(1, 2, 3)
        self.assertEqual(version.bump("major"), Version(2, 0, 0))
        self.assertEqual(version.bump("minor"), Version(1, 3, 0))
        self.assertEqual(version.bump("patch"), Version(1, 2, 4))


class TestNextVersion(unittest.TestCase):
    def test_zero_series_defaults_to_minor(self):
        self.assertEqual(next_version(Version(0, 1, 0)), Version(0, 2, 0))

    def test_one_and_above_requires_an_explicit_level(self):
        with self.assertRaises(ValueError):
            next_version(Version(1, 0, 0))
        self.assertEqual(next_version(Version(1, 0, 0), level="patch"), Version(1, 0, 1))

    def test_explicit_version(self):
        self.assertEqual(
            next_version(Version(0, 1, 0), explicit=Version(1, 0, 0)), Version(1, 0, 0)
        )

    def test_explicit_version_must_move_forward(self):
        for explicit in (Version(0, 1, 0), Version(0, 0, 9)):
            with self.subTest(explicit=explicit), self.assertRaises(ValueError):
                next_version(Version(0, 1, 0), explicit=explicit)

    def test_level_and_explicit_version_conflict(self):
        with self.assertRaises(ValueError):
            next_version(Version(0, 1, 0), level="minor", explicit=Version(0, 5, 0))


class TestPyproject(unittest.TestCase):
    def test_read(self):
        self.assertEqual(read_pyproject_version(PYPROJECT), Version(0, 1, 0))

    def test_read_without_a_version_raises(self):
        with self.assertRaises(ValueError):
            read_pyproject_version('[project]\nname = "opensiddur-ai"\n')

    def test_write_changes_only_the_version_line(self):
        written = write_pyproject_version(PYPROJECT, Version(0, 2, 0))
        self.assertEqual(written, PYPROJECT.replace('version = "0.1.0"', 'version = "0.2.0"'))

    def test_write_leaves_dependency_pins_alone(self):
        text = '[project]\nversion = "0.1.0"\ndependencies = ["requests>=2.32.4"]\n'
        written = write_pyproject_version(text, Version(0, 2, 0))
        self.assertIn("requests>=2.32.4", written)
        self.assertEqual(read_pyproject_version(written), Version(0, 2, 0))


if __name__ == "__main__":
    unittest.main()
