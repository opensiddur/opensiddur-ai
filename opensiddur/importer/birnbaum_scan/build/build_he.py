# -*- coding: utf-8 -*-
"""Write the Hebrew project: one file per prayer, a unit file per unit, and an index."""
import argparse
import sys
from .common import set_project_directory
from .common import (PROJECT_EN, PROJECT_HE, PRAYER, SIDDUR, document, write, cond,
                    endcond, feature, SERVICE, AGG)
from .front import SECTIONS, front_block, section_body
from .index import index
from .he_prayers import PRAYERS as AMIDAH_PRAYERS
from .he_yeladim import PRAYERS as YELADIM_PRAYERS

#: Every prayer file this project writes, both units.
PRAYERS = AMIDAH_PRAYERS + YELADIM_PRAYERS

U, S = PRAYER, SIDDUR

# The unit declares its service and that it is a weekday, and declares EVERY service --
# an undeclared false is undefined, and undefined keeps the text, so declaring shaharit
# alone would leave every other service's readings standing. It declares NOTHING about
# the date, so the rain seasons, the Ten Days, Ya'aleh v'Yavo and עננו stay open.
def declaration():
    svc = "\n".join(
        f'          <tei:f name="{n}">\n            <tei:binary value="{"true" if n=="shaharit" else "false"}"/>\n          </tei:f>'
        for n in ("shaharit", "minha", "maariv", "musaf", "neila", "slihot"))
    agg = "\n".join(
        f'          <tei:f name="{n}">\n            <tei:binary value="false"/>\n          </tei:f>'
        for n in ("shabbat", "yom-tov"))
    return (f'        <j:declare xml:id="unit_service">\n'
            f'          <tei:fs type="{SERVICE}">\n{svc}\n          </tei:fs>\n'
            f'          <tei:fs type="{AGG}">\n{agg}\n          </tei:fs>\n'
            f'        </j:declare>')


# Shaḥarith li-Yladim is not the weekday Amidah's kind of unit: a child says it every
# morning, festivals and Sabbaths included, so it declares the service and says NOTHING
# about the date or the holiday aggregates. The Amidah declares those false because it is
# specifically the weekday Amidah; repeating that here would file this page under weekdays.
# There is no j:conditional anywhere in the unit -- nothing on the page depends on season,
# occasion, service or minyan -- so the declaration governs no conditional text. It is kept
# as the unit's standing claim about when it is said, for whatever later transcludes it.
def declaration_yeladim():
    svc = "\n".join(
        f'          <tei:f name="{n}">\n            <tei:binary value="{"true" if n=="shaharit" else "false"}"/>\n          </tei:f>'
        for n in ("shaharit", "minha", "maariv", "musaf", "neila", "slihot"))
    return (f'        <j:declare xml:id="unit_service">\n'
            f'          <tei:fs type="{SERVICE}">\n{svc}\n          </tei:fs>\n'
            f'        </j:declare>')


#: The rubrics of printed page 1, in the order the page sets them, each naming the
#: prayers it governs. Birnbaum sets them in ENGLISH on the Hebrew page as well as on the
#: English one, so both projects emit them identically -- the same practice as the Amidah.
#: "When dressed:" governs two prayers, which is why this is a table and not a field on
#: each prayer.
YELADIM_RUBRICS = (
    ("Upon awakening in the morning:", ["yeladim_modeh_ani"]),
    ("When washing the hands:", ["yeladim_netilat_yadayim"]),
    ("When putting on the <tei:foreign xml:lang=\"he-Latn\">arba kanfoth</tei:foreign>:",
     ["yeladim_tzitzit"]),
    ("When dressed:", ["yeladim_torah_tziva", "yeladim_elohai_netzor"]),
)


def unit_body_yeladim(head, by_name):
    """The children's unit.

    `head` differs between the projects -- see YELADIM_HEAD -- and `by_name` is the
    calling project's own prayer table, since each project transcludes its own files.
    """
    lines = [f'      <tei:div corresp="{S}all/shacharit/yeladim">', declaration_yeladim(), head]
    for note, names in YELADIM_RUBRICS:
        lines.append(f'        <tei:note type="instruction" xml:lang="en">{note}</tei:note>')
        for name in names:
            lines.append(f'        <j:transclude type="external" target="{by_name[name]["urn"]}"/>')
    lines.append('        <j:endDeclare target="#unit_service"/>')
    lines.append("      </tei:div>")
    return "\n".join(lines)


#: The book's running order: the children's page is printed first, and comes first here.
#: Each entry is what write() needs to put one unit file on disk. Both projects build
#: their units from this one function, so a unit cannot exist on one side only.
def units(project, pages, by_name, amidah_body):
    """`pages` maps a unit key to its (first, last) printed pages in THIS project.

    The two projects foliate differently -- the Hebrew is on 1 and 81-97, the English on
    2 and 82-98 -- which is the same thing the Amidah already does across an opening.
    """
    return (
        dict(name="all_shacharit_yeladim",
             body=unit_body_yeladim(YELADIM_HEAD[project], by_name),
             title_he="שַׁחֲרִית לִילָדִים", title_en="Morning prayer for children",
             urn=f"{S}all/shacharit/yeladim", pages=pages["yeladim"]),
        dict(name="chol_shacharit_amidah", body=amidah_body,
             title_he="תְּפִלַּת הָעֲמִידָה לְשַׁחֲרִית בְּחוֹל",
             title_en="The weekday morning Amidah",
             urn=f"{S}chol/shacharit/amidah", pages=pages["amidah"]),
    )


#: The one place the two projects' unit files genuinely differ. The Amidah's three
#: headings are English on both sides because that is what the print does; this unit's
#: heading is Hebrew on the Hebrew page and English on the English one.
YELADIM_HEAD = {
    PROJECT_HE: '        <tei:head xml:lang="he">שַׁחֲרִית לִילָדִים</tei:head>',
    PROJECT_EN: '        <tei:head xml:lang="en">MORNING PRAYER FOR CHILDREN</tei:head>',
}


ORDER = ["amidah_adonai_sefatai", "amidah_avot", "amidah_gevurot", "amidah_qedushah",
         "amidah_qedushat_hashem", "amidah_binah", "amidah_teshuvah", "amidah_selichah",
         "amidah_geulah", "amidah_refuah", "amidah_shanim", "amidah_qibbutz_galuyot",
         "amidah_mishpat", "amidah_minim", "amidah_tzadiqim", "amidah_yerushalayim",
         "amidah_david", "amidah_tefilah", "amidah_avodah", "amidah_hodaah",
         "amidah_birkat_kohanim", "amidah_shalom", "amidah_elohai_netzor",
         "amidah_yehi_ratzon"]

BY_NAME = {p["name"]: p for p in PRAYERS}

#: Which printed pages each unit spans, on the Hebrew side of the opening.
HE_UNIT_PAGES = {"yeladim": (1, 1), "amidah": (81, 97)}


def unit_body():
    lines = [f'      <tei:div corresp="{S}chol/shacharit/amidah">', declaration()]
    lines.append('        <tei:head xml:lang="en">SHEMONEH ESREH</tei:head>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Shemoneh Esreh is recited in silent devotion while standing, facing east.</tei:note>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Reader repeats the Shemoneh Esreh aloud when a minyan holds service.</tei:note>')
    for name in ORDER:
        if name == "amidah_qedushah":
            lines.append('        <tei:head xml:lang="en">KEDUSHAH</tei:head>')
        lines.append(f'        <j:transclude type="external" target="{BY_NAME[name]["urn"]}"/>')
    # A cross-reference rubric: it names a page in this book and governs nothing here.
    lines.append(cond("cond_unit_hallel",
                      note="Hallel (page 565) is recited here on Rosh Ḥodesh, Ḥol ha-Mo‘ed and Ḥanukkah.",
                      fs="\n".join(["          <j:any>",
                                    feature("opensiddur:holiday", "rosh-hodesh", '<tei:numeric value="1" max="2"/>'),
                                    feature(AGG, "chol-hamoed"),
                                    feature("opensiddur:holiday", "hanukkah", '<tei:numeric value="1" max="8"/>'),
                                    "          </j:any>"])))
    lines.append(endcond("cond_unit_hallel"))
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
    written = []
    written.append(write(PROJECT_HE, "index", index(
        project=PROJECT_HE, lang="he", front=front_block(PROJECT_HE))))
    for unit in units(PROJECT_HE, HE_UNIT_PAGES, BY_NAME, unit_body()):
        written.append(write(PROJECT_HE, unit["name"], document(
            body=unit["body"], lang="he", title_he=unit["title_he"],
            title_en=unit["title_en"], urn=unit["urn"], project=PROJECT_HE,
            first=unit["pages"][0], last=unit["pages"][1])))
    for p in PRAYERS:
        written.append(write(PROJECT_HE, p["name"], document(
            body=p["body"], lang="he", title_he=p["title"], title_en="",
            urn=p["urn"], project=PROJECT_HE, first=p["first"], last=p["last"])))
    print(f"{len(written)} files")
    for w in written:
        print(" ", w.name)


if __name__ == "__main__":
    sys.exit(main())
