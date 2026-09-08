# -*- coding: utf-8 -*-
"""Write the English project. Same URNs as the Hebrew, which is what aligns them."""
import argparse
import sys
from .common import set_project_directory
from .common import PROJECT_EN, PRAYER, SIDDUR, document, write, cond, endcond, feature, SERVICE, AGG
from .en_prayers import PRAYERS
from . import build_he

U, S = PRAYER, SIDDUR

INDEX = build_he.INDEX.replace(f'@{build_he.PROJECT_HE}', f'@{PROJECT_EN}').replace(
    '<tei:edition>Read directly from the scanned 1949 printing, page by page. Not derived from any transcription of it.</tei:edition>',
    '<tei:edition>Birnbaum’s own English, read from the facing pages of the scanned 1949 printing</tei:edition>').replace(
    'xml:lang="he">\n  <tei:teiHeader', 'xml:lang="en">\n  <tei:teiHeader')
# The English is Birnbaum's own translation, and that is said here, beside the citation of
# the book it was read out of. It is not a respStmt: a respStmt records who *digitised* a
# text, and he is the author of the one being digitised, recorded as a source.
_SCAN_NOTE = '          <tei:note xml:lang="en">The scan cited here is'
INDEX = INDEX.replace(
    _SCAN_NOTE,
    '          <tei:note xml:lang="en">The English of this project is Birnbaum’s own '
    'translation, printed on the pages facing the Hebrew.</tei:note>\n'
    + _SCAN_NOTE, 1)

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
    write(PROJECT_EN, "index", INDEX); n += 1
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
