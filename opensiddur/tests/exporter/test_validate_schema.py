"""Tests for the schema-validation CI gate.

Every fixture here is synthetic, built in a temporary directory -- never the real
``project/`` data, so these tests do not break when that data changes (see the top-level
CLAUDE.md). Validation runs against the real, built schema (``bash scripts/build-schema.sh``
must have run first, exactly as the rest of the suite requires).
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from opensiddur.exporter.validate_schema import (
    format_annotation,
    iter_target_files,
    main,
    validate_file,
    validate_schema,
)

VALID_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:j="http://jewishliturgy.org/ns/jlptei/2"
         xml:lang="en">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt>
        <tei:title type="main" xml:lang="en">Test Document</tei:title>
        <tei:respStmt>
          <tei:resp key="mrk">Markup editor</tei:resp>
          <tei:name ref="urn:x-opensiddur:contributor:opensiddur.org/test-editor">Test Editor</tei:name>
        </tei:respStmt>
      </tei:titleStmt>
      <tei:publicationStmt>
        <tei:distributor>
          <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
        </tei:distributor>
        <tei:idno type="urn">urn:x-opensiddur:test:doc1@synthetic_project</tei:idno>
        <tei:availability status="free">
          <tei:licence target="http://www.creativecommons.org/publicdomain/zero/1.0/">Creative Commons Zero (Public Domain Dedication)</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc>
        <tei:p>Synthetic fixture, not real project data.</tei:p>
      </tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text xml:lang="en">
    <tei:body>
      <tei:div corresp="urn:x-opensiddur:test:doc1" n="doc1">
        <tei:head>Test Heading</tei:head>
        <tei:p>
          <tei:milestone unit="verse" n="1" corresp="urn:x-opensiddur:test:doc1/1"/>Test verse one.
          <tei:milestone unit="verse" n="2" corresp="urn:x-opensiddur:test:doc1/2"/>Test verse two.
        </tei:p>
      </tei:div>
    </tei:body>
  </tei:text>
</tei:TEI>
"""

# Schema-invalid: tei:p is not a permitted child of tei:titleStmt.
INVALID_DOC = VALID_DOC.replace(
    "<tei:titleStmt>",
    "<tei:titleStmt><tei:p>not allowed here</tei:p>",
)

MALFORMED_DOC = "<tei:TEI xmlns:tei=\"http://www.tei-c.org/ns/1.0\"><tei:text>"


def _write(base: Path, project: str, filename: str, content: str) -> Path:
    project_path = base / project
    project_path.mkdir(parents=True, exist_ok=True)
    path = project_path / filename
    path.write_text(content, encoding="utf-8")
    return path


class TestValidateFile(unittest.TestCase):
    def test_valid_document(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write(Path(td), "proj", "a.xml", VALID_DOC)
            result = validate_file(path)
            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.errors, ())

    def test_schema_invalid_document(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write(Path(td), "proj", "a.xml", INVALID_DOC)
            result = validate_file(path)
            self.assertFalse(result.ok)
            self.assertTrue(result.errors)

    def test_malformed_document(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write(Path(td), "proj", "a.xml", MALFORMED_DOC)
            result = validate_file(path)
            self.assertFalse(result.ok)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("XML syntax error", result.errors[0])
            self.assertIn("line", result.errors[0])


class TestIterTargetFiles(unittest.TestCase):
    def test_defaults_to_every_project(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            a = _write(base, "proj1", "a.xml", VALID_DOC)
            b = _write(base, "proj2", "b.xml", VALID_DOC)
            files, skipped = iter_target_files(project_directory=base)
            self.assertCountEqual(files, [a, b])
            self.assertEqual(skipped, [])

    def test_named_project_only(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            a = _write(base, "proj1", "a.xml", VALID_DOC)
            _write(base, "proj2", "b.xml", VALID_DOC)
            files, skipped = iter_target_files(project_directory=base, projects=["proj1"])
            self.assertEqual(files, [a])
            self.assertEqual(skipped, [])

    def test_missing_project_is_skipped_not_an_error(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            files, skipped = iter_target_files(project_directory=base, projects=["gone"])
            self.assertEqual(files, [])
            self.assertEqual(skipped, ["gone"])

    def test_files_from_relative_to_project_directory(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj1", "a.xml", VALID_DOC)
            files, skipped = iter_target_files(
                project_directory=base, files_from=[Path("proj1/a.xml")]
            )
            self.assertEqual(files, [base / "proj1" / "a.xml"])


class TestValidateSchema(unittest.TestCase):
    def test_all_valid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj", "a.xml", VALID_DOC)
            report = validate_schema(project_directory=base)
            self.assertTrue(report.ok)
            self.assertEqual(len(report.results), 1)

    def test_one_invalid_fails_the_report(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj", "good.xml", VALID_DOC)
            _write(base, "proj", "bad.xml", INVALID_DOC)
            report = validate_schema(project_directory=base)
            self.assertFalse(report.ok)
            self.assertEqual(len(report.failures), 1)
            self.assertEqual(report.failures[0].path.name, "bad.xml")


class TestFormatAnnotation(unittest.TestCase):
    def test_jing_line_becomes_error_annotation(self):
        line = format_annotation("proj/a.xml", "XML:12:34: error: unexpected element")
        self.assertEqual(
            line, "::error file=proj/a.xml,line=12,col=34::error: unexpected element"
        )

    def test_syntax_error_becomes_error_annotation(self):
        error = "XML syntax error: Premature end of data at line 3, column 1"
        line = format_annotation("proj/a.xml", error)
        self.assertEqual(line, f"::error file=proj/a.xml,line=3,col=1::{error}")

    def test_schematron_error_has_no_line(self):
        error = "/tei:TEI[1]: assertion failed"
        line = format_annotation("proj/a.xml", error)
        self.assertEqual(line, f"::error file=proj/a.xml::{error}")


class TestMain(unittest.TestCase):
    def test_exit_zero_when_all_valid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj", "a.xml", VALID_DOC)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--project-directory", str(base)])
            self.assertEqual(code, 0)
            self.assertIn("OK", out.getvalue())

    def test_exit_one_when_any_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj", "bad.xml", INVALID_DOC)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--project-directory", str(base)])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out.getvalue())

    def test_github_annotations_emitted(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write(base, "proj", "bad.xml", INVALID_DOC)
            out = io.StringIO()
            with redirect_stdout(out):
                main(
                    [
                        "--project-directory",
                        str(base),
                        "--repo-root",
                        str(base),
                        "--github-annotations",
                    ]
                )
            self.assertIn("::error file=proj/bad.xml", out.getvalue())

    def test_missing_project_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--project-directory", str(base), "--project", "gone"])
            self.assertEqual(code, 0)
            self.assertIn("SKIP", out.getvalue())


if __name__ == "__main__":
    unittest.main()
