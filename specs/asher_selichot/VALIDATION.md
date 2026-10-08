# Reproducing the Asher first- and second-day encoding

Use the three companion `feat_asher-selichot-pilot` worktrees (the historical
branch name is retained). Pass standalone source and project directories
explicitly: `sourcetexts/feat_asher-selichot-pilot/sources` and
`opensiddur-projects/feat_asher-selichot-pilot/project`. Initialize code submodules,
install dependencies and build the schema before trusting validation. Archive
requests used efraim@opensiddur.org. Images, compiled XML, TeX and PDFs remain
untracked under output/asher_selichot.

## Coverage and reusable modules

Both title pages (n1/n2), the entire first day (through n51/n52), and the entire
second day (from the midpage heading on n51/n52 to the closing rubric in the
middle of n59/n60) are encoded. The third-day section is excluded, despite the
third-day running header above the last second-day material.

There are 55 XML files per language: 51 independent named texts and four actual
book/service assemblies (`index.xml`, `expanded.xml`, `first_day.xml`,
`second_day.xml`). Both book entrypoints include the title pages and transclude
the same two day assemblies. Common prayers use common names; piyyutim use their
distinctive incipits. Publication `@project` suffixes retain edition provenance.
Artificial authoring-batch grouping files remain removed. The source
`text-modules.json` records all independent module identities.

The second day adds Eiyyeh qinatkha, Ein qore beshimkha, Avvitikha qivitikha and
Israel Nosha. Hebrew poems use `lg`/`l`, retaining page breaks inside continuing
verses; English translations retain printed prose. Israel Nosha has six named
stanza milestones, terminated before unrelated text, four short refrain choices
and a final choice expanding the entire opening stanza including its refrain.
Seven English notes match the scan; two have the same patriarchs wording.

The first-day poetic adjudication remains recorded separately in
`poetry-structure.json`: Mi Sheanah has 20 verse lines and terminal refrains,
Anenu has 35 terminal responses, and Rahmana has four before changing petitions.
The invocation אלהינו ואלהי אבותינו remains body text in each piyyut.

## Regenerate and verify

```bash
python -m opensiddur.importer.asher_selichot.download --source-root "$source_root" --output-root "$output_root" --regenerate
python -m opensiddur.importer.asher_selichot.build --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.importer.asher_selichot.verify --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.exporter.refdb --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_he_1912 --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_en_1912 --project-directory "$project_root"
python -m opensiddur.common.urn_registry --check --project-directory "$project_root"
```

All 110 Asher XML files validate. Six opening page/language streams, seven
refrain/prayer streams and 96 first-day continuation units match readings.
The second-day verification follows all 15 units per language in source order,
compares documentary branches by scan page/language, checks footnotes separately,
and audits referenced prayer ranges and five refrain expansions per language.
Both language projects resolve all URNs/transclusions. The registry has 3,009
records: 2,937 canonical, 50 aliases and 22 contexts; zero errors/warnings and
four informational alias-migration notes concerning other projects.

## Compile and render

All four local export settings enable `typography.table_of_contents` through
level two. Both day headings are top-level bookmarks; each printed pizmon is a
child. The second-day English scan has no pizmon caption, so none is invented.

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

Add `--expanded` to the book checker for that view. PDF builds and the full suite
run serially because they use the shared reference database. Refresh it for the
standalone companion projects after the tests. SBL Hebrew at 12pt supplies the
raised phrase dots; the checker uses edition-calibrated 288pt/324pt alternating
gutters and a 16pt stanza baseline tolerance.

| Rendered check | Documentary | Expanded |
|---|---|---|
| PDF pages | 43 | 70 |
| First-day prayer-start differences | six 0pt | six 0pt |
| First pizmon stanza-start differences | first 13.55pt, seven 0pt | eight 0pt |
| Second pizmon stanza-start differences | six 0pt | six 0pt |
| Reversed Hebrew runs | 0 / 1,403 | 0 / 2,610 |
| Reversed-run control flags | 1,372 / 1,403 | 2,544 / 2,610 |
| TOC and bookmark hierarchy | pass | pass |
| Apparatus and expansion boundaries | pass | pass |

The book checker scopes the existing first-day checks using PDF outline
destinations while retaining page parity and excluding the TOC. It independently
checks second-day stanzas, notes, direction, fulfilled cues and referenced prayer
occurrences. The original second-day footnote citing Deut. iv. 31 occurs once;
expanded closing transclusions also carry their own separately sourced note with
that citation. Broken controls reject shifted stanza starts, duplicated notes,
wrong abbreviation branches, incorrectly nested day bookmarks, collapsed verses,
stranded/wrong punctuation, omitted repetitions and unwanted calendar additions.
Visual inspection confirmed both day/pizmon hierarchy and the corrected TOC.

Expanded second-day text supplies the verified opening range, bounded repeated
verses, three El Melekh/Vayaavor pairs and the first-day closing range beginning
Zekhor rahamekha. Fulfilled instructions are omitted. The secondary Full Kaddish
uses the Birnbaum projects selected in settings; its scope has `first_day=false`
and `aseret-ymei-tshuva=false`, then restores caller context. The first-day
Kaddish retains its own `first_day=true`, Ten Days false declaration.

A generic TOC defect discovered during rendering is fixed separately in code
PR #225: Polyglossia's `.toc` language switches mirrored Hebrew-only entries,
reversing page 35 as 53. Each contents line now uses an LTR slot while preserving
Hebrew title runs and bookmark text. Its LuaLaTeX regression fails on the original
exporter and passes after the fix. The regression, LaTeX driver and XSLT tests
pass 348 tests and 126 subtests. TOC-depth assertions retain local-scope checks
while allowing the direction setup. The fix is also applied to this worktree's PDF builds.

## Regression status and remaining work

The final full suite passes 3,052 tests and 4,673 subtests, with 12 skipped.
It emits one existing invalid `\p` escape warning in an unrelated XSLT-test
docstring. The two earlier TOC string assertions were updated in the separate
fix PR; the complete rerun is clean. Both PDF builds and the suite ran serially.

Synthetic importer checks cover poetry/page crossings, shared identities,
abbreviation expansions, existing repetition-feature defaults, source-verified
opening boundaries, contents settings and bookmark hierarchy. The full suite
includes Birnbaum regressions and the generic compiler/apparatus fixes tracked
separately in #217 and #218.

Independent Hebrew pointing proofreading remains pending, especially dense
second-day rhymed lines. Immutable first readings, same-assistant image-pass
corrections and English OCR comparison provenance are retained in source evidence.
Later-day encoding, full-volume conversion, publication and release integration
remain outside current coverage; these modules form the final book's foundation.
