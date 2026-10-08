"""The "Kind of day" choices of the electronic book's settings panel, worked out from the calendar.

Each kind of day is a test on what the compiler derives for a date -- "Pesah, first day" is the
dates on which ``holiday:pesah`` is 1 -- and the features the choice sets are the ones that come
out the same on *every* date that passes the test, over several years, in Israel and outside it
(or only outside it, for a day kept only there). So a choice sets exactly what it can be sure
of, and the compiler's own calendar is what makes it sure: Rosh Hodesh leaves Hanukkah unset,
because Rosh Hodesh Tevet falls in Hanukkah; an ordinary day leaves the omer unset, because the
omer is counted on ordinary days.

The result is committed, as kinds_of_day.json, so that building a book does not scan the
calendar. Regenerate it after changing this file or the calendar:

    python -m opensiddur.exporter.html.kinds_of_day

A test regenerates it and compares.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from opensiddur.exporter.calendar.compute import FS_HOLIDAY, FS_HOLIDAY_AGG
from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.conditional_settings import yaml_to_declaration_entries
from opensiddur.exporter.linear import get_linear_data, reset_linear_data

OUTPUT = Path(__file__).parent / "kinds_of_day.json"

#: Five Hebrew years, 5787 to 5791.
FIRST_DAY = date(2026, 9, 12)
LAST_DAY = date(2031, 9, 17)

ISRAEL = (31.78, 35.22)
OUTSIDE_ISRAEL = (40.71, -74.01)

#: Not a kind of day's to set. The day of the week has a choice of its own, and Shabbat goes
#: with it; the seasons of rain and dew change within a day (at Musaf), so no date settles them.
EXCLUDED = frozenset({
    (FS_HOLIDAY_AGG, "shabbat"),
    (FS_HOLIDAY_AGG, "motzaei-shabbat"),
    (FS_HOLIDAY_AGG, "day-before-holiday"),
    (FS_HOLIDAY_AGG, "day-after-holiday"),
    (FS_HOLIDAY_AGG, "eruv-tavshilin"),
    (FS_HOLIDAY_AGG, "geshem"),
    (FS_HOLIDAY_AGG, "tal-umatar"),
})

Day = dict[tuple[str, str], Any]


def holiday(day: Day, name: str) -> int:
    return day.get((FS_HOLIDAY, name)) or 0


def aggregate(day: Day, name: str) -> bool:
    return day.get((FS_HOLIDAY_AGG, name)) is True


#: The holidays an ordinary day is none of. The omer is not here: it is counted on ordinary days.
NOT_ORDINARY = (
    "rosh-hodesh", "pesah", "shavuot", "sukkot", "shmini-atzeret", "rosh-hashana", "yom-kippur",
    "hanukkah", "purim", "shushan-purim", "tzom-gedalia", "asara-btevet", "taanit-esther",
    "tzom-tammuz", "tisha-bav",
)


@dataclass(frozen=True)
class Kind:
    label: str
    test: Callable[[Day], bool]
    #: A day kept only outside Israel is sampled only there.
    outside_israel_only: bool = False


KINDS: tuple[Kind, ...] = (
    Kind("An ordinary day", lambda d: not any(holiday(d, h) for h in NOT_ORDINARY)
         and not any(aggregate(d, a) for a in ("yom-tov", "chol-hamoed", "minor-fast",
                                               "aseret-ymei-tshuva"))),
    Kind("Rosh Hodesh", lambda d: holiday(d, "rosh-hodesh") > 0 and not aggregate(d, "yom-tov")),
    Kind("Hol HaMoed Pesah", lambda d: aggregate(d, "chol-hamoed") and holiday(d, "pesah") > 0),
    Kind("Hol HaMoed Sukkot", lambda d: aggregate(d, "chol-hamoed") and holiday(d, "sukkot") > 0
         and not aggregate(d, "hoshana-rabba")),
    Kind("Hoshana Rabba", lambda d: aggregate(d, "hoshana-rabba")),
    Kind("Pesah, first day", lambda d: holiday(d, "pesah") == 1),
    Kind("Pesah, second day (outside Israel)", lambda d: holiday(d, "pesah") == 2,
         outside_israel_only=True),
    Kind("Pesah, seventh day", lambda d: holiday(d, "pesah") == 7),
    Kind("Pesah, eighth day (outside Israel)", lambda d: holiday(d, "pesah") == 8,
         outside_israel_only=True),
    Kind("Shavuot, first day", lambda d: holiday(d, "shavuot") == 1),
    Kind("Shavuot, second day (outside Israel)", lambda d: holiday(d, "shavuot") == 2,
         outside_israel_only=True),
    Kind("Sukkot, first day", lambda d: holiday(d, "sukkot") == 1),
    Kind("Sukkot, second day (outside Israel)", lambda d: holiday(d, "sukkot") == 2,
         outside_israel_only=True),
    Kind("Shemini Atzeret", lambda d: holiday(d, "shmini-atzeret") == 1),
    Kind("Simhat Torah (outside Israel)", lambda d: holiday(d, "shmini-atzeret") == 2,
         outside_israel_only=True),
    Kind("Rosh Hashanah", lambda d: holiday(d, "rosh-hashana") > 0),
    Kind("Yom Kippur", lambda d: holiday(d, "yom-kippur") > 0),
    Kind("The Ten Days of Repentance (a weekday)", lambda d: aggregate(d, "aseret-ymei-tshuva")
         and not aggregate(d, "yom-tov") and not aggregate(d, "minor-fast")
         and not holiday(d, "yom-kippur")),
    Kind("Hanukkah", lambda d: holiday(d, "hanukkah") > 0),
    Kind("Purim", lambda d: holiday(d, "purim") > 0),
    Kind("Shushan Purim", lambda d: holiday(d, "shushan-purim") > 0),
    Kind("A fast day", lambda d: aggregate(d, "minor-fast") and not holiday(d, "tisha-bav")),
    Kind("Tisha b'Av", lambda d: holiday(d, "tisha-bav") > 0),
)


def _derive(day: date, place: tuple[float, float]) -> Day:
    reset_linear_data()
    linear_data = get_linear_data()
    latitude, longitude = place
    CompilerProcessor.load_init_settings(linear_data, yaml_to_declaration_entries({
        "opensiddur:gregorian-date": {"year": day.year, "month": day.month, "day": day.day},
        "opensiddur:location": {"latitude": latitude, "longitude": longitude},
    }))
    derived = {(e.fs_type, e.feature_name): e.value for e in linear_data.conditional_settings
               if e.fs_type in (FS_HOLIDAY, FS_HOLIDAY_AGG)}
    reset_linear_data()
    return derived


def calendar_days() -> dict[str, list[Day]]:
    """What the compiler derives for every day of the range, in Israel and outside it."""
    days: dict[str, list[Day]] = {"israel": [], "outside": []}
    day = FIRST_DAY
    while day <= LAST_DAY:
        days["israel"].append(_derive(day, ISRAEL))
        days["outside"].append(_derive(day, OUTSIDE_ISRAEL))
        day += timedelta(days=1)
    return days


def certain(matching: list[Day]) -> dict[str, dict[str, Any]]:
    """The features with the same value on every one of the days, as {fs type: {feature: value}}."""
    keys = set.intersection(*(set(day) for day in matching)) - EXCLUDED
    found: dict[str, dict[str, Any]] = {}
    for fs, name in sorted(keys):
        values = {json.dumps(day[(fs, name)]) for day in matching}
        if len(values) == 1:
            found.setdefault(fs, {})[name] = matching[0][(fs, name)]
    return found


def generate(days: dict[str, list[Day]] | None = None) -> list[dict[str, Any]]:
    days = days or calendar_days()
    options = []
    for kind in KINDS:
        places = ["outside"] if kind.outside_israel_only else ["israel", "outside"]
        matching = [day for place in places for day in days[place] if kind.test(day)]
        if not matching:
            raise ValueError(f"no day in {FIRST_DAY}..{LAST_DAY} is {kind.label!r}")
        options.append({"label": kind.label, "set": certain(matching)})
    return options


def write(path: Path = OUTPUT) -> None:
    path.write_text(json.dumps(generate(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    write()
    print(f"Written: {OUTPUT}")
