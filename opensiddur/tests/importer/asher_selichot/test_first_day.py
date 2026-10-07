"""Synthetic checks for source boundaries, page crossings and printed apparatus."""
import unittest
from lxml import etree
from opensiddur.importer.asher_selichot.first_day import section, TEI, XML
from opensiddur.importer.scan.reverse import streams


class FirstDayTest(unittest.TestCase):
    def fragment(self, scan, text, notes=(), kind='prose'):
        return {'he': {'scan':scan,'printed_page':'16','text':text},
                'en': {'scan':scan,'printed_page':'16','text':text},
                'notes': {'he':list(notes),'en':list(notes)}}

    def render(self, fragments, lang='en', kind='prose'):
        return section(lang,'fixture','closing',[{'id':'test','kind':kind,'fragments':fragments}])

    def test_page_crossing_retains_one_paragraph_and_joins_word(self):
        first=self.fragment('s35','a trans');first['en']['join_next']=True
        root=self.render([first,self.fragment('s37','gression ends.')])
        paragraphs=root.findall(f'.//{{{TEI}}}body//{{{TEI}}}p')
        self.assertEqual(1,len(paragraphs))
        self.assertEqual('a transgression ends.', ''.join(paragraphs[0].itertext()).strip())
        self.assertEqual({('s35','en'):'a trans',('s37','en'):'gression ends.'},streams(root))
        self.assertIn('/n36_medium.jpg',paragraphs[0].find(f'{{{TEI}}}pb').get('facs'))

    def test_repeated_anchor_places_distinct_notes_once_in_source_order(self):
        root=self.render([self.fragment('s35','as written, first. as written, second.',
            [{'anchor':'as written,','text':'First citation.'},{'anchor':'as written,','text':'Second citation.'}])])
        notes=root.findall(f'.//{{{TEI}}}note')
        self.assertEqual(['First citation.','Second citation.'],[n.text for n in notes])
        self.assertEqual(' first. as written,',notes[0].tail)
        self.assertEqual(' second. ',notes[1].tail)

    def test_missing_footnote_anchor_fails_before_authoring(self):
        with self.assertRaisesRegex(ValueError,'Footnote anchor absent'):
            self.render([self.fragment('s35','Different words.',[{'anchor':'not here','text':'note'}])])

    def test_mixed_final_rubric_preserves_languages_and_stops_at_boundary(self):
        root=self.render([self.fragment('s52','The Reader says קדיש תתקבל.')],lang='he',kind='rubric')
        note=root.find(f'.//{{{TEI}}}note')
        self.assertEqual('en',note.get(XML+'lang'))
        self.assertEqual('he',note.find(f'{{{TEI}}}foreign').get(XML+'lang'))
        self.assertEqual('The Reader says קדיש תתקבל.', ''.join(note.itertext()).strip())
        self.assertNotIn('SECOND DAY',etree.tostring(root,encoding='unicode'))

    def test_litany_has_printed_line_breaks_and_reader_note_once(self):
        words='\n'.join(f'Answer {n}.' for n in range(1,10))
        root=self.render([self.fragment('s47',words,[{'anchor':'Answer 8.','text':'Numbers xxv 7.'}])],kind='litany')
        self.assertEqual(8,len(root.findall(f'.//{{{TEI}}}lb')))
        self.assertEqual(1,len(root.findall(f'.//{{{TEI}}}note')))
        self.assertEqual(' '.join(words.split()),streams(root)[('s47','en')])
