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

## Refrain and prayer interpretation

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

Use `readings.abbreviations: abbreviated` for the documentary edition and `expanded`
for prayer-use output. Edition settings stay under specs/asher_selichot, outside
release book settings. Verify both compiled and rendered outputs; derive row/column
thresholds from their actual typography rather than copying Birnbaum’s numeric values.

The edition uses SBL Hebrew at 12pt because the available CLM faces lack U+00B7.
Its measured gutter is x=288pt on odd PDF pages and x=324pt on even pages.
All expanded stanza starts share a baseline. In documentary output, the first
differs by 13.55pt after unequal rubric lengths; the other seven share a baseline. The poem check allows at most 16pt and requires the same page.
These are edition calibration values, not defaults for other settings or scans.
Run `python -m opensiddur.importer.asher_selichot.check_pdf PDF --complete --control`
(with `--expanded` for the expanded view). The shared direction check separately
reverses Hebrew glyph runs as its failing control.

## First-day continuation

`sources/asher_selichot/poetry-structure.json` records image-verified Hebrew
lineation for the first-day litanies and additional poems. Mi Sheanah on s46
(Archive n45, printed 22) has 20 verse lines with terminal הוא יעננו refrains;
Anenu on s44 has 35 terminal עננו responses. Rahmana on s46 has four ענינא
responses followed by different petitions. Keep each response inside its verse
as `tei:seg type="refrain"`; do not repeat it editorially or turn it into a
heading. Raised dots can delimit poetic clauses in these specified units, but
are not a universal rule making every dotted prayer a poem. The English
translations retain their independently printed prose or litany breaks.

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
pages with isolated excerpt modules. Record progress in `first-day-scope.json`.

The opening has a Latin `Ps. cxlv.` citation on the Hebrew page. Verify
both its increasing glyph x coordinates and its placement in the Hebrew column;
Hebrew-only direction checks cannot detect its reversal or column displacement.
Use `python -m opensiddur.importer.asher_selichot.check_first_day_pdf PDF --control`
for the first-day settings; use `--complete` when rendering through n52. Its 16pt baseline limit is measured for this
output, not a general scan requirement.

For normalized authoring of this edition’s Hebrew text, encode Hebrew two-dot verse stops as U+05C3
HEBREW PUNCTUATION SOF PASUQ (׃), not U+003A COLON (:). Attach these stops and
other closing punctuation to the preceding word. Do not carry the scan’s visual
gap into XML as an ordinary breakable space: TeX can strand the punctuation on a
new line. Preserve physical spacing in the first-pass evidence and document its
normalization. The opening PDF check must reject isolated punctuation lines.

For a contiguous first-day edition, place the reusable prayers and poem at their
original n23–26 and n31–32 positions after encoding intervening text. Pair complete
prayers across languages: facing pages do not necessarily end at equivalent words,
and some litanies order phrases differently. Retain printed footnotes at their
anchors and record apparent citation errors as edition evidence. Verify the final
Reader’s Kaddish rubric, and exclude the second-day text below it on n51/n52.

The recurring אלהינו ואלהי אבותינו invocation belongs to the piyyut’s opening
text, including its English translation. Its visual separation does not make it
a heading: encode it within the Hebrew verse group and English prose paragraph.
Identify the piyyut by the distinctive incipit that follows (for example,
אין מי יקרא בצדק), recording this as an incipit rather than inventing a printed
heading or asserting an independently verified formal title. Preserve the edition’s
spelling and pointing. Only actual section headings belong in `tei:head`.

## Expanded first-day service

Replace fulfilled “Say …” cues with transclusions of their verified target ranges,
including repeated scriptural petitions and Ashamnu. Keep documentary and expanded
entrypoints sharing their source modules through conditional instruction/transclusion
branches. The poem module conditionally supplies its concluding prayers next to
the printed cue; both book views use the same `first_day.xml` assembly.
The final Kaddish Titkabel is not printed in this Asher range. For this
expanded edition, transclude the unqualified Full Kaddish URN
`urn:x-opensiddur:text:prayer:kaddish/shalem`; select Birnbaum’s Hebrew and English
projects as fallbacks in `specs/asher_selichot/default.yaml`. Preserve that provenance
in documentation and do not present the supplied prayer as an Asher scan reading.
Verify all six Full Kaddish parts, including Titkabel and the closing peace passages,
and check the English column retains its configured secondary-source fallbacks.

For mixed-language footnotes, preserve the explicit language on each paragraph;
the English explanation must not inherit the Hebrew note’s direction. Inspect
Latin glyph positions in the apparatus as well as Hebrew runs and the Psalm
citation. MuPDF can split reversed Latin text into single-character lines, so
group apparatus glyphs by page, font and baseline before measuring their order.
The first-day settings measure apparatus at 9.826pt; their check inspects Latin
runs at sizes up to 10pt. This cutoff is a calibration for these settings.

The first-day Selichot is never during the Ten Days of Repentance. Immediately
before its final Full Kaddish transclusion, declare a scoped first-day Selichot
context and set `opensiddur:holiday-aggregate/aseret-ymei-tshuva` explicitly false.
Close the declaration after the prayer, restoring the caller’s settings. Do not
leave this date-dependent addition undefined or allow an unrelated default date
to activate it. Verify that neither the extra לעילא nor its Ten Days rubric is
present in this final Kaddish, even when the caller supplies a conflicting setting.


## Reusable book structure

`index.xml` and `expanded.xml` are the documentary and expanded book entrypoints,
with both title pages and the currently encoded first day. Both reference the
single `first_day.xml` assembly, which directly transcludes named texts and retains
printed rubrics in source order. Do not create opening/preface/before-piyyut/closing
subdivision files: these were authoring batches, not printed service divisions.
An expanded first-day assembly is redundant because cue replacements are
conditional within the shared text modules and service rubrics.

Use `ashrei.xml` with `prayer:ashrei` and `kaddish_chatzi.xml` with
`prayer:kaddish/chatzi`. The distinct piyyutim have their own files and `poem:`
URNs named for their distinctive incipits: `ein_mi_yiqra_betsedeq`,
`im_avoneinu_rabu_lehagdil`, `tavo_lefanekha_shavat_hinnun`, and
`bemotzaei_menuhah`. The common invocation remains in each poem's opening.
Reusable prayers and repeated verse ranges likewise use prayer identities,
independent of Asher or the day on which this source prints them. The source
README's module table records the reading-ID to filename/URN correspondence.
Do not add experimental-phase labels to titles, filenames or canonical identities.
