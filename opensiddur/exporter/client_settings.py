"""Which settings an electronic book leaves to its reader, and how the reader's device resolves
a condition with them.

A printed book is compiled once, for whatever its settings file says, and a setting it does not
declare stays undefined: every branch is printed with the rubric that says when to read it. An
electronic book is compiled once too, but resolved again on the reader's device, every time the
reader changes a setting and as the day goes by. Its compile keeps the conditions that turn on
*reader-supplied* settings undecided -- the rite, who is present, whether a mourner is in the
house -- so that the device can decide them.

The *calendar* settings are the others: the date, the time and the place, and everything derived
from them. The device answers them from its clock and from the place the reader gives, deriving
everything a compile derives (html/assets/calendar.js ports the derivations). A calendar setting
the settings file declares is compiled in, as in print.

`resolve` is the reference for what the device computes. The JavaScript in
`html/assets/condition.js` and `html/assets/calendar.js` has to agree with it, and the agreement
tests hold both to the same cases.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from opensiddur.exporter.calendar.avot import FS_AVOT
from opensiddur.exporter.calendar.compute import (
    FS_DAY_OF_WEEK,
    FS_GREGORIAN,
    FS_HEBREW_DATE,
    FS_HEBREW_TIME,
    FS_HOLIDAY,
    FS_HOLIDAY_AGG,
    FS_ISRAEL,
    FS_LOCATION,
    FS_PURIM_OBSERVANCE,
    FS_SERVICE_TIME,
    FS_TIME,
    FS_TORAH,
)
from opensiddur.exporter.calendar.hallel import FS_HALLEL
from opensiddur.exporter.calendar.motzaei_shabbat import FS_MOTZAEI_SHABBAT
from opensiddur.exporter.condition_eval import (
    ConditionNode,
    TriState,
    condition_from_json,
    evaluate_condition,
    value_from_json,
)
from opensiddur.exporter.linear import ConditionalSettingEntry, LinearData

#: Feature structures a device would answer from its clock and its location.
CALENDAR_FS_TYPES: frozenset[str] = frozenset({
    FS_GREGORIAN,
    FS_TIME,
    FS_LOCATION,
    FS_ISRAEL,
    FS_HEBREW_DATE,
    FS_HEBREW_TIME,
    FS_DAY_OF_WEEK,
    FS_HOLIDAY,
    FS_HOLIDAY_AGG,
    FS_TORAH,
    FS_SERVICE_TIME,
    FS_HALLEL,
    FS_MOTZAEI_SHABBAT,
    FS_AVOT,
    # Which day is Purim goes with the calendar, not the reader: an electronic book is
    # compiled with it, so the celebrated day is known wherever the date is.
    FS_PURIM_OBSERVANCE,
})


def is_reader_supplied(fs_type: str) -> bool:
    """Whether an electronic book leaves this feature structure to its reader.

    An open set: any feature structure that is not the calendar's is the reader's, so a new
    one (a new rite, a new circumstance) needs no change here.
    """
    return fs_type not in CALENDAR_FS_TYPES


Settings = Mapping[str, Mapping[str, Any]]

#: The layers the device resolves against, the earliest first: a later one prevails, and is the
#: later declaration where a civil and a Hebrew date are both given.
#:
#: 1. *device* -- what the device knows by itself: the date and the time, from its clock.
#: 2. *defaults* -- what the book starts from: the settings file's declarations and the static
#:    defaults, for the reader's feature structures. A null is undefined.
#: 3. *reader* -- what the reader has set in the book's settings panel: a chosen date and time,
#:    a place, any feature at all. A feature the reader has not touched is absent; a null is the
#:    reader's own "show every option", which holds even where the book has a default.
#: 4. *pinned* -- the values the compile knew where the condition stands: what the volume's
#:    settings file and the document's own `j:declare`s said, and what was derived from them.
#:    They are part of the text, and the reader cannot override them.
#:
#: The calendar's derivations run over all four, as a compile runs them over its declarations:
#: an explicit value -- even an explicit null -- is never replaced by a derived one. So the
#: device resolves a condition the way a compile would, given the same settings.
LAYERS = ("device", "defaults", "reader", "pinned")


def derive_settings(
    *, device: Settings | None = None, defaults: Settings | None = None,
    reader: Settings | None = None, pinned: Settings | None = None,
) -> dict[tuple[str, str], Any]:
    """Every setting in force on the device, derived ones included, by (fs type, feature)."""
    layers = {"device": device, "defaults": defaults, "reader": reader, "pinned": pinned}
    return _derive(json.dumps([layers[name] or {} for name in LAYERS], sort_keys=True))


_derived_settings_logger = logging.getLogger("opensiddur.exporter.derived_settings")


@lru_cache(maxsize=4096)
def _derive(key: str) -> dict[tuple[str, str], Any]:
    # derived_settings decides what is the reader's by this module, so it is imported here.
    from opensiddur.exporter.derived_settings import (
        SettingChangeTrigger,
        recalculate_derived_settings,
    )

    linear_data = LinearData(defer_reader_settings=True)
    for name, layer in zip(LAYERS, json.loads(key)):
        # What the device and the book start from is a settings file's; the rest is declared.
        source = "init" if name in ("device", "defaults") else "declared"
        for fs_type, features in layer.items():
            for feature_name, value in features.items():
                linear_data.conditional_settings.append(ConditionalSettingEntry(
                    declare_id=f"{name}:{fs_type}:{feature_name}", fs_type=fs_type,
                    feature_name=feature_name, value=value_from_json(value), source=source))
    # A date without a place is the device's ordinary state until the reader gives one, not a
    # mistake in a settings file to warn of.
    disabled = _derived_settings_logger.disabled
    _derived_settings_logger.disabled = True
    try:
        recalculate_derived_settings(linear_data, trigger=SettingChangeTrigger.INIT)
    finally:
        _derived_settings_logger.disabled = disabled
    return {(entry.fs_type, entry.feature_name): entry.value
            for entry in linear_data.conditional_settings}


class _Active:
    def __init__(self, settings: dict[tuple[str, str], Any]):
        self.settings = settings

    def get_active_setting(self, fs_type: str, feature_name: str) -> Any | None:
        return self.settings.get((fs_type, feature_name))


def resolve(
    condition: ConditionNode | Mapping[str, Any],
    *,
    pinned: Settings | None = None,
    reader: Settings | None = None,
    defaults: Settings | None = None,
    device: Settings | None = None,
) -> TriState:
    """Evaluate a condition as the reader's device does. Takes a parsed condition or its JSON.

    A value the compile pinned for bein hashmashot holds one value for each of the two days.
    The condition is resolved once for each day, the derivations included, and is decided only
    if it comes out the same on both. A moment the device is at between sunset and nightfall is
    worked out for both days by the derivations themselves.
    """
    if isinstance(condition, Mapping):
        condition = condition_from_json(condition)
    pinned = pinned or {}
    layers = {"device": device, "defaults": defaults, "reader": reader}
    if _has_twilight(pinned):
        ending, starting = (
            evaluate_condition(condition, _Active(derive_settings(
                **layers, pinned=_pinned_on_day(pinned, day))))
            for day in (0, 1))
        return ending if ending == starting else TriState.UNDEFINED
    return evaluate_condition(condition, _Active(derive_settings(**layers, pinned=pinned)))


def _is_twilight(encoded: Any) -> bool:
    return isinstance(encoded, Mapping) and "twilight" in encoded


def _has_twilight(settings: Settings) -> bool:
    return any(_is_twilight(value) for features in settings.values() for value in features.values())


def _pinned_on_day(settings: Settings, day: int) -> Settings:
    """Pinned settings as they stand on the ending day (0) or the starting day (1)."""
    return {
        fs_type: {name: value["twilight"][day] if _is_twilight(value) else value
                  for name, value in features.items()}
        for fs_type, features in settings.items()
    }
