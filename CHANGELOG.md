# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- The English side of the Birnbaum siddur, from two new sources over the same scan
  (`opensiddur/importer/util/internet_archive.py`,
  `opensiddur/importer/birnbaum_siddur/{en_wikisource,internet_archive}.py`). The Hebrew Wikisource
  edition already downloaded is not a faithful reproduction of the 1949 printing — it renders
  Birnbaum's English rubrics into Hebrew of its own and omits the English-only front matter — and
  it holds none of the translation: its 408 English leaves are `{{iwpage|en}}` stubs transcluding
  en.wikisource, and its 405 Hebrew leaves carry English footnote commentary nothing had captured.
  The Internet Archive item and the Commons file Wikisource transcribes are provably the same scan
  (both report SHA-1 `4208e06b…` at 488,138,938 bytes), so the Archive's OCR of the whole book
  pairs with the transcription leaf by leaf for nothing: **IA leaf `n` is scan page `n + 1`**,
  checked against all 361 pages where both sources state a printed page number, with none
  disagreeing. Four whole-book derivatives (~1 MB) are fetched rather than 815 per-page files, and
  their search text is sliced into `ia/ocr/NNN.txt` using the Archive's byte-offset page index —
  on bytes, since the file holds 40,983 non-ASCII bytes and decoding first would shift every leaf
  after the first of them. English Wikisource supplies `en/`: 284 of 815 pages exist, of which 129
  are proofread or better and non-empty, so it is a quality overlay on the OCR rather than a
  replacement. Everything on disk is named by scan page, never by leaf, so `text/100.txt`,
  `en/text/100.txt` and `ia/ocr/100.txt` are one leaf and the off-by-one lives in one function.
  `ia/ocr/` on a Hebrew page is not prose: the OCR reads Hebrew as Latin gibberish and interleaves
  it with the real English footnotes, which the region-segmentation stage will separate.
- `internet_archive.py` reuses the Wikisource client's pacing and backoff rather than growing a
  second idea of politeness. archive.org's bot policy sets no numeric rate limit but requires a
  descriptive `User-Agent`, honouring `429` and `Retry-After`, exponential backoff, and preferring
  bulk endpoints; the existing client already does all of that, so the only addition is the model
  name the policy asks of AI-agent clients (`--agent-model`, `$OPENSIDDUR_AGENT_MODEL`), omitted
  entirely for a human-invoked run.
- A Wikisource downloader that follows Wikimedia's rules, and a Birnbaum siddur importer built on
  it (`opensiddur/importer/util/wikisource.py`, `opensiddur/importer/birnbaum_siddur/`). The JPS
  1917 downloader scrapes `action=raw` and an Atom history feed through `/w/index.php` at two
  requests per page, sends no `maxlag`, ignores `Retry-After`, and refetches the whole book every
  run. The new client reads the Action API instead: batched 50 titles per request, `maxlag=5`,
  backoff on 429 and replication lag, strictly serial as the unauthenticated concurrency limit of
  1 requires, and gzipped. The contact address in the `User-Agent` is now a `--contact-email`
  parameter (or `$OPENSIDDUR_CONTACT_EMAIL`) with no default, because the address baked into the
  old downloaders was `opensiddur@example.com`, a reserved domain that reaches nobody.
  `manifest.json` records each page's revision id, so a re-run probes revisions and rewrites only
  what changed — for the 815-page Birnbaum siddur that is ~17 requests and no file writes, against
  ~1,630 requests before. Downloads all 815 pages into `sourcetexts/sources/birnbaum_siddur/`
  as `text/NNN.txt` and `credits/NNN.txt`, matching the `jps1917` layout.
- The Birnbaum importer now also downloads the pages the scans transclude their text from. Those
  815 scan pages hold almost no text — median size 109 bytes — because 405 of them are mostly
  `{{#קטע:PAGE|SECTION}}` calls, the Hebrew localisation of `{{#lst:}}` (labeled section
  transclusion), with the text living in mainspace pages. The client gained generic support for
  that mechanism (`find_transclusions`, `find_sections`, `is_redirect`, `download_closure`),
  matching the localised parser-function and tag aliases rather than only the English spellings,
  which is what hid this to begin with. 324 subtree pages land under `source/`, transitively
  referenced pages outside it under `external/`, both mirroring the wiki's title hierarchy as
  directories; a new `structure.json` records which named sections each page defines and which it
  transcludes, including for the scan pages, since that is what ties printed pagination to
  liturgical text. Redirects are kept — 151 of the subtree pages are redirects carrying
  alternative names for a service.

### Fixed
- Batched Action API queries are sent as POST. Fifty Hebrew subpage titles percent-encode past the
  URL length limit and the server answered `414 URI Too Long`, so batching was silently capped by
  URL length on any wiki whose titles are not short and Latin.

### Changed
- The JPS 1917 downloader now reads the Action API through the shared client, like the Birnbaum
  importer does. It had been scraping `action=raw` plus an Atom history feed through
  `/w/index.php` — two uncached, unbatched requests per page, so ~2,300 for the book's 1,152
  pages, where 50 batched API requests do the same work — sending no `maxlag`, ignoring
  `Retry-After` in favour of a flat three-retry loop, and refetching every page on every run. It
  also identified itself with `opensiddur@example.com`, a reserved domain that reaches nobody and
  so fails Wikimedia's User-Agent policy; the address is now `--contact-email` or
  `$OPENSIDDUR_CONTACT_EMAIL`, with no default, and `--force` refetches regardless of the
  manifest. The page range is no longer hardcoded: `list_book_pages` reports what is actually
  transcribed, which also retires a stale `start_page = 443` left behind by a partial re-run. The
  `sourcetexts/sources/jps1917/` layout and its four-digit filenames are unchanged.
- The download loop the two Wikisource importers would otherwise duplicate now lives in
  `opensiddur/importer/util/wikisource_book.py`: the manifest, the zero-padded page naming, and
  the enumerate → probe revisions → fetch only what changed → write pass. `util/wikisource.py`
  stays free of filesystem knowledge; what remains in each importer is what is particular to its
  book, which for Birnbaum is its mainspace source tree and `structure.json`, and for JPS is
  nothing beyond the book's name and where its files go.
- Credits now name registered accounts only, and are written in sorted order rather than whatever
  order a `set` happened to yield. `prop=contributors` reports anonymous edits as an aggregate
  count rather than by address, so the five JPS credits files that listed a bare IP no longer do —
  a TEI `respStmt` wants people who can be identified. MediaWiki's temporary accounts
  (`~2026-44995-25`), which under IP masking stand in for logged-out editors, are excluded on the
  same reasoning, alongside bots. The old Atom feed was also capped at its most recent entries, so
  pages with long histories gain the names it never showed.
- The JPS TEI `sourceDesc` now reports the date the Wikisource pages were actually downloaded,
  read from the manifest, instead of a date written into the source once by hand and left to go
  stale. Conversions of a tree with no manifest keep reporting the old literal date.
- `RELEASE_PROCEDURE.md` now says to re-lock and push `uv.lock` after a release. The release script
  writes the new version into `pyproject.toml` but never re-locks, so `uv.lock` kept the previous
  version and the next `uv sync --all-groups` left a modified lockfile in the working tree — which
  then collides with the "must be clean" check the procedure opens with.

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
