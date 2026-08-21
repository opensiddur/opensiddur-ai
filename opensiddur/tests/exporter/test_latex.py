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

from pydantic import ValidationError

import opensiddur.exporter.tex.latex as latex_module
from opensiddur.exporter import typography as typography_module
from opensiddur.exporter.typography import PaperType, ParallelLayout, TypographyConfig
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


def _no_fontconfig():
    """Mock out the installed-font lookup.

    The settings models check a font chain a settings file names against
    fontconfig. Whether the machine running the tests has Ezra SIL is not what
    any test here is about, and a test that turned on it would fail for reasons
    that have nothing to do with the code.
    """
    return patch.object(
        typography_module, "_installed_font_families", return_value=None
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
        self.assertIn(r"\section*{Legal}", out)
        self.assertIn("CC", out)
        self.assertIn(r"\url{http://creativecommons.org/cc}", out)

    def test_no_licences_emits_nothing(self):
        """An itemize with no items is a LaTeX error and kills the run before any PDF.

        A document can genuinely have no licences to list — one built entirely of public
        domain text, or compiled without annotations.
        """
        self.assertEqual(licenses_to_tex([]), "")


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
        self.assertIn(r"\subsection*{Authors}", out)

    def test_emits_singular_when_one_contributor(self):
        c1 = CreditRecord(
            role="aut", resp_text="Author", ref="urn:x:ns/a",
            name_text="A", namespace="ns", contributor="a",
        )
        out = credits_to_tex({"aut": {"ns": [c1]}})
        self.assertIn(r"\subsection*{Author}", out)
        self.assertNotIn(r"\subsection*{Authors}", out)


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

    def test_bibtex_wraps_hebrew_fields_in_texthebrew(self):
        index = """<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl>
              <tei:title xml:lang="he">מקרא על פי המסורה</tei:title>
              <tei:editor>Avi Kadish</tei:editor>
            </tei:bibl>
          </tei:listBibl>
        </root>""".encode("utf-8")
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([doc])
        self.assertIn(r"title = {\texthebrew{מקרא על פי המסורה}}", preamble)

    def test_bibtex_leaves_latin_fields_unwrapped_under_hebrew_lang(self):
        """Latin content inheriting xml:lang="he" must not get \\texthebrew.

        The wrapper sets \\textdir TRT, which renders Latin text reversed.
        """
        index = """<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:listBibl>
            <tei:bibl>
              <tei:title>Page-break reference facsimile</tei:title>
              <tei:edition>First edition (Yaari 447)</tei:edition>
              <tei:publisher>Wolf Heidenheim</tei:publisher>
              <tei:author>Meir Halevi Heidenheim</tei:author>
            </tei:bibl>
          </tei:listBibl>
        </root>""".encode("utf-8")
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([doc])
        self.assertNotIn(r"\texthebrew", preamble)
        self.assertIn("title = {Page-break reference facsimile}", preamble)
        self.assertIn("edition = {First edition (Yaari 447)}", preamble)
        self.assertIn("publisher = {Wolf Heidenheim}", preamble)
        self.assertIn("author = {Meir Halevi Heidenheim}", preamble)

    def test_bibtex_wraps_hebrew_runs_inside_english_text(self):
        index = """<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl>
              <tei:title>Notes</tei:title>
              <tei:note xml:lang="en">The print reads לשנה הבאה בירושלים then נרצה.</tei:note>
            </tei:bibl>
          </tei:listBibl>
        </root>""".encode("utf-8")
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([doc])
        self.assertIn(r"\texthebrew{לשנה הבאה בירושלים}", preamble)
        self.assertIn(r"\texthebrew{נרצה}", preamble)
        self.assertIn("The print reads ", preamble)

    def test_bibtex_escapes_tex_special_characters(self):
        """Unescaped specials abort the LaTeX run at \\printbibliography.

        Project slugs carry underscores, which TeX reads as math subscripts:
        "Missing $ inserted" with no PDF produced.
        """
        index = """<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl>
              <tei:title>Published as heidenheim_haggadah_1822</tei:title>
              <tei:note xml:lang="en">100% of A &amp; B; #3; a~b; x^2; cost $5</tei:note>
            </tei:bibl>
          </tei:listBibl>
        </root>""".encode("utf-8")
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([doc])
        self.assertIn(r"title = {Published as heidenheim\_haggadah\_1822}", preamble)
        self.assertIn(r"100\% of A \& B", preamble)
        self.assertIn(r"\#3", preamble)
        self.assertIn(r"a\textasciitilde{}b", preamble)
        self.assertIn(r"x\textasciicircum{}2", preamble)
        self.assertIn(r"cost \$5", preamble)

    def test_bibtex_escape_does_not_touch_its_own_wrapper_braces(self):
        """The \\texthebrew wrapper and escape output must not be re-escaped."""
        index = """<?xml version="1.0"?>
        <root xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:listBibl>
            <tei:bibl><tei:title xml:lang="he">הגדה</tei:title></tei:bibl>
          </tei:listBibl>
        </root>""".encode("utf-8")
        doc = self._create("p", "doc.xml", b"<root/>")
        self._create("p", "index.xml", index)
        preamble, _ = extract_sources([doc])
        self.assertIn(r"title = {\texthebrew{הגדה}}", preamble)
        self.assertNotIn(r"\textbackslash", preamble)
        self.assertNotIn(r"\{\}", preamble)


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
  fonts:
    hebrew: [Ezra SIL, FreeSerif]
    latin: TeX Gyre Pagella
  parallel:
    layout: pairs
  page:
    paper: letterpaper
    base_font_size: 12pt
  table_of_contents:
    enabled: true
    depth: 2
"""
        )
        with _no_fontconfig():
            cfg = load_typography(settings_path)
        self.assertEqual(cfg.fonts["hebrew"].names, ["Ezra SIL", "FreeSerif"])
        self.assertEqual(cfg.fonts["latin"].names, ["TeX Gyre Pagella"])
        self.assertEqual(cfg.parallel.layout, ParallelLayout.PAIRS)
        self.assertEqual(cfg.page.paper, PaperType.LETTERPAPER)
        self.assertEqual(cfg.page.base_font_size, "12pt")
        self.assertTrue(cfg.table_of_contents.enabled)
        self.assertEqual(cfg.table_of_contents.depth, 2)

    def test_table_of_contents_defaults_to_disabled(self):
        cfg = TypographyConfig()
        self.assertFalse(cfg.table_of_contents.enabled)
        self.assertEqual(cfg.table_of_contents.depth, 4)

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

    def test_reads_running_head_settings(self):
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
typography:
  page_header:
    odd:
      left: "{book-title}"
      right: {text: "{page}", language: en}
  page_footer:
    all:
      center: "{page}"
"""
        )
        cfg = load_typography(settings_path)
        self.assertEqual(cfg.page_header.odd.left.text, "{book-title}")
        self.assertEqual(cfg.page_header.odd.right.language, "en")
        self.assertIsNone(cfg.page_header.even)
        self.assertEqual(cfg.page_footer.all.center.text, "{page}")

    def test_invalid_typography_is_an_error_not_a_silent_default(self):
        """Substituting defaults for a mistyped running-head code would produce a
        PDF missing what was asked for, explained only by a warning on stderr."""
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
typography:
  page_header:
    all:
      left: "{no-such-code}"
"""
        )
        with self.assertRaises(ValidationError) as ctx:
            load_typography(settings_path)
        self.assertIn("Unknown header/footer code", str(ctx.exception))

    def test_all_combined_with_odd_is_an_error(self):
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
typography:
  page_footer:
    all:
      center: "{page}"
    odd:
      left: "{page}"
"""
        )
        with self.assertRaises(ValidationError):
            load_typography(settings_path)

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
  page:
    paper: a5paper
"""
        )
        cfg = load_typography(settings_path)
        self.assertEqual(cfg.page.paper, PaperType.A5PAPER)


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
        with _no_fontconfig():
            typography = TypographyConfig.model_validate(
                {
                    "fonts": {"hebrew": ["Ezra SIL", "FreeSerif"], "latin": "FreeSerif"},
                    "parallel": {"layout": "pairs"},
                    "page": {"paper": "letterpaper", "base_font_size": "12pt"},
                }
            )

            with patch.object(latex_module, "projects_source_root", self.test_dir):
                out = transform_xml_to_tex(f, typography=typography)

        self.assertIn(r"\documentclass[12pt,letterpaper]{book}", out)
        self.assertIn(r"\renewfontfamily\hebrewfont", out)
        self.assertIn(r"\setmainfont{FreeSerif}", out)

    def test_a_settings_file_reaches_the_emitted_tex(self):
        """The whole path, YAML to TeX: a settings file that names paper,
        margins, a heading size and line numbers has to show up in the
        document, and nothing it did not name may."""
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text(
            """
typography:
  page:
    paper: a5paper
    base_font_size: 10pt
    sides: one
    margins: {top: 2cm, inner: 25mm}
  paragraphs:
    line_spacing: 1.4
  styles:
    heading1: {size: small, weight: normal}
  line_numbers:
    enabled: false
"""
        )

        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, settings_file=settings_path)

        self.assertIn(r"\documentclass[10pt,a5paper,oneside]{book}", out)
        self.assertIn("top=2cm", out)
        self.assertIn("left=25mm", out)   # one-sided, so inner is the left margin
        self.assertIn(r"\linespread{1.4}", out)
        self.assertIn(r"\renewcommand{\OSheadA}", out)
        self.assertIn(r"\numberlinefalse", out)
        # Nothing the file did not ask for.
        self.assertNotIn(r"\renewcommand{\OSheadB}", out)
        self.assertNotIn("bottom=", out)

    def test_an_invalid_settings_file_fails_before_anything_is_rendered(self):
        """And says which setting is wrong. The blanket handler around the
        transform would flatten the message to one line, so validation has to
        happen outside it."""
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        settings_path = self.test_dir / "settings.yaml"
        settings_path.write_text("typography:\n  page:\n    paper: tabloid\n")

        with patch.object(latex_module, "projects_source_root", self.test_dir):
            with self.assertRaises(ValidationError) as caught:
                transform_xml_to_tex(f, settings_file=settings_path)
        self.assertIn("paper", str(caught.exception))

    def test_running_heads_are_built_into_the_page_style_preamble(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        typography = TypographyConfig.model_validate(
            {
                "page_header": {"odd": {"left": "{book-title}"}},
                "page_footer": {"all": {"center": "{page}"}},
            }
        )

        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)

        self.assertIn(r"\usepackage{fancyhdr}", out)
        self.assertIn(r"\fancyhead[LO]{", out)
        self.assertIn(r"\fancyfoot[C]{", out)

    def test_no_running_heads_configured_emits_no_page_style(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=TypographyConfig())
        self.assertNotIn("fancyhdr", out)

    def test_document_language_fills_in_for_slots_that_declare_none(self):
        xml = """<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>""".encode()
        f = self._create("p", "input.xml", xml)
        typography = TypographyConfig.model_validate(
            {"page_header": {"all": {"left": "{book-title}"}}}
        )
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)
        self.assertIn(r"\fancyhead[L]{{\textdir TRT\selectlanguage{hebrew} ", out)

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
        typography = TypographyConfig.model_validate({"parallel": {"layout": "pairs"}})
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\Columns", out)

    def test_table_of_contents_setting_is_threaded_into_xslt_params(self):
        xml = b"""<?xml version="1.0"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>x</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        f = self._create("p", "input.xml", xml)
        typography = TypographyConfig(
            table_of_contents={"enabled": True, "depth": 2}
        )
        with patch.object(latex_module, "projects_source_root", self.test_dir):
            out = transform_xml_to_tex(f, typography=typography)
        self.assertIn(r"\tableofcontents", out)
        self.assertIn(r"\setcounter{tocdepth}{2}", out)

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
        self.assertIn(r"\section*{Metadata}", out)
        self.assertIn(r"\section*{Legal}", out)
        self.assertIn("My License", out)


if __name__ == "__main__":
    unittest.main()
