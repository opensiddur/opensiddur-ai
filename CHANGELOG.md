# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-08-21

### Added
- Sub-verse URNs. A URN reached no further than a whole verse, so a reading that begins or ends
  inside one could not be said: Emor's third-year haftarah is Nachum 2:2b–3a, the Thirteen
  Attributes open partway through Exodus 34:6, and kiddush opens on the last words of Genesis
  1:31. Two milestone units now divide a verse, each hanging its URN one path component below
  the verse's, so no URN grammar changes: `half-verse` (`…/1/31/a`, `…/1/31/b`), the accentual
  division at the etnachta, placed mechanically on every verse the accents divide; and
  `verse-part` (`…/34/6/adonai_adonai`), any other break at a word boundary, named by its
  transliterated incipit and declared in `opensiddur/common/subverse.py`. See JLPTEI-3.md,
  "Sub-verse scope", for what the two cover and what they deliberately do not.
- Ranges may state their end absolutely: an end beginning with `/` replaces the whole path below
  the work, so `…:nahum/2/2/b-/2/5` runs from a half-verse to the end of a whole one. The
  relative form always lands at the start's own depth and cannot express that.
- `validate_urn_references` reports references that resolve only after a division is dropped
  from the end of them, so that reading a whole verse where half was asked for is never silent.

### Fixed
- A range whose relative end was deeper than the start it replaced — `…:nahum/2/2-2/3/a` —
  silently built a URN with the scheme sliced off it, which then resolved to nothing. It is now
  rejected, with the absolute spelling named in the message.
- Parallel alignment joined on exact URN equality, so an edition that divided the text more
  finely than the one beside it put its subdivisions in rows facing empty cells. Rows are now
  formed at the divisions both sides carry.

### Pinned sources

- `opensiddur-projects`: 075863d9754578b4b46a221a4dfdc0c5c3c1b9ef
- `sourcetexts`: 9557244eacdd33d03906148a0bfc67600664dff6

## [0.2.0] - 2026-08-17

### Added
- Shared table of the 54 weekly parshiyot (`opensiddur/importer/util/parshiyot.py`), mapping any
  source's spelling of a parshah name to a canonical Hebrew name and a URN slug.
- The humash emits the triennial haftarot: 150 readings over 51 parshiyot, each a headed
  alternative to the annual haftarah of its week rather than an addition to it.
- `opensiddur:reading-cycle`, the feature structure by which a volume says which haftarot it
  carries: `annual`, and one binary per year of the triennial cycle, so that a volume may be
  for one Shabbat or for a whole three-year cycle. `opensiddur:torah-reading` gains
  `triennial-year`, the cycle year of the declared date.

### Fixed
- `readings.triennial_haftarot` was read but never called, and dropped the 36 readings hebcal
  records as a list of pieces. A piece lying inside one already listed is the verse the pairing
  with the parshah turns on, and is no longer taken for a continuation of the reading.
- `parse_hebcal_ref` no longer raises on a boundary stated inside a verse, such as the
  Nachum 2:2b-2:3a of Emor's third year.
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

### Pinned sources

- `opensiddur-projects`: ba29479e194a3426f9aa7fd59eb9d526a85ddf5b
- `sourcetexts`: 2e59018fba559edc22affa47135d8f5c006e95c0

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
