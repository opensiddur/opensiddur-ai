import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lxml import etree

from opensiddur.exporter.xml_id_ref import (
    FileFragmentRef,
    parse_file_fragment_ref,
    resolve_file_fragment_ref,
)

TEI_NS = "http://www.tei-c.org/ns/1.0"


class TestParseFileFragmentRef(unittest.TestCase):
    def test_parses_a_well_formed_target(self):
        self.assertEqual(
            parse_file_fragment_ref("/heidenheim_haggadah_1822/index#project_source_bibl"),
            FileFragmentRef(
                project="heidenheim_haggadah_1822",
                file_stem="index",
                fragment="project_source_bibl",
            ),
        )

    def test_rejects_a_urn(self):
        self.assertIsNone(
            parse_file_fragment_ref("urn:x-opensiddur:text:haggadah:haggadah@p")
        )

    def test_rejects_an_external_url(self):
        self.assertIsNone(parse_file_fragment_ref("https://example.com/doc#id"))

    def test_rejects_a_same_file_fragment(self):
        self.assertIsNone(parse_file_fragment_ref("#note-ref-1"))

    def test_rejects_a_path_with_no_fragment(self):
        self.assertIsNone(parse_file_fragment_ref("/project/file"))


class TestResolveFileFragmentRef(unittest.TestCase):
    def test_resolves_an_existing_id(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project_dir = base / "proj1"
            project_dir.mkdir()
            root = etree.Element(f"{{{TEI_NS}}}TEI")
            bibl = etree.SubElement(root, f"{{{TEI_NS}}}bibl")
            bibl.set("{http://www.w3.org/XML/1998/namespace}id", "project_source_bibl")
            etree.ElementTree(root).write(str(project_dir / "index.xml"), encoding="utf-8")

            ref = FileFragmentRef(
                project="proj1", file_stem="index", fragment="project_source_bibl"
            )
            self.assertTrue(resolve_file_fragment_ref(base, ref))

    def test_reports_a_missing_id(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            project_dir = base / "proj1"
            project_dir.mkdir()
            root = etree.Element(f"{{{TEI_NS}}}TEI")
            etree.ElementTree(root).write(str(project_dir / "index.xml"), encoding="utf-8")

            ref = FileFragmentRef(
                project="proj1", file_stem="index", fragment="project_source_bibl"
            )
            self.assertFalse(resolve_file_fragment_ref(base, ref))

    def test_reports_a_missing_file(self):
        with TemporaryDirectory() as td:
            base = Path(td)
            ref = FileFragmentRef(project="proj1", file_stem="index", fragment="anything")
            self.assertFalse(resolve_file_fragment_ref(base, ref))


if __name__ == "__main__":
    unittest.main()
