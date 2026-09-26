"""The `print_once` settings block selects the note types printed only once (issue #168)."""

import tempfile
import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

from opensiddur.exporter.linear import reset_linear_data
from opensiddur.exporter.settings import load_default_settings, load_settings


class TestPrintOnceSettings(unittest.TestCase):
    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_dir = Path(self.temp_dir.name)
        (self.project_dir / "proj-a").mkdir()

    def load(self, **extra):
        data = {"priority": {"transclusion": ["proj-a"], "instructions": ["proj-a"]}, **extra}
        path = self.project_dir / "settings.yaml"
        path.write_text(yaml.dump(data))
        return load_settings(path, project_directory=self.project_dir)

    def test_defaults_to_printing_every_occurrence(self):
        self.assertEqual(self.load().annotation_print_once_types, set())

    def test_each_flag_selects_its_own_note_type(self):
        for flags, expected in (
            ({"commentary": True}, {"commentary"}),
            ({"editorial": True}, {"editorial"}),
            ({"commentary": True, "editorial": True}, {"commentary", "editorial"}),
            ({"commentary": False, "editorial": False}, set()),
        ):
            with self.subTest(flags=flags):
                reset_linear_data()
                self.assertEqual(self.load(print_once=flags).annotation_print_once_types, expected)

    def test_types_that_belong_to_every_occurrence_are_refused(self):
        for note_type in ("instruction", "citation", "commentry"):
            with self.subTest(note_type=note_type), self.assertRaises(ValidationError):
                self.load(print_once={note_type: True})

    def test_default_settings_print_every_occurrence(self):
        ld = load_default_settings("proj-a", "index.xml", project_directory=self.project_dir)
        self.assertEqual(ld.annotation_print_once_types, set())


if __name__ == "__main__":
    unittest.main()
