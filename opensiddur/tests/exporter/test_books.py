"""Tests for building a printed book per settings file (opensiddur.exporter.books)."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from opensiddur.exporter import books, typography

# A machine with one face for each default chain.
_FONTS = frozenset({"linux libertine o", "freeserif"})


class TestBooks(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.project_dir = root / "project"
        self.settings_dir = root / "settings"
        self.output_dir = root / "out"
        self.settings_dir.mkdir()
        for project in ("proj-a", "proj-b"):
            (self.project_dir / project).mkdir(parents=True)
            (self.project_dir / project / "index.xml").write_text("<TEI/>")
        fonts = patch.object(typography, "_installed_font_families", return_value=_FONTS)
        fonts.start()
        self.addCleanup(fonts.stop)

    def _settings(self, name: str, data: dict) -> Path:
        path = self.settings_dir / f"{name}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(data))
        return path

    def _book(self, name: str, project: str = "proj-a", **extra) -> Path:
        return self._settings(name, {"book": {"project": project, "file_name": "index.xml"},
                                     "priority": {"transclusion": [project]}, **extra})

    def _check(self, path: Path) -> books.BookResult:
        return books.check(path, self.settings_dir, self.project_dir)

    def _main(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = books.main([*argv, "--project-directory", str(self.project_dir)])
        return code, out.getvalue()

    # ── discovery and naming ────────────────────────────────────────────────

    def test_default_settings_directory_is_beside_projects(self):
        self.assertEqual(books.default_settings_directory(self.project_dir), self.settings_dir)

    def test_discover_sorted_yaml_only(self):
        self._book("b/one")
        self._book("a/two")
        self._book("a/one")
        (self.settings_dir / "a" / "README.md").write_text("not a book")
        self.assertEqual([books.book_name(p, self.settings_dir) for p in books.discover(self.settings_dir)],
                         ["a/one", "a/two", "b/one"])

    def test_discover_includes_misplaced_files(self):
        self._book("loose")
        self._book("a/b/deep")
        self.assertEqual(len(books.discover(self.settings_dir)), 2)

    def test_discover_missing_directory(self):
        self.assertEqual(books.discover(self.settings_dir / "nope"), [])

    def test_output_name(self):
        self.assertEqual(books.output_name("humash/annual"), "humash-annual.pdf")
        self.assertEqual(books.output_name("humash/annual", "v0.5.0"), "humash-annual-v0.5.0.pdf")

    # ── check ───────────────────────────────────────────────────────────────

    def test_check_ok(self):
        result = self._check(self._book("a/one", description="The plain edition."))
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.name, "a/one")
        self.assertEqual(result.book.project, "proj-a")

    def test_check_misplaced_at_top_level(self):
        self.assertIn("misplaced", self._check(self._book("loose")).error)

    def test_check_misplaced_too_deep(self):
        self.assertIn("misplaced", self._check(self._book("a/b/deep")).error)

    def test_check_requires_book(self):
        result = self._check(self._settings("a/one", {"priority": {}}))
        self.assertIn("no `book:` key", result.error)

    def test_check_invalid_settings(self):
        result = self._check(self._settings("a/one", {"priority": {}, "bogus": 1}))
        self.assertIn("invalid settings", result.error)

    def test_check_missing_project(self):
        result = self._check(self._book("a/one", project="nope"))
        self.assertIn("invalid settings", result.error)

    def test_check_missing_file(self):
        result = self._check(self._settings("a/one", {
            "book": {"project": "proj-a", "file_name": "missing.xml"}, "priority": {}}))
        self.assertIn("File missing.xml does not exist", result.error)

    def test_check_unparseable_yaml(self):
        path = self.settings_dir / "a" / "one.yaml"
        path.parent.mkdir()
        path.write_text("priority: [unclosed\n")
        self.assertIn("unreadable settings", self._check(path).error)

    def test_check_default_font_chain_missing(self):
        """ A default chain is not checked by settings validation, but the book can't be set without it. """
        path = self._book("a/one")
        with patch.object(typography, "_installed_font_families", return_value=frozenset({"freeserif"})):
            result = self._check(path)
        self.assertIn("font `latin`", result.error)

    def test_check_declared_font_chain_missing(self):
        path = self._book("a/one", typography={"fonts": {"hebrew": ["Nonesuch Hebrew"]}})
        self.assertIn("Nonesuch Hebrew", self._check(path).error)

    def test_check_without_fontconfig_fails(self):
        path = self._book("a/one")
        with patch.object(typography, "_installed_font_families", return_value=None):
            result = self._check(path)
        self.assertIn("fontconfig", result.error)

    def test_main_check_reports_each_file(self):
        self._book("good/one")
        self._settings("bad/one", {"priority": {}})
        with patch.object(books.subprocess, "run") as run:
            code, out = self._main("--check")
        run.assert_not_called()
        self.assertEqual(code, 1)
        self.assertIn("ok      good/one: proj-a/index.xml", out)
        self.assertIn("FAILED  bad/one", out)
        self.assertIn("1 of 2 books ok", out)

    def test_main_empty_directory_succeeds(self):
        code, out = self._main("--check")
        self.assertEqual(code, 0)
        self.assertIn("No settings files", out)

    # ── build ───────────────────────────────────────────────────────────────

    def _build(self, path: Path, suffix=None) -> books.BookResult:
        self.output_dir.mkdir(exist_ok=True)
        return books.build(path, self.settings_dir, self.project_dir, self.output_dir, suffix)

    def test_build_runs_compiler_then_pdf(self):
        path = self._book("a/one")
        with patch.object(books.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0)) as run:
            result = self._build(path, "v1.0.0")
        self.assertTrue(result.ok)
        self.assertEqual(result.output_pdf, self.output_dir / "a-one-v1.0.0.pdf")
        compile_cmd, pdf_cmd = (c.args[0] for c in run.call_args_list)
        self.assertEqual(compile_cmd[:3], [sys.executable, "-m", "opensiddur.exporter.compiler"])
        compiled = compile_cmd[compile_cmd.index("-o") + 1]
        self.assertEqual(pdf_cmd[:3], [sys.executable, "-m", "opensiddur.exporter.pdf.pdf"])
        self.assertEqual(pdf_cmd[3:5], [compiled, str(self.output_dir / "a-one-v1.0.0.pdf")])
        for cmd in (compile_cmd, pdf_cmd):
            self.assertEqual(cmd[cmd.index("-s") + 1], str(path))
            self.assertEqual(cmd[cmd.index("--project-directory") + 1], str(self.project_dir))
        self.assertTrue((self.output_dir / "a-one.log").exists())

    def test_build_stops_at_failed_compile(self):
        with patch.object(books.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 1)) as run:
            result = self._build(self._book("a/one"))
        self.assertEqual(run.call_count, 1)
        self.assertIn("compilation failed", result.error)

    def test_build_reports_failed_pdf(self):
        with patch.object(books.subprocess, "run",
                          side_effect=[subprocess.CompletedProcess([], 0),
                                       subprocess.CompletedProcess([], 1)]):
            result = self._build(self._book("a/one"))
        self.assertIn("typesetting failed", result.error)
        self.assertIsNone(result.output_pdf)

    def test_build_skips_invalid_settings(self):
        with patch.object(books.subprocess, "run") as run:
            result = self._build(self._settings("a/one", {"priority": {}}))
        run.assert_not_called()
        self.assertFalse(result.ok)

    def test_main_failed_book_does_not_stop_the_rest(self):
        self._book("a/one")
        self._book("b/one", project="proj-b")
        # a/one: compile fails. b/one: compile and pdf succeed.
        returncodes = iter([1, 0, 0])
        with patch.object(books.subprocess, "run",
                          side_effect=lambda *a, **k: subprocess.CompletedProcess([], next(returncodes))):
            code, out = self._main("-o", str(self.output_dir), "--suffix", "v1")
        self.assertEqual(code, 1)
        self.assertIn("FAILED  a/one: compilation failed", out)
        self.assertIn("ok      b/one: proj-b/index.xml -> ", out)
        self.assertIn("b-one-v1.pdf", out)
        self.assertIn("1 of 2 books ok", out)

    def test_main_all_ok(self):
        self._book("a/one")
        with patch.object(books.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0)):
            code, _ = self._main("-o", str(self.output_dir))
        self.assertEqual(code, 0)

    def test_main_select_a_book_selects_all_its_settings(self):
        self._book("a/one")
        self._book("a/two")
        self._book("ab/one")
        code, out = self._main("--check", "a")
        self.assertEqual(code, 0)
        self.assertIn("a/one", out)
        self.assertIn("a/two", out)
        self.assertNotIn("ab/one", out)

    def test_main_select_one_settings_file(self):
        self._book("a/one")
        self._book("a/two")
        code, out = self._main("--check", "a/two", "a/two")
        self.assertEqual(code, 0)
        self.assertNotIn("a/one", out)
        self.assertIn("1 of 1 books ok", out)

    def test_main_list(self):
        self._book("b/one")
        self._book("a/one")
        self._book("loose")
        code, out = self._main("--list")
        self.assertEqual(code, 0)
        # Misplaced files are listed too, so their build fails visibly rather than being skipped.
        self.assertEqual(json.loads(out), ["a/one", "b/one", "loose"])

    def test_main_list_empty(self):
        code, out = self._main("--list")
        self.assertEqual((code, json.loads(out)), (0, []))

    def test_main_list_and_check_are_exclusive(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit):
            self._main("--list", "--check")

    def test_main_unknown_name_is_an_error(self):
        with patch("sys.stderr"), self.assertRaises(SystemExit) as cm:
            self._main("nope")
        self.assertEqual(cm.exception.code, 2)

    def test_main_explicit_settings_directory(self):
        other = Path(self.temp_dir.name) / "elsewhere"
        (other / "x").mkdir(parents=True)
        (other / "x" / "y.yaml").write_text(yaml.dump({"priority": {}}))
        code, out = self._main("--check", "--settings-directory", str(other))
        self.assertEqual(code, 1)
        self.assertIn("x/y", out)


if __name__ == "__main__":
    unittest.main()
