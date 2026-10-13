# Reproducing the Asher Selichoth encoding

Use the three companion `feat_asher-selichot-pilot` worktrees; the branch name
is historical. Pass standalone source/project directories explicitly. Initialize
code submodules, install dependencies and build the schema before validation.
Archive requests use efraim@opensiddur.org. Scan images, OCR cache, compiled XML,
TeX and PDFs remain untracked under `output/asher_selichot`.

LuaLaTeX needs a writable font cache in this sandbox, including when invoked by
PDF geometry tests. Set it before either rendering or the full test suite:

```bash
export TEXMFVAR=/tmp/asher-tex-cache TEXMFCACHE=/tmp/asher-tex-cache
.venv/bin/python -m pytest
```

## Current coverage

Both title pages and all services through the final circumcision pizmon, Archive
n410 (printed204), are encoded. There are 398 project XML documents, 199 per
language. All validate and reverse-check against documentary readings; both
projects resolve references. The registry has 4008 records, zero errors/warnings.
Independent Hebrew proofreading remains pending. A previously omitted final-page
verse is restored by image proofreading; see the correction checkpoint below.

The checkpoints below record earlier scopes and results; the final section records
the current rendering and test run.

## Seven-day checkpoint

Both title pages and the first seven complete days are encoded through Archive
n99/n100, stopping before the Erev Rosh Hashanah body heading. There are 150 XML
files, 75 per language: 66 independent named texts and nine book/service
assemblies. Independent piyyutim use incipit URNs; common prayers retain their
common identities. Edition provenance is in `@project`; artificial batch
groupings remain removed.

Days four through seven cover n67–76, n75–84, n83–92 and n91–100. Hebrew retains
verse and refrains, English retains printed prose and anchored footnotes.
Numbered-day headings are top-level bookmarks above their pizmons, and all four
local settings generate contents through level two. The invocation
אלהינו ואלהי אבותינו remains body text.

Printed pages 31 and 32 have swapped Archive openings: Hebrew order is s60,
s62, s66, s64, s68; English is s61, s63, s67, s65, s69. Scan identities, observed
labels and verified bilingual pairing remain separate in source evidence. The
English printed page-47 numeral is not legible; its observed label stays
unknown, while verified Hebrew pairing identifies the printed opening.

Expanded services transclude verified Asher prayer ranges and omit fulfilled
instructions. Day five has only two El Melekh/Vayaavor pairs. Day six's final
opening cue is Hebrew-only. Day seven retains the extra English introductory
refrain cue and expands it only in its printed position; its Hebrew repetition
rubric names the refrain limits in reverse order, while expansion follows the
verified complete refrain. The unprinted Full Kaddish comes from Birnbaum via
default settings. Days two through seven set `first_day=false` and
`aseret-ymei-tshuva=false`, then restore caller context. Day one sets
`first_day=true`, with Ten Days false. No Erev Rosh Hashanah text is included.

## Regeneration and reference checks

```bash
python -m opensiddur.importer.asher_selichot.download --source-root "$source_root" --output-root "$output_root" --regenerate
python -m opensiddur.importer.asher_selichot.build --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.importer.asher_selichot.verify --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.exporter.refdb --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_he_1912 --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_en_1912 --project-directory "$project_root"
python -m opensiddur.common.urn_registry --check --project-directory "$project_root"
```

All 150 XML files validate. Documentary text, source order, footnote anchors,
choice branches and expansion targets match the adjudicated scan readings.
Both projects resolve all URNs/transclusions, and the registry reports zero
errors/warnings. Immutable first readings, image adjudications and English OCR
comparison provenance are committed in the source repository. Same-assistant
image rechecks are not independent Hebrew proofreading.

The Asher scan subsection records the new conventions; shared rules and the
Birnbaum subsection remain separate. Skill frontmatter validates and relative
reference links resolve.

## Compile, render and audit

```bash
export TEXMFVAR=/tmp/asher-tex-cache
export TEXMFCACHE=/tmp/asher-tex-cache
python -m opensiddur.exporter.compiler -s specs/asher_selichot/documentary.yaml --project-directory "$project_root" -o "$output_root/asher_selichot/selichot.xml"
python -m opensiddur.exporter.pdf.pdf -s specs/asher_selichot/documentary.yaml --project-directory "$project_root" --keep-tex --build-dir "$output_root/asher_selichot/build-selichot" "$output_root/asher_selichot/selichot.xml" "$output_root/asher_selichot/selichot.pdf"
python -m opensiddur.exporter.compiler -s specs/asher_selichot/expanded.yaml --project-directory "$project_root" -o "$output_root/asher_selichot/selichot-expanded.xml"
python -m opensiddur.exporter.pdf.pdf -s specs/asher_selichot/expanded.yaml --project-directory "$project_root" --keep-tex --build-dir "$output_root/asher_selichot/build-selichot-expanded" "$output_root/asher_selichot/selichot-expanded.xml" "$output_root/asher_selichot/selichot-expanded.pdf"
python -m opensiddur.importer.asher_selichot.check_book_pdf "$pdf" --control
python -m opensiddur.importer.scan.pdf_direction "$pdf" "$tex" --control
```

Add `--expanded` for the expanded book check. PDF builds and the full suite run
serially because both use the reference database. Restore standalone companion
references after tests. SBL Hebrew at 12pt supplies phrase dots. The source-specific
geometry checks use 288pt/324pt alternating gutters, 16pt stanza tolerance and
apparatus fonts up to 10pt. Isolated reledmac line numbers are excluded from
prayer-word comparison.

| Rendered check | Documentary | Expanded |
|---|---|---|
| PDF pages | 76 | 218 |
| Current TOC destinations | 14 | 14 |
| First-day prayer starts | six 0pt differences | six 0pt differences |
| First pizmon stanza starts | first 13.55pt, seven 0pt | eight 0pt |
| Second/third pizmon stanza starts | six 0pt each | six 0pt each |
| Fourth/fifth/sixth/seventh stanza starts | 5/8/5/9 starts, all 0pt | 5/8/5/9 starts, all 0pt |
| Reversed Hebrew runs | 0 / 2,685 | 0 / 8,853 |
| Reversed-run control flags | 2,614 / 2,685 | 8,530 / 8,853 |

Book checks scope each day by outline destinations while retaining page parity.
They audit notes, language direction, fulfilled cues, prayer occurrences,
calendar contexts and the next-section boundary. Deliberately broken controls
reject duplicated notes, shifted stanzas, wrong choices, incorrectly nested
bookmarks, collapsed verses, wrong/stranded punctuation, omitted repetitions,
unwanted calendar additions and stale TOC numbers. Both rendered TOCs and new
pizmon/footnote pages were inspected visually, including the closing Full
Kaddish boundary. Daily PDF snapshots remain under `output/asher_selichot/checkpoints`.

## Asher phrase-dot binding regression

Image inspection exposed isolated phrase dots in the fifth-day documentary
PDF. The importer now binds phrase dots with a nonbreaking space and preserves
that space through Unicode decomposition. Reverse comparison normalizes
whitespace without discarding wording or punctuation. The geometry check
recognizes both the encoded middle dot and the SBL extracted glyph, rejects a
solitary dot control, and rejects the original fifth-day PDF on page 21. All
existing modules were regenerated; the final PDFs pass this check throughout.
This is an Asher authoring regression, not a generic compiler change.

## Generic TOC convergence defect

The initial expanded build stopped after two passes while the TOC still showed
third day on page 64; the heading and bookmark had settled on page 63. Its `.toc`
file had changed without a LaTeX rerun warning. Separate code PR #226 compares
`.toc` contents before/after each pass and requests another pass on change.
The 64 → 63 → 63 regression fails on the original driver and passes with the
fix; an unchanged TOC adds no pass. All 43 PDF-driver tests pass with writable
TeX cache settings. The fix is applied here for the final Asher PDF build.
The new book check reproduces and rejects the original stale TOC result.

Earlier generic TOC direction fixes remain separate in PR #225; earlier
conditional/transclusion and mixed-language apparatus fixes were tracked in
#217 and #218.

## Upstream merge, regressions and limits

Upstream code `main` advanced to 1e65d16 during this work and was merged as
762ecc6 after the fifth-day checkpoint. Eighty affected tests and 132 subtests
passed, with five skips; both compiled edition XML files were byte-identical
before and after the merge. Code and projects were checked against their main
branches before the seventh-day build; neither required another merge.

The Asher importer suite passes 38 tests and 12 subtests. Synthetic coverage
includes scan/book isolation, printed-order corrections, language-specific
cues, paragraph/verse structure, choices, day conditions, phrase-dot binding,
footnote direction, bookmark hierarchy and stale TOC detection.

The final full suite passes 3,247 tests and 4,812 subtests, with 20 skips,
in 688.65 seconds. This includes the Birnbaum regressions and current upstream
changes. The run uses writable TeX-cache settings; PDF builds run separately.
Standalone companion references are restored afterward, and both project URN
checks, the registry and source reverse verification pass again.

Independent Hebrew consonant/pointing proofreading remains pending, especially
for dense rhymed and martial vocabulary; specific unresolved readings are
recorded in source proofreading evidence. Conversion beyond the seven encoded
days, publication and release integration remain outside this work. Local
settings keep this incomplete volume out of automatic release builds.

## Daily history

The following measurements preserve each completed day's checkpoint. Later
renders incorporate the phrase-dot correction noted above. Completed daily
pushes before the final seventh-day checkpoint are:

| Day | Sources commit | Code head | Projects commit |
|---|---|---|---|
| Fourth | f16b9a8 | 0825780 | c3bf22a |
| Fifth | c793d2e | 762ecc6 (includes upstream merge) | cd3b54c |
| Sixth | 3ea9e49 | 9f66c1b | 85d8c3c |

## Fourth-day checkpoint (2026-10-07)

Complete day four on n67–n76 adds Ayeh kol nifleotekha, Aryeh bayaar damiti
and the five-stanza Beashmoret haboqer, in independent incipit modules.
The Hebrew פזמון heading precedes its printed repetition rubric. Hebrew and
English source page breaks differ; the final English stanza has no additional
full refrain before its opening cue. All eight English footnotes are retained.

All 126 XML files validate and match source readings; both projects resolve
URNs/transclusions and the registry has zero errors/warnings. Importer checks:
31 tests and 12 subtests. Full suite: 3,211 tests and 4,781 subtests passed,
18 skipped, in 606.48 seconds. After correcting the broken alignment control to
shift only English glyphs, the importer checks passed again.

Documentary: 56 pages, five fourth-pizmon start differences of 0pt, 0 reversed
Hebrew runs out of 1,904; the reversed control flags 1,859. Expanded: 130 pages,
five start differences of 0pt, 0 reversed runs out of 5,077; reversed control
flags 4,941. Both book checks pass with broken controls, including notes,
fulfilled cues, prayer boundaries and eight current TOC destinations. The TOCs
and documentary pizmon page were inspected visually. `check_book_pdf` now takes
`--source-root` so standalone companion evidence is used explicitly.

Independent Hebrew proofreading remains pending. Days five through seven are
being added in subsequent daily checkpoints; Erev Rosh Hashanah is outside scope.

## Fifth-day checkpoint (2026-10-07)

The bilingual service is complete through the next printed day heading. Schema validation, source-order reverse comparison, note/choice audits, standalone URN/transclusion resolution and registry checks pass. Independent Hebrew proofreading remains pending.

- Documentary: 63 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 2149 Hebrew runs are set left to right; control: 2098 of 2149 flagged when every run is reversed.
- Expanded: 159 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 6272 Hebrew runs are set left to right; control: 6091 of 6272 flagged when every run is reversed.

Both editions pass deliberately broken controls for alignment, note duplication, direction and stale contents destinations. Source-specific branch/join tests and importer checks pass. Rendered contents and the new pizmon pages were inspected visually.

## Phrase-dot binding and fifth-day upstream merge

Visual inspection at the fifth-day checkpoint found phrase dots stranded by wrapping. The sixth-day generator binds phrase dots to preceding words with nonbreaking spaces, including prose and expansion branches. Serialization preserves those spaces while normalizing source glyphs. The new geometry check rejects the original PDF (first occurrence on PDF page 21) and a synthetic isolated-dot control. Regeneration applies this correction throughout the encoded book.

Before the fifth-day push, upstream code main `1e65d16` merged cleanly as `762ecc6`. Post-merge checks passed 80 tests and 132 subtests, with five skips. Both documentary and expanded compiler outputs were byte-identical before and after that merge. Projects main was already contained.

## Sixth-day checkpoint (2026-10-07)

The bilingual service is complete through the next printed day heading. Schema validation, source-order reverse comparison, note/choice audits, standalone URN/transclusion resolution and registry checks pass. Independent Hebrew proofreading remains pending.

- Documentary: 69 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 2414 Hebrew runs are set left to right; control: 2352 of 2414 flagged when every run is reversed.
- Expanded: 188 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 7586 Hebrew runs are set left to right; control: 7340 of 7586 flagged when every run is reversed.

Both editions pass deliberately broken controls for alignment, note duplication, direction and stale contents destinations. Source-specific branch/join tests and importer checks pass. Rendered contents and the new pizmon pages were inspected visually.

Sixth-day importer checks: 37 tests and 12 subtests pass. All 142 XML files validate and documentary readings match. The Hebrew-only final opening cue remains absent from both English editions. Phrase-dot binding checks pass across the full book and detect the deliberately broken control.

## Seventh-day checkpoint (2026-10-07)

The bilingual service is complete through the next printed day heading. Schema validation, source-order reverse comparison, note/choice audits, standalone URN/transclusion resolution and registry checks pass. Independent Hebrew proofreading remains pending.

- Documentary: 76 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 2685 Hebrew runs are set left to right; control: 2614 of 2685 flagged when every run is reversed.
- Expanded: 218 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  0 of 8853 Hebrew runs are set left to right; control: 8530 of 8853 flagged when every run is reversed.

Both editions pass deliberately broken controls for alignment, note duplication, direction and stale contents destinations. Source-specific branch/join tests and importer checks pass. Rendered contents and the new pizmon pages were inspected visually.

## Erev Rosh Hashanah checkpoint (2026-10-08)

The complete bilingual service covers n99–n184 (printed 49–91), stopping after
the Reader’s Kaddish cue before the Fast of Gedaliah. Its 113 source-ordered units
retain immutable initial capture bytes, separate English OCR findings, targeted
image adjudications and initial/working hashes. Twenty-one independent text
modules per language plus the service assembly extend the projects to 194 files.
Canonical names use eloah, including el_eloah_dalefah_eini.

All XML validates; documentary readings, printed choice branches, 26 Tamid
printed note markers, footnotes, language-specific expansion targets and calendar
scopes pass reverse verification. All URNs/transclusions resolve with no registry
errors or warnings. The registry’s four existing alias-migration notes remain.

The 12 repeat cues compile as paired prose paragraphs with inline transclusions.
Printed-58 targets preserve the reprinted page-52 translation; cues citing 9/10
retain the earlier readings. Fulfilled instructions are omitted from expansion,
Ark instructions stay in their printed positions, and secondary Full Kaddish is
scoped with first_day=false and Ten Days=false.

Compiler PR #231 isolates the inline-boundary fix: both new regressions fail on
the original code; 100 focused compiler tests pass with it. The fix is applied to
this branch. Importer checks pass 51 tests and 12 subtests. Upstream main 1427f08
was merged as f1a98f7 before the full suite; the companion branches already
contained their upstream main/master.

Documentary: 139 pages and 17 TOC/bookmark destinations; the six checked Erev
starts have differences [0, 0, 0, 0, 0, 0]pt. No Hebrew runs are left to right
among 5,580; the reversal control flags 5,248. The first-day pizmon’s measured
13.55pt difference remains within its scan-specific 16pt bound; all later checked
stanza starts match. The service opening and pizmon were inspected visually.

Expanded: 303 pages and 17 TOC/bookmark destinations; the six checked Erev starts
have differences [0, 0, 0, 0, 0, 0]pt. No Hebrew runs are left to right among
12,793; the reversal control flags 12,004. Both pizmons, their repeated refrains,
and the mixed-language Tamid passage were inspected visually.

Both editions pass deliberately broken controls for alignment, note duplication,
service boundaries, language direction, phrase-dot binding and stale contents.
Full suite: 3,262 tests and 4,812 subtests pass; 20 skipped, in 646.17 seconds.
Afterward, the standalone reference database was restored and all 194 files
passed validation and reverse comparison again. Recompilation with the corrected
eloah identities produces byte-identical TeX, so the naming change preserves the
verified expanded PDF layout.

Independent Hebrew proofreading and remaining English OCR adjudication are
pending. The 26 Tamid superscripts are unresolved printed note markers; their targets
are unknown and explanatory notes are not presumed to exist. Later services and release integration remain outside this checkpoint.

## Tzom Gedaliah checkpoint (2026-10-09)

The complete service covers n183/n184–n207/n208 (printed 91–103), including 38
source-ordered units, nine independent piyyutim and six scriptural prayer modules
per language. The projects contain 226 schema-valid files. Documentary page
streams, footnotes, source order, bilingual targets, all seven refrain choices per
language and the eight shared Horita stanza boundaries pass reverse verification.
Evidence hashes reject stale working readings; independent Hebrew review remains
pending. Separate initial captures, complete pre-OCR assembly, English OCR findings
and same-reader image adjudications are retained.

All URNs and transclusions resolve; the registry has no errors or warnings, with
four pre-existing alias-migration notes. The importer suite passes 60 tests and
12 subtests. Four expanded unequal petition lists preserve their compiled bilingual
pairings. The secondary Full Kaddish compiles with the Ten Days doubling, לעלא לעלא;
a synthetic ordinary-reading control fails. The service's unmarked holiday gate
and restoration of Kaddish setting scopes are checked.

Documentary: 158 pages and 19 TOC/bookmark destinations. All eight Gedaliah stanza
start differences measure 0pt; the first-day 13.55pt difference remains within
its existing 16pt bound. Seven distinctive English note fingerprints and the
unattached Hebrew marginal note occur once; Latin apparatus order is checked by
glyph coordinates. No Hebrew runs are left to right among 6,330; the reversal
control flags 5,758. Broken controls reject duplicated notes, missing marginal
commentary, shifted stanza starts, stale contents and stranded phrase dots. The
service transition, opening, pizmon and final note were inspected visually.

Visual inspection of the first expanded rendering found a retained secondary
“During the Ten Days of Repentance, add” rubric. An explicit empty Asher instruction
override suppresses that fulfilled rubric. Compiler PR #232 fixes the bypassed
instruction selection inside a resolved conditional; both regressions fail on
unfixed ordinary/external/inline compilation, and 74 focused tests with 22 subtests
pass afterward. The fix is applied to this branch. Actual compiled output retains
the Ten Days doubling and omits the rubric. Documentary TeX remains byte-identical;
the expanded TeX differs only by removal of that rubric macro.

Corrected expanded: 349 pages and 19 contents/bookmark destinations. All eight
Gedaliah stanza start differences measure 0pt. No Hebrew runs are left to right
among 14,777; the reversal control flags 13,487. The final Kaddish was inspected
visually: both לעילא words remain in one prose paragraph, the fulfilled rubric is
absent, and the Reader cue remains. All book controls pass, including reinserting
that unwanted rubric. The Hebrew marginal note appears once in both editions.

Final range audit: the English Gedaliah opening ends at Shomea tefillah's “for it
is great,” before the following reprinted Selah lanu. The abbreviated Hebrew
כי רבו citation is ambiguous. The documented editorial boundary removes the
extra earlier Selah lanu while preserving the printed citation. Initial and
assembled evidence remain immutable; the working hash and adjudication record
were updated. Both changed service files validate and reverse verification passes.
The PDF checker rejects the original rendering's duplicated opening. The 60
importer tests and 12 subtests pass after the correction.

Full suite: 3,341 tests and 5,031 subtests passed, with 20 skipped, in 737.98s.
The standalone reference database was restored, all URNs/transclusions resolve,
and the registry has no errors or warnings. All 226 project hashes match the
validated snapshot after the full suite. The range correction changes source
expansion data; the final rendering and its new boundary control are checked
separately below.

Final expanded after the opening correction: 349 pages, 19 TOC/bookmark entries,
and all eight Gedaliah stanza starts at 0pt difference. No reversed Hebrew runs
among 14,775; the reversed control flags 13,485. The opening contains Selah lanu
once, both injected duplication and fulfilled-rubric controls fail as intended,
and all book note, alignment, direction and boundary controls pass. All final
Gedaliah documentary streams match, evidence hashes are current, and URNs resolve.


## Third through fifth penitential days (2026-10-10)

Third day covers n233–n258, fourth n257–n282, and fifth n281–n308; the shared
boundary pages are split at the verified body headings. Each day was checked,
committed and pushed separately in code, sources and projects. The services add
111 bilingual units, 28 independent poem modules and 61 English apparatus notes.
All 308 project XML files validate and match the scan readings, including notes,
printed abbreviation branches, source order and expansion ranges. Both projects
resolve their URNs/transclusions. Registry: 3,664 records, no errors or warnings.
Immutable initial and pre-OCR readings, English OCR candidates and image
adjudications accompany each service; independent Hebrew proofreading is pending.

Per-day documentary/expanded PDFs: third 22/50 pages, fourth 21/49, fifth 22/51.
Their pizmon starts (six, eight, five respectively) align on identical baselines.
Prayer pairs, paired petition ranges, full-opening repeats, fulfilled-cue omission,
notes and scoped seasonal Half/Full Kaddishes pass, with deliberately broken
controls. Fifth day has 0/697 documentary and 0/1,936 expanded reversed Hebrew
runs; reversed controls flag 692 and 1,885. The initial fifth-day apparatus check
caught an authoring error: a single Hebrew letter caused its English footnote
to be marked as Hebrew. The mixed-language authoring helper and regression fixture
now wrap only the letter. The corrected note was inspected visually.

Cumulative documentary: 232 pages, 27 contents/bookmark destinations. All
whole-book controls pass, including the three new day scopes. Hebrew direction:
0/9,128 reversed runs; reversed control flags 8,213. The growing contents exposed
a checker error: an even page's title ordinal fell into the odd page's number
column. The checker now measures mirrored number columns, with an ordinal
fixture. Boundary checks retain verified notes from the preceding service below
the next body heading and exclude those notes from the following day; a synthetic
ownership fixture covers the exclusion. The relevant source anchors and the
second/third-day boundary were inspected in the PDF.

GitHub functional tests and code analysis pass at e9ab0df. Coverage gates remain
below their 85% targets: project 84.45%, patch 37.88%; the previous fourth-day
checkpoint also failed both coverage gates. PDF measurements run separately from
CI coverage and are retained in the untracked output directory. Skill frontmatter
and reference paths validate; both scan-specific subsections remain routed.


Final cumulative expanded: 536 pages and 27 contents/bookmark destinations.
All whole-book checks and broken controls pass. The third, fourth and fifth
pizmons have identical paired baselines throughout; the compiled services verify
4, 4 and 5 paired petition ranges respectively, plus both seasonal Kaddishes.
Hebrew direction: 0/22,491 reversed runs; the reversed control flags 20,322.
The fifth pizmon and final source-credit page were inspected visually.

Final local full suite: 3,391 tests and 5,060 subtests passed, with 21 skips,
in 619.78s. The standalone reference database is restored; all URNs/transclusions
resolve, and the registry retains zero errors and warnings. All 308 validated
project hashes remain unchanged after the suite. GitHub tests and code analysis
also pass at cf7549e; the companion projects PR passes validation.

Visual inspection found a separate generic bibliography issue: Birnbaum's long
Archive URL and eprint identifier overflow the source-credit page. Separate compiler PR [#236](https://github.com/opensiddur/opensiddur-ai/pull/236)
enables xurl's letter/digit breakpoints after biblatex, preserving
identifiers and hyperlink destinations. Its real rendering fixture fails without
the fix and passes with it. The cumulative PDFs above precede that separately
reviewed bibliography correction; their service text checks remain valid.

The separate bibliography PR passes 401 related exporter tests and 126 subtests.
Its real fixture reproduces an 85.18pt overflow without the fix and passes with
it, retaining the full identifier and hyperlink target.

The later coverage report at cf7549e remains below target: project 84.42%,
patch 37.82%. Functional tests and code analysis pass.

## Erev Yom Kippur, Archive n307–n320

The service begins under the large body heading on printed 153 and ends at the
Reader's Kaddish on printed 159, before the Second Fast body heading. Its 22
bilingual units add three independent incipit-named poems, seven shared Yertseh
stanza units and seven English notes. The fourth stanza crosses a page; full
printed refrain variants remain distinct. The closing repeat expands the whole
first stanza. The Ezekiel xxxvi.25 note below the Second Fast heading belongs to
Erev's preceding purification verse, not the following service.

The two opening citations conflict. Expanded output follows the complete Hebrew
Ashrei-through-Shomea range, excluding the Selah lanu reprint immediately after
it; this is an explicit editorial resolution. The unexplained raised English
mark remains unresolved. Three El melekh/Vayaavor pairs and one bounded petition
range expand in place. The final Full Kaddish uses the secondary-source default,
retaining the Reader role and seasonal settings. No Makhnise rahamim conclusion
is inserted. The index gates the entire service on 9 Tishrei.

Immutable first captures, complete pre-OCR snapshots and frozen comparison
inputs accompany the working readings. English Archive OCR was checked against
seven English pages; independent Hebrew proofreading remains pending. Enlarged
images settled the final Yertseh readings כְּהִתְוַעֲדוּ and וָאִכַּף. Earlier
unresolved findings remain recorded rather than silently normalized.

The standalone documentary and expanded PDFs have 13 and 22 pages respectively.
Both have two bookmarks, with the day above its pizmon. The cumulative editions
have 241 and 554 pages respectively, each with 29 contents/bookmark destinations.
All seven Erev stanza starts share identical Hebrew/English baselines. Rendering
checks cover seven notes occurring once, note direction, fulfilled instructions,
opening range, seasonal Kaddishes, closing prayers and the Second Fast boundary.
Deliberately broken controls must fail. The separate bibliography repair #236 is
merged upstream and included in these builds.

The first full-suite invocation could not write LuaLaTeX's default font cache;
PDF fixtures consequently failed before producing their output. Re-running with
`TEXMFVAR=/tmp/asher-tex-cache TEXMFCACHE=/tmp/asher-tex-cache` passed 3,397 tests
and 5,060 subtests, with 21 skips (563.18s). Both project reference checks pass;
the registry has 3,701 records, zero errors and zero warnings. Final source
verification validates all 316 files and all 22 new bilingual units.

Visual inspection then found the bare Hebrew-only pizmon heading stranded before
its first stanza. Separate compiler PR [#238](https://github.com/opensiddur/opensiddur-ai/pull/238)
routes a bare single primary title through the existing spanning-heading path.
Its 30-section rendering fixture fails against the original stylesheet and
passes after the repair. The separate branch's full suite passes 3,303 tests and
5,065 subtests, with 21 skips (649.87s). The repair is integrated here; all 83
Asher tests and 14 subtests pass after integration. The Asher PDF audit now also
rejects a missing or stranded pizmon heading, and rejects the original expanded
PDF that exposed this defect. Reference checks and PDF builds run serially after
the suites, restoring the standalone companion project database.


Final standalone PDFs retain 13 documentary and 22 expanded pages. Their seven
stanza-start deltas are all 0pt; the repaired heading and seven English notes
pass, as do all deliberately broken controls. Hebrew direction is 0/399
(documentary) and 0/787 (expanded); reversed controls flag 398 and 775 runs.
The repaired documentary pizmon page was inspected visually. The final cumulative
documentary has 241 pages and passes all whole-book checks and broken controls,
including the new heading check. Hebrew direction is 0/9,526, with 8,570 runs
flagged by the reversed control. Both final Hebrew corrections remain in all four
compiled views; all 316 project hashes remain unchanged after testing.


Final cumulative expanded: 554 pages, converged in three LaTeX passes, with 29
contents/bookmark destinations. All whole-book audits and broken controls pass;
all Erev stanza starts have 0pt paired deltas. Hebrew direction is 0/23,285,
with 21,034 runs flagged by the reversed control. The repaired expanded pizmon
page was inspected visually: the title stays with its complete opening stanza
and both English notes read correctly.

The pagination change exposed two PDF-audit extraction cases rather than text
loss: consecutive line/footnote markers (`5 509`) inside a prayer fingerprint,
and a line number following punctuation (`fathers, 35 may`). The fifth-day and
Erev checks now remove these rendering markers before counting their unchanged
prayer fingerprints. Three synthetic full-check fixtures cover consecutive
markers, punctuation-adjacent markers and a genuinely missing prayer; both
positive cases fail against the earlier checker, and the missing prayer remains
rejected. The original fifth-day target of eleven heritage endings is retained.


The final main/master refresh merged opensiddur-ai #237 (calendar corrections)
and opensiddur-projects #74 (Birnbaum Minhah fast-day conditions). The post-merge
full suite passed 3,430 tests and 5,128 subtests, with 21 skips (649.01s); the three
numeric-marker fixtures also pass against the final checker. Both project URN
checks and the 3,701-record registry pass, with zero errors and warnings. All 316
XML files and their source readings verify again. All four complete compiled XML
views are identical under canonical XML comparison before and after the merges,
so the verified PDFs remain current. The two final Hebrew corrections and all
316 project hashes remain intact. Independent Hebrew proofreading remains pending.


## Monday fast, Archive n319–n336

The large body headings delimit the first Monday of the Monday–Thursday–Monday
fast series. English “Second Fast” translates the Hebrew weekday לשני; it is
not a second penitential day. Its closing Ezekiel note remains with Monday even
though it is below Thursday's heading. The unsupplied weekday Amidah, usual
service, Torah and haftarah instructions remain in both views. No Full Kaddish
is inserted into this interrupted weekday-service sequence. Inspection of the
final leaves confirms the claimed Torah/haftarah appendix is absent from this
scan; Hebrew page fields are blank. This remains an unresolved printed claim.

Malakhei rahamim has eight shared stanza units, six short cues per language,
and a Hebrew-only final full refrain and opening-repeat cue. Expanded English
does not acquire that unprinted repeat. Three El melekh/Vayaavor pairs expand,
along with independently bounded Hebrew/English petition lists. The initial
Vayaavor is reprinted across two leaves. Immutable initial and complete pre-OCR
snapshots, frozen English OCR inputs, hashes and image adjudications accompany
all 26 readings. Independent Hebrew proof remains pending.

Standalone PDFs contain 16 documentary and 18 expanded pages. All eight stanza
starts align exactly; both outputs pass apparatus direction, 15-note occurrence,
prayer/refrain boundary and performance-instruction checks. Missing text, missing
or duplicated notes, and shifted-stanza controls are rejected. Hebrew direction:
0/465 documentary and 0/581 expanded; reversal controls flag 460 and 573 runs.
Both pizmon pages were inspected visually. All 324 XML files validate and reverse
match their source readings; both projects resolve URNs/transclusions. Registry:
3,742 records, zero errors and warnings.

The full suite passes 3,433 tests and 5,128 subtests, with 21 skips (614.62s).
After the numeric-marker security correction, all 89 Asher tests and 14 subtests
pass. A subprocess fixture reproduces catastrophic backtracking on the former
nested marker regex and passes with the shared single-repeat pattern. This
addresses the two CodeQL alerts in the Asher PDF audit helpers. Compiled occasion
checks additionally exposed missing title-page gates; the authoring code now
wraps each title leaf in the native paratext condition, keeping its page break
outside. Ordinary output retains the two title pages.

The cumulative documentary PDF has 254 pages and 31 contents/bookmark
destinations, converged after three LaTeX passes. All book checks and broken
controls pass. Hebrew direction is 0/9,990 reversed runs; the reversal control
flags 8,974. The second contents page and Monday pizmon page were inspected
visually; the day heading remains above its subordinate pizmon bookmark.
All three workstream branches were refreshed against upstream main/master,
with no additional changes to merge.

The final occasion checks compile Monday included, excluded, and on the wrong
weekday; all three pass. Declaring paratext/title-page false removes both source
title pages. The ordinary documentary TeX is byte-identical after introducing
these gates, so its verified cumulative PDF remains current. All 324 project
hashes are unchanged; schema/source/reference verification and the 89 Asher tests
pass again after the final gate edits. The cumulative expanded rebuild was
interrupted during its third pass; its damaged auxiliary files were retained
for diagnosis and are being regenerated. The independently verified 18-page
expanded Monday PDF is the expanded rendering evidence for this checkpoint;
no successful cumulative expanded check is claimed for the interrupted build.


## Thursday fast, Archive n335–n342

The Thursday/Fifth Fast begins beneath Monday's closing passage and ends before
the last Monday's body heading. Three independent poems include the fast-day
recension of Israel nosha, with six shared stanza units. Five choices per
language expand four short refrain cues and the final opening repeat. Printed
full refrains remain ordinary text. Source instructions resolve to three
El melekh/Vayaavor pairs and the Monday closing passages; weekday Amidah and
usual-service performance instructions remain. No Full Kaddish is inserted.

All 332 XML files validate, reverse-match the readings, and resolve their URNs
and transclusions. The registry contains 3,772 records with no errors or warnings.
All 90 Asher tests and 14 subtests pass. Actual compilation includes Thursday
when selected on weekday 5, excludes it when unselected or on weekday 2, and
honors the title-page paratext gates. The most recent full-suite run remains
the Monday checkpoint's 3,433 passing tests.

Standalone documentary and expanded PDFs contain 8 and 17 pages. All six stanza
start deltas are zero. The two Thursday notes occur once each; expanded output
also retains fourteen notes from the transcluded conclusion. Apparatus direction,
prayer boundaries, refrain counts, retained performance instructions, and
missing-note and shifted-stanza controls pass. Hebrew direction reports 0/158
and 0/521 reversed runs; reversal controls flag 157 and 516. Documentary and
expanded pizmon pages were inspected visually. Day bookmarks are above their
subordinate pizmon bookmarks in both outputs. These standalone PDFs provide the
rendering evidence for this checkpoint; cumulative expanded rendering remains
underway using the fixed Monday input.


## Final Monday fast, Archive n343–n350

The final Monday ends above the Tenth of Tevet body heading. Its three reusable
poems retain incipit identities, with Ezkerah's fast-day recension under the
existing poem identity. Ezkerah contains one prose Thirteen Attributes unit and
four verse units; its one concluding cue per language expands the complete
opening. The Hebrew verse crosses printed173/174 within one line. A Hebrew-only
petition-repeat instruction has an empty paired English expansion boundary,
rather than acquiring an invented English repeat. Opening and conclusion use
Monday ranges, keeping unsupplied performance instructions and omitting Full
Kaddish. One English note is printed here; the expanded conclusion inherits
fourteen more. All fourteen units retain immutable first captures, assembled
pre-OCR snapshots, frozen English comparison inputs and image adjudications.

All 340 XML documents validate and reverse-match their readings; both projects
resolve URNs/transclusions. The registry has 3,799 records, no errors or warnings.
All 92 Asher tests and fourteen subtests pass, including regressions for the
asymmetric repeat boundary and prose attribute unit. Actual occasion compilation
includes the selected service on Monday and excludes it when unselected or on
Thursday; paratext/title-page false is honored.

Standalone documentary/expanded PDFs have 8/17 pages. All five paired-unit start
deltas are zero; footnote occurrences, apparatus direction, prayer bounds,
opening-repeat counts and deliberately missing-note/shifted-stanza controls
pass. Contents destinations, day-over-pizmon hierarchy and attached phrase dots
pass. Hebrew direction: 0/187 and 0/554 reversed runs; reversal controls flag
185 and 548. Both revised pizmon pages were inspected visually. Independent
Hebrew proofreading remains pending, especially pointing and rare vocabulary.

The recovered cumulative expanded Monday PDF has 569 pages and 31 contents/
bookmark destinations. The fixed input converged on the third recovery pass;
all book checks and broken controls pass. Hebrew direction reports 0/23,871
reversed runs; the reversal control flags 21,547. Its second contents page was
inspected visually. This resolves the interrupted Monday rebuild recorded above;
it does not claim cumulative coverage of Thursday or the final Monday.


## Tenth of Tevet, Archive n349–n358

Complete through printed178 upper, above Esther's heading. Avotai has fourteen
paired stanza units, thirteen Hebrew choices and twelve English choices, each
expanding the complete opening. Its internal page breaks retain one joined
English word, to-/wards. Three reusable poems and fifteen units retain immutable
captures, assembled pre-OCR snapshots, English comparisons and image corrections.
Ten English notes retain their anchors; expanded English has twenty-four notes
including the transcluded Monday conclusion. No Full Kaddish is inserted.

All twelve changed/new XML files validate; source reverse checks and evidence
hashes pass. Both project URN checks and the registry check pass. The complete
project scope is 348 XML documents. All 94 Asher tests and fourteen subtests pass,
including word-join and native holiday regressions. Actual compilation includes
Tevet for asara-btevet=1 and excludes it for 0, honoring title-page gates.

Standalone documentary/expanded PDFs have 11/21 pages, converged in three passes.
All fourteen stanza start deltas are zero. Note counts, apparatus direction,
refrain and prayer ranges, word joining, performance instructions, contents and
bookmark hierarchy pass. Missing-note and shifted-stanza controls are rejected.
Hebrew direction: 0/288 and 0/751; reversal controls flag 288 and 745. Documentary
and expanded pizmon pages were inspected visually. Independent Hebrew proof
remains pending, especially rare vocabulary and pointing.


## Fast of Esther, Archive n357–n368

Eight Bematei stanza units align across different Hebrew/English page crossings.
Seven Hebrew refrain choices expand; English has none despite its repeat rubric.
The authoring code now omits empty-language facsimile fragments; a regression
rejects backward English page jumps. Reverse verification additionally checks
actual pizmon page order. Two prayer pairs and Monday opening/conclusion ranges
expand; no pair follows the final pizmon and no Full Kaddish is added. All nineteen
English notes retain their source anchors, including two mixed-language notes.

The twelve changed/new XML files validate; all later-service source/evidence
checks, both project URN checks and registry check pass. Registry:3,867 records,
zero errors/warnings. All 95 Asher tests and fourteen subtests pass. Actual
compilation includes taanit-esther=1 and excludes 0, with title-page gates honored.
The latest full suite remains the Monday checkpoint run; coverage targets are
still unmet, while final Monday GitHub tests, CodeQL and projects validation pass.

Documentary/expanded PDFs have 12/20 pages, converged in three passes. All eight
stanza start deltas are zero. Nineteen/thirty-three note occurrences, apparatus
direction, refrain counts, prayer boundaries, retained performance rubrics,
contents/bookmark hierarchy and phrase dots pass; missing-note and shifted-stanza
controls are rejected. Hebrew direction:0/239 and0/600; reversal controls flag239
and593. Documentary and expanded pizmon pages were inspected visually. Independent
Hebrew proof remains pending, especially pointing and rare vocabulary.


## Seventeenth of Tammuz, Archive n367–n376

Four Sheeh stanza units align. One Hebrew full-opening choice and one English
short refrain choice preserve different repetition scopes and full-refrain variants.
Thirteen actual notes plus three unresolved printed markers are distinguished;
source184's apparent interchanged note numbers are preserved by their printed
associations. The source README and adjudication disclose removed provisional
apparatus guesses and incidental introductory English OCR exposure.

Documentary/expanded PDFs have10/19 pages, converged in three passes. Four stanza
deltas are zero;13/27 note occurrences, apparatus direction, prayer/refrain bounds,
retained instructions, contents/bookmark hierarchy and phrase dots pass. Missing-note
and shifted-stanza controls fail as intended. Hebrew direction:0/244 and0/613;
reversal controls flag242 and605. Verse pages inspected visually. The string
“Say unto Zion, arise” is printed prayer text, not a fulfilled inclusion rubric.
Independent Hebrew proof remains pending.

All364 XML files validate; full source/evidence reverse checks and both project
URN checks pass. Registry:3,893 records,zero errors/warnings. All97 Asher tests and
fourteen subtests pass. Native tzom-tammuz=1/0 compilation includes/excludes the
service correctly and respects title-page=false. The latest full-suite run remains
the Monday checkpoint. Tevet/Esther CI is checked separately; coverage target
failures remain disclosed.

## Yom Kippur Katan checkpoint

Sixty-one bilingual source units cover printed 188–203 upper. Documentary and
expanded PDFs contain 26/36 pages. All 21 paired stanza starts align with zero
baseline delta. Nine source notes occur exactly once; mixed-language direction,
fulfilled-cue removal, independent refrain positions, performance instructions,
interleaved Samar petitions, supplied Kaddishes, TOC/hierarchy and phrase dots pass.
Missing-note and shifted-stanza controls fail as intended. Hebrew direction checks
find 0/783 and 0/1213 reversed runs; reversed controls flag 777/1201. Explicit occasion
inclusion/exclusion and title-page suppression pass. All 102 Asher unit tests pass.
The prior full-suite and cumulative-PDF counts above are historical; a final book
run follows the remaining circumcision section. No independent Hebrew proof is claimed.

## Final circumcision checkpoint

Three source units cover printed 203 lower–204, the end of the book. Five paired
stanza starts align with zero baseline delta in both four-page PDFs. Alternating
Hebrew cue expansions, absent English cues, retained performance instructions,
removed fulfilled rubric, final boundary and unresolved superscript marker pass.
The marker uses explicit superscript markup to survive text normalization. Broken
marker-deletion and shifted-stanza controls are rejected. Final-section bookmark,
TOC, phrase dots, explicit occasion inclusion/exclusion and title-page suppression
pass. Hebrew direction checks found 0/31 documentary and 0/28 expanded reversed
runs; reversed controls flag 28 in each. The unplaced s408 Hebrew fragment remains
in reading evidence pending identification, outside the poem body.

All 106 Asher unit tests pass, including final service-order and PDF body-word
regressions. The full local suite passes: 3,449 tests, 21 skipped, in 657.59
seconds, using the writable TeX cache above. This includes Birnbaum regressions
and PDF geometry tests. Subsequent changes concern verification and standalone
entrypoint metadata; the focused suite was rerun after those changes.

## Complete-book verification

The final documentary and expanded PDFs contain 311 and 680 pages respectively,
with 44 bookmarks each. Both converged in three rendering passes. The contents,
monthly verse pages and final expanded service were inspected visually. Hebrew
direction checks report 0/11,909 and 0/28,182 reversed runs; deliberately reversed
controls flag 10,590 and 25,110.

A fresh registry/project reference check and source verification pass: 4,008
registry records with zero errors/warnings, all 398 schema-valid XML documents,
documentary readings, source-page order and expansion targets/forms. The service
iteration order places circumcision after the monthly service, matching the book.

PDF verification assigns Thursday’s final note to its source anchor even when
typesetting places it below the following heading. Both whole-book checks pass with broken controls enabled: contents,
bookmark hierarchy, stanza alignment, apparatus occurrences/direction, fulfilled
cues, prayer/refrain ranges, phrase dots and final boundaries. One documentary
first-day stanza starts 13.55 points apart, within the 16-point bound; all other
measured pizmon starts align exactly. Body matching filters small
apparatus/line counters and removes numeric headers before joining words split
across pages. Synthetic regression coverage preserves the distinction between
body text and apparatus.

Independent Hebrew proofreading remains pending. The final English superscript
remains unresolved and explicitly recorded in source evidence. The previously
unplaced s408 words are restored in the correction checkpoint below.
These PDFs are inspection artifacts, outside automatic publication/release builds.


## Circumcision verse correction

User review identified the omitted s408 words as the beginning of stanza four,
after the והשב abbreviation. Image proofreading restores
מִפִּי אוֹהֲבֶיךָ עֵד בֵּינְךָ וּבֵין יְדִידֶיךָ across s408→s410 in one verse.
The former דם at the start of s410 was not printed and is removed. Working
readings, hashes, adjudication and the scan subsection are corrected; immutable
initial/pre-OCR captures retain their original errors. English remains as printed.

Corrected section PDFs each contain four pages, converged in two passes. All five
stanza baselines align exactly. Text presence, two refrain expansions, English
marker, performance rubrics and final boundaries pass; deleted-restored-verse,
deleted-marker and shifted-stanza controls are rejected. Hebrew direction is
0/32 documentary and 0/29 expanded; reversal controls flag 29 in each. The
expanded body was inspected visually. All 106 focused tests pass. Earlier
whole-book PDF results above refer to the pre-correction snapshot; those
aggregate artifacts have not been rerendered for this small text correction.


## Transcription proofreading batch 001

Fresh image-only captures for Hebrew title s2/n1 and opening s6/n5, s8/n7
(printed3) were frozen before comparison with working readings/XML. Crops
adjudicate six corrections: וואללענטין, אֱלוֹהַי, נִפְלְאֹתֶיךָ, word spaces
in יְדַבֶּר פִּי and זְכֹר רַחֲמֶיךָ, and maqqef in דִּי־בְרָא. Two
differences were rejected as blind-reading/wrapping errors; a possible title
ink mark remains undecided. Full provenance and frozen/pre/post hashes are in
`proofreading/image-pass-01` in the sources repository. This is a same-model
second image pass; independent-person proofreading remains pending.

Seven changed XML files validate; all six opening page/language streams and
both title-page comparisons pass. The separate title/opening inspection PDF
has10 pages and converged in three passes. Four measured anchor deltas are zero.
Hebrew direction:0/86; reversal control flags85. Reversed citation, shifted
English, stranded punctuation, substituted colon and deleted-corrected-line
controls are rejected. The opening body was inspected visually. The generic
full-day footnote control cannot run on this excerpt without apparatus; this
limited scope is recorded explicitly. Full-book PDFs remain earlier snapshots.

The coverage ledger records s10/n9 as the next Hebrew page; facing English
pages, contents and later Hebrew pages are outside this proofreading batch.


## Transcription proofreading batch 002

Frozen fresh image readings cover Hebrew s10/n9 and s12/n11, printed 4/5,
including the mixed-language footnote. Eight scan-adjudicated corrections remove
the extra vav in ומה־נאמר, remove dagesh from the second כל, restore defective
חצרתיו and ידעי, restore bet dagesh in הנה ברכו, remove an invented phrase dot
after קדש, restore מלפניו, and add the printed phrase dot before ישמיע.
A maqqef added by the blind reading in בבית יי was rejected against the image.
Frozen captures, image hashes, pre-correction comparison and adjudication are
in sources/asher_selichot/proofreading/image-pass-02. Initial scan-first fragment
captures remain unchanged; the canonical continuation reading and XML are corrected.
This is a same-model second pass, not independent-person proofreading. Next: s14/n13.

Both changed Hebrew XML modules validate. All 96 bilingual continuation units,
six opening streams and title comparisons pass. All 106 focused Asher tests pass.
The separate inspection PDF through printed5 has 12 pages, converged in three
passes, and was compiled with its own reference database. Four opening anchor
deltas are zero. Hebrew direction: 0/199; reversal control flags 197. Five Latin
apparatus runs read left to right. Both footnotes and corrected consonantal
forms appear once. Nine broken controls are rejected: reversed citation/note,
shifted English, wrong service boundary, stranded stop, colon substitution,
deleted corrected line, deleted note and duplicate note. Page 11's body and
apparatus were inspected visually. Facing English has not been independently
proofread; whole-book PDFs remain earlier snapshots.

## CI coverage diagnosis at code 61ea0af

Tests and CodeQL pass; projects 037dca5 validation passes. Codecov reports
37.42% patch coverage and 83.03% project coverage against 85% for both gates
(codecov.yml). Overall coverage falls from 93.70% on base 56c1151.
The patch contains 2,822 uncovered changed lines. The largest gaps include
check_book_pdf.py (21.10%, 299 missing) and verify.py (8.66%, 295 missing);
check_erev_yom_kippur_pdf.py and check_penitential_fourth_pdf.py have 0% coverage.
CI's tests.yml instruments only unittest discovery. Separately run local
source-verification and PDF-check commands do not contribute to its coverage.xml.
Meaningful automated tests or coverage-instrumented CI checks are needed for
these paths; passing local checks alone cannot satisfy the coverage gates.
Thresholds and exclusions have not been changed.

Report: https://app.codecov.io/gh/opensiddur/opensiddur-ai/pull/215


## Generic scan code and coverage boundary

Reusable XML authoring, metadata derivation and PDF measurement now live under
importer/scan with caller-supplied edition conventions. Asher assembly recipes,
identity tables, fixed download selection and disposable fixed-text inspection
commands remain compatible wrappers/recipes. Explicit Codecov ignore entries
match local coverage omissions; compiler/exporter and shared scan logic remain
measured. Both coverage targets remain 85%. The classification and extension
rules are documented in opensiddur/importer/scan/README.md.

Forty-two new synthetic unittest cases exercise reusable behavior, including
cache isolation and failure cleanup, unknown/duplicate labels, reciprocal
pairings, mixed languages, verse/refrain structure, validation before writes,
source-ordered reverse comparisons, stale adjudications, PDF geometry, bookmark
ancestry, contents destinations and deliberately reversed glyphs. They do not
assert edition words or inventories. The focused shared scan run has 48 tests;
all 106 existing Asher tests pass.

Merged main604344b and rebuilt RelaxNG/Schematron. Full merged-state coverage run:
3,507 tests run in 736 seconds, 12 skipped, no failures. Local overall statement
coverage is 94.43% (18,838/19,950); shared scan coverage is 99.85% (685/686).
Local changed-statement estimate against main604344b is 99.86% (720/721);
Codecov's remote calculation may differ. No thresholds were lowered.

All 398 generated XML files are byte-identical before/after the refactor.
All 398 companion-worktree XML files validate against the rebuilt schema;
documentary, title/opening/continuation, expansion and later-service verification
passes through the final service. The cached 12-page batch002 PDF passes the
refactored checks: four zero alignment offsets, Hebrew direction 0/199 and the
reversed control flags 197/199. Direction/alignment/boundary/verse-stop broken
controls are rejected. No new full-book render or proofreading is claimed.

Logs and local coverage reports are untracked under
output/asher_selichot/coverage-refactor/.


## Transcription proofreading batch 003; Asher PR consolidation

GitHub currently has only Asher code215, source49 and projects69 open; no
secondary draft PR targeting these branches exists to merge or close. Recent
compiler PR240 is already merged into main. Main74981d8 is merged into the
Asher code branch; the inline-choice conflict retains both abbreviation
selection and main's guarded qere/alternate-reading selection. All303 focused
compiler/inline/range/reference tests pass, including abbreviation and new
compiler-core regressions. Source/project main branches were already included.
Further proofreading checkpoints stay on the three existing Asher PRs.

The frozen image-only reading of s14/n13, Hebrew printed6, identifies two
scan-confirmed corrections: defective יֹשֵׁב הַכְּרוּבִים and plene בִּזְמִירוֹת.
Native crops confirm both and resolve the blind capture's מושל/ויבשת questions
without further changes. Frozen reading, image/source hashes, comparison and
adjudication are in sources/asher_selichot/proofreading/image-pass-03.
The working continuation reading and one Hebrew XML module are corrected;
initial scan-first captures remain unchanged. Same-model second pass,
not independent-person review. Next Hebrew page:s16/n15.

The changed module validates; all96 continuation units, six opening streams
and both titles match documentary evidence. All106 focused Asher tests pass.
The separate13-page excerpt PDF converges in three passes using an isolated
reference database. Four anchor offsets are zero; Hebrew direction0/252,
reversed control250/252. Both corrected consonantal forms occur once; six
existing direction/alignment/boundary/punctuation controls are rejected.
Page11 body was inspected visually. The existing mixed-language footnote
shares an English continuation line with the Hebrew paragraph; paragraph
separation remains to review despite passing glyph-direction controls.
Facing English is not independently proofread; whole-book PDFs remain older.

Remote CI for previous code9887154 passed tests, CodeQL and both Codecov gates:
99.86% patch and93.93% project. One defensive compare.py line is uncovered;
both targets remain85%. New checkpoint CI will run after push.


## Transcription proofreading batch004

Hebrew s16/n15 through s24/n23 (printed7–11) received a fresh frozen image
reading followed by comparison and native-crop adjudication. The source evidence
records96 accepted comparison hunks, including plural petitions in Adonai boqer,
misread words in Eikh niftah and Ein mi yiqra, and El Melekh/Vayaavor pointing
and punctuation. Blind mistakes are retained and explicitly rejected; final
פקדת retains its printed tav. Fine pointing uncertainties remain recorded.
The printed stops change mercy_invocation to15 lines and el_erekh_apayim to16.

All398 XML files passed schema validation. After correcting the stale verse
counts, all96 continuation units, six opening streams and title comparisons
pass. All106 existing Asher tests pass. The19-page bilingual inspection PDF
converged in three LuaLaTeX passes, using an isolated reference database.
Hebrew direction:0/508; reversing runs flags499/508. The17-page opening
prefix has four zero alignment deltas and rejects six broken controls.
The whole excerpt intentionally exceeds the opening-only checker boundary.
Rendered pages15,17,18 were inspected. Full-book PDFs are earlier snapshots;
facing English and independent-person Hebrew review remain pending. The
previously recorded mixed-language note paragraph separation remains pending.


## Proofreading checkpoint 005

Hebrew printed 12–15 (s26/n25–s32/n31) adjudicated from fresh image captures;
71 source edits update four XML modules. This remains a same-model second pass,
with independent-person review pending. Four changed files validate; six opening
streams, title metadata and 96 continuation units match the readings.

The isolated 24-page documentary inspection PDF passes eight poem alignment
checks (maximum 13.55pt), single footnote occurrence, abbreviation and prayer
boundaries, and broken controls. Opening-prefix checks pass on 17 pages with
four zero-delta anchors and six broken controls rejected. Hebrew direction:
0/698 reversed; reversed control flags 683/698. Rendered pages 20,22,24 inspected.
This excerpt is not a whole-book rebuild; facing English and unresolved fine
pointing still need independent review. The previously recorded mixed-note
paragraph-separation issue remains open. Evidence: source proofreading/image-pass-05.


## Proofreading checkpoint 006

Hebrew printed16–19 (s34/n33–s40/n39) adjudicated from frozen image captures.
Thirty-four replacement rules update eight modules, including קבץ נדחנו, תביאנו,
printed punctuation and the restored verse boundary after לזרים. Eight changed
XML modules validate; six opening streams/titles and96 continuation units match.

Merged current main as7ef5d93. The full post-merge suite runs3557 tests with12
skips and no failures. The corrected isolated documentary excerpt compiles with
that merged compiler and renders29 pages. Eight poem anchors align within13.55pt;
its footnote occurs once and three broken controls are rejected. Opening checks
on17 prefix pages give four zero-delta anchors and reject six controls. Hebrew
direction0/946; reversed control929/946. Pages25,27,28 inspected visually.

This selected-module excerpt omits some service-order repetition rubrics and is
not a whole-book rebuild. Independent-person review, facing English proofreading,
fine-mark uncertainties and the prior mixed-note paragraph issue remain open.
Evidence: source proofreading/image-pass-06.


## Proofreading checkpoint 007

The Hebrew second image pass reaches the first-day closing rubric on s52/n51,
printed25 upper. Forty-six replacement rules correct nine modules across
printed20–25, including Anenu phrase stops, Mi Sheanah pointing and Aramaic
wording. Maran captive has three verse units, following the restored printed
sof pasuq. Frozen captures, rejected readings and uncertain fine marks remain
in source proofreading/image-pass-07; this is not independent-person review.

All398 XML files validate. Seven core documentary streams, six opening streams
and title metadata,96 first-day continuation units and all later-service source
and expansion checks pass. No executable code changed; the last full code suite
passed3557 tests with12 skips after the main merge.

Actual first-day assemblies render37 documentary and42 expanded pages under
output/asher_selichot/proofreading/batch-007. Both have six zero-delta prayer
anchors and correct20-line/20-refrain Mi Sheanah, notes and service boundaries.
Eight poem anchors are within13.55pt documentary and exactly aligned expanded.
Nine documentary/thirteen expanded first-day broken controls and three poem
controls per view are rejected. Direction:0/1283 documentary and0/1509 expanded;
reversed controls flag1253/1283 and1471/1509. Expanded checks confirm supplied
prayers, omitted fulfilled instructions, and one Full Kaddish in first-day context.
Documentary pages31,33,35 and expanded40–42 inspected visually.

Independent-person Hebrew review, facing English proofreading, uncertain fine
marks and the previously recorded mixed-note paragraph issue remain pending.
Whole-book PDFs remain earlier snapshots. Second-day image captures are underway.


## Proofreading checkpoint 008

The Hebrew second image pass reaches the second-day closing rubric on s60/n59,
printed29 upper. Seventy-five replacement rules correct four modules across
printed25–29. Frozen captures and native-crop adjudication preserve rejected
blind readings and uncertain fine marks in source proofreading/image-pass-08.
Four changed XML files validate and second-day source/expansion checks pass.
Only two declarative PDF anchor strings change in code; the last full suite
passed3557 tests with12 skips. All398 XML files passed at checkpoint007.

Actual first-and-second-day assemblies render43 documentary and70 expanded pages
under output/asher_selichot/proofreading/batch-008. Contents, day bookmarks above
pizmons, notes, service boundaries and deliberately broken controls pass. Six
second-day stanza anchors align exactly in both views. First-day prayer anchors
also align exactly; first-day poem maximum is13.55pt documentary and0pt expanded.
Direction:0/1466 documentary and0/2739 expanded; reversed controls flag1431/1466
and2663/2739. Documentary pages37,39,41,42 and expanded53,54,68 inspected visually.

Independent-person Hebrew and facing-English proofreading, uncertain fine marks,
and the recorded mixed-note paragraph issue remain pending. Whole-book PDFs are
older snapshots. Third-day image captures are underway, preserving the verified
swap of printed31/32 in Archive scan order.


## Proofreading checkpoint 009

The Hebrew second image pass reaches the third-day closing rubric on s68/n67,
printed 33 upper. Eighty-eight replacement rules correct four modules across
printed 29–33. Read in verified printed order: s60,s62,s66,s64,s68; preserve the
Archive's swapped openings in facsimile identities. Frozen captures, comparison,
rejected blind readings and native-crop adjudication are in image-pass-09.
Four changed XML files validate and third-day source/expansion checks pass.
No executable code changes. Last full suite: 3557 tests, 12 skips, no failures;
all 398 XML files passed at checkpoint 007.

Actual assemblies through day three render 49 documentary and 100 expanded pages
under output/asher_selichot/proofreading/batch-009. Contents, day bookmarks above
pizmons, notes, expansions, service boundaries and deliberately broken controls
pass. Six third-day stanza anchors align exactly in both views. All other checked
anchors align exactly except the documentary first-pizmon maximum of 13.55pt.
Direction: 0/1717 documentary and 0/4030 expanded; reversed controls flag 1676/1717
and 3915/4030. Documentary 45,47,48 and expanded 82,83,84,86,98 inspected visually.

Independent-person Hebrew and facing-English proofreading, uncertain fine marks,
and the recorded mixed-note paragraph issue remain pending. Whole-book PDFs are
older snapshots. Fourth-day image captures and comparison are complete;
adjudication is underway and is not included in this checkpoint.


## Proofreading checkpoint 010

The Hebrew second image pass reaches the fourth-day closing rubric on s76/n75,
printed 37 upper. Ninety-two replacement rules correct four modules across
printed 33–37. Restore the omitted final-stanza phrase and remove its duplicated מלכי;
retain the small unpointed refrain cues. Frozen captures, comparison,
rejected blind readings and native-crop adjudication are in image-pass-10.
Four changed XML files validate and fourth-day source/expansion checks pass.
No executable code changes. Last full suite: 3557 tests, 12 skips, no failures;
all 398 XML files passed at checkpoint 007.

Actual assemblies through day four render 56 documentary and 130 expanded pages
under output/asher_selichot/proofreading/batch-010. Contents, day bookmarks above
pizmons, notes, expansions, service boundaries and deliberately broken controls
pass. Five fourth-day stanza anchors align exactly in both views. All other checked
anchors align exactly except the documentary first-pizmon maximum of 13.55pt.
Direction: 0/1964 documentary and 0/5321 expanded; reversed controls flag 1912/1964
and 5158/5321. Documentary 52,54,55 and expanded 112,113,128 inspected visually.

Independent-person Hebrew and facing-English proofreading, uncertain fine marks,
and the recorded mixed-note paragraph issue remain pending. Whole-book PDFs are
older snapshots. Fifth-day corrections and source checks are complete; PDF verification is pending.


## Proofreading checkpoint 011

The committed Hebrew proofreading checkpoint reaches the fifth-day closing rubric, printed page 41 upper (s84/n83), including title and opening pages. Frozen captures, comparison records, crop adjudication and hashes are under `sources/asher_selichot/proofreading/`. Latest batch: 82 replacement rules across four modules on printed 37–41. Restored omitted stanza openings and corrected the printed לישועתנו refrain. This is a same-model second image pass with prior exposure, not independent-person proofreading. Facing English review remains pending.

Four changed XML files validate and fifth-day source/expansion checks pass.
- Documentary: 63 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 2216 Hebrew runs are set left to right; control: 2158 of 2216 flagged when every run is reversed. Visual pages: 59,61,62.
- Expanded: 158 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 6579 Hebrew runs are set left to right; control: 6368 of 6579 flagged when every run is reversed. Visual pages: 138,139,141,142,143,144,156,157.

Artifacts: `output/asher_selichot/proofreading/batch-011/`. Last full post-merge suite: 3557 tests, 12 skips, no failures. No executable code changes. Independent-person Hebrew, facing English and uncertain marks remain pending. Previously recorded mixed-note paragraph issue remains. Next service: sixth day.


## Proofreading checkpoint 012

The committed Hebrew proofreading checkpoint reaches the sixth-day closing rubric, printed page 45 upper (s92/n91), including title and opening pages. Frozen captures, comparison records, crop adjudication and hashes are under `sources/asher_selichot/proofreading/`. Latest batch: 95 replacement rules across four modules on printed 41–45. Corrected poem readings and removed the unsupported Hebrew cue after חסין while preserving its printed English counterpart. This is a same-model second image pass with prior exposure, not independent-person proofreading. Facing English review remains pending.

Four changed XML files validate and sixth-day source/expansion checks pass.
- Documentary: 69 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 2464 Hebrew runs are set left to right; control: 2397 of 2464 flagged when every run is reversed. Visual pages: 66,68,69.
- Expanded: 188 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 7872 Hebrew runs are set left to right; control: 7592 of 7872 flagged when every run is reversed. Visual pages: 166,167,168,171,172,173,186,187,188.

Artifacts: `output/asher_selichot/proofreading/batch-012/`. Last full post-merge suite: 3557 tests, 12 skips, no failures. No executable code changes. Independent-person Hebrew, facing English and uncertain marks remain pending. Previously recorded mixed-note paragraph issue remains. Next service: seventh day.


## Proofreading checkpoint 013

The committed Hebrew proofreading checkpoint reaches the seventh-day closing rubric, printed page 49 upper (s100/n99), including title and opening pages. Frozen captures, comparison records, crop adjudication and hashes are under `sources/asher_selichot/proofreading/`. Latest batch: 114 replacement rules across four modules on printed 45–49. Corrected poem and pizmon readings; preserved unpointed invocations and the service boundary. This is a same-model second image pass with prior exposure, not independent-person proofreading. Facing English review remains pending.

Four changed XML files validate and seventh-day source/expansion checks pass.
- Documentary: 77 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 2736 Hebrew runs are set left to right; control: 2625 of 2736 flagged when every run is reversed. Visual pages: 71,72,73,74,75,76.
- Expanded: 218 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 9186 Hebrew runs are set left to right; control: 8571 of 9186 flagged when every run is reversed. Visual pages: 193,194,195,196,197,198,199,200,201,202,215,216,217.

Artifacts: `output/asher_selichot/proofreading/batch-013/`. Last full post-merge suite: 3557 tests, 12 skips, no failures. No executable code changes. Independent-person Hebrew, facing English and uncertain marks remain pending. Previously recorded mixed-note paragraph issue remains. Next service: Erev Rosh Hashanah.


## Proofreading checkpoint 014

The committed Hebrew proofreading checkpoint reaches the Erev Rosh Hashanah closing rubric, printed 91 upper (s184/n183 upper). Batch 014 covers 43 Hebrew pages from s100/n99 lower: 393 replacement rules across 22 XML modules, one additional native correction, and a boundary repair moving דנפישין to the next source page without duplicating it. Frozen readings, comparison records, adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-14/. This is a same-model second image pass with prior exposure; later pages are primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.

22 modules validate; 113 source-ordered units, documentary branches, notes and bilingual expansion targets checked. The PDF anchor now follows the corrected אדון כתקח opening rather than the obsolete אדון במועד reading.
- Documentary: Erev PDF: service boundaries, closing cue, retained Ark instructions and apparatus checked; start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
140 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [13.55, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 5658 Hebrew runs are set left to right; control: 5280 of 5658 flagged when every run is reversed. Visual PDF pages: 80,104,133,137,139,140.
- Expanded: Erev PDF: service boundaries, closing cue, retained Ark instructions and apparatus checked; start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
303 pages; contents generated; day bookmarks above pizmons; first-day prayers [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; first pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; second pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; third pizmon [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; later pizmons {'fourth': [0.0, 0.0, 0.0, 0.0, 0.0], 'fifth': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'sixth': [0.0, 0.0, 0.0, 0.0, 0.0], 'seventh': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}; footnotes and expansion boundaries checked; controls=True
  Direction: 0 of 13150 Hebrew runs are set left to right; control: 12061 of 13150 flagged when every run is reversed. Visual PDF pages: 222,295,301.

48 shared scan tests and 22 assembly tests pass. Artifacts: `output/asher_selichot/proofreading/batch-014/`. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains.


## Proofreading checkpoint015

The committed Hebrew proofreading checkpoint reaches the end of Tzom Gedaliah, printed103 (s208/n207). Batch015 covers13 Hebrew pages from s184/n183 lower:107 replacement rules across16 XML modules. Frozen readings, comparisons, native-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-15/. This is a same-model second image pass with prior exposure, primarily consonant-first. Uncertain rare words remain recorded; independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.

16 modules validate;38 source-ordered units, documentary branches, notes and bilingual expansion targets checked. Expanded compiled verification passes all four petition ranges and Ten Days Kaddish. The PDF checker uses the unchanged stanza words דמי אחיו after correcting the opening טעה גועו. No generic executable logic changed.
- Documentary: warning: ICC support is not available
Gedaliah PDF: apparatus, fulfilled cues and reference boundaries checked; 8 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
26 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 763 Hebrew runs are set left to right; control: 755 of 763 flagged when every run is reversed. Visual PDF pages: 5,17,18,21,23,24,25.
- Expanded: warning: ICC support is not available
Gedaliah PDF: apparatus, fulfilled cues and reference boundaries checked; 8 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
53 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 2041 Hebrew runs are set left to right; control: 1981 of 2041 flagged when every run is reversed. Visual PDF pages: 37,49,51.

Artifacts: `output/asher_selichot/proofreading/batch-015/`. These PDFs contain Tzom Gedaliah alone. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains.


## Proofreading checkpoint016

The committed Hebrew proofreading checkpoint reaches the end of the second penitential day, printed115 (s232/n231). Batch016 covers12 Hebrew pages from s210/n209:92 text replacement rules across10 XML modules, plus synchronization of the printed opening and its refrain expansion. Frozen readings, comparisons, native-band adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-16/. This is a same-model second image pass with prior exposure, primarily consonant-first. Uncertain rare words remain recorded; independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.

10 modules validate;40 source-ordered bilingual units, seven pizmon units and bilingual expansion targets checked. Expanded compiled verification passes all four petition ranges and Ten Days Kaddish. Two PDF anchors follow corrected words עבדיך and לפתוחך. No generic executable logic changed.
- Documentary: warning: ICC support is not available
second penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 7 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue
25 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 683 Hebrew runs are set left to right; control: 681 of 683 flagged when every run is reversed. Visual PDF pages: 18,22,24,25.
- Expanded: second penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 7 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue
54 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 1992 Hebrew runs are set left to right; control: 1941 of 1992 flagged when every run is reversed. Visual PDF pages: 34,36,48,51,53.

Artifacts: `output/asher_selichot/proofreading/batch-016/`. These PDFs contain the second penitential day alone. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains.


## Proofreading checkpoint017

The committed Hebrew proofreading checkpoint reaches the end of the third penitential day, printed128 upper (s258/n257). Batch017 covers13 Hebrew pages from s234/n233:191 text replacement rules across10 Hebrew XML modules, plus synchronization of the concluding opening-repeat cue. Two English XML files have regeneration-only whitespace/declaration-ID changes. Frozen readings, comparisons, native-band adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-17/. This is a same-model second image pass with prior exposure, primarily consonant-first. Uncertain rare words remain recorded; independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.


Validation:

- All 12 changed XML modules validate; 36 bilingual units, refrain choices, notes, source order and expansion targets pass reverse verification.
- Expanded compilation verifies four bilingual petition ranges and seasonal Half/Full Kaddish.
- Documentary PDF: 26 pages; expanded PDF: 54 pages. All six stanza-start deltas are 0.0pt in each view. Contents, bookmark hierarchy, note occurrences and reference boundaries pass.
- Direction: 0/762 reversed Hebrew runs in documentary; 0/2014 in expanded. Reversed controls flag 749 and 1963 respectively. Missing-note, shifted-stanza and fulfilled-cue controls are rejected.
- Visual inspection: documentary pages 18, 19, 21, 24; expanded pages 34, 35, 48, 54.
- Shared scan tests (48) and Asher service tests (106) pass. Changes to the PDF checker are declarative text anchors; no generic executable logic changed.

Artifacts: `output/asher_selichot/proofreading/batch-017/`. These PDFs contain the third penitential day alone. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains.


## Proofreading checkpoint018

The committed Hebrew proofreading checkpoint reaches the end of the fourth penitential day, printed140 upper (s282/n281). Batch018 covers13 Hebrew pages from s258/n257 lower:120 text replacement rules across10 Hebrew XML modules, with 50 additional unchanged confirmations. Two English XML files have regeneration-only whitespace/declaration-ID changes. Frozen readings, comparisons, native-band adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-18/. This is a same-model second image pass with prior exposure, primarily consonant-first. Uncertain rare words remain recorded; independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.

12 modules validate;36 source-ordered bilingual units, eight pizmon units and bilingual expansion targets checked. Expanded compiled verification passes all four petition ranges and Ten Days Kaddish. No generic executable logic changed.
- Documentary: warning: ICC support is not available
fourth penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 8 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue
25 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 708 Hebrew runs are set left to right; control: 704 of 708 flagged when every run is reversed. Visual PDF pages: 19,20,22,25.
- Expanded: warning: ICC support is not available
fourth penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 8 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue
53 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True
  Direction: 0 of 1958 Hebrew runs are set left to right; control: 1909 of 1958 flagged when every run is reversed. Visual PDF pages: 31,32,34,35,48,52,53.

Artifacts: `output/asher_selichot/proofreading/batch-018/`. These PDFs contain the fourth penitential day alone. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains.


## Proofreading checkpoint019

The committed Hebrew proofreading checkpoint reaches the end of the fifth penitential day, printed153 upper (s308/n307). Batch019 covers14 Hebrew pages from s282/n281 lower:177 replacement rules across11 Hebrew XML modules, with39 unchanged confirmations. Two English XML files have regeneration-only whitespace/declaration-ID changes. Frozen readings, comparisons, native-band adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-19/. This is a same-model second image pass with prior exposure, primarily consonant-first. Uncertain rare words remain recorded; independent-person Hebrew, facing-English and comprehensive fine-pointing review remain pending.

13 modules validate;39 source-ordered bilingual units, five pizmon units and bilingual expansion targets checked. Expanded compiled verification passes all five petition ranges and seasonal Half/Full Kaddish. Shared scan and Asher service assembly tests:154 pass. No generic executable logic changed.

- Documentary: fifth penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 5 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue; 26 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 706 Hebrew runs are set left to right; control: 701 of 706 flagged when every run is reversed. Visually inspected PDF pages: [12, 20, 21, 22, 25, 26].
- Expanded: fifth penitential day PDF: apparatus, fulfilled cues and reference boundaries checked; 5 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; Penitential PDF controls rejected missing notes, shifted stanza and fulfilled cue; 55 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 2012 Hebrew runs are set left to right; control: 1951 of 2012 flagged when every run is reversed. Visually inspected PDF pages: [20, 21, 34, 35, 36, 54].

Artifacts: `output/asher_selichot/proofreading/batch-019/`. These PDFs contain the fifth penitential day alone. Whole-book PDFs remain earlier snapshots; the known mixed-note paragraph separation issue remains. Counts describe adjudication operations; fine pointing and rare words remain provisional.


## Proofreading checkpoint 020

The committed Hebrew proofreading checkpoint reaches the end of Erev Yom Kippur, printed 159 upper (s320/n319). Batch 020 covers seven Hebrew pages from s308/n307 lower: 74 replacement operations and 30 unchanged confirmations. Seven XML files validate, including the bilingual rename of Adon din im tedaqdeq to match its corrected incipit. Frozen captures, comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-20/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Seven XML files validate; 22 source-ordered bilingual units, seven pizmon units and one abbreviation choice per language pass. One expanded petition range and seasonal Half/Full Kaddish pass. All seven source footnotes occur once; the unresolved opening mark remains recorded. Shared scan and Asher service assembly tests: 154 pass. No generic executable logic changed. The poem registry is declarative; its corrected URN resolves during both compilations.

- Documentary: Erev Yom Kippur PDF: seven notes, fulfilled cues and closing boundaries checked; 7 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Erev Yom Kippur PDF controls rejected missing notes, shifted stanza and fulfilled cue; 17 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 424 Hebrew runs are set left to right; control: 421 of 424 flagged when every run is reversed. Visually inspected PDF pages: [9, 10, 11, 12, 13, 16].
- Expanded: Erev Yom Kippur PDF: seven notes, fulfilled cues and closing boundaries checked; 7 stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Erev Yom Kippur PDF controls rejected missing notes, shifted stanza and fulfilled cue; 26 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 821 Hebrew runs are set left to right; control: 806 of 821 flagged when every run is reversed. Visually inspected PDF pages: [15, 19, 20, 21, 24, 25].

Artifacts: `output/asher_selichot/proofreading/batch-020/`. These PDFs isolate Erev Yom Kippur. Whole-book PDFs remain earlier snapshots. Enlarged crops corrected several fresh-reading errors; the frozen captures and tentative adjudication reversals remain available.


## Proofreading checkpoint 021

The committed Hebrew proofreading checkpoint reaches the end of Monday / Second Fast, printed 167 upper (s336/n335). Batch 021 covers nine Hebrew pages from s320/n319 lower: 81 replacement operations and 41 unchanged confirmations. Five XML files validate. Frozen captures, pre-edit comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-21/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Five XML files validate; 26 source-ordered bilingual units, eight shared pizmon units, seven Hebrew / six English abbreviation choices, 15 source notes and expansion targets pass. Both PDFs preserve weekday performance instructions and omit unrequested Full Kaddish; documentary cues and expanded asymmetric refrains pass. The PDF stanza anchor was corrected from לוקתה to the image reading לקתה; no generic executable logic changed. All 154 shared scan and service assembly tests pass.

- Documentary: Monday fast PDF: 15 notes, asymmetric refrains, performance rubrics and boundaries checked; 8 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Monday fast broken controls rejected; 20 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 482 Hebrew runs are set left to right; control: 478 of 482 flagged when every run is reversed. Visually inspected PDF pages: [7, 9, 11, 13, 14, 18].
- Expanded: Monday fast PDF: 15 notes, asymmetric refrains, performance rubrics and boundaries checked; 8 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Monday fast broken controls rejected; 22 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 604 Hebrew runs are set left to right; control: 597 of 604 flagged when every run is reversed. Visually inspected PDF pages: [14, 15, 16, 21].

Artifacts: `output/asher_selichot/proofreading/batch-021/`. These PDFs isolate Monday; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 022

The committed Hebrew proofreading checkpoint reaches the end of Thursday / Fifth Fast, printed 170 (s342/n341). Batch 022 covers four Hebrew pages from s336/n335 lower: 38 replacement operations and 19 unchanged confirmations. Five XML files validate. Frozen captures, pre-edit comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-22/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Five XML files validate; 15 source-ordered bilingual units, six shared pizmon units, five abbreviation choices per language and expansion targets pass. Both PDFs preserve weekday performance instructions and omit unrequested Full Kaddish. Documentary output has two source footnotes; expanded output also carries 14 Monday notes. Six stanza starts align at 0.0 pt, direction and broken controls pass. All 154 shared scan and service assembly tests pass. No generic executable logic changed.

- Documentary: thursday-fast: 2 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; thursday-fast: 2 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; thursday-fast: missing-note and shifted-stanza controls rejected; 12 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 168 Hebrew runs are set left to right; control: 167 of 168 flagged when every run is reversed. Visually inspected PDF pages: [7, 8, 9, 10, 11].
- Expanded: thursday-fast: 10 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; thursday-fast: 10 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; thursday-fast: missing-note and shifted-stanza controls rejected; 21 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 545 Hebrew runs are set left to right; control: 540 of 545 flagged when every run is reversed. Visually inspected PDF pages: [9, 13, 14, 20].

Artifacts: `output/asher_selichot/proofreading/batch-022/`. These PDFs isolate Thursday; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 023

The committed Hebrew proofreading checkpoint reaches the end of Last Monday / Last of the Three Fasts, printed 174 upper (s350/n349). Batch 023 covers four Hebrew pages from s344/n343: 35 replacement operations and 25 unchanged confirmations. Six XML files validate. Frozen captures, pre-edit comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-23/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Six XML files validate; 14 source-ordered bilingual units, five shared pizmon units, one abbreviation choice per language and expansion targets pass. Both PDFs preserve weekday performance instructions and omit unrequested Full Kaddish. Documentary output has one source footnote; expanded output also carries 14 Monday notes. Five stanza starts align at 0.0 pt, direction and broken controls pass. All 154 shared scan and service assembly tests pass. No generic executable logic changed.

- Documentary: last-monday-fast: 1 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; last-monday-fast: 1 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; last-monday-fast: missing-note and shifted-stanza controls rejected; 12 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 194 Hebrew runs are set left to right; control: 192 of 194 flagged when every run is reversed. Visually inspected PDF pages: [7, 8, 9, 10, 11].
- Expanded: last-monday-fast: 9 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; last-monday-fast: 9 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0]; last-monday-fast: missing-note and shifted-stanza controls rejected; 21 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 574 Hebrew runs are set left to right; control: 568 of 574 flagged when every run is reversed. Visually inspected PDF pages: [9, 13, 14, 20].

Artifacts: `output/asher_selichot/proofreading/batch-023/`. These PDFs isolate Last Monday; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 024

The committed Hebrew proofreading checkpoint reaches the end of Tenth of Tevet, printed 178 upper (s358/n357). Batch 024 covers five Hebrew pages from s350/n349 lower: 40 replacement operations and 30 unchanged confirmations. Five XML files validate. Frozen captures, pre-edit comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-24/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Five XML files validate; 15 source-ordered bilingual units, fourteen shared pizmon units, thirteen Hebrew and twelve English abbreviation choices and expansion targets pass. Both PDFs preserve weekday performance instructions and omit unrequested Full Kaddish. Documentary output has ten source footnotes; expanded output also carries 14 Monday notes. Fourteen stanza starts align at 0.0 pt, direction and broken controls pass. All 154 shared scan and service assembly tests pass. No generic executable logic changed.

- Documentary: tenth-tevet: 10 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; tenth-tevet: 10 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; tenth-tevet: missing-note and shifted-stanza controls rejected; 15 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 304 Hebrew runs are set left to right; control: 304 of 304 flagged when every run is reversed. Visually inspected PDF pages: [7, 8, 9, 10, 11, 12, 13, 14].
- Expanded: tenth-tevet: 18 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; tenth-tevet: 18 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; tenth-tevet: missing-note and shifted-stanza controls rejected; 25 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 781 Hebrew runs are set left to right; control: 773 of 781 flagged when every run is reversed. Visually inspected PDF pages: [10, 13, 15, 18, 22, 24].

Artifacts: `output/asher_selichot/proofreading/batch-024/`. These PDFs isolate Tenth of Tevet; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 025

The committed Hebrew proofreading checkpoint reaches the end of Fast of Esther, printed 183 upper (s368/n367). Batch 025 covers six Hebrew pages from s358/n357 lower: 57 replacement operations and 32 unchanged confirmations. Four XML files validate. Frozen captures, pre-edit comparisons, enlarged-image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-25/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Four XML files validate; 14 source-ordered bilingual units, eight shared pizmon units, seven Hebrew and zero English abbreviation choices and expansion targets pass. Both PDFs preserve weekday performance instructions and omit unrequested Full Kaddish. Documentary output has nineteen source footnotes; expanded output also carries 14 Monday notes. Eight stanza starts align at 0.0 pt, direction and broken controls pass. All 154 shared scan and service assembly tests pass. No generic executable logic changed.

- Documentary: esther-fast: 18 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; esther-fast: 18 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; esther-fast: missing-note and shifted-stanza controls rejected; 16 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 250 Hebrew runs are set left to right; control: 250 of 250 flagged when every run is reversed. Visually inspected PDF pages: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16].
- Expanded: esther-fast: 26 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; esther-fast: 26 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; esther-fast: missing-note and shifted-stanza controls rejected; 24 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 623 Hebrew runs are set left to right; control: 615 of 623 flagged when every run is reversed. Visually inspected PDF pages: [9, 14, 17, 20, 24].

Artifacts: `output/asher_selichot/proofreading/batch-025/`. These PDFs isolate Fast of Esther; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 026

The committed Hebrew proofreading checkpoint reaches the end of Seventeenth of Tammuz, printed 187 (s376/n375). Batch 026 covers five Hebrew pages from s368/n367 lower: 53 replacement operations and 33 unchanged confirmations. Eight current XML files validate, including two renamed bilingual poem pairs and their transclusions. Frozen captures, pre-edit comparisons, image adjudication, identity corrections and hashes are under sources/asher_selichot/proofreading/image-pass-26/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Eight XML files validate; 14 source-ordered bilingual units and four shared pizmon units pass. Both PDFs preserve performance instructions and omit unrequested Full Kaddish. Thirteen documentary and twenty-one expanded apparatus fingerprints pass; four stanza starts align at 0.0 pt. Direction and deliberately broken controls pass. All 207 shared scan, service assembly and URN registry tests pass. Poem identities now reflect the verified incipits אתאונן־לך יוצר רוחות and אמרר בבכי מפני יד שלחה. No generic executable logic changed.

- Documentary: tammuz-fast: 13 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0]; tammuz-fast: 13 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0]; tammuz-fast: missing-note and shifted-stanza controls rejected; 14 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 245 Hebrew runs are set left to right; control: 243 of 245 flagged when every run is reversed. Visually inspected PDF pages: [7, 8, 9, 10, 11, 12, 13, 14].
- Expanded: tammuz-fast: 21 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0]; tammuz-fast: 21 apparatus fingerprints; stanza start deltas [0.0, 0.0, 0.0, 0.0]; tammuz-fast: missing-note and shifted-stanza controls rejected; 23 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 628 Hebrew runs are set left to right; control: 618 of 628 flagged when every run is reversed. Visually inspected PDF pages: [9, 12, 14, 18, 22].

Artifacts: `output/asher_selichot/proofreading/batch-026/`. These PDFs isolate Seventeenth of Tammuz; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 027

The committed Hebrew proofreading checkpoint reaches the end of Yom Kippur Katan, printed 203 upper (s408/n407 upper). Batch 027 covers sixteen Hebrew pages from s378/n377: 92 replacement operations. Thirteen current XML files validate; 61 source-ordered bilingual units pass. Frozen captures, pre-edit comparisons, image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-27/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

Thirteen XML files validate; 61 source-ordered bilingual units pass. Both PDFs preserve performance instructions, omit fulfilled expansion cues, retain the interleaved petition rubric at its source position, and exclude the following circumcision poem. Nine source notes appear once; 21 stanza starts align at 0.0 pt. Direction and deliberately broken controls pass. All 154 shared scan and service assembly tests pass. No generic executable logic changed.

- Documentary: Yom Kippur Katan: 9 source notes; 21 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Yom Kippur Katan: 9 source notes; 21 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Yom Kippur Katan: missing-note and shifted-stanza controls rejected; 30 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 800 Hebrew runs are set left to right; control: 793 of 800 flagged when every run is reversed. Visually inspected PDF pages: [7, 12, 14, 16, 18, 21, 24, 27, 29, 30].
- Expanded: Yom Kippur Katan: 9 source notes; 21 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Yom Kippur Katan: 9 source notes; 21 stanza deltas [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; Yom Kippur Katan: missing-note and shifted-stanza controls rejected; 40 pages; contents and top-level day/subordinate pizmon bookmarks checked; controls=True Direction: 0 of 1241 Hebrew runs are set left to right; control: 1227 of 1241 flagged when every run is reversed. Visually inspected PDF pages: [7, 9, 15, 22, 30, 36, 39, 40].

Artifacts: `output/asher_selichot/proofreading/batch-027/`. These PDFs isolate Yom Kippur Katan; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## Proofreading checkpoint 028

The Hebrew second image pass reaches the final Hebrew page, printed 204 (s410/n409), after the circumcision poem. Batch 028 covers s408/n407 lower–s410/n409: five replacement operations and synchronized refrain metadata. One XML file validates; all three source-ordered bilingual units pass. Frozen captures, pre-edit comparisons, image adjudication and hashes are under sources/asher_selichot/proofreading/image-pass-28/. This is a same-model second image pass with prior exposure, primarily consonant-first. Independent-person Hebrew, facing-English and comprehensive pointing review remain pending.

One XML file validates; three source-ordered bilingual units pass. Both eight-page PDFs preserve the cross-page verse, alternating Hebrew refrains, printed English omission and the unresolved English superscript, and exclude the preceding monthly service. All five stanza starts align at 0.0 pt. Direction and deliberately broken marker, stanza and restored-verse controls pass. All 154 shared scan and service assembly tests pass. The whole-book verification passes all 398 XML files and all service documentary comparisons and expansion boundaries. The full suite passes: 3,557 tests, with 12 skips (732.140 seconds). No generic executable logic changed.

- Documentary: Circumcision: five stanza baseline deltas [0.0, 0.0, 0.0, 0.0, 0.0]; alternating Hebrew refrains, English omission, unresolved marker and final boundary checked; Circumcision: five stanza baseline deltas [0.0, 0.0, 0.0, 0.0, 0.0]; alternating Hebrew refrains, English omission, unresolved marker and final boundary checked; Circumcision: missing-marker, shifted-stanza and missing-restored-verse controls rejected; 8 pages; contents and final top-level section bookmark checked; controls=True Direction: 0 of 41 Hebrew runs are set left to right; control: 38 of 41 flagged when every run is reversed. Visually inspected PDF pages: [7, 8].
- Expanded: Circumcision: five stanza baseline deltas [0.0, 0.0, 0.0, 0.0, 0.0]; alternating Hebrew refrains, English omission, unresolved marker and final boundary checked; Circumcision: five stanza baseline deltas [0.0, 0.0, 0.0, 0.0, 0.0]; alternating Hebrew refrains, English omission, unresolved marker and final boundary checked; Circumcision: missing-marker, shifted-stanza and missing-restored-verse controls rejected; 8 pages; contents and final top-level section bookmark checked; controls=True Direction: 0 of 39 Hebrew runs are set left to right; control: 39 of 39 flagged when every run is reversed. Visually inspected PDF pages: [7, 8].

Artifacts: `output/asher_selichot/proofreading/batch-028/`. These PDFs isolate the final circumcision poem; whole-book PDFs remain earlier snapshots. Rare word uncertainties and corrections to the fresh capture remain in the per-page ledgers.


## English proofreading checkpoint 001

English title s3/n2 and complete first day s7/n6–s53/n52 upper were reread from images before opening the same-service existing readings/XML/OCR. The ledger records 29 distinct corrections across working readings and assembled data; 12 English XML modules changed. Printed archaic forms and apparent printing errors remain. This is a same-model second pass with prior exposure, not independent-person proofreading. Exhaustive emphasis and the exact s23 Reader-alone note anchor remain pending. Frozen captures, comparison snapshots and adjudications are under `sources/asher_selichot/proofreading/english-pass-01/`.

All 398 book XML files validate and all service documentary streams and expansion checks pass. Current first-day-only documentary and expanded PDFs pass prayer alignment, footnote occurrence, Kaddish context, fulfilled-instruction and boundary checks, including deliberately broken controls. All six measured prayer starts align at 0.0 pt. Contents and bookmark checks pass. The initial expanded inspection dropped pre-Rosh-Hashanah entrypoint declarations; the Kaddish check detected the error. Corrected inspection exports preserve those declarations.

- Documentary: 37 pages; 0 of 1283 Hebrew runs are set left to right; control: 1253 of 1283 flagged when every run is reversed; PDF SHA-256 `648edb103d61c8614b388325b181763a0fa084045ee4477cee8733d3665b4a35`.
- Expanded: 42 pages; 0 of 1509 Hebrew runs are set left to right; control: 1471 of 1509 flagged when every run is reversed; PDF SHA-256 `9a3f9fc30a23d881f125c65814437c5cb04ba1e9f55d4c92ebdba225bdb81cca`.

Artifacts: `output/asher_selichot/proofreading/english-001/`. Whole-book PDFs remain earlier snapshots. No executable logic changed; the previous full suite result was 3,557 passed with 12 skips.


## English proofreading checkpoint 002

Second-day English s53/n52 lower–s61/n60 upper was image-reread and frozen before comparison. Ten corrections cover the printed wording and punctuation; the seven English footnotes match the fresh readings. Ten second-day XML files validate, and documentary page streams, refrain choices, notes, ordering and expansion boundaries pass. Both service-only PDFs pass six pizmon alignment checks at 0.0 pt, footnote counts, fulfilled-instruction/third-day boundaries, contents and bookmark hierarchy. Duplicate-note, shifted-stanza and boundary controls are rejected. Same-model second pass; exhaustive typography and independent-person proofreading remain pending.

- Documentary: 13 pages; 0 of 194 Hebrew runs are set left to right; control: 194 of 194 flagged when every run is reversed; SHA-256 `c5f54550b9684490753ca72bf15f3a499bdda919d7f33aadf851bef432fa4de1`.
- Expanded: 36 pages; 0 of 1242 Hebrew runs are set left to right; control: 1218 of 1242 flagged when every run is reversed; SHA-256 `bea4021af12fc4c98d32a35b704d7032eec804ab85378d15a53d55157ceb37f5`.

Evidence: `sources/asher_selichot/proofreading/english-pass-02/`. Artifacts: `output/asher_selichot/proofreading/english-002/`. Whole-book PDFs remain earlier snapshots; no executable logic changed.


## English proofreading checkpoint003

Third-day English s61/n60 lower–s69/n68 upper was reread from images before comparison, following image-verified printed31/32 despite swapped Archive leaves. Four corrections preserve the printed wording and punctuation, including “oppessors.” Ten XML files validate and reverse verification checks source order, footnotes, choice branches and expansions. Both service PDFs pass all six stanza alignment checks at0.0pt, eight printed footnotes, direction, contents, bookmarks and section boundaries; deliberately duplicated notes, shifted stanzas and boundary leakage are rejected. Visual inspection covers the opening poem, pizmon, apparatus and expanded conclusion. Same-model second pass; independent-person and exhaustive typography review remain pending. The numeral-inclusive audit of batches001–002 found no further corrections.

- Documentary: 14 pages; 0 of 263 Hebrew runs are set left to right; control: 262 of 263 flagged when every run is reversed; SHA-256 `59c195e0495762836ed75ff8f2b1e4907c0a3b88f0b5acc706e219491a90a00e`.
- Expanded: 37 pages; 0 of 1302 Hebrew runs are set left to right; control: 1278 of 1302 flagged when every run is reversed; SHA-256 `b945b709d078ac90b0504069caf7ea90021c46ea71cc76fdce81e2d0137c4509`.

Evidence: `sources/asher_selichot/proofreading/english-pass-03/`. Artifacts: `output/asher_selichot/proofreading/english-003/`. Whole-book PDFs remain earlier snapshots. No executable logic changed.


## English proofreading checkpoint004

Fourth-day English s69/n68 lower–s77/n76 upper was reread from images before comparison. Six punctuation corrections are confirmed; damaged “from” is retained, and the punctuation after “unintelligible” remains uncertain with the existing colon retained. Ten XML files validate and reverse verification checks source order, footnotes, choice branches and expansions. Both service PDFs pass all five stanza alignment checks at0.0pt, eight printed footnotes, direction, contents, bookmarks and section boundaries; deliberately duplicated notes, shifted stanzas and boundary leakage are rejected. Visual inspection covers the opening poem, pizmon, apparatus and expanded conclusion. Same-model second pass; independent-person and exhaustive typography review remain pending.

- Documentary: 14 pages; 0 of 258 Hebrew runs are set left to right; control: 258 of 258 flagged when every run is reversed; SHA-256 `d34c075052b6578239cae59ba80de50c648a748b3d7435777040f6ffd80085bf`.
- Expanded: 37 pages; 0 of 1302 Hebrew runs are set left to right; control: 1277 of 1302 flagged when every run is reversed; SHA-256 `82d09ca4b90ac5604ef21996375a3e9b1ac65cbfc2e4e93e0830408718b753c3`.

Evidence: `sources/asher_selichot/proofreading/english-pass-04/`. Artifacts: `output/asher_selichot/proofreading/english-004/`. Whole-book PDFs remain earlier snapshots. No executable logic changed.


## English proofreading checkpoint005

Fifth-day English s77/n76 lower–s85/n84 upper was reread from images before comparison. Five corrections restore printed wording/punctuation, including “by a law.” Damaged final letter of “Noachic” remains uncertain; existing spelling retained. Ten XML files validate and reverse verification checks source order, footnotes, choice branches and expansions. Both service PDFs pass all eight stanza alignment checks at0.0pt, eight printed footnotes, direction, contents, bookmarks and section boundaries; deliberately duplicated notes, shifted stanzas and boundary leakage are rejected. Visual inspection covers the opening poem, pizmon, apparatus and expanded conclusion. Same-model second pass; independent-person and exhaustive typography review remain pending.

- Documentary: 14 pages; 0 of 263 Hebrew runs are set left to right; control: 263 of 263 flagged when every run is reversed; SHA-256 `f9f145c37539ba55116e02b98ec365ea775be6132819b890b17aa22f98279e06`.
- Expanded: 36 pages; 0 of 1270 Hebrew runs are set left to right; control: 1249 of 1270 flagged when every run is reversed; SHA-256 `4d861dac614ae1a9c8d6c75881e5931555dc156089e583beae0f8fef28a5e236`.

Evidence: `sources/asher_selichot/proofreading/english-pass-05/`. Artifacts: `output/asher_selichot/proofreading/english-005/`. Whole-book PDFs remain earlier snapshots. No executable logic changed.


## English proofreading checkpoint006

Sixth-day English s85/n84 lower–s93/n92 upper was read from images and frozen before comparison. Seven corrections restore printed wording/punctuation and remove the unprinted English cue after “O God of the faithful.” Its empty Hebrew cue already represented no print; replacing that cue pair with empty full-text segments also removes unsupported expansion in both languages. Ten XML files validate; documentary reverse comparison, source order, notes, choice branches and expansion boundaries pass. Both service PDFs pass all stanza alignment checks at0.0pt, 6 printed footnotes, direction, contents, bookmarks and boundary checks. Duplicate-note, shifted-stanza and boundary controls fail as intended. Representative source body, pizmon, apparatus and expanded conclusion inspected visually. Same-model second pass; independent-person and exhaustive typography review remain pending.

- Documentary: 13 pages; 0 of 259 Hebrew runs are set left to right; control: 259 of 259 flagged when every run is reversed; SHA-256 `1bb03703944d27ac29377e2860c5d8945213641126c684d15c8d69dbf1018666`.
- Expanded: 37 pages; 0 of 1303 Hebrew runs are set left to right; control: 1276 of 1303 flagged when every run is reversed; SHA-256 `c85f8be2c96b27772f2a1536afc2afe31a938e4eee64b42685e38cff48ebabe9`.

Evidence: `sources/asher_selichot/proofreading/english-pass-06/`. Artifacts: `output/asher_selichot/proofreading/english-006/`. Whole-book PDFs remain earlier snapshots. No generic executable logic changed.


## English proofreading checkpoint007

Seventh-day English s93/n92 lower–s101/n100 upper was read from images and frozen before comparison. Two missing commas are restored in printed rubrics; the body, eight footnotes and printed refrain occurrences match the fresh reading. The fresh s97 label47 is only a candidate, since no numeral is visible. Ten XML files validate; documentary reverse comparison, source order, notes, choice branches and expansion boundaries pass. Both service PDFs pass all stanza alignment checks at0.0pt, 8 printed footnotes, direction, contents, bookmarks and boundary checks. Duplicate-note, shifted-stanza and boundary controls fail as intended. Representative source body, pizmon, apparatus and expanded conclusion inspected visually. Same-model second pass; independent-person and exhaustive typography review remain pending.

- Documentary: 14 pages; 0 of 282 Hebrew runs are set left to right; control: 282 of 282 flagged when every run is reversed; SHA-256 `405780300babf2e56ef81a60a14da13bb039e22f8fd5e30a0bcc3f477c63b700`.
- Expanded: 38 pages; 0 of 1326 Hebrew runs are set left to right; control: 1266 of 1326 flagged when every run is reversed; SHA-256 `025451ac86a11b192c794f8151d727015b170b741ac0cee014e0224394659cb8`.

Evidence: `sources/asher_selichot/proofreading/english-pass-07/`. Artifacts: `output/asher_selichot/proofreading/english-007/`. Whole-book PDFs remain earlier snapshots. No generic executable logic changed.


## English proofreading checkpoint008

Erev Rosh Hashanah English s101/n100 lower–s185/n184 upper (printed 49–91) was image-reread and all 43 captures frozen before comparison. Fifty image-adjudicated token corrections restore printed wording, punctuation and citations. Forty-four XML files validate; all 113 service units reverse-compare including documentary branches, notes and bilingual expansion targets. All 12 compiled bilingual petition expansions and page 52 wording pass. Both service PDFs pass the six start-alignment anchors, all 59 printed English notes, apparatus direction, contents, bookmark hierarchy, fulfilled instructions and service boundaries. Duplicate-note, shifted-alignment, boundary and direction controls fail as intended. Representative source body, pizmon, apparatus and expanded conclusion inspected visually. Same-model second pass with prior exposure; independent-person and exhaustive typography review remain pending. Tamid 1–26 are unresolved printed markers without accompanying apparatus on these source pages; no references are invented.

- Documentary: 70 pages; 0 of 2933 Hebrew runs are set left to right; control: 2815 of 2933 flagged when every run is reversed; SHA-256 `05ad5f559e95f65630a188bafefca8d7fbdc93f418e7c5909b85839e33e5e532`.
- Expanded: 93 pages; 0 of 3975 Hebrew runs are set left to right; control: 3779 of 3975 flagged when every run is reversed; SHA-256 `5305cce55e5ccb057978c01aee80dbb450755d8972bc383b089f797c8699fc35`.

Evidence: `sources/asher_selichot/proofreading/english-pass-08/`. Artifacts: `output/asher_selichot/proofreading/english-008/`. Whole-book PDFs remain earlier snapshots. No generic executable logic changed.


## English proofreading checkpoint009

Tzom Gedaliah English s185/n184 lower–s209/n208 (printed 91–103) was image-reread and all 13 captures frozen before comparison. Ten image-adjudicated token corrections restore printed wording, quotation marks, notes and rubric punctuation. Whole-page viewer images were used for the first reading; targeted full-resolution crops adjudicate differences. The capture helper’s overgeneralized native-band description is clarified in the separate adjudication without rewriting immutable captures. Thirty-two XML files validate; all 38 bilingual service units, eight stanza groups, seven refrain choices per language and apparatus reverse-compare. All four compiled petition expansions, Ten Days Half/Full Kaddishes and suppression of fulfilled rubrics pass. Both PDFs pass eight stanza alignment starts, all 18 English notes and the Hebrew marginal note, apparatus direction, contents, bookmark hierarchy, expansions and service boundaries. Duplicate-note, shifted-stanza, missing marginal note and direction controls fail as intended; expanded controls reject wrong seasonal Kaddish counts, a duplicated opening and fulfilled rubrics. Representative opening, pizmon, mixed-language apparatus and closing expansion inspected visually. Same-model second pass with prior exposure; independent-person and exhaustive typography review remain pending.

- Documentary: 26 pages; 0 of 763 Hebrew runs are set left to right; control: 755 of 763 flagged when every run is reversed; SHA-256 `21b5213cca51504cc93a0a8251514713e53048405f7e7e4575e43112cf50509a`.
- Expanded: 53 pages; 0 of 2041 Hebrew runs are set left to right; control: 1981 of 2041 flagged when every run is reversed; SHA-256 `79ff1dd7f578fac1a3a3d0fb9f3ebf1ac6bf378b3c115998e9680460f6ca0257`.

Evidence: `sources/asher_selichot/proofreading/english-pass-09/`. Artifacts: `output/asher_selichot/proofreading/english-009/`. Whole-book PDFs remain earlier snapshots. No generic executable logic changed. Preceding checkpoint CI tests, CodeQL and Codecov all passed.


## English proofreading checkpoint010

[English batch010](`sources/asher_selichot/proofreading/english-pass-10/batch-010.json`) covers Second penitential day, s211/n210–s233/n232, printed104–115.
12 image-first page observations were frozen before cached OCR comparison;
7 image-adjudicated replacement rules changed 9 stored occurrences.
Schema, source-order reverse comparison, compilation, both service PDFs, all printed
English-page notes, contents/bookmarks, alignment and deliberately broken controls pass.
Documentary: 25 pages; expanded: 54 pages.
This is same-model proofreading with prior exposure, sparse observations and OCR-assisted
comparison, rather than a second full manual transcription or independent-person review.
Exhaustive typography review remains pending. See the adjudication for uncertain readings.

- Documentary: 25 pages; 0 of 683 Hebrew runs are set left to right; control: 681 of 683 flagged when every run is reversed; SHA-256 `9e05792dc6013d912a3518fd548c031a78405f5a8ecf6334375efedd49b94afd`.
- Expanded: 54 pages; 0 of 1992 Hebrew runs are set left to right; control: 1941 of 1992 flagged when every run is reversed; SHA-256 `87bb4b67c2efad3456aca1abb0c0b701c5b75d26c15490c95d2da72fe3064bd5`.

Artifacts: `output/asher_selichot/proofreading/english-010/`. Whole-book PDFs remain earlier snapshots.


## English proofreading checkpoint011

[English batch011](`sources/asher_selichot/proofreading/english-pass-11/batch-011.json`) covers Third penitential day, s235/n234–s259/n258 upper, printed116–128 upper.
13 image-first page observations were frozen before cached OCR comparison;
13 image-adjudicated replacement rules changed 15 stored occurrences.
Schema, source-order reverse comparison, compilation, both service PDFs, all printed
English-page notes, contents/bookmarks, alignment and deliberately broken controls pass.
Documentary: 26 pages; expanded: 54 pages.
This is same-model proofreading with prior exposure, sparse observations and OCR-assisted
comparison, rather than a second full manual transcription or independent-person review.
Exhaustive typography review remains pending. See the adjudication for uncertain readings.

- Documentary: 26 pages; 0 of 762 Hebrew runs are set left to right; control: 749 of 762 flagged when every run is reversed; SHA-256 `648fe5fa6873dbe3d401734fdf8ad7f5b27a166e920634a1fcf035f4ffa7ed1c`.
- Expanded: 54 pages; 0 of 2014 Hebrew runs are set left to right; control: 1963 of 2014 flagged when every run is reversed; SHA-256 `97cf3d7bd04e3ef396097ac5990832160f63f263c934c2ee5973c8a18e8c4fc8`.

Artifacts: `output/asher_selichot/proofreading/english-011/`. Whole-book PDFs remain earlier snapshots.


## English proofreading checkpoint012

[English batch012](`sources/asher_selichot/proofreading/english-pass-12/batch-012.json`) covers Fourth penitential day, s259/n258 lower–s283/n282 upper, printed128 lower–140 upper.
13 image-first page observations were frozen before cached OCR comparison;
14 image-adjudicated replacement rules changed 15 stored occurrences.
Schema, source-order reverse comparison, compilation, both service PDFs, all printed
English-page notes, contents/bookmarks, alignment and deliberately broken controls pass.
Documentary: 25 pages; expanded: 53 pages.
This is same-model proofreading with prior exposure, sparse observations and OCR-assisted
comparison, rather than a second full manual transcription or independent-person review.
Exhaustive typography review remains pending. See the adjudication for uncertain readings.

- Documentary: 25 pages; 0 of 708 Hebrew runs are set left to right; control: 704 of 708 flagged when every run is reversed; SHA-256 `c6cf9ba9460c3286652b1d97c2df740bc1518d6fe4bb0fcea8ab728ed8648ed3`.
- Expanded: 53 pages; 0 of 1958 Hebrew runs are set left to right; control: 1909 of 1958 flagged when every run is reversed; SHA-256 `256710b3cb0023a188ae4e7286b36ec5c4b66f94b851a8aec9493e5802f7b120`.

Artifacts: `output/asher_selichot/proofreading/english-012/`. Whole-book PDFs remain earlier snapshots.


## English proofreading checkpoint013

[English batch013](`sources/asher_selichot/proofreading/english-pass-13/batch-013.json`) covers Fifth penitential day, s283/n282 lower–s309/n308 upper, printed140 lower–153 upper.
14 image-first page observations were frozen before cached OCR comparison;
7 image-adjudicated replacement rules changed 7 stored occurrences.
Schema, source-order reverse comparison, compilation, both service PDFs, all printed
English-page notes, contents/bookmarks, alignment and deliberately broken controls pass.
Documentary: 26 pages; expanded: 55 pages.
This is same-model proofreading with prior exposure, sparse observations and OCR-assisted
comparison, rather than a second full manual transcription or independent-person review.
Exhaustive typography review remains pending. See the adjudication for uncertain readings.

- Documentary: 26 pages; 0 of 706 Hebrew runs are set left to right; control: 701 of 706 flagged when every run is reversed; SHA-256 `2c66df1014b28144384448a5505ed6ce3e5724a571b5fbcd2693feb0e5c6cfce`.
- Expanded: 55 pages; 0 of 2012 Hebrew runs are set left to right; control: 1951 of 2012 flagged when every run is reversed; SHA-256 `11ca6c42afff44084829661aa0f22c1acb16ad38ac4ee8ef042ff39f2e86b51b`.

Artifacts: `output/asher_selichot/proofreading/english-013/`. Whole-book PDFs remain earlier snapshots.
