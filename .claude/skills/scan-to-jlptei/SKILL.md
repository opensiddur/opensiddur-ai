---
name: scan-to-jlptei
description: Convert scanned books to JLPTEI by reading page images, checking independent text, authoring source-grounded XML, and verifying rendered PDFs. Load the relevant scan subsection for edition-specific conventions.
---

# Reading scans into JLPTEI

The page image is the source. OCR and existing transcriptions are proofreading
checks, never substitutes for reading the print. Preserve edition-specific text,
pointing, rubrics, poetry, and apparatus; do not silently import a familiar wording.

## Dynamically loaded scan subsections

Identify the edition and Archive item before applying any scan-specific rules.
Load **only** its subsection. Load both only for an explicit comparison.

| Scan / names | Archive identifier | Subsection |
|---|---|---|
| Birnbaum, ha-Siddur ha-Shalem, Daily Prayer Book, 1949 | `PhilipBirnbaumHaSiddurHaShalemTheDailyPrayerBook1949` | [Birnbaum 1949](reference/scans/birnbaum-1949.md) |
| Asher, Selichoth / Selichot / Slichot, 1912 reprint | `selichothdavidasher1912` | [Asher 1912](reference/scans/asher-1912.md) |

For another scan, start with this shared workflow. Establish its conventions from
images, record them in a new `reference/scans/<edition>.md`, and add one routing row.
Do not load other editions as a source of defaults for its glyphs or pagination.

## Shared workflow

1. Read repository authoring instructions and the selected scan subsection.
2. Fetch metadata and derive a leaf map. Separate scan identity, printed labels,
   language, and verified translation pairing. Unknown labels stay unknown; no
   parity-based language or pairing guesses. Record image corrections separately.
3. Cache full-resolution images outside git. Read whole pages for structure, then
   overlapping bands and targeted crops for ambiguous pointing and punctuation.
4. Write a scan-first reading before opening OCR or another transcription. Keep
   poem structure distinct from prose wrapping. Commit readings and provenance.
5. Compare an independently derived check of the same content. Use English OCR
   only for English; when no Hebrew transcription exists, make an independent
   image reading. Record comparison source, scope, corrections, and unresolved
   findings. A diff cannot detect an error shared by both readings.
6. Return to the image to adjudicate differences. Do not transfer an edition’s
   mechanical settlement rules to another edition. A second reader can triage
   difficult marks; verify its claims against crops and retain uncertainty.
7. Author JLPTEI with source-page links and registered URNs. Preserve the printed
   forms of abbreviations in `tei:choice/tei:abbr`; put verified editorial
   expansions in `tei:expan`. Document expansion and transclusion decisions.
   When an expanded view supplies the requested text, omit the instructions that
   requested that expansion. Retain instructions whose requested text is absent.
8. Validate and resolve references. Reverse-check the **printed** XML branch
   against the readings in source-page order. Audit editorial additions separately.
9. Compile each intended view and measure its actual PDF. Read
   [PDF measurement methods](reference/measuring-the-pdf.md) at this stage.
   Verify alignment, text presence, apparatus, and direction using glyph positions.
   Confirm checks reject deliberately broken controls.

## Authoring and operation

- `schema/jlptei.odd.xml` and validation are authoritative; consult
  `schema/JLPTEI-3.md` for alignment, milestone scope, contributors, and transclusion.
- Give divisions a semantic identity or a real grouping purpose. Use distinct
  instruction URNs for distinct rubric texts. Page breaks may occur inside prose.
- Build the final book from reusable text modules from the outset. Put each
  independent piyyut or prayer in its own file, named for its established common
  name or distinctive incipit. Use source-independent canonical URNs (for example,
  `urn:x-opensiddur:text:prayer:ashrei`); the edition belongs in the publication
  URN's `@project` suffix and source metadata. Do not put a scan name, experimental
  phase such as “pilot”, or a service position into a reusable text's identity.
  Reuse existing registry identities for common prayers and their parts; do not
  identify a single petition as an entire longer prayer. Keep service-order files
  as assemblies of URN transclusions and printed rubrics. `index.xml` is the book
  entrypoint; incomplete coverage belongs in edition metadata and documentation,
  rather than in text identities. Verify references, source order, alignment and
  both rendered views after splitting modules.
- Keep grouping files only for real, useful book or service divisions supported
  by the source. Do not create files for temporary reading batches or editorial
  positions such as “before the piyyut”, especially when they contain piyyutim.
  A service should directly transclude its independent texts and retain its
  printed rubrics. Put the conditional replacement for a printed cue alongside
  that cue, so expanded settings can use the same service assembly. Remove
  redundant view-specific assemblies and their obsolete URNs; update the importer
  so regeneration does not recreate deleted scaffolding.
- Alignment needs exact shared URNs, at the granularity the translation supports.
  Reusing a correspondence within one document can silently break alignment.
- Readings, verse structure, headings, rubrics, and notes are different evidence
  streams: compare like with like and check all streams for omissions.
- The book’s author/translator belongs in source metadata. Register contributor
  URNs for the people responsible for this transcription, not check-source editors.
- Refresh the reference database for the project directory being built. Run builds
  and tests serially because both use it. Keep images, TeX, XML, and PDFs in output/.
- Exercise conditional passages with settings making them both true and false.
  Schema validity alone cannot establish correct rendered content.
