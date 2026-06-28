import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from opensiddur.importer.feinstein_haggadah import download
from opensiddur.importer.util.pages import (
    feinstein_haggadah_data_directory,
    heidenheim_haggadah_data_directory,
)

MINIMAL_JSON = {
    "post_id": 6207,
    "title": "Haggadah for Pesah",
    "author": "Eve Feinstein",
    "permalink": download.OSP_PERMALINK,
    "content": "<table></table>",
}


class TestDownloadFeinsteinHaggadah(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.sourcetexts_root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _mock_json_response(self) -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.content = json.dumps(MINIMAL_JSON).encode("utf-8")
        return response

    def _mock_xml_response(self) -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.content = b"<tei:TEI/>"
        return response

    @patch("opensiddur.importer.feinstein_haggadah.download.requests.get")
    def test_download_osp_writes_manifest(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = [self._mock_json_response(), self._mock_xml_response()]

        download.download_osp_compilation(self.sourcetexts_root)

        data_dir = feinstein_haggadah_data_directory(self.sourcetexts_root)
        json_path = data_dir / "compilation.json"
        manifest_path = data_dir / "manifest.json"
        metadata_path = data_dir / "metadata.yaml"

        self.assertTrue(json_path.is_file())
        self.assertTrue(manifest_path.is_file())
        self.assertTrue(metadata_path.is_file())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"], "opensiddur.org")
        self.assertEqual(len(manifest["files"]), 3)
        for entry in manifest["files"]:
            self.assertIn("sha256", entry)
            self.assertEqual(len(entry["sha256"]), 64)

    @patch("opensiddur.importer.feinstein_haggadah.download.requests.get")
    def test_dry_run_writes_nothing(self, mock_get: MagicMock) -> None:
        download.download_osp_compilation(self.sourcetexts_root, dry_run=True)
        data_dir = feinstein_haggadah_data_directory(self.sourcetexts_root)
        self.assertFalse(data_dir.exists())
        mock_get.assert_not_called()

    @patch("opensiddur.importer.feinstein_haggadah.download._download_url")
    def test_hebrewbooks_pdf_failure_writes_manifest(self, mock_download: MagicMock) -> None:
        mock_download.side_effect = requests.RequestException("blocked")

        manifest = download.download_hebrewbooks_pdf(self.sourcetexts_root)

        data_dir = heidenheim_haggadah_data_directory(self.sourcetexts_root)
        manifest_path = data_dir / "manifest.json"
        self.assertTrue(manifest_path.is_file())
        self.assertIsNotNone(manifest)
        self.assertFalse(manifest["pdf_downloaded"])

    def test_main_dry_run_exit_code(self) -> None:
        with patch(
            "opensiddur.importer.feinstein_haggadah.download.download_all"
        ) as mock_download_all:
            code = download.main(
                ["--dry-run", "--sourcetexts-root", str(self.sourcetexts_root)]
            )
        self.assertEqual(code, 0)
        mock_download_all.assert_called_once()


if __name__ == "__main__":
    unittest.main()
