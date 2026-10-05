# Open Siddur Exporter

The exporter takes data in JLPTEI files and converts it into directly
consumable formats, like PDF and HTML.

The exporter operates in two stages:
1. **Compilation**: Given a starting file and a settings file, generate a compiled pseudo-TEI file that includes all of the data needed to convert into a final format in a linear form. The compilation step is common to all output formats.
2. **Output format**: Given the compiled file, output to the consumable format. The current output formats are:
    1. TeX typesetting system (LuaLaTeX, via [`reledmac`](https://ctan.org/pkg/reledmac) + [`reledpar`](https://ctan.org/pkg/reledpar) for critical-edition apparatus and parallel-text alignment)
    2. PDF, via the same LuaLaTeX pipeline

## Run the compiler

See
`uv run python -m opensiddur.exporter.compiler --help`

## Export to PDF

For TeX and PDF export, you'll need a TeX Live install with the LuaLaTeX
pipeline (`lualatex`, `latexmk`, `biber`, `reledmac`, `reledpar`, `polyglossia`,
`biblatex`). On Debian/Ubuntu the installer script `install-tex.sh` covers it:

```bash
sudo bash opensiddur/exporter/tex/install-tex.sh
```

For round-trip command examples, see `scripts/tei-to-pdf.sh` — the same
`-s <settings-file>` flag drives both the compiler and the PDF stage, so any
typography settings in the YAML are forwarded to the LuaLaTeX preamble.

## Printed books

Printed books are settings files in
[`opensiddur-projects/settings/`](https://github.com/opensiddur/opensiddur-projects/tree/main/settings),
one subdirectory per book holding that book's variants:

```
settings/
  humash/
    annual.yaml       # description: one parsha a week, the annual cycle
    triennial.yaml    # description: a third of each parsha, the triennial cycle
```

Each file names the root file it formats with a `book:` key and says how it differs from its
siblings with `description:` (below). When an opensiddur-ai release is published,
`.github/workflows/release-books.yml` lists them (`books --list`) at the opensiddur-projects
commit the release pins, and starts a `release-book.yml` job for each, which builds that book
and attaches it to the release as `<book>-<variant>-<tag>.pdf` (e.g. `humash-annual-v0.5.0.pdf`).

To build them locally (after syncing the reference database):

```bash
uv run python -m opensiddur.exporter.books                  # all books, into ./books/
uv run python -m opensiddur.exporter.books humash           # every variant of one book
uv run python -m opensiddur.exporter.books humash/annual    # one variant
uv run python -m opensiddur.exporter.books --check          # validate only, build nothing
uv run python -m opensiddur.exporter.books --list           # names, as JSON: ["humash/annual", ...]
```

A book that fails is reported and skipped and the rest are still built; the exit status is
nonzero if any failed. Each book's compiler and LaTeX output goes to
`<output>/<book>-<variant>.log`.

Pull requests to opensiddur-projects run `--check`, so a broken settings file fails there
rather than at release. It checks that each file:
- is in a book's subdirectory (`settings/<book>/<variant>.yaml`; a file anywhere else is an
  error, not silently left out of the release);
- parses, and matches the settings schema below, including a `book:` key;
- names a project and file that exist;
- can be typeset on that machine: every font chain, the defaults included, has an installed
  font. Without fontconfig this is an error rather than skipped.

## Settings file

To control compilation, use a YAML-based settings file.
The settings are defined below:

### Description and book
```yaml
description: >
  One parsha a week, the annual cycle. The triennial variant beside it
  reads a third of each parsha.
book:
  project: humash
  file_name: index.xml
  title: Humash   # optional
```
`description` is free text for people: what these settings make and why they differ from the
book's other variants. `book` is the root file the settings format. With a `book:`, the compiler needs only `-s`; `-p`/`-f`
still override it. Both the project and the file must exist. Optional, except in
`opensiddur-projects/settings/`, where every file is a book.

### Transclusion priority
```yaml
priority:
  transclusion:
    - prj1
    - prj2
    - ...
```

When a file is transcluded by URN and a project is not specified, take the file from the URNs in this list of projects, in this order (first to last). For example, if I reference: `urn:x-opensiddur:text:bible:genesis/1/1`, and my transclusion priority is `wlc`, then `jps1917`, the text will be derived from the WLC.

If no transclusion priority is specified, the project that owns the first file processed is used.

### Instructions priority
```yaml
  instructions:
    - prj1
    - prj2
    - ...
```

When instructional notes are given, take them from the given projects, in the given order instead of from the project being processed. 

### Annotation sources

```yaml
annotations:
  - prj1
  - prj2
  - ...
```

From which projects should notes (such as editorial notes or commentary) be derived?
Unlike instructions and transclusions, annotations are not in prioritized order; the annotations from all listed projects will be included when available.

### Printing annotations once

```yaml
print_once:
  commentary: true
  editorial: false
```

A note is set wherever its target is, so text that is transcluded more than once repeats its notes. Each flag
makes the notes of the same `@type` set only at the first occurrence of their target in the book. Both are
`false` by default. Instructions and citations belong to every occurrence of their text and cannot be listed.

This decides how often a note is set. Whether a note belongs in a given context at all is decided by the note's own
`j:condition` (see *Conditional notes* in `schema/JLPTEI-3.md`). A note that is out of context where its text first
appears is set at the first occurrence where it is in context.

### Parallel texts

```yaml
parallel:
  projects:
    - jps1917
  column_order: primary_first   # or primary_last
```

When the compiler builds a document, it also looks up matching content in
each of the listed `parallel` projects (by `corresp` URN) and emits
`p:parallel`/`p:parallelItem` blocks. The PDF stage feeds those blocks into
`reledpar` so the verses on each side stay aligned across page breaks, or, in
the `interleaved` layout, sets each block's translation directly after it.
A block with text on one side only (for example, Hebrew whose English
document carries only anchors for its notes) is set at the full page width
between column blocks, with any notes from the empty side attached to it.

`column_order: primary_first` puts the primary stream on the left page (or
left column for a `pairs` layout, or first in an `interleaved` one);
`primary_last` swaps them. The left page is the verso: for facing pages in a
book bound on the right, put the Hebrew on the right with `primary_last`.

### Typography (PDF/TeX stage only)

The `typography` section says how the exported document should look: paper and margins, fonts,
the size and weight of each kind of text, line spacing, line numbers, how notes are marked,
running heads. It is read by the PDF/TeX stage only; the linear-XML compiler ignores it.

**[`doc/typography.md`](../../doc/typography.md) is the full reference** — every key, its type,
its allowed values, its default and what it affects.

```yaml
typography:
  fonts:
    hebrew: ["Frank Ruehl CLM", "Ezra SIL", "SBL Hebrew", "FreeSerif"]  # tried in order
    latin: "Linux Libertine O"
  page:
    paper: letterpaper          # a4paper | letterpaper | legalpaper | a5paper | b5paper
                                # | executivepaper | custom
    base_font_size: 11pt        # 10pt | 11pt | 12pt
    sides: two                  # two | one
    margins: {inner: 1in, outer: 0.75in}
  paragraphs:
    line_spacing: 1.0           # 0.5-3.0
  styles:
    heading1: {size: xx-large, weight: bold, align: center}
    note: {size: 9pt}
  line_numbers:
    enabled: true
    increment: 5
  notes:
    placement: footnote         # footnote | endnote | none
    anchor: interlinear         # interlinear | superscript | inline
  parallel:
    layout: pairs               # pairs -> two columns/page; pages -> facing pages;
                                # interleaved -> each block followed by its translation
  table_of_contents:
    enabled: false
    depth: 4
  page_header: {}               # running heads; see doc/typography.md
  page_footer: {}
```

Every key is optional, and every default reproduces the output this exporter has always
produced — a settings file need only say what it wants changed.

Every key is also *checked*. An unknown key, a value outside a closed list, a malformed length
or a font chain with nothing installed is an error naming the offending path, raised before
anything is rendered. Nothing is silently ignored: a setting that was quietly dropped would
leave a document missing what was asked for with nothing to say why.

Note that which text goes on which side of a parallel layout is `parallel.column_order` in the
compiler section above, not in `typography` — the compiler is what decides the order the
streams are emitted in.

## Settings file versioning
Note that this file is likely to change slightly in format as more output
formats are introduced.
