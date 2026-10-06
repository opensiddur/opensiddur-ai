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

Seven stanza starts have identical baselines; the first differs by 13.55pt after
unequal rubric lengths. The pilot limit is 16pt on the same PDF page. Latin anchor
runs have increasing glyph x coordinates. No Hebrew run is reversed: documentary
0/54, expanded 0/104; reversed controls flag 54/54 and 104/104 respectively.
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
