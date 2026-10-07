"""Which settings an electronic book leaves to its reader, and how the reader's device resolves
a condition with them.

A printed book is compiled once, for whatever its settings file says, and a setting it does not
declare stays undefined: every branch is printed with the rubric that says when to read it. An
electronic book is compiled once too, but resolved again on the reader's device, every time the
reader changes a setting. Its compile keeps the conditions that turn on *reader-supplied*
settings undecided -- the rite, who is present, whether a mourner is in the house -- so that the
device can decide them.

The *calendar* settings are the others: the date, the time and the place, and everything derived
from them. A device could answer them too, from its clock and its location, but not yet: that
takes a port of the calendar layer (`calendar/compute.py`), and until there is one they are
left as print leaves them. The reader sees every branch, with its rubric.

`resolve` is the reference for what the device computes. The JavaScript in
`html/assets/condition.js` has to agree with it, and the agreement tests hold both to the same
cases.
"""

from __future__ import annotations

from collections.abc import Mapping
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
    FS_QUORUM,
    FS_READING_CYCLE,
    FS_SERVICE_TIME,
    FS_TIME,
    FS_TORAH,
    SettingSnapshot,
    compute_quorum,
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
from opensiddur.exporter.linear import Undefined

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
    # Annual or triennial is the reader's to choose, but the cycle's year comes from the
    # date, and the two are one feature structure.
    FS_READING_CYCLE,
})

#: Derivations the device runs, because every one of their inputs is the reader's. Each must
#: have a counterpart in `condition.js`'s `DERIVATIONS`, which a test checks.
CLIENT_DERIVATIONS: dict[str, Any] = {
    FS_QUORUM: compute_quorum,
}


def is_reader_supplied(fs_type: str) -> bool:
    """Whether an electronic book leaves this feature structure to its reader.

    An open set: any feature structure that is not the calendar's is the reader's, so a new
    one (a new rite, a new circumstance) needs no change here.
    """
    return fs_type not in CALENDAR_FS_TYPES


Settings = Mapping[str, Mapping[str, Any]]


def _lookup(settings: Settings, fs_type: str, feature_name: str) -> tuple[bool, Any]:
    """(present, value) for one feature in a JSON settings mapping, value decoded."""
    features = settings.get(fs_type) or {}
    if feature_name not in features:
        return False, None
    return True, value_from_json(features[feature_name])


class ClientSettings:
    """The settings one condition is evaluated against on the reader's device.

    In order of precedence:

    1. *pinned* -- the values the compile knew where the condition stands: what the volume's
       settings file and the document's own `j:declare`s said, and what was derived from them.
       They are part of the text, and the reader cannot override them.
    2. *reader* -- what the reader has set in the book's settings panel. A null is "not set".
    3. *defaults* -- what the book starts from: the settings file's declarations and the static
       defaults, for the reader's feature structures. A null is undefined.
    4. derived -- what `CLIENT_DERIVATIONS` compute from the layers above.

    The reader's settings and the defaults together play the part of a settings file's
    declarations in a compile, and rank the same way: an explicit value -- even an explicit
    null -- is never replaced by a derived one, just as `derived_settings` never overrides an
    `init` entry. So the device resolves a condition the way a compile would, given the same
    settings.
    """

    def __init__(self, pinned: Settings, reader: Settings, defaults: Settings):
        self.pinned = pinned
        self.reader = reader
        self.defaults = defaults

    def _given(self, fs_type: str, feature_name: str) -> tuple[bool, Any]:
        present, value = _lookup(self.pinned, fs_type, feature_name)
        if present:
            return True, value
        present, value = _lookup(self.reader, fs_type, feature_name)
        if present and value is not Undefined:
            return True, value
        return False, None

    def _derived(self, fs_type: str, feature_name: str) -> tuple[bool, Any]:
        compute = CLIENT_DERIVATIONS.get(fs_type)
        if compute is None:
            return False, None

        def get_setting(fs, name):
            present, value = self._explicit(fs, name)
            return value if present and value is not Undefined else None

        computed = compute(SettingSnapshot(get_setting=get_setting)) or {}
        if feature_name in computed:
            return True, computed[feature_name]
        return False, None

    def _explicit(self, fs_type: str, feature_name: str) -> tuple[bool, Any]:
        present, value = self._given(fs_type, feature_name)
        if present:
            return True, value
        return _lookup(self.defaults, fs_type, feature_name)

    def get_active_setting(self, fs_type: str, feature_name: str) -> Any | None:
        for layer in (self._explicit, self._derived):
            present, value = layer(fs_type, feature_name)
            if present:
                return value
        return None


def resolve(
    condition: ConditionNode | Mapping[str, Any],
    *,
    pinned: Settings | None = None,
    reader: Settings | None = None,
    defaults: Settings | None = None,
) -> TriState:
    """Evaluate a condition as the reader's device does. Takes a parsed condition or its JSON."""
    if isinstance(condition, Mapping):
        condition = condition_from_json(condition)
    return evaluate_condition(
        condition, ClientSettings(pinned or {}, reader or {}, defaults or {}))
