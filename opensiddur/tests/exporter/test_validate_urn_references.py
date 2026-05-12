import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lxml import etree

from opensiddur.exporter.refdb import ReferenceDatabase
from opensiddur.exporter.validate_urn_references import validate_project_urn_references


TEI_NS = "http://www.tei-c.org/ns/1.0"
NSMAP = {"tei": TEI_NS}


class TestValidateUrnReferences(unittest.TestCase):
    def test_validates_ptr_and_ref_targets(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project = "proj1"
            (base / project).mkdir(parents=True, exist_ok=True)

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="urn:x-opensiddur:test:doc1")
            etree.SubElement(body, f"{{{TEI_NS}}}ref", target="urn:x-opensiddur:test:doc2/1")

            xml_path = base / project / "a.xml"
            etree.ElementTree(xml).write(str(xml_path), encoding="utf-8", xml_declaration=True)

            db_path = base / "ref.db"
            db = ReferenceDatabase(db_path)
            try:
                # Add URN mappings so resolver can resolve the references.
                e1 = etree.Element(f"{{{TEI_NS}}}milestone")
                e1.set("corresp", "urn:x-opensiddur:test:doc1")
                db.add_urn_mapping(project, "a.xml", e1)

                e2 = etree.Element(f"{{{TEI_NS}}}milestone")
                e2.set("corresp", "urn:x-opensiddur:test:doc2/1")
                db.add_urn_mapping(project, "a.xml", e2)
            finally:
                db.close()

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
            (base / project).mkdir(parents=True, exist_ok=True)

            xml = etree.Element(f"{{{TEI_NS}}}TEI", nsmap=NSMAP)
            text = etree.SubElement(xml, f"{{{TEI_NS}}}text")
            body = etree.SubElement(text, f"{{{TEI_NS}}}body")
            etree.SubElement(body, f"{{{TEI_NS}}}ptr", target="urn:x-opensiddur:test:missing")

            xml_path = base / project / "a.xml"
            etree.ElementTree(xml).write(str(xml_path), encoding="utf-8", xml_declaration=True)

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

