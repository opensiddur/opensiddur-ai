"""Dynamic references must follow surviving content and its source edition."""
import unittest
from lxml import etree
from opensiddur.exporter.tex.page_references import resolve_page_references
from opensiddur.tests.exporter.test_reledmac_xslt import _transform


class TestPageReferences(unittest.TestCase):
    def document(self, body):
        return etree.fromstring(f'''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
            xmlns:p="http://jewishliturgy.org/ns/processing" p:project="he">
            <tei:text><tei:body>{body}</tei:body></tei:text></tei:TEI>''')

    def test_edition_and_first_occurrence(self):
        root = self.document('''<tei:note type="instruction">See page
            <tei:ref type="page" target="urn:prayer@en"/></tei:note>
            <tei:div corresp="urn:prayer"><tei:p>Hebrew</tei:p></tei:div>
            <p:transclude p:project="en"><tei:div corresp="urn:prayer">
            <tei:p>English</tei:p></tei:div></p:transclude>
            <p:transclude p:project="en"><tei:div corresp="urn:prayer">
            <tei:p>Repeated</tei:p></tei:div></p:transclude>''')
        resolve_page_references(root)
        anchors = root.xpath('//*[local-name()="anchor"]')
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0].getparent().getparent().get('{http://jewishliturgy.org/ns/processing}project'), 'en')
        tex = _transform(etree.tostring(root, encoding='unicode'))
        label = anchors[0].get('n')
        self.assertIn('\\pageref{' + label + '}', tex)
        self.assertEqual(tex.count('\\label{' + label + '}'), 1)

    def test_missing_clause_preserves_other_instructions_and_tail(self):
        root = self.document('''<tei:note type="instruction">Keep this.
            <tei:seg type="optional-page-reference">Missing service, page
            <tei:ref type="page" target="urn:missing@he"/>.</tei:seg> Continue here.
            <tei:seg type="optional-page-reference">Present service, page
            <tei:ref type="page" target="urn:present@he"/>.</tei:seg></tei:note>
            <tei:p><tei:milestone unit="prayer-part" corresp="urn:present"/>Text</tei:p>''')
        resolve_page_references(root)
        tex = _transform(etree.tostring(root, encoding='unicode'))
        self.assertNotIn('Missing service', tex)
        self.assertIn('Keep this.', tex)
        self.assertIn('Continue here.', tex)
        self.assertIn('Present service', tex)
        self.assertIn('\\label{os-page-', tex)
        self.assertLess(tex.index('\\label{os-page-'), tex.index('Text'))

    def test_required_missing_reference_fails(self):
        root = self.document('<tei:p><tei:ref type="page" target="urn:missing@he"/></tei:p>')
        with self.assertRaisesRegex(ValueError, 'destination absent'):
            resolve_page_references(root)

    def test_whole_missing_instruction_disappears(self):
        root = self.document('''<tei:note type="instruction"><tei:seg type="optional-page-reference">
            Absent, page <tei:ref type="page" target="urn:absent@he"/>.</tei:seg></tei:note>
            <tei:p>Prayer</tei:p>''')
        resolve_page_references(root)
        self.assertEqual(root.xpath('//*[local-name()="note"]'), [])

    def test_parallel_languages_have_distinct_labels(self):
        root = self.document('''<tei:p>Hebrew page <tei:ref type="page" target="urn:prayer@he"/>,
            English page <tei:ref type="page" target="urn:prayer@en"/>.</tei:p>
            <p:parallel><p:parallelItem role="primary" p:project="he" xml:lang="he">
            <tei:p><tei:milestone unit="prayer-part" corresp="urn:prayer"/>שלום</tei:p>
            </p:parallelItem><p:parallelItem role="parallel" p:project="en" xml:lang="en">
            <tei:p><tei:milestone unit="prayer-part" corresp="urn:prayer"/>Peace</tei:p>
            </p:parallelItem></p:parallel>''')
        resolve_page_references(root)
        targets = root.xpath('//*[local-name()="ref"]/@target')
        self.assertEqual(len(set(targets)), 2)
        for layout in ['pairs', 'pages']:
            tex = _transform(etree.tostring(root, encoding='unicode'), layout=layout)
            for target in targets:
                self.assertEqual(tex.count('\\label{' + target + '}'), 1)
                self.assertIn('\\pageref{' + target + '}', tex)
            self.assertLess(tex.index('\\label{' + targets[0]), tex.index('שלום'))
            self.assertLess(tex.index('\\label{' + targets[1]), tex.index('Peace'))

    def test_label_precedes_container_text(self):
        root = self.document('''<tei:note type="instruction">Page <tei:ref type="page" target="urn:target@he"/></tei:note>
            <tei:p corresp="urn:target">Target begins <tei:hi>here</tei:hi>.</tei:p>''')
        resolve_page_references(root)
        tex = _transform(etree.tostring(root, encoding='unicode'))
        self.assertLess(tex.index('\\label{os-page-'), tex.index('Target begins'))
        self.assertIn('Target begins ', tex)
