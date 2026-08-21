import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.birnbaum_siddur import wikisource
from opensiddur.importer.birnbaum_siddur.wikisource import download_book, main
from opensiddur.importer.util.pages import (
    birnbaum_siddur_credits_directory,
    birnbaum_siddur_data_directory,
    birnbaum_siddur_text_directory,
)
from opensiddur.importer.util.wikisource import RevisionInfo, WikisourceError

# Page numbers chosen so the zero-padding width is the real one (three digits).
FIRST, LAST = 1, 815
TITLES = {
    FIRST: f"{wikisource.WIKI_NAMESPACE}:{wikisource.BOOK_NAME}/{FIRST}",
    LAST: f"{wikisource.WIKI_NAMESPACE}:{wikisource.BOOK_NAME}/{LAST}",
}


class BirnbaumDownloadTestCase(unittest.TestCase):
    """Fixture wiring the downloader to a temporary sourcetexts tree and a fake wiki."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.text_dir = birnbaum_siddur_text_directory(self.root)
        self.credits_dir = birnbaum_siddur_credits_directory(self.root)
        self.manifest_file = birnbaum_siddur_data_directory(self.root) / "manifest.json"

        # Latest revision id per title, as the wiki would report it.
        self.revids = {TITLES[FIRST]: 111, TITLES[LAST]: 222}
        self.contributors = {TITLES[FIRST]: ["Dovi"], TITLES[LAST]: ["Dovi", "Nahum"]}

        self.content_requests = []
        self.contributor_requests = []

        patcher = patch.multiple(
            wikisource,
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
                content=f"wikitext for {title}" if include_content else None,
            )
            for title in titles
        }

    def fake_fetch_contributors(self, wiki, titles, **kwargs):
        titles = list(titles)
        self.contributor_requests.append(titles)
        return {title: self.contributors[title] for title in titles}

    def run_download(self, **kwargs):
        return download_book(
            "example@opensiddur.org",
            self.root,
            wiki=MagicMock(server=wikisource.SERVER),
            **kwargs,
        )

    def seed_page(self, page_num, key, revid, text="existing", credits="Dovi"):
        """Write a page to disk and record it in the manifest as already current."""
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.credits_dir.mkdir(parents=True, exist_ok=True)
        (self.text_dir / f"{key}.txt").write_text(text, encoding="utf-8")
        (self.credits_dir / f"{key}.txt").write_text(credits, encoding="utf-8")
        manifest = {
            "source": wikisource.SERVER,
            "book_name": wikisource.BOOK_NAME,
            "namespace": wikisource.WIKI_NAMESPACE,
            "downloaded_at": "2022-02-07T05:35:00Z",
            "pages": {key: {"revid": revid, "timestamp": "2022-02-07T05:35:00Z"}},
        }
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    def read_manifest(self):
        return json.loads(self.manifest_file.read_text(encoding="utf-8"))


class TestFirstRun(BirnbaumDownloadTestCase):
    def test_downloads_every_page_when_there_is_no_manifest(self):
        self.run_download()

        self.assertEqual(sorted(self.content_requests[0]), sorted(TITLES.values()))

    def test_writes_text_and_credits_with_three_digit_names(self):
        self.run_download()

        self.assertEqual(
            sorted(p.name for p in self.text_dir.iterdir()), ["001.txt", "815.txt"]
        )
        self.assertEqual(
            (self.text_dir / "815.txt").read_text(encoding="utf-8"),
            f"wikitext for {TITLES[LAST]}",
        )

    def test_writes_contributors_one_per_line(self):
        self.run_download()

        self.assertEqual(
            (self.credits_dir / "815.txt").read_text(encoding="utf-8"), "Dovi\nNahum"
        )

    def test_records_every_page_in_the_manifest(self):
        self.run_download()

        manifest = self.read_manifest()
        self.assertEqual(manifest["pages"]["001"]["revid"], 111)
        self.assertEqual(manifest["pages"]["815"]["revid"], 222)
        self.assertEqual(manifest["book_name"], wikisource.BOOK_NAME)

    def test_refuses_a_book_with_no_transcribed_pages(self):
        wikisource.list_book_pages.return_value = {}

        with self.assertRaises(WikisourceError):
            self.run_download()


class TestIncrementalUpdate(BirnbaumDownloadTestCase):
    def test_skips_pages_whose_revision_is_unchanged(self):
        self.seed_page(FIRST, "001", revid=111)
        self.revids[TITLES[LAST]] = 999  # page 815 has moved on

        self.run_download()

        self.assertEqual(self.content_requests, [[TITLES[LAST]]])
        self.assertEqual(self.contributor_requests, [[TITLES[LAST]]])

    def test_leaves_an_unchanged_page_untouched_on_disk(self):
        self.seed_page(FIRST, "001", revid=111, text="existing", credits="Dovi")
        self.revids[TITLES[LAST]] = 999

        self.run_download()

        self.assertEqual((self.text_dir / "001.txt").read_text(encoding="utf-8"), "existing")

    def test_keeps_the_old_entry_and_records_the_new_one(self):
        self.seed_page(FIRST, "001", revid=111)
        self.revids[TITLES[LAST]] = 999

        self.run_download()

        pages = self.read_manifest()["pages"]
        self.assertEqual(pages["001"]["revid"], 111)
        self.assertEqual(pages["815"]["revid"], 999)

    def test_downloads_nothing_when_the_whole_book_is_current(self):
        self.seed_page(FIRST, "001", revid=111)
        # Make page 815 current too.
        (self.text_dir / "815.txt").write_text("existing", encoding="utf-8")
        (self.credits_dir / "815.txt").write_text("Dovi", encoding="utf-8")
        manifest = self.read_manifest()
        manifest["pages"]["815"] = {"revid": 222, "timestamp": "2022-02-07T05:35:00Z"}
        self.manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

        self.run_download()

        self.assertEqual(self.content_requests, [])
        self.assertEqual(self.contributor_requests, [])

    def test_refetches_when_a_file_has_gone_missing(self):
        # A manifest entry is not proof the files survived.
        self.seed_page(FIRST, "001", revid=111)
        (self.credits_dir / "001.txt").unlink()
        self.revids[TITLES[LAST]] = 222

        self.run_download()

        self.assertIn(TITLES[FIRST], self.content_requests[0])

    def test_starts_over_when_the_manifest_is_corrupt(self):
        self.seed_page(FIRST, "001", revid=111)
        self.manifest_file.write_text("{not json", encoding="utf-8")

        self.run_download()

        self.assertEqual(sorted(self.content_requests[0]), sorted(TITLES.values()))


class TestForce(BirnbaumDownloadTestCase):
    def test_refetches_everything_regardless_of_the_manifest(self):
        self.seed_page(FIRST, "001", revid=111)

        self.run_download(force=True)

        self.assertEqual(sorted(self.content_requests[0]), sorted(TITLES.values()))


class TestDryRun(BirnbaumDownloadTestCase):
    def test_writes_nothing(self):
        self.run_download(dry_run=True)

        self.assertFalse(self.text_dir.exists())
        self.assertFalse(self.manifest_file.exists())

    def test_does_not_fetch_content(self):
        self.run_download(dry_run=True)

        self.assertEqual(self.content_requests, [])


class TestCli(unittest.TestCase):
    def test_refuses_to_run_without_a_contact_address(self):
        # Wikimedia's User-Agent policy wants a reachable address; without one we
        # should stop rather than send a placeholder.
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(wikisource, "download_book") as download:
                exit_code = main(["--dry-run"])

        self.assertEqual(exit_code, 1)
        download.assert_not_called()

    def test_passes_the_contact_address_through(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(wikisource, "download_book") as download:
                exit_code = main(["--contact-email", "example@opensiddur.org", "--dry-run"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(download.call_args.args[0], "example@opensiddur.org")
        self.assertTrue(download.call_args.kwargs["dry_run"])


if __name__ == "__main__":
    unittest.main()
