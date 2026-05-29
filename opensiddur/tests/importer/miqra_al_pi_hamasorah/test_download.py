import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.miqra_al_pi_hamasorah import download
from opensiddur.importer.util.pages import (
    miqra_al_pi_hamasorah_data_directory,
    miqra_al_pi_hamasorah_sheets_directory,
)

FIXTURE_XLSX = (
    Path(__file__).resolve().parents[2] / "fixtures" / "miqra_minimal.xlsx"
)


class TestDownloadMiqra(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.sourcetexts_root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _mock_response(self) -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.content = FIXTURE_XLSX.read_bytes()
        return response

    @patch("opensiddur.importer.miqra_al_pi_hamasorah.download.requests.get")
    def test_download_writes_tsv_and_manifest(self, mock_get: MagicMock) -> None:
        mock_get.return_value = self._mock_response()

        download.download_miqra(self.sourcetexts_root)

        data_dir = miqra_al_pi_hamasorah_data_directory(self.sourcetexts_root)
        sheets_dir = miqra_al_pi_hamasorah_sheets_directory(self.sourcetexts_root)

        torah_tsv = sheets_dir / "torah.tsv"
        readme_tsv = sheets_dir / "readme.tsv"
        self.assertTrue(torah_tsv.is_file())
        self.assertTrue(readme_tsv.is_file())
        self.assertFalse((sheets_dir / "unknowntab.tsv").exists())

        torah_lines = torah_tsv.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(torah_lines), 2)
        self.assertIn("בְּרֵאשִׁית", torah_lines[1])

        manifest_path = data_dir / "manifest.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["spreadsheet_id"], download.SPREADSHEET_ID)
        slugs = {s["slug"] for s in manifest["sheets"]}
        self.assertIn("torah", slugs)
        self.assertIn("readme", slugs)
        for entry in manifest["sheets"]:
            self.assertIn("sha256", entry)
            self.assertEqual(len(entry["sha256"]), 64)

        xlsx_files = list(data_dir.glob("*.xlsx"))
        self.assertEqual(xlsx_files, [])

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        self.assertEqual(call_kwargs[0][0], download.EXPORT_XLSX_URL)
        self.assertIn("User-Agent", call_kwargs[1]["headers"])

    @patch("opensiddur.importer.miqra_al_pi_hamasorah.download.requests.get")
    def test_dry_run_writes_nothing(self, mock_get: MagicMock) -> None:
        download.download_miqra(self.sourcetexts_root, dry_run=True)

        data_dir = miqra_al_pi_hamasorah_data_directory(self.sourcetexts_root)
        self.assertFalse(data_dir.exists())
        mock_get.assert_not_called()

    @patch("opensiddur.importer.miqra_al_pi_hamasorah.download.logger")
    @patch("opensiddur.importer.miqra_al_pi_hamasorah.download.requests.get")
    def test_unknown_sheet_logs_warning(
        self, mock_get: MagicMock, mock_logger: MagicMock
    ) -> None:
        mock_get.return_value = self._mock_response()
        download.download_miqra(self.sourcetexts_root)

        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if "UnknownTab" in str(c)
        ]
        self.assertEqual(len(warning_calls), 1)

    def test_main_dry_run_exit_code(self) -> None:
        with patch(
            "opensiddur.importer.miqra_al_pi_hamasorah.download.download_miqra"
        ) as mock_download:
            code = download.main(
                ["--dry-run", "--sourcetexts-root", str(self.sourcetexts_root)]
            )
        self.assertEqual(code, 0)
        mock_download.assert_called_once()
        self.assertTrue(mock_download.call_args.kwargs["dry_run"])


if __name__ == "__main__":
    unittest.main()
