# Converting the Birnbaum siddur from its scan

The evidence is the page. Philip Birnbaum's *ha-Siddur ha-Shalem* (1949) is converted by
reading the scanned print, Hebrew recto and facing English verso, and writing the TEI
from what the page says. The transcriptions of this book that exist are used only as a
proofreading check on the reading, never as its source.

This supersedes the wikitext-driven approach on `feat/birnbaum-he-importer`. That branch
built the text from the Hebrew Wikisource transcription, which is not this book: it
renders Birnbaum's English rubrics into Hebrew of its own, adds Eretz Yisrael customs,
and corrects the text. Most of the importer it needed existed to undo that distance —
and it still wanted his rubrics entered by hand from the scan, because the transcription
does not contain them. Reading the scan first removes the distance instead of correcting
for it.

## What is on disk

The line is drawn at what a machine can remake. **Images stay out of every repository**: a
leaf is re-fetchable from the Archive, and the enlarged bands are cut from it by
`pages.py`, so 63MB of the working directory is worth nothing in git.

```
output/birnbaum_scan/pages/{printed}.jpg      the full-resolution leaf, untracked
output/birnbaum_scan/bands/{printed}_{i}.png  overlapping bands, enlarged, untracked
```

**The reading is committed**, because nothing regenerates it. In `sourcetexts`, under
`sources/birnbaum_siddur/scan_reading/`:

```
readings/{printed}.md         what the page was read to say
hebrew/{printed}.txt          the Hebrew lifted out of that reading
transcription/{printed}.txt   the Wikisource slice it was compared against
```

and in this repository, the measurement and the tooling:

```
specs/birnbaum_scan/accuracy.md    the transcription-distance measurement
specs/birnbaum_scan/verdicts/      which side each difference was decided for
specs/birnbaum_scan/settings_*.yaml the export settings the commands below name
opensiddur/importer/birnbaum_scan/ pages.py fetches and cuts; compare.py measures;
                                   build/ writes the TEI
```

`transcription/` duplicates 12K of a file already in `sourcetexts`. That is deliberate: the
slice boundaries are a judgement, and without them `accuracy.md` cannot be rechecked.

```bash
export OPENSIDDUR_CONTACT_EMAIL=... OPENSIDDUR_AGENT_MODEL=...
uv run python -m opensiddur.importer.birnbaum_scan.pages 81 82 83   # fetch and cut up
```

**The scan is 1541×2291 per leaf and that is not a derivative.** `ia/derivatives/
*_scandata.xml` states it and the live JPEG headers confirm it, so `_large` and the plain
`.jpg` are the same file and the 488 MB PDF would add nothing. At that size a qamats is a
few pixels tall, which is why `bands()` cuts the page up and enlarges it 3×: the bands are
what makes pointing legible. Bands overlap so a line falling on a seam is whole in one of
the two that share it.

## How far the transcription stands from the print

`opensiddur.importer.birnbaum_scan.compare` counts the differences between a reading and
a transcription in three buckets, comparing word skeletons first so that a different word
is never counted as a different vowel:

| bucket | what counts |
|---|---|
| whitespace | spacing, line and paragraph breaks, maqqef against space |
| consonants | the base-letter skeleton — a word added, dropped or spelled differently |
| vowels | pointing only, over an identical skeleton |

Which side the page supported is **not computable**. A difference starts `unresolved` and
is set to `print` or `reading` by someone going back to the image; the tally reports the
buckets split by verdict, because a raw count conflates the transcription departing from
the print with a misreading.

Measured on printed pages 81 and 83, 164 words: **no misreadings**. All thirteen
differences are the transcription departing from the print — its own Hebrew rubric where
Birnbaum sets English, a five-word Eretz Yisrael passage he does not print (its own
footnote says so), a segol its own footnote concedes he did not use, and four
qamats-qatan spellings of a glyph the print does not distinguish.

**This print does not distinguish qamats from qamats qatan.** They are one glyph. A
diplomatic transcription of it writes U+05B8 throughout; U+05C7 is an interpretation, and
belongs to whoever makes it.

## What the print does, that the encoding has to carry

Found by reading, and each one changes how a passage must be encoded:

**The asterisk is a substitution, not an addition.** An asterisk in the running text,
repeated before the rubric, marks the passage as substitutable: *"\*Between Rosh Hashanah
and Yom Kippur substitute:"*. The ordinary reading and the alternative are exclusive, so
each is written under its own conditional and the ordinary one is negated. Four occur in
this unit, and the fourth (p. 95) says *say* rather than *substitute* — his wording is per
position and is set as he printed it, never normalised.

**Two columns can mean two different things.** Birkat ha-Shanim's seasonal phrase (p. 87)
is an alternation: one column or the other, inside one sentence. Modim and Modim
d'Rabbanan (p. 91) are simultaneous, split by a printed vertical rule — the congregation
says one while the Reader says the other. The second is conditioned on the repetition and
the first on nothing.

**Column geometry inverts between the two sides and means nothing by itself.** The Hebrew
page sets the columns in Hebrew reading order and the English page mirrors their physical
placement so that reading order is preserved. Encode the season or the occasion, which the
headings state; never the position. *Crop and look before asserting which column is which*
— the arrangement reads backwards at a glance, and did.

**Order columns by reading order, which is rightmost-first on a Hebrew page.** That puts
רֹאשׁ הַחֹֽדֶשׁ first among Ya'aleh v'Yavo's three (p. 89) and the summer phrase first in
Birkat ha-Shanim (p. 87), where the right column is וְתֵן בְּרָכָה. The facing English page
confirms it independently, since mirroring the placement preserves the order: "Bestow a
blessing" is leftmost on p. 88 and so is read first there too.

**Where the columns are simultaneous rather than alternative, the conditional one goes
first.** Modim and Modim d'Rabbanan (p. 91) begin at the same vertical position, and the
instruction over the second says the congregation "responds **here**" — which points at the
moment Modim begins. Linearised with Modim first, "here" would land at the *end* of Modim,
which is not where the congregation starts. Nothing in a single column can express
simultaneity, so the order is chosen to keep the instruction's deixis true; that is the
only thing the choice can preserve.

**A bare day-name over a column is an instruction**, short for "say this on Rosh Hodesh".

**He states the diaspora rain rule as a civil date** — December 4th — and gives no Eretz
Yisrael date at all. He prints no summer insert in the Gevurot: מוריד הטל is nowhere.

**Al ha-Nissim is two complete passages**, Ḥanukkah then Purim, each under its own rubric
and its own parentheses. Not one passage with a variable middle.

**Three headings in the whole unit, all English**: SHEMONEH ESREH (p. 82), KEDUSHAH
(p. 84), ABRIDGED SHEMONEH ESREH (p. 97 — on a *Hebrew* page). Everything else that
structures these pages is a rubric, "Priestly blessing recited by Reader:" included.

**Parentheses are his.** An optional passage is printed in parentheses, and they belong to
the text.

**The two sides cite different pages for the same cross-reference.** Hallel is page 565 on
the Hebrew side and 566 on the English; each points at its own language. Verified at 3× on
both.

**A page turn falls mid-sentence** and is not a paragraph break. `tei:pb` is in
`model.milestoneLike` and valid inside `tei:p`.

**The speaker labels are Hebrew-side only**, in small roman capitals set inline. The
English page sets "Reader:" as its own centred italic line, and at the Kedushah responses
gives no label at all, translating the words instead.

**Birnbaum gets no `respStmt`**, in either project. A `respStmt` records who *digitised* a
text; he is the author of the one being digitised, and is recorded as a source. That the
English is his own translation is said in the English project's `tei:editionStmt` and in a
`tei:note` on `project_source_bibl` — beside the citation, where a reader looking for who
made the book will find it. Crediting him as `trl` instead would claim he did work he did
not do, and push the people who did read the scan out of view.

## The front matter

Twenty-five leaves precede printed page 1, and the book divides them by language exactly as
it divides its body. Read off the scan; the Wikisource transcription of these pages is
proofread and was used only as a check, which is how it turned up wrong on the dedicatee's
name — the print reads WERBELOWSKY, not Werblowsky.

| leaf | designation | holds | side |
|---|---|---|---|
| 1 | `[1]` | blank | — |
| 2 | `[2]` | the Hebrew title page | he |
| 3 | `[I]` | the English title page | en |
| 4 | `[II]` | copyright, rights statement, Hebrew typesetting imprint, printer | en |
| 5 | `[III]` | the dedication | en |
| 6 | `[IV]` | הַתֹּכֶן, the Hebrew table of contents | he |
| 7 | `[V]` | CONTENTS, the English table of contents | en |
| 8 | `[VI]` | blank | — |
| 9 | `[VII]` | ACKNOWLEDGMENTS | en |
| 10 | `[VIII]` | blank | — |
| 11–25 | `IX`–`XXIII` | INTRODUCTION, in three parts he numbers himself, with footnotes | en |

**The book numbers only leaves 11–25.** It prints `IX` on leaf 11 and `XXIII` on leaf 25,
which fixes leaf 3 as `I`; leaves 3–10 are therefore designated `[I]`–`[VIII]`, in brackets,
and leaves 1–2 precede the sequence and are numbered from the scan as `[1]` and `[2]`. The
brackets are the whole of the claim: this is a number the book implies and does not print.
`tei:pb/@ed` here is `1949` alone — the second token names a printing, and front matter is
printed once.

**Both tables of contents are deferred.** They index some 600 printed pages the projects do
not hold yet. Their leaves still carry a page break, so nothing renumbers when they are read.

**The reading is XML, not markdown.** `sourcetexts/.../scan_reading/front/` holds one
well-formed fragment per section, and `build/front.py` splices them in. For the body a
markdown reading and the TEI are two artifacts because the TEI is assembled from Python; here
the fragment *is* the reading, and a parallel prose copy of it would only drift.

**Birnbaum's introduction has to reach the Hebrew compile.** He wrote it in English and the
print has no Hebrew counterpart, so the English project realises it and the Hebrew index
transcludes it, issuing no `corresp` of its own — see `front:` in
[`SIDDUR_URN_SCHEME.md`](SIDDUR_URN_SCHEME.md). Two things had to change for that to work:

- `priority.transclusion` in every `settings_*.yaml` now names the English project after the
  Hebrew. The list is a filter rather than a preference, so a URN no listed project realises
  raised `No prioritized URNs found` instead of resolving to the one project that has it.
- `common.pb()` briefly read `pages.json` for the leaf a page falls on, which looked like
  removing a duplicate and was not: the prayer modules call it at import time, so no part of
  the importer could be imported without the sourcetexts submodule, and CI does not
  initialise one. The mapping is written out again, and a test checks it against
  `pages.json` wherever the submodule is present, so it cannot drift. **A unit test here
  tests the code, never the reading** -- the builders' tests stand synthetic fragments in
  place of `scan_reading/front/`.
- `reledmac.xslt` grouped front-matter prose under the *root* language. In a Hebrew-rooted
  project every line of the English introduction came out reversed. It now groups by the
  prose's own language, so each language gets its own numbered stream.

**The comparison of the old and new translations (p. XXI) is a `tei:list`, not two divisions.**
A `tei:div` may not be followed by a `tei:p`, and the comparison sits mid-section with
paragraphs after it; a labelled list is `model.inter` and sits among them. It is also the
better reading of the page — two labelled alternatives, not two divisions of the introduction.

**The dedication's three display lines are `tei:lg`/`tei:l`.** Written as one paragraph broken
by `tei:lb`, the trailing line break left an empty line box that the next heading was set into,
and ACKNOWLEDGMENTS printed on top of the dedicatee's name.

## The projects

| project | holds |
|---|---|
| `birnbaum_ashkenaz_he_1949` | the Hebrew of the 1949 print |
| `birnbaum_ashkenaz_en_1949` | Birnbaum's own English, from the facing pages |

Three tiers: `index.xml`, a unit file holding document order and no words of its own, and
one file per prayer holding the words, the conditionals and the `tei:pb`. Both projects
emit **identical** URNs under their own project ids, which is what aligns them; a URN
repeated inside one document would break the join silently, so none is.

Naming follows [`SIDDUR_URN_SCHEME.md`](SIDDUR_URN_SCHEME.md). Ya'aleh v'Yavo and Al ha-Nissim are top-level
because both are also said in Birkat HaMazon — nest only what lives in one place.

## Building and checking

```bash
W=opensiddur-projects/project
uv run python -m opensiddur.importer.util.validation "$W/birnbaum_ashkenaz_he_1949/amidah_avot.xml"
uv run python -m opensiddur.exporter.refdb --project-directory "$W"
uv run python -m opensiddur.exporter.validate_urn_references birnbaum_ashkenaz_he_1949 --project-directory "$W"
uv run python -m opensiddur.exporter.compiler -p birnbaum_ashkenaz_he_1949 \
    -f chol_shacharit_amidah.xml -s specs/birnbaum_scan/settings_undecided.yaml \
    -o output/amidah.xml --project-directory "$W"
uv run python -m opensiddur.exporter.pdf.pdf output/amidah.xml output/amidah.pdf \
    -s specs/birnbaum_scan/settings_undecided.yaml --project-directory "$W"
```

`refdb` must be re-run before `validate_urn_references`; a stale index reads as
unresolved references. Indexing the whole corpus takes several minutes.

**Compile for a day and a place, or the conditions are untested.** Reading the XML proves
nothing. `settings_undecided.yaml` declares the service and the recitation and no date, so
every day-dependent reading survives with its rubric; `settings_15jan_jerusalem.yaml`
names a day and a place, and nothing conditional should survive it.

## Known defects in the parallel PDF

Found by compiling this unit two-column; both are in the exporter, not in the TEI.

**Fixed here: an instruction set in a fixed-width box ran off the page.**
`\OSInstructionBlock` and `\OSInstructionLine` set the rubric in `\hbox to \linewidth`,
which cannot break, and `\linewidth` inside reledpar's parallel setting is the page rather
than the column. So every rubric wider than half the measure overhung the margin — invisible
in a single-column compile, where the measure is the whole page, and unmissable in a
parallel one. A `\parbox` of the same width does not help, for the same reason. Both macros
now set the rubric as ordinary text between two `\newline`, which is measured by whatever
column it lands in. That gives up the flush margin and keeps the words on the page.

**Fixed here: the labelled list was not set as a list at all.** The visible symptom was that
"THE NEW TRANSLATION" printed at the head of its first paragraph rather than on a line of its
own, but the label was only the part that showed. `reledmac.xslt` had no template for
`tei:label`, `tei:list` or `tei:item`, so all three fell to its pass-through fallback, which
descends without emitting a sentinel. Paragraph boundaries in that stylesheet are made by an
`f:para-break` that only `tei:p`/`tei:ab` and `tei:lg` emit, so nothing separated the label
from the paragraph after it — and, because the list and the item were equally unhandled, the
item's four paragraphs became four sibling `\pstart`s with no mark of where an item began or
ended. Birnbaum sets the passage as two labelled blocks; it came out as one continuous run of
prose. The reading and the encoding were right, as this said; what was missing was the whole
list, not the label's line break.

The label now takes a line of its own, out of the line numbering, styled by
`styles.list_label` (small caps by default); the item's paragraphs are indented on both
margins by `lists.item_indent` (`2em` by default), so the two alternatives read as two blocks.
It is placed the way a `tei:head` is — the same problem — but emits no running-head mark and
no PDF outline entry, because a list label names an alternative inside a section rather than
opening one. The indent applies in a single-column stream, which is where labelled lists are
used: the front matter is set full width, and under reledpar a whole column is one `\pstart`
with no paragraph head to hang the skip on.

**Open: a paragraph's overflow can be typeset in the facing column.** Where a Hebrew
paragraph is short and its English counterpart runs longer, the tail of the English lands
in the Hebrew column — "all kinds of its produce for the best." under Birkat ha-Shanim,
"thou hast always been our hope." under Modim. It is reledpar's column assignment, not the
alignment: the two sides pair correctly everywhere, and naming the divisions (which the
pairs now all are) does not change it. Three occurrences in eleven pages.

## What is done, and what is next

Done: printed pages 81–97, the weekday shacharit Amidah, both projects, 60 files, all
validating. Done: the front matter, scan leaves 1–25 — both title leaves, the dedication, the
acknowledgments and the introduction — 3 further files and a `tei:front` on each index.

Next, in the order the evidence suggests:

1. **Birnbaum's footnotes.** He runs two apparatuses: commentary keyed by Hebrew lemma,
   set across the opening so a note begun under a Hebrew page finishes under the facing
   English one; and numbered scripture citations keyed to superscripts in the English
   text. They are a standoff apparatus and belong in their own file. The introduction's own
   footnotes are not these: they are ordinary inline `tei:note`, already encoded.
2. **The two tables of contents**, once there is enough of the book for them to point at.
3. **Finish the accuracy measurement** for pages 85–97, which is cheap now and is the
   evidence for whether this scales.
4. **The surrounding units**, page by page.
