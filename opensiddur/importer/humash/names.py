"""The parshah names the humash needs beyond the shared table.

The 54 weekly names, and lookups by Hebrew or hebcal name, live in
:mod:`opensiddur.importer.util.parshiyot` and are re-exported here. What is local to the
humash is the *pairs*: the weeks on which two parshiyot are read together. The shared table
knows a pair's hebcal name because hebcal names one, but the humash also needs the Hebrew
form to match MAM, and needs to know which two parshiyot each pair joins so that a combined
week's aliyot can be scoped to the pair rather than to either member.
"""

from __future__ import annotations

from opensiddur.importer.util.parshiyot import (
    COMBINED_PARSHIYOT as _COMBINED_HEBCAL,
    HEBCAL_TO_SLUG,
    PARSHA_NAMES,
    SLUG_TO_HEBREW,
    hebcal_for_hebrew,
    slug_for_hebrew,
    slugify_reading_name,
)
from opensiddur.importer.util.hebrew import normalize_hebrew

__all__ = [
    "COMBINED_PARSHIYOT",
    "HEBCAL_TO_SLUG",
    "PAIR_FOR_MEMBER",
    "PAIR_MEMBERS",
    "PARSHA_NAMES",
    "SLUG_TO_HEBREW",
    "hebcal_for_hebrew",
    "slug_for_combined_hebrew",
    "slug_for_hebrew",
    "slugify_reading_name",
]

# MAM writes a joined name with an en-dash — ויקהל–פקודי — which is neither the maqaf of
# לך־לך nor the hyphen hebcal joins with, so the Hebrew form is given here rather than
# composed from the two members.
_COMBINED_HEBREW: dict[str, str] = {
    "vayakhel_pekudei": "ויקהל–פקודי",
    "tazria_metzora": "תזריע–מצֹרע",
    "achrei_mot_kedoshim": "אחרי מות–קדֹשים",
    "behar_bechukotai": "בהר–בחֻקֹתי",
    "chukat_balak": "חֻקת–בלק",
    "matot_masei": "מטות–מסעי",
    "nitzavim_vayeilech": "נִצבים–וילך",
}

# (MAM Hebrew name, hebcal name, opensiddur slug) for each pair, in the shared table's order.
COMBINED_PARSHIYOT: tuple[tuple[str, str, str], ...] = tuple(
    (_COMBINED_HEBREW[slug], hebcal, slug) for hebcal, slug in _COMBINED_HEBCAL
)

_ORDER = [slug for _, _, slug in PARSHA_NAMES]

# The two parshiyot each pair joins. The first is the earlier of the two in the annual order
# and the second follows it directly, so only the pair's slug has to be given: both members
# are read off it. Nothing else in the table is composed from a slug, but here the slugs are
# the join of the two members by construction.
PAIR_MEMBERS: dict[str, tuple[str, str]] = {}
for _hebrew, _hebcal, _slug in COMBINED_PARSHIYOT:
    _first = HEBCAL_TO_SLUG[_hebcal.split("-", 1)[0]]
    PAIR_MEMBERS[_slug] = (_first, _ORDER[_ORDER.index(_first) + 1])

# The pair a parshah belongs to, for the fourteen that have one. Every other parshah is absent.
PAIR_FOR_MEMBER: dict[str, str] = {
    member: pair for pair, members in PAIR_MEMBERS.items() for member in members
}

SLUG_TO_HEBREW = dict(SLUG_TO_HEBREW)
SLUG_TO_HEBREW.update({slug: hebrew for hebrew, _, slug in COMBINED_PARSHIYOT})

_PAIR_BY_SKELETON = {
    normalize_hebrew(hebrew): slug for hebrew, _, slug in COMBINED_PARSHIYOT
}


def slug_for_combined_hebrew(hebrew: str) -> str:
    """The slug for a *pair* named in Hebrew, e.g. ויקהל–פקודי."""
    slug = _PAIR_BY_SKELETON.get(normalize_hebrew(hebrew))
    if slug is None:
        raise KeyError(f"Unknown combined parshah name: {hebrew!r}")
    return slug
