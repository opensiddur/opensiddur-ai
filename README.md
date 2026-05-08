# Open Siddur Project (AI aided version)

[![Tests](https://github.com/efeins/opensiddur-ai/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/efeins/opensiddur-ai/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/efeins/opensiddur-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/efeins/opensiddur-ai)

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

Input converters for each specific source are in the `importer` directory.

## JLPTEI sources

JLPTEI sources are compiled into the `project` directory.

## Reference database

The exporter resolves `urn:x-opensiddur:` URIs to project files via a SQLite
database at `database/reference.db`. Whenever you add, remove, or rename files
in the `project/` directory, re-sync the database so the compiler can find them:

```bash
uv run python -m opensiddur.exporter.refdb
```

The command scans every `project/<name>/` subdirectory, updates URN and
cross-reference mappings for changed files, and removes stale entries for
projects or files that no longer exist.  It prints a per-project summary on
completion.

You must re-sync before running the compiler on any newly-added project. 

## Compilation (JLPTEI → compiled linear XML)

The compiler takes a `project/<name>/` file, resolves transclusions, annotations, and parallel texts,
and outputs a single “compiled” XML file that can be 
converted into a final printable format (eg, PDF).

Example (compile `project/wlc/ruth.xml` to `compiled.xml`):

```bash
uv run python -m opensiddur.exporter.compiler \
  --project wlc \
  --file_name ruth.xml \
  --output_file compiled.xml
```

Example with a settings YAML (controls project priorities, annotations, and optional parallel lookup):

```bash
uv run python -m opensiddur.exporter.compiler \
  --project wlc \
  --file_name ruth.xml \
  --settings doc/exporter-settings.example.yaml \
  --output_file compiled.xml
```

## TeX export (compiled XML → LuaLaTeX)

Convert the compiled XML file to LuaLaTeX using the `reledmac`/`reledpar` pipeline:

```bash
uv run python -m opensiddur.exporter.tex.latex \
  compiled.xml \
  --settings doc/exporter-settings.example.yaml \
  --output compiled.tex
```

## PDF export (compiled XML → PDF)

Export directly to PDF (generates TeX internally, then runs LuaLaTeX/latexmk):

```bash
uv run python -m opensiddur.exporter.pdf.pdf \
  --settings doc/exporter-settings.example.yaml \
  compiled.xml \
  output.pdf
```

Keep the intermediate TeX (helpful for debugging LaTeX issues):

```bash
uv run python -m opensiddur.exporter.pdf.pdf \
  --settings doc/exporter-settings.example.yaml \
  --keep-tex \
  compiled.xml \
  output.pdf
```