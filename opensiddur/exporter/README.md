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
  table_of_contents:
    enabled: false                   # true → print a table of contents page
    depth: 4                         # 1-4; heading levels shown in the printed TOC
```

The `typography` section is read by the PDF/TeX stage only; the linear-XML
compiler ignores it. Every key is optional — when the section (or any single
key) is omitted, the defaults shown above are used. Fonts that aren't found
on the system fall back to a sensible default automatically (`Ezra SIL` →
`SBL Hebrew` → `FreeSerif` for Hebrew).

`table_of_contents.depth` controls only the printed table of contents; it is
independent of the PDF bookmark/outline depth, which is always 4 levels deep
regardless of this setting.

### Running heads and feet

`typography.page_header` and `typography.page_footer` put content in the left,
center and right of each page. Omit them and the book class's own page style is
left alone.

```yaml
typography:
  page_header:
    odd:
      left: "{book-title}"                                    # bare string = just text
      right: {text: "Page {page}", language: en}
    even:
      left: {text: "{page-hebrew}", language: he}
      center: {text: "Chapter {chapter-number}", language: en, if: "{chapter-number}"}
  page_footer:
    all:                                                      # same on every page
      center: "{page}"
```

Each of `page_header` and `page_footer` takes either `all` — the same content on
every page — or `odd` and/or `even` to differentiate them. Combining `all` with
`odd` or `even` is an error.

`left`, `center` and `right` are *physical* positions on the page, not logical
ones: `left` is the left edge whichever way the text runs.

Each position is either a bare string or a mapping with:

- `text` — the template (see the codes below).
- `language` — the slot's base direction, which decides the order its runs are
  laid out in, and the font for content that declares nothing else. Defaults to
  the document's own `xml:lang`; only Hebrew (`he`, `he-*`) versus everything
  else is distinguished. Every run — literal text, a heading recorded in a mark,
  the page number — carries its own direction inside that, so a mixed title like
  "רות RUTH" reads correctly in a slot of either direction, and digits are never
  reversed.
- `if` — a second template. When it expands to nothing, the whole position is
  dropped, literal text included, so `"Chapter {chapter-number}"` leaves no
  orphaned "Chapter" on a page before the first chapter.

Anything outside braces is literal text; `{{` and `}}` are literal braces. The
codes are a closed list, and an unrecognized one is a settings error:

| Code | Expands to |
| --- | --- |
| `{page}` | the page number as the document numbers it (roman in front matter) |
| `{page-hebrew}` | the page number in Hebrew numerals |
| `{document-title}` | the title from the TEI header, fixed for the whole document |
| `{book-title}` | the head of the enclosing `tei:div[@type='book']` |
| `{chapter-number}` | the `n` of the last `tei:milestone[@unit='chapter']` |
| `{chapter-number-hebrew}` | the same, in Hebrew numerals |
| `{head1}` … `{head4}` | the last heading at that level |
| `{section-title}` | the last heading at any level |
| `{book-title-alt}`, `{head1-alt}` … `{head4-alt}`, `{section-title-alt}` | the same, from the *second* parallel column |

Everything but `{page}`, `{page-hebrew}` and `{document-title}` names whatever
was in force at the *end* of the page, so a heading starting partway down a page
names that page. The `-alt` codes are what let a running head name the second
language of a parallel volume; in a non-parallel document they expand to
nothing.

Title pages never carry a running head or foot, nor do the blank pages inserted
to keep a title page on a recto.

## Settings file versioning
Note that this file is likely to change slightly in format as more output
formats are introduced.
