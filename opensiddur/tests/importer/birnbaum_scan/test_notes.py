# -*- coding: utf-8 -*-
"""Tests for Birnbaum's footnotes as a standoff apparatus.

Birnbaum's own words are not checked here. They are a reading committed to
`sourcetexts`, and asserting on them would transcribe the book a second time into a
test and break the next time a reading is corrected. The entries below are synthetic.
What is checked is the shape: where the apparatus lives, what it points at, and that it
points at something that exists.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from lxml import etree

from opensiddur.importer.birnbaum_scan.build import common, front, notes
from opensiddur.importer.birnbaum_scan.build import build_en, build_he
from opensiddur.tests.importer.birnbaum_scan import write_synthetic_front

TEI = "http://www.tei-c.org/ns/1.0"
XML = "http://www.w3.org/XML/1998/namespace"


class TestNoteShape(unittest.TestCase):
    def test_a_commentary_note_carries_its_catchword_as_a_label(self):
        """Birnbaum keys each commentary note by a Hebrew catchword, which is how a
        reader finds it. That catchword is a quotation of the text, not prose about
        it, so it is a `tei:label` rather than the first words of the note."""
        out = notes.note(dict(kind="commentary", target=common.PRAYER + "x",
                             lemma="לֶמָּה", text="is explained."))
        el = etree.fromstring(f'<r xmlns:tei="{TEI}">{out}</r>')
        note = el[0]
        self.assertEqual(note.get("type"), "commentary")
        label = note.find(f"{{{TEI}}}label")
        self.assertIsNotNone(label)
        self.assertEqual(label.get(f"{{{XML}}}lang"), "he")

    def test_a_citation_note_carries_the_printed_numeral_and_no_catchword(self):
        """The numbered series is keyed to a superscript in the English text, so it has
        a numeral and nothing to quote. The numeral is evidence of what the page
        printed; the renderer draws its own series, because a PDF repaginates."""
        out = notes.note(dict(kind="citation", target=common.PRAYER + "x",
                             n="3", text="<tei:bibl>Psalm 51:17</tei:bibl>"))
        note = etree.fromstring(f'<r xmlns:tei="{TEI}">{out}</r>')[0]
        self.assertEqual(note.get("type"), "citation")
        self.assertEqual(note.get("n"), "3")
        self.assertIsNone(note.find(f"{{{TEI}}}label"))

    def test_a_note_targets_a_urn_and_never_an_id(self):
        """`refdb` matches a URN target in every project but an `#id` target only inside
        the one file that declares it. An apparatus in its own file can therefore only
        reach the text by URN -- an `#id` here would resolve to nothing, silently."""
        for entry in notes.YELADIM_NOTES:
            self.assertTrue(entry["target"].startswith("urn:x-opensiddur:"), entry)
            self.assertNotIn("#", entry["target"])


class TestApparatusPlacement(unittest.TestCase):
    """Where the apparatus is written, and what it is allowed to point at."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.directory = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.object(front, "FRAGMENTS",
                                    write_synthetic_front(self.directory))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _build(self):
        build_he.main(["--project-directory", str(self.directory)])
        build_en.main(["--project-directory", str(self.directory)])

    def test_the_apparatus_is_realised_in_the_english_project_only(self):
        """The commentary is English prose about Hebrew words, as the introduction is.
        One side realises it and the other reaches it by resolution; realising it twice
        would print it twice."""
        self._build()
        en = sorted(p.name for p in (self.directory / common.PROJECT_EN).glob("notes_*.xml"))
        he = sorted(p.name for p in (self.directory / common.PROJECT_HE).glob("notes_*.xml"))
        self.assertTrue(en)
        self.assertEqual(he, [])

    def test_the_standoff_is_a_sibling_of_the_text_not_a_child_of_it(self):
        """An apparatus file has no text of its own: it annotates words that live
        elsewhere. `tei:standOff` is a `model.resource` like `tei:text`, so a document
        may carry one without the other."""
        self._build()
        for path in (self.directory / common.PROJECT_EN).glob("notes_*.xml"):
            root = etree.parse(str(path)).getroot()
            kids = [etree.QName(c).localname for c in root]
            self.assertIn("standOff", kids, path.name)
            self.assertNotIn("text", kids, path.name)

    def test_every_note_points_at_a_urn_the_corpus_actually_realises(self):
        """A note aimed at a URN nothing carries is materialised nowhere and says so
        nowhere. This is computed from the builders' own output, never from disk."""
        self._build()
        realised = set()
        for project in (common.PROJECT_HE, common.PROJECT_EN):
            for path in (self.directory / project).glob("*.xml"):
                for el in etree.parse(str(path)).iter():
                    if el.get("corresp"):
                        realised.add(el.get("corresp"))
        targeted = {e["target"] for a in build_en.APPARATUS.values() for e in a["entries"]}
        self.assertTrue(targeted)
        self.assertEqual(targeted - realised, set())

    def test_no_note_is_written_twice(self):
        """One printed note is one `tei:note`. A repeat would print the same commentary
        twice against the same words, and nothing downstream would object."""
        self._build()
        seen = [(e["target"], e["kind"], e.get("n"))
                for a in build_en.APPARATUS.values() for e in a["entries"]]
        self.assertEqual(len(seen), len(set(seen)))


if __name__ == "__main__":
    unittest.main()
