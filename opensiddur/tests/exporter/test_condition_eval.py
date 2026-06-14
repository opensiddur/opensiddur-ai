"""Unit tests for j:conditional parsing and evaluation."""

import unittest
from unittest.mock import MagicMock

from lxml import etree

from opensiddur.exporter.condition_eval import (
    CombinatorCondition,
    TriState,
    evaluate_condition,
    parse_condition_element,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.linear import Undefined

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
        parsed = node.features[0].value
        self.assertEqual(parsed.value, 1)
        self.assertEqual(parsed.max_value, 5)
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

    def test_multiple_features_in_one_fs_implicit_all(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs">'
            '<tei:f name="a"><tei:binary value="true"/></tei:f>'
            '<tei:f name="b"><tei:binary value="true"/></tei:f>'
            '</tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "a"): True, ("t:fs", "b"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "a"): True, ("t:fs", "b"): False})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_string_no_match(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="s"><tei:string>hello</tei:string></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "s"): "world"})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_symbol_undefined_in_condition(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:symbol value="undefined"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_symbol_non_undefined_in_condition(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="s"><tei:symbol value="foo"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "s"): "foo"})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "s"): "bar"})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_numeric_active_not_numeric_returns_false(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="n"><tei:numeric value="3"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "n"): "3"})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_vnot_with_undefined_inner(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:default/></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_valt_with_undefined_alternative(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vAlt><tei:default/><tei:numeric value="2"/></tei:vAlt></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): 9})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_active_undefined_with_concrete_condition(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): Undefined})
        self.assertEqual(evaluate_condition(node, proc), TriState.UNDEFINED)

    def test_parse_skips_instruction_note_sibling(self):
        el = _conditional_xml(
            '<tei:note type="instruction">On Shabbat</tei:note>'
            '<tei:fs type="t:fs"><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)


class TestParseErrors(unittest.TestCase):
    def test_conditional_without_condition_child(self):
        el = _conditional_xml('<tei:note type="instruction">only note</tei:note>')
        with self.assertRaisesRegex(ValueError, "at least one condition child"):
            parse_condition_element(el)

    def test_fs_missing_type(self):
        el = _conditional_xml('<tei:fs><tei:f name="x"><tei:binary value="true"/></tei:f></tei:fs>')
        with self.assertRaisesRegex(ValueError, "missing required @type"):
            parse_condition_element(el)

    def test_f_missing_name(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f><tei:binary value="true"/></tei:f></tei:fs>'
        )
        with self.assertRaisesRegex(ValueError, "missing required @name"):
            parse_condition_element(el)

    def test_fs_without_f_children(self):
        el = _conditional_xml('<tei:fs type="t:fs"/>')
        with self.assertRaisesRegex(ValueError, "has no tei:f children"):
            parse_condition_element(el)

    def test_numeric_missing_value_on_f(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="n"><tei:numeric/></tei:f></tei:fs>'
        )
        with self.assertRaisesRegex(ValueError, "tei:numeric missing @value"):
            parse_condition_element(el)

    def test_f_without_value_element(self):
        el = _conditional_xml('<tei:fs type="t:fs"><tei:f name="x"/></tei:fs>')
        with self.assertRaisesRegex(ValueError, "No value element found"):
            parse_condition_element(el)

    def test_vnot_requires_single_child(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:binary value="true"/><tei:binary value="false"/></tei:vNot>'
            '</tei:f></tei:fs>'
        )
        with self.assertRaisesRegex(ValueError, "exactly one value element"):
            parse_condition_element(el)

    def test_unexpected_condition_element(self):
        el = _conditional_xml('<tei:p>not a condition</tei:p>')
        with self.assertRaisesRegex(ValueError, "Unexpected condition element"):
            parse_condition_element(el)

    def test_empty_combinator_raises(self):
        el = _conditional_xml('<j:all xmlns:j="{J}"/>'.replace("{J}", J))
        with self.assertRaisesRegex(ValueError, "at least one child condition"):
            parse_condition_element(el)

    def test_vnot_numeric_missing_value(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:numeric/></tei:vNot></tei:f></tei:fs>'
        )
        with self.assertRaisesRegex(ValueError, "tei:numeric missing @value"):
            parse_condition_element(el)

    def test_unsupported_value_element_in_vnot(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:p>bad</tei:p></tei:vNot></tei:f></tei:fs>'
        )
        with self.assertRaisesRegex(ValueError, "Unsupported value element"):
            parse_condition_element(el)

    def test_vnot_with_string_value(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:string>yes</tei:string></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): "no"})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)

    def test_vnot_with_symbol_and_default_value_elements(self):
        for inner, active, expected in (
            ('<tei:symbol value="undefined"/>', True, TriState.UNDEFINED),
            ('<tei:default/>', False, TriState.UNDEFINED),
        ):
            el = _conditional_xml(
                f'<tei:fs type="t:fs"><tei:f name="x">'
                f'<tei:vNot>{inner}</tei:vNot></tei:f></tei:fs>'
            )
            node = parse_condition_element(el)
            proc = _mock_processor({("t:fs", "x"): active})
            self.assertEqual(evaluate_condition(node, proc), expected, inner)

    def test_vnot_with_numeric_range_value_element(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="n">'
            '<tei:vNot><tei:numeric value="1" max="3"/></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "n"): 2})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)
        proc = _mock_processor({("t:fs", "n"): 5})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)

    def test_vnot_with_valt_value_element(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="x">'
            '<tei:vNot><tei:vAlt><tei:numeric value="1"/><tei:numeric value="2"/>'
            '</tei:vAlt></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): 3})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)

    def test_vnot_with_symbol_value(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs"><tei:f name="s">'
            '<tei:vNot><tei:symbol value="foo"/></tei:vNot></tei:f></tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "s"): "bar"})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)
        proc = _mock_processor({("t:fs", "s"): "foo"})
        self.assertEqual(evaluate_condition(node, proc), TriState.FALSE)

    def test_fs_ignores_non_f_children(self):
        el = _conditional_xml(
            '<tei:fs type="t:fs">'
            '<tei:note type="instruction">ignored</tei:note>'
            '<tei:f name="x"><tei:binary value="true"/></tei:f>'
            '</tei:fs>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t:fs", "x"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)


class TestCombinators(unittest.TestCase):
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


class TestCombinatorEdgeCases(unittest.TestCase):
    def test_unknown_combinator_op_raises(self):
        node = CombinatorCondition(op="MAYBE", children=())
        with self.assertRaisesRegex(ValueError, "Unknown combinator"):
            evaluate_condition(node, _mock_processor({}))

    def test_empty_all_evaluates_true(self):
        node = CombinatorCondition(op="ALL", children=())
        self.assertEqual(evaluate_condition(node, _mock_processor({})), TriState.TRUE)

    def test_empty_any_evaluates_false(self):
        node = CombinatorCondition(op="ANY", children=())
        self.assertEqual(evaluate_condition(node, _mock_processor({})), TriState.FALSE)

    def test_empty_one_evaluates_false(self):
        node = CombinatorCondition(op="ONE", children=())
        self.assertEqual(evaluate_condition(node, _mock_processor({})), TriState.FALSE)

    def test_empty_none_evaluates_true(self):
        node = CombinatorCondition(op="NONE", children=())
        self.assertEqual(evaluate_condition(node, _mock_processor({})), TriState.TRUE)

    def test_nested_combinator(self):
        el = _conditional_xml(
            f'<j:all xmlns:j="{J}">'
            f'<j:any xmlns:j="{J}">'
            f'<tei:fs type="t"><tei:f name="a"><tei:binary value="true"/></tei:f></tei:fs>'
            f'<tei:fs type="t"><tei:f name="b"><tei:binary value="true"/></tei:f></tei:fs>'
            f'</j:any>'
            f'<tei:fs type="t"><tei:f name="c"><tei:binary value="true"/></tei:f></tei:fs>'
            f'</j:all>'
        )
        node = parse_condition_element(el)
        proc = _mock_processor({("t", "a"): False, ("t", "b"): True, ("t", "c"): True})
        self.assertEqual(evaluate_condition(node, proc), TriState.TRUE)


if __name__ == "__main__":
    unittest.main()
