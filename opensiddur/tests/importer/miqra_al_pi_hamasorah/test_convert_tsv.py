import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile


from opensiddur.importer.miqra_al_pi_hamasorah.convert_tsv import (
    _extract_chapter_verse_numbers,
    main,
)


class TestMiqraConvertTsv(unittest.TestCase):
    @patch("opensiddur.importer.miqra_al_pi_hamasorah.convert_tsv.validate")
    def test_only_book_writes_output(self, mock_validate):
        mock_validate.return_value = (True, [])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sourcetexts_root = tmp_path / "sources"
            sheets_dir = sourcetexts_root / "miqra_al_pi_hamasorah" / "sheets"
            sheets_dir.mkdir(parents=True, exist_ok=True)

            # Minimal README (front matter)
            (sheets_dir / "readme.tsv").write_text(
                "License\tCC-BY-SA 4.0\nAttribution\tHebrew Wikisource\n",
                encoding="utf-8",
            )

            # Minimal Torah TSV: header + one data row for Genesis 1
            (sheets_dir / "torah.tsv").write_text(
                "\t".join(["Page key", "Row id", "Nav", "Scaffold", "Text"])
                + "\n"
                + "\t".join(
                    [
                        "ספר בראשית/א",
                        "א",
                        "",
                        "{{מ:פסוק|בראשית|1|1}}",
                        '{{נוסח|{{מ:אות-ג|בְּ}}רֵאשִׁ֖ית|2=test note}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            project_dir = tmp_path / "project"
            rc = main(
                [
                    "--sourcetexts-root",
                    str(sourcetexts_root),
                    "--project-dir",
                    str(project_dir),
                    "--only-book",
                    "genesis",
                ]
            )
            self.assertEqual(rc, 0)

            genesis_xml = project_dir / "genesis.xml"
            self.assertTrue(genesis_xml.exists())
            xml = genesis_xml.read_text(encoding="utf-8")
            self.assertIn("<tei:TEI", xml)
            self.assertIn('unit="verse"', xml)
            self.assertIn('n="1"', xml)
            self.assertIn("urn:x-opensiddur:text:bible:genesis/1/1", xml)
            self.assertIn("<tei:ab>", xml)
            self.assertIn('<tei:head xml:lang="en">', xml)
            self.assertIn("Genesis", xml)
            self.assertIn('rend="large"', xml)
            self.assertIn("בְּ", xml)
            self.assertIn("tei:standOff", xml)
            self.assertIn("test note", xml)

    def test_special_tsv_row_does_not_produce_invalid_urn_segments(self):
        # special.tsv uses a 2-column schema; must not be merged into book output.
        ch, v = _extract_chapter_verse_numbers(
            "ספר שמות/טו תתת",
            "<noinclude>{{#קטע:שירת הים/צורת השיר|צורת-השיר}}{{מ:טעמי",
            "",
        )
        self.assertEqual(ch, "")
        self.assertEqual(v, "")

    @patch("opensiddur.importer.miqra_al_pi_hamasorah.convert_tsv.validate")
    def test_special_tsv_not_merged_into_book(self, mock_validate):
        mock_validate.return_value = (True, [])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sourcetexts_root = tmp_path / "sources"
            sheets_dir = sourcetexts_root / "miqra_al_pi_hamasorah" / "sheets"
            sheets_dir.mkdir(parents=True, exist_ok=True)

            (sheets_dir / "torah.tsv").write_text(
                "\t".join(["Page key", "Row id", "Nav", "Scaffold", "Text"])
                + "\n"
                + "\t".join(
                    [
                        "ספר שמות/טו",
                        "א",
                        "",
                        "{{מ:פסוק|שמות|15|1}}",
                        "שירה",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (sheets_dir / "special.tsv").write_text(
                "ספר שמות/טו תתת\t{{#קטע:שירת הים/צורת השיר|צורת-השיר}}{{מ:טעמי\n",
                encoding="utf-8",
            )

            project_dir = tmp_path / "project"
            main(
                [
                    "--sourcetexts-root",
                    str(sourcetexts_root),
                    "--project-dir",
                    str(project_dir),
                    "--only-book",
                    "exodus",
                ]
            )
            xml = (project_dir / "exodus.xml").read_text(encoding="utf-8")
            self.assertIn("urn:x-opensiddur:text:bible:exodus/15/1", xml)
            self.assertNotIn("צורת-השיר", xml)
            self.assertNotIn("השיר|", xml)


if __name__ == "__main__":
    unittest.main()

