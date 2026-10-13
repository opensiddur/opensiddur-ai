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

    def compile(self, project: str, file_name: str, *, sync: bool = True) -> str:
        if sync:
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

    def test_a_parallel_column_may_transclude_the_range_it_stands_beside(self):
        """Only the primary column is the range itself; a column of another project is not."""
        self.linear_data.parallel_projects = ["q"]
        self.write("p", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>primary</tei:p></tei:div>')
        self.write("q", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>column '
                                 f'<j:transclude type="inline" target="{URN}a@p"/></tei:p></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        compiled = self.compile("p", "index.xml")
        self.assertIn("column", compiled)
        self.assertIn("parallel", compiled)

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
        # On one line and on two: the order is read from source lines where they differ.
        for separator in ("", "\n"):
            with self.subTest(separator=repr(separator)):
                self.write("p", "a.xml",
                           f'<tei:div corresp="{URN}x/1"><tei:p>one</tei:p></tei:div>{separator}'
                           f'<tei:div corresp="{URN}x/2"><tei:p>two</tei:p></tei:div>')
                self.write("p", "index.xml",
                           f'<j:transclude target="{URN}x/2" targetEnd="{URN}x/1"/>')
                self.linear_data.xml_cache.cache.clear()
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


class TestIds(CompilerGuardTestCase):
    def test_a_standoff_note_points_at_its_anchor(self):
        """A note's pointer and its anchor's id are rewritten alike, once each."""
        self.write("p", "a.xml",
                   f'<tei:div corresp="{URN}a"><tei:p>one<tei:anchor xml:id="r1"/> two</tei:p>'
                   f'</tei:div></tei:body><tei:back/></tei:text>'
                   f'<tei:standOff type="notes"><tei:note target="#r1">n</tei:note></tei:standOff>'
                   f'<tei:text><tei:body>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        compiled = etree.fromstring(f"<r>{self.compile('p', 'index.xml')}</r>")
        note = compiled.find(f".//{{{TEI}}}note")
        anchor = compiled.find(f".//{{{TEI}}}anchor")
        self.assertIsNotNone(note)
        self.assertEqual(note.get("target"), "#" + anchor.get("{http://www.w3.org/XML/1998/namespace}id"))


class TestIndexAndNamespaces(CompilerGuardTestCase):
    def test_a_file_changed_since_it_was_indexed_is_reported(self):
        self.write("p", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>one</tei:p></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        self.compile("p", "index.xml")
        self.write("p", "a.xml", f'<tei:div corresp="{URN}a"><tei:p>edited</tei:p></tei:div>')
        self.linear_data.xml_cache.cache.clear()
        self.linear_data.index_checked.clear()
        with self.assertLogs("opensiddur.exporter.compiler", level="WARNING") as logs:
            self.compile("p", "index.xml", sync=False)
        self.assertIn("p/a.xml has changed since it was indexed", "".join(logs.output))

    def test_a_document_in_the_default_namespace_compiles(self):
        (self.base / "p").mkdir(exist_ok=True)
        (self.base / "p" / "a.xml").write_bytes(
            f'<TEI xmlns="{TEI}" xmlns:j="{J}" xml:lang="en"><text><body>'
            f'<div corresp="{URN}a"><p>plain</p></div></body></text></TEI>'.encode())
        self.write("p", "index.xml", f'<j:transclude target="{URN}a"/>')
        self.assertIn("plain", self.compile("p", "index.xml"))


class TestRubricOfAHoldingCondition(CompilerGuardTestCase):
    """A j:conditional's rubric says when; once the condition holds it is not printed."""

    FS = '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'

    def test_the_rubric_of_a_true_condition_is_not_printed(self):
        self.write("p", "index.xml",
                   f'<j:declare xml:id="d">{self.FS}</j:declare>'
                   f'<j:conditional xml:id="c"><tei:note type="instruction">On the Sabbath:'
                   f'</tei:note>{self.FS}</j:conditional><tei:p>the passage</tei:p>'
                   f'<j:endConditional target="#c"/><j:endDeclare target="#d"/>')
        compiled = self.compile("p", "index.xml")
        self.assertIn("the passage", compiled)
        self.assertNotIn("On the Sabbath:", compiled)

    def test_nor_a_rubric_the_instruction_priority_would_have_replaced(self):
        rubric = "urn:x-opensiddur:instruction:test/say"
        self.write("p", "notes.xml",
                   f'<tei:p><tei:note type="instruction" corresp="{rubric}" xml:id="rub">'
                   f'Say this:</tei:note></tei:p>')
        self.write("p", "index.xml",
                   f'<j:declare xml:id="d">{self.FS}</j:declare>'
                   f'<j:conditional xml:id="c"><tei:note type="instruction" corresp="{rubric}"/>'
                   f'{self.FS}</j:conditional><tei:p>the passage</tei:p>'
                   f'<j:endConditional target="#c"/><j:endDeclare target="#d"/>')
        compiled = self.compile("p", "index.xml")
        self.assertIn("the passage", compiled)
        self.assertNotIn("Say this:", compiled)

    def test_a_rubric_inside_the_scope_is_part_of_the_passage(self):
        """A rubric saying what the passage is goes inside the scope, and prints with it."""
        self.write("p", "index.xml",
                   f'<j:declare xml:id="d">{self.FS}</j:declare>'
                   f'<j:conditional xml:id="c">{self.FS}</j:conditional>'
                   f'<tei:p><tei:note type="instruction">Mourners’ Kaddish.</tei:note>'
                   f'the passage</tei:p>'
                   f'<j:endConditional target="#c"/><j:endDeclare target="#d"/>')
        compiled = self.compile("p", "index.xml")
        self.assertIn("Mourners’ Kaddish.", compiled)
        self.assertIn("the passage", compiled)


class TestFileSources(CompilerGuardTestCase):
    def test_text_taken_back_from_the_first_file_is_credited_to_it(self):
        """a.xml -> b.xml -> a.xml: the innermost text comes from a.xml, not from b.xml."""
        self.write("p", "a.xml",
                   f'<tei:div corresp="{URN}a1"><j:transclude target="{URN}b"/></tei:div>'
                   f'<tei:div corresp="{URN}a2"><tei:p>back in a</tei:p></tei:div>')
        self.write("p", "b.xml",
                   f'<tei:div corresp="{URN}b"><j:transclude target="{URN}a2"/></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}a1"/>')
        compiled = etree.fromstring(f"<r>{self.compile('p', 'index.xml')}</r>")
        inner = compiled.find(
            f".//{{http://jewishliturgy.org/ns/processing}}transclude[@target='{URN}a2']")
        self.assertEqual(inner.get("{http://jewishliturgy.org/ns/processing}file_name"), "a.xml")


class TestSmallerCases(CompilerGuardTestCase):
    def test_a_comment_does_not_hide_the_chapter_a_range_opens_into(self):
        self.write("p", "a.xml",
                   f'<tei:div><tei:p><tei:milestone unit="chapter" n="2" corresp="{URN}c/2"/>'
                   f'<!-- the second chapter --><tei:milestone unit="verse" n="1" '
                   f'corresp="{URN}c/2/1"/>first verse</tei:p></tei:div>')
        self.write("p", "index.xml", f'<j:transclude target="{URN}c/2/1"/>')
        compiled = etree.fromstring(f"<r>{self.compile('p', 'index.xml')}</r>")
        self.assertIsNotNone(compiled.find(f".//{{{TEI}}}milestone[@unit='chapter']"))

    def test_an_empty_type_is_external(self):
        from opensiddur.exporter.compiler import transclusion_type_of
        self.assertEqual(transclusion_type_of(etree.fromstring(f'<j:transclude xmlns:j="{J}" type=""/>')),
                         "external")

    def test_a_failed_compilation_takes_its_credits_with_it(self):
        from opensiddur.exporter.compiler import CompilerProcessor
        self.write("p", "a.xml", "<tei:p>x</tei:p>")
        processor = CompilerProcessor("p", "a.xml", linear_data=self.linear_data,
                                      reference_database=self.refdb)
        self.linear_data.credits.append(("trc", "", "Kept", "Transcribed by"))
        with self.assertRaises(RuntimeError):
            with processor._printed_annotations_rollback():
                self.linear_data.credits.append(("trc", "", "Discarded", "Transcribed by"))
                raise RuntimeError("the column failed")
        self.assertEqual([credit[2] for credit in self.linear_data.credits], ["Kept"])


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

    def test_words_either_side_of_a_line_break_stay_apart(self):
        self.assertEqual(self._inline("alpha<tei:lb/>beta<tei:lb/> gamma"), "alpha beta gamma")

    def test_a_range_starting_inside_an_unread_reading_is_still_read(self):
        self.write("p", "a.xml", f'<tei:p>a <tei:choice><j:written>K'
                                 f'<tei:anchor corresp="{URN}x"/>2</j:written><j:read>Q</j:read>'
                                 f'</tei:choice> b</tei:p>')
        self.write("p", "index.xml",
                   f'<tei:p>[<j:transclude type="inline" target="{URN}x"/>]</tei:p>')
        compiled = etree.fromstring(f"<r>{self.compile('p', 'index.xml')}</r>")
        inline = compiled.find(".//{http://jewishliturgy.org/ns/processing}transclude")
        self.assertNotEqual("".join(inline.itertext()).strip(), "")

    def test_the_first_of_several_wordings_stands_in(self):
        self.assertEqual(
            self._inline("a <tei:choice><j:option>one</j:option><j:option>two</j:option>"
                         "</tei:choice> b"),
            "a one b")


if __name__ == "__main__":
    unittest.main()
