"""Numbered services preserve edition-dependent stanza and rubric structure."""
import unittest
from lxml import etree
from opensiddur.importer.asher_selichot.second_day import pizmon, TEI


class NumberedDaysTest(unittest.TestCase):
    def test_differing_translation_page_boundaries_and_unprinted_refrain(self):
        def fragment(scan, he, en):
            return {'he':{'scan':f's{scan}','printed_page':'36','text':he},
                    'en':{'scan':f's{scan+1}','printed_page':'36','text':en},
                    'notes':{'he':[],'en':[]}}
        reading={'urn':'urn:x-opensiddur:text:poem:fixture','title_he':'שיר',
                 'heading_before_rubric':True,'stanzas':[
                     {'id':'first','fragments':[fragment(74,'שיר ·','Song.')],
                      'refrain':{'he':'עננו׃','en':'Answer us.'}},
                     {'id':'last','fragments':[fragment(74,'','In'),fragment(76,'אחרון׃','judgment.')],
                      'refrain':{'he':'עננו׃','en':''},
                      'opening_cue':{'he':'שיר וכו׳','en':'(Song &c.)'}}]}
        root=pizmon('en','fixture',reading,{'he':'עננו׃','en':'Answer us.'})
        div=root.find(f'.//{{{TEI}}}body/{{{TEI}}}div')
        self.assertIsNone(div.find(f'{{{TEI}}}head'))
        blocks=div.findall(f'{{{TEI}}}p')
        self.assertEqual(2,len(blocks))
        self.assertEqual('In',''.join(blocks[1].itertext()).split()[0])
        self.assertEqual(1,len(blocks[1].findall(f'{{{TEI}}}pb')))
        self.assertEqual('',''.join(blocks[1].find(f'{{{TEI}}}seg').itertext()))
        self.assertEqual('Song. Answer us.',''.join(blocks[1].find(f'{{{TEI}}}choice/{{{TEI}}}expan').itertext()))
        he=pizmon('he','fixture',reading,{'he':'עננו׃','en':'Answer us.'})
        self.assertEqual(2,len(he.findall(f'.//{{{TEI}}}lg')))
        self.assertNotIn('In',' '.join(he.find(f'.//{{{TEI}}}body').itertext()))

    def test_each_numbered_day_keeps_its_own_top_level_bookmark(self):
        from opensiddur.importer.asher_selichot.check_book_pdf import day_bookmarks
        words=['FIRST','SECOND','THIRD','FOURTH','FIFTH','SIXTH','SEVENTH']
        rows=[r for i,word in enumerate(words) for r in [(0,word+' DAY',i*10+1,600),(1,'פזמון',i*10+3,600)]]
        self.assertEqual(rows[::2],day_bookmarks(rows,[word+' DAY' for word in words]))
        rows[-2]=(1,*rows[-2][1:])
        with self.assertRaises(ValueError):day_bookmarks(rows,[word+' DAY' for word in words])

    def test_mixed_footnote_keeps_hebrew_language_and_anchor(self):
        from opensiddur.importer.asher_selichot.first_day import words_with_notes
        from opensiddur.importer.asher_selichot.build import XML
        node=etree.Element(f'{{{TEI}}}p')
        words_with_notes(node,'A friend is remembered.',[{'anchor':'friend','text':'קרן הפוך is an allusion to Job.'}],'en')
        note=node.find(f'{{{TEI}}}note')
        self.assertEqual('en',note.get(XML+'lang'))
        self.assertEqual('he',note.find(f'{{{TEI}}}foreign').get(XML+'lang'))
        self.assertEqual('A friend',node.text)
        self.assertEqual(' is remembered.',note.tail)
        self.assertEqual('קרן הפוך is an allusion to Job.',''.join(note.itertext()))

    def test_english_word_join_retains_source_page_break(self):
        from opensiddur.importer.asher_selichot.second_day import printed_unit
        node=etree.Element(f'{{{TEI}}}body')
        def fragment(scan,text,join=False):
            return {'he':{'scan':f's{scan}','printed_page':'39','text':'שיר'},
                    'en':{'scan':f's{scan+1}','printed_page':'39','text':text,'join_next':join},
                    'notes':{'he':[],'en':[]}}
        printed_unit(node,{'kind':'poem','fragments':[fragment(80,'sacri',True),fragment(82,'fices.')]},'en','urn:x-opensiddur:text:poem:fixture')
        para=node.find(f'.//{{{TEI}}}p')
        self.assertEqual('sacrifices.',''.join(para.itertext()).strip())
        self.assertIn('/n82_medium.jpg',para.find(f'{{{TEI}}}pb').get('facs'))
