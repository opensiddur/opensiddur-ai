"""A rubric saying when is the j:conditional's own; one saying what goes inside the scope.

schema/JLPTEI-3.md, *Kinds of rubric*: a true condition does not print its rubric, so a rubric
that names the passage, says who says it or how, belongs to the passage instead.
"""

import re
import unittest

from lxml import etree

from opensiddur.importer.birnbaum_scan.build import build_en, build_he
from opensiddur.importer.birnbaum_scan.build.common import (
    cond,
    is_descriptive_rubric,
)

TEI = "http://www.tei-c.org/ns/1.0"
J = "http://jewishliturgy.org/ns/jlptei/2"
FS = '<tei:fs type="opensiddur:quorum"><tei:f name="minyan"><tei:binary value="true"/></tei:f></tei:fs>'


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(f'<r xmlns:tei="{TEI}" xmlns:j="{J}">{xml}</r>')


class TestCond(unittest.TestCase):

    def test_a_rubric_saying_when_is_the_conditionals_own(self):
        root = _parse(cond("c", note="With a minyan:", fs=FS))
        conditional = root.find(f"{{{J}}}conditional")
        self.assertEqual("instruction", conditional.find(f"{{{TEI}}}note").get("type"))
        self.assertEqual(1, len(root))

    def test_a_rubric_saying_what_goes_first_inside_the_scope(self):
        root = _parse(cond("c", note="Mourners’ Kaddish.", fs=FS, note_urn="urn:x"))
        conditional, note = root
        self.assertIsNone(conditional.find(f"{{{TEI}}}note"))
        self.assertEqual(f"{{{TEI}}}note", note.tag)
        self.assertEqual(("description", "urn:x"), (note.get("type"), note.get("corresp")))
        self.assertEqual("Mourners’ Kaddish.", note.text)

    def test_markup_and_spacing_do_not_hide_a_descriptive_rubric(self):
        self.assertTrue(is_descriptive_rubric("In   silent <tei:hi>devotion:</tei:hi>"))
        self.assertFalse(is_descriptive_rubric("On the Sabbath:"))


class TestTheBuild(unittest.TestCase):
    """The prayers the generator writes follow the rule."""

    def _bodies(self, build) -> str:
        return "\n".join(unit["body"] for unit in build.PRAYERS)

    def test_no_descriptive_rubric_is_a_conditionals_own(self):
        for build in (build_he, build_en):
            for match in re.finditer(r'(?s)<j:conditional\b.*?</j:conditional>',
                                     self._bodies(build)):
                for note in re.findall(r'<tei:note type="instruction"[^>]*>(.*?)</tei:note>',
                                       match.group(0)):
                    with self.subTest(build=build.__name__, note=note):
                        self.assertFalse(is_descriptive_rubric(note))


if __name__ == "__main__":
    unittest.main()
