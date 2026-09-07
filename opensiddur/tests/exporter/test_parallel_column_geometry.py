r"""Does one column's vertical spacing stay in that column?

Every other test in this directory asserts on the ``.tex`` the XSLT emits. None of them
can see this bug, because it is not in the text: it is in what TeX does with the text.
``\Columns`` cuts each column into slices of ``\baselineskip``, ``\unvbox``-es each slice
onto the full-width page list, and keeps only its ``\lastbox`` as the column's line
(``reledpar.sty``, ``\do@lineL``). Whatever else was in the slice stays behind on the
shared list, between two rows, and moves *both* columns.

So these tests typeset a two-column document and measure where the lines land. The
facing column is filled with one long paragraph, which must come out evenly leaded: any
row that is taller than its neighbours is something escaping from the other column.

The macros under test are pulled out of the real XSLT output rather than written here,
so that a regression in the exporter is what fails, not a stale copy.
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from opensiddur.common.xslt import xslt_transform_string
from opensiddur.exporter.tex.latex import XSLT_FILE

_MINIMAL_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
</tei:TEI>"""

# Long enough to run past the row where the other column does something.
_FILLER = " ".join(f"word{n}" for n in range(60))

_DOCUMENT = r"""\documentclass[11pt,letterpaper]{book}
\usepackage{reledmac}
\usepackage{reledpar}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.5em}
%(macros)s
\Lcolwidth=0.43\textwidth
\Rcolwidth=0.43\textwidth
\begin{document}
\begin{pairs}
\begin{Leftside}
\setlength{\parskip}{0pt}
\beginnumbering
\pstart %(left)s\pend
\endnumbering
\end{Leftside}
\begin{Rightside}
\setlength{\parskip}{0pt}
\beginnumbering
\pstart %(right)s\pend
\endnumbering
\end{Rightside}
\end{pairs}
\Columns
\end{document}
"""


def _preamble() -> str:
    return xslt_transform_string(
        XSLT_FILE, _MINIMAL_TEI,
        xslt_params={"additional-preamble": "", "additional-postamble": ""},
    )


_PARALLEL_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
         xmlns:p="http://jewishliturgy.org/ns/processing">
  <tei:text><tei:body>
    <p:parallel column-order="primary_first">
      <p:parallelItem role="primary" xml:lang="en">
        <tei:div><tei:p>First</tei:p><tei:p>Second</tei:p></tei:div>
      </p:parallelItem>
      <p:parallelItem role="parallel" xml:lang="en">
        <tei:div><tei:p>Alpha</tei:p><tei:p>Beta</tei:p></tei:div>
      </p:parallelItem>
    </p:parallel>
  </tei:body></tei:text>
</tei:TEI>"""


def _paragraph_break() -> str:
    r"""Whatever the exporter now puts between two paragraphs of one parallel block."""
    out = xslt_transform_string(
        XSLT_FILE, _PARALLEL_TEI,
        xslt_params={"additional-preamble": "", "additional-postamble": "",
                     "layout": "pairs"},
    )
    found = re.search(r"First(.*?)Second", out, re.S)
    assert found, "the two paragraphs are not both in the output"
    return found.group(1).strip()


def _macro(name: str) -> str:
    r"""The exporter's own definition of \<name>, verbatim."""
    for line in _preamble().splitlines():
        if line.startswith(rf"\newcommand{{\{name}}}"):
            return line
    raise AssertionError(rf"\{name} is not defined in the preamble")


@unittest.skipUnless(
    shutil.which("lualatex") and shutil.which("pdftotext"),
    "requires a real lualatex installation and pdftotext",
)
class TestParallelColumnGeometry(unittest.TestCase):

    def _leading(self, left: str, right: str, macros: str) -> list[float]:
        """Typeset the two columns and return the right column's line-to-line advances."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "t.tex").write_text(
                _DOCUMENT % {"macros": macros, "left": left, "right": right}
            )
            for _ in range(2):  # reledpar needs a second pass to pair the columns
                done = subprocess.run(
                    ["lualatex", "-interaction=nonstopmode", "t.tex"],
                    cwd=work, capture_output=True, text=True,
                )
            self.assertTrue(
                (work / "t.pdf").exists(),
                f"lualatex produced no PDF:\n{done.stdout[-2000:]}",
            )
            boxes = subprocess.run(
                ["pdftotext", "-bbox-layout", "t.pdf", "-"],
                cwd=work, capture_output=True, text=True,
            ).stdout

        # Only the filler's own lines: every one of its words is "wordN", which keeps
        # page numbers, reledmac's margin line numbers and the other column out of the
        # measurement without having to guess at column boundaries.
        ys = []
        for m in re.finditer(
            r'<line xMin="[\d.]+" yMin="([\d.]+)"[^>]*>(.*?)</line>', boxes, re.S
        ):
            words = re.findall(r">([^<]*)</word>", m.group(2))
            if any(w.startswith("word") for w in words):
                ys.append(float(m.group(1)))
        ys.sort()
        self.assertGreater(len(ys), 3, "the facing column did not set enough lines")
        return [round(ys[i + 1] - ys[i], 1) for i in range(len(ys) - 1)]

    def assertEvenlyLeaded(self, advances: list[float]) -> None:
        """One paragraph, so every line sits one line below the last."""
        smallest = min(advances)
        self.assertLessEqual(
            max(advances), smallest + 2.0,
            f"the facing column is not evenly leaded: {advances} -- a row is taller "
            f"than the rest, which is spacing that escaped the other column",
        )

    def test_a_paragraph_break_stays_in_its_column(self):
        r"""A ``\par`` carrying ``\parskip`` used to leave the skip on the shared list,
        which put a blank line through the middle of the facing paragraph. The Birnbaum
        Amidah showed it as "...December 4th say: Be-" / blank / "stow a blessing"."""
        advances = self._leading(
            left=f"AAA aaa aaa aaa aaa{_paragraph_break()} BBB bbb bbb",
            right=_FILLER,
            macros="",
        )
        self.assertEvenlyLeaded(advances)

    def test_two_adjacent_rubrics_stay_in_their_column(self):
        r"""Two rubrics in a row put two ``\newline`` together. The empty line between
        them has no height, so instead of becoming a row it left the glue before it on
        the shared list -- a 6pt gap through the middle of a word in the facing column."""
        block = _macro("OSInstructionBlock")
        advances = self._leading(
            left=r"\OSInstructionBlock{AAA aaa aaa aaa}\OSInstructionBlock{BBB bbb bbb}",
            right=_FILLER,
            macros=block,
        )
        self.assertEvenlyLeaded(advances)

    def _rubric_rows(self, macros: str) -> tuple[list[float], list[float]]:
        r"""Where each column sets a rubric that opens its \pstart.

        One column crosses direction and gets \OSInstructionBlock, the other does not and
        gets \instructionnote run-in -- which is correct, an English rubric cannot share a
        line with Hebrew. Both must still start on the same row.
        """
        rubric = r"{\bfseries Used when one is unable to recite the complete Amidah}"
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "t.tex").write_text(
                _DOCUMENT % {
                    "macros": _macro("OSInstructionBlock") + "\n" + macros,
                    "left": r"\par\mbox{}\par\OSInstructionBlock{" + rubric + "}",
                    "right": r"\par\mbox{}\par" + rubric,
                }
            )
            for _ in range(2):
                done = subprocess.run(["lualatex", "-interaction=nonstopmode", "t.tex"],
                                      cwd=work, capture_output=True, text=True)
            self.assertTrue((work / "t.pdf").exists(),
                            f"lualatex produced no PDF:\n{done.stdout[-2000:]}")
            boxes = subprocess.run(["pdftotext", "-bbox", "t.pdf", "-"],
                                   cwd=work, capture_output=True, text=True).stdout
        left, right = [], []
        for m in re.finditer(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>([^<]*)</word>', boxes
        ):
            x, y, word = float(m.group(1)), float(m.group(2)), m.group(3)
            if y > 85 and word.strip() and not word.strip().isdigit():
                (left if x < 250 else right).append(round(y, 1))
        return sorted(set(left)), sorted(set(right))

    def assertRubricsShareRows(self, left, right) -> None:
        self.assertTrue(left and right, "one column set no rubric at all")
        self.assertEqual(
            left, right,
            f"the same rubric is set on different rows: left {left}, right {right} -- "
            f"a break taken where no line was in progress spends a row in one column only",
        )

    def test_a_rubric_opening_a_pstart_starts_on_the_same_row_in_both_columns(self):
        left, right = self._rubric_rows("")
        self.assertRubricsShareRows(left, right)

    def test_the_measurement_would_notice_a_rubric_pushed_down(self):
        r"""\leavevmode is the pre-fix definition: it breaks even in vertical mode."""
        leaky = (r"\renewcommand{\OSInstructionBlock}[1]"
                 r"{\leavevmode\unskip\strut\newline{\bfseries #1}\newline\ignorespaces}")
        left, right = self._rubric_rows(leaky)
        with self.assertRaises(AssertionError):
            self.assertRubricsShareRows(left, right)

    def test_the_measurement_would_notice(self):
        r"""The check has to be able to fail, or the two tests above prove nothing.
        An unstrutted rubric macro is the pre-fix definition, and it must be caught."""
        leaky = (r"\newcommand{\OSInstructionBlock}[1]"
                 r"{\leavevmode\unskip\newline{\bfseries #1}\newline\ignorespaces}")
        advances = self._leading(
            left=r"\OSInstructionBlock{AAA aaa aaa aaa}\OSInstructionBlock{BBB bbb bbb}",
            right=_FILLER,
            macros=leaky,
        )
        with self.assertRaises(AssertionError):
            self.assertEvenlyLeaded(advances)
