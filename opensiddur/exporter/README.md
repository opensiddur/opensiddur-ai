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

## Settings file

To control compilation, use a YAML-based settings file.
The settings are defined below:

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
`reledpar` so the verses on each side stay aligned across page breaks.

`column_order: primary_first` puts the primary stream on the left page (or
left column for a `pairs` layout); `primary_last` swaps them.

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
    layout: pairs               # pairs -> two columns/page; pages -> facing pages
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
