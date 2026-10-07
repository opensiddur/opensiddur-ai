# Reproducing the Asher first-day encoding

Use the three companion `feat_asher-selichot-pilot` worktrees (the existing branch
name is retained). Pass standalone source and project directories explicitly:
`sourcetexts/feat_asher-selichot-pilot/sources` and
`opensiddur-projects/feat_asher-selichot-pilot/project`. Initialize code submodules,
install dependencies, and build the schema before trusting validation. Archive
requests use a reachable contact address; this work used efraim@opensiddur.org.
Images, compiled XML, TeX and PDFs stay outside git under output/asher_selichot.

## Reusable text modules

There are 50 XML files per language: 47 named text modules and three book/service
assemblies. `index.xml` is the documentary book entrypoint; `expanded.xml` is the
expanded book entrypoint. Each includes both title pages and transcludes the
same `first_day.xml` assembly. This directly references independent texts by
source-independent canonical URN and retains printed rubrics. Artificial opening,
preface, before-piyyut and closing subdivision files are removed, along with the
redundant expanded first-day assembly. The generator prunes these obsolete files
after replacement XML validates; their URNs are removed from the registry. Incomplete book
coverage is recorded in edition metadata, rather than in text identities.

`identities.py` maps continuation evidence IDs to filenames and registry identities;
`sources/asher_selichot/text-modules.json` records the complete editorial mapping.
The Hebrew and English projects share canonical identities and alignment URNs,
while their publication `@project` suffixes retain edition and language provenance.
Common prayers use common names, including `prayer:ashrei`, `prayer:ashamnu` and
`prayer:kaddish/chatzi`. Piyyutim use distinctive incipits in their own files.
The common אלהינו ואלהי אבותינו invocation stays in the piyyut opening.

## Hebrew poetry and refrains

Twelve additional Hebrew units use `tei:lg`/`tei:l` rather than paragraphs.
A separate source `poetry-structure.json` records scan identities, verified line
stops and verse/refrain counts. Mi Sheanah has 20 verse lines with 20 terminal
`tei:seg type="refrain"` responses; Anenu has 35 and Rahmana has four responses.
The English translation structures and all documentary words remain unchanged.
Source-page breaks inside a verse do not introduce a new verse. Verification
audits poetic structure separately from text equality, rejecting paragraph
substitutions and missing or misplaced refrains. Complete PDF checks require
20 distinct Mi Sheanah verse starts and 20 responses, and reject a removed-line
control. The shared skill now explicitly distinguishes verse structure from
physical wrapping and retains prose translations independently.

## Regenerate and validate

```bash
python -m opensiddur.importer.asher_selichot.download --source-root "$source_root" --output-root "$output_root" --regenerate
python -m opensiddur.importer.asher_selichot.build --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.importer.asher_selichot.verify --source-root "$source_root" --project-directory "$project_root"
python -m opensiddur.exporter.refdb --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_he_1912 --project-directory "$project_root"
python -m opensiddur.exporter.validate_urn_references asher_selichot_en_1912 --project-directory "$project_root"
python -m opensiddur.common.urn_registry --check --project-directory "$project_root"
```

The builder validates every file before writing. Reverse verification follows the
flat service assembly in source-page order, checks each extracted module's canonical
publication identity and correspondence, and compares it to its documentary
reading. It separately audits expansion targets, branches, bounded repeat ranges,
printed footnotes and scoped first-day Kaddish context.

Results after extraction:

- All 100 Asher XML files are schema-valid; both Birnbaum Full Kaddish wrappers
  remain schema-valid. No experimental-phase labels remain in the Asher XML.
- Six opening page/language streams, seven refrain/prayer streams, both title pages
  and 96 continuation units match their documentary readings. Facsimiles follow
  source order through n51/n52; second-day text is excluded.
- Both projects resolve URNs/transclusions after synchronization. The registry has
  2,980 records, zero errors and zero warnings; four informational alias-migration
  notes concern other projects.
- Skill frontmatter, relative reference links and four export settings validate.
- Compiled word occurrences in both views are unchanged by module extraction.
  Source-order comparison is performed against readings, independently of those
  compiled word counts.

## Compile and render both book views

Run tests and PDF builds serially because both use the reference database. Set
both TeX caches to a writable directory; SBL Hebrew supplies this edition's raised
phrase dots missing from the available CLM faces.

```bash
export TEXMFVAR=/tmp/asher-tex-cache
export TEXMFCACHE=/tmp/asher-tex-cache
python -m opensiddur.exporter.compiler -s specs/asher_selichot/first-day.yaml --project-directory "$project_root" -o "$output_root/asher_selichot/first-day.xml"
python -m opensiddur.exporter.pdf.pdf -s specs/asher_selichot/first-day.yaml --project-directory "$project_root" --keep-tex --build-dir "$output_root/asher_selichot/build-first-day" "$output_root/asher_selichot/first-day.xml" "$output_root/asher_selichot/first-day.pdf"
python -m opensiddur.exporter.compiler -s specs/asher_selichot/default.yaml --project-directory "$project_root" -o "$output_root/asher_selichot/first-day-expanded.xml"
python -m opensiddur.exporter.pdf.pdf -s specs/asher_selichot/default.yaml --project-directory "$project_root" --keep-tex --build-dir "$output_root/asher_selichot/build-first-day-expanded" "$output_root/asher_selichot/first-day-expanded.xml" "$output_root/asher_selichot/first-day-expanded.pdf"
```

`documentary.yaml` and `expanded.yaml` select these same book views. All settings
remain under specifications, outside automatic release-book settings.

For each PDF, run the checks below; add `--expanded` to both Asher checks for the
expanded PDF:

```bash
python -m opensiddur.importer.asher_selichot.check_first_day_pdf "$pdf" --complete --control
python -m opensiddur.importer.asher_selichot.check_pdf "$pdf" --complete --control
python -m opensiddur.importer.scan.pdf_direction "$pdf" "$tex" --control
```

Measured results:

| Check | Documentary | Expanded |
|---|---|---|
| PDF pages | 35 | 40 |
| Six prayer-start baseline differences | all 0pt | all 0pt |
| Eight piyyut stanza-start differences | first 13.55pt, seven 0pt | all 0pt |
| Reversed Hebrew runs | 0 / 1,216 | 0 / 1,436 |
| Deliberately reversed runs flagged | 1,190 / 1,216 | 1,402 / 1,436 |
| Page-15 English footnote | once | once |

The stanza check follows ordered anchors from the poem's opening, excluding a
short matching anchor in an earlier piyyut. Both actual PDFs and synthetic fixtures
exercise that distinction. The 16pt baseline limit and alternating 288pt/324pt
gutters are calibrated to these settings, rather than universal scan conventions.

English apparatus paragraphs have increasing glyph x coordinates even inside
Hebrew notes. The Latin Psalm citation appears once in the Hebrew column. Hebrew
verse stops are attached U+05C3 sof pasuq, with no stranded stops or ASCII colons.
Documentary output retains printed cues. Expanded output omits fulfilled cues,
including the poem conclusion whose prayers are supplied in its own conditional
branch. Both views share the first-day assembly. It expands verified refrains, repeats bounded scriptural petitions and Ashamnu, and
supplies El Melekh/Vayaavor at the recorded positions.

The final Full Kaddish contains all six edition-bound Birnbaum parts once per
language. Its first-day declaration explicitly disables the Ten Days aggregate,
excluding the extra לעילא and its rubric even with conflicting caller settings;
the declaration restores caller context afterward. The original reusable Birnbaum
text and Asher's documentary readings are unchanged.

Broken controls are rejected: reversed Hebrew/Latin notes or citations, shifted
prayer/stanza starts, duplicated footnotes, wrong abbreviation branch, stranded or
incorrect punctuation, collapsed or missing Mi Sheanah verse starts, missing conclusion, unwanted second-day text, omitted or
duplicated repetitions, retained fulfilled instructions, and injected Ten Days
text/rubric. These checks establish observable output, rather than just XML shape.

## Regression checks and limits

```bash
python -m pytest opensiddur/tests/importer/asher_selichot opensiddur/tests/common/test_urn_registry.py -q
```

The focused module/registry run passes 70 tests and 22 subtests. Synthetic fixtures
cover separate reusable piyyut files and shared Hebrew/English identities, canonical
Ashrei/Kaddish, crossed page breaks, printed notes, invocation placement, repetition
boundaries, conflicting calendar settings and caller-context restoration. Geometry
fixtures reject actual misalignment while excluding an earlier matching anchor.

The earlier full-suite run passed 3,028 tests and 4,660 subtests with 12 skipped;
that historical run precedes the later encoding/context/module changes. Generic
compiler and apparatus-direction fixes were merged separately in code PRs #217
and #218. No new compiler bug fix is included in this module reorganization.

First-day coverage is complete. Independent Hebrew pointing review and unresolved
OCR findings remain, recorded with the source evidence. Full-volume conversion,
publication and release integration are outside the current coverage, but these
modules and book entrypoints are intended for the final encoding.
