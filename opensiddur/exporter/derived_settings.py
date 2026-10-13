"""Derived conditional settings (feature defaulting)."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from opensiddur.exporter.client_settings import is_reader_supplied
from opensiddur.exporter.calendar.compute import (
    FS_HEBREW_DATE,
    FS_READING_CYCLE,
    READING_CYCLE_DEFAULTS,
    SettingSnapshot,
)
from opensiddur.exporter.conditional_settings import INIT_DECLARE_ID
from opensiddur.exporter.derivation_graph import DerivationSpec, topological_derivation_order
from opensiddur.exporter.linear import ConditionalSettingEntry, LinearData, Undefined

logger = logging.getLogger(__name__)

FS_OVERRIDE = "opensiddur:override"
FS_PARATEXT = "opensiddur:paratext"

OVERRIDE_FEATURES = (
    "omit-tahanun",
    "house-of-mourning",
    "brit-milah",
    "wedding",
    "sheva-brachot",
)

# Features that are never computed from anything and take a fixed value unless the volume
# declares otherwise. An undeclared feature is normally *undefined*, which keeps every variant
# of a conditional text; these are the ones that instead have to answer true or false, because
# leaving them open would keep alternatives that contradict one another.
STATIC_DEFAULTS: dict[str, dict[str, Any]] = {
    FS_OVERRIDE: dict.fromkeys(OVERRIDE_FEATURES, False),
    FS_READING_CYCLE: READING_CYCLE_DEFAULTS,
    # A book's prefaces and title pages are kept unless a volume leaves them out.
    FS_PARATEXT: {"include": True, "title-page": True},
}


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


def remove_derived_for_contributor(linear_data: LinearData, declare_id: str) -> None:
    """Remove the derived entries that were computed from a declaration."""
    linear_data.conditional_settings = [
        entry
        for entry in linear_data.conditional_settings
        if not (entry.source == "derived" and declare_id in entry.contributors)
    ]


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


def _push_static_defaults(linear_data: LinearData) -> None:
    for fs_type, features in STATIC_DEFAULTS.items():
        for feature_name in features:
            if get_active_setting_entry(linear_data, fs_type, feature_name) is not None:
                continue
            _push_static_default(linear_data, fs_type, feature_name)


def _push_static_default(linear_data: LinearData, fs_type: str, feature_name: str) -> None:
    """Put a feature's fixed default on the stack, if it has one."""
    features = STATIC_DEFAULTS.get(fs_type, {})
    if feature_name not in features:
        return
    if linear_data.defer_reader_settings and is_reader_supplied(fs_type):
        # The book's default for its reader to change, not a value to compile in.
        return
    _remove_derived_for_feature(linear_data, fs_type, feature_name)
    register_derived_entry(
        linear_data,
        ConditionalSettingEntry(
            declare_id=derived_declare_id(fs_type, feature_name),
            fs_type=fs_type,
            feature_name=feature_name,
            value=features[feature_name],
            source="derived",
            contributors={INIT_DECLARE_ID},
        ),
    )


def _clear_derived(linear_data: LinearData, fs_type: str, feature_name: str) -> None:
    """Withdraw a derived value that no longer holds, falling back to the static default.

    Nothing but the static default stands behind the feature then: the absence of a date is
    exactly when a volume's fixed choice matters.
    """
    entry = get_active_setting_entry(linear_data, fs_type, feature_name)
    if entry is None or entry.source != "derived":
        return
    _remove_derived_for_feature(linear_data, fs_type, feature_name)
    _push_static_default(linear_data, fs_type, feature_name)


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
            _clear_derived(linear_data, fs_type, feature_name)
        return

    contributors, inputs_ok = _collect_contributors(linear_data, spec.required_inputs)
    if not inputs_ok:
        # An input is declared undefined. What was derived from it before no longer holds,
        # so it goes rather than standing in for a value nothing now supports.
        for feature_name in computed:
            _clear_derived(linear_data, fs_type, feature_name)
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


def _get_setting_from_linear_data(
    linear_data: LinearData,
    fs_type: str,
    feature_name: str,
) -> Any | None:
    entry = get_active_setting_entry(linear_data, fs_type, feature_name)
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
        _push_static_defaults(linear_data)

    snapshot = SettingSnapshot(
        get_setting=lambda fs_type, feature_name: _get_setting_from_linear_data(
            linear_data, fs_type, feature_name
        ),
    )
    for spec in topological_derivation_order():
        _apply_derivation_spec(linear_data, spec, snapshot)

    if trigger == SettingChangeTrigger.INIT:
        _warn_on_a_date_without_a_place(snapshot)


def _warn_on_a_date_without_a_place(snapshot: SettingSnapshot) -> None:
    """A civil date says which Hebrew date it is only at a place, the day turning at nightfall.

    Without one, and without a declared Hebrew date to fall back on, nothing that follows from
    the Hebrew date is derived -- not the holidays, not Shabbat -- and a volume that meant to be
    dated would come out undated without a word.
    """
    hebrew_date = [snapshot.get_int(FS_HEBREW_DATE, key) for key in ("year", "month", "day")]
    if (snapshot.gregorian_date() is not None and snapshot.location() is None
            and None in hebrew_date):
        logger.warning(
            "opensiddur:gregorian-date is set without an opensiddur:location, so no Hebrew "
            "date, holiday or Shabbat is derived from it")
