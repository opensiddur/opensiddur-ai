"""Tests for the occasion conditions a running order gates its sections on."""

import unittest

from lxml import etree

from opensiddur.importer.util.occasion import (
    AGGREGATE,
    HEBREW_DATE,
    HOLIDAY,
    SERVICE_TIME,
    Feature,
    aggregate,
    all_of,
    any_of,
    fixed,
    gate,
    gated,
    holiday,
    none_of,
    service,
)

J = "http://jewishliturgy.org/ns/jlptei/2"
TEI = "http://www.tei-c.org/ns/1.0"
NS = {"j": J, "tei": TEI}


def _parse(markup: str) -> etree.ElementBase:
    return etree.fromstring(f'<root xmlns:j="{J}" xmlns:tei="{TEI}">{markup}</root>')


class TestFixed(unittest.TestCase):
    """What a condition fixes to one value wherever it holds."""

    def test_a_binary_is_fixed(self):
        self.assertEqual(fixed(aggregate("shabbat")), [Feature(AGGREGATE, "shabbat", True)])

    def test_a_single_number_is_fixed(self):
        self.assertEqual(fixed(holiday("shavuot", 1)), [Feature(HOLIDAY, "shavuot", 1)])

    def test_a_range_is_not(self):
        self.assertEqual(fixed(holiday("hanukkah", 1, 8)), [])

    def test_all_fixes_what_each_part_fixes(self):
        self.assertEqual(
            fixed(all_of(none_of(aggregate("shabbat"), aggregate("yom-tov")), service("maariv"))),
            [Feature(AGGREGATE, "shabbat", False), Feature(AGGREGATE, "yom-tov", False),
             Feature(SERVICE_TIME, "maariv", True)])

    def test_any_of_several_fixes_nothing(self):
        self.assertEqual(fixed(any_of(aggregate("shabbat"), aggregate("yom-tov"))), [])

    def test_any_of_one_is_that_one(self):
        self.assertEqual(fixed(any_of(aggregate("shabbat"))), [Feature(AGGREGATE, "shabbat", True)])

    def test_inputs_to_the_calendar_are_never_declared(self):
        """Declaring part of a date would recompute everything from a date with a piece
        missing."""
        self.assertEqual(fixed(Feature(HEBREW_DATE, "month", 1)), [])


class TestGate(unittest.TestCase):

    def test_a_gate_has_no_instruction_and_is_not_marked(self):
        opening, closing = gate("g", aggregate("shabbat"))
        conditional = _parse(opening + closing).find("j:conditional", NS)
        self.assertIsNone(conditional.find("tei:note", NS))
        self.assertIsNone(conditional.get("type"))

    def test_a_gate_declares_what_it_fixes_inside_the_conditional(self):
        root = _parse(gated("g", holiday("shavuot", 1), "<j:transclude target='x'/>"))
        self.assertEqual([etree.QName(child).localname for child in root],
                         ["conditional", "declare", "transclude", "endDeclare", "endConditional"])
        declared = root.find("j:declare/tei:fs", NS)
        self.assertEqual(declared.get("type"), HOLIDAY)
        self.assertEqual(declared.find("tei:f", NS).get("name"), "shavuot")
        self.assertEqual(declared.find("tei:f/tei:numeric", NS).get("value"), "1")
        self.assertEqual(root.find("j:endDeclare", NS).get("target"),
                         "#" + root.find("j:declare", NS).get("{http://www.w3.org/XML/1998/namespace}id"))

    def test_a_gate_that_fixes_nothing_declares_nothing(self):
        root = _parse(gated("g", holiday("hanukkah", 1, 8), "<j:transclude target='x'/>"))
        self.assertEqual([etree.QName(child).localname for child in root],
                         ["conditional", "transclude", "endConditional"])

    def test_no_condition_is_no_gate(self):
        self.assertEqual(gated("g", None, "<x/>"), "<x/>")

    def test_a_range_is_written_as_one(self):
        root = _parse(gate("g", holiday("hanukkah", 1, 8))[0])
        numeric = root.find(".//tei:numeric", NS)
        self.assertEqual((numeric.get("value"), numeric.get("max")), ("1", "8"))


if __name__ == "__main__":
    unittest.main()
