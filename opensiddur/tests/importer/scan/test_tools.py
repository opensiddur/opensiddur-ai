import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from lxml import etree
from opensiddur.importer.scan import pages, reverse, compare
from opensiddur.importer.asher_selichot.download import derive_pages

class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def profile(self,name):
        p=pages.BookProfile.for_book(name,self.root/'sources',self.root/'output')
        p.source_directory.mkdir(parents=True)
        p.page_map.write_text(json.dumps({'identifier':p.archive_identifier,'pages':[
            {'scan_page':1,'ia_leaf':0,'printed_page':'11','language':'he','facs':'x'},
            {'scan_page':2,'ia_leaf':1,'printed_page':'11','language':'en','facs':'y'}]}))
        return p
    def test_duplicate_labels_and_cache_isolation(self):
        a,b=self.profile('asher_selichot'),self.profile('birnbaum_siddur')
        self.assertEqual(0,pages.lookup(a,'s1').leaf)
        with self.assertRaises(pages.ScanError):pages.lookup(a,'11')
        self.assertNotEqual(a.cache_directory,b.cache_directory)
        self.assertNotEqual(a.source_directory,b.source_directory)
        p=a.cache_directory/'pages/s1.jpg';p.parent.mkdir(parents=True);p.write_bytes(b'existing')
        archive=Mock();self.assertEqual(p,pages.fetch(a,'s1',archive=archive));archive.session.get.assert_not_called()
    def test_map_identity_mismatch(self):
        p=self.profile('asher_selichot');p.page_map.write_text('{"identifier":"other","pages":[]}')
        with self.assertRaises(pages.ScanError):pages.load_pages(p)
    def test_metadata_correction_requires_evidence_and_reciprocal_pairing(self):
        scan=b'<book><pageData><page leafNum="0"/><page leafNum="1"/></pageData></book>'
        machine={'pages':[{'leafNum':0,'pageNumber':'1'}]}
        result=derive_pages('item',scan,machine,{'0':{'printed_page':'14','evidence':'image'}})
        self.assertEqual('14',result['pages'][0]['printed_page']);self.assertEqual('1',result['pages'][0]['machine_page_candidate'])
        self.assertIsNone(result['pages'][1]['printed_page'])
        with self.assertRaises(ValueError):derive_pages('item',scan,machine,{'0':{'printed_page':'14'}})
        with self.assertRaises(ValueError):derive_pages('item',scan,machine,{'0':{'evidence':'image','facing_leaf':1}})
    def test_english_errors_and_hebrew_points(self):
        result=compare.compare('mercy and truth.','rnercy and truth,')
        self.assertEqual(2,len(result.differences));self.assertTrue(all(d.bucket==compare.CONSONANTS for d in result.differences))
        result=compare.compare('כָּל','כַל');self.assertEqual(compare.VOWELS,result.differences[0].bucket)
        self.assertEqual(['stale'],result.apply_verdicts({'stale':compare.PRINT}))
    def test_reverse_uses_printed_choice_and_scan_identity(self):
        root=etree.fromstring('''<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="he"><text><body><div><pb n="11" facs="https://example/page/n23_medium.jpg"/><p>א <choice><abbr>ב</abbr><expan>ג ד</expan></choice> ה</p><pb n="11" facs="https://example/page/n24_medium.jpg"/><p xml:lang="en">cue</p></div></body></text></TEI>''')
        actual=reverse.streams(root);self.assertEqual('א ב ה',actual[('s24','he')]);self.assertEqual('cue',actual[('s25','en')])
        self.assertEqual({},reverse.check(actual,actual))
        broken=dict(actual);broken[('s24','he')]='א ב';self.assertTrue(reverse.check(broken,actual))
        with self.assertRaises(ValueError):reverse.check({},actual)
