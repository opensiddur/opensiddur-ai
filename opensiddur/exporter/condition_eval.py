"""Parse and evaluate j:conditional feature structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from lxml.etree import ElementBase

from opensiddur.exporter.conditional_settings import (
    J_ALL,
    J_ANY,
    J_NONE,
    J_ONE,
    TEI_BINARY,
    TEI_DEFAULT,
    TEI_F,
    TEI_FS,
    TEI_NOTE,
    TEI_NUMERIC,
    TEI_STRING,
    TEI_SYMBOL,
    TEI_VALT,
    TEI_VNOT,
)
from opensiddur.exporter.linear import NumericValue, Undefined


class TriState(StrEnum):
    TRUE = "true"
    FALSE = "false"
    UNDEFINED = "undefined"


class _SettingLookup(Protocol):
    def get_active_setting(self, fs_type: str, feature_name: str) -> Any | None: ...


@dataclass(frozen=True)
class FeatureCondition:
    fs_type: str
    feature_name: str
    value: Any


@dataclass(frozen=True)
class FsCondition:
    fs_type: str
    features: tuple[FeatureCondition, ...]


@dataclass(frozen=True)
class CombinatorCondition:
    op: str  # ALL, ANY, NONE, ONE
    children: tuple[ConditionNode, ...]


ConditionNode = FsCondition | CombinatorCondition


_COMBINATOR_TAGS = {
    J_ALL: "ALL",
    J_ANY: "ANY",
    J_NONE: "NONE",
    J_ONE: "ONE",
}


def _parse_condition_f_value(f_element: ElementBase) -> Any:
    """Parse tei:f value for conditions (supports vAlt / vNot)."""
    for child in f_element:
        if child.tag == TEI_NUMERIC:
            raw = child.get("value")
            if raw is None:
                raise ValueError(f"tei:numeric missing @value in {f_element.get('name')!r}")
            numeric = NumericValue(value=int(raw))
            if child.get("max") is not None:
                numeric = NumericValue(value=int(raw), max_value=int(child.get("max")))
            return numeric
        if child.tag == TEI_BINARY:
            raw = child.get("value", "")
            return raw == "true"
        if child.tag == TEI_STRING:
            return child.text or ""
        if child.tag == TEI_SYMBOL:
            sym = child.get("value", "")
            if sym == "undefined":
                return Undefined
            return sym
        if child.tag == TEI_DEFAULT:
            return Undefined
        if child.tag == TEI_VALT:
            return tuple(_parse_condition_value_element(alt) for alt in child)
        if child.tag == TEI_VNOT:
            inner_children = list(child)
            if len(inner_children) != 1:
                raise ValueError("tei:vNot must contain exactly one value element")
            return ("vNot", _parse_condition_value_element(inner_children[0]))
    raise ValueError(f"No value element found in tei:f[@name={f_element.get('name')!r}]")


def _parse_condition_value_element(el: ElementBase) -> Any:
    """Parse a standalone value element (used inside tei:vNot)."""
    if el.tag == TEI_NUMERIC:
        raw = el.get("value")
        if raw is None:
            raise ValueError("tei:numeric missing @value")
        numeric = NumericValue(value=int(raw))
        if el.get("max") is not None:
            numeric = NumericValue(value=int(raw), max_value=int(el.get("max")))
        return numeric
    if el.tag == TEI_BINARY:
        return el.get("value", "") == "true"
    if el.tag == TEI_STRING:
        return el.text or ""
    if el.tag == TEI_SYMBOL:
        sym = el.get("value", "")
        if sym == "undefined":
            return Undefined
        return sym
    if el.tag == TEI_DEFAULT:
        return Undefined
    if el.tag == TEI_VALT:
        return tuple(_parse_condition_value_element(alt) for alt in el)
    raise ValueError(f"Unsupported value element {el.tag!r}")


def _parse_fs_condition(fs_element: ElementBase) -> FsCondition:
    fs_type = fs_element.get("type")
    if not fs_type:
        raise ValueError("tei:fs missing required @type attribute")
    features: list[FeatureCondition] = []
    for f_el in fs_element:
        if f_el.tag != TEI_F:
            continue
        feature_name = f_el.get("name")
        if not feature_name:
            raise ValueError("tei:f missing required @name attribute")
        features.append(
            FeatureCondition(
                fs_type=fs_type,
                feature_name=feature_name,
                value=_parse_condition_f_value(f_el),
            )
        )
    if not features:
        raise ValueError(f"tei:fs[@type={fs_type!r}] has no tei:f children")
    return FsCondition(fs_type=fs_type, features=tuple(features))


def _parse_condition_node(element: ElementBase) -> ConditionNode:
    if element.tag == TEI_FS:
        return _parse_fs_condition(element)
    if element.tag in _COMBINATOR_TAGS:
        children = tuple(_parse_condition_node(child) for child in element)
        if not children:
            raise ValueError(f"{element.tag} requires at least one child condition")
        return CombinatorCondition(op=_COMBINATOR_TAGS[element.tag], children=children)
    raise ValueError(f"Unexpected condition element {element.tag!r}")


def _condition_children(conditional_el: ElementBase) -> list[ElementBase]:
    """Return condition AST source children (exclude tei:note)."""
    return [child for child in conditional_el if child.tag != TEI_NOTE]


def parse_condition_element(conditional_el: ElementBase) -> ConditionNode:
    """Parse condition specification from a j:conditional element."""
    children = _condition_children(conditional_el)
    if not children:
        raise ValueError("j:conditional requires at least one condition child")
    if len(children) == 1:
        return _parse_condition_node(children[0])
    return CombinatorCondition(
        op="ALL",
        children=tuple(_parse_condition_node(child) for child in children),
    )


def _is_undefined(value: Any) -> bool:
    return value is Undefined


def _single_value_match(active: Any, condition: Any) -> TriState:
    if _is_undefined(active) or _is_undefined(condition):
        return TriState.UNDEFINED
    if isinstance(condition, tuple) and condition and condition[0] == "vNot":
        inner = _single_value_match(active, condition[1])
        if inner == TriState.UNDEFINED:
            return TriState.UNDEFINED
        if inner == TriState.TRUE:
            return TriState.FALSE
        return TriState.TRUE
    if isinstance(condition, tuple) and not (condition and condition[0] == "vNot"):
        # tei:vAlt
        results = [_single_value_match(active, alt) for alt in condition]
        return _combine_any(results)
    if isinstance(condition, NumericValue):
        if not isinstance(active, (int, float)):
            return TriState.FALSE
        active_int = int(active)
        if condition.max_value is not None:
            if condition.value <= active_int <= condition.max_value:
                return TriState.TRUE
            return TriState.FALSE
        return TriState.TRUE if active_int == condition.value else TriState.FALSE
    return TriState.TRUE if active == condition else TriState.FALSE


def _combine_all(results: list[TriState]) -> TriState:
    if not results:
        return TriState.TRUE
    if all(r == TriState.TRUE for r in results):
        return TriState.TRUE
    if any(r == TriState.UNDEFINED for r in results):
        return TriState.UNDEFINED
    return TriState.FALSE


def _combine_any(results: list[TriState]) -> TriState:
    if not results:
        return TriState.FALSE
    if any(r == TriState.TRUE for r in results):
        return TriState.TRUE
    if any(r == TriState.UNDEFINED for r in results):
        return TriState.UNDEFINED
    return TriState.FALSE


def _combine_one(results: list[TriState]) -> TriState:
    if not results:
        return TriState.FALSE
    true_count = sum(1 for r in results if r == TriState.TRUE)
    if true_count > 1:
        return TriState.FALSE
    if true_count == 1:
        if any(r == TriState.UNDEFINED for r in results):
            return TriState.UNDEFINED
        return TriState.TRUE
    if any(r == TriState.UNDEFINED for r in results):
        return TriState.UNDEFINED
    return TriState.FALSE


def _combine_none(results: list[TriState]) -> TriState:
    if not results:
        return TriState.TRUE
    if any(r == TriState.TRUE for r in results):
        return TriState.FALSE
    if any(r == TriState.UNDEFINED for r in results):
        return TriState.UNDEFINED
    return TriState.TRUE


def _combine(op: str, results: list[TriState]) -> TriState:
    if op == "ALL":
        return _combine_all(results)
    if op == "ANY":
        return _combine_any(results)
    if op == "ONE":
        return _combine_one(results)
    if op == "NONE":
        return _combine_none(results)
    raise ValueError(f"Unknown combinator {op!r}")


def _evaluate_fs(node: FsCondition, processor: _SettingLookup) -> TriState:
    results: list[TriState] = []
    for feature in node.features:
        active = processor.get_active_setting(feature.fs_type, feature.feature_name)
        if active is None:
            active = Undefined
        results.append(_single_value_match(active, feature.value))
    return _combine_all(results)


def evaluate_condition(node: ConditionNode, processor: _SettingLookup) -> TriState:
    """Evaluate a parsed condition against the processor's active settings."""
    if isinstance(node, FsCondition):
        return _evaluate_fs(node, processor)
    child_results = [evaluate_condition(child, processor) for child in node.children]
    return _combine(node.op, child_results)
