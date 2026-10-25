"""Tests for the `book:` key of a settings file, and the compiler taking its target from it."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from pydantic import ValidationError

from opensiddur.exporter.compiler import main as compiler_main
from opensiddur.exporter.linear import reset_linear_data
from opensiddur.exporter.settings import load_settings, read_settings


class _BookSettingsCase(unittest.TestCase):

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_dir = Path(self.temp_dir.name) / "project"
        (self.project_dir / "proj-a" / "sub").mkdir(parents=True)
        (self.project_dir / "proj-a" / "index.xml").write_text("<TEI/>")
        (self.project_dir / "proj-a" / "sub" / "part.xml").write_text("<TEI/>")

    def _write_yaml(self, data: dict) -> Path:
        path = Path(self.temp_dir.name) / "settings.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def _read(self, data: dict):
        return read_settings(self._write_yaml(data), project_directory=self.project_dir)


class TestBookKey(_BookSettingsCase):

    def test_book_is_optional(self):
        self.assertIsNone(self._read({"priority": {}}).book)

    def test_book_is_read(self):
        book = self._read({
            "book": {"project": "proj-a", "file_name": "index.xml", "title": "Book A"},
            "priority": {},
        }).book
        self.assertEqual(book.project, "proj-a")
        self.assertEqual(book.file_name, "index.xml")
        self.assertEqual(book.title, "Book A")

    def test_file_name_may_be_in_a_subdirectory(self):
        book = self._read({"book": {"project": "proj-a", "file_name": "sub/part.xml"}, "priority": {}}).book
        self.assertEqual(book.file_name, "sub/part.xml")

    def test_unknown_project_is_refused(self):
        with self.assertRaises(ValidationError) as cm:
            self._read({"book": {"project": "nope", "file_name": "index.xml"}, "priority": {}})
        self.assertIn("Project nope does not exist", str(cm.exception))

    def test_missing_file_is_refused(self):
        with self.assertRaises(ValidationError) as cm:
            self._read({"book": {"project": "proj-a", "file_name": "missing.xml"}, "priority": {}})
        self.assertIn("File missing.xml does not exist in project proj-a", str(cm.exception))

    def test_directory_is_not_a_file(self):
        with self.assertRaises(ValidationError):
            self._read({"book": {"project": "proj-a", "file_name": "sub"}, "priority": {}})

    def test_unknown_book_key_is_refused(self):
        with self.assertRaises(ValidationError):
            self._read({"book": {"project": "proj-a", "file_name": "index.xml", "author": "x"},
                        "priority": {}})

    def test_description_is_read(self):
        settings = self._read({"description": "Triennial readings.", "priority": {}})
        self.assertEqual(settings.description, "Triennial readings.")

    def test_load_settings_accepts_book(self):
        path = self._write_yaml({
            "book": {"project": "proj-a", "file_name": "index.xml"},
            "priority": {"transclusion": ["proj-a"]},
        })
        linear_data = load_settings(path, project_directory=self.project_dir)
        self.assertEqual(linear_data.project_priority, ["proj-a"])


class TestFormats(_BookSettingsCase):

    def test_default_is_both(self):
        self.assertEqual(self._read({"priority": {}}).formats, ["html", "pdf"])

    def test_electronic_only(self):
        self.assertEqual(self._read({"priority": {}, "formats": ["html"]}).formats, ["html"])

    def test_refused(self):
        for formats in ([], ["html", "html"], ["epub"], "html"):
            with self.subTest(formats=formats), self.assertRaises(ValidationError):
                self._read({"priority": {}, "formats": formats})


class _CompilerCalled(Exception):
    pass


class TestCompilerTargetFromBook(_BookSettingsCase):
    """ The compiler CLI falls back to the settings file's book for -p/-f. """

    def _target(self, argv: list[str]) -> tuple[str, str]:
        with patch("opensiddur.exporter.external_compiler.ExternalCompilerProcessor",
                   side_effect=_CompilerCalled) as processor:
            with self.assertRaises(_CompilerCalled):
                compiler_main([*argv, "--project-directory", str(self.project_dir)])
        return processor.call_args.args[:2]

    def test_target_from_book(self):
        path = self._write_yaml({"book": {"project": "proj-a", "file_name": "index.xml"},
                                 "priority": {"transclusion": ["proj-a"]}})
        self.assertEqual(self._target(["-s", str(path)]), ("proj-a", "index.xml"))

    def test_flags_override_book(self):
        path = self._write_yaml({"book": {"project": "proj-a", "file_name": "index.xml"},
                                 "priority": {"transclusion": ["proj-a"]}})
        self.assertEqual(self._target(["-s", str(path), "-f", "sub/part.xml"]),
                         ("proj-a", "sub/part.xml"))

    def test_no_target_is_an_error(self):
        path = self._write_yaml({"priority": {"transclusion": ["proj-a"]}})
        with patch("sys.stderr"), self.assertRaises(SystemExit) as cm:
            compiler_main(["-s", str(path), "--project-directory", str(self.project_dir)])
        self.assertEqual(cm.exception.code, 2)

    def test_no_settings_and_no_flags_is_an_error(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as cm:
            compiler_main(["--project-directory", str(self.project_dir)])
        self.assertEqual(cm.exception.code, 2)



class TestFontsAreNotTheCompilersQuestion(_BookSettingsCase):
    """The compiler typesets nothing, so a face missing here must not stop a compile."""

    SETTINGS = {"priority": {}, "typography": {"fonts": {"latin": "No Such Face"}}}

    def _no_fonts_installed(self):
        from opensiddur.exporter import typography
        return patch.object(typography, "_installed_font_families", return_value=frozenset())

    def test_read_settings_resolves_fonts_by_default(self):
        with self._no_fonts_installed():
            with self.assertRaises(ValidationError):
                self._read(self.SETTINGS)

    def test_read_settings_can_skip_font_resolution(self):
        with self._no_fonts_installed():
            settings = read_settings(
                self._write_yaml(self.SETTINGS), project_directory=self.project_dir,
                resolve_fonts=False,
            )
        self.assertEqual(["No Such Face"], settings.typography.fonts["latin"].names)

    def test_load_settings_does_not_resolve_fonts(self):
        with self._no_fonts_installed():
            load_settings(self._write_yaml(self.SETTINGS), project_directory=self.project_dir)


if __name__ == "__main__":
    unittest.main()
