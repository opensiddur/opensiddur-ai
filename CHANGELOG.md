# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- An electronic-book output format (#92): one self-contained HTML file. Its undecided
  passages are resolved on the reader's device, against settings the reader chooses in the
  book: the rite, who is present, a house of mourning, and the like. The text changes as
  they do, and they are remembered in the browser. Read without scripts, the page is the
  printed book. Passages that turn on the date, the time or the place are not yet decided
  on the device, and show every option with its rubric, as in print.
  - `python -m opensiddur.exporter.compiler --destination electronic` leaves the reader's
    settings undecided, and records on each undecided conditional what the compile did
    know (`p:pinned`).
  - `python -m opensiddur.exporter.html.html` renders the compiled file.
  - `python -m opensiddur.exporter.books --format html` builds the electronic books in the
    settings directory, alone or alongside the PDFs.
  - Every release attaches each book as `<book>-<variant>-<tag>.html` as well as `.pdf`. The
    electronic book is built first, and a PDF that fails does not keep it off the release.
  - The device's evaluator is a JavaScript port of the compiler's. The two are tested
    against one corpus of cases, the JavaScript under Node.

### Fixed
- Undecided conditional scopes keep both of their markers through compilation (#219). In a
  compiled Birnbaum, 652 of 1459 scopes had lost their `j:endConditional` and 12 their
  `j:conditional`. In the PDF, each of those opened a bracket or rule that never closed.
  There were four causes:
  - A segment with no words, pruned after a div is split around a transclusion, took any
    marker it held with it.
  - A range transcluded from the middle of a file picked up the markers and rubrics of scopes
    before its start.
  - A range that ended inside a scope never closed it.
  - Each level between a file's root and the range rewrote ids its children had already
    rewritten, so ids carried their path hash several times over.

  A range now carries the markers of exactly the scopes that overlap it. The compiler warns
  about any marker that still doesn't pair. A range that ends on a transclusion now ends
  there, instead of running on to the end of its file.

## [0.5.1] - 2026-10-05

### Fixed
- Release books build again on CI. `install-tex.sh` did not install `texlive-lang-arabic`, which
  provides `luabidi.sty`; polyglossia's Hebrew module loads it under LuaLaTeX, so every book
  with Hebrew stopped at the preamble and the v0.5.0 release went out without its PDFs.

### Pinned sources

- `opensiddur-projects`: cf50102c451a1823e88656c52f74131b5e180e9d
- `sourcetexts`: 5927629e34a555649f6c35e3e5b814be9e7205b2

## [0.5.0] - 2026-10-05

### Added
- Printed books at release (#153). Exporter settings files gain an optional `book:` key naming
  the root file they format, so the compiler needs only `-s`, and an optional `description:`.
  `opensiddur-projects/settings/<book>/<variant>.yaml` holds the books, several variants per
  book allowed (an annual and a triennial humash): `python -m opensiddur.exporter.books` builds
  them all, and when a release is published the new `release-books.yml` workflow starts one
  `release-book.yml` job per settings file, which builds that book and attaches it as
  `<book>-<variant>-<tag>.pdf`. A book that fails is not attached and its job goes red; the
  others are unaffected. opensiddur-projects pull requests now run `books --check`: each settings file is
  where it belongs, parses, matches the schema, names a project and file that exist, and has an
  installed font for every font chain it will be set with.

### Fixed
- Page breaks no longer strand a line or a heading in the PDF (#198). The last line of a
  paragraph no longer opens a page and its first line no longer closes one. A heading,
  together with its translated title, stays whole and on the same page as at least the first
  lines of what it heads. Each layout needed its own fix. In single-stream text, LaTeX's club
  and widow penalties of 150 were preferences, not rules, and nothing tied a heading's
  `\pstart` to the next. Under `pairs`, reledpar sets a column with every penalty zeroed, and a
  column's paragraphs and headings are all one `\pstart`, so the column's lines are now tagged
  and read back before each row is set. Under `pages`, reledpar ends each page itself by
  counting, so the same reading tells it to end a page early when the lines that must stay
  together would not fit.
- A rubric set on lines of its own is no longer left at the foot of a page with the text it
  introduces on the next. A rubric of up to five lines stays whole with that text, and a longer
  one keeps at least its last five lines with it. This also holds when the rubric ends its
  block, as "Reader:" and "Chanted on the eighth day of Sukkoth during Musaf" do in the
  Birnbaum compiles, and the text, or the heading over it, starts the next block. One case is
  not covered under `pages`: a rubric that ends its block while the facing page runs on further.
  reledpar then pads the rubric's page with blank lines until the facing page catches up, so
  the rubric is parted from its text by that padding anyway.

### Pinned sources

- `opensiddur-projects`: cf50102c451a1823e88656c52f74131b5e180e9d
- `sourcetexts`: 5927629e34a555649f6c35e3e5b814be9e7205b2

## [0.4.0] - 2026-10-02

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
- `pages.json`, the table that says what each of the Birnbaum siddur's 815 leaves is and where its
  text comes from (`opensiddur/importer/birnbaum_siddur/correspondence.py`), plus a `download.py`
  front door running all four stages in the order they depend on — the reconciliation reads all
  three layers off disk, so running the commands by hand in the wrong order yields a table
  describing a book that is no longer there. Each page records its IA leaf, printed page number
  and where that number came from, which side of the opening it is, its facsimile URL, its facing
  page, and its text source. Three things it works out rather than assumes. **Side** comes from
  the markers, never from parity: ten pages break the odd-English/even-Hebrew rule, in two
  contiguous runs that print Hebrew with no facing English at all, and a parity rule would
  mis-pair everything after each run — those 20 pages are reported as unpaired rather than
  wrongly paired. **The running header** is parsed by argument shape, not position: the printed
  page number sits in the first, second or third slot depending on the variant, and reading slot 0
  positionally loses 44 of the 405 pages that carry one. **The printed page number** prefers the
  human transcription over OCR, but checks the sequence for monotonicity and falls back to the
  Archive where a transcribed number goes backwards — which catches exactly one page in the book,
  scan 738, where the running header was copied from scan 722 and its `697` never updated to
  `713`. Both readings are kept and the correction is reported, and a number that cannot be
  repaired is left alone and flagged rather than invented; `--check` exits non-zero on those.
- The Archive stage now leaves its manifest and its 815 OCR files untouched when nothing changed,
  matching the Wikisource downloaders. Rewriting a manifest whose only difference is its own
  timestamp turns a run that fetched nothing into a diff, which teaches people to ignore diffs on
  exactly the file that records provenance. `pages.json` is held to the same rule.
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
- A third parallel layout, `typography.parallel.layout: interleaved`, for a measure too narrow to
  split into columns: each aligned block is followed by its translation in one column rather
  than set beside it (#112). `parallel.column_order` decides which text comes first, and the new
  `typography.parallel.interleaved` settings decide how the translation is set apart
  (`translation_size`, `translation_indent`, the `spacing` between a block and its translation)
  and whether its lines are numbered (`line_numbers: primary | both`). Headings, rubrics,
  bookmarks and the `-alt` running heads behave as in columns, with the text that comes first
  as the first column. The whole run is one reledmac numbered section, with the direction
  changing from one paragraph to the next; reledpar is not loaded.

### Fixed
- Honor exact registered URNs before stripping numeric subdivisions during reference-database checks. Canonical Mishnah references such as `tamid/7/4` no longer fail as unregistered.
- `ReferenceDatabase.get_references_to` dropped references in different files or projects that
  happened to sit at the same element path, such as the first note of two notes files targeting
  the same URN; only one of them reached the compiled output. It now treats references as the
  same only when project, file and path all match (#173).
- Hebrew reads the right way round in the table of contents. A contents entry is written once
  and read twice — hyperref builds a PDF outline string from it, and `\tableofcontents`
  typesets it on a page — and only the outline existed when it was first written, so the entry
  took the heading's own language and left Hebrew titles unwrapped. The contents page runs in
  the document class's direction, not the heading's, so every Hebrew line of it came out
  reversed. Each run now takes its own wrapper, as a running head already did.
- Contributor URNs are validated. Nothing checked them before: `specs/urn_registry/` had no
  contributor file and the reference validator looked only at `@target`/`@targetEnd`, so a
  misspelt identifier on `tei:name/@ref` was not a broken link but a different person, credited
  silently — the only signal was a warning at typeset time, after the credit had already been
  set. The shape is now enforced by Schematron (so an ordinary file validation catches it), the
  new `specs/urn_registry/contributor.jsonl` is the roster, and both
  `validate_urn_references` and `urn_registry --check` apply the rules in CI. `opensiddur.org`
  identifiers are ours, so they must be registered; wikisource usernames arrive from the wiki
  and are grammar-checked only. The malformed references fixed by hand below would now fail a
  build rather than waiting to be noticed.
- The author of a source is no longer credited as a contributor. Meir Halevi (Wolf) Heidenheim
  carried an `edt` "Edited and published by" `respStmt` on all 97 files of
  `heidenheim_haggadah_1822`, while also standing as `tei:author` in the project's source bibl.
  A `respStmt` credits whoever made the *digital* text, so this claimed he did work he did not do
  and, having no `@ref` to a contributor URN, made the LaTeX exporter warn once per file and list
  him under no namespace heading. He is removed from every `titleStmt` and stays in the
  bibliography, where a reader looking for who made the book will find him: the exporter gathers
  each referenced project's `index.xml`, so the printed Sources section is unchanged.
  `opensiddur/importer/feinstein_haggadah/heidenheim_haggadah_1822_header_stub.xml` no longer
  emits the credit, so re-running the importer will not put it back.
- Both haggadah header stubs wrote contributor references as `urn:x-opensiddur:opensiddur.org/…`,
  missing the `contributor:` type segment the URN form requires. The committed project XML has the
  correct shape, so re-running either importer would have regressed the references it writes and
  made the LaTeX exporter report each one as "not a contributor URN".
- The humash importer wrote the same malformed shape,
  `urn:x-opensiddur:opensiddur.org/efraim-feinstein`. As with the haggadah stubs, the projects had
  already been corrected and the generator had not, so a regeneration reintroduced it.
- `schema/JLPTEI-3.md` now says that a contributor namespace is a claim about the person rather
  than a default — `opensiddur.org/` names someone who contributed to Open Siddur — and that a
  source's translator or editor gets no contributor URN at all, belonging in the `tei:bibl`
  instead. Nothing said this, which is how a credit under an invented identifier passed review.
- Batched Action API queries are sent as POST. Fifty Hebrew subpage titles percent-encode past the
  URL length limit and the server answered `414 URI Too Long`, so batching was silently capped by
  URL length on any wiki whose titles are not short and Latin.
- Line numbers in a Hebrew text outside reledpar columns were printed over the first word of
  each line instead of in the margin. reledmac hangs the number off a line-width box built in
  the prevailing direction, so in right-to-left text its "left" edge was the right-hand one. The
  box now has a fixed left-to-right direction, and `line_numbers.margin` names the same margin
  for Hebrew lines as for English ones.
- Unnumbered lines put reledmac's per-page line-number restart early, so numbering began again
  partway down a page. reledmac counts an unnumbered line but wrote no page record for it; it
  now writes one for every line.
- A line break that ended its paragraph set an empty line, with a line number of its own, before
  the paragraph's end. Verse is encoded line by line and a source closes the last line of a
  paragraph with a `tei:lb` like every other, so a psalm aligned verse by verse carried a blank
  numbered row after every verse, in every layout. A break with nothing that prints after it
  before the paragraph ends is now dropped; a break before a rubric likewise, since the rubric
  breaks the line itself.
- A note on a whole division — which the compiler sets beside the division's heading rather than
  in any of its paragraphs — was set after the heading as a mark alone on a line of its own,
  and where the heading was hoisted above the columns, under a heading that had already been
  set. It is now set after the title of the heading it is about: in the heading itself, in the
  heading set across the page (given a numbered section of its own for the purpose), or, where
  a column suppresses its copy of the heading, on that column's placeholder row. A division of
  only a heading and rubrics, as the haggadah has, keeps its note this way too.
- The Birnbaum Minḥah commentary on **מנחה** targeted the Ashrei division instead of the service
  whose title it explains; it now targets `chol/minchah` (opensiddur-projects).
- The rule marking a conditional paragraph was sized to `\hsize` and ignored the paragraph's own
  indents, so in an indented paragraph (a list item, an interleaved translation) its box overran
  the right margin by the indent.
- The facing-pages layout, `typography.parallel.layout: pages`, now keeps a spread together
  (#113). A heading a parallel block opened with was hoisted out to span the page, as it is in
  columns, but `\Pages` cannot be interrupted and starts its spread on the next verso, so the
  heading was left alone on a page of its own, often with a blank page after it. Facing pages
  now hoist nothing: each page sets its own heading, and under `headings.from: combined` both
  pages do so even where the titles agree. The blank recto `\Pages` inserts to start a spread
  on a verso no longer carries a running head, and the space between aligned units is no longer
  halved, which was right only for `\Columns`. A verso's running head names its own text with
  `{section-title}`, a recto's with `{section-title-alt}`. A Hebrew page's line numbers were
  printed over the first word of their lines, because `\Pages` builds a Hebrew page's rows right
  to left and the outer margin was then each row's far end; they now sit in the outer margin.
- `typography.parallel.column_width` and `column_position` were accepted under the `pages` and
  `interleaved` layouts and did nothing; naming either outside `pairs` is now a settings error.
  The stylesheet's own default layout was `pages` while the settings model's is `pairs`; it is
  now `pairs` too.

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
- `RELEASE_PROCEDURE.md` is now the only release documentation. Its pre-flight gains the two
  checks that until now lived only in `specs/RELEASING.md` — `uv run coverage report -m` and
  `uv build` — and `dist/`, where `uv build` writes, is gitignored so the build check does not
  leave the working tree dirty.

### Removed
- The unused LangGraph text-encoding agent (`opensiddur/importer/agent/`), along with the
  dependencies only it used (`langgraph`, `langgraph-supervisor`, `langchain`, `langchain-openai`,
  `langchain-community`, `diff-match-patch`) and those nothing used (`openai`, `chromadb`,
  `unstructured`, `markdown`, `pyppeteer`).
  `pyyaml` and `pypdf`, which the code imports but had only been installed through those
  dependencies, are now declared directly.
- `specs/RELEASING.md`, a v0.1.0-era release guide superseded by `RELEASE_PROCEDURE.md` and the
  release script. It described tagging and publishing by hand, which the script now does.

### Pinned sources

- `opensiddur-projects`: 73555a3feb879a0c374a400701b4f9416a22012f
- `sourcetexts`: 5927629e34a555649f6c35e3e5b814be9e7205b2

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
