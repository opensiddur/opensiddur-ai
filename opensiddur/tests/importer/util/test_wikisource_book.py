"""Tests for the shared scan-page download loop.

Everything here runs against a synthetic two-page book in a temporary directory: no
network, no checked-in source data, so nothing depends on what Wikisource says today.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.util import wikisource_book
from opensiddur.importer.util.wikisource import RevisionInfo, WikisourceError
from opensiddur.importer.util.wikisource_book import (
    ScanPageLayout,
    download_scan_pages,
    load_manifest,
    needs_download,
    page_key,
    save_manifest,
    sha256_text,
)

BOOK = "Synthetic Book.djvu"

# Page numbers chosen so the derived padding width is three digits, and so the two
# pages do not share one: a book numbered 7-815 pads to "007" and "815".
FIRST, LAST = 7, 815
TITLES = {FIRST: f"Page:{BOOK}/{FIRST}", LAST: f"Page:{BOOK}/{LAST}"}
KEYS = {FIRST: "007", LAST: "815"}

WIKITEXT = "fetched wikitext"


class ScanDownloadTestCase(unittest.TestCase):
    """Fixture wiring the shared loop to a temporary tree and a fake wiki."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "book"
        self.layout = ScanPageLayout(
            data_dir=self.data_dir,
            text_dir=self.data_dir / "text",
            credits_dir=self.data_dir / "credits",
        )
        self.manifest_file = self.data_dir / "manifest.json"

        self.revids = {TITLES[FIRST]: 111, TITLES[LAST]: 222}
        self.contributors = {TITLES[FIRST]: ["Dovi"], TITLES[LAST]: ["Dovi", "Nahum"]}
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
        return download_scan_pages(
            MagicMock(server="en.wikisource.org"), BOOK, self.layout, **kwargs
        )

    def seed_page(self, page_num, revid, text="existing", credits="Dovi"):
        """Write a page to disk and return the manifest entry that marks it current."""
        key = KEYS[page_num]
        self.layout.text_dir.mkdir(parents=True, exist_ok=True)
        self.layout.credits_dir.mkdir(parents=True, exist_ok=True)
        (self.layout.text_dir / f"{key}.txt").write_text(text, encoding="utf-8")
        (self.layout.credits_dir / f"{key}.txt").write_text(credits, encoding="utf-8")
        return {key: {"revid": revid, "timestamp": "2022-02-07T05:35:00Z"}}


class TestFirstRun(ScanDownloadTestCase):
    def test_downloads_every_page_when_the_manifest_is_empty(self):
        result = self.run_download()
        self.assertEqual(result.written, 2)
        self.assertEqual(result.stale, [FIRST, LAST])

    def test_pads_filenames_to_the_width_of_the_highest_page_number(self):
        self.run_download()
        self.assertEqual(
            sorted(p.name for p in self.layout.text_dir.iterdir()),
            ["007.txt", "815.txt"],
        )

    def test_an_explicit_width_overrides_the_derived_one(self):
        result = self.run_download(digits=4)
        self.assertEqual(result.digits, 4)
        self.assertTrue((self.layout.text_dir / "0007.txt").is_file())

    def test_writes_the_wikitext_the_wiki_returned(self):
        self.run_download()
        self.assertEqual(
            (self.layout.text_dir / "007.txt").read_text(encoding="utf-8"), WIKITEXT
        )

    def test_writes_contributors_one_per_line(self):
        self.run_download()
        self.assertEqual(
            (self.layout.credits_dir / "815.txt").read_text(encoding="utf-8"),
            "Dovi\nNahum",
        )

    def test_records_every_page_with_its_revision_and_hashes(self):
        result = self.run_download()
        self.assertEqual(sorted(result.pages), ["007", "815"])
        entry = result.pages["007"]
        self.assertEqual(entry["revid"], 111)
        self.assertEqual(entry["text_sha256"], sha256_text(WIKITEXT))
        self.assertEqual(entry["credits_sha256"], sha256_text("Dovi"))

    def test_refuses_a_book_with_no_transcribed_pages(self):
        wikisource_book.list_book_pages.return_value = {}
        with self.assertRaises(WikisourceError):
            self.run_download()

    def test_skips_a_page_the_wiki_reports_no_revision_for(self):
        wikisource_book.fetch_revisions.side_effect = (
            lambda wiki, titles, **kwargs: {}
        )
        result = self.run_download()
        self.assertEqual(result.stale, [])
        self.assertEqual(result.written, 0)


class TestIncrementalUpdate(ScanDownloadTestCase):
    def test_skips_pages_whose_revision_is_unchanged(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        result = self.run_download(manifest_pages=recorded)
        self.assertEqual(result.stale, [LAST])
        self.assertEqual(self.content_requests, [[TITLES[LAST]]])

    def test_leaves_an_unchanged_page_untouched_on_disk(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        self.run_download(manifest_pages=recorded)
        self.assertEqual(
            (self.layout.text_dir / "007.txt").read_text(encoding="utf-8"), "existing"
        )

    def test_keeps_the_old_entry_and_records_the_new_one(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        result = self.run_download(manifest_pages=recorded)
        self.assertEqual(sorted(result.pages), ["007", "815"])
        self.assertEqual(result.pages["007"], recorded["007"])

    def test_refetches_a_page_whose_revision_moved_on(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]] - 1)
        result = self.run_download(manifest_pages=recorded)
        self.assertIn(FIRST, result.stale)

    def test_refetches_when_a_file_has_gone_missing(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        (self.layout.credits_dir / "007.txt").unlink()
        result = self.run_download(manifest_pages=recorded)
        self.assertIn(FIRST, result.stale)

    def test_downloads_nothing_when_the_whole_book_is_current(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        recorded.update(self.seed_page(LAST, revid=self.revids[TITLES[LAST]]))
        result = self.run_download(manifest_pages=recorded)
        self.assertEqual(result.stale, [])
        self.assertEqual(result.written, 0)
        self.assertEqual(self.content_requests, [])

    def test_does_not_mutate_the_manifest_it_was_given(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        self.run_download(manifest_pages=recorded)
        self.assertEqual(sorted(recorded), ["007"])


class TestForce(ScanDownloadTestCase):
    def test_refetches_everything_regardless_of_the_manifest(self):
        recorded = self.seed_page(FIRST, revid=self.revids[TITLES[FIRST]])
        recorded.update(self.seed_page(LAST, revid=self.revids[TITLES[LAST]]))
        result = self.run_download(manifest_pages=recorded, force=True)
        self.assertEqual(result.stale, [FIRST, LAST])
        self.assertEqual(result.written, 2)

    def test_starts_the_manifest_over(self):
        recorded = {"999": {"revid": 1}}
        result = self.run_download(manifest_pages=recorded, force=True)
        self.assertEqual(sorted(result.pages), ["007", "815"])


class TestDryRun(ScanDownloadTestCase):
    def test_writes_nothing(self):
        result = self.run_download(dry_run=True)
        self.assertEqual(result.written, 0)
        self.assertFalse(self.layout.text_dir.exists())

    def test_still_reports_what_would_be_downloaded(self):
        result = self.run_download(dry_run=True)
        self.assertEqual(result.stale, [FIRST, LAST])

    def test_does_not_fetch_content(self):
        self.run_download(dry_run=True)
        self.assertEqual(self.content_requests, [])


class TestManifestFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = Path(self._tmp.name) / "book"

    def test_a_missing_manifest_reads_as_empty(self):
        self.assertEqual(load_manifest(self.data_dir), {})

    def test_round_trips_what_was_saved(self):
        save_manifest({"pages": {"007": {"revid": 111}}}, self.data_dir)
        self.assertEqual(load_manifest(self.data_dir)["pages"]["007"]["revid"], 111)

    def test_starts_over_when_the_manifest_is_corrupt(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "manifest.json").write_text("{not json", encoding="utf-8")
        with self.assertLogs(wikisource_book.logger, level="WARNING"):
            self.assertEqual(load_manifest(self.data_dir), {})

    def test_writes_readable_utf8_json(self):
        save_manifest({"book_name": "ספר"}, self.data_dir)
        raw = (self.data_dir / "manifest.json").read_text(encoding="utf-8")
        self.assertIn("ספר", raw)
        self.assertEqual(json.loads(raw)["book_name"], "ספר")


class TestHelpers(unittest.TestCase):
    def test_page_key_pads_to_the_requested_width(self):
        self.assertEqual(page_key(7, 4), "0007")

    def test_page_key_does_not_truncate_a_longer_number(self):
        self.assertEqual(page_key(1158, 3), "1158")

    def test_needs_download_is_true_for_an_unknown_page(self):
        self.assertTrue(needs_download("007", 111, {}, Path("/nonexistent"), Path("/nonexistent")))
