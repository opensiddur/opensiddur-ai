"""Compute derived JLPTEI calendar feature values from active settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

import hdate
from pyluach import dates as pyluach_dates
from pyluach import parshios

from opensiddur.exporter.linear import NumericValue

FeatureRef = tuple[str, str]

FS_GREGORIAN = "opensiddur:gregorian-date"
FS_TIME = "opensiddur:time"
FS_HEBREW_DATE = "opensiddur:hebrew-date"
FS_HEBREW_TIME = "opensiddur:hebrew-time"
FS_LOCATION = "opensiddur:location"
FS_ISRAEL = "opensiddur:israel"
FS_DAY_OF_WEEK = "opensiddur:day-of-week"
FS_HOLIDAY = "opensiddur:holiday"
FS_HOLIDAY_AGG = "opensiddur:holiday-aggregate"
FS_TORAH = "opensiddur:torah-reading"
FS_SERVICE_TIME = "opensiddur:service-time"

# Israel approximate bounding box (lat/lon).
_ISRAEL_LAT = (29.5, 33.5)
_ISRAEL_LON = (34.2, 36.0)

HOLIDAY_FEATURES = (
    "pesah",
    "omer",
    "pesah-sheini",
    "lag-baomer",
    "shavuot",
    "tisha-bav",
    "tu-bav",
    "rosh-hashana",
    "tzom-gedalia",
    "yom-kippur",
    "sukkot",
    "shmini-atzeret",
    "hanukkah",
    "asara-btevet",
    "taanit-esther",
    "purim",
    "shushan-purim",
    "purim-meshulash",
    "purim-katan",
    "shushan-purim-katan",
    "rosh-hodesh",
    "tu-bishvat",
    "taanit-bchorot",
    "tzom-tammuz",
    "sigd",
    "yom-hashoah",
    "yom-hazikaron",
    "yom-haatzmaut",
    "yom-yerusahalayim",
)

AGGREGATE_FEATURES = (
    "shabbat",
    "yom-tov",
    "chol-hamoed",
    "regalim",
    "hoshana-rabba",
    "high-holidays",
    "aseret-ymei-tshuva",
    "minor-fast",
    "day-before-holiday",
    "day-after-holiday",
)

TORAH_FEATURES = (
    "diaspora-parsha",
    "israel-parsha",
    "shabbat-shuva",
    "shabbat-shira",
    "shabbat-shkalim",
    "shabbat-zachor",
    "shabbat-hahodesh",
    "shabbat-hagadol",
    "shabbat-hazon",
    "shabbat-nahamu",
)

SERVICE_TIME_FEATURES = (
    "shaharit",
    "minha",
    "maariv",
    "musaf",
    "neila",
    "slihot",
)


@dataclass(frozen=True)
class SettingSnapshot:
    """Read-only view of active setting values."""

    get_setting: Callable[[str, str], Any | None]

    def get(self, fs_type: str, feature_name: str) -> Any | None:
        return self.get_setting(fs_type, feature_name)

    def get_int(self, fs_type: str, feature_name: str) -> int | None:
        value = self.get(fs_type, feature_name)
        if value is None:
            return None
        if isinstance(value, NumericValue):
            return value.value
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            return int(value)
        return int(value)

    def get_bool(self, fs_type: str, feature_name: str) -> bool | None:
        value = self.get(fs_type, feature_name)
        if value is None:
            return None
        return bool(value)

    def gregorian_date(self) -> date | None:
        year = self.get_int(FS_GREGORIAN, "year")
        month = self.get_int(FS_GREGORIAN, "month")
        day = self.get_int(FS_GREGORIAN, "day")
        if year is None or month is None or day is None:
            return None
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def time_of_day(self) -> time | None:
        hour = self.get_int(FS_TIME, "hour")
        minute = self.get_int(FS_TIME, "minute")
        second = self.get_int(FS_TIME, "second")
        if hour is None or minute is None:
            return None
        if second is None:
            second = 0
        try:
            return time(hour, minute, second)
        except ValueError:
            return None

    def location(self) -> hdate.Location | None:
        lat = self.get(FS_LOCATION, "latitude")
        lon = self.get(FS_LOCATION, "longitude")
        if lat is None or lon is None:
            return None
        return hdate.Location("", float(lat), float(lon), "UTC", 0)

    def is_diaspora(self) -> bool:
        is_israel = self.get_bool(FS_ISRAEL, "is-israel")
        if is_israel is not None:
            return not is_israel
        loc = self.location()
        if loc is None:
            return True
        return not (
            _ISRAEL_LAT[0] <= loc.latitude <= _ISRAEL_LAT[1]
            and _ISRAEL_LON[0] <= loc.longitude <= _ISRAEL_LON[1]
        )


def _jlptei_weekday(python_weekday: int) -> int:
    """Convert Python weekday (Mon=0) to JLPTEI (Sun=1 .. Sat=7)."""
    return ((python_weekday + 1) % 7) + 1


def _pyluach_from_gregorian(gdate: date) -> pyluach_dates.GregorianDate:
    return pyluach_dates.GregorianDate(gdate.year, gdate.month, gdate.day)


def _hebrew_from_snapshot(snapshot: SettingSnapshot) -> pyluach_dates.HebrewDate | None:
    gdate = snapshot.gregorian_date()
    if gdate is not None and snapshot.location() is not None:
        return _pyluach_from_gregorian(gdate).to_heb()
    year = snapshot.get_int(FS_HEBREW_DATE, "year")
    month = snapshot.get_int(FS_HEBREW_DATE, "month")
    day = snapshot.get_int(FS_HEBREW_DATE, "day")
    if year is None or month is None or day is None:
        return None
    try:
        return pyluach_dates.HebrewDate(year, month, day)
    except ValueError:
        return None


def _datetime_from_snapshot(snapshot: SettingSnapshot) -> datetime | None:
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    tod = snapshot.time_of_day()
    if tod is None:
        return datetime.combine(gdate, time(12, 0))
    return datetime.combine(gdate, tod)


def compute_hebrew_date(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None or snapshot.location() is None:
        return None
    heb = _pyluach_from_gregorian(gdate).to_heb()
    return {"year": heb.year, "month": heb.month, "day": heb.day}


def compute_hebrew_time(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    loc = snapshot.location()
    dt = _datetime_from_snapshot(snapshot)
    if gdate is None or loc is None or dt is None:
        return None
    z = hdate.Zmanim(gdate, location=loc)
    sunrise = z.netz_hachama.local
    sunset = z.shkia.local
    aware_dt = dt.replace(tzinfo=sunrise.tzinfo)
    if aware_dt < sunrise:
        variable_hour = 0
        elapsed = (aware_dt - (sunrise - timedelta(days=1))).total_seconds()
    elif aware_dt < sunset:
        day_length = (sunset - sunrise).total_seconds()
        elapsed = (aware_dt - sunrise).total_seconds()
        variable_hour = min(11, int(elapsed / day_length * 12)) if day_length else 0
    else:
        night_start = sunset
        next_sunrise = z.netz_hachama.local + timedelta(days=1)
        night_length = (next_sunrise - night_start).total_seconds()
        elapsed = (aware_dt - night_start).total_seconds()
        variable_hour = 12 + min(11, int(elapsed / night_length * 12)) if night_length else 12
    part = int((elapsed % 3600) / (3600 / 1080)) if elapsed >= 0 else 0
    part = max(0, min(1079, part))
    return {"variable-hour": variable_hour, "part": part}


def compute_israel(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    lat = snapshot.get(FS_LOCATION, "latitude")
    lon = snapshot.get(FS_LOCATION, "longitude")
    if lat is None or lon is None:
        return None
    is_israel = (
        _ISRAEL_LAT[0] <= float(lat) <= _ISRAEL_LAT[1]
        and _ISRAEL_LON[0] <= float(lon) <= _ISRAEL_LON[1]
    )
    return {"is-israel": is_israel}


def compute_day_of_week(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    result: dict[str, Any] = {"secular-day": _jlptei_weekday(gdate.weekday())}
    loc = snapshot.location()
    dt = _datetime_from_snapshot(snapshot)
    heb = _hebrew_from_snapshot(snapshot)
    if heb is not None:
        hebrew_day = _jlptei_weekday(
            pyluach_dates.HebrewDate(heb.year, heb.month, heb.day).to_greg().weekday()
        )
        bayn = False
        if loc is not None and dt is not None and snapshot.time_of_day() is not None:
            z = hdate.Zmanim(gdate, location=loc)
            aware_dt = dt.replace(tzinfo=z.shkia.local.tzinfo)
            bayn = z.shkia.local < aware_dt < z.tset_hakohavim.local
            if bayn:
                hebrew_day = _jlptei_weekday((gdate + timedelta(days=1)).weekday())
        result["hebrew-day"] = hebrew_day
        result["bayn-hashmashot"] = bayn
    return result


def _zero_holidays() -> dict[str, int]:
    return {name: 0 for name in HOLIDAY_FEATURES}


def _map_hdate_holidays(
    hi: hdate.HDateInfo,
    heb: pyluach_dates.HebrewDate,
) -> dict[str, int]:
    values = _zero_holidays()
    for holiday in hi.holidays:
        name = holiday.name
        if name == "pesach":
            values["pesah"] = 1
        elif name == "pesach_ii":
            values["pesah"] = 2
        elif name.startswith("hol_hamoed_pesach"):
            values["pesah"] = heb.day - 14
        elif name == "pesach_vii":
            values["pesah"] = 7
        elif name == "pesach_viii":
            values["pesah"] = 8
        elif name == "shavuot":
            values["shavuot"] = 1
        elif name == "shavuot_ii":
            values["shavuot"] = 2
        elif name == "rosh_hashana_i":
            values["rosh-hashana"] = 1
        elif name == "rosh_hashana_ii":
            values["rosh-hashana"] = 2
        elif name == "yom_kippur":
            values["yom-kippur"] = 1
        elif name == "sukkot":
            values["sukkot"] = 1
        elif name == "sukkot_ii":
            values["sukkot"] = 2
        elif name.startswith("hol_hamoed_sukkot"):
            values["sukkot"] = heb.day - 14
        elif name == "hoshana_raba":
            values["sukkot"] = 7
        elif name == "shmini_atzeret":
            values["shmini-atzeret"] = 1
        elif name == "simchat_torah":
            values["shmini-atzeret"] = 2
        elif name == "chanuka":
            values["hanukkah"] = heb.day - 24
        elif name == "purim":
            values["purim"] = 1
        elif name == "shushan_purim":
            values["shushan-purim"] = 1
        elif name == "tzom_gedalia":
            values["tzom-gedalia"] = 1
        elif name == "asara_btevet":
            values["asara-btevet"] = 1
        elif name == "taanit_esther":
            values["taanit-esther"] = 1
        elif name == "tisha_bav":
            values["tisha-bav"] = 1
        elif name == "tu_bav":
            values["tu-bav"] = 1
        elif name == "tu_bishvat":
            values["tu-bishvat"] = 1
        elif name == "sigd":
            values["sigd"] = 1
        elif name == "yom_hashoah":
            values["yom-hashoah"] = 1
        elif name == "yom_hazikaron":
            values["yom-hazikaron"] = 1
        elif name == "yom_haatzmaut":
            values["yom-haatzmaut"] = 1
        elif name == "yom_yerushalayim":
            values["yom-yerusahalayim"] = 1
        elif name == "lag_baomer":
            values["lag-baomer"] = 1
        elif name == "pesach_sheini":
            values["pesah-sheini"] = 1

    if hi.omer:
        values["omer"] = hi.omer.day

    if heb.day in (1, 30) and heb.month in (1, 3, 5, 7, 9, 11):
        values["rosh-hodesh"] = 1 if heb.day == 1 else 2

    return values


def compute_holiday(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    heb = _hebrew_from_snapshot(snapshot)
    if gdate is None or heb is None:
        return None
    diaspora = snapshot.is_diaspora()
    hi = hdate.HDateInfo(gdate, diaspora=diaspora)
    return _map_hdate_holidays(hi, heb)


def compute_holiday_aggregate(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    holidays = compute_holiday(snapshot)
    dow = compute_day_of_week(snapshot)
    heb = _hebrew_from_snapshot(snapshot)
    if holidays is None or dow is None:
        return None
    is_shabbat = dow.get("hebrew-day") == 7 or dow.get("secular-day") == 7
    yom_tov = any(
        holidays.get(k, 0) > 0
        for k in (
            "pesah", "shavuot", "rosh-hashana", "yom-kippur", "sukkot", "shmini-atzeret",
        )
    )
    chol_hamoed = holidays.get("pesah", 0) in (3, 4, 5, 6) or holidays.get("sukkot", 0) in (3, 4, 5, 6)
    regalim = holidays.get("pesah", 0) > 0 or holidays.get("shavuot", 0) > 0 or holidays.get("sukkot", 0) > 0
    aseret = (
        heb is not None
        and heb.month == 7
        and 1 <= heb.day <= 10
    )
    return {
        "shabbat": is_shabbat,
        "yom-tov": yom_tov,
        "chol-hamoed": chol_hamoed,
        "regalim": regalim,
        "hoshana-rabba": holidays.get("sukkot", 0) == 7,
        "high-holidays": holidays.get("rosh-hashana", 0) > 0 or holidays.get("yom-kippur", 0) > 0,
        "aseret-ymei-tshuva": aseret,
        "minor-fast": any(holidays.get(k, 0) > 0 for k in ("tzom-gedalia", "asara-btevet", "taanit-esther", "tisha-bav")),
        "day-before-holiday": False,
        "day-after-holiday": False,
    }


def _parsha_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(",", "")


def compute_torah_reading(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    g = _pyluach_from_gregorian(gdate)
    diaspora = parshios.getparsha_string(g, israel=False) or ""
    israel = parshios.getparsha_string(g, israel=True) or ""
    result: dict[str, Any] = {
        "diaspora-parsha": _parsha_slug(diaspora),
        "israel-parsha": _parsha_slug(israel),
    }
    for feature in TORAH_FEATURES:
        if feature not in result:
            result[feature] = False
    # Special Shabbatot detection via parsha names (simplified).
    lower = diaspora.lower()
    result["shabbat-shuva"] = "haazinu" in lower and gdate.month == 9
    result["shabbat-shira"] = "beshalach" in lower
    result["shabbat-shkalim"] = "shekalim" in lower
    result["shabbat-zachor"] = "zachor" in lower or "zachor" in lower
    result["shabbat-hahodesh"] = "hachodesh" in lower or "hahodesh" in lower
    result["shabbat-hagadol"] = "hagadol" in lower
    result["shabbat-hazon"] = "hazon" in lower
    result["shabbat-nahamu"] = "nahamu" in lower or "vaetchanan" in lower
    return result


def compute_service_time(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    loc = snapshot.location()
    dt = _datetime_from_snapshot(snapshot)
    if gdate is None or loc is None or dt is None or snapshot.time_of_day() is None:
        return None
    z = hdate.Zmanim(gdate, location=loc)
    aware_dt = dt.replace(tzinfo=z.alot_hashachar.local.tzinfo)
    holidays = compute_holiday(snapshot) or {}
    dow = compute_day_of_week(snapshot) or {}
    is_shabbat = dow.get("hebrew-day") == 7
    return {
        "shaharit": z.alot_hashachar.local <= aware_dt < z.sof_zman_tfilla_gra.local,
        "minha": z.mincha_gedola.local <= aware_dt < z.shkia.local,
        "maariv": aware_dt >= z.tset_hakohavim.local,
        "musaf": is_shabbat or any(
            holidays.get(k, 0) > 0 for k in ("pesah", "shavuot", "rosh-hashana", "sukkot")
        ),
        "neila": holidays.get("yom-kippur", 0) > 0 and aware_dt >= z.plag_hamincha.local,
        "slihot": z.alot_hashachar.local <= aware_dt < z.netz_hachama.local,
    }
