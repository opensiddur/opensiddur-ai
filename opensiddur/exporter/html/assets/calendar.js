/*
 * The calendar for an Open Siddur electronic book, on the reader's device.
 *
 * A port of the compiler's calendar derivations (opensiddur/exporter/calendar/compute.py and
 * the three modules beside it), of the derivation graph that orders them
 * (derivation_graph.py) and of the settings stack they run on (derived_settings.py). Given the
 * same explicit settings -- a date, a time, a place -- it derives what a compile derives, and
 * the agreement tests hold the two to exactly the same values.
 *
 * Values are in the JSON forms of condition_eval.value_to_json: null is undefined, {num, max}
 * a declared number, {twilight: [ending, starting]} a value that differs across bein
 * hashmashot. A feature that is not set at all is JavaScript's undefined.
 *
 * Dates are Julian day numbers throughout. Moments are wall-clock times at the place, in
 * microseconds from the epoch as though the clock read UTC (see Snapshot.moment).
 *
 * The Hebrew calendar arithmetic and the table of weekly readings follow pyluach
 * (https://github.com/simlist/pyluach), which the compiler uses:
 *
 *   Copyright (c) 2014 Meir S. List
 *
 *   Permission is hereby granted, free of charge, to any person obtaining a copy of this
 *   software and associated documentation files (the "Software"), to deal in the Software
 *   without restriction, including without limitation the rights to use, copy, modify, merge,
 *   publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
 *   to whom the Software is furnished to do so, subject to the following conditions:
 *
 *   The above copyright notice and this permission notice shall be included in all copies or
 *   substantial portions of the Software.
 *
 *   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 *   INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
 *   PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
 *   FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 *   OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 *   DEALINGS IN THE SOFTWARE.
 *
 * The times of day are NOAA's low-accuracy solar equations
 * (https://gml.noaa.gov/grad/solcalc/solareqns.PDF), with the definitions of the zmanim that
 * the compiler's calendar library (hdate) uses. The holidays are the calendar's facts, restated
 * here, giving the same days as that library.
 *
 * No DOM access.
 */
(function (root) {
  "use strict";

  var FS_GREGORIAN = "opensiddur:gregorian-date";
  var FS_TIME = "opensiddur:time";
  var FS_HEBREW_DATE = "opensiddur:hebrew-date";
  var FS_HEBREW_TIME = "opensiddur:hebrew-time";
  var FS_LOCATION = "opensiddur:location";
  var FS_ISRAEL = "opensiddur:israel";
  var FS_DAY_OF_WEEK = "opensiddur:day-of-week";
  var FS_HOLIDAY = "opensiddur:holiday";
  var FS_HOLIDAY_AGG = "opensiddur:holiday-aggregate";
  var FS_TORAH = "opensiddur:torah-reading";
  var FS_READING_CYCLE = "opensiddur:reading-cycle";
  var FS_SERVICE_TIME = "opensiddur:service-time";
  var FS_QUORUM = "opensiddur:quorum";
  var FS_RECITATION = "opensiddur:recitation";
  var FS_PURIM_OBSERVANCE = "opensiddur:purim-observance";
  var FS_HALLEL = "opensiddur:hallel";
  var FS_MOTZAEI_SHABBAT = "opensiddur:motzaei-shabbat";
  var FS_AVOT = "opensiddur:pirkei-avot";

  function has(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
  }

  function isObject(value) {
    return value !== null && typeof value === "object";
  }

  function isTwilight(value) {
    return isObject(value) && has(value, "twilight");
  }

  // Python's == on the values a derivation gives: True == 1, and undefined (null) equals
  // only itself.
  function pyEqual(a, b) {
    if (a === b) return true;
    if (a === null || b === null || a === undefined || b === undefined) return false;
    var numeric = function (v) { return typeof v === "number" || typeof v === "boolean"; };
    if (numeric(a) && numeric(b)) return Number(a) === Number(b);
    if (isObject(a) && isObject(b)) return JSON.stringify(a) === JSON.stringify(b);
    return false;
  }

  // ── Gregorian dates (pyluach GregorianDate, Python's date) ───────────────

  function gregorianLeap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  }

  var GREGORIAN_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  function gregorianMonthLength(year, month) {
    return month === 2 && gregorianLeap(year) ? 29 : GREGORIAN_MONTH_DAYS[month - 1];
  }

  // Python's date(year, month, day) accepts it.
  function validGregorian(year, month, day) {
    return year >= 1 && year <= 9999 && month >= 1 && month <= 12 &&
      day >= 1 && day <= gregorianMonthLength(year, month);
  }

  // pyluach GregorianDate.jd, plus the half day.
  function gregorianToJdn(year, month, day) {
    if (month < 3) {
      year -= 1;
      month += 12;
    }
    month += 1;
    var a = Math.floor(year / 100);
    var b = 2 - a + Math.floor(a / 4);
    return Math.trunc(365.25 * year) + Math.trunc(30.6001 * month) + b + day + 1720995;
  }

  // pyluach JulianDay.to_greg (Fliegel-Van Flandern).
  function jdnToGregorian(jdn) {
    var L = jdn + 68569;
    var n = Math.floor(4 * L / 146097);
    L = L - Math.floor((146097 * n + 3) / 4);
    var i = Math.floor(4000 * (L + 1) / 1461001);
    L = L - Math.floor(1461 * i / 4) + 31;
    var j = Math.floor(80 * L / 2447);
    var day = L - Math.floor(2447 * j / 80);
    L = Math.floor(j / 11);
    var month = j + 2 - 12 * L;
    var year = 100 * (n - 49) + i + L;
    return { year: year, month: month, day: day };
  }

  // Sunday = 1 through Shabbat = 7, for any date.
  function weekday(jdn) {
    return (jdn + 1) % 7 + 1;
  }

  // ── The Hebrew calendar (pyluach utils) ──────────────────────────────────
  //
  // Months as pyluach numbers them: 1 = Nisan through 12 = Adar, with Adar I as 12 and Adar II
  // as 13 in a leap year. The year begins in Tishrei (7).

  var NISAN = 1, IYAR = 2, SIVAN = 3, TAMMUZ = 4, AV = 5, TISHREI = 7, MARCHESHVAN = 8,
      KISLEV = 9, TEVET = 10, SHEVAT = 11, ADAR = 12, ADAR_II = 13;

  function hebrewLeap(year) {
    return ((7 * year) + 1) % 19 < 7;
  }

  var elapsedCache = {};

  function elapsedDays(year) {
    if (has(elapsedCache, year)) return elapsedCache[year];
    var months = Math.floor((235 * year - 234) / 19);
    var parts = 204 + 793 * (months % 1080);
    var hours = 5 + 12 * months + 793 * Math.floor(months / 1080) + Math.floor(parts / 1080);
    var conjunctionDay = 1 + 29 * months + Math.floor(hours / 24);
    var conjunctionParts = 1080 * (hours % 24) + parts % 1080;
    var day = conjunctionDay;
    if (conjunctionParts >= 19440 ||
        (conjunctionDay % 7 === 2 && conjunctionParts >= 9924 && !hebrewLeap(year)) ||
        (conjunctionDay % 7 === 1 && conjunctionParts >= 16789 && hebrewLeap(year - 1))) {
      day = conjunctionDay + 1;
    }
    if (day % 7 === 0 || day % 7 === 3 || day % 7 === 5) day += 1;
    elapsedCache[year] = day;
    return day;
  }

  function daysInYear(year) {
    return elapsedDays(year + 1) - elapsedDays(year);
  }

  function hebrewMonthLength(year, month) {
    switch (month) {
      case 1: case 3: case 5: case 7: case 11: return 30;
      case 2: case 4: case 6: case 10: case 13: return 29;
      case 12: return hebrewLeap(year) ? 30 : 29;
      case 8: return daysInYear(year) % 10 === 5 ? 30 : 29;  // a long Marcheshvan
      case 9: return daysInYear(year) % 10 === 3 ? 29 : 30;  // a short Kislev
    }
    throw new RangeError("Invalid month " + month);
  }

  function shortKislev(year) {
    return daysInYear(year) % 10 === 3;
  }

  function monthsOfYear(year) {
    return hebrewLeap(year) ? [7, 8, 9, 10, 11, 12, 13, 1, 2, 3, 4, 5, 6]
                            : [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6];
  }

  function validHebrew(year, month, day) {
    if (year < 1 || month < 1 || month > 13) return false;
    if (month === 13 && !hebrewLeap(year)) return false;
    return day >= 1 && day <= hebrewMonthLength(year, month);
  }

  // A Hebrew date: {year, month, day, jdn}. Throws for one that does not exist, as pyluach's
  // HebrewDate raises ValueError.
  function hebrew(year, month, day) {
    if (!validHebrew(year, month, day)) {
      throw new RangeError("No such Hebrew date " + year + "-" + month + "-" + day);
    }
    var jdn = elapsedDays(year) + 347997 + (day - 1);
    var months = monthsOfYear(year);
    for (var i = 0; months[i] !== month; i++) jdn += hebrewMonthLength(year, months[i]);
    return { year: year, month: month, day: day, jdn: jdn };
  }

  // pyluach JulianDay.to_heb.
  function hebrewFromJdn(jdn) {
    var days = jdn - 347997;
    var year = Math.floor(days / 365) + 2;
    var first = elapsedDays(year);
    while (first > days) {
      year -= 1;
      first = elapsedDays(year);
    }
    var remaining = days - first;
    var months = monthsOfYear(year);
    for (var i = 0; i < months.length; i++) {
      var length = hebrewMonthLength(year, months[i]);
      if (remaining < length) {
        return { year: year, month: months[i], day: remaining + 1, jdn: jdn };
      }
      remaining -= length;
    }
    throw new RangeError("Date out of range");
  }

  function hebrewOrNull(year, month, day) {
    return validHebrew(year, month, day) ? hebrew(year, month, day) : null;
  }

  function addDays(heb, days) {
    return hebrewFromJdn(heb.jdn + days);
  }

  // compute._adar_of_purim: Adar II in a leap year, Adar otherwise.
  function adarOfPurim(year) {
    return hebrewLeap(year) ? ADAR_II : ADAR;
  }

  // ── The weekly reading (pyluach parshios) ────────────────────────────────

  var PARSHIOS = [
    "Bereishis", "Noach", "Lech Lecha", "Vayeira", "Chayei Sarah", "Toldos",
    "Vayeitzei", "Vayishlach", "Vayeishev", "Mikeitz", "Vayigash", "Vayechi",
    "Shemos", "Va'eira", "Bo", "Beshalach", "Yisro", "Mishpatim", "Terumah",
    "Tetzaveh", "Ki Sisa", "Vayakhel", "Pekudei", "Vayikra", "Tzav", "Shemini",
    "Tazria", "Metzora", "Acharei Mos", "Kedoshim", "Emor", "Behar",
    "Bechukosai", "Bamidbar", "Nasso", "Beha'aloscha", "Shelach", "Korach",
    "Chukas", "Balak", "Pinchas", "Mattos", "Masei", "Devarim", "Va'eschanan",
    "Eikev", "Re'eh", "Shoftim", "Ki Seitzei", "Ki Savo", "Nitzavim",
    "Vayeilech", "Haazinu", "Vezos Haberachah"
  ];

  var VAYAKHEL = 21, TAZRIA = 26, ACHAREI_MOS = 28, BEHAR = 31, CHUKAS = 38, MATTOS = 41,
      NITZAVIM = 50;

  function parshaless(heb, israel) {
    var m = heb.month, d = heb.day;
    if (israel && ((m === 7 && d === 23) || (m === 1 && d === 22) || (m === 3 && d === 7))) {
      return false;
    }
    if (m === 7 && (d === 1 || d === 2 || d === 10 || (d >= 15 && d <= 23))) return true;
    if (m === 1 && d >= 15 && d <= 22) return true;
    if (m === 3 && (d === 6 || d === 7)) return true;
    return false;
  }

  var tableCache = {};

  // pyluach parshios._gentable: each Shabbat of the year, by day number, to the readings of
  // that Shabbat (one or two parsha numbers), or null where a festival displaces them.
  function parshaTable(year, israel) {
    var key = year + (israel ? "i" : "d");
    if (has(tableCache, key)) return tableCache[key];
    var list = [51, 52];
    for (var p = 0; p < 52; p++) list.push(p);
    var table = {};
    var leap = hebrewLeap(year);
    var pesachDay = weekday(hebrew(year, NISAN, 15).jdn);
    var roshHashana = hebrew(year, TISHREI, 1);
    var shabbos = roshHashana.jdn + (7 - weekday(roshHashana.jdn));
    if (weekday(roshHashana.jdn) > 4) list.shift();
    var erevPesach = hebrew(year, NISAN, 14).jdn;
    var tishaBav = hebrew(year, AV, 9).jdn;
    var nextNewYearLate = weekday(hebrew(year + 1, TISHREI, 1).jdn) > 4;
    for (var date = hebrewFromJdn(shabbos); date.year === year;
         shabbos += 7, date = hebrewFromJdn(shabbos)) {
      if (parshaless(date, israel)) {
        table[shabbos] = null;
        continue;
      }
      var parsha = list.shift();
      var reading = [parsha];
      if ((parsha === VAYAKHEL && Math.floor(Math.abs(erevPesach - shabbos) / 7) < 3) ||
          ((parsha === TAZRIA || parsha === ACHAREI_MOS) && !leap) ||
          (parsha === BEHAR && !leap && (!israel || pesachDay !== 7)) ||
          (parsha === CHUKAS && !israel && pesachDay === 5) ||
          (parsha === MATTOS && Math.floor(Math.abs(tishaBav - shabbos) / 7) < 2) ||
          (parsha === NITZAVIM && nextNewYearLate)) {
        reading.push(list.shift());
      }
      table[shabbos] = reading;
    }
    tableCache[key] = table;
    return table;
  }

  // pyluach parshios.getparsha_string: the reading of the Shabbat on or after the date, or
  // null where there is none.
  function parshaName(jdn, israel) {
    var shabbos = jdn + (7 - weekday(jdn));
    var reading = parshaTable(hebrewFromJdn(shabbos).year, israel)[shabbos];
    if (!reading) return null;
    return reading.map(function (n) { return PARSHIOS[n]; }).join(", ");
  }

  // compute._parsha_slug.
  function parshaSlug(name) {
    return name.toLowerCase().split(" ").join("-").split(",").join("");
  }

  // ── The calendar's days ──────────────────────────────────────────────────
  //
  // The names the compiler's calendar library gives a day, those of them it reads, and
  // whether the day is a yom tov. In Israel or outside it.

  function day(name, yomTov) {
    return { name: name, yomTov: Boolean(yomTov) };
  }

  function calendarDays(heb, israel) {
    var m = heb.month, d = heb.day, w = weekday(heb.jdn), y = heb.year;
    var found = [];
    var add = function (name, yomTov) { found.push(day(name, yomTov)); };
    if (m === TISHREI) {
      if (d === 1) add("rosh_hashana_i", true);
      if (d === 2) add("rosh_hashana_ii", true);
      if ((d === 3 && w !== 7) || (d === 4 && w === 1)) add("tzom_gedaliah");
      if (d === 10) add("yom_kippur", true);
      if (d === 15) add("sukkot", true);
      if (d === 16) {
        if (israel) add("hol_hamoed_sukkot");
        else add("sukkot_ii", true);
      }
      if (d >= 17 && d <= 20) add("hol_hamoed_sukkot");
      if (d === 21) add("hoshana_raba");
      if (d === 22) {
        add("shmini_atzeret", true);
        if (israel) add("simchat_torah", true);
      }
      if (d === 23 && !israel) add("simchat_torah", true);
    } else if (m === KISLEV) {
      if (d >= 25) add("chanukah");
    } else if (m === TEVET) {
      if (d === 1 || d === 2 || (d === 3 && shortKislev(y))) add("chanukah");
      if (d === 10) add("asara_btevet");
    } else if (m === SHEVAT) {
      if (d === 15) add("tu_bshvat");
    } else if (m === adarOfPurim(y)) {
      if ((d === 11 && w === 5) || (d === 13 && w !== 7)) add("taanit_esther");
      if (d === 14) add("purim");
      if (d === 15) add("shushan_purim");
    } else if (m === NISAN) {
      if (d === 15) add("pesach", true);
      if (d === 16) {
        if (israel) add("hol_hamoed_pesach");
        else add("pesach_ii", true);
      }
      if (d >= 17 && d <= 20) add("hol_hamoed_pesach");
      if (d === 21) add("pesach_vii", true);
      if (d === 22 && !israel) add("pesach_viii", true);
      if (y > 5718 && ((d === 26 && w === 5) || (d === 27 && w !== 1 && w !== 6) ||
                       (d === 28 && w === 2))) {
        add("yom_hashoah");
      }
    } else if (m === IYAR) {
      if (y > 5708) {
        if (((d === 2 || d === 3) && w === 4) ||
            (d === 4 && y < 5764 && w !== 5 && w !== 6) ||
            (d === 4 && y > 5763 && w !== 5 && w !== 6 && w !== 1) ||
            (d === 5 && y > 5763 && w === 2)) {
          add("yom_hazikaron");
        }
        if (((d === 3 || d === 4) && w === 5) ||
            (d === 5 && y < 5764 && w !== 6 && w !== 7) ||
            (d === 5 && y > 5763 && w !== 6 && w !== 7 && w !== 2) ||
            (d === 6 && y > 5763 && w === 3)) {
          add("yom_haatzmaut");
        }
      }
      if (d === 18) add("lag_bomer");
      if (d === 28 && y > 5727) add("yom_yerushalayim");
    } else if (m === SIVAN) {
      if (d === 6) add("shavuot", true);
      if (d === 7 && !israel) add("shavuot_ii", true);
    } else if (m === TAMMUZ) {
      if ((d === 17 && w !== 7) || (d === 18 && w === 1)) add("tzom_tammuz");
    } else if (m === AV) {
      if ((d === 9 && w !== 7) || (d === 10 && w === 1)) add("tisha_bav");
      if (d === 15) add("tu_bav");
    }
    return found;
  }

  function isYomTov(jdn, israel) {
    return calendarDays(hebrewFromJdn(jdn), israel).some(function (h) { return h.yomTov; });
  }

  // The day of the omer, 1 to 49, or 0 outside it.
  function omerDay(heb) {
    var m = heb.month, d = heb.day;
    if ((m === NISAN && d >= 16) || m === IYAR || (m === SIVAN && d <= 5)) {
      return heb.jdn - hebrew(heb.year, NISAN, 16).jdn + 1;
    }
    return 0;
  }

  // ── Times of day ─────────────────────────────────────────────────────────

  // The minutes from midnight UTC at which the sun crosses a zenith angle on a civil date,
  // rising and setting, in whole minutes truncated toward zero. -720 for both where it does
  // not reach the angle that day.
  function sunTimes(jdn, latitude, longitude, degrees) {
    var g = jdnToGregorian(jdn);
    var dayOfYear = jdn - gregorianToJdn(g.year, 1, 1);
    var gamma = 2.0 * Math.PI * ((dayOfYear - 1) / 365.0);
    var eqtime = 229.18 * (
      0.000075 + 0.001868 * Math.cos(gamma) - 0.032077 * Math.sin(gamma) -
      0.014615 * Math.cos(2.0 * gamma) - 0.040849 * Math.sin(2.0 * gamma));
    var decl = 0.006918 - 0.399912 * Math.cos(gamma) + 0.070257 * Math.sin(gamma) -
      0.006758 * Math.cos(2.0 * gamma) + 0.000907 * Math.sin(2.0 * gamma) -
      0.002697 * Math.cos(3.0 * gamma) + 0.00148 * Math.sin(3.0 * gamma);
    var lat = latitude * Math.PI / 180;
    var zenith = degrees * Math.PI / 180;
    var cosine = Math.cos(zenith) / (Math.cos(lat) * Math.cos(decl)) - Math.tan(lat) * Math.tan(decl);
    if (!(cosine >= -1 && cosine <= 1)) return [-720, -720];
    var hourAngle = 720.0 * Math.acos(cosine) / Math.PI;
    return [Math.trunc(720.0 - 4.0 * longitude - hourAngle - eqtime),
            Math.trunc(720.0 - 4.0 * longitude + hourAngle - eqtime)];
  }

  var MICROS_PER_DAY = 86400 * 1e6;
  var UNIX_EPOCH_JDN = 2440588;
  var zmanimCache = {};

  // The zmanim of a civil date at a place, each as a wall-clock time in the place's zone (or
  // in UTC, for none), in microseconds from the epoch.
  function zmanim(jdn, place, zone) {
    var key = jdn + ":" + place.latitude + ":" + place.longitude + ":" + zone;
    if (has(zmanimCache, key)) return zmanimCache[key];
    var rise = sunTimes(jdn, place.latitude, place.longitude, 90.833);
    var sunrise = rise[0], sunset = rise[1];
    var firstLight = sunTimes(jdn, place.latitude, place.longitude, 106.1)[0];
    // A seasonal hour, a twelfth of the daylight.
    var sunHour = Math.floor((sunset - sunrise) / 12);
    var midnight = (jdn - UNIX_EPOCH_JDN) * MICROS_PER_DAY;
    var at = function (minutes) {
      var utc = midnight + Math.round(minutes * 60e6);
      return zone ? utc + zoneOffset(zone, Math.floor(utc / 1000)) * 1000 : utc;
    };
    var times = {
      alot: at(firstLight),
      netz: at(sunrise),
      sofZmanTfilla: at(sunrise + sunHour * 4.0),
      minchaGedola: at(sunrise + 6.5 * sunHour),
      plag: at(sunset - 1.25 * sunHour),
      shkia: at(sunset),
      // Nightfall: eighteen seasonal minutes after sunset.
      tzet: at(sunset + 18.0 * sunHour / 60.0)
    };
    zmanimCache[key] = times;
    return times;
  }

  // ── Time zones ───────────────────────────────────────────────────────────

  var formatters = {};

  function formatter(zone) {
    if (!has(formatters, zone)) {
      formatters[zone] = new Intl.DateTimeFormat("en-US", {
        timeZone: zone, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric",
        hour: "numeric", minute: "numeric", second: "numeric"
      });
    }
    return formatters[zone];
  }

  // The zone's canonical name ("Asia/Jerusalem" for "Israel" or "asia/jerusalem"), or null for
  // one this device does not know.
  function canonicalZone(zone) {
    if (typeof zone !== "string" || !zone) return null;
    try {
      return formatter(zone).resolvedOptions().timeZone;
    } catch (e) {
      return null;
    }
  }

  // The zone's offset from UTC at an instant, in milliseconds.
  function zoneOffset(zone, utcMs) {
    var parts = {};
    formatter(zone).formatToParts(new Date(utcMs)).forEach(function (part) {
      parts[part.type] = part.value;
    });
    var wall = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day),
                        Number(parts.hour) % 24, Number(parts.minute), Number(parts.second));
    return wall - Math.floor(utcMs / 1000) * 1000;
  }

  // ── Reading settings (compute.SettingSnapshot) ───────────────────────────

  // get(fs, feature) gives a value, null for one declared undefined, or undefined when
  // nothing is set. day is 0 or 1 in a view of one of the two days of bein hashmashot.
  function Snapshot(get, day) {
    this.getSetting = get;
    this.day = day === undefined ? null : day;
  }

  Snapshot.prototype.get = function (fsType, feature) {
    return this.getSetting(fsType, feature);
  };

  Snapshot.prototype.onDay = function (day) {
    var self = this;
    return new Snapshot(function (fsType, feature) {
      var value = self.getSetting(fsType, feature);
      return isTwilight(value) ? value.twilight[day] : value;
    }, day);
  };

  // The value, or null when it is unset or undefined.
  Snapshot.prototype.defined = function (fsType, feature) {
    var value = this.get(fsType, feature);
    if (isTwilight(value)) value = value.twilight[0];
    return value === undefined || value === null ? null : value;
  };

  Snapshot.prototype.getInt = function (fsType, feature) {
    var value = this.defined(fsType, feature);
    if (value === null) return null;
    if (isObject(value)) return Math.trunc(value.num);
    if (typeof value === "boolean") return value ? 1 : 0;
    if (typeof value === "number") return Math.trunc(value);
    if (/^\s*[+-]?\d+\s*$/.test(value)) return parseInt(value, 10);
    throw new TypeError("Not an integer: " + value);
  };

  Snapshot.prototype.getFloat = function (fsType, feature) {
    var value = this.defined(fsType, feature);
    if (value === null) return null;
    if (isObject(value)) return Number(value.num);
    if (typeof value === "boolean") return value ? 1 : 0;
    if (typeof value === "number") return value;
    var number = Number(String(value).trim());
    return String(value).trim() === "" || isNaN(number) ? null : number;
  };

  var BOOLEAN_WORDS = { "true": true, "1": true, "false": false, "0": false };

  Snapshot.prototype.getBool = function (fsType, feature) {
    var value = this.defined(fsType, feature);
    if (value === null) return null;
    if (isObject(value)) return value.num !== 0;
    if (typeof value === "string") {
      var word = value.trim().toLowerCase();
      return has(BOOLEAN_WORDS, word) ? BOOLEAN_WORDS[word] : null;
    }
    return Boolean(value);
  };

  // The civil date as a day number, or null.
  Snapshot.prototype.gregorianDate = function () {
    var year = this.getInt(FS_GREGORIAN, "year");
    var month = this.getInt(FS_GREGORIAN, "month");
    var day = this.getInt(FS_GREGORIAN, "day");
    if (year === null || month === null || day === null) return null;
    if (!validGregorian(year, month, day)) return null;
    return gregorianToJdn(year, month, day);
  };

  // The time of day in seconds from midnight, or null.
  Snapshot.prototype.timeOfDay = function () {
    var hour = this.getInt(FS_TIME, "hour");
    var minute = this.getInt(FS_TIME, "minute");
    var second = this.getInt(FS_TIME, "second");
    if (hour === null || minute === null) return null;
    if (second === null) second = 0;
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
      return null;
    }
    return hour * 3600 + minute * 60 + second;
  };

  // The zone the time is read in, or null. The device gives the zone with the place: it does
  // not look a zone up from coordinates, as the compiler can.
  Snapshot.prototype.zone = function () {
    return canonicalZone(this.get(FS_LOCATION, "timezone"));
  };

  // The place, or null. A place without a zone this device knows is no place: its clock cannot
  // be read, and it is better unknown -- every option shown -- than read as UTC.
  Snapshot.prototype.location = function () {
    var latitude = this.getFloat(FS_LOCATION, "latitude");
    var longitude = this.getFloat(FS_LOCATION, "longitude");
    if (latitude === null || longitude === null || this.zone() === null) return null;
    return { latitude: latitude, longitude: longitude };
  };

  // compute._ISRAEL_ZONES: Israel is decided by its time zones, by their canonical names. The
  // compiler looks the zone up from the coordinates; the device takes the zone it is given with
  // them, so the two agree when that zone is the one the coordinates are in.
  var ISRAEL_ZONES = ["Asia/Jerusalem", "Asia/Hebron", "Asia/Gaza"];

  function isIsraelZone(zone) {
    return ISRAEL_ZONES.some(function (name) { return canonicalZone(name) === zone; });
  }

  Snapshot.prototype.inIsrael = function () {
    var declared = this.get(FS_ISRAEL, "is-israel");
    if (declared === null) return null;
    if (declared !== undefined) return this.getBool(FS_ISRAEL, "is-israel");
    if (this.location() === null) return null;
    return isIsraelZone(this.zone());
  };

  // The declared moment, at noon when no time is given: a wall-clock time at the place, in
  // microseconds from the epoch, as the zmanim are. The compiler compares the two as wall
  // clock times too -- Python compares datetimes that share a zone by their clocks -- so a
  // time a change of clocks skips or repeats is read as the clock reads, not as an instant.
  Snapshot.prototype.moment = function () {
    var gdate = this.gregorianDate();
    if (gdate === null) return null;
    var seconds = this.timeOfDay();
    if (seconds === null) seconds = 12 * 3600;
    return ((gdate - UNIX_EPOCH_JDN) * 86400 + seconds) * 1e6;
  };

  Snapshot.prototype.inTwilight = function () {
    var gdate = this.gregorianDate();
    var place = this.location();
    if (gdate === null || place === null || this.timeOfDay() === null) return false;
    var moment = this.moment();
    var z = zmanim(gdate, place, this.zone());
    return z.shkia < moment && moment < z.tzet;
  };

  // compute._for_locale: where the locale is unknown, work out both, and keep only what they
  // agree on.
  function forLocale(snapshot, compute) {
    var israel = snapshot.inIsrael();
    if (israel !== null) return compute(israel);
    var inside = compute(true), outside = compute(false);
    if (inside === null || outside === null) return null;
    var merged = {};
    Object.keys(outside).concat(Object.keys(inside)).forEach(function (name) {
      if (has(merged, name)) return;
      var value = has(inside, name) ? inside[name] : outside[name];
      var other = has(outside, name) ? outside[name] : null;
      merged[name] = pyEqual(other, value) ? value : null;
    });
    return merged;
  }

  // compute._effective_gregorian_date: the civil date whose Hebrew date is current, which
  // from nightfall is the next one.
  function effectiveGregorianDate(snapshot) {
    var gdate = snapshot.gregorianDate();
    if (gdate === null) return null;
    var place = snapshot.location();
    if (place === null || snapshot.timeOfDay() === null) return gdate;
    if (snapshot.moment() >= zmanim(gdate, place, snapshot.zone()).tzet) return gdate + 1;
    if (snapshot.day === 1) return gdate + 1;
    return gdate;
  }

  function hebrewFromSnapshot(snapshot) {
    if (snapshot.gregorianDate() !== null && snapshot.location() !== null) {
      return hebrewFromJdn(effectiveGregorianDate(snapshot));
    }
    return snapshotHebrewDate(snapshot);
  }

  // ── The derivations (compute.py) ─────────────────────────────────────────

  var HOLIDAY_FEATURES = [
    "pesah", "omer", "pesah-sheini", "lag-baomer", "shavuot", "tisha-bav", "tu-bav",
    "rosh-hashana", "tzom-gedalia", "yom-kippur", "sukkot", "shmini-atzeret", "hanukkah",
    "asara-btevet", "taanit-esther", "purim", "shushan-purim", "purim-observed",
    "purim-meshulash", "purim-katan", "shushan-purim-katan", "rosh-hodesh", "tu-bishvat",
    "taanit-bchorot", "tzom-tammuz", "sigd", "yom-hashoah", "yom-hazikaron",
    "yom-haatzmaut", "yom-yerushalayim"
  ];

  var TRIENNIAL_EPOCH_YEAR = 5756;
  var SIMHAT_TORAH_DAY = 22;

  var TRIENNIAL_PAIRS = [
    ["vayakhel-pekudei", 21], ["tazria-metzora", 26], ["achrei-mot-kedoshim", 28],
    ["behar-bechukotai", 31], ["chukat-balak", 38], ["matot-masei", 41]
  ];

  var TORAH_FEATURES = [
    "diaspora-parsha", "israel-parsha", "diaspora-next-parsha", "israel-next-parsha", "triennial-year"
  ].concat(TRIENNIAL_PAIRS.map(function (p) { return "triennial-pattern-" + p[0]; }), [
    "shabbat-shuva", "shabbat-shira", "shabbat-shkalim", "shabbat-zachor", "shabbat-parah",
    "shabbat-hahodesh", "shabbat-hagadol", "shabbat-hazon", "shabbat-nahamu",
    "shabbat-rosh-hodesh", "shabbat-mahar-hodesh", "shabbat-mevarchim"
  ]);

  var ALWAYS_YOM_TOV = ["shavuot", "rosh-hashana", "yom-kippur", "shmini-atzeret"];
  var MINOR_FASTS = ["tzom-gedalia", "asara-btevet", "taanit-esther", "tzom-tammuz"];
  var REGALIM = ["pesah", "shavuot", "sukkot", "shmini-atzeret"];
  var MUSAF_DAYS = ["pesah", "shavuot", "rosh-hashana", "yom-kippur", "sukkot",
                    "shmini-atzeret", "rosh-hodesh"];
  var LAST_FESTIVAL_DAYS = ["pesach_vii", "pesach_viii", "shavuot", "shavuot_ii",
                            "shmini_atzeret", "simchat_torah"];
  var TRIENNIAL_YEARS = [1, 2, 3];
  var PARTS_PER_HOUR = 1080;

  function computeHebrewDate(snapshot) {
    if (snapshot.gregorianDate() === null || snapshot.location() === null) return null;
    var heb = hebrewFromJdn(effectiveGregorianDate(snapshot));
    return { year: heb.year, month: heb.month, day: heb.day, "leap-year": hebrewLeap(heb.year) };
  }

  function computeHebrewTime(snapshot) {
    var gdate = snapshot.gregorianDate();
    var place = snapshot.location();
    var moment = snapshot.moment();
    if (gdate === null || place === null || moment === null) return null;
    var today = zmanim(gdate, place, snapshot.zone());
    var firstHour, start, end;
    if (moment < today.netz) {
      firstHour = 12;
      start = zmanim(gdate - 1, place, snapshot.zone()).shkia;
      end = today.netz;
    } else if (moment < today.shkia) {
      firstHour = 0;
      start = today.netz;
      end = today.shkia;
    } else {
      firstHour = 12;
      start = today.shkia;
      end = zmanim(gdate + 1, place, snapshot.zone()).netz;
    }
    var length = (end - start) / 1e6;
    var hours = length > 0 ? (moment - start) / 1e6 / length * 12 : 0.0;
    var hour = Math.min(11, Math.max(0, Math.trunc(hours)));
    var part = Math.min(PARTS_PER_HOUR - 1, Math.max(0, Math.trunc((hours - hour) * PARTS_PER_HOUR)));
    return { "variable-hour": firstHour + hour, part: part };
  }

  function computeIsrael(snapshot) {
    if (snapshot.location() === null) return null;
    return { "is-israel": isIsraelZone(snapshot.zone()) };
  }

  // The device gives the zone with the place, so there is nothing to derive.
  function computeLocation(snapshot) {
    if (snapshot.location() === null) return null;
    return { timezone: snapshot.zone() };
  }

  function computeDayOfWeek(snapshot) {
    var gdate = snapshot.gregorianDate();
    if (gdate === null) return null;
    var result = { "secular-day": weekday(gdate) };
    var place = snapshot.location();
    var heb = hebrewFromSnapshot(snapshot);
    if (heb !== null) {
      var bayn = false;
      if (place !== null && snapshot.timeOfDay() !== null) {
        var moment = snapshot.moment();
        var z = zmanim(gdate, place, snapshot.zone());
        bayn = z.shkia < moment && moment < z.tzet;
      }
      result["hebrew-day"] = weekday(heb.jdn);
      result["bayn-hashmashot"] = bayn;
    }
    return result;
  }

  function roshHodeshDay(heb) {
    if (heb.day === 30) return 1;
    if (heb.day === 1 && heb.month !== TISHREI) return addDays(heb, -1).day === 30 ? 2 : 1;
    return 0;
  }

  // compute._map_hdate_holidays: what the calendar's days of a civil date say, with the day
  // numbers counted from the Hebrew date.
  function mapCalendarDays(gdate, heb, israel) {
    var values = {};
    HOLIDAY_FEATURES.forEach(function (name) { values[name] = 0; });
    calendarDays(hebrewFromJdn(gdate), israel).forEach(function (h) {
      var name = h.name;
      if (name === "pesach") values.pesah = 1;
      else if (name === "pesach_ii") values.pesah = 2;
      else if (name.indexOf("hol_hamoed_pesach") === 0) values.pesah = heb.day - 14;
      else if (name === "pesach_vii") values.pesah = 7;
      else if (name === "pesach_viii") values.pesah = 8;
      else if (name === "shavuot") values.shavuot = 1;
      else if (name === "shavuot_ii") values.shavuot = 2;
      else if (name === "rosh_hashana_i") values["rosh-hashana"] = 1;
      else if (name === "rosh_hashana_ii") values["rosh-hashana"] = 2;
      else if (name === "yom_kippur") values["yom-kippur"] = 1;
      else if (name === "sukkot") values.sukkot = 1;
      else if (name === "sukkot_ii") values.sukkot = 2;
      else if (name.indexOf("hol_hamoed_sukkot") === 0) values.sukkot = heb.day - 14;
      else if (name === "hoshana_raba") values.sukkot = 7;
      else if (name === "shmini_atzeret") values["shmini-atzeret"] = 1;
      else if (name === "simchat_torah") values["shmini-atzeret"] = heb.day - 21;
      else if (name === "chanukah") {
        values.hanukkah = Math.abs(heb.jdn - hebrew(heb.year, KISLEV, 25).jdn) + 1;
      }
      else if (name === "purim") values.purim = 1;
      else if (name === "shushan_purim") values["shushan-purim"] = 1;
      else if (name === "tzom_tammuz") values["tzom-tammuz"] = 1;
      else if (name === "tzom_gedaliah") values["tzom-gedalia"] = 1;
      else if (name === "asara_btevet") values["asara-btevet"] = 1;
      else if (name === "taanit_esther") values["taanit-esther"] = 1;
      else if (name === "tisha_bav") values["tisha-bav"] = 1;
      else if (name === "tu_bav") values["tu-bav"] = 1;
      else if (name === "tu_bshvat") values["tu-bishvat"] = 1;
      else if (name === "yom_hashoah") values["yom-hashoah"] = 1;
      else if (name === "yom_hazikaron") values["yom-hazikaron"] = 1;
      else if (name === "yom_haatzmaut") values["yom-haatzmaut"] = 1;
      else if (name === "yom_yerushalayim") values["yom-yerushalayim"] = 1;
      else if (name === "lag_bomer") values["lag-baomer"] = 1;
    });
    var dated = hebrewDateHolidays(heb);
    Object.keys(dated).forEach(function (name) { values[name] = dated[name]; });
    var omer = omerDay(hebrewFromJdn(gdate));
    if (omer) values.omer = omer;
    values["rosh-hodesh"] = roshHodeshDay(heb);
    return values;
  }

  // compute._hebrew_date_holidays: the days the Hebrew date settles by itself.
  function hebrewDateHolidays(heb) {
    var found = {};
    var leap = hebrewLeap(heb.year);
    if (heb.month === IYAR && heb.day === 14) found["pesah-sheini"] = 1;
    if (heb.month === MARCHESHVAN && heb.day === 29) found.sigd = 1;
    var erevPesach = hebrew(heb.year, NISAN, 14);
    var firstborn = weekday(erevPesach.jdn) === 7 ? erevPesach.jdn - 2 : erevPesach.jdn;
    if (heb.jdn === firstborn) found["taanit-bchorot"] = 1;
    if (leap && heb.month === ADAR) {
      if (heb.day === 14) found["purim-katan"] = 1;
      else if (heb.day === 15) found["shushan-purim-katan"] = 1;
    }
    var adar = adarOfPurim(heb.year);
    var shushanPurim = hebrew(heb.year, adar, 15);
    if (weekday(shushanPurim.jdn) === 7 && heb.month === adar && heb.day >= 14 && heb.day <= 16) {
      found["purim-meshulash"] = heb.day - 13;
    }
    return found;
  }

  function holidays(snapshot, israel) {
    var gdate = effectiveGregorianDate(snapshot);
    var heb = hebrewFromSnapshot(snapshot);
    if (gdate === null || heb === null) return null;
    var values = mapCalendarDays(gdate, heb, israel);
    values["purim-observed"] = purimObserved(snapshot, values);
    return values;
  }

  function purimObserved(snapshot, values) {
    if (!values.purim && !values["shushan-purim"]) return 0;
    var day = snapshot.getInt(FS_PURIM_OBSERVANCE, "day");
    if (day === null) return null;
    var observed = day === 14 ? values.purim : day === 15 ? values["shushan-purim"] : 0;
    return observed ? 1 : 0;
  }

  function computeHoliday(snapshot) {
    return forLocale(snapshot, function (israel) { return holidays(snapshot, israel); });
  }

  function computeHolidayFromAggregate(snapshot) {
    if (snapshot.getBool(FS_HOLIDAY_AGG, "yom-tov") !== false) return {};
    var derived = {};
    ALWAYS_YOM_TOV.forEach(function (festival) { derived[festival] = 0; });
    return derived;
  }

  function computeHolidayAggregate(snapshot) {
    return forLocale(snapshot, function (israel) { return holidayAggregate(snapshot, israel); });
  }

  function anyPositive(values, names) {
    return names.some(function (name) { return (values[name] || 0) > 0; });
  }

  function holidayAggregate(snapshot, israel) {
    var days = holidays(snapshot, israel);
    var dow = computeDayOfWeek(snapshot);
    var heb = hebrewFromSnapshot(snapshot);
    if (days === null || dow === null) return null;
    var gdate = effectiveGregorianDate(snapshot);
    var yomTov = isYomTov(gdate, israel);
    var firstIntermediate = israel ? 2 : 3;
    var pesah = days.pesah || 0, sukkot = days.sukkot || 0;
    var result = {
      shabbat: dow["hebrew-day"] === 7,
      "motzaei-shabbat": isMotzaeiShabbat(snapshot, dow),
      "yom-tov": yomTov,
      "chol-hamoed": (firstIntermediate <= pesah && pesah <= 6) ||
                     (firstIntermediate <= sukkot && sukkot <= 7),
      regalim: anyPositive(days, REGALIM),
      "hoshana-rabba": sukkot === 7,
      "high-holidays": (days["rosh-hashana"] || 0) > 0 || (days["yom-kippur"] || 0) > 0,
      "aseret-ymei-tshuva": heb !== null && heb.month === 7 && heb.day >= 1 && heb.day <= 10,
      "minor-fast": anyPositive(days, MINOR_FASTS),
      "eruv-tavshilin": needsEruvTavshilin(snapshot, israel),
      "day-before-holiday": !yomTov && isYomTov(gdate + 1, israel),
      "day-after-holiday": !yomTov && endsAPilgrimageFestival(gdate - 1, israel)
    };
    var seasons = rainSeasons(snapshot, heb, israel);
    Object.keys(seasons).forEach(function (name) { result[name] = seasons[name]; });
    return result;
  }

  function endsAPilgrimageFestival(jdn, israel) {
    var found = calendarDays(hebrewFromJdn(jdn), israel);
    return found.some(function (h) { return h.yomTov; }) &&
      found.some(function (h) { return LAST_FESTIVAL_DAYS.indexOf(h.name) >= 0; });
  }

  function isMotzaeiShabbat(snapshot, dow) {
    if (dow["secular-day"] === 7) return dow["hebrew-day"] !== 7;
    if (dow["secular-day"] !== 1) return false;
    var gdate = snapshot.gregorianDate();
    var place = snapshot.location();
    if (gdate === null || place === null || snapshot.timeOfDay() === null) return false;
    return snapshot.moment() < zmanim(gdate, place, snapshot.zone()).alot;
  }

  function rainSeasons(snapshot, heb, israel) {
    if (heb === null) return {};
    var pesach = hebrew(heb.year, NISAN, 15).jdn;
    var found = { geshem: hebrew(heb.year, TISHREI, 22).jdn <= heb.jdn && heb.jdn <= pesach };
    if (israel) {
      found["tal-umatar"] = hebrew(heb.year, MARCHESHVAN, 7).jdn <= heb.jdn && heb.jdn <= pesach;
      return found;
    }
    var effective = effectiveGregorianDate(snapshot);
    if (effective === null) return found;
    var civil = jdnToGregorian(effective);
    if (heb.jdn > pesach) {
      found["tal-umatar"] = false;
    } else if (civil.month === 12) {
      found["tal-umatar"] = civil.day > (gregorianLeap(civil.year + 1) ? 5 : 4);
    } else {
      found["tal-umatar"] = civil.month <= 4;
    }
    return found;
  }

  function needsEruvTavshilin(snapshot, israel) {
    var gdate = effectiveGregorianDate(snapshot);
    if (gdate === null) return false;
    for (var offset = 0; offset < 4; offset++) {
      if (weekday(gdate + offset) === 6 && isYomTov(gdate + offset, israel)) return true;
    }
    return false;
  }

  function triennialCyclePatterns(hebrewYear, israel) {
    var start = hebrewYear - (((hebrewYear - TRIENNIAL_EPOCH_YEAR) % 3) + 3) % 3;
    var combined = [start, start + 1, start + 2].map(function (year) {
      var table = parshaTable(year, israel);
      var doubled = {};
      Object.keys(table).forEach(function (shabbos) {
        var reading = table[shabbos];
        if (reading !== null && reading.length > 1) doubled[reading[0]] = true;
      });
      return doubled;
    });
    var patterns = {};
    TRIENNIAL_PAIRS.forEach(function (pair) {
      patterns["triennial-pattern-" + pair[0]] = combined.map(function (doubled) {
        return doubled[pair[1]] ? "T" : "S";
      }).join("");
    });
    return patterns;
  }

  function containingShabbat(heb) {
    return addDays(heb, 7 - weekday(heb.jdn));
  }

  function shabbatOnOrBefore(heb) {
    return addDays(heb, -(weekday(heb.jdn) % 7));
  }

  function triennialYear(heb) {
    var year = heb.year;
    if (heb.month === TISHREI && heb.day < SIMHAT_TORAH_DAY) year -= 1;
    return ((((year - TRIENNIAL_EPOCH_YEAR) % 3) + 3) % 3) + 1;
  }

  function isShabbatMevarchim(shabbat) {
    for (var days = 1; days < 8; days++) {
      var candidate = addDays(shabbat, days);
      if (candidate.day !== 1 && candidate.day !== 30) continue;
      var firstOfMonth = candidate.day === 30 ? addDays(candidate, 1) : candidate;
      if (firstOfMonth.month === TISHREI) return false;
      var firstRoshHodesh = firstOfMonth;
      if (addDays(firstOfMonth, -1).day === 30) firstRoshHodesh = addDays(firstOfMonth, -1);
      return shabbat.jdn < firstRoshHodesh.jdn;
    }
    return false;
  }

  function nextWeeklyParsha(day, israel) {
    var first = weekday(day) === 7 ? 1 : 0;
    for (var offset = first; offset < first + 29; offset += 7) {
      var name = parshaName(day + offset, israel);
      if (name) {
        var h = hebrewFromJdn(day);
        if (parshaSlug(name) === "bereishis" && h.month === TISHREI && h.day < (israel ? 22 : 23)) {
          return "vezos-haberachah";
        }
        return parshaSlug(name);
      }
    }
    throw new Error("No weekly Torah reading within four weeks");
  }

  function computeTorahReading(snapshot) {
    var gdate = effectiveGregorianDate(snapshot);
    if (gdate === null) return null;
    var diaspora = parshaName(gdate, false) || "";
    var inIsrael = parshaName(gdate, true) || "";
    var shabbat = containingShabbat(hebrewFromJdn(gdate));
    var year = shabbat.year;
    var adar = adarOfPurim(year);
    var hahodesh = shabbatOnOrBefore(hebrew(year, NISAN, 1));
    var tishaBav = shabbatOnOrBefore(hebrew(year, AV, 9));
    var tomorrow = addDays(shabbat, 1);
    var is = function (other) { return shabbat.jdn === other.jdn; };
    var result = {
      "diaspora-parsha": parshaSlug(diaspora),
      "israel-parsha": parshaSlug(inIsrael),
      "diaspora-next-parsha": nextWeeklyParsha(gdate, false),
      "israel-next-parsha": nextWeeklyParsha(gdate, true),
      "triennial-year": triennialYear(shabbat),
      "shabbat-shuva": is(shabbatOnOrBefore(hebrew(year, TISHREI, 9))),
      "shabbat-shira": parshaSlug(diaspora) === "beshalach",
      "shabbat-shkalim": is(shabbatOnOrBefore(hebrew(year, adar, 1))),
      "shabbat-zachor": is(shabbatOnOrBefore(hebrew(year, adar, 13))),
      "shabbat-parah": shabbat.jdn === hahodesh.jdn - 7,
      "shabbat-hahodesh": is(hahodesh),
      "shabbat-hagadol": is(shabbatOnOrBefore(hebrew(year, NISAN, 14))),
      "shabbat-hazon": is(tishaBav),
      "shabbat-nahamu": shabbat.jdn === tishaBav.jdn + 7,
      "shabbat-rosh-hodesh": roshHodeshDay(shabbat) > 0,
      "shabbat-mahar-hodesh": roshHodeshDay(tomorrow) > 0,
      "shabbat-mevarchim": isShabbatMevarchim(shabbat)
    };
    var patterns = forLocale(snapshot, function (israel) {
      return triennialCyclePatterns(year, israel);
    }) || {};
    Object.keys(patterns).forEach(function (name) { result[name] = patterns[name]; });
    return result;
  }

  function computeServiceTime(snapshot) {
    return forLocale(snapshot, function (israel) { return serviceTime(snapshot, israel); });
  }

  function serviceTime(snapshot, israel) {
    var gdate = snapshot.gregorianDate();
    var place = snapshot.location();
    var moment = snapshot.moment();
    if (gdate === null || place === null || moment === null || snapshot.timeOfDay() === null) {
      return null;
    }
    var z = zmanim(gdate, place, snapshot.zone());
    var days = holidays(snapshot, israel) || {};
    var dow = computeDayOfWeek(snapshot) || {};
    return {
      shaharit: z.alot <= moment && moment < z.sofZmanTfilla,
      minha: z.minchaGedola <= moment && moment < z.shkia,
      maariv: moment >= z.tzet,
      musaf: dow["hebrew-day"] === 7 || anyPositive(days, MUSAF_DAYS),
      neila: (days["yom-kippur"] || 0) > 0 && moment >= z.plag,
      slihot: moment >= z.tzet || moment < z.sofZmanTfilla
    };
  }

  function computeReadingCycle(snapshot) {
    var triennial = snapshot.getBool(FS_READING_CYCLE, "triennial") === true;
    var year = triennial ? snapshot.getInt(FS_TORAH, "triennial-year") : null;
    var result = { annual: year === null };
    TRIENNIAL_YEARS.forEach(function (n) { result["triennial-year-" + n] = n === year; });
    return result;
  }

  function computeRecitation(snapshot) {
    if (snapshot.getBool(FS_SERVICE_TIME, "maariv") !== true) return {};
    return { silent: true, repetition: false };
  }

  function computeQuorum(snapshot) {
    if (snapshot.getBool(FS_QUORUM, "minyan") !== true) return null;
    return { zimmun: true };
  }

  function snapshotHebrewDate(snapshot) {
    var year = snapshot.getInt(FS_HEBREW_DATE, "year");
    var month = snapshot.getInt(FS_HEBREW_DATE, "month");
    var day = snapshot.getInt(FS_HEBREW_DATE, "day");
    if (year === null || month === null || day === null) return null;
    return hebrewOrNull(year, month, day);
  }

  // calendar/hallel.hallel_on.
  function hallelOn(heb, israel) {
    var month = heb.month, date = heb.day;
    var sinceHanukkah = heb.jdn - hebrew(heb.year, KISLEV, 25).jdn;
    if (sinceHanukkah >= 0 && sinceHanukkah < 8) return "full";
    if (month === 1 && date >= 15 && date <= (israel ? 21 : 22)) {
      return date <= (israel ? 15 : 16) ? "full" : "half";
    }
    if (month === 3 && date >= 6 && date <= (israel ? 6 : 7)) return "full";
    if (month === 7 && date >= 15 && date <= (israel ? 22 : 23)) return "full";
    if (date === 30 || (date === 1 && month !== 7)) return "half";
    return "none";
  }

  function computeHallel(snapshot) {
    var heb = snapshotHebrewDate(snapshot);
    var israel = snapshot.inIsrael();
    if (heb === null || israel === null) return null;
    var mode = hallelOn(heb, israel);
    return { recite: mode !== "none", full: mode === "full" };
  }

  // calendar/motzaei_shabbat.omit_vihi_noam: a festival in the six working days to come.
  function omitVihiNoam(heb, israel) {
    var w = weekday(heb.jdn);
    var sunday = w === 7 ? heb.jdn + 1 : heb.jdn - (w - 1);
    for (var offset = 0; offset < 6; offset++) {
      if (isYomTov(sunday + offset, israel)) return true;
    }
    return false;
  }

  function computeMotzaeiShabbat(snapshot) {
    var heb = snapshotHebrewDate(snapshot);
    var israel = snapshot.inIsrael();
    if (heb === null || israel === null) return null;
    return { "omit-vihi-noam": omitVihiNoam(heb, israel) };
  }

  // calendar/avot.chapters_on: the chapter or chapters of Pirkei Avot read on a Shabbat.
  function avotChapters(heb, israel) {
    var end = hebrew(heb.year + 1, TISHREI, 1).jdn;
    var start = hebrew(heb.year, NISAN, israel ? 21 : 22).jdn;
    if (weekday(heb.jdn) !== 7 || !(start < heb.jdn && heb.jdn < end)) return [];
    var eligible = [];
    for (var jdn = start + 1; jdn < end; jdn++) {
      if (weekday(jdn) !== 7) continue;
      var date = hebrewFromJdn(jdn);
      var shavuot = date.month === 3 && (date.day === 6 || (!israel && date.day === 7));
      var tishaBav = date.month === 5 && (date.day === 8 || date.day === 9);
      if (!shavuot && !tishaBav) eligible.push(jdn);
    }
    var index = eligible.indexOf(heb.jdn);
    if (index < 0) return [];
    if (index < 18) return [index % 6 + 1];
    var remain = eligible.length - index;
    if (remain === 1) return [5, 6];
    if (remain === 2) return [3, 4];
    if (remain === 3) return index === 19 ? [2] : [1, 2];
    if (remain === 4) return [1];
    throw new Error("Unexpected number of Sabbaths in the Avot season");
  }

  function computeAvot(snapshot) {
    var heb = snapshotHebrewDate(snapshot);
    var israel = snapshot.inIsrael();
    if (heb === null || israel === null) return null;
    var selected = avotChapters(heb, israel);
    var start = hebrew(heb.year, NISAN, israel ? 21 : 22).jdn;
    var end = hebrew(heb.year + 1, TISHREI, 1).jdn;
    var result = { season: weekday(heb.jdn) === 7 && start < heb.jdn && heb.jdn < end };
    for (var n = 1; n <= 6; n++) result["chapter-" + n] = selected.indexOf(n) >= 0;
    return result;
  }

  // ── The derivation graph (derivation_graph.DERIVATION_SPECS) ─────────────

  function refs(fsType, features) {
    return features.map(function (feature) { return [fsType, feature]; });
  }

  var GREGORIAN_INPUTS = refs(FS_GREGORIAN, ["year", "month", "day"]);
  var LOCATION_INPUTS = refs(FS_LOCATION, ["latitude", "longitude"]);
  var TIME_INPUTS = refs(FS_TIME, ["hour", "minute"]);
  var HEBREW_DATE_INPUTS = refs(FS_HEBREW_DATE, ["year", "month", "day"]);
  var ISRAEL_INPUT = [[FS_ISRAEL, "is-israel"]];

  function spec(fsType, inputs, name, compute) {
    return { fsType: fsType, inputs: inputs, name: name, compute: compute };
  }

  // In the order of DERIVATION_SPECS, each named for its Python counterpart.
  var SPECS = [
    spec(FS_HALLEL, HEBREW_DATE_INPUTS.concat(ISRAEL_INPUT), "compute_hallel", computeHallel),
    spec(FS_MOTZAEI_SHABBAT, HEBREW_DATE_INPUTS.concat(ISRAEL_INPUT), "compute_motzaei_shabbat",
         computeMotzaeiShabbat),
    spec(FS_AVOT, HEBREW_DATE_INPUTS.concat(ISRAEL_INPUT), "compute_avot", computeAvot),
    spec(FS_LOCATION, LOCATION_INPUTS, "compute_location", computeLocation),
    spec(FS_ISRAEL, LOCATION_INPUTS, "compute_israel", computeIsrael),
    spec(FS_HEBREW_DATE, GREGORIAN_INPUTS.concat(LOCATION_INPUTS), "compute_hebrew_date",
         computeHebrewDate),
    spec(FS_DAY_OF_WEEK, GREGORIAN_INPUTS, "compute_day_of_week", computeDayOfWeek),
    spec(FS_HEBREW_TIME, GREGORIAN_INPUTS.concat(LOCATION_INPUTS, TIME_INPUTS),
         "compute_hebrew_time", computeHebrewTime),
    spec(FS_HOLIDAY, GREGORIAN_INPUTS.concat(HEBREW_DATE_INPUTS), "compute_holiday",
         computeHoliday),
    spec(FS_HOLIDAY_AGG, GREGORIAN_INPUTS.concat(HEBREW_DATE_INPUTS),
         "compute_holiday_aggregate", computeHolidayAggregate),
    spec(FS_TORAH, GREGORIAN_INPUTS, "compute_torah_reading", computeTorahReading),
    spec(FS_SERVICE_TIME, GREGORIAN_INPUTS.concat(LOCATION_INPUTS, TIME_INPUTS),
         "compute_service_time", computeServiceTime),
    spec(FS_READING_CYCLE, [[FS_READING_CYCLE, "triennial"], [FS_TORAH, "triennial-year"]],
         "compute_reading_cycle", computeReadingCycle),
    spec(FS_HOLIDAY, [[FS_HOLIDAY_AGG, "yom-tov"]], "compute_holiday_from_aggregate",
         computeHolidayFromAggregate),
    spec(FS_RECITATION, [[FS_SERVICE_TIME, "maariv"]], "compute_recitation", computeRecitation),
    spec(FS_QUORUM, [[FS_QUORUM, "minyan"]], "compute_quorum", computeQuorum)
  ];

  // derivation_graph.topological_derivation_order.
  function derivationOrder() {
    var derivedTypes = {};
    SPECS.forEach(function (s) { derivedTypes[s.fsType] = true; });
    var ordered = [];
    var emitted = {};
    while (ordered.length < SPECS.length) {
      var progress = false;
      SPECS.forEach(function (s) {
        if (ordered.indexOf(s) >= 0) return;
        var ready = s.inputs.every(function (input) {
          var fsType = input[0];
          return fsType === s.fsType || !derivedTypes[fsType] || emitted[fsType];
        });
        if (ready) {
          ordered.push(s);
          emitted[s.fsType] = true;
          progress = true;
        }
      });
      if (!progress) throw new Error("Circular dependency in derivation graph");
    }
    return ordered;
  }

  var ORDER = derivationOrder();

  // Every feature a derivation reads, its inputs and what it consults besides. A value given
  // for any other feature changes nothing else that is derived.
  var READ_FEATURES = {};
  READ_FEATURES[FS_GREGORIAN] = ["year", "month", "day"];
  READ_FEATURES[FS_TIME] = ["hour", "minute", "second"];
  READ_FEATURES[FS_LOCATION] = ["latitude", "longitude", "timezone"];
  READ_FEATURES[FS_ISRAEL] = ["is-israel"];
  READ_FEATURES[FS_HEBREW_DATE] = ["year", "month", "day"];
  READ_FEATURES[FS_PURIM_OBSERVANCE] = ["day"];
  READ_FEATURES[FS_HOLIDAY_AGG] = ["yom-tov"];
  READ_FEATURES[FS_READING_CYCLE] = ["triennial"];
  READ_FEATURES[FS_TORAH] = ["triennial-year"];
  READ_FEATURES[FS_SERVICE_TIME] = ["maariv"];
  READ_FEATURES[FS_QUORUM] = ["minyan"];

  // ── The settings stack (derived_settings.recalculate_derived_settings) ───
  //
  // A list of entries {fs, feature, value, source}, the last one for a feature being the one
  // in force. Explicit entries ("init", "declared") are what the volume and its reader said;
  // derived ones are what follows from them, and never replace an explicit one.

  // derived_settings.STATIC_DEFAULTS, of the calendar's feature structures: an electronic
  // book's reader supplies the rest, as the book's own defaults.
  var STATIC_DEFAULTS = {};
  STATIC_DEFAULTS[FS_PURIM_OBSERVANCE] = { day: 14 };

  var DATE_FEATURES = ["year", "month", "day"];
  var MAX_DATE_PASSES = 3;

  function Stack(entries) {
    this.entries = entries.map(function (e) {
      return { fs: e.fs, feature: e.feature, value: e.value,
             source: e.source === "init" ? "init" : "declared" };
    });
  }

  Stack.prototype.active = function (fsType, feature) {
    for (var i = this.entries.length - 1; i >= 0; i--) {
      var entry = this.entries[i];
      if (entry.fs === fsType && entry.feature === feature) return entry;
    }
    return null;
  };

  Stack.prototype.value = function (fsType, feature) {
    var entry = this.active(fsType, feature);
    return entry === null ? undefined : entry.value;
  };

  Stack.prototype.removeDerived = function (fsType, feature) {
    this.entries = this.entries.filter(function (e) {
      return !(e.source === "derived" && e.fs === fsType && e.feature === feature);
    });
  };

  Stack.prototype.pushDerived = function (fsType, feature, value) {
    this.removeDerived(fsType, feature);
    this.entries.push({ fs: fsType, feature: feature, value: value, source: "derived" });
  };

  Stack.prototype.pushStaticDefault = function (fsType, feature) {
    var defaults = STATIC_DEFAULTS[fsType];
    if (!defaults || !has(defaults, feature)) return;
    this.pushDerived(fsType, feature, defaults[feature]);
  };

  // derived_settings._clear_derived: withdraw a derived value, falling back to the default.
  Stack.prototype.clearDerived = function (fsType, feature) {
    var entry = this.active(fsType, feature);
    if (entry === null || entry.source !== "derived") return;
    this.removeDerived(fsType, feature);
    this.pushStaticDefault(fsType, feature);
  };

  Stack.prototype.lastDeclared = function (fsType) {
    for (var i = this.entries.length - 1; i >= 0; i--) {
      var entry = this.entries[i];
      if (entry.fs === fsType && DATE_FEATURES.indexOf(entry.feature) >= 0 &&
          entry.source !== "derived") {
        return i;
      }
    }
    return -1;
  };

  function explicit(entry) {
    return entry !== null && entry.source !== "derived";
  }

  function computeAcrossTwilight(s, snapshot, twilight) {
    if (!twilight) return s.compute(snapshot);
    var days = [snapshot.onDay(0), snapshot.onDay(1)];
    var ending = s.compute(days[0]), starting = s.compute(days[1]);
    if (ending === null || starting === null) return null;
    var on = function (day, computed, feature) {
      if (has(computed, feature)) return computed[feature];
      var value = days[day].get(s.fsType, feature);
      return value === undefined ? null : value;
    };
    var merged = {};
    Object.keys(ending).concat(Object.keys(starting)).forEach(function (feature) {
      if (has(merged, feature)) return;
      var onEnding = on(0, ending, feature), onStarting = on(1, starting, feature);
      merged[feature] = pyEqual(onEnding, onStarting) ? onEnding
                                                       : { twilight: [onEnding, onStarting] };
    });
    return merged;
  }

  function unknownOverridden(stack, fsType, overridable) {
    overridable.filter(function (ref) { return ref[0] === fsType; })
      .map(function (ref) { return ref[1]; }).sort()
      .forEach(function (feature) { stack.pushDerived(fsType, feature, null); });
  }

  function applySpec(stack, s, snapshot, overridable, twilight) {
    var existing = {};
    stack.entries.forEach(function (e) { if (e.fs === s.fsType) existing[e.feature] = true; });
    var computed = computeAcrossTwilight(s, snapshot, twilight);
    if (computed === null) {
      Object.keys(existing).forEach(function (feature) { stack.clearDerived(s.fsType, feature); });
      unknownOverridden(stack, s.fsType, overridable);
      return;
    }
    var inputsKnown = s.inputs.every(function (input) {
      var entry = stack.active(input[0], input[1]);
      return entry !== null && entry.value !== null;
    });
    if (!inputsKnown) {
      Object.keys(computed).forEach(function (feature) { stack.clearDerived(s.fsType, feature); });
      unknownOverridden(stack, s.fsType, overridable);
      return;
    }
    var isOverridable = function (feature) {
      return overridable.some(function (ref) { return ref[0] === s.fsType && ref[1] === feature; });
    };
    Object.keys(computed).forEach(function (feature) {
      if (explicit(stack.active(s.fsType, feature)) && !isOverridable(feature)) return;
      stack.pushDerived(s.fsType, feature, computed[feature]);
    });
  }

  function hebrewDatePrevails(stack) {
    var heb = stack.lastDeclared(FS_HEBREW_DATE);
    return heb >= 0 && heb > stack.lastDeclared(FS_GREGORIAN);
  }

  // derived_settings._reconcile_dates: when both a civil and a Hebrew date are declared, the
  // last one declared prevails.
  function reconcileDates(stack, snapshot) {
    var gregorian = stack.lastDeclared(FS_GREGORIAN);
    var heb = stack.lastDeclared(FS_HEBREW_DATE);
    if (gregorian < 0 || heb < 0 || gregorian > heb) {
      DATE_FEATURES.forEach(function (feature) { stack.clearDerived(FS_GREGORIAN, feature); });
      if (gregorian >= 0 && heb >= 0) return refs(FS_HEBREW_DATE, DATE_FEATURES);
      return [];
    }
    if (DATE_FEATURES.some(function (f) { return snapshot.getInt(FS_HEBREW_DATE, f) === null; })) {
      return [];
    }
    var civil = civilDateOfHebrew(snapshot);
    var values = [null, null, null];
    var g = civil === null ? null : jdnToGregorian(civil);
    // Before the first year of the Common Era there is no civil date to give.
    if (g !== null && g.year >= 1) values = [g.year, g.month, g.day];
    DATE_FEATURES.forEach(function (feature, i) {
      stack.pushDerived(FS_GREGORIAN, feature, values[i]);
    });
    return [];
  }

  // derived_settings._civil_date_of_hebrew: the civil date a Hebrew date falls on, at the
  // declared time -- the evening before its daytime, from nightfall.
  function civilDateOfHebrew(snapshot) {
    var values = DATE_FEATURES.map(function (f) { return snapshot.getInt(FS_HEBREW_DATE, f); });
    if (values.indexOf(null) >= 0 || !validHebrew(values[0], values[1], values[2])) return null;
    var daytime = hebrew(values[0], values[1], values[2]).jdn;
    var evening = jdnToGregorian(daytime - 1);
    var probe = new Snapshot(function (fsType, feature) {
      if (fsType === FS_GREGORIAN && has(evening, feature)) return evening[feature];
      return snapshot.get(fsType, feature);
    });
    return effectiveGregorianDate(probe) === daytime ? daytime - 1 : daytime;
  }

  function dateFingerprint(stack) {
    var out = [];
    [FS_GREGORIAN, FS_HEBREW_DATE].forEach(function (fsType) {
      DATE_FEATURES.forEach(function (feature) { out.push(stack.value(fsType, feature)); });
    });
    return out;
  }

  function sameFingerprint(a, b) {
    return a.every(function (value, i) {
      return value === b[i] || pyEqual(value, b[i]);
    });
  }

  // Everything the settings imply. `entries` are the explicit settings, the earliest first:
  // [{fs, feature, value, source?}], source "init" or else "declared" -- never a derived value,
  // which the derivations would treat as their own. A place is given with its time zone. Returns the settings in
  // force, {fs type: {feature: value}}, derived values included.
  function derive(entries) {
    var stack = new Stack(entries);
    Object.keys(STATIC_DEFAULTS).forEach(function (fsType) {
      Object.keys(STATIC_DEFAULTS[fsType]).forEach(function (feature) {
        if (stack.active(fsType, feature) === null) stack.pushStaticDefault(fsType, feature);
      });
    });
    var snapshot = new Snapshot(function (fsType, feature) {
      return stack.value(fsType, feature);
    });
    for (var pass = 0; pass < MAX_DATE_PASSES; pass++) {
      var before = dateFingerprint(stack);
      var overridable = reconcileDates(stack, snapshot);
      var twilight = snapshot.inTwilight() && !hebrewDatePrevails(stack);
      ORDER.forEach(function (s) { applySpec(stack, s, snapshot, overridable, twilight); });
      if (sameFingerprint(dateFingerprint(stack), before)) break;
    }
    var settings = {};
    stack.entries.forEach(function (entry) {
      if (!has(settings, entry.fs)) settings[entry.fs] = {};
      settings[entry.fs][entry.feature] = entry.value;
    });
    return settings;
  }

  root.OSCal = {
    derive: derive,
    SPECS: SPECS,
    ORDER: ORDER,
    READ_FEATURES: READ_FEATURES,
    STATIC_DEFAULTS: STATIC_DEFAULTS,
    HOLIDAY_FEATURES: HOLIDAY_FEATURES,
    TORAH_FEATURES: TORAH_FEATURES,
    ALWAYS_YOM_TOV: ALWAYS_YOM_TOV,
    ISRAEL_ZONES: ISRAEL_ZONES,
    // The pieces, for the agreement tests.
    gregorianToJdn: gregorianToJdn,
    jdnToGregorian: jdnToGregorian,
    hebrew: hebrew,
    hebrewFromJdn: hebrewFromJdn,
    hebrewLeap: hebrewLeap,
    weekday: weekday,
    parshaTable: parshaTable,
    parshaName: parshaName,
    calendarDays: calendarDays,
    isYomTov: isYomTov,
    omerDay: omerDay,
    zmanim: zmanim,
    Snapshot: Snapshot
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
