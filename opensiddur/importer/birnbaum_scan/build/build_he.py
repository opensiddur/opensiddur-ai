# -*- coding: utf-8 -*-
"""Write the Hebrew project: one file per prayer, a unit file, and an index."""
import argparse
import sys
from .common import set_project_directory
from .common import (PROJECT_HE, PRAYER, SIDDUR, document, write, pb, cond, endcond,
                    feature, SERVICE, AGG)
from .front import SECTIONS, front_block, section_body
from .index import index
from .he_prayers import PRAYERS

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


ORDER = ["amidah_adonai_sefatai", "amidah_avot", "amidah_gevurot", "amidah_qedushah",
         "amidah_qedushat_hashem", "amidah_binah", "amidah_teshuvah", "amidah_selichah",
         "amidah_geulah", "amidah_refuah", "amidah_shanim", "amidah_qibbutz_galuyot",
         "amidah_mishpat", "amidah_minim", "amidah_tzadiqim", "amidah_yerushalayim",
         "amidah_david", "amidah_tefilah", "amidah_avodah", "amidah_hodaah",
         "amidah_birkat_kohanim", "amidah_shalom", "amidah_elohai_netzor",
         "amidah_yehi_ratzon"]

BY_NAME = {p["name"]: p for p in PRAYERS}


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
    written.append(write(PROJECT_HE, "chol_shacharit_amidah", document(
        body=unit_body(), lang="he",
        title_he="תְּפִלַּת הָעֲמִידָה לְשַׁחֲרִית בְּחוֹל",
        title_en="The weekday morning Amidah",
        urn=f"{S}chol/shacharit/amidah", project=PROJECT_HE, first=81, last=97)))
    for p in PRAYERS:
        written.append(write(PROJECT_HE, p["name"], document(
            body=p["body"], lang="he", title_he=p["title"], title_en="",
            urn=p["urn"], project=PROJECT_HE, first=p["first"], last=p["last"])))
    print(f"{len(written)} files")
    for w in written:
        print(" ", w.name)


if __name__ == "__main__":
    sys.exit(main())
