import unittest
from pathlib import Path

from lxml import etree


ODD_PATH = Path(__file__).resolve().parents[3] / "schema" / "jlptei.odd.xml"


class TestJlpteiOddConstraints(unittest.TestCase):
    def setUp(self):
        self.tree = etree.parse(str(ODD_PATH))
        self.ns = {
            "tei": "http://www.tei-c.org/ns/1.0",
            "sch": "http://purl.oclc.org/dsdl/schematron",
        }

    def test_requires_xml_lang_on_tei_root(self):
        asserts = self.tree.xpath(
            "//tei:elementSpec[@ident='TEI']//sch:assert[@test='@xml:lang']",
            namespaces=self.ns,
        )
        self.assertTrue(asserts, "Expected schematron assert requiring tei:TEI/@xml:lang")

    def test_standoff_type_is_closed_list(self):
        vals = self.tree.xpath(
            "//tei:elementSpec[@ident='standOff']//tei:attDef[@ident='type']//tei:valItem/@ident",
            namespaces=self.ns,
        )
        self.assertEqual(set(vals), {"notes", "settings", "conditions"})

    def test_transclude_type_is_closed_list(self):
        vals = self.tree.xpath(
            "//tei:elementSpec[@ident='transclude']//tei:attDef[@ident='type']//tei:valItem/@ident",
            namespaces=self.ns,
        )
        self.assertEqual(set(vals), {"external", "inline"})

    def test_paragraph_type_is_closed_list(self):
        vals = self.tree.xpath(
            "//tei:elementSpec[@ident='p']//tei:attDef[@ident='type']//tei:valItem/@ident",
            namespaces=self.ns,
        )
        self.assertEqual(
            set(vals),
            {"open-1", "open-2", "open-3", "closed-1", "closed-2", "closed-3"},
        )

    def test_divine_name_exists_and_is_agent_like(self):
        divine = self.tree.xpath(
            "//tei:elementSpec[@ident='divineName']",
            namespaces=self.ns,
        )
        self.assertTrue(divine, "Expected j:divineName elementSpec to exist in ODD")

        member = self.tree.xpath(
            "//tei:elementSpec[@ident='divineName']//tei:memberOf[@key='model.nameLike.agent']",
            namespaces=self.ns,
        )
        self.assertTrue(member, "Expected j:divineName to be member of model.nameLike.agent")

    def test_corresp_is_unique_within_a_document(self):
        """A repeated URN breaks alignment and resolution silently, so the schema rejects it."""
        reports = self.tree.xpath(
            "//tei:constraintSpec[@ident='corresp-uniqueness']//sch:report",
            namespaces=self.ns,
        )
        self.assertTrue(reports, "Expected a schematron report for duplicate @corresp")

    def test_edition_verse_milestone_must_not_carry_a_urn(self):
        """unit='edition-verse' records an edition's own numbering, never an identity."""
        asserts = self.tree.xpath(
            "//tei:constraintSpec[@ident='edition-verse-constraints']//sch:assert/@test",
            namespaces=self.ns,
        )
        self.assertIn("not(@corresp)", asserts)
        self.assertIn("@n", asserts)

