# -*- coding: utf-8 -*-
"""Write the English project. Same URNs as the Hebrew, which is what aligns them."""
import argparse
import sys
from .common import set_project_directory
from .common import PROJECT_EN, PRAYER, SIDDUR, FRONT, document, write, cond, endcond, feature, SERVICE, AGG
from .front import SECTIONS, front_block, section_body
from .index import index
from .en_prayers import PRAYERS
from . import build_he

U, S = PRAYER, SIDDUR

BY_NAME = {p["name"]: p for p in PRAYERS}


def unit_body():
    lines = [f'      <tei:div corresp="{S}chol/shacharit/amidah">', build_he.declaration()]
    lines.append('        <tei:head xml:lang="en">SHEMONEH ESREH</tei:head>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Shemoneh Esreh is recited in silent devotion while standing, facing east.</tei:note>')
    lines.append('        <tei:note type="instruction" xml:lang="en">The Reader repeats the Shemoneh Esreh aloud when a minyan holds service.</tei:note>')
    for name in build_he.ORDER:
        if name == "amidah_qedushah":
            lines.append('        <tei:head xml:lang="en">KEDUSHAH</tei:head>')
        lines.append(f'        <j:transclude type="external" target="{BY_NAME[name]["urn"]}"/>')
    lines.append(cond("cond_unit_hallel",
                      note="Hallel (page 566) is recited here on Rosh Ḥodesh, Ḥol ha-Mo‘ed and Ḥanukkah.",
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
    write(PROJECT_EN, "chol_shacharit_amidah", document(
        body=unit_body(), lang="en",
        title_he="תְּפִלַּת הָעֲמִידָה לְשַׁחֲרִית בְּחוֹל",
        title_en="The weekday morning Amidah",
        urn=f"{S}chol/shacharit/amidah", project=PROJECT_EN, first=82, last=98)); n += 1
    for p in PRAYERS:
        write(PROJECT_EN, p["name"], document(
            body=p["body"], lang="en", title_he="", title_en=p["title"],
            urn=p["urn"], project=PROJECT_EN, first=p["first"], last=p["last"])); n += 1
    print(f"{n} files")


if __name__ == "__main__":
    sys.exit(main())
