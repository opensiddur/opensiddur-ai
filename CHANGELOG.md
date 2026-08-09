# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shared table of the 54 weekly parshiyot (`opensiddur/importer/util/parshiyot.py`), mapping any
  source's spelling of a parshah name to a canonical Hebrew name and a URN slug.

### Fixed
- Miqra al pi ha-Masorah importer: the `{{מ:כפול}}` template, which carries a verse in both
  cantillations (ta'am elyon and ta'am tachton), was discarded by the stylesheet, emitting the
  Ten Commandments as empty verses in Exodus 20 and Deuteronomy 5. The two readings now become a
  `tei:choice` of `j:option`, each carrying a `corresp` URN by which a setting selects one, and
  the manuscript apparatus attached to the merged doubly-accented text is preserved.
- Miqra al pi ha-Masorah importer: a row whose text contained a parashah break lost both its
  text and its verse milestone, dropping 54 verses across the project — among them Exodus 20:13,
  Deuteronomy 5:17, and most of the Shirat haYam and Ha'azinu shirah.
- JPS 1917 importer: the 22 acrostic stanza headings of Psalm 119 are no longer emitted as
  `tei:milestone[@unit='parsha']`; they become `@unit='acrostic'` and carry no URN.
- JPS 1917 importer: parsha URNs are transliterated path segments
  (`…/ki_teitzei`) instead of raw Hebrew with literal spaces, and `@n` carries the canonical
  name (`לך־לך`, not `לךלך`).
- JPS 1917 importer: the opening parshah of each book of the Torah, which has no running head in
  the source, is now emitted. All 54 parshiyot are present.
- JPS 1917 importer: each generated file declares its own document URN instead of all 44 sharing
  `urn:x-opensiddur:text:bible:tanakh@jps1917`.

## [0.1.0] - 2026-05-26

Initial public release.

### Added
- JLPTEI v2 schema source (`schema/jlptei.odd.xml`) and build pipeline (`scripts/build-schema.sh`) producing RelaxNG output for validation.
- Import tooling for canonical sources:
  - WLC importer: `uv run python -m opensiddur.importer.wlc.wlc`
  - JPS 1917 MediaWiki importer: `uv run python -m opensiddur.importer.jps1917.convert_wikisource`
- Reference database sync for resolving `urn:x-opensiddur:` URIs to project files:
  - `uv run python -m opensiddur.exporter.refdb`
- Compilation and export pipeline:
  - Compiler (JLPTEI → compiled linear XML): `uv run python -m opensiddur.exporter.compiler`
  - TeX export (compiled XML → LuaLaTeX): `uv run python -m opensiddur.exporter.tex.latex`
  - PDF export (compiled XML → PDF): `uv run python -m opensiddur.exporter.pdf.pdf`

### Known limitations
- This is a pre-1.0 release; schemas, CLI flags, and module APIs may change quickly.
- PDF/TeX output requires an external TeX toolchain and may need environment-specific tuning.

