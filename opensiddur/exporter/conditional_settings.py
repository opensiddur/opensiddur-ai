"""Parse j:declare feature structures and YAML declaration entries."""

from typing import Any

from lxml.etree import ElementBase

from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS, XML_NS
from opensiddur.exporter.linear import (
    ConditionalSettingEntry,
    DeclarationFeatureValue,
    NumericValue,
    Undefined,
    parse_numeric_literal,
)

INIT_DECLARE_ID = "__init__"

TEI_FS = f"{{{TEI_NS}}}fs"
TEI_F = f"{{{TEI_NS}}}f"
TEI_NUMERIC = f"{{{TEI_NS}}}numeric"
TEI_BINARY = f"{{{TEI_NS}}}binary"
TEI_STRING = f"{{{TEI_NS}}}string"
TEI_SYMBOL = f"{{{TEI_NS}}}symbol"
TEI_DEFAULT = f"{{{TEI_NS}}}default"
TEI_VALT = f"{{{TEI_NS}}}vAlt"
TEI_VNOT = f"{{{TEI_NS}}}vNot"
J_DECLARE = f"{{{JLPTEI_NAMESPACE}}}declare"
J_END_DECLARE = f"{{{JLPTEI_NAMESPACE}}}endDeclare"
J_CONDITION = f"{{{JLPTEI_NAMESPACE}}}condition"
J_CONDITIONAL = f"{{{JLPTEI_NAMESPACE}}}conditional"
J_END_CONDITIONAL = f"{{{JLPTEI_NAMESPACE}}}endConditional"
J_ALL = f"{{{JLPTEI_NAMESPACE}}}all"
J_ANY = f"{{{JLPTEI_NAMESPACE}}}any"
J_NONE = f"{{{JLPTEI_NAMESPACE}}}none"
J_ONE = f"{{{JLPTEI_NAMESPACE}}}one"
TEI_NOTE = f"{{{TEI_NS}}}note"
XML_ID = f"{{{XML_NS}}}id"

CONDITIONAL_CONTROL_TAGS = frozenset(
    {J_DECLARE, J_END_DECLARE, J_CONDITIONAL, J_END_CONDITIONAL}
)


#: The lexical forms of xsd:boolean, which tei:binary/@value takes.
_BINARY_WORDS = {"true": True, "1": True, "false": False, "0": False}

_SIMPLE_VALUE_TAGS = frozenset({TEI_NUMERIC, TEI_BINARY, TEI_STRING, TEI_SYMBOL, TEI_DEFAULT})
_VALUE_TAGS = _SIMPLE_VALUE_TAGS | {TEI_VALT, TEI_VNOT}


def _parse_numeric(element: ElementBase) -> NumericValue:
    raw = element.get("value")
    if raw is None:
        raise ValueError("tei:numeric missing @value")
    upper = element.get("max")
    return NumericValue(
        value=parse_numeric_literal(raw),
        max_value=parse_numeric_literal(upper) if upper is not None else None,
    )


def parse_value_element(element: ElementBase, *, in_condition: bool,
                        negation_allowed: bool = True) -> Any:
    """The value one feature-value element stands for.

    Declarations and conditions read values alike, except that only a condition may give
    alternatives (``tei:vAlt``, a tuple) or a negation (``tei:vNot``, ``("vNot", value)``). A
    negation stands alone: it is not one of a set of alternatives.
    """
    tag = element.tag
    if tag == TEI_NUMERIC:
        return _parse_numeric(element)
    if tag == TEI_BINARY:
        raw = (element.get("value") or "").strip()
        if raw not in _BINARY_WORDS:
            raise ValueError(f"tei:binary @value must be true or false (or 1 or 0), not {raw!r}")
        return _BINARY_WORDS[raw]
    if tag == TEI_STRING:
        return element.text or ""
    if tag == TEI_SYMBOL:
        symbol = element.get("value", "")
        return Undefined if symbol == "undefined" else symbol
    if tag == TEI_DEFAULT:
        return Undefined
    if tag in (TEI_VALT, TEI_VNOT) and not in_condition:
        raise ValueError("tei:vAlt and tei:vNot belong in conditions, not in j:declare")
    if tag == TEI_VALT:
        return tuple(parse_value_element(alternative, in_condition=True, negation_allowed=False)
                     for alternative in _value_children(element))
    if tag == TEI_VNOT:
        if not negation_allowed:
            raise ValueError("tei:vNot cannot be one of the alternatives of a tei:vAlt")
        inner = _value_children(element)
        if len(inner) != 1:
            raise ValueError("tei:vNot must contain exactly one value element")
        return ("vNot", parse_value_element(inner[0], in_condition=True, negation_allowed=False))
    raise ValueError(f"Unsupported value element {tag!r}")


def _value_children(element: ElementBase) -> list[ElementBase]:
    return [child for child in element if child.tag in _VALUE_TAGS]


def parse_f_value(f_element: ElementBase, *, in_condition: bool) -> Any:
    """The value of a tei:f, which holds exactly one value element."""
    values = _value_children(f_element)
    name = f_element.get("name")
    if not values:
        raise ValueError(f"No value element found in tei:f[@name={name!r}]")
    if len(values) > 1:
        raise ValueError(f"tei:f[@name={name!r}] has more than one value element")
    return parse_value_element(values[0], in_condition=in_condition)


def fs_features(fs_element: ElementBase) -> tuple[str, list[ElementBase]]:
    """A tei:fs's type and its tei:f children, which must be named and at least one."""
    fs_type = fs_element.get("type")
    if not fs_type:
        raise ValueError("tei:fs missing required @type attribute")
    features = [child for child in fs_element if child.tag == TEI_F]
    if not features:
        raise ValueError(f"tei:fs[@type={fs_type!r}] has no tei:f children")
    for f_el in features:
        if not f_el.get("name"):
            raise ValueError("tei:f missing required @name attribute")
    return fs_type, features


def parse_declare_element(
    declare_el: ElementBase,
    declare_id: str,
) -> list[ConditionalSettingEntry]:
    """Parse the tei:fs children of a j:declare element into stack entries.

    A j:declare holds feature structures and nothing else, and declares at least one feature:
    one that declares nothing would have nothing for its j:endDeclare to end.
    """
    entries: list[ConditionalSettingEntry] = []
    for child in declare_el:
        if not isinstance(child.tag, str):
            continue  # a comment or processing instruction
        if child.tag != TEI_FS:
            raise ValueError(
                f"j:declare holds only tei:fs, not {child.tag!r} (in {declare_id!r})")
        fs_type, features = fs_features(child)
        entries.extend(
            ConditionalSettingEntry(
                declare_id=declare_id,
                fs_type=fs_type,
                feature_name=f_el.get("name"),
                value=parse_f_value(f_el, in_condition=False),
                source="declared",
            )
            for f_el in features
        )
    if not entries:
        raise ValueError(f"j:declare {declare_id!r} declares nothing")
    return entries


def yaml_to_declaration_entries(
    declarations: dict[str, dict[str, DeclarationFeatureValue]],
) -> list[ConditionalSettingEntry]:
    """Convert YAML declarations section to init stack entries."""
    entries: list[ConditionalSettingEntry] = []
    for fs_type, features in declarations.items():
        for feature_name, value in features.items():
            if value is None:
                parsed: Any = Undefined
            else:
                parsed = value
            entries.append(
                ConditionalSettingEntry(
                    declare_id=INIT_DECLARE_ID,
                    fs_type=fs_type,
                    feature_name=feature_name,
                    value=parsed,
                    source="init",
                )
            )
    return entries
