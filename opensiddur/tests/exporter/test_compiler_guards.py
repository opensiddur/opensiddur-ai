"""The compiler refuses what it cannot compile, and leaves its state as it found it.

Each test builds small synthetic projects, indexes them into a reference database of its own,
and compiles one file.
"""

import tempfile
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase

TEI = "http://www.tei-c.org/ns/1.0"
J = "http://jewishliturgy.org/ns/jlptei/2"
URN = "urn:x-opensiddur:text:test:"


def _document(body: str) -> bytes:
    return (f'<tei:TEI xmlns:tei="{TEI}" xmlns:j="{J}" xml:lang="en">'
            f'<tei:text><tei:body>{body}</tei:body></tei:text></tei:TEI>').encode()


class CompilerGuardTestCase(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.base = Path(temp_dir.name)
        self.refdb = ReferenceDatabase(self.base / "reference.db")
        self.addCleanup(self.refdb.close)
        self.linear_data = LinearData(
            project_priority=["p"], instruction_priority=["p"], annotation_projects=["p"])
        self.linear_data.xml_cache.base_path = self.base

    def write(self, project: str, file_name: str, body: str) -> None:
        (self.base / project).mkdir(exist_ok=True)
        (self.base / project / file_name).write_bytes(_document(body))

    def compile(self, project: str, file_name: str) -> str:
        for project_dir in self.base.iterdir():
            if project_dir.is_dir():
                self.refdb.sync_project(project_dir.name, self.base)
        processor = ExternalCompilerProcessor(
            project, file_name, linear_data=self.linear_data, reference_database=self.refdb)
        return "".join(etree.tostring(element, encoding="unicode")
                       for element in processor.process())


class TestTransclusionCycles(CompilerGuardTestCase):
    def test_a_cycle_is_reported_with_its_chain(self):
        self.write("p", "a.xml",
                   f'<tei:div corresp="{URN}a"><j:transclude target="{URN}b"/></tei:div>')
        self.write("p", "b.xml",
                   f'<tei:div corresp="{URN}b"><j:transclude target="{URN}a"/></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        with self.assertRaisesRegex(ValueError, "Transclusion cycle.*p/a.xml -> p/b.xml -> p/a.xml"):
            self.compile("p", "index.xml")

    def test_the_same_range_twice_in_a_row_is_not_a_cycle(self):
        self.write("p", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>once</tei:p></tei:div>')
        self.write("p", "index.xml",
                   f'<j:transclude target="{URN}a"/><j:transclude target="{URN}a"/>')
        self.assertEqual(self.compile("p", "index.xml").count("once"), 2)

    def test_state_is_restored_after_a_failure(self):
        self.write("p", "a.xml",
                   f'<tei:div corresp="{URN}a"><j:transclude target="{URN}a"/></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        with self.assertRaises(ValueError):
            self.compile("p", "index.xml")
        self.assertEqual(self.linear_data.processing_context, [])
        self.assertEqual(self.linear_data.transclusion_chain, [])


class TestRanges(CompilerGuardTestCase):
    def test_a_range_that_ends_before_it_starts_is_an_error(self):
        self.write("p", "a.xml", f'<tei:div corresp="{URN}x/1"><tei:p>one</tei:p></tei:div>'
                                 f'<tei:div corresp="{URN}x/2"><tei:p>two</tei:p></tei:div>')
        self.write("p", "index.xml",
                   f'<j:transclude target="{URN}x/2" targetEnd="{URN}x/1"/>')
        with self.assertRaisesRegex(ValueError, "ends before it starts"):
            self.compile("p", "index.xml")

    def test_a_range_across_files_says_so(self):
        self.write("p", "a.xml", f'<tei:div corresp="{URN}x/1"><tei:p>one</tei:p></tei:div>')
        self.write("p", "b.xml", f'<tei:div corresp="{URN}x/2"><tei:p>two</tei:p></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}x/1-2"/>')
        with self.assertRaisesRegex(ValueError, "different files"):
            self.compile("p", "index.xml")

    def test_a_target_naming_its_project_needs_no_priority(self):
        """The priority list chooses among projects only when the target does not."""
        self.write("q", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>from q</tei:p></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a@q"/>')
        self.assertIn("from q", self.compile("p", "index.xml"))


class TestInlineText(CompilerGuardTestCase):
    def _inline(self, paragraph: str) -> str:
        self.write("p", "a.xml", f'<tei:p corresp="{URN}a">{paragraph}</tei:p>')
        self.write("p", "index.xml",
                   f'<tei:p>[<j:transclude type="inline" target="{URN}a"/>]</tei:p>')
        compiled = etree.fromstring(f"<r>{self.compile('p', 'index.xml')}</r>")
        inline = compiled.find(".//{http://jewishliturgy.org/ns/processing}transclude")
        return "".join(inline.itertext())

    def test_a_word_divided_by_markup_stays_one_word(self):
        self.assertEqual(self._inline("<tei:hi>נֹ</tei:hi>צֵר חֶסֶד"), "נֹצֵר חֶסֶד")

    def test_only_the_qere_of_a_ketiv_and_qere_is_read(self):
        self.assertEqual(
            self._inline("a <tei:choice><j:written>K</j:written><j:read>Q</j:read></tei:choice> b"),
            "a Q b")

    def test_the_first_of_several_wordings_stands_in(self):
        self.assertEqual(
            self._inline("a <tei:choice><j:option>one</j:option><j:option>two</j:option>"
                         "</tei:choice> b"),
            "a one b")


if __name__ == "__main__":
    unittest.main()
