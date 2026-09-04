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

Page images are cached outside every repository, in `output/birnbaum_scan/`, so they
survive a worktree and are never committed:

```
output/birnbaum_scan/pages/{printed}.jpg      the full-resolution leaf
output/birnbaum_scan/bands/{printed}_{i}.png  overlapping bands, enlarged
output/birnbaum_scan/readings/{printed}.md    what the page was read to say
output/birnbaum_scan/accuracy.md              the transcription-distance measurement
```

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

**Birnbaum gets no `respStmt`.** A `respStmt` records who *digitised* a text; he is the
author, and is recorded as a source. In the English project he is also `trl`, because
the translation is his.

## The projects

| project | holds |
|---|---|
| `birnbaum_ashkenaz_he_1949` | the Hebrew of the 1949 print |
| `birnbaum_ashkenaz_en_1949` | Birnbaum's own English, from the facing pages |

Three tiers: `index.xml`, a unit file holding document order and no words of its own, and
one file per prayer holding the words, the conditionals and the `tei:pb`. Both projects
emit **identical** URNs under their own project ids, which is what aligns them; a URN
repeated inside one document would break the join silently, so none is.

Naming follows `SIDDUR_URN_SCHEME.md`. Ya'aleh v'Yavo and Al ha-Nissim are top-level
because both are also said in Birkat HaMazon — nest only what lives in one place.

## Building and checking

```bash
W=../../opensiddur-projects/feat_birnbaum-from-scan/project
uv run python -m opensiddur.importer.util.validation "$W/birnbaum_ashkenaz_he_1949/amidah_avot.xml"
uv run python -m opensiddur.exporter.refdb --project-directory "$W"
uv run python -m opensiddur.exporter.validate_urn_references birnbaum_ashkenaz_he_1949 --project-directory "$W"
uv run python -m opensiddur.exporter.compiler -p birnbaum_ashkenaz_he_1949 \
    -f chol_shacharit_amidah.xml -s output/birnbaum_scan/settings_undecided.yaml \
    -o output/amidah.xml --project-directory "$W"
uv run python -m opensiddur.exporter.pdf.pdf output/amidah.xml output/amidah.pdf \
    -s output/birnbaum_scan/settings_undecided.yaml --project-directory "$W"
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

**Open: a paragraph's overflow can be typeset in the facing column.** Where a Hebrew
paragraph is short and its English counterpart runs longer, the tail of the English lands
in the Hebrew column — "all kinds of its produce for the best." under Birkat ha-Shanim,
"thou hast always been our hope." under Modim. It is reledpar's column assignment, not the
alignment: the two sides pair correctly everywhere, and naming the divisions (which the
pairs now all are) does not change it. Three occurrences in eleven pages.

## What is done, and what is next

Done: printed pages 81–97, the weekday shacharit Amidah, both projects, 60 files, all
validating.

Next, in the order the evidence suggests:

1. **Birnbaum's footnotes.** He runs two apparatuses: commentary keyed by Hebrew lemma,
   set across the opening so a note begun under a Hebrew page finishes under the facing
   English one; and numbered scripture citations keyed to superscripts in the English
   text. They are a standoff apparatus and belong in their own file.
2. **Finish the accuracy measurement** for pages 85–97, which is cheap now and is the
   evidence for whether this scales.
3. **The surrounding units**, page by page.
