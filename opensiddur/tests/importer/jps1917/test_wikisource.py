"""Tests for the JPS 1917 downloader.

The shared download loop is covered in ``tests/importer/util/test_wikisource_book.py``;
what is checked here is the wiring particular to this book — where its files land, what
its manifest says, and its CLI. Everything runs against a synthetic two-page book in a
temporary tree, so no test depends on the checked-in sourcetexts data.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.jps1917 import wikisource
from opensiddur.importer.jps1917.wikisource import download_book, main
from opensiddur.importer.util import wikisource_book
from opensiddur.importer.util.pages import (
    jps1917_credits_directory,
    jps1917_data_directory,
    jps1917_text_directory,
)
from opensiddur.importer.util.wikisource import RevisionInfo, WikisourceError

# Page numbers chosen so the derived padding width is the real one (four digits): the
# book's transcribed pages run 7-1158, and downstream readers expect "0007.txt".
FIRST, LAST = 7, 1158
TITLES = {
    FIRST: f"{wikisource.WIKI_NAMESPACE}:{wikisource.BOOK_NAME}/{FIRST}",
    LAST: f"{wikisource.WIKI_NAMESPACE}:{wikisource.BOOK_NAME}/{LAST}",
}

WIKITEXT = "{{verse|1|1}}In the beginning"


class JpsDownloadTestCase(unittest.TestCase):
    """Fixture wiring the downloader to a temporary sourcetexts tree and a fake wiki."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.text_dir = jps1917_text_directory(self.root)
        self.credits_dir = jps1917_credits_directory(self.root)
        self.manifest_file = jps1917_data_directory(self.root) / "manifest.json"

        self.revids = {TITLES[FIRST]: 111, TITLES[LAST]: 222}
        self.contributors = {TITLES[FIRST]: ["Outlier59"], TITLES[LAST]: ["Prosody"]}
        self.content_requests = []

        patcher = patch.multiple(
            wikisource_book,
            list_book_pages=MagicMock(return_value=dict(TITLES)),
            fetch_revisions=MagicMock(side_effect=self.fake_fetch_revisions),
            fetch_contributors=MagicMock(side_effect=self.fake_fetch_contributors),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_fetch_revisions(self, wiki, titles, *, include_content, **kwargs):
        titles = list(titles)
        if include_content:
            self.content_requests.append(titles)
        return {
            title: RevisionInfo(
                revid=self.revids[title],
                timestamp="2022-02-07T05:35:00Z",
                content=WIKITEXT if include_content else None,
            )
            for title in titles
        }

    def fake_fetch_contributors(self, wiki, titles, **kwargs):
        return {title: self.contributors.get(title, []) for title in titles}

    def run_download(self, **kwargs):
        return download_book(
            "example@opensiddur.org",
            self.root,
            wiki=MagicMock(server=wikisource.SERVER),
            **kwargs,
        )

    def read_manifest(self):
        return json.loads(self.manifest_file.read_text(encoding="utf-8"))

    def seed_everything_current(self):
        """Put both pages on disk and in the manifest, exactly as a finished run would."""
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.credits_dir.mkdir(parents=True, exist_ok=True)
        pages = {}
        for number, key in ((FIRST, "0007"), (LAST, "1158")):
            (self.text_dir / f"{key}.txt").write_text(WIKITEXT, encoding="utf-8")
            (self.credits_dir / f"{key}.txt").write_text("Outlier59", encoding="utf-8")
            pages[key] = {"revid": self.revids[TITLES[number]]}
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_file.write_text(
            json.dumps({"pages": pages}), encoding="utf-8"
        )


class TestFirstRun(JpsDownloadTestCase):
    def test_downloads_every_page_when_there_is_no_manifest(self):
        self.run_download()
        self.assertEqual(self.content_requests, [[TITLES[FIRST], TITLES[LAST]]])

    def test_writes_text_and_credits_with_four_digit_names(self):
        self.run_download()
        self.assertEqual(
            sorted(p.name for p in self.text_dir.iterdir()), ["0007.txt", "1158.txt"]
        )
        self.assertEqual(
            sorted(p.name for p in self.credits_dir.iterdir()), ["0007.txt", "1158.txt"]
        )

    def test_writes_the_wikitext_the_wiki_returned(self):
        self.run_download()
        self.assertEqual(
            (self.text_dir / "0007.txt").read_text(encoding="utf-8"), WIKITEXT
        )

    def test_writes_contributors_one_per_line(self):
        self.run_download()
        self.assertEqual(
            (self.credits_dir / "1158.txt").read_text(encoding="utf-8"), "Prosody"
        )

    def test_records_the_book_it_came_from(self):
        manifest = self.run_download()
        self.assertEqual(manifest["source"], wikisource.SERVER)
        self.assertEqual(manifest["book_name"], wikisource.BOOK_NAME)
        self.assertEqual(manifest["namespace"], wikisource.WIKI_NAMESPACE)
        self.assertIn("downloaded_at", manifest)

    def test_records_every_page_in_the_manifest(self):
        self.run_download()
        pages = self.read_manifest()["pages"]
        self.assertEqual(sorted(pages), ["0007", "1158"])
        self.assertEqual(pages["0007"]["revid"], 111)

    def test_refuses_a_book_with_no_transcribed_pages(self):
        wikisource_book.list_book_pages.return_value = {}
        with self.assertRaises(WikisourceError):
            self.run_download()


class TestIncrementalUpdate(JpsDownloadTestCase):
    def test_skips_pages_whose_revision_is_unchanged(self):
        self.seed_everything_current()
        self.revids[TITLES[LAST]] = 999
        self.run_download()
        self.assertEqual(self.content_requests, [[TITLES[LAST]]])

    def test_leaves_an_unchanged_page_untouched_on_disk(self):
        self.seed_everything_current()
        (self.text_dir / "0007.txt").write_text("hand edited", encoding="utf-8")
        self.revids[TITLES[LAST]] = 999
        self.run_download()
        self.assertEqual(
            (self.text_dir / "0007.txt").read_text(encoding="utf-8"), "hand edited"
        )

    def test_downloads_nothing_when_the_whole_book_is_current(self):
        self.seed_everything_current()
        self.run_download()
        self.assertEqual(self.content_requests, [])

    def test_a_no_op_rerun_leaves_the_manifest_untouched(self):
        self.seed_everything_current()
        before = self.manifest_file.read_text(encoding="utf-8")
        self.run_download()
        self.assertEqual(self.manifest_file.read_text(encoding="utf-8"), before)

    def test_refetches_when_a_file_has_gone_missing(self):
        self.seed_everything_current()
        (self.credits_dir / "0007.txt").unlink()
        self.run_download()
        self.assertEqual(self.content_requests, [[TITLES[FIRST]]])

    def test_starts_over_when_the_manifest_is_corrupt(self):
        self.seed_everything_current()
        self.manifest_file.write_text("{not json", encoding="utf-8")
        self.run_download()
        self.assertEqual(self.content_requests, [[TITLES[FIRST], TITLES[LAST]]])


class TestForce(JpsDownloadTestCase):
    def test_refetches_everything_regardless_of_the_manifest(self):
        self.seed_everything_current()
        self.run_download(force=True)
        self.assertEqual(self.content_requests, [[TITLES[FIRST], TITLES[LAST]]])


class TestDryRun(JpsDownloadTestCase):
    def test_writes_nothing(self):
        self.run_download(dry_run=True)
        self.assertFalse(self.text_dir.exists())
        self.assertFalse(self.manifest_file.exists())

    def test_does_not_fetch_content(self):
        self.run_download(dry_run=True)
        self.assertEqual(self.content_requests, [])


class TestCli(unittest.TestCase):
    def test_refuses_to_run_without_a_contact_address(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(wikisource, "download_book") as download:
                with self.assertLogs(wikisource.logger, level="ERROR"):
                    self.assertEqual(main(["--dry-run"]), 1)
        download.assert_not_called()

    def test_passes_the_contact_address_through(self):
        with patch.object(wikisource, "download_book") as download:
            self.assertEqual(
                main(["--contact-email", "someone@opensiddur.org", "--force"]), 0
            )
        self.assertEqual(download.call_args.args[0], "someone@opensiddur.org")
        self.assertTrue(download.call_args.kwargs["force"])
