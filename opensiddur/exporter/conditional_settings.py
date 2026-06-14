"""Parse j:declare feature structures and YAML declaration entries."""

from typing import Any

from lxml.etree import ElementBase

from opensiddur.exporter.constants import JLPTEI_NAMESPACE, TEI_NS, XML_NS
from opensiddur.exporter.linear import (
    ConditionalSettingEntry,
    DeclarationFeatureValue,
    NumericValue,
    Undefined,
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


def _parse_te_f_value(f_element: ElementBase) -> Any:
    """Parse the value child of a tei:f element."""
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
            if raw == "true":
                return True
            return False
        if child.tag == TEI_STRING:
            return child.text or ""
        if child.tag == TEI_SYMBOL:
            sym = child.get("value", "")
            if sym == "undefined":
                return Undefined
            return sym
        if child.tag == TEI_DEFAULT:
            return Undefined
        if child.tag in (TEI_VALT, TEI_VNOT):
            raise ValueError(
                f"tei:vAlt/tei:vNot not supported in j:declare for feature {f_element.get('name')!r}"
            )
    raise ValueError(f"No value element found in tei:f[@name={f_element.get('name')!r}]")


def _parse_te_fs(fs_element: ElementBase, declare_id: str, source: str) -> list[ConditionalSettingEntry]:
    fs_type = fs_element.get("type")
    if not fs_type:
        raise ValueError("tei:fs missing required @type attribute")
    entries: list[ConditionalSettingEntry] = []
    for f_el in fs_element:
        if f_el.tag != TEI_F:
            continue
        feature_name = f_el.get("name")
        if not feature_name:
            raise ValueError("tei:f missing required @name attribute")
        entries.append(
            ConditionalSettingEntry(
                declare_id=declare_id,
                fs_type=fs_type,
                feature_name=feature_name,
                value=_parse_te_f_value(f_el),
                source=source,  # type: ignore[arg-type]
            )
        )
    return entries


def parse_declare_element(
    declare_el: ElementBase,
    declare_id: str,
) -> list[ConditionalSettingEntry]:
    """Parse tei:fs children of a j:declare element into stack entries."""
    entries: list[ConditionalSettingEntry] = []
    for child in declare_el:
        if child.tag == TEI_FS:
            entries.extend(_parse_te_fs(child, declare_id, "declared"))
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
