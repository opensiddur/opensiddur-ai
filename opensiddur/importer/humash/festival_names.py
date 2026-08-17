"""Hebrew titles for the festival and special-Shabbat readings.

hebcal names its readings in English — "Shabbat Shekalim", "Pesach VII (on Shabbat)" — and
those names reached the page, which in a Hebrew volume is the one place the humash spoke
English where everything else is Hebrew.

The names are composed rather than listed one by one: 112 readings are built from about forty
occasions and a handful of qualifiers, and a table with every combination spelled out would
repeat פֶּסַח fourteen times and go stale the moment hebcal adds a day. An occasion with no
Hebrew name keeps its English one and says so in the log, so a name hebcal adds later is
visible rather than silently dropped.
"""

from __future__ import annotations

import logging
import re

from opensiddur.importer.humash.names import (
    SLUG_TO_HEBREW,
    SLUG_TO_VOCALIZED,
    slugify_reading_name,
)

logger = logging.getLogger(__name__)

# The occasions themselves. Longest match wins, so "Shabbat Rosh Chodesh Chanukah" is found
# before "Shabbat Rosh Chodesh", and that before "Rosh Chodesh".
OCCASION_NAMES: dict[str, str] = {
    "Asara B'Tevet": "עֲשָׂרָה בְּטֵבֵת",
    "Chanukah": "חֲנֻכָּה",
    "Erev Purim": "עֶרֶב פּוּרִים",
    "Erev Simchat Torah": "עֶרֶב שִׂמְחַת תּוֹרָה",
    "Erev Tish'a B'Av": "עֶרֶב תִּשְׁעָה בְּאָב",
    "Fast Day": "יוֹם תַּעֲנִית",
    "Pesach": "פֶּסַח",
    "Pesach Chol ha-Moed": "חֹל הַמּוֹעֵד פֶּסַח",
    "Pesach Shabbat Chol ha-Moed": "שַׁבָּת חֹל הַמּוֹעֵד פֶּסַח",
    "Purim": "פּוּרִים",
    "Rosh Chodesh": "רֹאשׁ חֹדֶשׁ",
    "Rosh Hashana": "רֹאשׁ הַשָּׁנָה",
    "Shabbat HaChodesh": "שַׁבָּת הַחֹדֶשׁ",
    "Shabbat HaGadol": "שַׁבָּת הַגָּדוֹל",
    "Shabbat Machar Chodesh": "שַׁבָּת מָחָר חֹדֶשׁ",
    "Shabbat Parah": "שַׁבָּת פָּרָה",
    "Shabbat Rosh Chodesh": "שַׁבָּת רֹאשׁ חֹדֶשׁ",
    "Shabbat Rosh Chodesh Chanukah": "שַׁבָּת רֹאשׁ חֹדֶשׁ חֲנֻכָּה",
    "Shabbat Shekalim": "שַׁבָּת שְׁקָלִים",
    "Shabbat Shuva": "שַׁבָּת שׁוּבָה",
    "Shabbat Zachor": "שַׁבָּת זָכוֹר",
    "Shavuot": "שָׁבוּעוֹת",
    "Shmini Atzeret": "שְׁמִינִי עֲצֶרֶת",
    "Shushan Purim": "שׁוּשַׁן פּוּרִים",
    "Simchat Torah": "שִׂמְחַת תּוֹרָה",
    "Sukkot": "סֻכּוֹת",
    "Sukkot Chol ha-Moed": "חֹל הַמּוֹעֵד סֻכּוֹת",
    "Sukkot Final Day": "יוֹם אַחֲרוֹן שֶׁל סֻכּוֹת",
    "Sukkot Shabbat Chol ha-Moed": "שַׁבָּת חֹל הַמּוֹעֵד סֻכּוֹת",
    "Ta'anit Esther": "תַּעֲנִית אֶסְתֵּר",
    "Tish'a B'Av": "תִּשְׁעָה בְּאָב",
    "Tzom Gedaliah": "צוֹם גְּדַלְיָה",
    "Tzom Tammuz": "צוֹם תַּמּוּז",
    "Yom HaAtzma'ut": "יוֹם הָעַצְמָאוּת",
    "Yom Kippur": "יוֹם הַכִּפּוּרִים",
    "Yom Yerushalayim": "יוֹם יְרוּשָׁלַיִם",
}

# The month a Rosh Chodesh reading belongs to, spelled as hebcal spells it.
MONTH_NAMES: dict[str, str] = {
    "Nisan": "נִיסָן",
    "Iyyar": "אִיָּר",
    "Sivan": "סִיוָן",
    "Tamuz": "תַּמּוּז",
    "Av": "אָב",
    "Elul": "אֱלוּל",
    "Tishrei": "תִּשְׁרֵי",
    "Cheshvan": "חֶשְׁוָן",
    "Kislev": "כִּסְלֵו",
    "Tevet": "טֵבֵת",
    "Sh'vat": "שְׁבָט",
    "Adar": "אֲדָר",
    "Adar I": "אֲדָר א׳",
    "Adar II": "אֲדָר ב׳",
}

# What a parenthetical says. Anything else is passed through untranslated.
QUALIFIERS: dict[str, str] = {
    "on Shabbat": "בְּשַׁבָּת",
    "on Rosh Chodesh": "בְּרֹאשׁ חֹדֶשׁ",
    "Mincha": "מִנְחָה",
    "Mincha, Alternate": "מִנְחָה, נֻסָּח אַחֵר",
    "Mincha, Traditional": "מִנְחָה, מָסֹרֶת",
    "Morning": "שַׁחֲרִית",
    "Afternoon": "מִנְחָה",
    "CH''M": "חֹל הַמּוֹעֵד",
    "Hoshana Raba": "הוֹשַׁעְנָא רַבָּה",
}

# Phrases that follow a parshah's name and say which year's variant of its reading this is.
TRAILERS: tuple[tuple[str, str], ...] = (
    ("on Shabbat Rosh Chodesh", "בְּשַׁבָּת רֹאשׁ חֹדֶשׁ"),
    ("following Special Shabbat", "אַחֲרֵי שַׁבָּת מְיֻחֶדֶת"),
    ("with 3rd Haftarah of Consolation", "עִם הַהַפְטָרָה הַשְּׁלִישִׁית דְּנֶחָמְתָא"),
    ("occurring after 17 Tammuz", "אַחַר י״ז בְּתַמּוּז"),
    ("on Sunday", "בְּיוֹם רִאשׁוֹן"),
    ("on Monday", "בְּיוֹם שֵׁנִי"),
)

# Roman numerals name the days of a festival; hebrew letters do the same job without being
# reversed when set inside right-to-left text.
ORDINALS: dict[str, str] = {
    "I": "א׳", "II": "ב׳", "III": "ג׳", "IV": "ד׳", "V": "ה׳",
    "VI": "ו׳", "VII": "ז׳", "VIII": "ח׳",
}

DAY_LETTERS: dict[int, str] = {
    1: "א׳", 2: "ב׳", 3: "ג׳", 4: "ד׳", 5: "ה׳", 6: "ו׳", 7: "ז׳", 8: "ח׳",
}

_PARENTHETICAL = re.compile(r"^(?P<base>.*?)\s*\((?P<qualifier>[^)]*)\)\s*$")
_DAY = re.compile(r"^(?P<base>.*?)\s+Day\s+(?P<day>\d+)$")
_ORDINAL = re.compile(r"^(?P<base>.*?)\s+(?P<ordinal>I{1,3}|IV|VI{0,3})$")


def _occasion(name: str) -> str | None:
    """The Hebrew for a bare occasion, a Rosh Chodesh of a named month, or a parshah."""
    known = OCCASION_NAMES.get(name)
    if known is not None:
        return known
    if name.startswith("Rosh Chodesh "):
        month = MONTH_NAMES.get(name[len("Rosh Chodesh "):])
        if month is not None:
            return f"{OCCASION_NAMES['Rosh Chodesh']} {month}"
        return None
    # Several readings are a weekly parshah read on a particular year, named by the parshah.
    slug = slugify_reading_name(name)
    return SLUG_TO_VOCALIZED.get(slug) or SLUG_TO_HEBREW.get(slug)


def hebrew_name(name: str) -> str:
    """The Hebrew title for one of hebcal's reading names, or the name itself if unknown."""
    qualifier_he: str | None = None
    base = name

    parenthetical = _PARENTHETICAL.match(base)
    if parenthetical is not None:
        base = parenthetical.group("base")
        qualifier = parenthetical.group("qualifier")
        qualifier_he = QUALIFIERS.get(qualifier)
        if qualifier_he is None and qualifier.startswith("with "):
            # "(with Ha'azinu)" — which parshah Shabbat Shuva falls on that year.
            slug = slugify_reading_name(qualifier[len("with "):])
            parshah = SLUG_TO_VOCALIZED.get(slug) or SLUG_TO_HEBREW.get(slug)
            qualifier_he = f"עִם {parshah}" if parshah is not None else None
        if qualifier_he is None:
            logger.warning("No Hebrew for the qualifier %r of %r", qualifier, name)
            qualifier_he = qualifier

    for english, hebrew in TRAILERS:
        if base.endswith(" " + english):
            base = base[: -len(english) - 1]
            qualifier_he = hebrew if qualifier_he is None else f"{hebrew}, {qualifier_he}"
            break

    suffix: str | None = None
    day = _DAY.match(base)
    ordinal = _ORDINAL.match(base) if day is None else None
    if day is not None:
        base, suffix = day.group("base"), f"יוֹם {DAY_LETTERS[int(day.group('day'))]}"
    elif ordinal is not None and _occasion(ordinal.group("base")) is not None:
        # Only when the stem without it is a known occasion: "Adar II" is a month, not an
        # ordinal, and "Rosh Chodesh Adar II" must not be read as the second Rosh Chodesh Adar.
        base, suffix = ordinal.group("base"), ORDINALS[ordinal.group("ordinal")]

    hebrew = _occasion(base)
    if hebrew is None:
        logger.warning("No Hebrew name for the reading %r, so it stays in English", name)
        return name

    if suffix is not None:
        hebrew = f"{hebrew} {suffix}"
    if qualifier_he is not None:
        hebrew = f"{hebrew} ({qualifier_he})"
    return hebrew
