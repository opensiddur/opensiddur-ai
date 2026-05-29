# Open Siddur Project (AI aided version)

[![Tests](https://github.com/opensiddur/opensiddur-ai/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/opensiddur/opensiddur-ai/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/opensiddur/opensiddur-ai/branch/main/graph/badge.svg?token=S4DAU7F6VY)](https://codecov.io/github/opensiddur/opensiddur-ai)

This is a work in progress to convert the Open Siddur Project to use AI to aid in the conversion of the liturgical texts.

## Features:
* A new version of JLPTEI (2) with a simplified schema.
* Less emphasis on UI: This is primarily about converting texts from any input format to JLPTEI, and converting the JLPTEI to useful output formats and combining texts in novel ways.

## Schema
To compile the schema:

Prerequisites:
You need a working version of podman (open source implementation of docker).

The main schema is in `schema/jlptei.odd.xml`. To compile it, run:
```bash
$ scripts/build-schema.sh
```

The output will be in the `schema` directory as RelaxNG XML (and, eventually, ISO Schematron).

## Sources

Available sources in their original (or close to original) form are in the `sources` directory.
The canonical source texts repository is at [opensiddur/sourcetexts](https://github.com/opensiddur/sourcetexts).
Clone or symlink it as the `sources` root before running any importers.

Input converters for each specific source are in the `importer` directory.

Example: run the WLC importer against an external clone:

```bash
uv run python -m opensiddur.importer.wlc.wlc \
  --sourcetexts-root ~/src/opensiddur-repos/sourcetexts/sources \
  --project-dir ~/src/opensiddur-repos/opensiddur-projects/project/wlc
```

Example: run the JPS 1917 importer against an external clone:

```bash
uv run python -m opensiddur.importer.jps1917.convert_wikisource \
  --sourcetexts-root ~/src/opensiddur-repos/sourcetexts/sources \
  --project-dir ~/src/opensiddur-repos/opensiddur-projects/project/jps1917
```

Example: download Miqra al pi ha-Masorah from Google Sheets into sourcetexts:

```bash
uv run python -m opensiddur.importer.miqra_al_pi_hamasorah.download \
  --sourcetexts-root ~/src/opensiddur-repos/sourcetexts/sources
```

## JLPTEI sources

JLPTEI sources are compiled into the `project` directory.
The canonical projects repository is at [opensiddur/opensiddur-projects](https://github.com/opensiddur/opensiddur-projects).
Clone or symlink it as the `project` root before running the compiler or exporter.

## Reference database

The exporter resolves `urn:x-opensiddur:` URIs to project files via a SQLite
database at `database/reference.db`. Whenever you add, remove, or rename files
in the `project/` directory (e.g. a clone of [opensiddur/opensiddur-projects](https://github.com/opensiddur/opensiddur-projects)),
re-sync the database so the compiler can find them, as in the example here:

```bash
uv run python -m opensiddur.exporter.refdb --project-directory ~/src/opensiddur-projects/project
```

The command scans every `project/<name>/` subdirectory, updates URN and
cross-reference mappings for changed files, and removes stale entries for
projects or files that no longer exist.  It prints a per-project summary on
completion.

You must re-sync before running the compiler on any newly-added project. 

## Compilation (JLPTEI → compiled linear XML)

The compiler takes a `project/<name>/` file (from [opensiddur/opensiddur-projects](https://github.com/opensiddur/opensiddur-projects)),
resolves transclusions, annotations, and parallel texts,
and outputs a single “compiled” XML file that can be 
converted into a final printable format (eg, PDF).

Example (compile `project/wlc/ruth.xml` to `compiled.xml`):

```bash
uv run python -m opensiddur.exporter.compiler \
  --project-directory ~/src/opensiddur-repos/opensiddur-projects/project \
  --project wlc \
  --file_name ruth.xml \
  --output_file compiled.xml
```

Example with a settings YAML (controls project priorities, annotations, and optional parallel lookup):

```bash
uv run python -m opensiddur.exporter.compiler \
  --project-directory ~/src/opensiddur-repos/opensiddur-projects/project \
  --project wlc \
  --file_name ruth.xml \
  --settings doc/exporter-settings.example.yaml \
  --output_file compiled.xml
```

## TeX export (compiled XML → LuaLaTeX)

Convert the compiled XML file to LuaLaTeX using the `reledmac`/`reledpar` pipeline:

```bash
uv run python -m opensiddur.exporter.tex.latex \
  --project-directory ~/src/opensiddur-repos/opensiddur-projects/project \
  compiled.xml \
  --settings doc/exporter-settings.example.yaml \
  --output compiled.tex
```

## PDF export (compiled XML → PDF)

Export directly to PDF (generates TeX internally, then runs LuaLaTeX/latexmk):

```bash
uv run python -m opensiddur.exporter.pdf.pdf \
  --project-directory ~/src/opensiddur-repos/opensiddur-projects/project \
  --settings doc/exporter-settings.example.yaml \
  compiled.xml \
  output.pdf
```

Keep the intermediate TeX (helpful for debugging LaTeX issues):

```bash
uv run python -m opensiddur.exporter.pdf.pdf \
  --project-directory ~/src/opensiddur-repos/opensiddur-projects/project \
  --settings doc/exporter-settings.example.yaml \
  --keep-tex \
  compiled.xml \
  output.pdf
```
