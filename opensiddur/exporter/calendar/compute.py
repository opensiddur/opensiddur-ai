"""Compute derived JLPTEI calendar feature values from active settings."""

from __future__ import annotations

import calendar
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import hdate
import tzfpy
from pyluach import dates as pyluach_dates
from pyluach import hebrewcal
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
FS_READING_CYCLE = "opensiddur:reading-cycle"
FS_SERVICE_TIME = "opensiddur:service-time"
FS_QUORUM = "opensiddur:quorum"
FS_HOUSEHOLD = "opensiddur:household"
FS_VARIANT = "opensiddur:variant"
FS_RECITATION = "opensiddur:recitation"

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
    "geshem",
    "tal-umatar",
)

# The modern triennial cycle as reckoned by the CJLS, whose first year was 5756.
_TRIENNIAL_EPOCH_YEAR = 5756

# The six pairs of parshiyot whose triennial division depends on how the pair fell in the
# cycle, each with the index pyluach gives the first of the two. Nitzavim-Vayeilech is doubled
# as well but divides the same way however it falls, so it needs no feature.
TRIENNIAL_PAIRS: tuple[tuple[str, int], ...] = (
    ("vayakhel-pekudei", 21),
    ("tazria-metzora", 26),
    ("achrei-mot-kedoshim", 28),
    ("behar-bechukotai", 31),
    ("chukat-balak", 38),
    ("matot-masei", 41),
)

TRIENNIAL_PATTERN_FEATURES = tuple(
    f"triennial-pattern-{pair}" for pair, _ in TRIENNIAL_PAIRS
)

TORAH_FEATURES = (
    "diaspora-parsha",
    "israel-parsha",
    "triennial-year",
    *TRIENNIAL_PATTERN_FEATURES,
    "shabbat-shuva",
    "shabbat-shira",
    "shabbat-shkalim",
    "shabbat-zachor",
    "shabbat-parah",
    "shabbat-hahodesh",
    "shabbat-hagadol",
    "shabbat-hazon",
    "shabbat-nahamu",
    "shabbat-rosh-hodesh",
    "shabbat-mahar-hodesh",
)

# Hebrew month numbers as pyluach counts them: 1 = Nisan through 12 = Adar, with Adar I as 12
# and Adar II as 13 in a leap year.
_NISAN = 1
_AV = 5
_TISHREI = 7
_ADAR = 12
_ADAR_II = 13

# The cycle turns over on Simhat Torah; see _triennial_year for why the Israel date serves both
# rites.
_SIMHAT_TORAH_DAY = 22

# Which readings the volume carries: the annual haftarah of each week, or the triennial one of
# a given cycle year, or several at once. One binary per year rather than a single year number,
# so that a volume for a whole three-year cycle can turn on all three — a printed humash is a
# durable book, and covering a cycle is at least as natural as being for one Shabbat. Several
# may be true together, the way several rites may be.
#
# `triennial` is the volume's opt-in, and is what makes a date mean anything here: every date
# falls in some year of the cycle, including the dates a volume that reads annually is compiled
# for, so the date alone can never select a reading. It is never derived.
#
# These take a value rather than staying undefined, unlike most features. The annual haftarah
# and the three triennial ones are read on the same Shabbat, and an undefined condition keeps
# its text, so leaving them open would print four haftarot for one week.
TRIENNIAL_YEARS = (1, 2, 3)

TRIENNIAL_YEAR_FEATURES = tuple(f"triennial-year-{year}" for year in TRIENNIAL_YEARS)

READING_CYCLE_DEFAULTS: dict[str, Any] = {
    "annual": True,
    "triennial": False,
    **dict.fromkeys(TRIENNIAL_YEAR_FEATURES, False),
}

#: Which recitation of a prayer said more than once in a service this is.
#:
#: Independent of *which* service: every Amidah is said silently and then, when a minyan is
#: present, repeated aloud -- the Kedushah belongs to the repetition and Atah Kadosh to the
#: silent. ``quorum/minyan`` will not stand in for it, since with a minyan present the
#: individual still says the silent Amidah first.
#:
#: Declared, never derived from a date, and undefined by default: a volume printing both
#: recitations declares neither, and both are kept.
RECITATION_FEATURES = (
    "silent",
    "repetition",
)

SERVICE_TIME_FEATURES = (
    "shaharit",
    "minha",
    "maariv",
    "musaf",
    "neila",
    "slihot",
)


def _timezone_name_at(latitude: float, longitude: float) -> str | None:
    """The IANA zone name covering a coordinate, or None if there is none."""
    # tzfpy takes longitude first, the reverse of the order used everywhere else here.
    return tzfpy.get_tz(longitude, latitude)


def _zone_from_name(name: str | None) -> tzinfo | None:
    """Resolve an IANA zone name, or None if it is absent or unknown to the system."""
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


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
            return int(value.value)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            return int(value)
        return int(value)

    def get_float(self, fs_type: str, feature_name: str) -> float | None:
        """Coordinates, which reach the stack as a NumericValue when declared in JLPTEI."""
        value = self.get(fs_type, feature_name)
        if value is None:
            return None
        if isinstance(value, NumericValue):
            return float(value.value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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

    def timezone(self) -> tzinfo:
        """The zone in which ``opensiddur:time`` is to be read.

        An explicitly declared ``timezone`` wins; otherwise the zone is looked up from the
        coordinates, so a document that gives only latitude and longitude still gets local wall
        clock time. UTC is the last resort, for a document with no location at all.

        The lookup lives here rather than only in the derivation graph because the compute
        functions are also called directly, without a settings stack behind them.
        """
        name = self.get(FS_LOCATION, "timezone")
        if isinstance(name, str) and name:
            zone = _zone_from_name(name)
            if zone is not None:
                return zone
        lat = self.get_float(FS_LOCATION, "latitude")
        lon = self.get_float(FS_LOCATION, "longitude")
        if lat is not None and lon is not None:
            zone = _zone_from_name(_timezone_name_at(lat, lon))
            if zone is not None:
                return zone
        return timezone.utc

    def location(self) -> hdate.Location | None:
        lat = self.get_float(FS_LOCATION, "latitude")
        lon = self.get_float(FS_LOCATION, "longitude")
        if lat is None or lon is None:
            return None
        return hdate.Location("", lat, lon, self.timezone(), 0)

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


def _effective_gregorian_date(snapshot: SettingSnapshot) -> date | None:
    """The civil date whose Hebrew equivalent is current, accounting for nightfall.

    The Hebrew day begins in the evening, so from nightfall onward the current Hebrew date is
    that of the *following* civil day. Everything derived from the Hebrew calendar — the date
    itself, the day of the week, the holiday — must be computed from this date rather than the
    civil one, or an evening service is dated to the day that has just ended. The seder is the
    plain case: it begins after nightfall on 14 Nisan, and belongs to 15 Nisan.

    The boundary is tzet hakochavim rather than sunset. Between sunset and nightfall it is
    doubtful which day it is; that window is reported separately as ``bayn-hashmashot`` and is
    left on the day that is ending rather than being silently rolled forward.

    Rolling requires both a location and a time of day, since neither nightfall nor "is it yet
    evening" is otherwise knowable. Without them the civil date is returned unchanged, so
    callers that supply only a date behave exactly as before.
    """
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    loc = snapshot.location()
    tod = snapshot.time_of_day()
    if loc is None or tod is None:
        return gdate
    nightfall = hdate.Zmanim(gdate, location=loc).tset_hakohavim.local
    return gdate + timedelta(days=1) if _datetime_from_snapshot(snapshot) >= nightfall else gdate


def _hebrew_from_snapshot(snapshot: SettingSnapshot) -> pyluach_dates.HebrewDate | None:
    gdate = snapshot.gregorian_date()
    if gdate is not None and snapshot.location() is not None:
        return _pyluach_from_gregorian(_effective_gregorian_date(snapshot)).to_heb()
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
    """The author-supplied moment, as an instant.

    ``opensiddur:time`` is a wall clock reading at ``opensiddur:location``, so it is the zone of
    that location that turns it into an instant comparable with the zmanim. This is the only
    place that conversion happens; combining with a ``ZoneInfo`` resolves the offset for the
    date in question, so a date on either side of a daylight saving transition is handled.
    """
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    tod = snapshot.time_of_day()
    if tod is None:
        tod = time(12, 0)
    return datetime.combine(gdate, tod, tzinfo=snapshot.timezone())


def compute_hebrew_date(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None or snapshot.location() is None:
        return None
    heb = _pyluach_from_gregorian(_effective_gregorian_date(snapshot)).to_heb()
    # Whether the year holds a thirteenth month. The liturgy asks for it: a leap year
    # takes a thirteenth petition in the blessing of the new month, to match the thirteen
    # months. This is the Hebrew leap year, not the Gregorian one that decides when the
    # diaspora begins asking for rain -- the two are unrelated and both are needed.
    return {"year": heb.year, "month": heb.month, "day": heb.day,
            "leap-year": hebrewcal.Year(heb.year).leap}


def compute_hebrew_time(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    loc = snapshot.location()
    aware_dt = _datetime_from_snapshot(snapshot)
    if gdate is None or loc is None or aware_dt is None:
        return None
    z = hdate.Zmanim(gdate, location=loc)
    sunrise = z.netz_hachama.local
    sunset = z.shkia.local
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
    lat = snapshot.get_float(FS_LOCATION, "latitude")
    lon = snapshot.get_float(FS_LOCATION, "longitude")
    if lat is None or lon is None:
        return None
    is_israel = (
        _ISRAEL_LAT[0] <= lat <= _ISRAEL_LAT[1]
        and _ISRAEL_LON[0] <= lon <= _ISRAEL_LON[1]
    )
    return {"is-israel": is_israel}


def compute_location(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    """Derive the time zone from the coordinates.

    Only the zone is derived; latitude and longitude are the author's to state. Deriving it
    means a document that gives coordinates alone still reads ``opensiddur:time`` as local wall
    clock time, and an author who declares ``timezone`` explicitly overrides this by the usual
    explicit-beats-derived rule.
    """
    lat = snapshot.get_float(FS_LOCATION, "latitude")
    lon = snapshot.get_float(FS_LOCATION, "longitude")
    if lat is None or lon is None:
        return None
    name = _timezone_name_at(lat, lon)
    if name is None:
        return None
    return {"timezone": name}


def compute_day_of_week(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    # secular-day stays on the civil weekday while hebrew-day follows the Hebrew date, which
    # has already rolled over at sunset. The divergence between the two is what identifies
    # Saturday night: civil Saturday, Hebrew Sunday. See motzaei-shabbat below.
    result: dict[str, Any] = {"secular-day": _jlptei_weekday(gdate.weekday())}
    loc = snapshot.location()
    dt = _datetime_from_snapshot(snapshot)
    heb = _hebrew_from_snapshot(snapshot)
    if heb is not None:
        # pyluach numbers weekdays Sunday=1..Saturday=7 already, which is the JLPTEI
        # numbering; _jlptei_weekday is for Python's Monday=0 dates and must not be applied.
        hebrew_day = pyluach_dates.HebrewDate(heb.year, heb.month, heb.day).weekday()
        bayn = False
        if loc is not None and dt is not None and snapshot.time_of_day() is not None:
            z = hdate.Zmanim(gdate, location=loc)
            bayn = z.shkia.local < dt < z.tset_hakohavim.local
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
    gdate = _effective_gregorian_date(snapshot)
    heb = _hebrew_from_snapshot(snapshot)
    if gdate is None or heb is None:
        return None
    diaspora = snapshot.is_diaspora()
    hi = hdate.HDateInfo(gdate, diaspora=diaspora)
    return _map_hdate_holidays(hi, heb)


#: Festivals every one of whose days is yom tov.
#:
#: Pesah and Sukkot are deliberately absent: their middle days are chol hamoed, so knowing
#: a day is not yom tov says nothing about whether Pesah is running -- and the day number
#: cannot settle it either, since the second of Pesah is yom tov in the diaspora and chol
#: hamoed in Israel.
ALWAYS_YOM_TOV = ("shavuot", "rosh-hashana", "yom-kippur", "shmini-atzeret")


def compute_holiday_from_aggregate(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    """What a day being *not* yom tov says about which festivals it can be.

    The other derivations here run forward from a date. This one runs the other way, for a
    volume that says what kind of day it is without saying which day: a weekday siddur
    declares ``yom-tov`` false, and it follows that the day is not Rosh Hashanah, not Yom
    Kippur, not Shavuot and not Shemini Atzeret -- every day of each of those being yom
    tov. Without this the festivals stay undefined, and undefined *keeps* the text they
    govern, so a weekday Amidah still carried the Days of Awe Kedushah.

    Only from false. Yom tov being true does not say which festival it is.

    Contributes nothing by returning an empty mapping rather than ``None``: ``None`` means
    *this derivation cannot run*, and clears every derived value the feature structure
    already has -- which here would throw away the festivals the date itself derived.
    """
    if snapshot.get_bool(FS_HOLIDAY_AGG, "yom-tov") is not False:
        return {}
    return dict.fromkeys(ALWAYS_YOM_TOV, 0)


def compute_holiday_aggregate(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    holidays = compute_holiday(snapshot)
    dow = compute_day_of_week(snapshot)
    heb = _hebrew_from_snapshot(snapshot)
    if holidays is None or dow is None:
        return None
    # The Hebrew day is authoritative: it has rolled over at sunset, so Friday evening is
    # already Shabbat and Saturday evening is no longer. Where no rollover is possible (no
    # location or no time) hebrew-day equals secular-day, so this is unchanged for callers
    # that supply a bare date.
    is_shabbat = dow.get("hebrew-day") == 7
    # Saturday night: the civil day is still Saturday but the Hebrew day has moved on. This
    # is when havdalah is said — in the haggadah, the yaknehaz paragraph of the kiddush.
    motzaei_shabbat = dow.get("secular-day") == 7 and dow.get("hebrew-day") != 7
    # A festival *day*, meaning one on which work is forbidden -- not the whole festival
    # period. Chol hamoed is not yom tov, and cannot be told from the day number alone:
    # the second of Pesah is yom tov in the diaspora and chol hamoed in Israel, and both
    # are day 2. hdate knows which, having been given the diaspora setting already.
    gdate = _effective_gregorian_date(snapshot)
    yom_tov = gdate is not None and hdate.HDateInfo(
        gdate, diaspora=snapshot.is_diaspora()).is_yom_tov
    chol_hamoed = holidays.get("pesah", 0) in (3, 4, 5, 6) or holidays.get("sukkot", 0) in (3, 4, 5, 6)
    regalim = holidays.get("pesah", 0) > 0 or holidays.get("shavuot", 0) > 0 or holidays.get("sukkot", 0) > 0
    aseret = (
        heb is not None
        and heb.month == 7
        and 1 <= heb.day <= 10
    )
    return {
        "shabbat": is_shabbat,
        "motzaei-shabbat": motzaei_shabbat,
        "yom-tov": yom_tov,
        "chol-hamoed": chol_hamoed,
        "regalim": regalim,
        "hoshana-rabba": holidays.get("sukkot", 0) == 7,
        "high-holidays": holidays.get("rosh-hashana", 0) > 0 or holidays.get("yom-kippur", 0) > 0,
        "aseret-ymei-tshuva": aseret,
        "minor-fast": any(holidays.get(k, 0) > 0 for k in ("tzom-gedalia", "asara-btevet", "taanit-esther", "tisha-bav")),
        "eruv-tavshilin": _needs_eruv_tavshilin(snapshot),
        "day-before-holiday": False,
        "day-after-holiday": False,
        **_seasons(snapshot, heb),
    }


def _seasons(snapshot: SettingSnapshot, heb: pyluach_dates.HebrewDate | None
             ) -> dict[str, Any]:
    """The two rain seasons, which are not the same season.

    ``geshem`` is when מַשִּׁיב הָרוּחַ וּמוֹרִיד הַגֶּשֶׁם is said in the second berakhah
    of the Amidah: from Shmini Atzeret to the first day of Pesach, the same everywhere.

    ``tal-umatar`` is when וְתֵן טַל וּמָטָר לִבְרָכָה is asked for in the ninth: from
    7 Marcheshvan **in Israel**, but in the diaspora only from 4 December — 5 December in
    the year before a Gregorian leap year — because the petition follows the agricultural
    year of the place asking. Both end at Pesach.

    A feature is **left out** rather than guessed where its inputs are missing: an omitted
    feature evaluates as undefined, which keeps the text it governs and leaves the marker
    in the output for a later stage. Guessing would silently print the wrong season.
    """
    if heb is None:
        return {}
    pesach = pyluach_dates.HebrewDate(heb.year, 1, 15)
    # Within one Hebrew year the months run Tishrei first and Nisan last, so Shmini Atzeret
    # to Pesach is one unbroken stretch rather than a wrap around the new year.
    found: dict[str, Any] = {
        "geshem": pyluach_dates.HebrewDate(heb.year, 7, 22) <= heb <= pesach,
    }
    in_israel = snapshot.get_bool(FS_ISRAEL, "is-israel")
    if in_israel is None:
        computed = compute_israel(snapshot)
        in_israel = computed.get("is-israel") if computed else None
    if in_israel is None:
        return found
    if in_israel:
        found["tal-umatar"] = pyluach_dates.HebrewDate(heb.year, 8, 7) <= heb <= pesach
        return found
    gregorian = _effective_gregorian_date(snapshot)
    if gregorian is None or heb > pesach:
        found["tal-umatar"] = False if gregorian is not None else None
        return {k: v for k, v in found.items() if v is not None}
    if gregorian.month == 12:
        found["tal-umatar"] = gregorian.day >= _tal_umatar_december_day(gregorian.year)
    else:
        # Before Pesach and not December: January to Pesach is still the winter that
        # began last December; October and November are not, since the diaspora waits.
        found["tal-umatar"] = gregorian.month <= 4
    return found


def _tal_umatar_december_day(year: int) -> int:
    """The December day the diaspora begins asking for rain.

    The fourth, except in the year before a Gregorian leap year, when the extra day the
    coming February will hold has not yet been inserted and the reckoning slips to the
    fifth. This is the one place the liturgical year consults the civil calendar.
    """
    return 5 if calendar.isleap(year + 1) else 4


def _needs_eruv_tavshilin(snapshot: SettingSnapshot) -> bool:
    """Whether an eruv tavshilin is called for in the coming days.

    Cooking on a festival is permitted only for that festival, so when one runs straight into
    Shabbat an eruv tavshilin must be prepared beforehand to allow cooking for Shabbat. That is
    the case exactly when a yom tov within the next few days is immediately followed by
    Shabbat — for Pesah, when the first days fall on Thursday and Friday.

    True from the eve of the festival onward rather than only on the day the eruv is made, so
    that a haggadah compiled for the seder still carries the passage.
    """
    gdate = _effective_gregorian_date(snapshot)
    if gdate is None:
        return False
    diaspora = snapshot.is_diaspora()
    for offset in range(0, 4):
        day = gdate + timedelta(days=offset)
        if _jlptei_weekday(day.weekday()) != 6:  # a yom tov that is itself Friday
            continue
        if not hdate.HDateInfo(day, diaspora=diaspora).is_yom_tov:
            continue
        return True
    return False


def _parsha_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace(",", "")


def _triennial_cycle_patterns(hebrew_year: int, israel: bool) -> dict[str, str]:
    """For each pair, whether it was read [T]ogether or [S]eparately in each year of the cycle.

    The three characters run from the first year of the cycle, so ``"TSS"`` means the pair was
    read together in the first year and apart in the other two. The triennial division of a
    parshah that is sometimes doubled depends on this pattern rather than on the cycle year
    alone, which is why it is derived here; the humash conditions on it.

    The Hebrew year is enough to identify a pair's week, even though the reading year turns
    over at Simhat Torah rather than at Rosh Hashanah: every one of these pairs is read
    between Adar and Av.
    """
    start = hebrew_year - ((hebrew_year - _TRIENNIAL_EPOCH_YEAR) % 3)
    combined_per_year = []
    for year in (start, start + 1, start + 2):
        table = parshios.parshatable(year, israel=israel)
        combined_per_year.append({
            reading[0] for reading in table.values()
            if reading is not None and len(reading) > 1
        })
    return {
        pair: "".join("T" if index in combined else "S" for combined in combined_per_year)
        for pair, index in TRIENNIAL_PAIRS
    }


def _adar_of_purim(year: int) -> int:
    """The Adar in which Purim falls: Adar II in a leap year, Adar otherwise."""
    return _ADAR_II if hebrewcal.Year(year).leap else _ADAR


def _containing_shabbat(heb: pyluach_dates.HebrewDate) -> pyluach_dates.HebrewDate:
    """The Shabbat of `heb`'s week — itself if it is Shabbat, else the one that follows.

    The Torah reading belongs to a week, not to a day: pyluach reckons the parshah the same
    way (Sunday through Shabbat), so a document compiled on a Thursday selects the reading of
    the coming Shabbat rather than none at all.
    """
    # pyluach weekdays run Sunday = 1 through Shabbat = 7.
    return heb.add(days=7 - heb.weekday())


def _shabbat_on_or_before(heb: pyluach_dates.HebrewDate) -> pyluach_dates.HebrewDate:
    """The latest Shabbat that is not after `heb`."""
    return heb.subtract(days=heb.weekday() % 7)


def _triennial_year(heb: pyluach_dates.HebrewDate) -> int:
    """Which of the three years of the modern triennial cycle `heb` falls in (1, 2 or 3).

    The reading year turns over at Simhat Torah, not at Rosh Hashanah, so the Shabbatot of
    early Tishrei — Shabbat Shuva above all, which reads an ordinary parshah — still belong to
    the outgoing cycle year.

    Simhat Torah is 22 Tishrei in Israel and 23 in the diaspora, but a single turnover on the
    22nd serves both. The two reckonings can disagree only on 22 Tishrei itself, and lo ADU
    rosh forces that day to share Rosh Hashanah's weekday while barring the 23rd from ever
    being Shabbat. So no Shabbat carrying a weekly reading falls in the disputed window: over
    5756-5855 the reckonings differ on 29 Shabbatot, every one of them 22 Tishrei, where the
    festival reading is selected and no parshah is read.
    """
    year = heb.year
    if heb.month == _TISHREI and heb.day < _SIMHAT_TORAH_DAY:
        year -= 1
    return ((year - _TRIENNIAL_EPOCH_YEAR) % 3) + 1


def compute_torah_reading(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    if gdate is None:
        return None
    g = _pyluach_from_gregorian(gdate)
    diaspora = parshios.getparsha_string(g, israel=False) or ""
    israel = parshios.getparsha_string(g, israel=True) or ""

    shabbat = _containing_shabbat(g.to_heb())
    year = shabbat.year
    adar = _adar_of_purim(year)
    rosh_hodesh_adar = pyluach_dates.HebrewDate(year, adar, 1)
    rosh_hodesh_nisan = pyluach_dates.HebrewDate(year, _NISAN, 1)
    hahodesh = _shabbat_on_or_before(rosh_hodesh_nisan)
    tisha_bav = _shabbat_on_or_before(pyluach_dates.HebrewDate(year, _AV, 9))
    tomorrow = shabbat.add(days=1)

    result: dict[str, Any] = {
        "diaspora-parsha": _parsha_slug(diaspora),
        "israel-parsha": _parsha_slug(israel),
        "triennial-year": _triennial_year(shabbat),
        # Between Rosh Hashanah and Yom Kippur. Anchoring on 9 Tishrei rather than on a range
        # keeps the case where Erev Yom Kippur is itself Shabbat.
        "shabbat-shuva": shabbat == _shabbat_on_or_before(
            pyluach_dates.HebrewDate(year, _TISHREI, 9)
        ),
        # Shirat ha-Yam is in Beshalach, so this one really is defined by the parshah.
        "shabbat-shira": _parsha_slug(diaspora) == "beshalach",
        # The four parshiyot. Each is the Shabbat on or before a fixed date, except Parah,
        # which is simply the Shabbat before ha-Hodesh.
        "shabbat-shkalim": shabbat == _shabbat_on_or_before(rosh_hodesh_adar),
        "shabbat-zachor": shabbat == _shabbat_on_or_before(
            pyluach_dates.HebrewDate(year, adar, 13)
        ),
        "shabbat-parah": shabbat == hahodesh.subtract(days=7),
        "shabbat-hahodesh": shabbat == hahodesh,
        # Erev Pesah falling on Shabbat is itself Shabbat ha-Gadol.
        "shabbat-hagadol": shabbat == _shabbat_on_or_before(
            pyluach_dates.HebrewDate(year, _NISAN, 14)
        ),
        # When 9 Av is Shabbat the fast is deferred, but the haftarah of Hazon is read that day.
        "shabbat-hazon": shabbat == tisha_bav,
        "shabbat-nahamu": shabbat == tisha_bav.add(days=7),
        # Rosh Hodesh and Mahar Hodesh each carry their own haftarah.
        "shabbat-rosh-hodesh": shabbat.day in (1, 30),
        "shabbat-mahar-hodesh": tomorrow.day in (1, 30),
    }
    patterns = _triennial_cycle_patterns(
        year, israel=not snapshot.is_diaspora()
    )
    for pair, pattern in patterns.items():
        result[f"triennial-pattern-{pair}"] = pattern
    for feature in TORAH_FEATURES:
        if feature not in result:
            result[feature] = False
    return result


def compute_service_time(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    gdate = snapshot.gregorian_date()
    loc = snapshot.location()
    aware_dt = _datetime_from_snapshot(snapshot)
    if gdate is None or loc is None or aware_dt is None or snapshot.time_of_day() is None:
        return None
    z = hdate.Zmanim(gdate, location=loc)
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


def compute_reading_cycle(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    """Turn a triennial volume's date into the one cycle year it reads.

    This is where the volume's choice of cycle and its date meet: the cycle year of the date
    sits on ``opensiddur:torah-reading`` whatever cycle the volume follows, so it cannot select
    a reading by itself. A volume that reads annually is left alone however its date falls.

    Only the volume compiled for a particular Shabbat is derived. One that turns the year
    features on itself — a volume for a whole cycle, which turns on all three — says so
    explicitly and is not overridden, since a declared value beats a derived one.
    """
    triennial = snapshot.get_bool(FS_READING_CYCLE, "triennial") is True
    year = snapshot.get_int(FS_TORAH, "triennial-year") if triennial else None
    return {
        "annual": year is None,
        **{f"triennial-year-{n}": n == year for n in TRIENNIAL_YEARS},
    }


def compute_recitation(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    """What the service implies about which recitations it has.

    Ma'ariv has no repetition, so the Ma'ariv Amidah is always the silent one and nothing
    in it is conditioned on being read aloud. Nothing is derived in the other direction:
    the services that *do* have a repetition have a silent recitation as well, so knowing
    the service says nothing about which of the two is in hand.

    Contributes an empty mapping rather than ``None`` where it has nothing to say, ``None``
    meaning *this derivation cannot run* and clearing every derived value the structure
    already holds.
    """
    if snapshot.get_bool(FS_SERVICE_TIME, "maariv") is not True:
        return {}
    return {"silent": True, "repetition": False}


def compute_quorum(snapshot: SettingSnapshot) -> dict[str, Any] | None:
    """Derive what a quorum implies about the smaller quorums it contains.

    Ten adults are also three, so a minyan entails a zimmun. Nothing is derived in the other
    direction, and nothing is derived when minyan is unset: quorum features must stay
    undefined by default, so that a haggadah compiled without knowing who will be present
    keeps both the passage and the rubric explaining when to say it.
    """
    minyan = snapshot.get_bool(FS_QUORUM, "minyan")
    if minyan is not True:
        return None
    return {"zimmun": True}
