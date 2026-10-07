# Asher 1912 scan subsection

Load for Archive item `selichothdavidasher1912`: David Asher’s Selichoth,
Vallentine & Sons, London, 1912–5672 reprint (first published in 1866).
This is the edition linked by opensiddur-ai issue 207.

## Evidence and pagination

The scan has 411 leaves, reported dimensions 2013×3106. Address pages by `sN`
(one-based scan identity, IA leaf N−1), never by printed label alone: Hebrew and
English sides share a printed number. Record both the printed Hebrew label and
its numeric value when verified. Language and translation pairing are independent
of physical left/right position and must be verified from images.

Archive’s page-number JSON is sparse and wrong in places: IA leaf 30 prints 14,
not its machine label 1. Scandata lacks printed labels. Retain the metadata as
candidate evidence and apply explicit image-verified corrections to derive pages.json.

Use shared scan tools with `--book asher_selichot --source-root <sources>`.
Images and crops live under `output/asher_selichot/`; evidence belongs under
`sources/asher_selichot/`. No Wikisource check is required or currently established.
Archive OCR was configured for English: compare it with English readings only.
For Hebrew, read independently from images and record the second reading’s scope.
Do not auto-settle qamats-qatan or assume Birnbaum’s punctuation/glyph conventions.

## Pilot and interpretation

- Leaf 2: English title and imprint, explicitly dated 1912–5672.
- Leaves 31–32: Hebrew טו / English 15, במוצאי מנוחה and its translation.
- Leaves 23–26: Hebrew יא–יב / English 11–12, containing אל מלך יושב
  and ויעבור plus adjacent texts. Encode only the referenced ranges as dependencies;
  retain boundary context in readings and identify the slice precisely.
- The Hebrew poem has English rubrics with embedded Hebrew. Preserve their language
  boundaries and direction; its translation is prose, not matching printed verse lines.
  Align semantic stanzas, keeping Hebrew lineation and English paragraphs independent.
- Refrain cues such as לשמוע and “Hearken, &c.” are printed abbreviations.
  Store cues in `abbr` and the complete verified refrain in `expan`; the final
  “On the outgoing, &c.” refers to the opening stanza, not just the short refrain.
- The concluding “Say …” points back to אל מלך יושב and ויעבור. Documentary
  output retains the instruction. Expanded output replaces it with transclusions of
  this edition’s encoded prayers, and omits the opening refrain-repetition rubric
  when the refrains are expanded. Never substitute another edition’s wording.
- Retain the English footnote on page 15 and verify it appears once.
- Document every expansion and target range in the source README. Do not attribute
  expanded words to printing on a leaf where only a cue appears.

## Output and measurement

Use `readings.abbreviations: abbreviated` for the documentary pilot and `expanded`
for prayer-use output. Pilot settings stay under specs/asher_selichot, outside
release book settings. Verify both compiled and rendered outputs; derive row/column
thresholds from their actual typography rather than copying Birnbaum’s numeric values.

The pilot uses SBL Hebrew at 12pt because the available CLM faces lack U+00B7.
Its measured gutter is x=288pt on odd PDF pages and x=324pt on even pages.
All expanded stanza starts share a baseline. In documentary output, the first
differs by 13.55pt after unequal rubric lengths; the other seven share a baseline. The pilot check allows at most 16pt and requires the same page.
These are pilot calibration values, not defaults for other settings or scans.
Run `python -m opensiddur.importer.asher_selichot.check_pdf PDF --control`
(with `--expanded` for the expanded view). The shared direction check separately
reverses Hebrew glyph runs as its failing control.

## First-day continuation

The Hebrew and English title pages are Archive leaves n1 and n2. The first-day
opening is n5/n6; its first printed numeral is 3 on n7/n8. Do not assign a printed
number to the opening from the contents table or a later cross-reference.
Psalm 145:9 continues across n5→n7 and n6→n8 within a prose paragraph; retain the
source page break within the verse rather than inventing a verse boundary.

The first day ends partway down n51 (Hebrew) / n52 (English), after the Reader’s
Kaddish instruction and before the large second-day section heading. The running
heading on n51 already says second day; it does not establish the section boundary.
Keep these verified target limits separate from encoded coverage. A partial
entrypoint must identify its actual contiguous coverage and must not bridge pending
pages with isolated pilot modules. Record progress in `first-day-scope.json`.

The partial opening has a Latin `Ps. cxlv.` citation on the Hebrew page. Verify
both its increasing glyph x coordinates and its placement in the Hebrew column;
Hebrew-only direction checks cannot detect its reversal or column displacement.
Use `python -m opensiddur.importer.asher_selichot.check_first_day_pdf PDF --control`
for the current opening settings. Its 16pt baseline limit is measured for this
output, not a general scan requirement.
