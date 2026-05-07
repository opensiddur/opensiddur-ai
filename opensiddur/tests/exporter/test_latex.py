"""Tests for the latex.py driver around the reledmac.xslt stylesheet.

The driver is responsible for:

  - extracting license/credit/source metadata from referenced source files,
  - loading the optional ``typography`` section of a settings.yaml,
  - and feeding all of those into the XSLT as parameters.

These tests cover those responsibilities. The actual XSLT output is tested
separately in ``test_reledmac_xslt.py``.
"""

import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import opensiddur.exporter.tex.latex as latex_module
from opensiddur.exporter.settings import PaperType, ParallelLayout, TypographyConfig
from opensiddur.exporter.tex.latex import (
    CreditRecord,
    LicenseRecord,
    credits_to_tex,
    extract_credits,
    extract_licenses,
    extract_sources,
    get_file_references,
    group_credits,
    group_licenses,
    licenses_to_tex,
    load_typography,
    transform_xml_to_tex,
)


class TestExtractLicenses(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def _create(self, project: str, filename: str, content: bytes) -> Path:
        d = self.test_dir / project
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_bytes(content)
        return p

    def test_extract_single_license(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:teiHeader><tei:fileDesc><tei:publicationStmt>
            <tei:availability>
              <tei:licence target="http://example.com/cc">CC0</tei:licence>
            </tei:availability>
          </tei:publicationStmt></tei:fileDesc></tei:teiHeader>
        </root>"""
        f = self._create("p", "a.xml", xml)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            result = extract_licenses([f])
        self.assertEqual(len(result), 1)
        record = next(iter(result.values()))
        self.assertEqual(record.url, "http://example.com/cc")
        self.assertEqual(record.name, "CC0")

    def test_license_without_url_is_skipped(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:licence>Unknown</tei:licence></root>"""
        f = self._create("p", "a.xml", xml)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            result = extract_licenses([f])
        self.assertEqual(len(result), 0)

    def test_invalid_xml_is_skipped(self):
        f = self._create("p", "a.xml", b"not xml")
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            result = extract_licenses([f])
        self.assertEqual(len(result), 0)


class TestGroupLicenses(unittest.TestCase):

    def test_dedupes_by_url(self):
        records = {
            Path("a"): LicenseRecord(url="http://x", name="X"),
            Path("b"): LicenseRecord(url="http://x", name="X"),
            Path("c"): LicenseRecord(url="http://y", name="Y"),
        }
        grouped = group_licenses(records)
        self.assertEqual(len(grouped), 2)
        self.assertEqual({lr.url for lr in grouped}, {"http://x", "http://y"})


class TestLicensesToTex(unittest.TestCase):

    def test_emits_legal_chapter(self):
        out = licenses_to_tex(
            [LicenseRecord(url="http://creativecommons.org/cc", name="CC")]
        )
        self.assertIn(r"\chapter{Legal}", out)
        self.assertIn("CC", out)
        self.assertIn(r"\url{http://creativecommons.org/cc}", out)


class TestExtractCredits(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def _create(self, project: str, filename: str, content: bytes) -> Path:
        d = self.test_dir / project
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_bytes(content)
        return p

    def test_extracts_resp_stmt(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:respStmt>
            <tei:resp key="aut">Author</tei:resp>
            <tei:name ref="urn:x-opensiddur:ns/person">A B</tei:name>
          </tei:respStmt>
        </root>"""
        f = self._create("p", "a.xml", xml)
        result = extract_credits([f])
        credits = result[f]
        self.assertEqual(len(credits), 1)
        self.assertEqual(credits[0].role, "aut")
        self.assertEqual(credits[0].namespace, "ns")
        self.assertEqual(credits[0].contributor, "person")

    def test_skips_resp_without_required_attrs(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:respStmt><tei:resp key="aut">Author</tei:resp></tei:respStmt>
        </root>"""
        f = self._create("p", "a.xml", xml)
        result = extract_credits([f])
        self.assertEqual(result[f], [])


class TestGroupCredits(unittest.TestCase):

    def test_groups_by_role_and_namespace(self):
        c = CreditRecord(
            role="aut",
            resp_text="Author",
            ref="urn:x-opensiddur:ns/p1",
            name_text="P1",
            namespace="ns",
            contributor="p1",
        )
        grouped = group_credits({Path("a"): [c]})
        self.assertIn("aut", grouped)
        self.assertIn("ns", grouped["aut"])
        self.assertEqual(len(grouped["aut"]["ns"]), 1)

    def test_dedupes_by_role_and_ref(self):
        c = CreditRecord(
            role="aut",
            resp_text="Author",
            ref="urn:x-opensiddur:ns/p1",
            name_text="P1",
            namespace="ns",
            contributor="p1",
        )
        grouped = group_credits({Path("a"): [c], Path("b"): [c]})
        self.assertEqual(len(grouped["aut"]["ns"]), 1)


class TestCreditsToTex(unittest.TestCase):

    def test_pluralizes_role_when_multiple_contributors(self):
        c1 = CreditRecord(
            role="aut", resp_text="Author", ref="urn:x:ns/a",
            name_text="A", namespace="ns", contributor="a",
        )
        c2 = CreditRecord(
            role="aut", resp_text="Author", ref="urn:x:ns/b",
            name_text="B", namespace="ns", contributor="b",
        )
        out = credits_to_tex({"aut": {"ns": [c1, c2]}})
        self.assertIn(r"\section{Authors}", out)

    def test_emits_singular_when_one_contributor(self):
        c1 = CreditRecord(
            role="aut", resp_text="Author", ref="urn:x:ns/a",
            name_text="A", namespace="ns", contributor="a",
        )
        out = credits_to_tex({"aut": {"ns": [c1]}})
        self.assertIn(r"\section{Author}", out)
        self.assertNotIn(r"\section{Authors}", out)


class TestExtractSources(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def _create(self, project: str, filename: str, content: bytes) -> Path:
        d = self.test_dir / project
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_bytes(content)
        return p

    def test_emits_filecontents_block_when_bibl_present(self):
        index = b"""<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl><tei:title>T</tei:title><tei:author>A</tei:author></tei:bibl>
          </tei:listBibl>
        </root>"""
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, postamble = extract_sources([doc])
        self.assertIn(r"\begin{filecontents*}{job.bib}", preamble)
        self.assertIn(r"\addbibresource{job.bib}", preamble)
        self.assertIn(r"\printbibliography", postamble)

    def test_returns_empty_strings_when_no_bibl(self):
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", b"<root/>")
        preamble, postamble = extract_sources([doc])
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_dedupes_when_multiple_files_share_index(self):
        index = b"""<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl><tei:title>T</tei:title><tei:author>A</tei:author></tei:bibl>
          </tei:listBibl>
        </root>"""
        f1 = self._create("p", "doc1.xml", b"<root/>")
        f2 = self._create("p", "doc2.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([f1, f2])
        self.assertEqual(preamble.count("@"), 1)


class TestGetFileReferences(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)
        self.project_dir = self.test_dir / "project"
        self.project_dir.mkdir()

    def _create(self, filename: str, content: bytes) -> Path:
        p = self.project_dir / filename
        p.write_bytes(content)
        return p

    def test_collects_main_and_index(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                       xmlns:p="http://jewishliturgy.org/ns/processing"
                       p:project="proj" p:file_name="main.xml"/>"""
        f = self._create("main.xml", xml)
        result = get_file_references(f, self.project_dir)
        self.assertIn(self.project_dir / "proj" / "main.xml", result)
        self.assertIn(self.project_dir / "proj" / "index.xml", result)

    def test_collects_transcluded_files(self):
        xml = b"""<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                       xmlns:p="http://jewishliturgy.org/ns/processing"
                       p:project="a" p:file_name="main.xml">
          <p:transclude p:project="b" p:file_name="x.xml"/>
        </root>"""
        f = self._create("main.xml", xml)
        result = get_file_references(f, self.project_dir)
        self.assertIn(self.project_dir / "a" / "main.xml", result)
        self.assertIn(self.project_dir / "b" / "x.xml", result)
        self.assertIn(self.project_dir / "a" / "index.xml", result)
        self.assertIn(self.project_dir / "b" / "index.xml", result)


class TestLoadTypography(unittest.TestCase):
    """Loading the optional `typography` section of a settings.yaml.

    Defaults must apply when the file is missing, the section is missing,
    or the file is malformed. The PDF stage must not depend on the full
    SettingsYaml passing validation — the compiler stage already validates
    the rest, and the PDF stage can run without project paths existing on
    disk (e.g. against pre-compiled XML).
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def test_defaults_when_settings_file_is_none(self):
        cfg = load_typography(None)
        self.assertEqual(cfg, TypographyConfig())

    def test_reads_typography_section(self):
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
priority:
  transclusion: [p]
  instructions: []
typography:
  hebrew_font: Ezra SIL
  latin_font: TeX Gyre Pagella
  layout: pairs
  paper: letterpaper
  fontsize: 12pt
"""
        )
        cfg = load_typography(settings_path)
        self.assertEqual(cfg.hebrew_font, "Ezra SIL")
        self.assertEqual(cfg.latin_font, "TeX Gyre Pagella")
        self.assertEqual(cfg.layout, ParallelLayout.PAIRS)
        self.assertEqual(cfg.paper, PaperType.LETTERPAPER)
        self.assertEqual(cfg.fontsize, "12pt")

    def test_defaults_when_typography_section_missing(self):
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
priority:
  transclusion: [p]
  instructions: []
"""
        )
        cfg = load_typography(settings_path)
        self.assertEqual(cfg, TypographyConfig())

    def test_returns_defaults_on_invalid_file(self):
        f = self.test_dir / "broken.yaml"
        f.write_text(":\n: not yaml")
        cfg = load_typography(f)
        self.assertEqual(cfg, TypographyConfig())

    def test_settings_with_unknown_projects_does_not_block_typography(self):
        """Project-list validation in the broader settings file (which the
        compiler does) must not interfere with reading typography here."""
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
priority:
  transclusion: [a-project-that-does-not-exist]
typography:
  hebrew_font: Some Font
"""
        )
        cfg = load_typography(settings_path)
        self.assertEqual(cfg.hebrew_font, "Some Font")


class TestTransformXmlToTex(unittest.TestCase):
    """End-to-end driver test: confirms the typography parameters reach
    the XSLT and that integration with license/credit/source extraction
    works."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def _create(self, project: str, filename: str, content: bytes) -> Path:
        d = self.test_dir / project
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_bytes(content)
        return p

    def test_basic_transform_produces_lualatex_document(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Hello.
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f)

        self.assertIn(r"\documentclass", out)
        self.assertIn(r"\begin{document}", out)
        self.assertIn(r"\end{document}", out)
        self.assertIn(r"\usepackage{reledmac}", out)
        # Hebrew font must be declared via fontspec for Hebrew script support.
        self.assertIn(r"\newfontfamily\hebrewfont", out)

    def test_typography_object_is_threaded_into_preamble(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        typography = TypographyConfig(
            hebrew_font="Ezra SIL",
            latin_font="TeX Gyre Pagella",
            layout=ParallelLayout.PAIRS,
            paper="letterpaper",
            fontsize="12pt",
        )

        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)

        self.assertIn(r"\documentclass[12pt,letterpaper]{book}", out)
        self.assertIn("Ezra SIL", out)
        self.assertIn("TeX Gyre Pagella", out)

    def test_layout_pairs_propagates_to_parallel_block(self):
        xml = """<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p>שלום</tei:p></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p>Hi</tei:p></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>""".encode("utf-8")
        f = self._create("p", "input.xml", xml)
        typography = TypographyConfig(layout=ParallelLayout.PAIRS)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\Columns", out)

    def test_integrates_licenses_into_postamble(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing"
                 p:project="p" p:file_name="input.xml">
          <tei:teiHeader><tei:fileDesc><tei:publicationStmt>
            <tei:availability>
              <tei:licence target="http://example.com/lic">My License</tei:licence>
            </tei:availability>
          </tei:publicationStmt></tei:fileDesc></tei:teiHeader>
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f)
        self.assertIn(r"\chapter{Legal}", out)
        self.assertIn("My License", out)


if __name__ == "__main__":
    unittest.main()
