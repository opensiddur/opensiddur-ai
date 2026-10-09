"""The conditionals over passages Birnbaum sets off himself are type="marked".

How an undecided passage looks follows the book: parentheses, or an asterisk keying a reading
to its substitute, are delimiters the edition must keep (schema/JLPTEI-3.md, *How an undecided
scope is set off*).
"""

import re
import unittest

from opensiddur.importer.birnbaum_scan.build import build_en, build_he


def _openers(build) -> dict[str, str]:
    bodies = "\n".join(unit["body"] for unit in build.PRAYERS)
    return {match.group(1): match.group(0)
            for match in re.finditer(r'<j:conditional xml:id="([^"]+)"[^>]*>', bodies)}


class TestMarkedScopes(unittest.TestCase):

    def test_the_starred_ordinary_seals_are_marked(self):
        for build in (build_he, build_en):
            openers = _openers(build)
            for cid in ("cond_qedushah_seal_ordinary", "cond_qh_seal_ordinary",
                        "cond_mishpat_seal_ordinary", "cond_shalom_seal_ordinary"):
                with self.subTest(build=build.__name__, cid=cid):
                    self.assertIn('type="marked"', openers[cid])

    def test_the_bracketed_prefix_is_marked_and_joined_to_its_word(self):
        bodies = "\n".join(unit["body"] for unit in build_he.PRAYERS)
        self.assertRegex(
            bodies,
            r'(?s)<j:conditional xml:id="arvit_vechanenu" type="marked">.*?</j:conditional>'
            r'וְ<j:endConditional target="#arvit_vechanenu"/>(?!\s)')


if __name__ == "__main__":
    unittest.main()
