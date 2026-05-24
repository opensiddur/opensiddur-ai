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

```yaml
typography:
  hebrew_font: "Frank Ruehl CLM"     # any installed OpenType font with Hebrew coverage
  latin_font: "Linux Libertine O"    # any installed OpenType font for the Latin stream
  layout: pages                      # "pages" → facing pages; "pairs" → two columns/page
  paper: a4paper                     # any \documentclass paper option
  fontsize: 11pt                     # 10pt | 11pt | 12pt
```

The `typography` section is read by the PDF/TeX stage only; the linear-XML
compiler ignores it. Every key is optional — when the section (or any single
key) is omitted, the defaults shown above are used. Fonts that aren't found
on the system fall back to a sensible default automatically (`Ezra SIL` →
`SBL Hebrew` → `FreeSerif` for Hebrew).

## Settings file versioning
Note that this file is likely to change slightly in format as more output
formats are introduced.
