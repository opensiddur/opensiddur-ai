# Reproducing the Asher pilot

Use the three companion `feat_asher-selichot-pilot` worktrees. The source root is
`sourcetexts/feat_asher-selichot-pilot/sources`; the project root is
`opensiddur-projects/feat_asher-selichot-pilot/project`. Pass both explicitly.
Initialize code submodules, install all dependency groups, and build the schema
before validation. Archive requests use the shared client and a reachable contact
address; the pilot download used efraim@opensiddur.org.

```bash
python -m opensiddur.importer.asher_selichot.download --source-root "$source_root" --output-root "$output_root" --regenerate
python -m opensiddur.importer.asher_selichot.build --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.importer.asher_selichot.verify --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_he_1912 --project-directory "$project_root" --index
python -m opensiddur.exporter.validate_urn_references asher_selichot_en_1912 --project-directory "$project_root" --index
```

For each `view` of `documentary` and `expanded`, compile and render serially:

```bash
python -m opensiddur.exporter.compiler -s "specs/asher_selichot/$view.yaml" --project-directory "$project_root" -o "$output_root/asher_selichot/$view.xml"
python -m opensiddur.exporter.pdf.pdf -s "specs/asher_selichot/$view.yaml" --project-directory "$project_root" --keep-tex --build-dir "$output_root/asher_selichot/build-$view" "$output_root/asher_selichot/$view.xml" "$output_root/asher_selichot/$view.pdf"
python -m opensiddur.importer.scan.pdf_direction "$output_root/asher_selichot/$view.pdf" "$output_root/asher_selichot/$view.tex" --control
python -m opensiddur.importer.asher_selichot.check_pdf "$output_root/asher_selichot/$view.pdf" --control
```

Add `--expanded` to `check_pdf` for that view. On a restricted filesystem, set
`TEXMFVAR` and `TEXMFCACHE` to a writable directory before rendering or running
PDF regression tests. The pilot used `/tmp/asher-tex-cache`. The required SBL Hebrew
font includes the raised dots missing from the available CLM faces.

## Observed results

All ten XML files validate. Seven documentary page/language streams match the
adjudicated readings. Shared URNs align eight stanza pairs. The PDFs have five
(documentary) and six (expanded) pages, including front matter and metadata.
Both render the English footnote once. Only the expanded view includes the two
referenced prayers, ending before “The hope of Israel.”

All eight expanded stanza starts have identical baselines. In the documentary
view, seven match and the first differs by 13.55pt after unequal rubric lengths. The pilot limit is 16pt on the same PDF page. Latin anchor
runs have increasing glyph x coordinates. No Hebrew run is reversed: documentary
0/54, expanded 0/99; reversed controls flag 54/54 and 99/99 respectively.
Duplicate-footnote, 50pt stanza-shift, and wrong-expansion controls all fail.
Screenshots of the content pages were inspected for pointing, dots, bilingual
rubrics, alignment, and prayer boundaries. The generic root parallel warning is
expected: alignment is supplied by the transcluded modules' shared URNs.

Skill frontmatter validation and Markdown reference-link checks pass. Source
accuracy limits are recorded in `sources/asher_selichot/scan_reading/accuracy.md`.
This pilot does not claim whole-volume conversion or publication readiness.

The serial full regression run passed: 3,020 tests, 4,656 subtests, 12 skips
(542.52 seconds). This includes the Birnbaum importer regressions and existing
kri/ktiv and alternate-wording checks. Six older transclusion assertions now
expect the printed abbreviation alone under the new default, instead of both forms.
Both pilot projects pass URN resolution after indexing their companion worktree;
the registry has 2,931 records with zero errors or warnings.

Companion commits: sources `4af4d77`; projects `f25ef1d`. The code submodules retain
their release pins; these pilot projects are deliberately supplied through the
explicit project-directory argument rather than changing those pins.


After suppressing fulfilled expansion instructions, the relevant conditional,
abbreviation and shared scan tests pass (36 tests, 26 subtests). Both PDFs were
rebuilt and their checks pass, including failing controls. The expanded view omits
the opening repetition rubric and concluding “Say …”; the documentary view retains
both. Independent `asher:expansions` declarations control refrain and prayer
instructions, allowing either to remain when its requested text is absent.

## First-day opening increment

The builder now produces 14 schema-valid XML files. Four new files provide the
partial `first_day.xml` entrypoint and its `first_day_opening.xml` module in each
language. The entrypoint includes both complete title pages, and only the contiguous
opening through Half Kaddish; it does not claim to reach the recorded n52 boundary.
Six additional source-page/language streams match the committed opening readings.
Both title pages also match their readings, including credentials and imprints.
The first-day final boundary and pending range are in `first-day-scope.json`.

Compile/render `first-day` with the same commands above. The previous pilot entrypoints
and PDF calibrations are retained. Hebrew opening pointing remains provisional until
an independent scan reading is compared. The historical full-suite result above
predates this authoring increment.

Opening-increment checks passed: 302 relevant exporter and scan-tool tests; all
14 XML files validate; both projects resolve URNs after syncing their changed
source modules into the reference database. Registry validation reports 2,934
records with zero errors or warnings. If regenerating previously indexed modules,
use `ReferenceDatabase.sync_project(project_name, project_root)` before resolution;
plain `--index` can retain an obsolete element location during authoring.

The first-day opening PDF has eight pages, including both title pages, blank verso
pages, and metadata. All four checked bilingual prayer starts have identical
baselines. No Hebrew run is reversed (0/84); the reversed control flags 83/84.
The Latin Psalm citation occurs once in the Hebrew column and its glyph coordinates
increase. Reversed-citation, 50pt prayer-shift, and next-day-boundary controls fail.
Removing the continuation of Psalm 145:9 and substituting the isolated piyyut for
the contiguous entry module also fail documentary verification. Title and prayer
pages were inspected visually; the citation is kept inside the first verse’s
alignment segment rather than emitted as an unpaired block.

```bash
python -m opensiddur.importer.asher_selichot.check_first_day_pdf "$output_root/asher_selichot/first-day.pdf" --control
```

English `tei:foreign[@xml:lang='en']` now receives a scoped LTR wrapper in the
PDF exporter, with the surrounding paragraph started before switching direction.
Two synthetic XSLT regressions cover the English citation and nested Hebrew.

The punctuation follow-up attaches all 29 closing Hebrew colons in the opening
reading and XML to their preceding words. First-pass evidence keeps the initial
spacing. The rebuilt PDF retains identical checked prayer baselines and passes
Hebrew direction checks (0/85 reversed, 84/85 flagged by the reversed control).
The PDF check now rejects isolated colon lines: it fails on the pre-fix PDF and
on a synthetic stranded-colon control. The corrected Psalm page was inspected
visually; verse-ending punctuation remains with its word across line wrapping.
All 14 XML files and the documentary stream comparisons still pass.

The Hebrew two-dot verse-stop correction uses U+05C3 SOF PASUQ (׃), attached to
its preceding word, throughout the opening and pilot modules, including expanded
refrains. The first-pass evidence retains its initial provisional colon encoding.
All 14 XML files and documentary streams validate; all three PDFs were rebuilt
and pass alignment, footnote/range, and direction checks. The opening check rejects
both a stranded sof pasuq and an ASCII colon substituted for a Hebrew verse stop.

## Complete first-day continuation (current)

The complete documentary day has 20 schema-valid project XML files. Both title
pages, six opening page/language streams, seven pilot streams and 96 continuation
units match their source readings. All source leaves are present in monotonic
order through n51/n52, and 22 continuation footnotes match their recorded text.
Missing-final-rubric, duplicate-footnote, next-day-heading and wrong-page controls
all fail verification. The new synthetic fixtures cover page crossings, repeated
anchors, absent anchors, litanies and mixed-language rubrics.

`first-day.pdf` has 35 pages. Six prayer-start pairs have baseline differences of
0pt, with a measured 16pt maximum allowed. The Latin Psalm citation occurs once in
the Hebrew column and reads left to right. Hebrew glyph verification finds 0/1,250
runs reversed; reversing them flags 1,224/1,250. PDF controls reject shifted prayer
starts, reversed citation, next-day heading, isolated or wrong verse stops, missing
final Kaddish and duplicate explanatory footnote. The original documentary and
expanded pilot checks still pass, including all eight stanza pairs and their
footnote and reference boundaries. Running headers identify the first day even
after the piyyut, rather than inheriting its heading. Long Hebrew/English prose
blocks can occupy different numbers of lines; alignment is at complete prayers.

Independent Hebrew pointing proofreading remains pending. English OCR comparison
records still contain unresolved findings; automatic comparison does not adjudicate
against the edition. Full-volume encoding and publication remain outside this work.

Reproduce the complete first-day PDF using `first-day.yaml` in the same compile
and render commands above; set both `TEXMFVAR` and `TEXMFCACHE` to a writable
cache. Then run:

```bash
python -m opensiddur.importer.asher_selichot.check_first_day_pdf "$output_root/asher_selichot/first-day.pdf" --complete --control
python -m opensiddur.importer.scan.pdf_direction "$output_root/asher_selichot/first-day.pdf" "$output_root/asher_selichot/first-day.tex" --control
```

The serial full regression run passed: 3,028 tests and 4,660 subtests passed; 12 skipped (recommended pytest runner, 585.75 seconds).

Use `python -m pytest -q` with both TeX cache variables set as above. A broad
`unittest discover` run encountered font-loading failures in geometry fixtures;
the affected facing-page fixture passed in isolation and the complete recommended
pytest run passed. The new synthetic unittest fixtures also pass discovery alone.

Current companion commits: source `1e561c1`; projects `8a69fea`. The URN registry
contains 2,985 records with no errors or warnings; four informational notes concern
existing alias migrations in other projects.

## Invocation structure follow-up

The three recurring piyyut invocations now remain in opening body text in both
languages. Distinctive incipits identify the poems in source metadata and URN
labels; no additional printed heading is introduced. The primary readings remain
unchanged. Six focused tests and two language subtests pass. Reverse verification
checks this structure and rejects a deliberately restored invocation heading.
All 20 XML files validate, documentary streams match, and both projects resolve
URNs/transclusions. Skill frontmatter and scan reference links validate.

The rebuilt first-day PDF still has 35 pages, six identical prayer-start baselines,
and 0/1,250 reversed Hebrew runs. Direction, alignment, verse-stop, footnote and
n52 boundary controls pass; the reversed-direction control flags 1,224 runs.
Visual inspection of page 14 confirms the invocation is ordinary opening text
in both columns. The full-suite result above precedes this focused correction;
the focused checks and rendering were rerun for this follow-up.

## Expanded complete first day with Full Kaddish fallback

`default.yaml` selects `first_day_expanded.xml`, expanded abbreviation readings,
and all supplied-text flags. It prioritizes Asher and then Birnbaum in both
languages. The expanded PDF has 40 pages. All six checked prayer-start pairs have
identical baselines. Hebrew direction verification finds 0/1,475 reversed runs;
the deliberately reversed control flags 1,439. Visual inspection confirms the
bilingual Titkabel and closing peace passages, and the source list includes both
Asher and Birnbaum.

PDF checks require four occurrences of El Melekh, three of each repeated verse
range and Ashamnu, and one complete closing Kaddish. They reject missing repetitions,
retained fulfilled instructions, omitted Titkabel, reversed direction, shifted
alignment, stranded/wrong verse stops, duplicated footnotes and next-day content.
Compiled XML resolves every transclusion; its Full Kaddish contains all six parts
once per language and draws exclusively from the Birnbaum projects.

All 22 Asher XML files validate; both new Birnbaum Full Kaddish wrappers also
validate. Documentary comparisons still match 96 continuation units, six opening
streams and seven pilot streams. Reverse verification separately audits the
editorial targets and conditional branch polarity before comparing the printed
branch. Both Asher projects resolve URNs; the registry now has 2,989 records with
no errors or warnings. Skill references and both view settings validate.

The serial focused regression run passes 161 tests and 56 subtests, covering
Asher encoding, Birnbaum conclusion assembly, abbreviation readings, marker
reconstruction, conditional scopes and parallel compilation/apparatus. It includes
controls for a disabled transclusion to an absent source and English fallback
priority/restoration. The historical full-suite result above precedes this increment.

Reproduce the expanded PDF with the same compile/render commands, using
`specs/asher_selichot/default.yaml` and `first-day-expanded.xml` / `.pdf` output
paths. Check it with:

```bash
python -m opensiddur.importer.asher_selichot.check_first_day_pdf "$output_root/asher_selichot/first-day-expanded.pdf" --complete --expanded --control
python -m opensiddur.importer.scan.pdf_direction "$output_root/asher_selichot/first-day-expanded.pdf" "$output_root/asher_selichot/first-day-expanded.tex" --control
```

The documentary settings disable the supplied-text branches; their compilation
requires no Birnbaum fallback. The marker compiler skips disabled transclusions
before resolving them, preserving the documentary edition’s printed instructions.

The rebuilt documentary PDF remains 35 pages with six identical checked baselines,
0/1,252 reversed Hebrew runs, and 1,226 flagged by its reversed control. Its printed
Kaddish rubric and all documentary rendering controls pass after the conditional
transclusion fix.

## Mixed-language apparatus paragraph direction

The English paragraph inside the Hebrew commentary note was explicitly marked
`xml:lang="en"`, but the apparatus emitter ignored that paragraph’s language.
The separate exporter fix is PR #218. Both new synthetic direction tests fail
against the previous exporter; its 292 PDF-transform tests and 126 subtests pass
with the fix. The new Asher Latin-apparatus glyph check rejects the original PDF
on page 9, even though its old Hebrew-direction check passed.

Both first-day PDFs were rebuilt. The documentary edition remains 35 pages and
the expanded edition 40 pages; all six checked prayer-start baselines coincide.
Latin apparatus runs pass the new baseline/font grouping check and a deliberately
reversed note fails. Hebrew direction still reports 0/1,252 reversed runs in the
documentary edition and 0/1,475 in the expanded edition, with reversed controls
flagging 1,226 and 1,439 respectively. Existing repetition, reference-boundary,
footnote and punctuation checks pass. Visual inspection of expanded page 9 confirms
the English explanation reads left to right and its Hebrew passages are preserved.
The XML language declarations and source readings required no changes.

After merging the separate fix into the Asher worktree, all 303 combined
PDF-transform/Asher encoding tests and 128 subtests pass (one pre-existing warning).
