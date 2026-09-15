# -*- coding: utf-8 -*-
"""Check the authored text against the reading, page by page and word for word.

`compare` runs in one direction only: it asks how far the Wikisource transcription stands
from the reading. It says nothing about whether the TEI actually carries what the reading
records. Those are different questions, and the second one has been wrong twice:

- Printed page 21 lost its last line from the reading and from the transcription at once,
  so `compare` reported nothing and every downstream check stayed green.
- The first draft of `he_akedah` had six words typed from memory rather than lifted from
  the reading -- a `,` for a `.`, a dropped clause of eight words, an added `בְּתוֹרָתֶֽךָ`.
  Nothing in the schema, the registry or the reference database can see any of that.

So this asks the other question: **for each printed page, do the words the generator emits
on that page equal the words the reading records for it?** It is a diff, not a tally, and
a single wrong vowel fails it.

Why page by page rather than end to end: a first attempt concatenated the authored files in
*filename* order and reported 380 words missing that were in fact present, in a different
place. Ordering by printed page is what makes the answer mean anything -- and it also
localises a failure to the page whose image can settle it.

Transclusion is the one thing that has to be declared. A unit that transcludes a text
realised by another unit emits nothing for it, so those words are on the page in the print
and absent from this unit's files. :data:`TRANSCLUDED` names them, which is also a standing
record of what the consolidation still owes.
"""
from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path

#: Words a unit's pages carry that the unit itself does not realise, because another unit
#: realises them first and `refdb` refuses one text URN mapped twice in a project.
#:
#: Every entry here is a consolidation debt, not a design: the children's page is never the
#: canonical place for a text the rest of the book also says. See `he_akedah`'s docstring.
TRANSCLUDED: dict[int, tuple[str, ...]] = {
    # Barukh Shem, after the tefillin blessing -- realised by the children's unit.
    7: ("בָּרוּךְ שֵׁם כְּבוֹד מַלְכוּתוֹ לְעוֹלָם וָעֶד.",),
    # The washing blessing -- likewise.
    13: (
        "בָּרוּךְ אַתָּה, יְיָ אֱלֹהֵֽינוּ, מֶֽלֶךְ הָעוֹלָם, אֲשֶׁר קִדְּשָֽׁנוּ "
        "בְּמִצְוֺתָיו וְצִוָּֽנוּ עַל נְטִילַת יָדָֽיִם.",
    ),
    25: (
        "שְׁמַע יִשְׂרָאֵל, יְיָ אֱלֹהֵֽינוּ, יְיָ אֶחָד.",
        "בָּרוּךְ שֵׁם כְּבוֹד מַלְכוּתוֹ לְעוֹלָם וָעֶד.",
    ),
}

_TAG = re.compile(r"<[^>]+>")
_PB = re.compile(r'<tei:pb\s+n="([^"]+)"[^>]*/>')


def pages_of(body: str, first: int) -> dict[int, list[str]]:
    """The words a prayer puts on each printed page.

    The text before the first `tei:pb` is on `first`; each `tei:pb n="N"` moves what
    follows to page N. Markup is removed leaving a space, never nothing -- deleting a tag
    between two words joins them into one token, which is the same mistake `strip_markup`
    had to be corrected for.
    """
    out: dict[int, list[str]] = {}
    page = first
    position = 0
    for match in _PB.finditer(body):
        out.setdefault(page, []).extend(_TAG.sub(" ", body[position:match.start()]).split())
        page = int(match.group(1))
        position = match.end()
    out.setdefault(page, []).extend(_TAG.sub(" ", body[position:]).split())
    return out


def authored(prayers) -> dict[int, list[str]]:
    """Every prayer's words, gathered by the printed page they fall on.

    The prayers are taken in the order the content modules declare them, which is the order
    the print sets them. That is an assumption the diff itself checks: get the order wrong
    and the words come out in the wrong sequence on some page and the diff says so.
    """
    out: dict[int, list[str]] = {}
    for prayer in prayers:
        for page, words in pages_of(prayer["body"], prayer["first"]).items():
            out.setdefault(page, []).extend(words)
    return out


def read(directory: Path, page: int) -> list[str]:
    return (directory / f"{page}.txt").read_text(encoding="utf-8").split()


def check(prayers, directory: Path, pages) -> dict[int, list[str]]:
    """Per page, the unified diff of reading against authored. Empty means they agree."""
    emitted = authored(prayers)
    report: dict[int, list[str]] = {}
    for page in pages:
        expected = read(directory, page)
        for phrase in TRANSCLUDED.get(page, ()):
            words = phrase.split()
            index = next(
                (i for i in range(len(expected)) if expected[i:i + len(words)] == words),
                None,
            )
            if index is None:
                report[page] = [f"declared as transcluded but not in the reading: {phrase}"]
                break
            del expected[index:index + len(words)]
        else:
            diff = list(difflib.unified_diff(
                expected, emitted.get(page, []), "reading", "authored", lineterm="", n=1))
            if diff:
                report[page] = diff
    return report


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", type=int, nargs="+", help="Printed pages to check.")
    parser.add_argument(
        "--readings",
        type=Path,
        required=True,
        help="Directory of `hebrew/{page}.txt` readings.",
    )
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="A content module to take PRAYERS from, e.g. he_akedah. Repeatable.",
    )
    args = parser.parse_args(argv)

    import importlib

    prayers = []
    for name in args.module:
        prayers += importlib.import_module(
            f"opensiddur.importer.birnbaum_scan.build.{name}").PRAYERS

    report = check(prayers, args.readings, args.pages)
    for page in args.pages:
        if page in report:
            print(f"### page {page}")
            print("\n".join(report[page]))
    if report:
        print(f"{len(report)} of {len(args.pages)} pages differ")
        return 1
    print(f"{len(args.pages)} pages: the authored text is the reading, word for word")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
