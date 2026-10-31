"""The Asher book's names are respelled once built, while its readings keep their own."""
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.common.validate_names import Spellings
from opensiddur.importer.asher_selichot import build

#: A spelling list of the tests' own, so that these do not change with the real one.
SPELLINGS = Spellings(frozenset(), {"rahamekha": "rachamekha", "tsom": "tzom"})
TEI = "http://www.tei-c.org/ns/1.0"
J = "http://jewishliturgy.org/ns/jlptei/2"
URN = "urn:x-opensiddur:text:prayer:"


def document(body):
    return etree.fromstring(f'<tei:TEI xmlns:tei="{TEI}" xmlns:j="{J}">{body}</tei:TEI>')


class RespelledTestCase(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(build, "load_spellings", return_value=SPELLINGS)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_file_names_and_urns_are_respelled_and_renames_reported(self):
        project = Path("/projects/selichoth-asher-1912-he")
        root = document(
            f'<tei:idno type="urn">{URN}ki_al_rahamekha@selichoth-asher-1912-he</tei:idno>'
            f'<tei:div corresp="{URN}ki_al_rahamekha"><j:transclude target="{URN}tsom/opening"/>'
            '<tei:p>rahamekha stays in the text</tei:p></tei:div>')
        unchanged = document(f'<tei:div corresp="{URN}ashrei"/>')
        documents, renamed = build.respelled([
            (project / "ki_al_rahamekha.xml", root), (project / "ashrei.xml", unchanged)])
        self.assertEqual([p.name for p, _ in documents], ["ki_al_rachamekha.xml", "ashrei.xml"])
        self.assertEqual(renamed, [project / "ki_al_rahamekha.xml"])
        text = etree.tostring(documents[0][1], encoding="unicode")
        self.assertIn(f"{URN}ki_al_rachamekha@selichoth-asher-1912-he<", text)
        self.assertIn(f'corresp="{URN}ki_al_rachamekha"', text)
        self.assertIn(f'target="{URN}tzom/opening"', text)
        self.assertIn("rahamekha stays in the text", text)

    def test_the_verifiers_look_names_up_the_same_way(self):
        with patch("opensiddur.common.validate_names.load_spellings", return_value=SPELLINGS):
            self.assertEqual(build.spelled_name("ki_al_rahamekha"), "ki_al_rachamekha")
            self.assertEqual(build.spelled_urn(f"{URN}tsom@selichoth-asher-1912-he"),
                             f"{URN}tzom@selichoth-asher-1912-he")


if __name__ == "__main__":
    unittest.main()
