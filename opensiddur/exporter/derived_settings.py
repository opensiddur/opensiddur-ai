"""Derived conditional settings (feature defaulting)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from opensiddur.exporter.calendar.compute import SettingSnapshot
from opensiddur.exporter.conditional_settings import INIT_DECLARE_ID
from opensiddur.exporter.derivation_graph import DerivationSpec, topological_derivation_order
from opensiddur.exporter.linear import ConditionalSettingEntry, LinearData, Undefined

FS_OVERRIDE = "opensiddur:override"

OVERRIDE_FEATURES = (
    "omit-tahanun",
    "house-of-mourning",
    "brit-milah",
    "wedding",
    "sheva-brachot",
)


class SettingChangeTrigger(StrEnum):
    INIT = "init"
    DECLARE = "declare"
    END_DECLARE = "end_declare"


def derived_declare_id(fs_type: str, feature_name: str) -> str:
    return f"__derived__:{fs_type}:{feature_name}"


def get_active_setting_entry(
    linear_data: LinearData,
    fs_type: str,
    feature_name: str,
) -> ConditionalSettingEntry | None:
    for entry in reversed(linear_data.conditional_settings):
        if entry.fs_type == fs_type and entry.feature_name == feature_name:
            return entry
    return None


def _is_explicit(entry: ConditionalSettingEntry) -> bool:
    return entry.source in ("init", "declared")


def _rebuild_derived_dependency_index(linear_data: LinearData) -> None:
    linear_data.derived_dependency_index = {}
    for i, entry in enumerate(linear_data.conditional_settings):
        if entry.source == "derived":
            for contributor in entry.contributors:
                linear_data.derived_dependency_index.setdefault(contributor, set()).add(i)


def _remove_derived_for_feature(
    linear_data: LinearData,
    fs_type: str,
    feature_name: str,
) -> None:
    declare_id = derived_declare_id(fs_type, feature_name)
    linear_data.conditional_settings = [
        entry
        for entry in linear_data.conditional_settings
        if not (entry.source == "derived" and entry.declare_id == declare_id)
    ]


def register_derived_entry(linear_data: LinearData, entry: ConditionalSettingEntry) -> None:
    linear_data.conditional_settings.append(entry)
    idx = len(linear_data.conditional_settings) - 1
    for contributor in entry.contributors:
        linear_data.derived_dependency_index.setdefault(contributor, set()).add(idx)


def _collect_contributors(
    linear_data: LinearData,
    required_inputs: frozenset[tuple[str, str]],
) -> tuple[set[str], bool]:
    """Return contributor declare_ids and whether all required inputs are present."""
    contributors: set[str] = set()
    for fs_type, feature_name in required_inputs:
        entry = get_active_setting_entry(linear_data, fs_type, feature_name)
        if entry is None or entry.value is Undefined:
            return contributors, False
        contributors.add(entry.declare_id)
    return contributors, True


def _push_static_override_defaults(linear_data: LinearData) -> None:
    for feature_name in OVERRIDE_FEATURES:
        if get_active_setting_entry(linear_data, FS_OVERRIDE, feature_name) is not None:
            continue
        declare_id = derived_declare_id(FS_OVERRIDE, feature_name)
        _remove_derived_for_feature(linear_data, FS_OVERRIDE, feature_name)
        register_derived_entry(
            linear_data,
            ConditionalSettingEntry(
                declare_id=declare_id,
                fs_type=FS_OVERRIDE,
                feature_name=feature_name,
                value=False,
                source="derived",
                contributors={INIT_DECLARE_ID},
            ),
        )


def _apply_derivation_spec(
    linear_data: LinearData,
    spec: DerivationSpec,
    snapshot: SettingSnapshot,
) -> None:
    fs_type = spec.fs_type
    existing_features = {
        entry.feature_name
        for entry in linear_data.conditional_settings
        if entry.fs_type == fs_type
    }

    computed = spec.compute(snapshot)
    if computed is None:
        for feature_name in existing_features:
            entry = get_active_setting_entry(linear_data, fs_type, feature_name)
            if entry is not None and entry.source == "derived":
                _remove_derived_for_feature(linear_data, fs_type, feature_name)
        _rebuild_derived_dependency_index(linear_data)
        return

    contributors, inputs_ok = _collect_contributors(linear_data, spec.required_inputs)
    if not inputs_ok:
        return

    for feature_name, value in computed.items():
        winning = get_active_setting_entry(linear_data, fs_type, feature_name)
        if winning is not None and _is_explicit(winning):
            continue
        _remove_derived_for_feature(linear_data, fs_type, feature_name)
        register_derived_entry(
            linear_data,
            ConditionalSettingEntry(
                declare_id=derived_declare_id(fs_type, feature_name),
                fs_type=fs_type,
                feature_name=feature_name,
                value=value,
                source="derived",
                contributors=contributors,
            ),
        )


class _LinearSettingLookup:
    def __init__(self, linear_data: LinearData) -> None:
        self._linear_data = linear_data

    def get(self, fs_type: str, feature_name: str) -> Any | None:
        entry = get_active_setting_entry(self._linear_data, fs_type, feature_name)
        if entry is None:
            return None
        return entry.value


def recalculate_derived_settings(
    linear_data: LinearData,
    *,
    trigger: SettingChangeTrigger,
    declare_id: str | None = None,
) -> None:
    """Recompute derived entries invalidated by a settings change."""
    del declare_id  # reserved for incremental invalidation in future

    if trigger == SettingChangeTrigger.INIT:
        _push_static_override_defaults(linear_data)

    snapshot = SettingSnapshot(_LinearSettingLookup(linear_data))
    for spec in topological_derivation_order():
        _apply_derivation_spec(linear_data, spec, snapshot)

    _rebuild_derived_dependency_index(linear_data)
