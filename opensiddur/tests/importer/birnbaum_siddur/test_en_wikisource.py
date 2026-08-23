"""Tests for the English Wikisource half of the Birnbaum siddur.

Runs against a synthetic three-page book in a temporary sourcetexts tree with the
Action API faked, so nothing here depends on what en.wikisource holds today — which
matters more than usual, since that transcription is actively being worked on.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from opensiddur.importer.birnbaum_siddur import en_wikisource
from opensiddur.importer.birnbaum_siddur.en_wikisource import (
    download_book,
    is_usable,
    main,
    page_body,
    page_quality,
)
from opensiddur.importer.util import wikisource_book
from opensiddur.importer.util.pages import (
    birnbaum_siddur_en_credits_directory,
    birnbaum_siddur_en_data_directory,
    birnbaum_siddur_en_text_directory,
    get_birnbaum_en_credits,
    get_birnbaum_en_page,
)
from opensiddur.importer.util.wikisource import RevisionInfo

CONTACT = "tests@opensiddur.invalid"

# The real book has 815 leaves but only a fraction are transcribed in English. These
# three stand for that: the highest is 27, well under three digits.
PAGES = (1, 14, 27)
TITLES = {
    number: f"{en_wikisource.WIKI_NAMESPACE}:{en_wikisource.BOOK_NAME}/{number}"
    for number in PAGES
}

WIKITEXT = '<noinclude><pagequality level="4" user="Someone" /></noinclude>English text<noinclude><references/></noinclude>'


class EnWikisourceTestCase(unittest.TestCase):
    """Fixture wiring the downloader to a temporary tree and a fake wiki."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        self.data_dir = birnbaum_siddur_en_data_directory(self.root)
        self.text_dir = birnbaum_siddur_en_text_directory(self.root)
        self.credits_dir = birnbaum_siddur_en_credits_directory(self.root)
        self.manifest_file = self.data_dir / "manifest.json"

        self.revids = {TITLES[n]: 100 + n for n in PAGES}
        self.contributors = {TITLES[n]: ["Someone", "Another"] for n in PAGES}
        self.content_requests = []

        patcher = patch.multiple(
            wikisource_book,
            list_book_pages=MagicMock(return_value=dict(TITLES)),
            fetch_revisions=MagicMock(side_effect=self.fake_fetch_revisions),
            fetch_contributors=MagicMock(side_effect=self.fake_fetch_contributors),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        connect_patcher = patch.object(
            en_wikisource, "connect", MagicMock(return_value=MagicMock(server="en.wikisource.org"))
        )
        connect_patcher.start()
        self.addCleanup(connect_patcher.stop)

    def fake_fetch_revisions(self, wiki, titles, *, include_content, **kwargs):
        titles = list(titles)
        if include_content:
            self.content_requests.append(titles)
        return {
            title: RevisionInfo(
                revid=self.revids[title],
                timestamp="2024-05-01T00:00:00Z",
                content=WIKITEXT if include_content else None,
            )
            for title in titles
        }

    def fake_fetch_contributors(self, wiki, titles, **kwargs):
        return {title: self.contributors.get(title, []) for title in titles}

    def run_download(self, **kwargs):
        return download_book(CONTACT, self.root, **kwargs)

    def read_manifest(self):
        return json.loads(self.manifest_file.read_text(encoding="utf-8"))


class FilenameTestCase(EnWikisourceTestCase):
    """The English tree must stay page-for-page addressable with the other two."""

    def test_pages_are_padded_to_three_digits(self):
        self.run_download()
        self.assertEqual(
            sorted(p.name for p in self.text_dir.glob("*.txt")),
            ["001.txt", "014.txt", "027.txt"],
        )

    def test_padding_does_not_shrink_to_fit_the_pages_found(self):
        # Only a third of the book exists in English, and which pages exist changes
        # as people transcribe. If the width were inferred from the highest page
        # found -- 27 here -- these files would be "1.txt", "14.txt", "27.txt" and
        # would no longer pair with text/001.txt and ia/ocr/001.txt.
        self.run_download()
        for name in ("1.txt", "14.txt", "27.txt"):
            self.assertFalse((self.text_dir / name).exists(), name)

    def test_manifest_keys_match_the_filenames(self):
        self.run_download()
        self.assertEqual(sorted(self.read_manifest()["pages"]), ["001", "014", "027"])

    def test_pages_are_readable_through_the_shared_accessors(self):
        self.run_download()
        page = get_birnbaum_en_page(14, self.root)
        self.assertIsNotNone(page)
        self.assertEqual(page.number, 14)
        self.assertEqual(get_birnbaum_en_credits(14, self.root), ["Someone", "Another"])
        # Absent pages are the common case here, not an error.
        self.assertIsNone(get_birnbaum_en_page(2, self.root))


class DownloadTestCase(EnWikisourceTestCase):
    def test_text_and_credits_are_both_written(self):
        self.run_download()
        self.assertEqual((self.text_dir / "014.txt").read_text(encoding="utf-8"), WIKITEXT)
        self.assertEqual(
            (self.credits_dir / "014.txt").read_text(encoding="utf-8"),
            "Someone\nAnother",
        )

    def test_manifest_names_the_english_wiki(self):
        self.run_download()
        manifest = self.read_manifest()
        self.assertEqual(manifest["source"], "en.wikisource.org")
        self.assertEqual(manifest["namespace"], "Page")
        self.assertEqual(manifest["book_name"], en_wikisource.BOOK_NAME)

    def test_dry_run_writes_nothing(self):
        self.run_download(dry_run=True)
        self.assertFalse(self.manifest_file.exists())
        self.assertFalse(self.text_dir.exists())

    def test_an_unchanged_rerun_writes_nothing(self):
        self.run_download()
        before = self.manifest_file.read_text(encoding="utf-8")
        self.content_requests.clear()

        self.run_download()

        # No wikitext refetched, and the manifest left byte-identical so an
        # unchanged run never shows up as a diff.
        self.assertEqual(self.content_requests, [])
        self.assertEqual(self.manifest_file.read_text(encoding="utf-8"), before)

    def test_a_changed_page_is_refetched_alone(self):
        self.run_download()
        self.content_requests.clear()
        self.revids[TITLES[14]] += 1

        self.run_download()

        self.assertEqual(self.content_requests, [[TITLES[14]]])

    def test_force_refetches_everything(self):
        self.run_download()
        self.content_requests.clear()

        self.run_download(force=True)

        self.assertEqual(sorted(self.content_requests[0]), sorted(TITLES.values()))


class ProofreadStatusTestCase(unittest.TestCase):
    """Reading ProofreadPage's own record of how far a page has been checked."""

    def test_quality_is_read_from_the_header(self):
        self.assertEqual(page_quality(WIKITEXT), 4)
        self.assertEqual(
            page_quality('<noinclude><pagequality level="1" user="X" /></noinclude>a'), 1
        )

    def test_a_page_without_a_quality_marker_reports_none(self):
        self.assertIsNone(page_quality("just text"))

    def test_body_excludes_the_header_and_footer(self):
        self.assertEqual(page_body(WIKITEXT), "English text")

    def test_an_untyped_page_has_an_empty_body(self):
        # Created by the proofreading interface and never filled in. Roughly half of
        # the pages that exist for this book are like this, and they are
        # indistinguishable from real ones until the wrappers come off.
        shell = '<noinclude><pagequality level="4" user="X" /></noinclude>   \n<noinclude><references/></noinclude>'
        self.assertEqual(page_body(shell), "")
        self.assertFalse(is_usable(shell))

    def test_usability_follows_proofreading_level(self):
        def page(level):
            return f'<noinclude><pagequality level="{level}" user="X" /></noinclude>text<noinclude/></noinclude>'

        # A human has read 3 and 4 against the scan; nothing below that.
        self.assertTrue(is_usable(page(4)))
        self.assertTrue(is_usable(page(3)))
        self.assertFalse(is_usable(page(2)))
        self.assertFalse(is_usable(page(1)))
        self.assertFalse(is_usable(page(0)))
        self.assertFalse(is_usable("no marker at all"))


class MainTestCase(EnWikisourceTestCase):
    def test_main_returns_zero_on_success(self):
        code = main(["--sourcetexts-root", str(self.root), "--contact-email", CONTACT])
        self.assertEqual(code, 0)
        self.assertTrue(self.manifest_file.is_file())

    def test_main_requires_a_real_contact_address(self):
        with patch.dict("os.environ", {"OPENSIDDUR_CONTACT_EMAIL": ""}):
            self.assertEqual(main(["--sourcetexts-root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
