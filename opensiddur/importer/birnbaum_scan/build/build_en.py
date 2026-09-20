# -*- coding: utf-8 -*-
"""Write the English project. Same URNs as the Hebrew, which is what aligns them."""
import argparse
import sys
from .common import set_project_directory
from .common import PROJECT_EN, PRAYER, SIDDUR, FRONT, NOTES, document, standoff_document, write, cond, endcond, feature, SERVICE, AGG
from .front import SECTIONS, front_block, section_body
from .index import index
from .en_prayers import PRAYERS as AMIDAH_PRAYERS
from .en_yeladim import PRAYERS as YELADIM_PRAYERS
from .en_tallith import PRAYERS as TALLITH_PRAYERS
from .en_tefillin import PRAYERS as TEFILLIN_PRAYERS
from .en_poems import PRAYERS as POEM_PRAYERS
from .en_berakhot import PRAYERS as BERAKHOT_PRAYERS
from .en_akedah import PRAYERS as AKEDAH_PRAYERS
from .en_korbanot import PRAYERS as KORBANOT_PRAYERS
from .en_ishmael import PRAYERS as ISHMAEL_PRAYERS
from .en_pesukei import PRAYERS as PESUKEI_PRAYERS
from .shema import prayers as shema_prayers
SHEMA_PRAYERS = shema_prayers("en")
from .avinu_malkenu import prayers as avinu_prayers
AVINU_PRAYERS = avinu_prayers("en")
from .tachanun import prayers as tachanun_prayers
TACHANUN_PRAYERS = tachanun_prayers("en")
from .torah import prayers as torah_prayers
TORAH_PRAYERS = torah_prayers("en")
from . import build_he
from . import notes as apparatus
from .notes_pesukei import PESUKEI_NOTES
from .notes_shema import SHEMA_NOTES

#: Every prayer file this project writes, both units.
PRAYERS = (AMIDAH_PRAYERS + YELADIM_PRAYERS + TALLITH_PRAYERS
           + TEFILLIN_PRAYERS + POEM_PRAYERS + BERAKHOT_PRAYERS
           + AKEDAH_PRAYERS + KORBANOT_PRAYERS + ISHMAEL_PRAYERS + PESUKEI_PRAYERS + SHEMA_PRAYERS + AVINU_PRAYERS + TACHANUN_PRAYERS + TORAH_PRAYERS)
from .conclusion import prayers as conclusion_prayers
PRAYERS += conclusion_prayers("en", PRAYERS)
from .shacharit_end import prayers as final_prayers
PRAYERS += final_prayers("en")


U, S = PRAYER, SIDDUR

BY_NAME = {p["name"]: p for p in PRAYERS}

#: Which printed pages each unit spans, on the English side of the opening.
EN_UNIT_PAGES = {"yeladim": (2, 2), "birchot": (4, 48), "opening": (50, 52), "pesukei": (52, 70), "shema": (72, 82), "amidah": (82, 98), "avinu": (98, 102)}

#: Birnbaum's footnotes, one apparatus file per unit. They are written here and not in
#: `build_he` because the commentary is English prose, as his introduction is: the
#: English side realises it and the Hebrew reaches it by resolution. The pages named
#: are the pages the notes were read from, which for the commentary are the *Hebrew*
#: pages -- that is where the print sets it.
from .avinu_malkenu import NOTES as AVINU_NOTES

from .notes_tachanun import NOTES as TACHANUN_NOTES

from .notes_torah import NOTES as TORAH_NOTES

from .notes_conclusion import make_notes
from .conclusion import ANCHORS
CONCLUSION_NOTES = make_notes(ANCHORS)

from .shacharit_end import NOTES as FINAL_NOTES

APPARATUS = {
    "notes_shacharit_end": dict(entries=FINAL_NOTES, slug="birnbaum_1949/shacharit_end",
                               title="Notes on the final morning readings", first=151, last=156),
    "notes_conclusion": dict(entries=CONCLUSION_NOTES, slug="birnbaum_1949/conclusion",
                             title="Notes on the conclusion and psalms", first=128, last=152),
    "notes_torah": dict(entries=TORAH_NOTES, slug="birnbaum_1949/torah",
                        title="Notes on the weekday Torah service", first=119, last=128),
    "notes_tachanun": dict(entries=TACHANUN_NOTES, slug="birnbaum_1949/tachanun",
                           title="Notes on Tachanun", first=103, last=118),
    "notes_avinu_malkenu": dict(entries=AVINU_NOTES, slug="birnbaum_1949/avinu_malkenu",
                                title="Notes on Avinu Malkenu", first=98, last=100),
    "notes_shema": dict(entries=SHEMA_NOTES, slug="birnbaum_1949/shema",
                        title="Notes on Shema and its blessings", first=71, last=82),
    "notes_pesukei": dict(entries=PESUKEI_NOTES, slug="birnbaum_1949/pesukei_dezimra",
                          title="Notes on the opening of the morning service", first=49, last=70),
    "notes_yeladim": dict(entries=apparatus.YELADIM_NOTES, slug="birnbaum_1949/yeladim",
                          title="Notes on Shaḥarith li-Yladim", first=1, last=1),
    "notes_birchot": dict(entries=apparatus.BIRCHOT_NOTES,
                          slug="birnbaum_1949/birchot_hashachar",
                          title="Notes on Birkhoth ha-Shaḥar", first=3, last=47),
    "notes_amidah": dict(entries=apparatus.AMIDAH_NOTES, slug="birnbaum_1949/amidah",
                         title="Notes on the weekday morning Amidah", first=81, last=98),
}


def unit_body():
    lines = [f'      <tei:div corresp="{S}chol/shacharit/amidah">', build_he.declaration()]
    lines.append('        <tei:head xml:lang="en">SHEMONEH ESREH</tei:head>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Shemoneh Esreh is recited in silent devotion while standing, facing east.</tei:note>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Reader repeats the Shemoneh Esreh aloud when a minyan holds service.</tei:note>')
    for name in build_he.ORDER:
        if name == "amidah_qedushah":
            lines.append('        <tei:head xml:lang="en">KEDUSHAH</tei:head>')
        lines.append(f'        <j:transclude type="external" target="{BY_NAME[name]["urn"]}"/>')
    lines.append('        <tei:note type="instruction" xml:lang="en">Hallel (page 566) is recited here on Rosh Ḥodesh, Ḥol ha-Mo‘ed and Ḥanukkah.</tei:note>')
    lines.append('        <tei:div>')
    lines.append('          <tei:head xml:lang="en">ABRIDGED SHEMONEH ESREH</tei:head>')
    lines.append('          <tei:note type="instruction" xml:lang="en">Used when one is unable to recite the complete Amidah</tei:note>')
    lines.append(f'          <j:transclude type="external" target="{BY_NAME["amidah_havinenu"]["urn"]}"/>')
    lines.append('        </tei:div>')
    lines.append('        <j:endDeclare target="#unit_service"/>')
    lines.append("      </tei:div>")
    return "\n".join(lines)


def main(argv=None):
    parsed = argparse.ArgumentParser(description=__doc__)
    parsed.add_argument(
        "--project-directory",
        help="Where to write the TEI. Defaults to the opensiddur-projects submodule; "
             "point it at a worktree to write there instead.",
    )
    args = parsed.parse_args(argv)
    if args.project_directory:
        set_project_directory(args.project_directory)
    n = 0
    write(PROJECT_EN, "index", index(
        project=PROJECT_EN, lang="en", front=front_block(PROJECT_EN))); n += 1
    # The prose front matter is realised here and transcluded by both indexes:
    # Birnbaum wrote it in English and the print has no Hebrew counterpart.
    for s in SECTIONS:
        write(PROJECT_EN, s["name"], document(
            body=section_body(s), lang="en", title_he="", title_en=s["title"],
            urn=FRONT + s["slug"], project=PROJECT_EN,
            first=s["first"], last=s["last"])); n += 1
    for unit in build_he.units(PROJECT_EN, EN_UNIT_PAGES, BY_NAME, unit_body()):
        write(PROJECT_EN, unit["name"], document(
            body=unit["body"], lang="en", title_he=unit["title_he"],
            title_en=unit["title_en"], urn=unit["urn"], project=PROJECT_EN,
            first=unit["pages"][0], last=unit["pages"][1])); n += 1
    for name, a in APPARATUS.items():
        if not a["entries"]:
            continue
        write(PROJECT_EN, name, standoff_document(
            notes=apparatus.standoff(a["entries"]), lang="en", title_he="",
            title_en=a["title"], urn=NOTES + a["slug"], project=PROJECT_EN,
            first=a["first"], last=a["last"])); n += 1
    for p in PRAYERS:
        write(PROJECT_EN, p["name"], document(
            body=p["body"], lang="en", title_he="", title_en=p["title"],
            urn=p["urn"], project=PROJECT_EN, first=p["first"], last=p["last"], printings=p.get("printings", ()))); n += 1
    print(f"{n} files")


if __name__ == "__main__":
    sys.exit(main())
