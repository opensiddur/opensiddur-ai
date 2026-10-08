"""The compiler's evaluator and the electronic book's agree.

An electronic book resolves its undecided conditions on the reader's device, in JavaScript
(html/assets/condition.js), against the reader's settings (client_settings). The cases in
fixtures/condition_agreement are resolved three ways -- by the Python reference, by the Python
reference after a round trip through the JSON the book carries, and by the JavaScript -- and
all three must give the expected result.
"""

import json
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.exporter.calendar.compute import ALWAYS_YOM_TOV, SettingSnapshot
from opensiddur.exporter.client_settings import CLIENT_DERIVATIONS, resolve
from opensiddur.exporter.condition_eval import (
    TriState,
    _combine,
    condition_from_json,
    condition_to_json,
    parse_condition_element,
    value_from_json,
)
from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS
from opensiddur.exporter.linear import Undefined
from opensiddur.tests.exporter.js_engine import require_node, run_js
from opensiddur.tests.exporter.spec_tables import truth_tables

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "condition_agreement"


def _cases():
    for path in sorted(CORPUS.glob("*.json")):
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            yield path.stem, case


def _condition(case) -> dict:
    element = etree.fromstring(
        f'<j:conditional xmlns:j="{JLPTEI_NAMESPACE}" xmlns:tei="{TEI_NS}" '
        f'xml:id="c">{case["condition"]}</j:conditional>')
    return condition_to_json(parse_condition_element(element))


def _layers(case) -> dict:
    return {key: case.get(key, {}) for key in ("pinned", "reader", "defaults")}


class TestPythonReference(unittest.TestCase):

    def test_corpus(self):
        for corpus, case in _cases():
            with self.subTest(corpus=corpus, case=case["name"]):
                element = etree.fromstring(
                    f'<j:conditional xmlns:j="{JLPTEI_NAMESPACE}" xmlns:tei="{TEI_NS}" '
                    f'xml:id="c">{case["condition"]}</j:conditional>')
                self.assertEqual(
                    resolve(parse_condition_element(element), **_layers(case)),
                    case["expected"])

    def test_corpus_after_json_round_trip(self):
        for corpus, case in _cases():
            with self.subTest(corpus=corpus, case=case["name"]):
                encoded = json.loads(json.dumps(_condition(case)))
                self.assertEqual(condition_to_json(condition_from_json(encoded)), encoded)
                self.assertEqual(resolve(encoded, **_layers(case)), case["expected"])


class TestJavaScript(unittest.TestCase):

    def setUp(self):
        self.node = require_node(self)

    def test_corpus(self):
        cases = list(_cases())
        results = run_js(
            self.node,
            "return args.map(c => OSCond.resolve(c.condition, c.pinned, c.reader, c.defaults));",
            [{"condition": _condition(case), **_layers(case)} for _, case in cases])
        for (corpus, case), result in zip(cases, results, strict=True):
            with self.subTest(corpus=corpus, case=case["name"]):
                self.assertEqual(result, case["expected"])

    def test_truth_tables(self):
        cells = [(op, row.value, column.value, expected.value)
                 for op, table in truth_tables().items()
                 for (row, column), expected in table.items()]
        results = run_js(
            self.node,
            "return args.map(c => OSCond.combine(c[0], [c[1], c[2]]));",
            cells)
        for (op, row, column, expected), result in zip(cells, results, strict=True):
            with self.subTest(op=op, row=row, column=column):
                self.assertEqual(result, expected)

    def test_n_ary_and_empty_operands(self):
        """Beyond the two-operand tables: the rules for any number of operands."""
        values = [TriState.TRUE, TriState.FALSE, TriState.UNDEFINED]
        operands = [[]] + [[v] for v in values] + [
            [a, b, c] for a in values for b in values for c in values]
        cases = [(op, [v.value for v in ops]) for op in ("all", "any", "one", "none")
                 for ops in operands]
        results = run_js(self.node, "return args.map(c => OSCond.combine(c[0], c[1]));", cases)
        for (op, ops), result in zip(cases, results, strict=True):
            with self.subTest(op=op, operands=ops):
                self.assertEqual(result, _combine(op.upper(), [TriState(v) for v in ops]).value)

    #: The one input each device derivation reads.
    DERIVATION_INPUTS = {
        "opensiddur:quorum": ("opensiddur:quorum", "minyan"),
        "opensiddur:recitation": ("opensiddur:service-time", "maariv"),
        "opensiddur:holiday": ("opensiddur:holiday-aggregate", "yom-tov"),
    }

    def test_derivations_are_the_clients(self):
        """The device runs the derivations client_settings says it does, and gives the same
        results for every value their input can be set to."""
        self.assertEqual(
            run_js(self.node, "return Object.keys(OSCond.DERIVATIONS).sort();"),
            sorted(CLIENT_DERIVATIONS))
        self.assertEqual(sorted(self.DERIVATION_INPUTS), sorted(CLIENT_DERIVATIONS))
        values = [None, True, False, 0, 1, "", "yes", {"num": 10}, {"num": 0}]
        cases = [(fs, value) for fs in sorted(CLIENT_DERIVATIONS) for value in values]
        results = run_js(
            self.node,
            "return args.cases.map(([fs, v]) => OSCond.DERIVATIONS[fs]("
            "(f, n) => (f === args.inputs[fs][0] && n === args.inputs[fs][1]) ? v : null));",
            {"cases": cases, "inputs": self.DERIVATION_INPUTS})
        for (fs, value), result in zip(cases, results, strict=True):
            with self.subTest(derivation=fs, input=value):
                def get(f, n, fs=fs, value=value):
                    decoded = value_from_json(value)
                    if (f, n) != self.DERIVATION_INPUTS[fs] or decoded is Undefined:
                        return None
                    return decoded

                # Python says "nothing" with None or {}; the device with null.
                expected = CLIENT_DERIVATIONS[fs](SettingSnapshot(get)) or None
                self.assertEqual(result, expected)

    def test_festivals_always_yom_tov_are_the_compilers(self):
        self.assertEqual(run_js(self.node, "return OSCond.ALWAYS_YOM_TOV;"), list(ALWAYS_YOM_TOV))


if __name__ == "__main__":
    unittest.main()
