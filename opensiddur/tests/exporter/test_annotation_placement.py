"""A structural annotation is anchored on the first words of what it annotates."""
import unittest

from lxml import etree

from opensiddur.exporter.annotation_placement import (
    find_text_slot,
    place_structural_annotations,
    place_structural_annotations_in_stream,
    place_structural_annotations_in_tree,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS

NS = {'tei': TEI_NS, 'p': PROCESSING_NAMESPACE, 'j': JLPTEI_NAMESPACE}
URN = 'urn:x-opensiddur:text:prayer:demo/1'


def parse(xml: str):
    return etree.fromstring(
        f'<root xmlns:tei="{TEI_NS}" xmlns:p="{PROCESSING_NAMESPACE}" '
        f'xmlns:j="{JLPTEI_NAMESPACE}">{xml}</root>')


def note(text='APPARATUS', **attrib):
    element = etree.Element(f'{{{TEI_NS}}}note', **attrib)
    element.text = text
    return element


class TestPlacementInATree(unittest.TestCase):
    def place(self, xml, notes=None):
        target = parse(xml)[0]
        notes = notes or [note()]
        placed = place_structural_annotations_in_tree(target, notes)
        return placed, target

    def test_anchor_lands_after_the_first_alignment_milestone(self):
        """The whole point: the note joins the row its words are in, not the one before."""
        placed, target = self.place(
            f'<tei:div><tei:p><tei:milestone unit="verse" corresp="{URN}"/>'
            'He will give his angels charge over you.</tei:p></tei:div>')
        self.assertTrue(placed)
        self.assertEqual(''.join(target.itertext()),
                         'APPARATUSHe will give his angels charge over you.')
        milestone = target.xpath('.//tei:milestone', namespaces=NS)[0]
        self.assertIs(milestone.getnext(), target.xpath('.//tei:note', namespaces=NS)[0])

    def test_a_heading_is_skipped(self):
        placed, target = self.place(
            '<tei:div><tei:head>Shalom Aleichem</tei:head>'
            '<tei:p>Peace be with you.</tei:p></tei:div>')
        self.assertTrue(placed)
        anchor = target.xpath('.//tei:note', namespaces=NS)[0]
        self.assertEqual(anchor.getparent().tag, f'{{{TEI_NS}}}p')
        self.assertEqual(''.join(target.itertext()),
                         'Shalom AleichemAPPARATUSPeace be with you.')

    def test_the_target_s_own_leading_text_wins(self):
        placed, target = self.place('<tei:div>Lead<tei:p>Later</tei:p></tei:div>')
        self.assertTrue(placed)
        self.assertEqual(''.join(target.itertext()), 'APPARATUSLeadLater')

    def test_leading_whitespace_stays_in_front_of_the_anchor(self):
        """Indentation is not a word; the mark belongs against the first one."""
        placed, target = self.place('<tei:div><tei:p>\n      Words.</tei:p></tei:div>')
        self.assertTrue(placed)
        paragraph = target.xpath('.//tei:p', namespaces=NS)[0]
        self.assertEqual(paragraph.text, '\n      ')
        self.assertEqual(paragraph[0].tail, 'Words.')

    def test_the_search_stops_in_front_of_a_rubric(self):
        """An instruction is a block of its own, so the anchor goes before it."""
        placed, target = self.place(
            '<tei:div><tei:head>A Heading</tei:head>'
            '<tei:note type="instruction">Recited standing.</tei:note></tei:div>')
        self.assertTrue(placed)
        anchor = target.xpath('.//tei:note[not(@type)]', namespaces=NS)[0]
        self.assertEqual(anchor.getnext().get('type'), 'instruction')

    def test_a_note_body_is_not_mistaken_for_the_target_s_text(self):
        placed, target = self.place(
            '<tei:div><tei:note type="instruction">Recited standing.</tei:note>'
            '<tei:p>Words.</tei:p></tei:div>')
        self.assertTrue(placed)
        anchor = target.xpath('.//tei:note[not(@type)]', namespaces=NS)[0]
        self.assertEqual(anchor.getnext().get('type'), 'instruction')
        self.assertEqual(anchor.getparent().tag, f'{{{TEI_NS}}}div')

    def test_apparatus_parked_in_a_milestone_is_left_alone(self):
        """Those notes belong to place_milestone_annotations, and are not text."""
        placed, target = self.place(
            f'<tei:div><tei:p><tei:milestone unit="verse" corresp="{URN}">'
            '<tei:note>PARKED</tei:note></tei:milestone>Words.</tei:p></tei:div>')
        self.assertTrue(placed)
        anchors = target.xpath('.//tei:milestone/following-sibling::tei:note',
                               namespaces=NS)
        self.assertEqual([a.text for a in anchors], ['APPARATUS'])

    def test_several_notes_keep_their_order(self):
        notes = [note('ONE'), note('TWO')]
        placed, target = self.place('<tei:div><tei:p>Words.</tei:p></tei:div>', notes)
        self.assertTrue(placed)
        self.assertEqual(''.join(target.itertext()), 'ONETWOWords.')

    def test_an_empty_target_has_no_slot(self):
        placed, target = self.place('<tei:div/>')
        self.assertFalse(placed)
        self.assertEqual(len(target), 0)

    def test_a_heading_only_target_has_no_slot(self):
        placed, _ = self.place('<tei:div><tei:head>A Heading</tei:head></tei:div>')
        self.assertFalse(placed)

    def test_a_transcluded_target_has_no_slot(self):
        """Those words belong to another document and another alignment row."""
        placed, _ = self.place(
            '<tei:div><p:transclude target="urn:x-opensiddur:text:prayer:other">'
            '<tei:p>Someone else’s words.</tei:p></p:transclude></tei:div>')
        self.assertFalse(placed)

    def test_a_second_placement_joins_the_first_anchor(self):
        """The slot is gone, but the note still belongs with the same words."""
        placed, target = self.place('<tei:div><tei:p>Words.</tei:p></tei:div>')
        self.assertTrue(placed)
        self.assertTrue(place_structural_annotations_in_tree(target, [note('SECOND')]))
        self.assertEqual(''.join(target.itertext()), 'SECONDAPPARATUSWords.')


class TestPlacementInAMarkerStream(unittest.TestCase):
    """The flat form the external compiler builds: carriers, not nesting."""

    @staticmethod
    def stream(xml):
        return list(parse(xml))

    def test_the_opening_carrier_s_tail_is_the_first_candidate(self):
        stream = self.stream('<tei:div p:start="a"/><tei:div p:end="a"/>')
        stream[0].tail = '\n  Lead words.'
        anchor = note()
        self.assertTrue(place_structural_annotations_in_stream(stream, stream[0], [anchor]))
        self.assertEqual(stream[0].tail, '\n  ')
        self.assertIs(stream[1], anchor)
        self.assertEqual(anchor.tail, 'Lead words.')

    def test_the_anchor_crosses_the_first_milestone(self):
        stream = self.stream(
            f'<tei:div p:start="a"/><tei:p p:start="b"/>'
            f'<tei:milestone unit="verse" corresp="{URN}"/><tei:p p:end="b"/>'
            '<tei:div p:end="a"/>')
        stream[2].tail = 'Verse words.'
        anchor = note()
        self.assertTrue(place_structural_annotations_in_stream(stream, stream[0], [anchor]))
        self.assertEqual(stream.index(anchor), 3)
        self.assertEqual(anchor.tail, 'Verse words.')

    def test_a_suspend_carrier_ends_the_search(self):
        """Past it the row belongs to a transclusion, not to this element."""
        stream = self.stream(
            '<tei:div p:start="a"/><tei:div p:suspend="a"/><tei:div p:resume="a"/>'
            '<tei:div p:end="a"/>')
        stream[2].tail = 'Words after the transclusion.'
        self.assertFalse(place_structural_annotations_in_stream(stream, stream[0], [note()]))

    def test_no_text_anywhere_in_the_scope(self):
        stream = self.stream('<tei:div p:start="a"/><tei:p p:start="b"/>'
                             '<tei:p p:end="b"/><tei:div p:end="a"/>')
        self.assertFalse(place_structural_annotations_in_stream(stream, stream[0], [note()]))


class TestFindTextSlot(unittest.TestCase):
    def test_no_notes_is_not_a_placement(self):
        target = parse('<tei:div><tei:p>Words.</tei:p></tei:div>')[0]
        self.assertFalse(place_structural_annotations(list(target), []))

    def test_whitespace_only_text_is_not_a_slot(self):
        target = parse('<tei:div>\n  <tei:p>\n  </tei:p>\n</tei:div>')[0]
        self.assertIsNone(find_text_slot(list(target), owner=target))


if __name__ == '__main__':
    unittest.main()
