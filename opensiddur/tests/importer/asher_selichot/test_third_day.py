"""Numbered-day structure across reordered facsimiles and Hebrew-only rubrics."""
import json
import tempfile
import unittest
from pathlib import Path
from lxml import etree
from opensiddur.importer.asher_selichot.build import TEI, XML, J, poem
from opensiddur.importer.asher_selichot.second_day import numbered_documents, printed_unit
from opensiddur.tests.importer.asher_selichot import test_second_day as fixtures
from opensiddur.importer.scan.reverse import streams


class ThirdDayTest(unittest.TestCase):
    def test_reordered_source_pages_and_closed_day_specific_expansions(self):
        opening={'id':'opening_instruction','kind':'rubric','fragments':[fixtures.SecondDayTest.fragment('s60','Say אשרי','Say Happy.') ]}
        readings=[opening]+[{'id':'part_'+str(n),'kind':'prose','fragments':[fixtures.SecondDayTest.fragment('s'+str(n),'טקסט׃')]} for n in [62,66,64,68]]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)
            (source/'third-day.json').write_text(json.dumps({'heading':{'he':'סליחות ליום שלישי','en':'THIRD DAY'},'units':readings}))
            docs=list(numbered_documents(source,'third'))
        self.assertEqual(['third_day.xml']*2,[d[1] for d in docs])
        for project,name,root in docs:
            self.assertEqual('urn:x-opensiddur:text:siddur:selichot/third_day',root.find(f'.//{{{TEI}}}body/{{{TEI}}}div').get('corresp'))
            ids=[n.get(XML+'id') for n in root.findall(f'.//{{{J}}}conditional')]
            self.assertEqual(['third_opening_instruction_printed','third_opening_instruction_expanded'],ids)
            self.assertEqual(['#'+id for id in ids],[n.get('target') for n in root.findall(f'.//{{{J}}}endConditional')])
            expected=['n61.jpg','n65.jpg','n63.jpg','n67.jpg'] if project.startswith('asher_selichot_he') else ['n62.jpg','n66.jpg','n64.jpg','n68.jpg']
            self.assertEqual(expected,[n.get('facs').split('/')[-1].replace('_medium','') for n in root.findall(f'.//{{{TEI}}}pb')][-4:])

    def test_hebrew_only_rubric_keeps_its_own_language(self):
        root=etree.Element('{'+TEI+'}div');root.set(XML+'lang','he')
        reading={'kind':'rubric','fragments':[fixtures.SecondDayTest.fragment('s66','כרחם אב · יי שמעה')]}
        unit=printed_unit(root,reading,'he','urn:x-opensiddur:text:siddur:fixture')
        self.assertEqual('he',unit.find(f'{{{TEI}}}note').get(XML+'lang'))
        self.assertEqual({('s66','he'):'כרחם אב · יי שמעה'},streams(root,include_notes=True))

    def test_english_running_header_is_not_a_pizmon_heading(self):
        root=poem('en','fixture',{'running_header':'PROPITIATORY PRAYERS FOR THE FIRST DAY.','rubric':'Repeat the refrain.','stanzas':['Opening.'], 'cues':{}, 'conclusion':'Say the prayer.'})
        self.assertIsNone(root.find(f'.//{{{TEI}}}head'))
        self.assertNotIn('PROPITIATORY PRAYERS',' '.join(root.itertext()))
