# Open Siddur Exporter

The exporter takes data in JLPTEI files and converts it into directly 
consumable formats, like PDF and HTML.

The exporter operates in two stages:
1. **Compilation**: Given a starting file and a settings file, generate a compiled pseudo-TEI file that includes all of the data needed to convert into a final format in a linear form. The compilation step is common to all output formats.
2. **Output format**: Given the compiled file, output to the consumable format. The current output formats are:
    1. TeX typesetting system (XeLaTeX)
    2. PDF, via XeLaTeX

## Run the compiler

See
`poetry run python -m opensiddur.exporter.compiler --help`

## Export to PDF

For TeX and PDF export, you will need an installation of XeLaTeX. See `install-tex.sh`.

For round-trip command examples, 
see `tei-to-pdf.sh`.

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

## Settings file versioning
Note that this file is likely to change slightly in format when parallel texts are introduced.
