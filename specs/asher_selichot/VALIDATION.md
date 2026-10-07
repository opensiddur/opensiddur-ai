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
