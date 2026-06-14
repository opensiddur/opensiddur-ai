"""Unit tests for j:conditional parsing and evaluation."""

import unittest
from unittest.mock import MagicMock

from lxml import etree

from opensiddur.exporter.condition_eval import (
    TriState,
    evaluate_condition,
    parse_condition_element,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.linear import NumericValue, Undefined

TEI = TEI_NS
J = JLPTEI_NAMESPACE


def _mock_processor(settings: dict[tuple[str, str], object]) -> MagicMock:
    proc = MagicMock()

    def get_active_setting(fs_type: str, feature_name: str):
        return settings.get((fs_type, feature_name))

    proc.get_active_setting.side_effect = get_active_setting
    return proc


def _conditional_xml(inner: str) -> etree._Element:
    xml = f'<j:conditional xmlns:tei="{TEI}" xmlns:j="{J}" xml:id="c">{inner}</j:conditional>'
    return etree.fromstring(xml.encode())


class TestLeafComparison(unittest.TestCase):
    def test_binary_match(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)

    def test_binary_no_match(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): False})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_unset_feature_is_undefined(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_condition_undefined(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:default/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_numeric_exact(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="n"><tei:numeric value="3"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "n"): 3})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "n"): 4})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_numeric_range(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="n"><tei:numeric value="1" max="5"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        for val in (1, 3, 5):
            proc = _mock_processor({("t:fs", "n"): val})
            self.assertEqual(evaluate_condition(node, proc), TriState.TRUE, val)
        proc = _mock_processor({("t:fs", "n"): 6})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_string_match(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="s"><tei:string>hello</tei:string></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "s"): "hello"})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)

    def test_vnot(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:binary value="true"/></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): False})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_valt(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vAlt><tei:numeric value="1"/><tei:numeric value="2"/></tei:vAlt></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): 2})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "x"): 3})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_implicit_all_multiple_fs(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="a"><tei:binary value="true"/></tei:f></tei:fs>'
            '<tei:fs type="t:fs"><tei:f name="b"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "a"): True, ("t:fs", "b"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "a"): True, ("t:fs", "b"): False})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)


class TestCombinators(unittest.TestCase):
    def _combinator(self, op: str, inner: str) -> etree._Element:
        tag = {"all": "all", "any": "any", "none": "none", "one": "one"}[op]
        return _conditional_xml(
            f'<j:{tag} xmlns:j="{J}">'
            f'<tei:fs type="t"><tei:f name="a"><tei:binary value="true"/></tei:f></tei:fs>'
            f'{inner}'
            f'</j:{tag}>'
        )

    def _leaf(self, name: str, value: str) -> str:
        return f'<tei:fs type="t"><tei:f name="{name}"><tei:binary value="{value}"/></tei:f></tei:fs>'

    def test_all_truth_table(self):
        cases = [
            (TriState.TRUE, TriState.TRUE, TriState.TRUE),
            (TriState.TRUE, TriState.FALSE, TriState.FALSE),
            (TriState.TRUE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.FALSE, TriState.FALSE, TriState.FALSE),
            (TriState.FALSE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.UNDEFINED, TriState.UNDEFINED, TriState.UNDEFINED),
        ]
        for left, right, expected in cases:
            settings = {}
            if left != TriState.UNDEFINED:
                settings[("t", "a")] = left == TriState.TRUE
            if right != TriState.UNDEFINED:
                settings[("t", "b")] = right == TriState.TRUE
            el = _conditional_xml(
                f'<j:all xmlns:j="{J}">{self._leaf("a", "true")}{self._leaf("b", "true")}</j:all>'
            )
            node = parse_condition_element(el)
            proc = _mock_processor(settings)
            self.assertEqual(evaluate_condition(node, proc), expected, (left, right))

    def test_any_truth_table(self):
        cases = [
            (TriState.TRUE, TriState.TRUE, TriState.TRUE),
            (TriState.TRUE, TriState.FALSE, TriState.TRUE),
            (TriState.TRUE, TriState.UNDEFINED, TriState.TRUE),
            (TriState.FALSE, TriState.FALSE, TriState.FALSE),
            (TriState.FALSE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.UNDEFINED, TriState.UNDEFINED, TriState.UNDEFINED),
        ]
        for left, right, expected in cases:
            settings = {}
            if left != TriState.UNDEFINED:
                settings[("t", "a")] = left == TriState.TRUE
            if right != TriState.UNDEFINED:
                settings[("t", "b")] = right == TriState.TRUE
            el = _conditional_xml(
                f'<j:any xmlns:j="{J}">{self._leaf("a", "true")}{self._leaf("b", "true")}</j:any>'
            )
            node = parse_condition_element(el)
            proc = _mock_processor(settings)
            self.assertEqual(evaluate_condition(node, proc), expected, (left, right))

    def test_one_truth_table(self):
        cases = [
            (TriState.TRUE, TriState.TRUE, TriState.FALSE),
            (TriState.TRUE, TriState.FALSE, TriState.TRUE),
            (TriState.TRUE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.FALSE, TriState.FALSE, TriState.FALSE),
            (TriState.FALSE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.UNDEFINED, TriState.UNDEFINED, TriState.UNDEFINED),
        ]
        for left, right, expected in cases:
            settings = {}
            if left != TriState.UNDEFINED:
                settings[("t", "a")] = left == TriState.TRUE
            if right != TriState.UNDEFINED:
                settings[("t", "b")] = right == TriState.TRUE
            el = _conditional_xml(
                f'<j:one xmlns:j="{J}">{self._leaf("a", "true")}{self._leaf("b", "true")}</j:one>'
            )
            node = parse_condition_element(el)
            proc = _mock_processor(settings)
            self.assertEqual(evaluate_condition(node, proc), expected, (left, right))

    def test_none_truth_table(self):
        cases = [
            (TriState.TRUE, TriState.TRUE, TriState.FALSE),
            (TriState.TRUE, TriState.FALSE, TriState.FALSE),
            (TriState.TRUE, TriState.UNDEFINED, TriState.FALSE),
            (TriState.FALSE, TriState.FALSE, TriState.TRUE),
            (TriState.FALSE, TriState.UNDEFINED, TriState.UNDEFINED),
            (TriState.UNDEFINED, TriState.UNDEFINED, TriState.UNDEFINED),
        ]
        for left, right, expected in cases:
            settings = {}
            if left != TriState.UNDEFINED:
                settings[("t", "a")] = left == TriState.TRUE
            if right != TriState.UNDEFINED:
                settings[("t", "b")] = right == TriState.TRUE
            el = _conditional_xml(
                f'<j:none xmlns:j="{J}">{self._leaf("a", "true")}{self._leaf("b", "true")}</j:none>'
            )
            node = parse_condition_element(el)
            proc = _mock_processor(settings)
            self.assertEqual(evaluate_condition(node, proc), expected, (left, right))


if __name__ == "__main__":
    unittest.main()
