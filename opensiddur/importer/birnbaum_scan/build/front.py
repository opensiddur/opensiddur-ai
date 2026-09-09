# -*- coding: utf-8 -*-
"""The front matter of the 1949 print, leaves 1-25 of the scan.

The words are not here. They are in ``sourcetexts``, under
``sources/birnbaum_siddur/scan_reading/front/``, one well-formed XML fragment per
section, read off the scan and committed there because nothing regenerates a reading.
This module says which leaf holds what, which project realises which section, and how a
leaf the book does not number is designated.

**Designations.** The book prints Roman numerals only from leaf 11 (``IX``) to leaf 25
(``XXIII``). That fixes leaf 3 as ``I``, so leaves 3-10 are designated ``[I]``-``[VIII]``
-- brackets marking a number the book implies rather than prints. Leaves 1 and 2 precede
the Roman sequence entirely and are designated ``[1]`` and ``[2]``.

**Sides.** The book's front matter divides by language exactly as its body does: the
Hebrew title leaf is leaf 2, the English title leaf is leaves 3-4, and the table of
contents is set twice, Hebrew on leaf 6 and English on leaf 7. Each project transcribes
its own leaves, so each project's foliation skips the other's -- the same thing the
Amidah already does with 81/82, 83/84.

**Title pages cannot be transcluded.** ``tei:titlePage`` is in ``model.frontPart``, which
only ``tei:front`` admits; a transcluded section arrives inside a ``tei:div``, which does
not. So the two title leaves are written into each index's ``tei:front`` literally, and
carry ``front:title_page``/``front:copyright`` on themselves so the two sides still
declare the correspondence. Only the prose sections are transcluded.
"""
from pathlib import Path

from .common import FRONT, FRONT_SIGIL, PROJECT_EN, PROJECT_HE, pb

#: The committed reading. Outside this repository, in the sourcetexts submodule.
FRAGMENTS = (Path(__file__).resolve().parents[4] / "sourcetexts" / "sources"
             / "birnbaum_siddur" / "scan_reading" / "front")

#: Leaf -> the designation the book prints on it, or implies. See the module docstring.
DESIGNATION = {1: "[1]", 2: "[2]"}
DESIGNATION.update({leaf: f"[{r}]" for leaf, r in enumerate(
    ("I", "II", "III", "IV", "V", "VI", "VII", "VIII"), start=3)})
DESIGNATION.update({leaf: r for leaf, r in enumerate(
    ("IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII",
     "XIX", "XX", "XXI", "XXII", "XXIII"), start=11)})

#: Sections written as their own file and reached by transclusion. `leaf` is where the
#: section starts; `first`/`last` are the designations its pages carry.
SECTIONS = (
    dict(name="front_dedication", slug="dedication", fragment="dedication.xml",
         leaf=5, first="[III]", last="[III]", title="Dedication"),
    dict(name="front_acknowledgements", slug="acknowledgements",
         fragment="acknowledgments.xml",
         leaf=9, first="[VII]", last="[VII]", title="Acknowledgments"),
    dict(name="front_introduction", slug="introduction", fragment="introduction.xml",
         leaf=11, first="IX", last="XXIII", title="Introduction"),
)

#: Title leaves, written into a project's own ``tei:front``. Keyed by project.
TITLE_LEAVES = {
    PROJECT_HE: ((2, "title_page_he.xml"),),
    PROJECT_EN: ((3, "title_page_en.xml"), (4, "copyright.xml")),
}

#: Leaves that carry no section in this project and so contribute a bare page break:
#: the blanks, which belong to no language, and this project's half of the contents,
#: which is deferred -- it indexes some 600 printed pages the projects do not yet hold.
BARE = {PROJECT_HE: (1, 6, 8, 10), PROJECT_EN: (1, 7, 8, 10)}


def fragment(name: str) -> str:
    """One committed reading, indented to sit inside ``tei:front``."""
    text = (FRAGMENTS / name).read_text(encoding="utf-8").rstrip("\n")
    return "\n".join("      " + line if line else line for line in text.split("\n"))


def section_body(section) -> str:
    """A transcluded section's document body: its ``tei:div``, as read."""
    text = (FRAGMENTS / section["fragment"]).read_text(encoding="utf-8").rstrip("\n")
    return "\n".join("      " + line if line else line for line in text.split("\n"))


def front_block(project: str) -> str:
    """The ``tei:front`` for a project's index, leaf by leaf in the book's order.

    Every leaf appears exactly once, as a title page written out, a transclusion of the
    section that starts there, or a bare page break -- so the foliation of each side runs
    unbroken through the front matter.
    """
    titles = dict(TITLE_LEAVES[project])
    starts = {s["leaf"]: s for s in SECTIONS}
    lines = ["    <tei:front>"]
    for leaf in sorted(set(titles) | set(starts) | set(BARE[project])):
        if leaf in titles:
            lines.append(fragment(titles[leaf]))
        elif leaf in starts:
            lines.append('      <j:transclude type="external" '
                         f'target="{FRONT}{starts[leaf]["slug"]}"/>')
        else:
            lines.append("      " + pb(f"s{leaf}", sigil=FRONT_SIGIL,
                                       n=DESIGNATION[leaf]))
    lines.append("    </tei:front>")
    return "\n".join(lines)
