"""Tests for the Birnbaum front door.

This module's only job is running the four stages in the order they depend on, so
that is all these tests check: which stages ran, in what order, and with what.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.birnbaum_siddur import download
from opensiddur.importer.birnbaum_siddur.download import main

CONTACT = "tests@opensiddur.invalid"


class DownloadAllTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.calls: list[str] = []

        def record(name, result=None):
            def stage(*args, **kwargs):
                self.calls.append(name)
                return result if result is not None else {}

            return MagicMock(side_effect=stage)

        self.he = MagicMock()
        self.he.download_book = record("he")
        self.en = MagicMock()
        self.en.download_book = record("en")
        self.ia = MagicMock()
        self.ia.download_ia = record("ia")
        self.correspondence = MagicMock()
        self.correspondence.build_correspondence = record("correspondence", {"counts": {}})
        self.correspondence.report = MagicMock(return_value=[])
        self.correspondence.save_correspondence = MagicMock(return_value=self.root / "pages.json")

        patcher = patch.multiple(
            download,
            he_wikisource=self.he,
            en_wikisource=self.en,
            internet_archive=self.ia,
            correspondence_stage=self.correspondence,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, *extra):
        return main(
            ["--sourcetexts-root", str(self.root), "--contact-email", CONTACT, *extra]
        )

    def test_the_table_is_built_last(self):
        # It reads all three layers off disk, so anything else running after it
        # would leave it describing a book that has since changed.
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.calls, ["he", "en", "ia", "correspondence"])

    def test_each_stage_can_be_skipped(self):
        self.assertEqual(self.run_main("--skip-he", "--skip-ia"), 0)
        self.assertEqual(self.calls, ["en", "correspondence"])

    def test_skipping_the_table_leaves_the_downloads(self):
        self.assertEqual(self.run_main("--skip-correspondence"), 0)
        self.assertEqual(self.calls, ["he", "en", "ia"])

    def test_a_dry_run_does_not_build_a_table_over_a_partial_tree(self):
        self.assertEqual(self.run_main("--dry-run"), 0)
        self.assertEqual(self.calls, ["he", "en", "ia"])
        self.correspondence.save_correspondence.assert_not_called()

    def test_archive_only_options_reach_the_archive_stage(self):
        self.assertEqual(self.run_main("--with-djvu", "--fetch-pdf"), 0)
        _, kwargs = self.ia.download_ia.call_args
        self.assertTrue(kwargs["with_djvu"])
        self.assertTrue(kwargs["fetch_pdf"])

    def test_the_contact_address_reaches_every_stage(self):
        self.run_main()
        for stage in (self.he.download_book, self.en.download_book, self.ia.download_ia):
            self.assertEqual(stage.call_args[0][0], CONTACT)

    def test_the_model_is_passed_to_the_archive_only(self):
        # Wikimedia's policy asks for a contact address; the Archive additionally
        # asks AI agents to name their model.
        with patch.dict("os.environ", {"OPENSIDDUR_AGENT_MODEL": "some-model"}):
            self.run_main()
        self.assertEqual(self.ia.download_ia.call_args[1]["agent_model"], "some-model")
        self.assertNotIn("agent_model", self.en.download_book.call_args[1])

    def test_a_real_contact_address_is_required(self):
        with patch.dict("os.environ", {"OPENSIDDUR_CONTACT_EMAIL": ""}):
            self.assertEqual(main(["--sourcetexts-root", str(self.root)]), 1)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
