r"""Does a page break ever strand a line or a heading (#198)?

Four things must never happen at a page break:

* a widow: the last line of a paragraph alone at the head of a page;
* an orphan: the first line of a paragraph alone at the foot of one;
* a split heading: a heading, or its translated title, on two pages;
* a stranded heading: a heading at the foot of a page, the text it heads on the next.

Each layout breaks its pages differently -- TeX's page builder over reledmac's lines in a
single stream, the same over reledpar's rows under ``\Columns``, and reledpar's own count
under ``\Pages`` -- so each is typeset and measured on its own. None of it is visible in
the ``.tex``.

Nothing here aims a heading at the foot of a page, which would depend on the fonts. The
documents are a long run of headed sections whose paragraphs cycle through many lengths,
so their edges land at every height on the page and some of them meet a page break
whatever the metrics. Each layout is set a second time with the protection switched off,
which must then go wrong somewhere: otherwise the sweep never reached a page edge and the
clean result would mean nothing.

Every word names itself: ``LP3w7`` is the eighth word of section 3's first paragraph on
the left (or only) side, ``LQ3`` its second paragraph, ``LH3`` its heading and ``LT3`` the
heading's translation.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from opensiddur.exporter.tex.latex import transform_xml_to_tex
from opensiddur.exporter.typography import TypographyConfig

_SECTIONS = 30
# Words in a section's first paragraph; the second has twice as many and five more.
_LENGTHS = (3, 9, 17, 26, 34, 45, 12, 21, 7, 40, 30, 15)
# A section with nothing on the right is set across the page between column blocks
# (#194), as a single stream inside a parallel text.
_UNPAIRED = {4, 11, 19, 26}


def _words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}w{n}" for n in range(count))


def _div(side: str, n: int, length: int, translated: bool) -> str:
    heads = f"<tei:head>{side}H{n}</tei:head>"
    if translated:
        heads += f"<tei:head>{side}T{n}</tei:head>"
    return (f'<tei:div corresp="urn:x-opensiddur:text:t:s{n}">{heads}'
            f"<tei:p>{_words(f'{side}P{n}', length)}</tei:p>"
            f"<tei:p>{_words(f'{side}Q{n}', 2 * length + 5)}</tei:p></tei:div>")


def _document(parallel: bool) -> str:
    sections = []
    for n in range(_SECTIONS):
        left = _LENGTHS[n % len(_LENGTHS)]
        if not parallel:
            sections.append(_div("L", n, left, translated=True))
            continue
        right = (f'<tei:p><tei:milestone unit="prayer-part" '
                 f'corresp="urn:x-opensiddur:text:t:s{n}"/></tei:p>'
                 if n in _UNPAIRED
                 else _div("R", n, _LENGTHS[(n + 5) % len(_LENGTHS)], translated=False))
        sections.append(f"""
    <p:parallel column-order="primary_first">
      <p:parallelItem role="primary" xml:lang="en">{_div("L", n, left, translated=False)}</p:parallelItem>
      <p:parallelItem role="parallel" xml:lang="en">{right}</p:parallelItem>
    </p:parallel>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:p="http://jewishliturgy.org/ns/processing" xml:lang="en">
  <tei:text><tei:body>{"".join(sections)}
  </tei:body></tei:text>
</tei:TEI>"""


# Everything #198 added, switched back off: the stock penalties, no heading kept with
# what follows it, and nothing read off a parallel column. The heading's own lines stay
# bound; the sweep does not need them to show that it reaches the page edges.
_UNPROTECTED = r"""
\clubpenalty=150 \widowpenalty=150
\renewcommand{\OSApplyKeep}{\global\OSKeepNextfalse}
\directlua{if OSkeep then
  OSkeep.line = function() end
  OSkeep.chain = function() tex.setcount("global", "OS@chainlines", 1) end
end}
"""

# Words above this are the running head, if there is one.
_HEAD_BOTTOM = 85.0


def _typeset(parallel: bool, typography: dict, protected: bool = True) -> dict[str, tuple[int, int]]:
    """Each word's (page, rounded yMin)."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "in.xml").write_text(_document(parallel))
        transform_xml_to_tex(
            work / "in.xml", output_file=str(work / "t.tex"),
            typography=TypographyConfig.model_validate(typography),
            project_directory=work,
        )
        if not protected:
            tex = (work / "t.tex").read_text()
            (work / "t.tex").write_text(
                tex.replace(r"\begin{document}", _UNPROTECTED + r"\begin{document}", 1))
        for _ in range(3):  # reledpar pairs and paginates from the earlier passes
            done = subprocess.run(
                ["lualatex", "-interaction=nonstopmode", "t.tex"],
                cwd=work, capture_output=True, text=True,
            )
        if not (work / "t.pdf").exists():
            raise AssertionError(f"lualatex produced no PDF:\n{done.stdout[-2000:]}")
        log = (work / "t.log").read_text(errors="replace")
        if "could not patch" in log:
            raise AssertionError("a reledmac or reledpar patch did not apply")
        errors = re.findall(r"^! .*", log, re.MULTILINE)
        if errors:
            raise AssertionError(f"TeX errors: {errors[:5]}")
        boxes = subprocess.run(
            ["pdftotext", "-bbox", "t.pdf", "-"],
            cwd=work, capture_output=True, text=True,
        ).stdout
    where = {}
    for page, chunk in enumerate(boxes.split("<page ")[1:], 1):
        for y, word in re.findall(
                r'<word xMin="[\d.]+" yMin="([\d.]+)"[^>]*>([^<]*)</word>', chunk):
            if float(y) > _HEAD_BOTTOM:
                where[word] = (page, round(float(y)))
    return where


def _lines(where: dict[str, tuple[int, int]], paragraph: str) -> list[tuple[int, int]]:
    """A paragraph's printed lines, top to bottom, as (page, y)."""
    pattern = re.compile(re.escape(paragraph) + r"w\d+")
    return sorted({at for word, at in where.items() if pattern.fullmatch(word)})


def _violations(where: dict[str, tuple[int, int]], sides: str) -> list[str]:
    found = []
    for side in sides:
        for n in range(_SECTIONS):
            head = where.get(f"{side}H{n}")
            if head is None:
                continue  # an unpaired section's empty side, or a title set across both
            translation = where.get(f"{side}T{n}")
            if translation is not None and translation[0] != head[0]:
                found.append(f"split heading {side}H{n}")
            opening = _lines(where, f"{side}P{n}")[:2]
            if any(page != head[0] for page, _ in opening):
                found.append(f"stranded heading {side}H{n}")
            for paragraph in (f"{side}P{n}", f"{side}Q{n}"):
                lines = _lines(where, paragraph)
                if len(lines) >= 2 and lines[0][0] != lines[1][0]:
                    found.append(f"orphan {paragraph}")
                if len(lines) >= 2 and lines[-1][0] != lines[-2][0]:
                    found.append(f"widow {paragraph}")
    return found


class _KeepTogether:
    """Mixin: one layout, typeset with and without the protection."""

    PARALLEL: bool
    TYPOGRAPHY: dict
    SIDES: str

    @classmethod
    def setUpClass(cls):
        cls.where = _typeset(cls.PARALLEL, cls.TYPOGRAPHY)
        cls.unprotected = _typeset(cls.PARALLEL, cls.TYPOGRAPHY, protected=False)

    def _of_kind(self, kind: str) -> list[str]:
        return [v for v in _violations(self.where, self.SIDES) if v.startswith(kind)]

    def test_every_word_is_set(self):
        # A line lost while reading the columns would also mean no widows.
        expected = sum(_LENGTHS[n % len(_LENGTHS)] * 3 + 5 for n in range(_SECTIONS))
        self.assertEqual(
            sum(1 for w in self.where if re.fullmatch(r"L[PQ]\d+w\d+", w)), expected)

    def test_no_widows(self):
        self.assertEqual(self._of_kind("widow"), [])

    def test_no_orphans(self):
        self.assertEqual(self._of_kind("orphan"), [])

    def test_no_split_headings(self):
        self.assertEqual(self._of_kind("split heading"), [])

    def test_no_stranded_headings(self):
        self.assertEqual(self._of_kind("stranded heading"), [])

    def test_the_sweep_reaches_a_page_edge(self):
        # Without the protection the same document breaks somewhere it should not.
        self.assertNotEqual(_violations(self.unprotected, self.SIDES), [])


_NEEDS_TEX = unittest.skipUnless(
    shutil.which("lualatex") and shutil.which("pdftotext"),
    "requires a real lualatex installation and pdftotext",
)


@_NEEDS_TEX
class TestSingleStream(_KeepTogether, unittest.TestCase):
    """One text: each heading, with its translated title, is a \\pstart of its own."""

    PARALLEL = False
    TYPOGRAPHY = {}
    SIDES = "L"


@_NEEDS_TEX
class TestPairsColumnHeadings(_KeepTogether, unittest.TestCase):
    """``\\Columns``, each column setting its own heading, with unpaired passages."""

    PARALLEL = True
    TYPOGRAPHY = {"parallel": {"layout": "pairs"}, "headings": {"from": "both"}}
    SIDES = "LR"


@_NEEDS_TEX
class TestPairsSpanningHeadings(_KeepTogether, unittest.TestCase):
    """``\\Columns``, with the headings set across the page above the columns."""

    PARALLEL = True
    TYPOGRAPHY = {"parallel": {"layout": "pairs"}, "headings": {"from": "combined"}}
    SIDES = "LR"


@_NEEDS_TEX
class TestFacingPages(_KeepTogether, unittest.TestCase):
    """``\\Pages``, where reledpar ends each page itself."""

    PARALLEL = True
    TYPOGRAPHY = {"parallel": {"layout": "pages"}, "headings": {"from": "both"}}
    SIDES = "LR"


if __name__ == "__main__":
    unittest.main()
