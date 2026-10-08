# Reproducing the Asher Selichoth encoding

Use the three companion `feat_asher-selichot-pilot` worktrees; the branch name
is historical. Pass standalone source/project directories explicitly. Initialize
code submodules, install dependencies and build the schema before validation.
Archive requests use efraim@opensiddur.org. Scan images, OCR cache, compiled XML,
TeX and PDFs remain untracked under `output/asher_selichot`.

## Current coverage

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
