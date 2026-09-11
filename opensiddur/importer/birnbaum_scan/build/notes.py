# -*- coding: utf-8 -*-
"""Birnbaum's own footnotes, as a standoff apparatus.

The print carries two apparatuses, and they are different things:

*Commentary* sits at the foot of the Hebrew page, keyed by a Hebrew catchword set in
bold, and is set across the opening -- a note begun under a Hebrew page finishes under
the facing English one. Birnbaum describes the keying himself in his introduction: each
note begins with a Hebrew catchword so that a reader can find the explanation he seeks.

*Scripture citations* are numbered, keyed to superscript numerals, and are printed on the
English pages only -- again his own statement, and confirmed by every page read so far.

Both are `tei:note` in one `tei:standOff`, told apart by `@type`. A commentary note
carries the catchword in `tei:label`; a citation carries the printed numeral in `@n`.

Two decisions worth stating, because neither is obvious:

**The apparatus is realised in the English project only.** The commentary is English
prose about Hebrew words, like Birnbaum's introduction, and the same reasoning applies:
English-only material is realised on the English side and the Hebrew reaches it by
resolution rather than by duplication. What is given up is that the commentary begins
physically under the Hebrew page in the print and will not in the rendered PDF.

**A note carries no URN of its own.** `urn:x-opensiddur:notes:` exists for swapping one
edition's apparatus for another's, and there is exactly one Birnbaum apparatus. A note is
not a text: it is addressed by what it annotates, and `@target` says that already.

The printed numeral in `@n` is evidence, not an instruction to the renderer. Birnbaum
restarts at 1 on every page; a PDF repaginates, so the renderer draws its own series.
"""
from .common import PRAYER

#: What the apparatus is attached to, per unit. `target` is a `@corresp` URN that the
#: text already carries -- never an `#id`, which `refdb` resolves only inside one file.
YELADIM_NOTES = [
    dict(
        kind="commentary",
        target=PRAYER + "torah_tziva/morasha",
        lemma="תורה צוה לנו",
        text=("(Deuteronomy 33:4) is the first Hebrew verse which a father is directed "
              "to teach his child at a very early age (Sukkah 42a; Maimonides, "
              "<tei:hi rend=\"italic\">Talmud Torah</tei:hi> 1:6). Although the child is "
              "held to be free from religious duties, his father is required to make him "
              "amenable to them."),
    ),
]


def note(entry: dict, *, indent: int = 4) -> str:
    """One `tei:note` in the apparatus."""
    pad = " " * indent
    attrs = [f'type="{entry["kind"]}"']
    if entry.get("n"):
        attrs.append(f'n="{entry["n"]}"')
    attrs.append(f'target="{entry["target"]}"')
    opening = f'{pad}<tei:note {" ".join(attrs)}>'
    if entry.get("lemma"):
        opening += f'<tei:label xml:lang="he">{entry["lemma"]}</tei:label> '
    return f'{opening}{entry["text"]}</tei:note>'


def standoff(entries: list[dict], *, indent: int = 4) -> str:
    """The body of one apparatus file."""
    return "\n".join(note(e, indent=indent) for e in entries)
