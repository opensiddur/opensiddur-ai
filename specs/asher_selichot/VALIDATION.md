# Reproducing the Asher Selichoth encoding

Use the three companion `feat_asher-selichot-pilot` worktrees; the branch name
is historical. Pass standalone source/project directories explicitly. Initialize
code submodules, install dependencies and build the schema before validation.
Archive requests use efraim@opensiddur.org. Scan images, OCR cache, compiled XML,
TeX and PDFs remain untracked under `output/asher_selichot`.

## Current coverage

Both title pages and the first six complete days are encoded through Archive n91/n92, before the seventh-day body heading. There are 142 XML files (71 per language): 63 independent named texts and eight book/service assemblies. Daily checkpoints below record current validation and rendering results. Independent Hebrew proofreading remains pending.

## First-three-day validation baseline

Both title pages and the first three complete days are encoded, ending above the
fourth-day section heading on Archive n67/n68. Printed pages 31 and 32 have
swapped Archive openings: Hebrew order is s60, s62, s66, s64, s68; English is
s61, s63, s67, s65, s69. `third-day-scope.json` documents image-verified order,
page labels, pairing and boundaries independently from physical scan identity.

There are 59 XML files per language: 54 independent named texts and five actual
book/service assemblies (`index.xml`, `expanded.xml`, `first_day.xml`,
`second_day.xml`, `third_day.xml`). Each independent piyyut has an incipit URN;
common prayers retain common names. Edition provenance is in `@project`.
Artificial authoring-batch grouping files remain removed.

The third day adds Eqra beshimkha lehahaziq bekha, Taarog eilekha kaayal and
Shahar qamti. Hebrew poetry retains `lg`/`l` and internal page breaks; English
retains printed prose. Shahar qamti has six named stanza milestones, four short
refrain choices and a final complete-opening choice. All eight English notes
retain image-verified anchors. Its pure Hebrew repeated-verse rubric retains
Hebrew language. The invocation אלהינו ואלהי אבותינו remains body text.

The first pizmon's English running page header is reclassified as source
metadata and removed from its body and TOC. The actual Hebrew פזמון heading
remains. All three day headings are top-level bookmarks above their pizmons.
All four local settings generate contents through level two.

Expanded numbered-day services replace fulfilled instructions with the verified
opening range, bounded repeated verses, three El Melekh/Vayaavor pairs, and
closing prayers from Zekhor rahamekha. The unprinted Full Kaddish is supplied
from Birnbaum through default settings. Each numbered-day declaration sets
`first_day=false`, `aseret-ymei-tshuva=false`, then restores caller context.
First-day Kaddish keeps its own `first_day=true`, Ten Days false scope.

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

All 118 XML files validate. Six opening page/language streams, seven
refrain/prayer streams, 96 first-day continuation units and all 15 units per
language in each numbered day match documentary readings. Reverse checks
follow encoded printed order, compare only documentary choice branches, audit
footnotes separately and check referenced prayer ranges/expansions. Both
projects resolve all URNs/transclusions. Registry: 3,038 records, 2,966 canonical,
50 aliases, 22 contexts; zero errors/warnings, four informational migration notes
concerning other projects. Skill frontmatter validates and reference links resolve.

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
| PDF pages | 49 | 100 |
| First-day prayer starts | six 0pt differences | six 0pt differences |
| First pizmon stanza starts | first 13.55pt, seven 0pt | eight 0pt |
| Second pizmon stanza starts | six 0pt | six 0pt |
| Third pizmon stanza starts | six 0pt | six 0pt |
| Reversed Hebrew runs | 0 / 1,657 | 0 / 3,845 |
| Reversed-run control flags | 1,621 / 1,657 | 3,747 / 3,845 |

Book checks scope each day by outline destinations while retaining page parity.
They audit notes, language direction, fulfilled cues, prayer occurrences and the
fourth-day boundary. Broken controls reject duplicate notes, shifted stanzas,
wrong choices, incorrectly nested bookmarks, collapsed verses, wrong/stranded
punctuation, omitted repetitions and unwanted calendar additions. The TOC check
also compares rendered page numbers against current bookmark destinations and
rejects deliberately stale numbers.

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

Merged current upstream `main` (8891637) into the code branch as 221ce00 before
pushing. The settings-example conflict retains both abbreviation selection and
upstream electronic-book typography guidance. Sources/projects already contain
their current `master`/`main` bases. Final compilation includes the enlarged-image
Hebrew adjudications recorded in the source proofreading evidence.

Synthetic importer checks cover reordered scans, pure Hebrew rubric direction,
closed day-specific conditional/declaration scopes, reusable identities, poetry,
choice expansions, contents settings, bookmark hierarchy and stale TOC detection.
The final full suite passes: 3,209 tests and 4,781 subtests, with 18 skips,
in 587.15 seconds. This includes relevant Birnbaum regressions. Both projects
resolve all URNs/transclusions after restoring the standalone reference database.
The final 49-page documentary and 100-page expanded renders both pass the book
and direction checks, including deliberately broken controls. Documentary day
three starts on printed PDF page 36; expanded day three starts on page 63.
All six contents entries match the current bookmark destinations. The final TOCs
and third-day verse/footnote pages were also inspected visually.

Independent Hebrew consonant/pointing proofreading remains pending, especially
in dense rhymed lines. Immutable first readings, same-assistant image-pass
adjudications and English OCR comparison provenance remain in source evidence.
Conversion beyond the currently encoded days, publication and release integration remain outside current
coverage. Local settings keep this incomplete book out of automatic releases.

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
