"""Prepare a compiled document's undecided conditions for an electronic book.

A scope the compiler could not decide reaches the compiled document as a pair of sibling
markers, `j:conditional` ... `j:endConditional`, around whatever it governs -- a phrase, a
paragraph, a run of sections. On the page the reader's device shows or hides what a scope
governs, which the HTML can only do element by element. Scopes may also cross, so they cannot
simply become wrapping elements.

So instead, every element and every run of text is labelled with each scope that governs all
of it, and the device hides whatever carries the label of a scope that does not hold. This
pass computes the labels on the compiled tree, as `p:scopes` attributes and `p:span` wrappers
around text, for html.xslt to turn into classes:

- an element is governed by a scope that is open at its start and still open at its end;
- a run of text, by every scope open where it stands;
- each is labelled only with the scopes its parent is not already labelled with.

A parallel column is a stream of its own. A scope opened in the primary column governs that
column through the rows that follow, and not the column beside it; a scope opened outside the
columns governs both.

The pass also numbers the scopes (`p:cid`, on both markers) and collects their conditions, for
the book's JSON.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from opensiddur.exporter.client_settings import is_reader_supplied
from opensiddur.exporter.condition_eval import (
    condition_features,
    condition_to_json,
    parse_condition_element,
)
from opensiddur.exporter.conditional_markers import check_pairing
from opensiddur.exporter.conditional_settings import J_CONDITIONAL, J_END_CONDITIONAL, XML_ID
from opensiddur.exporter.constants import PROCESSING_NAMESPACE, TEI_NS, is_element_node

logger = logging.getLogger(__name__)

P_CID = f"{{{PROCESSING_NAMESPACE}}}cid"
P_SCOPES = f"{{{PROCESSING_NAMESPACE}}}scopes"
P_SPAN = f"{{{PROCESSING_NAMESPACE}}}span"
P_PINNED = f"{{{PROCESSING_NAMESPACE}}}pinned"
P_PARALLEL_ITEM = f"{{{PROCESSING_NAMESPACE}}}parallelItem"
P_SILENT = f"{{{PROCESSING_NAMESPACE}}}silent"
TEI_MILESTONE = f"{{{TEI_NS}}}milestone"
TEI_NOTE = f"{{{TEI_NS}}}note"


@dataclass
class Feature:
    """A reader-supplied feature the book's conditions ask about, for the settings panel."""

    fs: str
    name: str
    #: The values conditions compare it with, in the order first met.
    values: list[Any] = field(default_factory=list)
    #: How many scopes turn on it.
    scopes: int = 0


@dataclass
class BookConditions:
    #: Distinct (condition, pinned values) pairs, as JSON.
    expressions: list[dict[str, Any]] = field(default_factory=list)
    #: For each scope, by its number, the index of its expression.
    scopes: list[int] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)


def _leaf_values(condition: dict[str, Any]):
    """(fs, feature, value) for every value a JSON condition compares with."""
    if "fs" in condition:
        for f in condition["f"]:
            yield from _values_of(condition["fs"], f["name"], f["v"])
        return
    for child in condition["args"]:
        yield from _leaf_values(child)


def _values_of(fs, name, value):
    if isinstance(value, dict) and "alt" in value:
        for alt in value["alt"]:
            yield from _values_of(fs, name, alt)
    elif isinstance(value, dict) and "not" in value:
        yield from _values_of(fs, name, value["not"])
    elif not (isinstance(value, dict) and value.get("undefined")):
        yield fs, name, value


def _number_scopes(root: etree.ElementBase) -> tuple[dict[str, etree.ElementBase], BookConditions]:
    """Number each paired scope in document order, and collect its condition.

    Returns the openers by their xml:id, and the book's conditions.
    """
    problems = check_pairing(root)
    unpaired = {problem.xml_id for problem in problems}
    for problem in problems:
        logger.warning("conditional markers do not pair, left undecided: %s", problem)

    book = BookConditions()
    expression_index: dict[str, int] = {}
    features: dict[tuple[str, str], Feature] = {}
    openers: dict[str, etree.ElementBase] = {}

    for opener in root.iter(J_CONDITIONAL):
        xml_id = opener.get(XML_ID)
        pinned_element = opener.find(P_PINNED)
        pinned = json.loads(pinned_element.text) if pinned_element is not None else {}
        if pinned_element is not None:
            opener.remove(pinned_element)
        if xml_id is None or xml_id in unpaired:
            continue

        node = parse_condition_element(opener)
        expression = {"cond": condition_to_json(node), "pinned": pinned}
        key = json.dumps(expression, sort_keys=True, ensure_ascii=False)
        if key not in expression_index:
            expression_index[key] = len(book.expressions)
            book.expressions.append(expression)

        cid = len(book.scopes)
        book.scopes.append(expression_index[key])
        opener.set(P_CID, str(cid))
        openers[xml_id] = opener

        for fs, name in sorted(condition_features(node)):
            if is_reader_supplied(fs) and name not in pinned.get(fs, {}):
                features.setdefault((fs, name), Feature(fs, name)).scopes += 1
        for fs, name, value in _leaf_values(expression["cond"]):
            feature = features.get((fs, name))
            if feature is not None and value not in feature.values:
                feature.values.append(value)

    for closer in root.iter(J_END_CONDITIONAL):
        opener = openers.get((closer.get("target") or "").removeprefix("#"))
        if opener is not None:
            closer.set(P_CID, opener.get(P_CID))

    # A feature conditions compare only with "undefined" has nothing a reader could choose.
    book.features = sorted((f for f in features.values() if f.values), key=lambda f: (f.fs, f.name))
    return openers, book


class _Spans:
    """The open scopes, per stream, as the walk goes through the document."""

    def __init__(self):
        self.open: dict[str | None, list[int]] = {}

    def active(self, stream: str | None) -> frozenset[int]:
        found = set(self.open.get(None, ()))
        if stream is not None:
            found.update(self.open.get(stream, ()))
        return frozenset(found)

    def toggle(self, marker: etree.ElementBase, stream: str | None) -> None:
        cid = int(marker.get(P_CID))
        scopes = self.open.setdefault(stream, [])
        if marker.tag == J_CONDITIONAL:
            scopes.append(cid)
        elif cid in scopes:
            scopes.remove(cid)


def _is_marker(element: etree.ElementBase) -> bool:
    return element.tag in (J_CONDITIONAL, J_END_CONDITIONAL) and element.get(P_CID) is not None


def _measure(root: etree.ElementBase) -> dict[etree.ElementBase, tuple[frozenset, frozenset]]:
    """The scopes active at the start and at the end of every element."""
    spans = _Spans()
    measured: dict[etree.ElementBase, tuple[frozenset, frozenset]] = {}

    def walk(element, stream):
        if element.tag == P_PARALLEL_ITEM:
            stream = element.get("role")
        before = spans.active(stream)
        if _is_marker(element):
            spans.toggle(element, stream)
        else:
            for child in element:
                if is_element_node(child):
                    walk(child, stream)
        measured[element] = (before, spans.active(stream))

    walk(root, None)
    return measured


def _label(element: etree.ElementBase, scopes: frozenset[int]) -> None:
    if scopes:
        element.set(P_SCOPES, " ".join(str(cid) for cid in sorted(scopes)))


def _span(text: str, scopes: frozenset[int]) -> etree.ElementBase:
    span = etree.Element(P_SPAN)
    span.text = text
    _label(span, scopes)
    return span


def _assign(root: etree.ElementBase, measured) -> None:
    """Label each element and run of text with the scopes that govern it and not its parent."""

    def walk(element, inherited):
        before, after = measured[element]
        governed = before & after
        _label(element, governed - inherited)
        if _is_marker(element):
            return
        covered = inherited | governed
        children = list(element)
        if element.text and element.text.strip() and before - covered:
            element.insert(0, _span(element.text, before - covered))
            element.text = None
        for child in children:
            if not is_element_node(child):
                continue
            walk(child, covered)
            tail_scopes = measured[child][1] - covered
            if child.tail and child.tail.strip() and tail_scopes:
                span = _span(child.tail, tail_scopes)
                child.tail = None
                child.addnext(span)

    walk(root, frozenset())


def _is_reading_division(element: etree.ElementBase) -> bool:
    unit = element.get("unit") or ""
    return element.tag == TEI_MILESTONE and unit.startswith(("aliyah", "maftir"))


def _silence(openers: dict[str, etree.ElementBase]) -> None:
    """Mark the scopes that only say which reading division begins here (p:silent).

    A humash marks where each aliyah begins, in every cycle it follows, and which apply
    depends on the year's reading pattern. The label is the whole of what such a scope
    governs, and showing it or not says all there is to say: a rule or a bracket around it
    would only crowd the page. The PDF stage silences the same scopes (reledmac.xslt,
    f:governs-markers-only).
    """
    for opener in openers.values():
        if opener.find(TEI_NOTE) is not None:
            continue
        between = []
        sibling = opener.getnext()
        while sibling is not None and sibling.tag != J_END_CONDITIONAL:
            between.append(sibling)
            sibling = sibling.getnext()
        if (sibling is None or sibling.get(P_CID) != opener.get(P_CID) or not between
                or not all(_is_reading_division(node) for node in between)
                or any((node.tail or "").strip() for node in [opener, *between])):
            continue
        opener.set(P_SILENT, "true")
        sibling.set(P_SILENT, "true")


def prepare(root: etree.ElementBase) -> BookConditions:
    """Number, collect and label the undecided scopes in a compiled document, in place."""
    openers, book = _number_scopes(root)
    if book.scopes:
        _silence(openers)
        _assign(root, _measure(root))
    return book
