"""Monday fast is a weekday occasion, with asymmetric printed refrain cues."""
import unittest
from unittest.mock import patch
from lxml import etree
from opensiddur.importer.asher_selichot import penitential_days as service
from opensiddur.importer.asher_selichot.build import TEI, XML

class MondayFastTests(unittest.TestCase):
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
