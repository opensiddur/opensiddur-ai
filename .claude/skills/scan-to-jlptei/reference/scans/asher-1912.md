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
For a first-day-only export, run `python -m opensiddur.importer.asher_selichot.check_pdf PDF --complete --control`
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


## Second-day continuation

The second day begins below the first-day closing rubric on n51/n52 and ends
above the third-day section heading in the middle of n59/n60. These openings
print 25–29 in both languages; do not treat the final running third-day heading
as a section boundary. Use the printed day heading as the top-level service
heading and its printed Hebrew פזמון as a subordinate heading. Do not invent an
English pizmon caption where none is printed. Enable
`typography.table_of_contents.enabled: true` with `depth: 2` in these export settings.

Israel Nosha has six Hebrew verse groups paired with English prose paragraphs.
Use named stanza milestones to align them; retain page breaks inside a continuing
verse. Four כי אתה cues expand the edition’s full refrain; the final וישראל נושע
cue expands the first stanza including its refrain. The seven English footnotes
include two distinct occurrences of “The three patriarchs.” Keep the unusual
singular “God of our Father!” as printed, pending any documented adjudication.

The second-day opening rubric reuses the printed first-day ranges through
כי רבו עוונינו, then El erekh apayim through ורב חסד לכל קראיך. Its conclusion
reuses the closing range beginning Zekhor rahamekha and a secondary-source Full
Kaddish. Preserve first-day context only for the first day: second-day Kaddish
must not inherit `first_day=true`. Scope its copied pre-Rosh-Hashanah conclusion
with `first_day=false`, `aseret-ymei-tshuva=false`, then restore caller context.
Expanded output omits each instruction whose prescribed text is present.

Use `python -m opensiddur.importer.asher_selichot.check_book_pdf PDF --control`
(and `--expanded` for that view) for the two-day book. It scopes the older
first-day checks to the bookmarked first-day range, excludes the generated TOC,
and independently checks second-day stanzas, notes and expansion boundaries.

## Third-day continuation and swapped openings

The third day starts below the second-day conclusion on n59/n60 and ends above
the fourth-day section heading on n67/n68. Its verified printed page sequence is:

| Printed page | Hebrew scan / Archive leaf | English scan / Archive leaf |
|---|---|---|
| 29 | s60 / n59 | s61 / n60 |
| 30 | s62 / n61 | s63 / n62 |
| 31 | s66 / n65 | s67 / n66 |
| 32 | s64 / n63 | s65 / n64 |
| 33 | s68 / n67 | s69 / n68 |

The Archive openings for 31 and 32 are swapped. Read in image-verified printed
order while retaining actual scan identities on facsimile links. Record the
ordering evidence in `third-day-scope.json`; never infer a missing page solely
from a discontinuity in the physical scan sequence.

The three independent piyyutim use incipit identities `eqra_beshimkha_lehahaziq_bekha`,
`taarog_eilekha_kaayal`, and `shahar_qamti`. Shahar qamti has six Hebrew verse
groups paired with English prose, four נפשי refrain choices, and a final שחר
choice supplying its entire opening including the refrain. The last English
full refrain ends with a period, while the first ends with an exclamation mark;
retain each printed occurrence. Keep all eight English footnotes at their
image-verified anchors. The Palestine note follows “thy poor people.”

The small Hebrew-only repeated-verse instruction on printed 31 retains Hebrew
language and direction; mixed English/Hebrew rubrics retain their own language
spans. Expanded day-three instructions follow the same verified opening,
repeated-verse, prayer-pair and conclusion ranges as day two. Scope its secondary
Full Kaddish with its own declaration, `first_day=false` and Ten Days false.

Running page headers are pagination evidence, not body headings. In particular,
“PROPITIATORY PRAYERS FOR THE FIRST DAY.” above Bemotzaei menuhah is an English
running header: retain it in source evidence, omit it from the poem body and
TOC, and preserve the actual Hebrew פזמון heading. The day headings remain
at the top bookmark level, above the piyyut's printed heading.

## Days four through seven

Use the large body headings to delimit these days; the running headers can
announce the following day before its body begins. The paired ranges overlap
because two days share a printed page.

| Day | Archive leaves | Pizmon stanza groups |
|---|---|---|
| Fourth | n67–n76 | 5 |
| Fifth | n75–n84 | 8 |
| Sixth | n83–n92 | 5 |
| Seventh | n91–n100 | 9, including the opening refrain |

Keep independently printed Hebrew and English cue positions. In day five,
“O extend thy grace” follows the ocean stanza's English refrain cue, while
its Hebrew counterpart precedes that cue. Do not move the English sentence
across the cue to match Hebrew grouping. Day five prints only two prayer-pair
instructions; the other days in this table print three.

The sixth-day final חוקר cue appears only in Hebrew. Expand its verified Hebrew
opening without inventing an English cue or repetition. Day seven prints an
additional English `(Help us, &c.)` after its opening full refrain; preserve that
English choice without adding a Hebrew counterpart. Its Hebrew repetition rubric
names נשענו and עזרנו in reverse order: preserve the documentary wording and use
the complete image-verified refrain for expansion, documenting the resolution.
The English page-47 numeral is not visible: keep its printed label unknown and
record page 47 and translation pairing as separately verified evidence.

Bind this edition's spaced Hebrew phrase dots to the preceding word using a
nonbreaking space, including prose and expanded choice branches. Preserve it
through Unicode normalization; NFKD alone turns U+00A0 into a breakable space.
Check the serialized XML and rendered glyph rows for stranded dots (SBL Hebrew
extracts the printed dot as ∙). Stop day seven at its closing Kaddish cue before
the large Erev Rosh Hashanah heading on n99/n100. Source scope/proofreading files
record the detailed boundaries and unresolved independent Hebrew review.
