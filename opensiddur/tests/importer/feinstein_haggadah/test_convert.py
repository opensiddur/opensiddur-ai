import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opensiddur.importer.feinstein_haggadah.convert import convert_all
from opensiddur.importer.feinstein_haggadah.parse_compilation import _clean_html_cell
from opensiddur.importer.feinstein_haggadah.tei_builder import (
    tei_document,
    validate_and_write,
    validate_project_directory,
)
from opensiddur.importer.util.validation import validate

SAMPLE_HTML = """
<table>
<tr>
<td><div class="liturgy">קַדֵּשׁ</div></td>
<td><div class="english"><h3>Sanctification of the Day</h3><p>Kadesh text.</p></div></td>
</tr>
</table>
"""


class TestParseCompilationCleanup(unittest.TestCase):
    def test_clean_html_cell_strips_footnote_jquery(self) -> None:
        raw = (
            "Blessed.[1] Genesis 1:1 "
            "jQuery('#footnote_plugin_tooltip__1_1').tooltip({ tip: 'x' });"
        )
        cleaned = _clean_html_cell(raw)
        self.assertNotIn("jQuery", cleaned)
        self.assertIn("Genesis 1:1", cleaned)


class TestTeiBuilderValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_validate_and_write_rejects_invalid_jlptei(self) -> None:
        invalid = """<tei:TEI xml:lang="he" xmlns:tei="http://www.tei-c.org/ns/1.0">
<tei:text><tei:body><tei:head>bad</tei:head></tei:body></tei:text>
</tei:TEI>"""
        with self.assertRaises(RuntimeError) as ctx:
            validate_and_write(invalid, "bad", self.project_dir)
        self.assertIn("JLPTEI validation failed", str(ctx.exception))

    def test_validate_project_directory_checks_all_files(self) -> None:
        valid = tei_document(
            """<tei:teiHeader xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:fileDesc>
    <tei:titleStmt><tei:title>Test</tei:title></tei:titleStmt>
    <tei:publicationStmt><tei:distributor><tei:ref target="http://opensiddur.org">OSP</tei:ref></tei:distributor></tei:publicationStmt>
    <tei:sourceDesc><tei:bibl><tei:title>Test</tei:title></tei:bibl></tei:sourceDesc>
  </tei:fileDesc>
</tei:teiHeader>""",
            """<tei:body><tei:div><tei:p>ok</tei:p></tei:div></tei:body>""",
            lang="he",
        )
        validate_and_write(valid, "ok", self.project_dir)
        validate_project_directory(self.project_dir)


class TestConvertProducesValidJlptei(unittest.TestCase):
    def test_convert_all_writes_valid_project_files(self) -> None:
        compilation_path = Path("sources/feinstein_haggadah_2009/compilation.json")
        if not compilation_path.is_file():
            self.skipTest("compilation.json not available locally")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = root / "sources"
            feinstein_dir = sources / "feinstein_haggadah_2009"
            feinstein_dir.mkdir(parents=True)
            shutil.copy(compilation_path, feinstein_dir / "compilation.json")

            project_root = root / "project"
            convert_all(sourcetexts_root=sources, project_root=project_root)

            self._assert_psalms_follow_the_1822_print(
                project_root / "heidenheim_haggadah_1822"
            )

            for project in ("heidenheim_haggadah_1822", "feinstein_haggadah_translation_2009"):
                project_dir = project_root / project
                self.assertTrue(project_dir.is_dir())
                xml_files = list(project_dir.glob("*.xml"))
                self.assertGreater(len(xml_files), 10)
                validate_project_directory(project_dir)
                for path in xml_files:
                    is_valid, errors = validate(path)
                    self.assertTrue(is_valid, f"{path.name}: {errors}")

    def _assert_psalms_follow_the_1822_print(self, project_dir: Path) -> None:
        """The psalms the print carries reach the project as transcribed, not as WLC."""
        for slug in ("psalm_113", "psalm_115", "psalm_117", "psalm_136"):
            written = (project_dir / f"{slug}.xml").read_text(encoding="utf-8")
            with self.subTest(slug=slug):
                self.assertIn("<j:divineName>יְיָ</j:divineName>", written)
                self.assertNotIn("יְהֹוָה", written)
                self.assertNotIn("יהוה", written)
                # WLC cites itself as the text source; these no longer come from it.
                self.assertNotIn("text:bible:psalms@wlc", written)

        # Psalm 126 is not in the print and keeps the compilation's text and its WLC citation.
        psalm_126 = (project_dir / "psalm_126.xml").read_text(encoding="utf-8")
        self.assertIn("text:bible:psalms@wlc", psalm_126)
        self.assertNotIn("<j:divineName>", psalm_126)


if __name__ == "__main__":
    unittest.main()
