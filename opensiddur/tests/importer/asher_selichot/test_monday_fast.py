"""Monday fast is a weekday occasion, with asymmetric printed refrain cues."""
import unittest
from unittest.mock import patch
from lxml import etree
from opensiddur.importer.asher_selichot import penitential_days as service
from opensiddur.importer.asher_selichot.build import TEI, XML

class MondayFastTests(unittest.TestCase):
    def test_thursday_uses_weekday_five(self):
        from opensiddur.importer.asher_selichot.first_day import entry
        with patch('opensiddur.importer.asher_selichot.first_day.titles'):
            root=entry('he','example',{},book=True,remaining_services=('thursday-fast',))
        node=root.find('.//{'+service.J+'}conditional[@xml:id="thursday_fast_occasion"]',namespaces={'xml':XML[1:-1]})
        self.assertEqual([(fs.get('type'),fs[0].get('name'),fs[0][0].get('value')) for fs in node.findall('.//{'+TEI+'}fs')], [('asher:occasion','thursday_fast','true'),('opensiddur:day-of-week','hebrew-day','5')])
        self.assertIsNone(node.find('.//{'+TEI+'}note'))

    def test_identity_and_occasion_are_distinct_from_penitential_ordinals(self):
        from opensiddur.importer.asher_selichot.first_day import entry
        self.assertEqual(service.service_urn('monday-fast'),'urn:x-opensiddur:text:siddur:selichot/monday_fast')
        self.assertNotIn('monday-fast',service.DAYS)
        with patch('opensiddur.importer.asher_selichot.first_day.titles'):
            root=entry('he','example',{},book=True,remaining_services=('monday-fast',))
        gate=root.find('.//{'+service.J+'}conditional[@xml:id="monday_fast_occasion"]',namespaces={'xml':XML[1:-1]})
        self.assertEqual([(fs.get('type'),fs[0].get('name'),fs[0][0].get('value'))for fs in gate.findall('.//{'+TEI+'}fs')],[('asher:occasion','monday_fast','true'),('opensiddur:day-of-week','hebrew-day','2')])
        self.assertIsNone(gate.find('.//{'+TEI+'}note'))
        self.assertNotIn('override',etree.tostring(gate).decode())

    def test_hebrew_opening_repeat_does_not_invent_english_cue(self):
        he={'he':{'scan':'s330','printed_page':'164','text':'מלאכי וכו׳'},'notes':{'he':[]}}
        en={'en':{'scan':'s331','printed_page':'164','text':'The time of his redemption.'},'notes':{'en':[]}}
        reading={'fragments':[he],'stanzas':[{'fragments':[{'he':{'scan':'s328','printed_page':'163','text':'מַלְאֲכֵי רַחֲמִים׃'},'notes':{'he':[]}}]},{'fragments':[he]}],'refrain_cues':{'he':'אולי יחום'},'opening_cue':{'he':'מלאכי וכו׳'},'refrain':{'he':'אוּלַי יָחוּם׃'}}
        root=etree.Element('{'+TEI+'}body');service.pizmon(root,reading,'he','urn:example')
        self.assertEqual(root.find('.//{'+TEI+'}expan').text,'מַלְאֲכֵי רַחֲמִים׃')
        reading.update(fragments=[en],stanzas=[{'fragments':[en]}],refrain_cues={'en':r'\(Perchance, &c\.\)'},refrain={'en':'Perchance he will have mercy.'})
        root=etree.Element('{'+TEI+'}body');service.pizmon(root,reading,'en','urn:example')
        self.assertEqual(len(root.findall('.//{'+TEI+'}choice')),0)
        self.assertEqual(' '.join(''.join(root.itertext()).split()),'The time of his redemption.')

    def test_hebrew_only_repeat_retains_paired_expanded_boundary(self):
        fragment={'he':{'scan':'s346','printed_page':'172','text':'כרחם אב׃'},'en':{'scan':'s347','printed_page':'172','text':''},'notes':{'he':[],'en':[]}}
        reading={'id':'verses_after_haazinah','kind':'rubric','fragments':[fragment],'expansion_targets':{'he':['urn:x-opensiddur:text:prayer:keraham_av'],'en':[]}}
        manifest={'heading':{'he':'לשני','en':'Monday'}}
        with patch.object(service,'readings',return_value=(manifest,[reading])):
            authored=list(service.documents(None,'last-monday-fast'))
        for project,name,root in authored:
            milestones=root.findall('.//{'+TEI+'}milestone[@corresp]')
            self.assertEqual([n.get('corresp')for n in milestones],['urn:x-opensiddur:text:siddur:selichot/last_monday_fast/verses_after_haazinah/expanded'])
            self.assertEqual(len(root.findall('.//{'+service.J+'}transclude')),1 if '_he_'in project else 0)
            self.assertEqual(len(root.findall('.//{'+service.J+'}conditional')),2)

    def test_attributes_before_poem_remain_prose(self):
        fragment={'he':{'scan':'s348','printed_page':'173','text':'יי · אל · רחום׃'},'notes':{'he':[]}}
        reading={'fragments':[fragment],'stanzas':[{'fragments':[fragment],'prose':True}],'refrain_cues':{'he':'(?!)'},'refrain':{'he':''}}
        root=etree.Element('{'+TEI+'}body');service.pizmon(root,reading,'he','urn:example')
        self.assertEqual(len(root.findall('.//{'+TEI+'}p')),1)
        self.assertEqual(len(root.findall('.//{'+TEI+'}lg')),0)
        self.assertEqual(''.join(root.itertext()).strip(),'יי · אל · רחום׃')
