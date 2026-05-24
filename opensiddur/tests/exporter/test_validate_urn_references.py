import io
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.refdb import ReferenceDatabase
from opensiddur.exporter.validate_urn_references import (
    UnresolvableUrnReference,
    _format_failure,
    main,
    validate_project_urn_references,
)


TEI_NS = "http://www.tei-c.org/ns/1.0"
JLPTEI_NS = "http://jewishliturgy.org/ns/jlptei/2"
NSMAP = {"tei": TEI_NS, "j": JLPTEI_NS}


def _write_project_xml(base: Path, project: str, filename: str, root: etree._Element) -> Path:
    project_path = base / project
    project_path.mkdir(parents=True, exist_ok=True)
    xml_path = project_path / filename
    etree.ElementTree(root).write(str(xml_path), encoding="utf-8", xml_declaration=True)
    return xml_path


def _add_urn_mapping(db_path: Path, project: str, file_name: str, urn: str) -> None:
    db = ReferenceDatabase(db_path)
    try:
        element = etree.Element(f"{{{TEI_NS}}}milestone")
        element.set("corresp", urn)
        db.add_urn_mapping(project, file_name, element)
    finally:
        db.close()


class TestValidateUrnReferences(unittest.TestCase):
    def test_validates_ptr_and_ref_targets(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="urn:x-opensiddur:test:doc1")
            etree.SubElement(body, f"{{{TEI_NS}}}ref", target="urn:x-opensiddur:test:doc2/1")

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1")
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc2/1")

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
                index_before_validate=False,
            )
            self.assertEqual(failures, [])

    def test_reports_unresolvable_urns(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="urn:x-opensiddur:test:missing")

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
                index_before_validate=False,
            )
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0].file_name, "a.xml")
            self.assertEqual(failures[0].attribute_name, "target")

    def test_raises_when_project_directory_missing(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            with self.assertRaises(ValueError) as ctx:
                validate_project_urn_references(
                    "missing_project",
                    project_directory=base,
                    reference_db_path=db_path,
                )
            self.assertIn("Project directory does not exist", str(ctx.exception))

    def test_skips_non_urn_targets(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="http://example.com/doc")
            etree.SubElement(body, f"{{{TEI_NS}}}ref", target="local/path.xml")

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(failures, [])

    def test_index_before_validate(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            div = etree.SubElement(xml, f"{{{TEI_NS}}}div")
            div.set("corresp", "urn:x-opensiddur:test:doc1")

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
                index_before_validate=True,
            )
            self.assertEqual(failures, [])

    def test_validates_resolvable_transclude(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(
                body,
                f"{{{JLPTEI_NS}}}transclude",
                target="urn:x-opensiddur:test:doc1",
            )

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1")

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(failures, [])

    def test_validates_transclude_with_target_end_in_same_project(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(
                body,
                f"{{{JLPTEI_NS}}}transclude",
                target="urn:x-opensiddur:test:doc1/1",
                targetEnd="urn:x-opensiddur:test:doc1/2",
            )

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1/1")
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1/2")

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(failures, [])

    def test_reports_unresolvable_transclude_target(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(
                body,
                f"{{{JLPTEI_NS}}}transclude",
                target="urn:x-opensiddur:test:missing",
            )

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0].attribute_name, "target")
            self.assertEqual(failures[0].urn, "urn:x-opensiddur:test:missing")

    def test_reports_unresolvable_transclude_target_end(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(
                body,
                f"{{{JLPTEI_NS}}}transclude",
                target="urn:x-opensiddur:test:doc1/1",
                targetEnd="urn:x-opensiddur:test:doc1/missing",
            )

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1/1")

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0].attribute_name, "targetEnd")

    def test_reports_transclude_target_end_in_wrong_project(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(
                body,
                f"{{{JLPTEI_NS}}}transclude",
                target="urn:x-opensiddur:test:doc1/1",
                targetEnd="urn:x-opensiddur:test:doc1/2",
            )

            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            _add_urn_mapping(db_path, project, "a.xml", "urn:x-opensiddur:test:doc1/1")
            _add_urn_mapping(db_path, "proj2", "b.xml", "urn:x-opensiddur:test:doc1/1")
            _add_urn_mapping(db_path, "proj2", "b.xml", "urn:x-opensiddur:test:doc1/2")

            failures = validate_project_urn_references(
                project,
                project_directory=base,
                reference_db_path=db_path,
            )
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0].attribute_name, "targetEnd")

    def test_format_failure(self):
        failure = UnresolvableUrnReference(
            project="proj1",
            file_name="a.xml",
            element_path="/TEI/text/body/ptr[1]",
            attribute_name="target",
            urn="urn:x-opensiddur:test:missing",
        )
        self.assertEqual(
            _format_failure(failure),
            "proj1/a.xml: /TEI/text/body/ptr[1] @target=urn:x-opensiddur:test:missing",
        )


class TestValidateUrnReferencesMain(unittest.TestCase):
    def test_main_success(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            div = etree.SubElement(xml, f"{{{TEI_NS}}}div")
            div.set("corresp", "urn:x-opensiddur:test:doc1")
            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"

            result = main(
                [
                    project,
                    "--project-directory",
                    str(base),
                    "--reference-db",
                    str(db_path),
                    "--index",
                ]
            )
            self.assertEqual(result, 0)

    def test_main_reports_failures(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="urn:x-opensiddur:test:missing")
            _write_project_xml(base, project, "a.xml", xml)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                result = main(
                    [
                        project,
                        "--project-directory",
                        str(base),
                        "--reference-db",
                        str(db_path),
                    ]
                )

            self.assertEqual(result, 2)
            self.assertIn("urn:x-opensiddur:test:missing", stdout.getvalue())

    def test_main_module_entry_point(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"
            (base / project).mkdir(parents=True)

            db_path = base / "ref.db"
            ReferenceDatabase(db_path).close()

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "opensiddur.exporter.validate_urn_references",
                    project,
                    "--project-directory",
                    str(base),
                    "--reference-db",
                    str(db_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
