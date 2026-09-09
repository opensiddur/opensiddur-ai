---
name: scan-to-jlptei
description: Convert a scanned book into JLPTEI by reading its pages — fetching and enlarging leaves, reading the print, measuring a transcription against it, authoring the TEI, and checking the rendered PDF. Use when converting a scan, especially a facing-page bilingual one (Hebrew opposite English), or when a parallel PDF looks wrong.
---

# Reading a scan into JLPTEI

The page is the evidence. A transcription of the book, however good, is a proofreading
check on the reading and never its source — `specs/BIRNBAUM_FROM_SCAN.md` opens with why,
and `opensiddur/importer/birnbaum_scan/__init__.py` states it in three lines.

Everything below is what those documents do not already say. Where this file and a
document disagree, **the document wins and this file is wrong** — fix it.

## Order of work

| | | |
|---|---|---|
| 1 | Fetch and cut the leaf | `python -m opensiddur.importer.birnbaum_scan.pages 81 82 83` |
| 2 | Read the page into prose | by hand, into `readings/{printed}.md` |
| 3 | Diff against a transcription | `python -m opensiddur.importer.birnbaum_scan.compare` |
| 4 | Adjudicate each difference | go back to the image; record in `verdicts/{printed}.json` |
| 5 | Author the TEI | hand-written, one function per prayer |
| 6 | Compile and render | `exporter.compiler`, then `exporter.pdf.pdf` |
| 7 | **Measure** the PDF | `reference/measuring-the-pdf.md` |

Steps 1 and 3 explain themselves: the module docstrings of `opensiddur/importer/birnbaum_scan/pages.py` and `compare.py`
carry the reasoning — why a page is fetched once, why bands overlap and are enlarged, why
differences are counted in three buckets and not merely resolved. Read them rather than a
summary of them.

A printed page number is not a leaf number is not a scan page. `pages.json` is the only
place that correspondence lives; never re-derive it.

## What two languages change

**The alignment unit is the `p:parallel` block, and you choose it.** Two sides join on
*exact URN equality* — `schema/JLPTEI-3.md`, `### Alignment`. So granularity is an
authoring decision, not a rendering one: two passages line up because you gave them their
own matching `@corresp`, and inside a block the columns drift and only resync at the next
block boundary. If a passage must start level with its translation, give it a URN of its
own. A `@corresp` repeated within one document breaks the join **silently**.

The compiler's own invariants are in `specs/COMPILER_SPECIFICATION.md`, `## Parallel
Compilation`.

**A rubric can sit on different rows in the two columns, and be correct.** A rubric whose
direction differs from the text around it cannot share a line with it, so it takes a line
of its own; in the facing column, where it does not cross, the same rubric runs in. The
result is one rubric on two different rows. That is the layout working, not failing.

Set `typography.instructions.from: both` when rubrics fall mid-passage rather than at
alignment boundaries — anything else needs them *at* boundaries, or a column ends up with
a rubric nowhere near the words it governs. `doc/typography.md`, ``## `instructions` ``.

**Column geometry means nothing by itself.** Which column is left tells you nothing about
which is read first; the two sides of an opening invert. The linearised order must
preserve *reading* order — `specs/BIRNBAUM_FROM_SCAN.md`, `## What the print does, that
the encoding has to carry`, which sets out the rest of these (asterisk means substitution,
simultaneous columns, bare day-names, a page turn mid-sentence).

**When order or geometry is in doubt, crop the block and look at it.** Inferring column
order from surrounding text is how a page gets read backwards. Cropping costs a minute.

## Verifying the rendered PDF

**Measure it; do not look at it.** A parallel-layout defect is a geometric fact — a row
nobody used, a rubric split across a blank line, a number inside its own column — and the
eye is unreliable about all three, in both directions. Recipes and the specific
measurements that have caught real defects are in `reference/measuring-the-pdf.md`.

One rule generalises past this project: **an assertion that cannot fail proves nothing.**
When a measurement passes, feed the pre-fix state back into it and confirm it goes red. A
check that silently measures nothing is worse than no check, because it is believed.

## Traps

**Encoding**
- One instruction URN per distinct rubric *text*. Sharing a URN between rubrics that say
  different things makes the compiler print one where the other belongs.
- A page turn falls mid-sentence; `tei:pb` is valid inside `tei:p`.
- Slugs are unique per foundation page, not globally.
- Chapter and verse are separated by a colon.

**Attribution**
- The reading is ours. A transcription used as a check is not a source, and the people who
  made it are not this text's transcribers.
- The author of the book gets no `respStmt` — he is a source. `schema/JLPTEI-3.md`,
  `#### Contributors and contributor URNs`.
- Every `opensiddur.org` contributor URN must be registered in
  `specs/urn_registry/contributor.jsonl`; this is validated, and an unregistered one is a
  typo that credits a different person.

**Tooling**
- Never run the test suite while a build is running: both use the reference database at `database/reference.db`, and
  the collision shows up as an unrelated test failing.
- Refresh `refdb` for the project directory you are building, or sources and licences
  quietly come out thinner than they should — the compiled XML is identical either way, so
  nothing warns you.
- `--` inside an XML comment is illegal, and in `opensiddur/exporter/tex/reledmac.xslt` it fails *every*
  transform-based test at once, which reads as catastrophe rather than typo. Use an em
  dash.
- A comment that loses its opening `<!--` is still well-formed XML: the prose becomes a
  text node and lands in the LaTeX preamble. `TestPreambleIsAllTeX` guards this.

## Where things are written down

| Document | Covers |
|---|---|
| `specs/BIRNBAUM_FROM_SCAN.md` | The procedure end to end, and what this print does that the encoding must carry |
| `schema/JLPTEI-3.md` | The schema: alignment, contributors, conditionals, transclusion, URN scope |
| `specs/COMPILER_SPECIFICATION.md` | Transclusion, conditionals, parallel-compilation invariants |
| `doc/typography.md` | Every typography setting, including `parallel` and `instructions` |
| `doc/exporter-settings.example.yaml` | A complete annotated settings file |
| `AGENTS.md` | Repository layout, JLPTEI authoring rules, testing conventions |
| `specs/birnbaum_scan/accuracy.md` | How far one transcription stood from this print, measured |
| `sourcetexts`, `sources/birnbaum_siddur/scan_reading/` | The reading itself, page by page |

`schema/jlptei.odd.xml` is authoritative where the prose disagrees with it. Run the
validator.
