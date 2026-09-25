"""Issue #168: notes on transcluded text limited by a condition, and printed once by type."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase

NS = {'tei': 'http://www.tei-c.org/ns/1.0', 'p': 'http://jewishliturgy.org/ns/processing',
      'j': 'http://jewishliturgy.org/ns/jlptei/2'}
URN = 'urn:x-opensiddur:text:prayer:demo/'


def declare(xml_id, value):
    return (f'<j:declare xml:id="{xml_id}"><tei:fs type="demo"><tei:f name="weekday">'
            f'<tei:binary value="{value}"/></tei:f></tei:fs></j:declare>')


def condition(value='true', wrapper=None):
    fs = (f'<tei:fs type="demo"><tei:f name="weekday"><tei:binary value="{value}"/>'
          '</tei:f></tei:fs>')
    if wrapper:
        fs = f'<j:{wrapper}>{fs}</j:{wrapper}>'
    return f'<j:condition>{fs}</j:condition>'


class AnnotationHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = ReferenceDatabase(self.base / 'index.sqlite')
        self.addCleanup(self.db.close)

    def write(self, project, name, body, notes=False):
        directory = self.base / project
        directory.mkdir(exist_ok=True)
        content = (f'<tei:TEI xmlns:tei="{NS["tei"]}" xmlns:j="{NS["j"]}" '
                   f'xml:lang="{"he" if project == "he" else "en"}">')
        content += (f'<tei:standOff type="notes">{body}</tei:standOff>' if notes
                    else f'<tei:text><tei:body>{body}</tei:body></tei:text>')
        path = directory / name
        path.write_text(content + '</tei:TEI>')
        self.db.index_file(path, project, name)

    def notes(self, *notes, project='en'):
        """Write standoff notes; each is (type, target suffix, text[, condition])."""
        self.write(project, 'notes.xml', ''.join(
            f'<tei:note type="{kind}" target="{URN}{target}">{cond}<tei:p>{text}</tei:p></tei:note>'
            for kind, target, text, *rest in notes for cond in [rest[0] if rest else '']),
            notes=True)

    def sources(self, projects=('en',)):
        for project in projects:
            for n in ('one', 'two'):
                self.write(project, n + '.xml',
                           f'<tei:div corresp="{URN}{n}"><tei:p>Text {n} {project}</tei:p></tei:div>')

    def index(self, body, projects=('en',)):
        for project in projects:
            self.write(project, 'index.xml', f'<tei:div corresp="{URN}unit">{body}</tei:div>')

    def compile(self, once=(), parallel=False, primary='en'):
        data = LinearData()
        data.xml_cache.base_path = self.base
        counterpart = 'he' if primary == 'en' else 'en'
        data.project_priority = [primary, counterpart]
        data.annotation_projects = ['en']
        data.annotation_print_once_types = set(once)
        data.parallel_projects = [counterpart] if parallel else []
        result = ExternalCompilerProcessor(
            primary, 'index.xml', linear_data=data, reference_database=self.db).process()
        self.assertEqual(data.parallel_compilation_depth, 0)
        self.assertEqual(data.processing_context, [])
        self.data = data
        root = etree.Element('result')
        root.extend(result)
        return root

    def note_texts(self, root, kind=None):
        predicate = f'[@type="{kind}"]' if kind else ''
        return [' '.join(''.join(n.itertext()).split())
                for n in root.xpath(f'.//tei:body//tei:note{predicate}', namespaces=NS)]

    def body_text(self, root):
        return ' '.join(''.join(root.xpath('.//tei:body', namespaces=NS)[0].itertext()).split())


class TestPrintOnce(AnnotationHarness):
    def repeated(self, projects=('en',)):
        self.sources(projects)
        self.index(f'<j:transclude target="{URN}one"/><tei:p>Between</tei:p>'
                   f'<j:transclude target="{URN}two"/><j:transclude target="{URN}one"/>',
                   projects)
        self.notes(('commentary', 'one', 'Comment'), ('editorial', 'one', 'Editorial'),
                   ('citation', 'one', 'Citation'))

    def test_off_by_default_every_occurrence_keeps_its_notes(self):
        self.repeated()
        root = self.compile()
        self.assertEqual(self.note_texts(root, 'commentary'), ['Comment'] * 2)
        self.assertEqual(self.note_texts(root, 'editorial'), ['Editorial'] * 2)
        self.assertEqual(self.note_texts(root, 'citation'), ['Citation'] * 2)

    def test_each_type_follows_its_own_setting(self):
        self.repeated()
        for once, comments, editorials in (
            ({'commentary'}, 1, 2),
            ({'editorial'}, 2, 1),
            ({'commentary', 'editorial'}, 1, 1),
        ):
            with self.subTest(once=once):
                root = self.compile(once=once)
                self.assertEqual(len(self.note_texts(root, 'commentary')), comments)
                self.assertEqual(len(self.note_texts(root, 'editorial')), editorials)
                self.assertEqual(len(self.note_texts(root, 'citation')), 2)
                self.assertEqual(len(self.data.printed_annotations), len(once))

    def test_the_first_occurrence_keeps_the_note(self):
        self.repeated()
        text = self.body_text(self.compile(once={'commentary'}))
        self.assertLess(text.index('Comment'), text.index('Between'))
        self.assertEqual(text.count('Comment'), 1)
        self.assertEqual(text.count('Text one en'), 2)

    def test_instructions_are_never_printed_once(self):
        self.sources()
        self.write('en', 'one.xml',
                   f'<tei:div corresp="{URN}one"><tei:note type="instruction">Stand.</tei:note>'
                   '<tei:p>Text one</tei:p></tei:div>')
        self.index(f'<j:transclude target="{URN}one"/><j:transclude target="{URN}one"/>')
        self.notes(('commentary', 'one', 'Comment'))
        root = self.compile(once={'commentary', 'instruction'})
        self.assertEqual(self.note_texts(root, 'instruction'), ['Stand.'] * 2)
        self.assertEqual(self.note_texts(root, 'commentary'), ['Comment'])

    def test_once_in_parallel_columns(self):
        self.repeated(projects=('en', 'he'))
        for primary in ('he', 'en'):
            with self.subTest(primary=primary):
                root = self.compile(once={'commentary'}, parallel=True, primary=primary)
                self.assertEqual(self.note_texts(root, 'commentary'), ['Comment'])
                self.assertEqual(self.note_texts(root, 'citation'), ['Citation'] * 2)

    def test_failed_counterpart_does_not_claim_the_notes(self):
        self.repeated(projects=('en', 'he'))
        original = ExternalCompilerProcessor._process_element

        def fail_second_counterpart_file(processor, element, root=None):
            # The whole-document counterpart registers one.xml's notes, then fails in two.xml
            if processor.project == 'en' and processor.file_name == 'two.xml':
                raise ValueError('synthetic counterpart failure')
            return original(processor, element, root)

        with patch.object(ExternalCompilerProcessor, '_process_element', fail_second_counterpart_file):
            root = self.compile(once={'commentary'}, parallel=True, primary='he')
        self.assertEqual(self.note_texts(root, 'commentary'), ['Comment'])

    def test_milestone_note_printed_once(self):
        self.write('en', 'source.xml', f'''<tei:div><tei:p>
          <tei:milestone unit="verse" corresp="{URN}1"/>First verse.
          <tei:milestone unit="verse" corresp="{URN}2"/>Second verse.</tei:p></tei:div>''')
        self.index(f'<j:transclude target="{URN}1"/><j:transclude target="{URN}1"/>')
        self.notes(('commentary', '1', 'Verse note'))
        self.assertEqual(self.note_texts(self.compile()), ['Verse note'] * 2)
        text = self.body_text(self.compile(once={'commentary'}))
        self.assertEqual(text.count('First verse.'), 2)
        self.assertEqual(text.count('Verse note'), 1)

    def test_inline_transclusion_printed_once(self):
        self.write('en', 'source.xml',
                   f'<tei:div><tei:p><tei:seg corresp="{URN}phrase">A phrase</tei:seg></tei:p></tei:div>')
        self.index(f'<tei:p><j:transclude type="inline" target="{URN}phrase"/> and '
                   f'<j:transclude type="inline" target="{URN}phrase"/></tei:p>')
        self.notes(('commentary', 'phrase', 'Phrase note'))
        self.assertEqual(self.note_texts(self.compile()), ['Phrase note'] * 2)
        self.assertEqual(self.note_texts(self.compile(once={'commentary'})), ['Phrase note'])


class TestNoteCondition(AnnotationHarness):
    def contexts(self, projects=('en',)):
        """The same text in a false, a true and an undeclared context, in that order."""
        self.sources(projects)
        self.index(
            f'<tei:div>{declare("off", "false")}<tei:p>Off</tei:p>'
            f'<j:transclude target="{URN}one"/><j:endDeclare target="#off"/></tei:div>'
            f'<tei:div>{declare("on", "true")}<tei:p>On</tei:p>'
            f'<j:transclude target="{URN}one"/><j:endDeclare target="#on"/></tei:div>'
            f'<tei:div><tei:p>Undeclared</tei:p><j:transclude target="{URN}one"/></tei:div>',
            projects)

    def placements(self, root, text):
        """The context heading ('Off'/'On'/'Undeclared') preceding each copy of `text`."""
        return [note.xpath('preceding::tei:p[not(ancestor::tei:note)][. = "Off" or . = "On" '
                           'or . = "Undeclared"][1]/text()', namespaces=NS)[0]
                for note in root.xpath('.//tei:body//tei:note', namespaces=NS)
                if ''.join(note.itertext()).strip() == text]

    def test_false_omits_the_note_true_and_undefined_print_it(self):
        self.contexts()
        self.notes(('commentary', 'one', 'Weekday note', condition()))
        root = self.compile()
        self.assertEqual(self.placements(root, 'Weekday note'), ['On', 'Undeclared'])
        self.assertEqual(self.body_text(root).count('Text one en'), 3)

    def test_condition_is_not_printed(self):
        self.contexts()
        self.notes(('commentary', 'one', 'Weekday note', condition()))
        root = self.compile()
        self.assertFalse(root.xpath('//j:condition | //tei:note//tei:fs', namespaces=NS))
        self.assertEqual(self.note_texts(root), ['Weekday note'] * 2)

    def test_combinators(self):
        for wrapper, value, expected in (
            ('none', 'false', ['On', 'Undeclared']),
            ('none', 'true', ['Off', 'Undeclared']),
            ('any', 'false', ['Off', 'Undeclared']),
        ):
            with self.subTest(wrapper=wrapper, value=value):
                self.contexts()
                self.notes(('commentary', 'one', 'Note', condition(value, wrapper)))
                self.assertEqual(self.placements(self.compile(), 'Note'), expected)

    def test_unconditioned_notes_are_unaffected(self):
        self.contexts()
        self.notes(('commentary', 'one', 'Weekday note', condition()),
                   ('citation', 'one', 'Citation'))
        root = self.compile()
        self.assertEqual(self.placements(root, 'Citation'), ['Off', 'On', 'Undeclared'])

    def test_suppressed_occurrence_does_not_use_up_print_once(self):
        self.contexts()
        self.notes(('commentary', 'one', 'Weekday note', condition()))
        root = self.compile(once={'commentary'})
        self.assertEqual(self.placements(root, 'Weekday note'), ['On'])

    def test_conditional_text_inside_a_note_is_not_a_note_condition(self):
        self.contexts()
        self.write('en', 'notes.xml',
                   f'<tei:note type="commentary" target="{URN}one"><tei:p>Always'
                   '<j:conditional xml:id="c"><tei:fs type="demo"><tei:f name="weekday">'
                   '<tei:binary value="true"/></tei:f></tei:fs></j:conditional> weekday words'
                   '<j:endConditional target="#c"/> said.</tei:p></tei:note>'
                   f'<tei:note type="editorial" target="{URN}one">{condition()}<tei:p>Both'
                   '<j:conditional xml:id="d"><tei:fs type="demo"><tei:f name="weekday">'
                   '<tei:binary value="false"/></tei:f></tei:fs></j:conditional> non-weekday words'
                   '<j:endConditional target="#d"/> said.</tei:p></tei:note>', notes=True)
        root = self.compile()
        # The partly conditional note prints everywhere; only its conditional words vary
        self.assertEqual(self.note_texts(root, 'commentary'),
                         ['Always said.', 'Always weekday words said.', 'Always weekday words said.'])
        # The note's condition holds in "On" (where its inner span is false) and when undeclared
        self.assertEqual(self.placements(root, 'Both said.'), ['On'])
        self.assertEqual(len(self.note_texts(root, 'editorial')), 2)

    def test_false_condition_in_parallel_columns_reaches_no_output(self):
        from opensiddur.common.xslt import xslt_transform_string
        from opensiddur.exporter.tex.latex import XSLT_FILE
        self.contexts(projects=('en', 'he'))
        self.notes(('commentary', 'one', 'WEEKDAYNOTE', condition()))
        for primary in ('he', 'en'):
            with self.subTest(primary=primary):
                root = self.compile(parallel=True, primary=primary)
                self.assertEqual(self.placements(root, 'WEEKDAYNOTE'), ['On', 'Undeclared'])
                tex = xslt_transform_string(
                    XSLT_FILE, etree.tostring(root[0], encoding='unicode'),
                    xslt_params={'additional-preamble': '', 'additional-postamble': ''})
                self.assertEqual(tex.count('WEEKDAYNOTE'), 2)


if __name__ == '__main__':
    unittest.main()
