"""Tests for splitting JPS 1917's merged Decalogue verses onto canonical verses.

The fixtures are synthetic mediawiki intermediate documents, not JPS pages, so a change to
the source text cannot turn these into failures.
"""

import unittest

from lxml import etree

from opensiddur.importer.jps1917.canonical_verses import (
    CanonicalVerseError,
    annotate_canonical_verses,
)


def document(body: str) -> str:
    return f"<tei:body xmlns:tei='http://www.tei-c.org/ns/1.0'><mediawikis>{body}</mediawikis></tei:body>"


def verse(chapter: int, number: int, text: str) -> str:
    return f'<verse chapter="{chapter}" verse="{number}"></verse>{text}'


def verses_of(annotated: str) -> list[tuple[int, int, str | None, str]]:
    root = etree.fromstring(annotated.encode("utf-8"))
    return [
        (
            int(v.get("chapter")),
            int(v.get("verse")),
            v.get("editionVerse"),
            (v.tail or "").strip(),
        )
        for v in root.iter("verse")
    ]


class TestUndivergentChapters(unittest.TestCase):
    def test_numbering_passes_through(self):
        annotated = verses_of(annotate_canonical_verses(
            document(verse(1, 1, "In the beginning")), "genesis"))
        self.assertEqual(annotated, [(1, 1, "1", "In the beginning")])


class TestMergedDecalogueVerse(unittest.TestCase):
    """JPS reads the four short commandments as one verse; canonically they are 13-16."""

    FOUR = (
        verse(20, 13, "Thou shalt not murder.")
        + "<p/>Thou shalt not commit adultery."
        + "<p/>Thou shalt not steal."
        + "<p/>Thou shalt not bear false witness."
        + "<p/>"
        + verse(20, 14, "Thou shalt not covet.")
    )

    def test_one_verse_becomes_four(self):
        annotated = verses_of(annotate_canonical_verses(document(self.FOUR), "exodus"))
        self.assertEqual([v for _, v, _, _ in annotated], [13, 14, 15, 16, 17])

    def test_each_canonical_verse_keeps_its_own_text(self):
        annotated = verses_of(annotate_canonical_verses(document(self.FOUR), "exodus"))
        self.assertEqual(
            [text for _, _, _, text in annotated],
            [
                "Thou shalt not murder.",
                "Thou shalt not commit adultery.",
                "Thou shalt not steal.",
                "Thou shalt not bear false witness.",
                "Thou shalt not covet.",
            ],
        )

    def test_only_the_opening_verse_carries_the_edition_number(self):
        annotated = verses_of(annotate_canonical_verses(document(self.FOUR), "exodus"))
        self.assertEqual([edition for _, _, edition, _ in annotated], ["13", None, None, None, "14"])

    def test_the_closing_paragraph_break_is_not_a_verse_boundary(self):
        # There are four breaks inside the run but only three of them have text after them.
        annotated = verses_of(annotate_canonical_verses(document(self.FOUR), "exodus"))
        self.assertEqual(len(annotated), 5)

    def test_the_rest_of_the_chapter_is_renumbered(self):
        annotated = verses_of(annotate_canonical_verses(
            document(verse(20, 23, "Neither shalt thou go up by steps")), "exodus"))
        self.assertEqual(annotated, [(20, 26, "23", "Neither shalt thou go up by steps")])

    def test_deuteronomy_five_follows_the_same_pattern(self):
        body = (
            verse(5, 17, "Thou shalt not murder.")
            + "<p/>Neither shalt thou commit adultery."
            + "<p/>Neither shalt thou steal."
            + "<p/>Neither shalt thou bear false witness."
            + "<p/>"
            + verse(5, 18, "Neither shalt thou covet.")
        )
        annotated = verses_of(annotate_canonical_verses(document(body), "deuteronomy"))
        self.assertEqual([v for _, v, _, _ in annotated], [17, 18, 19, 20, 21])


class TestSourceAndTableMustAgree(unittest.TestCase):
    def test_too_few_paragraph_breaks_is_an_error(self):
        body = verse(20, 13, "Thou shalt not murder.") + "<p/>Thou shalt not commit adultery."
        with self.assertRaises(CanonicalVerseError) as caught:
            annotate_canonical_verses(document(body), "exodus")
        self.assertIn("paragraph breaks", str(caught.exception))

    def test_non_numeric_markers_are_left_alone(self):
        annotated = annotate_canonical_verses(document("<verse/>"), "genesis")
        root = etree.fromstring(annotated.encode("utf-8"))
        self.assertEqual(len(list(root.iter("verse"))), 1)


if __name__ == "__main__":
    unittest.main()
