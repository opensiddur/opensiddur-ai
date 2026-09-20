"""Issue #124: apparatus survives real reference resolution and parallel assembly."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase

NS = {'tei': 'http://www.tei-c.org/ns/1.0', 'p': 'http://jewishliturgy.org/ns/processing'}
URN = 'urn:x-opensiddur:text:prayer:demo/'


class TestParallelAnnotations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = ReferenceDatabase(self.base / 'index.sqlite')
        self.addCleanup(self.db.close)

    def write(self, project, name, body, notes=False):
        directory = self.base / project
        directory.mkdir(exist_ok=True)
        content = (f'<tei:TEI xmlns:tei="{NS["tei"]}" '
                   'xmlns:j="http://jewishliturgy.org/ns/jlptei/2" '
                   f'xml:lang="{"he" if project == "he" else "en"}">')
        content += (f'<tei:standOff type="notes">{body}</tei:standOff>' if notes
                    else f'<tei:text><tei:body>{body}</tei:body></tei:text>')
        path = directory / name
        path.write_text(content + '</tei:TEI>')
        self.db.index_file(path, project, name)

    def fixture(self, target='div', apparatus='en', root_pair=True, repeated=False):
        for project in ('he', 'en'):
            transcludes = ''.join(f'<j:transclude target="{URN}{n}"/>' for n in ('one', 'two'))
            if repeated:
                transcludes += f'<j:transclude target="{URN}one"/>'
            root_urn = URN + ('unit' if root_pair or project == 'he' else 'other')
            self.write(project, 'index.xml', f'<tei:div corresp="{root_urn}">{transcludes}</tei:div>')
            for n in ('one', 'two'):
                inner = (
                    f'<tei:{target} corresp="{URN}{n}/inner">Lead {n}'
                    f'<tei:hi xml:id="middle">middle</tei:hi> tail {n}</tei:{target}>')
                body = (f'<tei:div corresp="{URN}{n}"><tei:p>Text {n}</tei:p></tei:div>'
                        if target == 'div' else f'<tei:div corresp="{URN}{n}">{inner}</tei:div>')
                self.write(project, n + '.xml', body)
        suffix = '' if target == 'div' else '/inner'
        notes = ''.join(
            f'<tei:note type="commentary" xml:id="note-{n}-{i}" '
            f'target="{URN}{n}{suffix}"><tei:p>Note {n} {i}</tei:p></tei:note>'
            for n in ('one', 'two') for i in (1, 2))
        self.write(apparatus, 'notes.xml', notes, notes=True)

    def compile(self, apparatus='en', parallel=True, primary='he', projects=None):
        data = LinearData()
        data.xml_cache.base_path = self.base
        data.project_priority = [primary, 'en' if primary == 'he' else 'he']
        data.annotation_projects = [apparatus] if apparatus else []
        counterpart = 'en' if primary == 'he' else 'he'
        data.parallel_projects = (projects if projects is not None else [counterpart]) if parallel else []
        result = ExternalCompilerProcessor(
            primary, 'index.xml', linear_data=data, reference_database=self.db).process()
        self.assertEqual(data.annotation_projects, [apparatus] if apparatus else [])
        self.assertEqual(data.parallel_compilation_depth, 0)
        self.assertEqual(data.processing_context, [])
        root = etree.Element('result')
        root.extend(result)
        return root

    def assert_notes(self, root, expected=4, role=None):
        notes = root.xpath('.//tei:body//tei:note[@type="commentary"]', namespaces=NS)
        self.assertEqual(len(notes), expected)
        if expected:
            expected_text = ['Note one 1', 'Note one 2', 'Note two 1', 'Note two 2']
            if expected == 6:
                expected_text += ['Note one 1', 'Note one 2']
            self.assertEqual([''.join(n.itertext()) for n in notes], expected_text)
        for note in notes:
            if role:
                self.assertEqual(note.xpath('ancestor::p:parallelItem/@role', namespaces=NS), [role])
        ids = root.xpath('//@xml:id', namespaces={'xml': 'http://www.w3.org/XML/1998/namespace'})
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(root.xpath(
            './/p:parallel/ancestor::p:parallel | .//p:parallel/ancestor::tei:div | '
            './/p:parallelItem//p:transclude', namespaces=NS))
        self.assertFalse(root.xpath('//*[@p:start or @p:end or @p:suspend or @p:resume]', namespaces=NS))

    def test_milestone_notes_follow_their_verse_in_both_columns_and_plain_text(self):
        from opensiddur.common.xslt import xslt_transform_string
        from opensiddur.exporter.tex.latex import XSLT_FILE
        for project in ('he', 'en'):
            self.write(project, 'index.xml', f'''<tei:div corresp="{URN}unit"><tei:p>
              <tei:milestone unit="verse" corresp="{URN}1"/>First verse.
              <tei:milestone unit="verse" corresp="{URN}2"/>Second verse.
              <tei:milestone unit="verse"/>Unrelated text.</tei:p></tei:div>''')
        self.write('en', 'notes.xml', ''.join(
            f'<tei:note type="commentary" target="{URN}{n}">APPARATUS{n}</tei:note>'
            for n in (1, 2)), notes=True)
        for primary in ('he', 'en'):
            for parallel in (False, True):
                with self.subTest(primary=primary, parallel=parallel):
                    root = self.compile(primary=primary, parallel=parallel)
                    notes = root.xpath('.//tei:body//tei:note', namespaces=NS)
                    self.assertEqual(len(notes), 2)
                    for n, note in enumerate(notes, 1):
                        paragraph = note.xpath('ancestor::tei:p[1]', namespaces=NS)[0]
                        text = ''.join(paragraph.itertext())
                        self.assertLess(text.index(('First', 'Second')[n-1] + ' verse.'), text.index(f'APPARATUS{n}'))
                        if parallel:
                            row = note.xpath('ancestor::p:parallel[1]', namespaces=NS)[0]
                            self.assertEqual(len(row.xpath(f'.//tei:milestone[@corresp="{URN}{n}"]', namespaces=NS)), 2)
                    if not parallel:
                        continue
                    tex = xslt_transform_string(XSLT_FILE, etree.tostring(root[0], encoding='unicode'),
                        xslt_params={'additional-preamble': '', 'additional-postamble': ''})
                    self.assertLess(tex.index('First verse.'), tex.index('APPARATUS1'))
                    self.assertLess(tex.index('Second verse.'), tex.index('APPARATUS2'))

    def test_id_targeted_milestone_note_survives_repeated_range_transclusion(self):
        for project in ('he', 'en'):
            self.write(project, 'index.xml', f'<tei:div corresp="{URN}unit">'
                       f'<j:transclude target="{URN}1"/><j:transclude target="{URN}1"/></tei:div>')
            self.write(project, 'source.xml', f'''<tei:div><tei:p>
              <tei:milestone xml:id="verse" unit="verse" corresp="{URN}1"/>Addressed words.
              <tei:milestone unit="verse" corresp="{URN}2"/>Outside the range.
              </tei:p></tei:div>''')
        path = self.base / 'en' / 'source.xml'
        tree = etree.parse(str(path))
        stand = etree.SubElement(tree.getroot(), f'{{{NS["tei"]}}}standOff', type='notes')
        note = etree.SubElement(stand, f'{{{NS["tei"]}}}note', type='commentary', target='#verse')
        note.text = 'ID APPARATUS'
        tree.write(str(path))
        self.db.remove_file('source.xml', 'en')
        self.db.index_file(path, 'en', 'source.xml')
        root = self.compile()
        notes = root.xpath('.//tei:body//tei:note', namespaces=NS)
        self.assertEqual(len(notes), 2)
        for note in notes:
            row = note.xpath('ancestor::p:parallelItem[1]', namespaces=NS)[0]
            text = ''.join(row.itertext())
            self.assertLess(text.index('Addressed words.'), text.index('ID APPARATUS'))
            self.assertNotIn('Outside the range', text)

    def test_instruction_annotation_stays_before_milestone_text_in_same_row(self):
        for project in ('he', 'en'):
            self.write(project, 'index.xml', f'<tei:div corresp="{URN}unit"><tei:p>'
                       f'<tei:milestone unit="verse" corresp="{URN}1"/>Verse words.'
                       '<tei:milestone unit="verse"/></tei:p></tei:div>')
        self.write('en', 'notes.xml',
                   f'<tei:note type="instruction" target="{URN}1">READ THIS</tei:note>'
                   f'<tei:note type="commentary" target="{URN}1">APPARATUS</tei:note>', notes=True)
        root = self.compile()
        note = root.xpath('.//tei:body//tei:note[@type="instruction"]', namespaces=NS)[0]
        row = note.xpath('ancestor::p:parallelItem[1]', namespaces=NS)[0]
        text = ''.join(row.itertext())
        self.assertLess(text.index('READ THIS'), text.index('Verse words.'))
        self.assertLess(text.index('Verse words.'), text.index('APPARATUS'))

    def test_structural_notes_in_both_pairing_paths_and_columns(self):
        for root_pair in (True, False):
            for apparatus in ('he', 'en', 'notes'):
                with self.subTest(root_pair=root_pair, apparatus=apparatus):
                    self.fixture(apparatus=apparatus, root_pair=root_pair)
                    self.assert_notes(self.compile(apparatus, parallel=False))
                    self.assert_notes(self.compile(apparatus), role='parallel' if apparatus == 'en' else 'primary')
                    self.assert_notes(self.compile(None), expected=0)
                    for project in ('he', 'en', 'notes'):
                        self.db.remove_project(project)

    def test_inner_targets_and_leading_text(self):
        for target in ('p', 'seg'):
            with self.subTest(target=target):
                self.fixture(target=target)
                root = self.compile()
                self.assert_notes(root, role='parallel')
                text = ''.join(root.xpath('.//tei:body', namespaces=NS)[0].itertext())
                self.assertEqual(text.count('Lead one'), 2)
                self.assertEqual(text.count(' tail two'), 2)
                for project in ('he', 'en'):
                    self.db.remove_project(project)

    def test_repeated_transclusion_keeps_each_occurrence(self):
        self.fixture(repeated=True)
        self.assert_notes(self.compile(), expected=6, role='parallel')

    def test_missing_counterpart_keeps_primary_apparatus(self):
        self.fixture()
        self.assert_notes(self.compile(projects=['missing']), role=None)

    def test_reversed_columns(self):
        self.fixture()
        self.assert_notes(self.compile(primary='en'), role='primary')

    def test_segment_in_primary_and_paragraph_in_apparatus_column(self):
        self.fixture(target='seg')
        for n in ('one', 'two'):
            self.write('en', n + '.xml',
                       f'<tei:div corresp="{URN}{n}"><tei:p corresp="{URN}{n}/inner">'
                       f'English {n}</tei:p></tei:div>')
        self.assert_notes(self.compile(), role='parallel')

    def test_annotations_survive_split_container_and_reach_tex(self):
        from opensiddur.common.xslt import xslt_transform_string
        from opensiddur.exporter.tex.latex import XSLT_FILE
        self.fixture(target='p')
        for project in ('he', 'en'):
            for n in ('one', 'two'):
                self.write(
                    project, n + '.xml',
                    f'<tei:div corresp="{URN}{n}"><tei:p corresp="{URN}{n}/inner">'
                    f'Leading {n}<tei:milestone unit="verse" corresp="{URN}{n}/v1"/>'
                    f'First verse<tei:milestone unit="verse" corresp="{URN}{n}/v2"/>'
                    'Second verse</tei:p></tei:div>')
        root = self.compile()
        self.assert_notes(root, role='parallel')
        tex = xslt_transform_string(XSLT_FILE, etree.tostring(root[0], encoding='unicode'),
                                    xslt_params={'additional-preamble': '', 'additional-postamble': ''})
        for n in ('one', 'two'):
            for i in (1, 2):
                self.assertEqual(tex.count(f'Note {n} {i}'), 1)
        self.assertIn(r'\begin{Rightside}', tex)
        right = tex.split(r'\begin{Rightside}', 1)[1].split(r'\end{Rightside}', 1)[0]
        self.assertEqual(right.count(r'\Bfootnote{'), 4)

    def test_failed_counterpart_restores_context_and_apparatus(self):
        self.fixture()
        original = ExternalCompilerProcessor._process_element

        def fail_parallel(processor, element, root=None):
            if processor.project == 'en':
                raise ValueError('synthetic counterpart failure')
            return original(processor, element, root)

        with patch.object(ExternalCompilerProcessor, '_process_element', fail_parallel):
            self.assert_notes(self.compile())

    def test_range_omits_outside_notes_in_marker_mode(self):
        self.fixture(target='p')
        data = LinearData()
        data.xml_cache.base_path = self.base
        data.annotation_projects = ['en']
        # The annotated paragraph is outside the requested range; only its hi is selected.
        path = '/tei:TEI/tei:text/tei:body/tei:div/tei:p/tei:hi'
        proc = ExternalCompilerProcessor('en', 'one.xml', from_start=path, to_end=path,
                                         linear_data=data, reference_database=self.db)
        proc.marker_stack = []
        root = etree.Element('result')
        root.extend(proc.process())
        text = ''.join(root.itertext())
        self.assertNotIn('Lead one', text)
        self.assertNotIn('tail one', text)
        self.assertNotIn('Note two', text)
        self.assertIn('middle', text)

    def test_false_condition_does_not_emit_structural_notes(self):
        self.fixture()
        for project in ('he', 'en'):
            body = f'''<tei:div corresp="{URN}unit">
              <j:declare xml:id="d"><tei:fs type="demo"><tei:f name="show"><tei:binary value="false"/></tei:f></tei:fs></j:declare>
              <j:conditional xml:id="c"><tei:fs type="demo"><tei:f name="show"><tei:binary value="true"/></tei:f></tei:fs></j:conditional>
              <j:transclude target="{URN}one"/>
              <j:endConditional target="#c"/><j:endDeclare target="#d"/>
              <j:transclude target="{URN}two"/>
            </tei:div>'''
            self.write(project, 'index.xml', body)
        root = self.compile()
        notes = root.xpath('.//tei:body//tei:note[@type="commentary"]', namespaces=NS)
        self.assertEqual([''.join(n.itertext()) for n in notes], ['Note two 1', 'Note two 2'])

    def test_local_id_annotation_on_structural_target(self):
        self.fixture()
        for project in ('he', 'en'):
            path = self.base / project / 'one.xml'
            tree = etree.parse(str(path))
            target = tree.find('.//tei:p', NS)
            target.set('{http://www.w3.org/XML/1998/namespace}id', 'local')
            if project == 'en':
                stand = etree.SubElement(tree.getroot(), f'{{{NS["tei"]}}}standOff', type='notes')
                note = etree.SubElement(stand, f'{{{NS["tei"]}}}note', type='commentary', target='#local')
                note.text = 'Local note'
            tree.write(str(path))
            self.db.remove_file('one.xml', project)
            self.db.index_file(path, project, 'one.xml')
        root = self.compile()
        notes = root.xpath('.//tei:body//tei:note[.="Local note"]', namespaces=NS)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].getparent().tag, f'{{{NS["tei"]}}}p')
        self.assertEqual(notes[0].xpath('ancestor::p:parallelItem/@role', namespaces=NS), ['parallel'])

    def test_bookmark_depth_survives_splits_and_nested_transclusions(self):
        from opensiddur.common.xslt import xslt_transform_string
        from opensiddur.exporter.tex.latex import XSLT_FILE
        for project in ('he', 'en'):
            self.write(project, 'index.xml', f'''<tei:div corresp="{URN}unit">
              <tei:head>Days</tei:head>
              <tei:div><tei:head>First</tei:head><tei:p>One.</tei:p></tei:div>
              <j:transclude target="{URN}second"/>
              <tei:div><tei:head>Third</tei:head><tei:p>Three.</tei:p></tei:div>
              </tei:div><tei:div><tei:head>Next</tei:head><tei:p>Next section.</tei:p></tei:div>''')
            self.write(project, 'second.xml', f'''<tei:div corresp="{URN}second">
              <tei:head>Second</tei:head><tei:p>Two.</tei:p>
              <j:transclude target="{URN}nested"/></tei:div>''')
            self.write(project, 'nested.xml', f'''<tei:div corresp="{URN}nested">
              <tei:head>Nested</tei:head><tei:p>Nested text.</tei:p></tei:div>''')
        for parallel in (False, True):
            with self.subTest(parallel=parallel):
                root = self.compile(apparatus=None, parallel=parallel)
                heads = root.xpath('.//tei:head', namespaces=NS)
                expected = {'Days': '1', 'First': '2', 'Second': '2', 'Nested': '3', 'Third': '2', 'Next': '1'}
                self.assertEqual({h.text for h in heads}, set(expected))
                for head in heads:
                    self.assertEqual(head.get(f'{{{NS["p"]}}}heading-level'), expected[head.text])
                tex = xslt_transform_string(XSLT_FILE, etree.tostring(root[0], encoding='unicode'))
                for title, level in expected.items():
                    outline = next(line for line in tex.splitlines()
                                   if 'addcontentsline' in line and title in line)
                    toc = {'1': 'section', '2': 'subsection', '3': 'subsubsection'}[level]
                    self.assertIn('{toc}{' + toc + '}', outline)

    def test_range_heading_depth_excludes_unselected_ancestor_heading(self):
        self.write('he', 'index.xml', f'''<tei:div><tei:head>Unselected</tei:head>
          <tei:div corresp="{URN}selected"><tei:head>Selected</tei:head><tei:p>Text.</tei:p></tei:div>
          </tei:div>''')
        data = LinearData()
        data.xml_cache.base_path = self.base
        tree = etree.parse(str(self.base / 'he/index.xml'))
        selected = tree.xpath('//*[@corresp]')[0]
        processor = ExternalCompilerProcessor('he', 'index.xml',
            from_start=tree.getpath(selected), to_end=tree.getpath(selected),
            linear_data=data, reference_database=self.db)
        result = processor.process()
        heads = [h for el in result for h in el.xpath('.//tei:head', namespaces=NS)]
        self.assertEqual([(h.text, h.get(f'{{{NS["p"]}}}heading-level')) for h in heads], [('Selected', '1')])
        self.assertEqual(data.heading_depth, 0)
