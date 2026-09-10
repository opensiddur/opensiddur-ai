# Measuring a parallel PDF

Assertions on the emitted `.tex` cannot see any of this. Where a line lands is decided by
TeX, out of machinery that reledpar drives per column and per row, so the only way to know
whether a two-column page is right is to measure the PDF.

Keep the intermediate TeX while building — `--tex-output <path>` — because the answer to
"why did it do that" is usually in it.

## Getting rows out of a page

```python
import re, subprocess

def words(pdf, page):
    """Every word on one page as (x0, y0, x1, text)."""
    xml = subprocess.run(["pdftotext", "-bbox", "-f", str(page), "-l", str(page), pdf, "-"],
                         capture_output=True, text=True).stdout
    return [(float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4))
            for m in re.finditer(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">([^<]*)</word>',
                xml)
            if m.group(4).strip() and float(m.group(2)) > 90]   # 90 clears the folio
```

At 11pt a row advances **13.5pt**. So:

- `+13.5` — the next row, as expected
- `+27` — one row nobody used
- anything between, say `+19.5` — either a taller row (Hebrew with nikkud sets taller than
  Latin) or something leaking; look before concluding

Hebrew and Latin baselines within *the same* row differ by about 2.5pt. Collapse anything
closer than ~6pt into one row before measuring advances, or every row looks like two.

## The four measurements that have caught real defects

**A rubric's own lines are contiguous.** Pull the rubric strings out of the emitted TeX,
find the first and last word of each in the PDF, and require the span to cover no more rows
than the rubric has lines. A blank row through the middle of one rubric is never wanted.

**The same rubric starts on the same row in both columns.** Only meaningful for a rubric
that opens a `\pstart` in both — see the caveat about drift in `SKILL.md`.

**No line number lies inside its column's text.** Cluster the page's text into two columns
at the widest horizontal gap, take each column's span, and require every margin number's
box to fall entirely outside it. Stronger than "no collision on the same line", which
passes by luck whenever no numbered line happens to be full measure.

**Numbers restart on every page in both columns.** With `firstlinenum` 5 and increment 5, each
page's lowest number in each column should be 5. The right-hand series has its own
switches; a left column that resets while the right runs on to 320 is the signature.

**A Latin heading is painted left to right.** Where the two columns head a section in
different languages, the facing title is set inside the other column's direction, and a
reversed heading is a real defect that reads perfectly in `pdftotext` output. Take the
glyphs' own x coordinates, sort ascending, join, and require the expected string — not its
reverse — to appear. A heading is not covered by any rubric check: measure it separately,
or a whole section title can come out backwards with every rubric assertion still green.

## How the measurement lies

Every one of these produced a confident wrong answer before it was caught.

**An RTL column is right-aligned.** A word's `xMin` says nothing about where its line
begins; short lines start far to the right. Measure RTL lines from `xMax`, or from the
line's own extent, never from a single word's left edge.

**`pdftotext` merges a margin line number into the text line beside it.** A line that looks
17pt too wide is usually a line with `30` appended. Strip a trailing bare integer before
measuring a line's extent.

**Inline verse numbers look exactly like line numbers.** Both are bare integers. Tell them
apart by position — a margin number sits clear of the text by `\linenumsep`, an inline one
is adjacent — not by pattern.

**`pdftotext` reading order hides a reversed run.** It reorders RTL runs on output, so a
Latin heading typeset right to left comes back in the correct order and looks fine. Only
the glyph coordinates show it. The same caution applies to any assertion about order taken
from `pdftotext` text output rather than from `-bbox`.

**A window after a macro name is not its argument.** Slicing a fixed number of characters
after `\\OSheadTranslation{` reaches past the argument into the `\\addcontentsline` that
follows, which carries a direction wrapper of its own — so an assertion about the
argument's wrapper passes on the wrong text. Match balanced braces instead. This kept a
test green against the very stylesheet bug it was written to catch.

**Metadata, colophon and bibliography pages are not parallel text.** A column-splitting
heuristic will happily bisect a full-width licence block and report nonsense. Restrict to
pages that actually have two columns, or exclude the tail explicitly.

**A whole-document before/after is not a controlled comparison.** Changing a macro removes
or adds rows, which reflows pagination, so "page 7" is not the same content in both builds.
To isolate one construct: cut its `\pstart` pair out of the emitted TeX, wrap it in the
real preamble, and compile that alone. Content and pagination then hold still and the only
variable is the change.

**Reproduction can be content-sensitive.** Some defects appear only at particular line
counts — one repro split at Hebrew ×6 against English ×30 and not at ×10. If a minimal
repro fails to show a defect the real document shows, the repro is wrong, not the defect.
Sweep the lengths, or cut the real document down instead of building one up.
