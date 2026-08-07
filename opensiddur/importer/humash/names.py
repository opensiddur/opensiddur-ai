"""The names of the weekly parshiyot, in the three forms the importer needs.

``JLPTEI-3.md`` asks for transliterated Hebrew in URN path segments, "unless the text has a
common name (with a common spelling)". Every parshah does, so the table below is explicit
rather than produced by running the transliteration rules over the Hebrew: mechanical
transliteration would give forms nobody writes (``vzat_hbrkh``), and it would silently drop
the maqaf in לך־לך the way the jps1917 importer does.

The table is also the join between the two sources — MAM names the parshiyot in Hebrew, hebcal
in English — so it must not depend on the two happening to be in the same order.
"""

from __future__ import annotations

import re
import unicodedata

# (MAM Hebrew name, hebcal name, opensiddur slug)
PARSHA_NAMES: tuple[tuple[str, str, str], ...] = (
    ("בראשית", "Bereshit", "bereshit"),
    ("נֹח", "Noach", "noach"),
    ("לך־לך", "Lech-Lecha", "lech_lecha"),
    ("וירא", "Vayera", "vayera"),
    ("חיי שרה", "Chayei Sara", "chayei_sara"),
    ("תולדֹת", "Toldot", "toldot"),
    ("ויצא", "Vayetzei", "vayetzei"),
    ("וישלח", "Vayishlach", "vayishlach"),
    ("וישב", "Vayeshev", "vayeshev"),
    ("מקץ", "Miketz", "miketz"),
    ("ויגש", "Vayigash", "vayigash"),
    ("ויחי", "Vayechi", "vayechi"),
    ("שמות", "Shemot", "shemot"),
    ("וארא", "Vaera", "vaera"),
    ("בֹא", "Bo", "bo"),
    ("בשלח", "Beshalach", "beshalach"),
    ("יתרו", "Yitro", "yitro"),
    ("משפטים", "Mishpatim", "mishpatim"),
    ("תרומה", "Terumah", "terumah"),
    ("תצוה", "Tetzaveh", "tetzaveh"),
    ("כי תשא", "Ki Tisa", "ki_tisa"),
    ("ויקהל", "Vayakhel", "vayakhel"),
    ("פקודי", "Pekudei", "pekudei"),
    ("ויקרא", "Vayikra", "vayikra"),
    ("צו", "Tzav", "tzav"),
    ("שמיני", "Shmini", "shmini"),
    ("תזריע", "Tazria", "tazria"),
    ("מצֹרע", "Metzora", "metzora"),
    ("אחרי מות", "Achrei Mot", "achrei_mot"),
    ("קדֹשים", "Kedoshim", "kedoshim"),
    ("אמֹר", "Emor", "emor"),
    ("בהר", "Behar", "behar"),
    ("בחֻקֹתי", "Bechukotai", "bechukotai"),
    ("במדבר", "Bamidbar", "bamidbar"),
    ("נשֹא", "Nasso", "nasso"),
    ("בהעלֹתך", "Beha'alotcha", "behaalotcha"),
    ("שלח", "Sh'lach", "shlach"),
    ("קֹרח", "Korach", "korach"),
    ("חֻקת", "Chukat", "chukat"),
    ("בלק", "Balak", "balak"),
    ("פינחס", "Pinchas", "pinchas"),
    ("מטות", "Matot", "matot"),
    ("מסעי", "Masei", "masei"),
    ("דברים", "Devarim", "devarim"),
    ("ואתחנן", "Vaetchanan", "vaetchanan"),
    ("עקב", "Eikev", "eikev"),
    ("ראה", "Re'eh", "reeh"),
    ("שֹפטים", "Shoftim", "shoftim"),
    ("כי־תצא", "Ki Teitzei", "ki_teitzei"),
    ("כי־תבוא", "Ki Tavo", "ki_tavo"),
    ("נִצבים", "Nitzavim", "nitzavim"),
    ("וילך", "Vayeilech", "vayeilech"),
    ("האזינו", "Ha'azinu", "haazinu"),
    ("וזאת הברכה", "Vezot Haberakhah", "vezot_haberakhah"),
)

# Weeks on which two parshiyot are read together. hebcal names these by joining the two.
COMBINED_PARSHIYOT: tuple[tuple[str, str], ...] = (
    ("Vayakhel-Pekudei", "vayakhel_pekudei"),
    ("Tazria-Metzora", "tazria_metzora"),
    ("Achrei Mot-Kedoshim", "achrei_mot_kedoshim"),
    ("Behar-Bechukotai", "behar_bechukotai"),
    ("Chukat-Balak", "chukat_balak"),
    ("Matot-Masei", "matot_masei"),
    ("Nitzavim-Vayeilech", "nitzavim_vayeilech"),
)


def _fold(hebrew: str) -> str:
    """Strip pointing and cantillation so MAM's pointed names match the table's.

    Only combining marks are removed. The maqaf in לך־לך is punctuation, not a mark, and is
    deliberately kept: folding it away is what collapses the name to לךלך.
    """
    return "".join(
        char for char in unicodedata.normalize("NFD", hebrew)
        if unicodedata.category(char) != "Mn"
    )


_BY_FOLDED_HEBREW = {_fold(hebrew): (hebrew, hebcal, slug) for hebrew, hebcal, slug in PARSHA_NAMES}
_BY_HEBCAL = {hebcal: (hebrew, hebcal, slug) for hebrew, hebcal, slug in PARSHA_NAMES}

HEBCAL_TO_SLUG = {hebcal: slug for _, hebcal, slug in PARSHA_NAMES}
HEBCAL_TO_SLUG.update(dict(COMBINED_PARSHIYOT))
SLUG_TO_HEBREW = {slug: hebrew for hebrew, _, slug in PARSHA_NAMES}


def slug_for_hebrew(hebrew: str) -> str:
    """The slug for a parshah named in Hebrew, with or without pointing."""
    entry = _BY_FOLDED_HEBREW.get(_fold(hebrew))
    if entry is None:
        raise KeyError(f"Unknown parshah name: {hebrew!r}")
    return entry[2]


def hebcal_for_hebrew(hebrew: str) -> str:
    entry = _BY_FOLDED_HEBREW.get(_fold(hebrew))
    if entry is None:
        raise KeyError(f"Unknown parshah name: {hebrew!r}")
    return entry[1]


def slugify_reading_name(name: str) -> str:
    """Slug for a reading hebcal names but the parshah table does not, e.g. a festival."""
    folded = name.replace("'", "").replace("’", "")
    return re.sub(r"[\s\-/]+", "_", folded.lower()).strip("_")
