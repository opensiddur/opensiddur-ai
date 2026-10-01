# How far the Wikisource transcription stands from the 1949 print

Measured on the Hebrew pages read so far, by reading each page off the scan and then
diffing that reading against the Hebrew Wikisource text for the same page. For the
Amidah pages that text is one file,
`sourcetexts/.../source/text/אשכנז/דפי יסוד/תפילת העמידה.txt`. For page 1 it is not:
Wikisource assembles that page by transclusion from four foundation pages, so the
compared slice is stitched together and its boundaries are themselves a judgement — see
`scan_reading/readings/1.md`, "The transcription slice". Every difference was
adjudicated by going back to the page image.

`print` = the page said what was read off it, and the transcription departs from it.
`reading` = the transcription was right and the scan was misread.
`unresolved` = the scan cannot settle it.

## Pages read so far

| page | words | whitespace | consonants | vowels | misreadings |
|---|---:|---:|---:|---:|---:|
| 1 | 111 | 0 | 1 | 1 | 0 (1 caught before committing) |
| 3 | 94 | 0 | 0 | 4 | 0 (3 caught before committing) |
| 5 | 110 | 0 | 0 | 3 | 0 (3 caught before committing) |
| 7 | 162 | 0 | 0 | 9 | 0 (6 caught before committing) |
| 9 | 219 | 1 | 0 | 19 | 0 (3 caught before committing) |
| 11 | 148 | 0 | 1 | 7 | 0 (1 caught before committing) |
| 13 | 188 | 0 | 1 | 6 | 0 (none needed) |
| 15 | 142 | 0 | 2 | 4 | 0 (1 caught before committing) |
| 17 | 163 | 0 | 0 | 3 | 0 (none needed) |
| 19 | 203 | 0 | 0 | 9 | 0 (2 caught before committing) |
| 21 | 227 | 0 | 0 | 5 | 0 (3 caught before committing) |
| 23 | 193 | 0 | 0 | 8 | 0 (4 caught before committing) |
| 25 | 181 | 3 | 0 | 8 | 0 (1 caught before committing) |
| 27 | 176 | 0 | 0 | 13 | 0 (none needed) |
| 29 | 186 | 0 | 0 | 10 | 0 (none needed) |
| 31 | 206 | 0 | 0 | 8 | 0 (none needed) |
| 33 | 159 | 0 | 0 | 10 | 0 (none needed) |
| 35 | 163 | 1 | 0 | 5 | 0 (none needed) |
| 37 | 185 | 0 | 0 | 5 | 0 (none needed) |
| 39 | 167 | 0 | 0 | 15 | 0 (none needed) |
| 41 | 67 | 0 | 0 | 3 | 0 (none needed) |
| 43 | 84 | 0 | 0 | 4 | 0 (none needed) |
| 45 | 64 | 0 | 0 | 2 | 0 (none needed) |
| 47 | 92 | 0 | 1 | 9 | 0 (none needed) |
| 81 | 39 | 0 | 0 | 0 | 0 |
| 83 | 125 | 0 | 6 | 6 | 0 (1 caught **after** committing) |
| **total** | **3854** | **5** | **12** | **176** | **0** |

**No misreading survives in 3854 words.** But the second number in that column has grown
faster than the first, and it is now the one that matters: **twenty-nine readings have been
corrected, nearly all of them points, and every one was caught by the diff rather than
by looking harder.**

That revises what the first three pages concluded. Reading this scan in enlarged bands is
reliable *for consonants* — the skeleton has not been wrong once in 3854 words. It is not
reliable for pointing. At 3x a semicolon and a comma are one mark, a patach and a qamats
differ by a tail a pixel or two long, and a dagesh in a wide letter is a dot that the
neighbouring letter can lend it. Page 5 alone gave up a shva read as a patach, a patach
read as a qamats, and a defective spelling read where the print is plene.

So the transcription is not a formality to be run after the reading is finished. **It is
the instrument that finds the pointing errors**, and where it disagrees the presumption
should be that it is worth a 12x crop, not that the reading stands. Where it flags a
variant in a `{{נוסח}}` template it has been right every time so far: both of page 5's
tefillin readings were templates naming Birnbaum's own spelling, and both times the
reading was wrong and the template was right.

**This bears on pages 81-97, which were read the same way before any of it was known.**
Page 83's seven vowel differences were all adjudicated for the print, and page 81's
thirty-nine words produced none at all. Those verdicts were reached at band magnification.
They should be re-checked at 12x before the Amidah is treated as settled; that re-check is
not part of this pass and has not been done.

But page 1 is the first page on which the check earned its keep in the other direction.
The first draft of the reading had `יָחֹֽלוּ` where the transcription had `יָחֻֽלוּ`; going
back to the image settled it **for the transcription** — three dots set diagonally under
the ḥet, and no dot above it. The reading was corrected before it was committed, so the
difference is not in the table above; recording it here is the only way it is not simply
lost. Four catches in 369 words is the honest error rate of this method, and it is not
zero. It also shows the check working as designed: the transcription is not a source,
but it is a competent second reader.

## Page 83 carried a misreading through to a merged branch

The Amidah pages were read before any of the above was known, and this file recorded
zero misreadings for them. That is no longer true for page 83, whose dash before the
Kedushah response was read as an em dash where the print sets an **en dash**. It has been
corrected and the tally above now says so.

Three things make it worth more than the one character it changes.

**It confirms the re-check rather than merely suggesting it.** The warning below this
section said pages 81-97 should be re-examined because they were read at band
magnification. One of them has now been shown to carry an error, so the re-check is owed
and not optional.

**It was not found by a crop.** It was settled by someone who knew what the page should
say. The reading had recorded a difference and left it `unresolved`, which meant the
transcription had already flagged the right character and the reading declined to take
its side. That is the same failure as page 5's sin dot: reaching for "the scan cannot
settle it" when the answer was available.

**A correction after committing has nowhere good to live.** Once the reading is fixed the
difference disappears, so the `reading` verdict that should record it matches nothing --
`compare` prints `warning: no difference matches the verdict`, which is the tool behaving
correctly and still leaving the catch with no home but this paragraph. Nine of the other
ten corrections are in the same position. Until a verdict file can say *this was corrected
and here is what it was*, the error rate of this method is prose, and prose is not
checkable.

## Open: whether the meditation's לְהַנִֽיחַ carries a dagesh

**Contested, and the text currently follows the editor.** Printed page 7 sets the word twice
— once in the tefillin meditation and once in the blessing. The blessing is recorded with a
dagesh in the nun, the meditation without one, and this file previously treated that
difference as a finding.

A blind second reader put on the meditation instance reported a dagesh in **both**, and
called them the same word. Measuring the coordinates it gave: an isolated ink blob sits
inside the letter in each instance, at min gray 76 and 57 against blank paper at 252 and a
known ink stroke at 79, alike in size and shape and clearly separate from the strokes
around them.

So the evidence on the scan favours a dagesh in both, and the reading as it stands does not
have one in the meditation. It has been left as the editor answered rather than changed on
a machine's say-so; if the dagesh is right, the claim that the two occurrences differ comes
out of `readings/7.md` and out of this file with it.

## How a meteg verdict is reached

**Every meteg in `verdicts/` was decided by looking at the page image**, not by convention,
not by grammar, and not by which witness tends to carry more of them. That is the editor's
stated practice and it is recorded here because it is provenance: a reader who wants to
know what a `print` verdict on a meteg rests on should know it rests on the scan.

It also explains a pattern that would otherwise look like noise. On printed 21 the four
disputed metegs fell in **both** directions -- two the reading had and the print did not,
two the transcription had and the reading had missed. A rule of thumb, applied either way,
would have got half of them wrong. Only reading each one gives that distribution.

So metegs are not a class that can be settled in bulk, and the queue should keep bringing
them one at a time.

## The slice is derived, and was not

Every `transcription/{page}.txt` up to this point was assembled by hand: reading the
printed page's wikitext, deciding which foundation spans it sets, and pasting them
together. `transcription.page_slice` now does it from the page file, and
`python -m opensiddur.importer.birnbaum_scan.transcription <pages>` writes the files.

Re-slicing the twelve pages already measured changed five of them, and the changes say
what a hand-made slice gets wrong:

**Printed page 21 lost its last line — in both witnesses, the same way.** The page ends
`רִבּוֹנוֹ שֶׁל עוֹלָם, יְהִי רָצוֹן מִלְּפָנֶֽיךָ, יְיָ אֱלֹהֵֽינוּ וֵאלֹהֵי`, nine words
that were absent from the reading *and* from the slice. A comparison can only report a
disagreement between its two sides; where both sides are missing the same thing it reports
nothing, and every check downstream stays green. This is the failure mode
`SKILL.md` names as the one the reverse check exists for, caught here by a different
route: the machine assembled the slice from the page's own transclusions and the reading
then had nine words too few.

**Nested spans truncate silently.** `אתה הוא עד שלא נברא הכל` wraps `... א` and `... ב`
with the reader's rubric between them, and `section()` closed on the first
`<קטע סוף=` of any name — returning the first half. The diagnostic signature is the one
printed page 19 established: a word-count gap plus a wall of consonantal differences.

**The join between two spans is part of the reading.** Printed page 1 sets five spans as
one paragraph with `. ` between them. A slicer that concatenates spans manufactures four
paragraph breaks and loses four sentence-final periods, and `compare` then reports them as
whitespace and vowel differences that are the slicer's own doing. Page 1 fell from twelve
differences to two, page 11 from twenty-one to eight, page 13 from fourteen to seven. Those
were never disagreements with the edition.

**Both sides must hold the same kind of thing.** The edition's rubric spans (`הוראה`) are
its editors' Hebrew standing where Birnbaum sets English. Its heading spans (`כותרת`) and
citation spans (`מקור`) are a different case: he prints both in the Hebrew column — the
Akedah stands under `בראשית כב, א-יט` and the korbanot passages under theirs — but a
heading and a citation are read into `readings/` and never into `hebrew/`. All three are
left out by name, on both sides.

**Two spans a page transcludes no longer exist under that name**, because the page files
and the foundation pages were snapshotted at different revisions — one rename and one
typo fixed on one side only. They are recorded in `RENAMED_SPANS` rather than guessed at,
and an unrecognised missing span refuses to write the file at all.

One thing the hand slices carried that the machine does not: printed page 15's three
`אָמֵן.` after the Priestly Blessing. The current snapshot's span has no such word, so
the file now matches what the edition sets. The reading never had them and the print does
not carry them, so the adjudication is unchanged; what changed is that the slice can be
regenerated and checked.

## The qamats-qatan rule is applied by a tool now, and it found two mistakes

Qamats qatan is the only class this comparison settles without going back to the image: the
print has one qamats glyph, the edition writes U+05C7 where its editors read the vowel as
qatan, and that is their interpretation rather than something on the page. Applying it is
therefore mechanical -- and it was being applied by hand, page after page, which is copying.

`compare --settle-qamats-qatan` records the rule's verdicts and **refuses every difference
the rule does not wholly cover**: the two words must be identical once U+05C7 and U+05B8 are
folded together. Run over the twenty pages already adjudicated it accepted 89 differences and
declined two that had been filed under the rule:

| page | the print | the edition |
|---|---|---|
| 15 | `רִבּוֹן כָּל הַמַּעֲשִׂים` | `רִבּוֹן כׇל` |
| 17 | `לִי כָּל צָרְכִּי` | `לִי כׇל` |

In both the edition drops the **dagesh** as well as reading the vowel as qatan. Two things
differ, the rule covers neither, and the readings said "settled by rule" about a difference
it does not touch. Both have now been checked at 25× and both verdicts stand -- the print
carries the dagesh -- so nothing in the tally changes. What changes is that the reason is
true.

**And `כל` turns out not to be a class at all.** The edition is inconsistent about it within
eight words on page 15, and so is the print across pages: printed 25 sets
`וְיֵדְעוּ כָל בָּאֵי עוֹלָם` with no dagesh, and that correction was itself found by going
to the image. A word that looks settleable in bulk is worth one page of checking before it
is treated that way.

## The whole Hebrew side of Birchot ha-Shaḥar is now read

Printed 3 through 47, twenty-three pages, **3,854 words counting the Amidah's two**. No
misreading survives, and the last nine pages produced nothing that had to be put to a
person: every difference was either the qamats-qatan rule or settled on the image.

That is a change in the shape of the work, and it has a cause. The korbanot and Eizehu
Mekoman are Mishnah and Talmud, texts both witnesses were copying rather than deciding
about; printed 37 and 39 between them produced twenty differences of which every one was
the rule. The pages that generate questions are the ones where the edition's editors had
something to choose -- and they cluster in the blessings and the prayers, not the rabbinic
material.

Three defects in the tooling were found in the course of it, each by the reading rather
than by a test:

- The slice was built by hand. Rebuilt from the page file it found printed 21 nine words
  short **in both witnesses at once**.
- The qamats-qatan rule was applied by hand. Applied by the tool it found two pages where
  the edition had also dropped a dagesh.
- The `{{נוסח}}` resolver closed on the first `}}`. The Kaddish is the one place a template
  holds a template, so it broke on the last page of the section and nowhere else.

The common shape: **the step being done by hand was the step that was wrong**, and each
was found by mechanising it rather than by checking it again.

## Corrections are data now, not prose

`corrections.jsonl` records every reading corrected so far -- what it was, what the print
carries, what settled it, and whether it was caught before or after committing. Twenty-nine
entries.

It exists because a correction has nowhere else to live. Once a reading is fixed the
difference disappears from the comparison, so the `reading` verdict that recorded it
matches nothing and `compare` rightly warns about it. Verdict files describe live
differences; corrections describe ones that are gone. Keeping them in the same file made
the second kind either noisy or invisible.

The counts in the table above are therefore checkable rather than asserted: twenty-eight of
the twenty-nine were caught before committing, and the twenty-ninth is page 83's.

## Page 7: the queue's first run

Page 7's six open questions were the first put through `OPEN_QUESTIONS.md` and answered by
the editor rather than by another crop. Five behaved as expected. **The sixth did not, and
it is the useful one.**

Question 7.1 asked whether the meditation's לְהָנִֽיחַ carried a meteg, the reading and the
transcription differing by that alone. The answer was neither: the print sets a **pataḥ**
where both of them set a qamats. Two independent witnesses agreed with each other and were
both wrong, and the only reason it came out is that the queue asks what the print carries
rather than which of two candidates to pick.

That is an argument for the queue's refusal to guess. An answer that matches neither form
is an error, not a third option to be coerced into one of the two -- and here the error
was the right outcome, because it meant the reading had to be fixed before the verdict
could be recorded at all.

Note also that the page's two occurrences of the word remain genuinely different --
לְהַנִֽיחַ in the meditation, לְהַנִּֽיחַ in the blessing -- which is now confirmed by
someone who knows the text rather than inferred from a crop.

**The correction reached the reading and not the TEI.** `hebrew/7.txt` was fixed,
`corrections.jsonl` recorded it, and `he_tefillin.py` went on emitting the pre-correction
`לְהָנִיחַ` for months. Nothing could see it: the reading and the transcription now agree,
so `compare` reports nothing, and the schema, the registry and the reference database have
no opinion about which vowel a word carries. It was found by `reverse`, which asks the
question none of them ask -- whether the authored text *is* the reading.

Page 7's two catches were `זְרוֹעַ` for **זְרוֹעוֹ** and, in the blessing, `לְהָנִֽיחַ`
for **לְהַנִּֽיחַ** — the same word page 5 had to correct, so the spelling is his and
consistent. The page's two occurrences are genuinely different: the blessing sets
לְהַנִּֽיחַ and the meditation לְהַנִֽיחַ, pataḥ in both and dagesh only in the blessing.

**Six differences are recorded with no verdict, and that is the honest state rather than a
gap.** All six are meteg, a shva against a ḥataf-pataḥ, a qamats against a pataḥ, or a
comma — the exact class this reading has repeatedly got wrong — and none was settled on the
image in this pass. Two ways of clearing them were available and both are wrong: writing
`print` on the strength of the first reading is what the corrections above disprove, and
writing the transcription's side would make a check into a source. They stay open until
someone crops them at 12x.

The `unresolved` column therefore carries exactly one meaning at present — **not yet
done** — and page 7's six entries are all of it.

It briefly carried a second. Page 5's שֶׂ/שׁ was recorded as undecidable, on the ground
that the dot could not be placed at any magnification this scan supports. That was a
statement about the scan when it should have been a question about the word: עָשָׂה takes
a sin, so the print's reading was never in doubt and the transcription's shin is its own
error. It is now `print`. **Worth keeping as a caution: "the image cannot settle it" is
easy to reach for when what is actually missing is knowledge of the text, and the two
failure modes look identical from inside the crop.**

## Page 3: four differences, and three catches going the other way

Page 3's four surviving differences are all the transcription interpreting rather than
reading: two are qamats qatan written U+05C7 where this print has the one qamats glyph and
nothing else, and two are a dagesh and a segol the print carries and the transcription
drops. Verified at 9-20x.

**The three caught before committing are the more useful number.** The first draft of this
reading had a comma twice where the print sets a semicolon, and a dagesh in the mem of
מְאֹד that is not there. All three were settled *for the transcription* by going back to
the image at 12-18x. Recording them here is the only way they are not simply lost, and
they raise the honest error rate of this method to four catches in 369 words.

The two semicolons are worth naming as a class. Birnbaum uses both commas and semicolons,
sometimes in one line, and at 3x they are one mark; the semicolon's upper dot merges with
the comma's body. **A comma read off a band at 3x is not evidence.** Where the punctuation
carries a sense break, crop it.

### The transcription's variant templates are evidence, not markup

The Hebrew Wikisource foundation text marks the places its editors knew the print differs
from what they set, in a `{{נוסח}}` template that names the editions. Stripping those
templates -- the obvious thing to do with wiki markup -- throws away exactly what the
comparison is for, and it silently manufactures differences: both of page 3's apparent
dropped words were a stripped template, and both would have been recorded as the
transcription failing where in fact it was flagging a variant *and naming Birnbaum's side
of it*.

`opensiddur/importer/birnbaum_scan/transcription.py` resolves them. Four conventions are
in use and one inverts -- `{{נוסח|X|=בירנבוים|אחרים=Y}}` makes **X** the reading, so a
rule that simply prefers a `בירנבוים=` parameter takes the variant on every one of them.
One value is a sentence about how he sets two Torah portions rather than a word to
substitute, so a value that is not a short run of pointed Hebrew is kept out of the text
and reported.

## Page 1: three differences, all of them the transcription

10. **`נְצֹר` against `נְצוֹר`** and 11. **`וְגוֹאֲלִי` against `וְגֹאֲלִי`** — plene against
    defective spelling, in opposite directions within one sentence. Both verified at 7x:
    the print sets a holam point above the tsade in the first and a full vav after the
    gimel in the second. Consonantal by the tooling's reckoning, because a vav is a
    letter; they are not a different *text*.
12. **`אֱלֹהֵֽינוּ` against `אֱלֹהֵינוּ`** in the Shema verse — the print carries the meteg,
    and sets the same word the same way in the two blessings higher up the page, which
    is what makes the comparison decisive rather than a judgement about one glyph.

Page 1 also confirms the pattern page 83 disclosed: the transcription supplies Hebrew
rubrics of its own where Birnbaum sets English ones. On page 83 that produced a
consonantal difference; here the rubrics are carried in הוראה templates outside the
transcluded segments, so they never reach the slice at all. Same departure, different
mechanism — and on this page it is invisible to the count.

## Page 83: six consonantal differences, all of them substantive

Consonantal differences are where the transcription is a **different text**, and both
on this page are exactly the kind the conversion has to route away from Birnbaum's
project:

1. **`בחורף:`** — the transcribers' own Hebrew rubric, standing where Birnbaum sets the
   English *"Between Sukkoth and Pesaḥ add:"*. Their rubric, not his.
2. **`בקיץ בארץ ישראל: מוֹרִיד הַטַּל,`** (5 words) — an Eretz Yisrael passage Birnbaum does
   not print at all. The transcription's *own footnote* says so: *"אין אמירת 'מוֹרִיד הַטַּל'
   במנהג אשכנז הוותיק, והיא לא נאמרת בחו"ל"*. Confirmed against the scan: page 83 sets
   the winter insert alone, in parentheses, under one rubric, and no summer insert
   anywhere.

## Page 83: seven vowel differences

Two are genuine disagreements about what is printed, and the scan settles both against
the transcription:

3. **`הַגָּֽשֶׁם` (qamats), not `הַגֶּֽשֶׁם` (segol).** Verified at 4x. The transcription prints
   segol in its running text — and its own footnote concedes *"וכך אצל בירנבוים"* for the
   qamats. So the transcription knows it departs from him and does it anyway.
4. **`אַב הָרַחֲמִים` (patach), not `אָב`.** Verified at 4x: the alef carries a flat stroke
   only, against the unmistakable qamats on the ה of הָרַחֲמִים two letters later.

Four are the same phenomenon, and are not really vowel differences at all:

5-8. **`זָכְרֵֽנוּ`, `וְכָתְבֵֽנוּ`, `כָל`, `קָדְשְׁךָ`** — the transcription writes qamats qatan
   (U+05C7) where the print shows a plain qamats glyph (U+05B8). **The two are the same
   glyph**, so the scan cannot show which was meant; the qatan is the transcribers'
   phonological interpretation, not something Birnbaum printed. Counted as `print`
   because the reading did not misread anything, but the honest description is that the
   print does not distinguish them. *** A decision the conversion has to make once and
   apply everywhere: a diplomatic transcription of this print writes U+05B8. ***

9. **`יֹאמֵֽרוּ—` vs `–`** — em-dash against en-dash. Left `unresolved`; dash width at this
   resolution is not worth asserting.

## Still to measure

The English pages are not part of the table above, and cannot be: the tooling compares
pointed Hebrew, and there is no *independent* English witness to this print — en.wikisource
transcribes the same scan, so agreement between them is not corroboration.

Page 2 was nevertheless read and then compared by hand, and the exercise was worth it.
185 words, one difference: the print sets `falsehood.` where the transcription has
`falsehood,`. Verified at 7x — a full stop, and the `Open` that follows is capitalised —
and the facing Hebrew agrees, closing מִרְמָה with a full stop where the longer page-95
meditation has a comma because the sentence runs on there. The transcription had
punctuated the abridged text as though it were the long one.

Two things about that are worth keeping. It is a real error in a page marked proofread at
quality 4, which is the same lesson page 83 taught on the Hebrew side. And it would have
been invisible to any method that took the transcription as its starting point: the first
draft of this conversion derived the English mechanically from `en/text/027.txt` and
inherited the comma silently. Reading the page is what found it.

Pages 85-97. The method and the tooling are proved; what remains is the arithmetic. The
Hebrew Wikisource sections for those pages are named in the unit file's own page markers
(`<קטע התחלה=עמוד 85/>` and the rest), so extracting the comparison text is mechanical.

## What this means for the approach

- The scan is a sufficient source for pointed Hebrew at this resolution. The reading
  does not need the transcription to be accurate.
- The transcription is *not* a witness to this print, exactly as the conversion
  procedure warned: on one page it silently adds a passage, rewrites a rubric into
  Hebrew, and prints a vowel its own footnote says Birnbaum did not use.
- Using it as a proofreading check, and never as a source, is the right call. Across
  three pages it disclosed four things wrong with itself, and caught one thing wrong
  with the reading — which is precisely the division of labour intended for it.

## Printed 49 and 51: the weekday opening through Barukh sheamar

Checked directly against IA leaves n73 and n75, and against the resolved Wikisource
spans afterwards. The reading of 51 ends at Barukh sheamar, before Hodu.

No consonantal differences. Seven differences are the transcription’s qamats-qatan
interpretation of the print’s undifferentiated qamats. On 51 it also omits the stress
mark in the first `מֶֽלֶךְ` of the blessing and replaces the maqqef in `עֲדֵי־עַד`
with a space; both marks are visible in the enlarged scan.


### Printed 49

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 5 | 5 | 0 | 0 |

149 words read.


### Printed 51

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 1 | 1 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 3 | 3 | 0 | 0 |

120 words read.

## The apparatus's Hebrew, read against the print

The footnotes were extracted from the English Wikisource transcription, and their **Hebrew**
was never read off the page. That is the one place this conversion took a transcription as a
source rather than as a check, and it cost two errors, both invisible from inside the
transcription because both read as ordinary Hebrew:

| printed | transcription | print | |
|---|---|---|---|
| 48 | `על כל דברי שירות ותשבחות` | `על כל דברי שירות ותשבחות דוד` | a word dropped |
| 84 | `אתה גבור... מחיה המתים` | `אתה גבור... מחיה מתים` | an article added |

Both are in `corrections.jsonl` and in `extract_notes.TEXT_CORRECTIONS`, so a regeneration
keeps them.

**Openings read so far:** printed 4, 6, 18, 20, 24, 26, 48, 82, 84, 92 — ten of the
twenty-four that carry Hebrew in their notes. Two errors in ten openings is not a rate that
justifies assuming the rest are clean.

**Still owed:** the other fourteen — printed 2, 8, 12, 16, 22, 28, 34, 42, 46, 86, 88, 90,
94, 96, and the odd-numbered feet where a note begins before running across its opening. The
method is settled and cheap: crop the foot of the page image, and compare every Hebrew run in
that page's notes against it. `check_pdf_hebrew_direction.py` does not cover this — it asks
whether a run is set the right way round, not whether it is the right words.

## Hodu through Yehi khevod (printed 51–58)

Read from the images first, then compared with resolved Wikisource slices. Ashrei is excluded.

The review corrected full/defective spellings, punctuation and stress marks in the first reading. Notably, the print and the comparison both set `קִרְאוֹ` (holam) at the start of Hodu; it is preserved, not silently corrected to the familiar shuruq. The remaining differences are supported by the enlarged scan: qamats/qamats-qatan, punctuation, meteg and maqqef, plus the Unicode holam-haser distinction on vav. Psalm 20:10 has a meteg in `הַמֶּֽלֶךְ` on 57 but not on 55; both occurrences retain their printed pointing.


### hodu

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 15 | 15 | 0 | 0 |

229 words read.


### romemu

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

18 words read.


### vehu_rahum

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 1 | 1 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 5 | 5 | 0 | 0 |

89 words read.


### hoshia_et_amekha

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

71 words read.


### mizmor_letodah

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

43 words read.


### yehi_khevod

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 5 | 5 | 0 | 0 |

137 words read.

## Ashrei through Half Kaddish (printed 57–70, IA n81–n94)

The Hebrew and English were read from the images before the Hebrew Wikisource comparison. Enlarged bands resolved spelling, stress marks and punctuation. The comparison corrected full/defective spellings in Psalms 145–147 and Nehemiah 9, among other first-pass pointing errors. The retained differences include the repeated closing verses (Psalm 150:6 and Exodus 15:18), qamats versus qamats qatan, punctuation, and the missing sin dot in the transcription’s Psalm 145:9. The first Exodus 15:18 has defective לעֹלם; the repetition has plene לעולם. Psalm 150:6 is printed twice in Hebrew and only once in English. The existing shared Kaddish was separately checked against printed 69–70; its conditional replaces the literal parentheses.


### ashrei_prefix

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 0 | 0 | 0 | 0 |

14 words read.


### psalm_145

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 19 | 19 | 0 | 0 |

152 words read.


### ashrei_suffix

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

7 words read.


### psalm_146

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

83 words read.


### psalm_147

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

139 words read.


### psalm_148

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 11 | 11 | 0 | 0 |

109 words read.


### psalm_149

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 2 | 2 | 0 | 0 |

61 words read.


### psalm_150

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 5 | 5 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

40 words read.


### barukh_adonai

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 1 | 1 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 2 | 2 | 0 | 0 |

30 words read.


### vayevarekh_david

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

56 words read.


### atah_hu

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 6 | 6 | 0 | 0 |

111 words read.


### vayosha

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 0 | 0 | 0 | 0 |

33 words read.


### az_yashir

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 4 | 4 | 0 | 0 |
| vowels | 2 | 2 | 0 | 0 |

183 words read.


### ki_ladonai

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 1 | 1 | 0 | 0 |

29 words read.


### yishtabach

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 0 | 0 | 0 | 0 |

53 words read.

## Shema and its blessings (printed 71–82, IA n95–n106)

The first reading was entered from the scans before consulting Wikisource. Enlarged bands settled differences in spelling, dagesh, meteg and punctuation. Retained differences include defective זמרות, plene לעולם at the closing Exodus quotation, and the absence of ישראל after תהילות לאל עליון. Qamats uses U+05B8, and holam on consonantal vav uses U+05B9, following the encoding of preceding installments. Logical shin dots and holam are both encoded even when the print combines their glyphs. Verse/paragraph whitespace and dash length also differ from the comparison transcription. The two Kedushah responses were checked directly against the images; this comparison omits them because their transcription is shared with the Amidah.


### barekhu

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 3 | 3 | 0 | 0 |

55 words read.


### yotzer_or

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 1 | 1 | 0 | 0 |
| vowels | 6 | 6 | 0 | 0 |

256 words read.


### ahavah_rabbah

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 0 | 0 | 0 | 0 |
| vowels | 6 | 6 | 0 | 0 |

103 words read.


### shema

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 1 | 1 | 0 | 0 |
| consonants | 1 | 1 | 0 | 0 |
| vowels | 15 | 15 | 0 | 0 |

248 words read.


### emet_veyatziv

| bucket | total | print | reading | unresolved |
|---|---:|---:|---:|---:|
| whitespace | 0 | 0 | 0 | 0 |
| consonants | 2 | 2 | 0 | 0 |
| vowels | 2 | 2 | 0 | 0 |

277 words read.

## Sabbath and festival Arvit, printed 257–284 (IA n281–n308)

The scan has been read through Adon Olam, including its last four lines at the top of
283/284. The home service below it is outside this installment. The source reading
`scan_reading/readings/shabbat_arvit.md` records the order, rubrics, shared passages,
new text, commentary and source footnotes.

The shared weekday Arvit readings retain their established text and gain repeat-printing
provenance. The new Sabbath Hashkivenu ending, Atah Kidashta, Me‘ein Sheva and synagogue
Kiddush have their own readings. Me‘ein Sheva's English closing blessing differs from
the Amidah's (“deliverance”, “in truth”, “who hallow thy name”), and the thanksgiving
seal on 272 says “O God” where the earlier weekday printing says “O Lord”. Both variants
are retained locally. Page 262 also prints Jeremiah 31:11 rather than 196's 31:10;
its printed reference is retained at the new occurrence.

Comparison with the local Wikisource snapshot followed the direct scan reading.
The enlarged 263 scan confirms segol in בַּכֶּֽסֶה, the form היא in Veshamru, and
defective לְעֹלָם. The enlarged 273 scan confirms וְגוֹאֲלִי, which agrees with the
already encoded shared meditation. The English page does not translate סברי מרנן
ורבותי; its explanatory footnote is retained without supplying new liturgical text.

## Friday-night home prayers and hymns, printed 283–298 (IA n307–n322)

All sixteen images were read, starting below Adon Olam at Shalom Aleichem and ending
with Tzur Mishelo and its notes. `scan_reading/readings/leil_shabbat.md` records
both languages, rubrics, shared readings, commentary, and encoding decisions.
Enlarged crops were checked for the meditation, zemirot, and the Hebrew stanza
quoted in the Kol Mekadesh note. The local Wikisource snapshot was compared only
after the direct reading; its editorial additions are not imported.

Eshet Ḥayil has 22 biblical verse milestones. Hymn stanzas and refrains have separate
milestones, retaining the printed abbreviated English refrains. The additional
Kol Mekadesh stanza stays in the commentary. Vaykhullu and the Kiddush blessings
reuse existing texts with repeat-printing provenance. Ribbon kol ha‘olamim is
addressed separately from the morning prayer with the same opening words.
The Friday-night home section and its four-hymn zemirot wrapper have their own URNs
and hierarchical bookmarks, separate from synagogue Arvit.

Yah Ribbon uses `xml:lang="arc-Hebr"`. The renderer now honors explicit Hebrew-script
language tags for numbered streams; a synthetic regression test covers Aramaic,
Hebrew, regional Hebrew, and Latin-script Aramaic. Kiddush transcludes the three
Genesis verses individually to avoid inheriting the synagogue occurrence’s separate
source note alongside the combined Genesis 1:31; 2:1–3 note printed here.

## Sabbath and festival Pesukei Dezimrah, printed 299–336 (IA n323–n360)

All 38 images were read directly, through Half Kaddish and before Barekhu. The
paired readings, page turns, Reader cues, twelve new notes, six repeated source
citations, and collation decisions are recorded in
`scan_reading/readings/shabbat_pesukei.md`. The local Wikisource snapshot was
compared after the scan reading. Enlargements confirm the full spellings in
Psalms 19:15, 34:23, 135:2 and 135:21, אותת in 135:9, and מֵייָ in 33:8.
The scan's English “the the Lord” in Psalm 135:19 is retained.

Seven new complete chapters (19, 34, 90, 91, 135, 136, 33) add 140 verse
milestones per language. Psalms 92–93 and the weekday common material are reused
with repeat-printing provenance. Earlier quotations of verses from the new
chapters retain their own wording, local milestones, and biblical sources. The
Hebrew-only repetition of Psalm 91:16 is outside the chapter correspondence.
Psalm 136's refrain belongs within each verse.

The addressable Sabbath/festival Shacharit service includes the shared preliminary
morning service, Psalm 30 and Mourners' Kaddish, then its Pesukei Dezimrah child
from Hareni Mezamen through Half Kaddish. The Reader's festival entry at Ha'el
Betaatzumot and Sabbath entry at Shochen Ad remain performance instructions inside
the Nishmat section. Both Kaddishes have minyan gates in their callers. The
service declares Shacharit without forcing a calendar date.

Both generated projects pass schema validation and reference resolution. The full
corpus registry check has no errors or warnings. All 228 Birnbaum scan importer
tests pass; a corpus audit also checks the 140 verses, migrated quotation addresses,
service order, repeated verse, minyan gates, Reader cues, and all twelve new notes.

The 37-page section proof and 352-page full parallel edition were rendered and
visually checked at Nishmat, the two Reader entry cues, Psalm 136, and Half Kaddish.
The full-book outline places the shared preliminary service and opening under
Sabbath/festival Shacharit, with the psalms, Nishmat and Half Kaddish beneath its
Pesukei Dezimrah child. Artifacts: `output/birnbaum_shabbat_pesukei/parallel.pdf`
and the refreshed `output/birnbaum_parallel.pdf`.

## Sabbath and festival Shema blessings, printed 335–350 (IA n359–n374)

All sixteen images were read directly, beginning at Barekhu after Half Kaddish
and ending after the redemption blessing and festival-Amidah page reference.
The Amidah heading, instructions and text are excluded. Paired readings,
shared passages, rubrics, the three new notes and six repeated printed notes
are recorded in `scan_reading/readings/shabbat_shema.md`.

Yotzer Or has mutually exclusive festival-weekday and Sabbath openings. A
festival falling on Sabbath uses the Sabbath version; unknown calendar settings
retain both instructions. El Adon has six stanza milestones. La’el Asher
Shavat’s Psalm 92 quotation has biblical sources, preserving the existing
complete chapter as the canonical address. The new group extends the existing
addressable Sabbath/festival Shacharit service after Pesukei Dezimrah.

Ha-me’ir and Ahavah Rabbah preserve their locally different English wording.
Their matching Hebrew is reused from the established readings, with local
correspondences and source attributes; the remaining shared passages are
transcluded with repeat-printing provenance. This keeps the English variants
aligned with the matching Hebrew. The festival El Barukh transcludes an inner
text range so its different printed note replaces the weekday occurrence’s
commentary. Other commentary on shared canonical URNs follows those passages
as in the existing encoding; the source record distinguishes it from notes
actually repeated in this printing.

The local Wikisource snapshot was compared after the direct reading. Enlarged
crops confirm dagesh in הַמְּשֻׁבָּח, וְהַמְּפֹאָר and לְּךָ, sheva in
כְּעֶרְכְּךָ, full סוֹבְבִים אוֹתוֹ, qamats in לָאֵל מֶלֶךְ and יִתְקַדָּשׁ,
and נוגה in the commentary. The printed כַּייָ and לַייָ are retained without
an additional sheva under the first yod.

All 35 changed/new XML documents validate. Both projects resolve all references;
the full-corpus registry check has zero errors or warnings. All 231 importer
tests pass. A compiled-corpus audit checks both languages, stanza boundaries,
complete new commentary, shared continuation once, service order, exclusion
of Half Kaddish and Amidah, and alignment of the local translation variants.
Sabbath, festival weekday, festival Sabbath, private and unknown-calendar
compilations all select the expected text. Comparing the complete editions by
language confirms that all earlier liturgical text is unchanged.

The 14-page section proof was visually checked at both conditional branches,
El Adon and its commentary, Ahavah Rabbah, Shema’s private-recitation instruction,
and the closing redemption blessing. Artifact:
`output/birnbaum_shabbat_shema/parallel.pdf`.

The regenerated complete parallel edition has 363 pages. Its outline places this
section under Sabbath/festival Shacharit, following Pesukei Dezimrah. The full
artifact is refreshed at `output/birnbaum_parallel.pdf`.

## Sabbath morning Amidah and common Kaddish, printed 349–362 (IA n373–n386)

All fourteen images were read directly, from the Amidah instructions through
Full Kaddish, stopping before the Torah-service heading. Paired new readings,
shared text, page turns, instructions, three new commentary paragraphs and
eight printed source citations are recorded in
`scan_reading/readings/shabbat_amidah.md`. The local Wikisource snapshot was
compared afterward; enlarged scans confirm סִינָי, full לוּחוֹת, the
combined shin/holam glyph in מֹשֶׁה, and the Hebrew quotation in the Amram Gaon
note. Both logical marks are encoded, following the combined-dot policy.

The four new prayer paragraphs use existing canonical prayer URNs. Veshamru
and the closing Kedushat Hayom paragraph reuse the Sabbath evening readings;
the common opening and closing blessings reuse the weekday Amidah. Nekadesh
has a local correspondence for the English “in the world” variant, aligned
with its matching Hebrew. Repeat-printing provenance records the shared texts.
Six Kedushah responses and two Hodaah passages move into reusable files so
transclusions do not inherit the weekday caller’s enclosing instruction.
Their original callers retain their conditions, text and addresses.

The service caller selects the Sabbath Amidah on Shabbat except Yom Tov.
Shabbat Chol Hamoed uses this Amidah with Ya‘aleh Veyavo. Actual-date
compilations verify 19 Tishrei 5786 and 17 Nisan 5786 in Israel and the
Diaspora, including the correct holiday name. The unknown-calendar instruction
explicitly includes Chol Hamoed. Reader-only passages require both repetition
and a minyan; the silent meditation uses the opposite condition. The Hallel
navigation instruction and Full Kaddish are outside the Amidah calendar gate.
Kaddish is a service sibling and a common return address for the later
festival Amidah.

All 79 changed/new XML documents validate, both language projects resolve all
references, and the full-corpus registry check reports no errors or warnings.
All 235 importer tests pass. Compiled audits cover ordinary Sabbath, Reader’s
repetition, private prayer, festival Sabbath, festival weekday, Ten Days,
unknown settings and the four actual Chol Hamoed date/location combinations.
All new commentary is present, the reused Kedushat Hayom remains shared, and
all earlier liturgical text is unchanged in both languages.

The 12-page section proof was visually checked at Kedushah, the shared
Kedushat Hayom, holiday additions, meditation and the separate Kaddish.
Artifact: `output/birnbaum_shabbat_amidah/parallel.pdf`.

The regenerated complete parallel edition has 374 pages. Its outline places
Amidah and Full Kaddish as siblings beneath Sabbath/festival Shacharit, with
Kedushah beneath the Amidah. The full-book Amidah opening, explicit Chol Hamoed
instruction and Hallel/Kaddish boundary were visually checked. The refreshed
complete artifact is `output/birnbaum_parallel.pdf`.

A subsequent audit of both generated Birnbaum language projects checked pointed
words for missing vowels adjacent to shin/sin dots and missing shin/sin dots.
It found one omitted logical holam: Moses in Yismach Moshe. This is corrected
to `מֹשֶׁה` (U+05B9 on mem, U+05C1 on shin). The other candidates were normal
vowel-letter spellings, final consonants or words joined by maqqef. Existing
pointed occurrences elsewhere already encode both marks. Raw comparison
transcriptions and examples documenting their omissions remain unchanged.

## Sabbath and festival Torah service — printed 361–390 (IA n385–n414)

Read all thirty images directly before secondary Hebrew collation. The new
source-reading record preserves the paired readings, commentary, page order,
shared passages, and user-confirmed interpretation of the rubrics. The final
facing English page (n414) completes the requested Hebrew endpoint n413.

The morning-service hierarchy now continues through taking out the Torah,
Torah blessings and personal Mi Sheberakh prayers, Haftarah blessings, Yekum
Purkan, government prayer, blessing of the month, martyrs’ memorial, Ashrei,
and returning the Torah. Half Kaddish before Musaf is a separately addressable
sibling after the Torah-service wrapper. Shared prayers remain transclusions;
new biblical verses use Bible milestones and unique prayer parts use prayer
milestones. New printings and page turns are recorded on shared texts.

The user specified the Sabbath Haftarah ending on Chol Hamoed Pesach and the
festival ending on Chol Hamoed Sukkot. Av Harachamim is omitted on festivals,
Shabbat Rosh Hodesh, Shekalim, Zachor, Parah, HaChodesh, HaGadol, Shuva,
Nachamu, and Mevarchim; Chazon retains it. Customs retaining the memorial on
Mevarchim Iyar/Sivan were explicitly noted by the user but are not specified
by Birnbaum and have not been silently added to the default rule.

The calendar now computes `opensiddur:torah-reading/shabbat-mevarchim` from
the first day of the upcoming Rosh Hodesh, excluding Tishrei. Tests cover
single-day and two-day Rosh Hodesh and a Sabbath which is itself day 30.
Occurrence conditions remain in service wrappers. The first Yekum Purkan is
retained in private prayer; the second and communal Mi Sheberakh require a
minyan. The new person features `bar-mitzvah-father`, `naming-daughter`,
`prayer-for-sick-man`, and `prayer-for-sick-woman` have no default and stay
MAYBE when unspecified, as does the existing Hagomel feature.

Scan checks corrected the festival translation (“may he live to celebrate
festivals in Jerusalem”), festival names in the Haftarah blessing, Aramaic
pointing and defective spellings, and logical holam beside shin dots. The
scan’s sick-person blessings omit the secondary source’s added יברך. The
blessing before the Haftarah retains its cantillation. Printed parentheses
are removed where the same scope already has conditional markup.

Validation: 309 importer/calendar tests pass; all 115 changed/new XML
files pass RelaxNG and Schematron. The synchronized reference database and
registry check reports no errors or warnings. Actual-date compilation checks
13 dates in Israel and the Diaspora, including both Chol Hamoed cases, the
specified special Sabbaths, Chazon, and Mevarchim Iyar/Sivan. Private-prayer
compilation retains only the first Yekum Purkan. All new commentary survives
parallel compilation. Earlier prayer text remains unchanged apart from the
previously authorized holam correction already on the base branch.

Artifacts: `output/birnbaum_shabbat_torah/parallel.pdf` and the regenerated
complete `output/birnbaum_parallel.pdf`.

Additional regression checks: 125 derived-settings, condition-evaluation and
URN-registry tests pass. All eight newly introduced biblical verse anchors are
unique within each language project. The inclusive installment proof has 25
pages; its final Half Kaddish bookmark is a sibling of the Torah-service parent.
The final Torah-service and Half Kaddish bookmarks are siblings within Sabbath
morning Shacharit; the printed festival Musaf return instruction follows the
Kaddish. Identical source citations inherited from shared weekday passages are
not duplicated in the new apparatus; their printed references remain in the
source-reading record. The return-to-ark source citation occurs once in the PDF.
The cleaned full-book PDF settled at 392 pages after two refresh passes.

## Sabbath Musaf — printed 391–424 (IA n415–n448)

All 34 scans were read directly, through Adon Olam at the top of 423/424;
Sabbath morning Kiddush and its note are excluded. The paired reading and page
inventory are in `scan_reading/readings/shabbat_musaf.md` in sourcetexts.

The importer adds ordinary Sabbath and Sabbath–Rosh Hodesh central blessings,
Musaf Kedushah, En Kelohenu, the shorter incense passage, Mishnah Tamid 7:4,
Tana Devei Eliyahu, and all 31 Anim Zemirot stanzas. Shared prayers retain their
existing URNs, with additional source-page ranges and page turns. The local
Rabbi Elazar gloss preserves this printing's shorter English wording. All
37 new commentary/source notes survive the parallel compilation.

The scan confirms ובשביעי in Yismechu against Wikisource's והשביעי. Enlarged
crops corrected pointing in ונקדישך, המיחדים, ונֻטל, הודעת and several Anim
Zemirot words; the full comparison decisions are recorded with the reading.
Logical holam and shin dots remain separate, including both instances of מֹשֶׁה.

Musaf is independently addressable at `siddur:shabbat/musaf`, with a nested
bookmark hierarchy. The ordinary and Rosh Hodesh blessings are mutually
exclusive. Sabbath Musaf is excluded on Yom Tov and Chol Hamoed; its concluding
Kaddish is a sibling after the Amidah, ready for the future festival Musaf return.
There is no Yaaleh Veyavo in the Musaf Avodah. The leap-year phrase follows the
scan's whole-year rubric, remaining MAYBE when no year is supplied.

Validation: 157 changed/new XML documents pass RelaxNG and Schematron; both
projects pass URN resolution, the canonical registry has zero errors/warnings,
and versification passes with only the three previously documented JPS chapters.
The focused importer and calendar suite passes 314 tests and 1301 subtests.
Dated compilations cover ordinary Sabbath, both Rosh Hodesh day numbers,
common/leap years, Hanukkah overlap, Shabbat Shuva, Chol Hamoed Pesach and
Sukkot, Rosh Hashanah, and private prayer, including both Israel/diaspora and
silent/repetition settings. Previously encoded prayer wording remains an exact
prefix of the new full parallel compilation in each language.

The Hanukkah overlap audit exposed a calendar adapter bug: the installed hdate
library calls the holiday `chanukah`, whereas the adapter recognized only
`chanuka`. Both spellings now work, and the day count measures from 25 Kislev
rather than subtracting 24 from a day number in Tevet. Regression checks cover
all eight days and both boundaries in short/full Kislev years, with Rosh Hodesh
still recognized simultaneously.

The final undecided parallel proof is 33 pages, with 21 nested bookmarks. The
complete encoded parallel is 425 pages; its Musaf hierarchy and final Adon Olam
endpoint were checked after the three-pass PDF render. The focused proof was
visually inspected at the opening, leap-year insertion, and Anim Zemirot.


## Pirkei Avot, printed 477–534

All 58 pages were read directly, including both languages and notes. A blind second
reader checked the scan independently, followed by detailed comparison against
mechanically generated Wikisource page slices. The initial reading required many
corrections, especially missing stress marks, and must not be described as error-free.
The page-keyed corrected readings and applied-correction log are preserved in
sourcetexts. Enlarged crops settled the variant spellings and points individually;
qamats/qamats-qatan remains the sole mechanical pointing equivalence.

The XML was compared back to the corrected readings by printed page: all 29 Hebrew
and 29 English pages match, including page-spanning paragraphs and repeated formulas.
The English apparatus contains 78 commentary notes and 36 source notes, grouping 193
printed paragraphs. The complete parallel compile includes all 114 notes and no
selection instructions. The focused 44-page PDF has all six chapter bookmarks below
Avot. Direction measurement found 0 of 1863 Hebrew runs reversed; the deliberately
reversed control flagged 1841. Commentary fingerprint checks found all 115 paragraphs
long enough for six distinctive words; repeated introductory wording was checked
against the compiled note counts rather than mistaken for duplicate annotations.

All 33 new or changed XML documents pass RelaxNG and Schematron. The canonical
registry reports no errors or warnings. Calendar and compiler checks cover
Israel/diaspora differences, combined chapters, skipped weeks, unknown inputs,
explicit chapter overrides, and complete-text instruction suppression. In the
siddur caller, a skipped week suppresses the entire unit, including its heading.

The complete parallel siddur through Avot renders successfully in three LuaLaTeX
passes to 497 pages. Its Avot bookmark contains all six chapter bookmarks, and
all 114 Avot apparatus notes are present in the full compilation.

## Conclusion of Shabbat and Birkat Levanah, printed 535–566

Internet Archive n559–n590 was read in both languages, including the notes, with
independent second readings and individual scan adjudication of the differences.
The corrected page readings and adjudications are retained in sourcetexts. Hallel
and its commentary are excluded; the three Birkat Levanah citations on 566 remain.
The Hebrew-only prayers continue across printed 559–561, including the even page
560; empty English realizations preserve the absence of a printed translation.

The reverse comparison of generated prayer text against the corrected readings
has no page differences. It excludes the reused Kaddish, headings and apparatus;
those were checked separately. Biblical anthology boundaries use milestones,
with local correspondences and bounded source quotations for alternate printings.
Printed citation numbering is retained even where canonical verse numbering differs.

The user corrected the upcoming-week rule: Erev Pesach alone does not omit Vihi
Noam or Veatah Kadosh. Omission requires Yom Tov within Sunday–Friday, using the
Israel/diaspora calendar. Tishah B'Av separately omits Vihi Noam and Psalm 91 while
retaining Veatah Kadosh. Ten targeted checks pass, including settings derivation,
the Erev Pesach
boundary, diaspora second days, unknown settings, and distinct output filenames
for the Hamavdil hymn and blessing (a collision found and fixed during validation).

Both projects pass reference validation, and the registry reports no errors or
warnings. All 1,119 project XML files pass RelaxNG and Schematron. The focused
Saturday-night proof has 51 pages and the Birkat Levanah proof has six. All 34 new
apparatus notes have matching long-word fingerprints in the rendered proofs.
The Hebrew-only continuation and the opening of Birkat Levanah were visually
inspected. Hebrew direction checks pass with deliberately reversed controls.

The final reuse audit found a local Titkabal variant: Hebrew תִּתְקַבַּל (pataḥ),
rather than the earlier tsere, and English “whole household of Israel,” rather
than “whole house of Israel.” This printing now has local correspondences for
Titkabal and Yitbarakh (whose punctuation also differs). The second l'ella alone
retains the standardized Ten Days conditional without the printed parentheses.

The complete test suite passes: 2,742 tests, 12 skipped, and 3,157 subtests.
The added final Kaddish regression was then run with all ten focused checks.

The final full parallel renders in three passes to 549 pages. The conclusion of
Shabbat has nested section bookmarks, Birkat Levanah has its own bookmark, and all
34 new notes have matching long-word fingerprints in the full PDF. The full-book
Hebrew-direction measurement reports one flag among 21,250 runs: the pre-existing
weekday Mincha rubric's unwrapped “שים שלום” on PDF page 162 (printed folio 150).
This is outside the new installment; both focused proofs pass their direction checks.

### Follow-up: weekday Mincha rubric direction

The page-162 direction flag is fixed in the existing worktrees. The importer now
marks שים שלום as Hebrew within its English instruction, and regeneration changes
only that rubric in the Hebrew XML; the English output is identical. Both Amidah
files pass RelaxNG and Schematron. A focused PDF made from the generated rubric
reproduces the backwards phrase before the fix and passes the glyph-direction
check afterward, including the deliberately reversed control. The full 549-page
PDF above predates this follow-up; the corrected focused proof is
`output/birnbaum_mincha_rubric_fixed.pdf`.

## Hallel: Internet Archive n 589–n 598 (printed 565–574)

Read the complete section from the scan, with blind independent Hebrew and English
readers. Hebrew was subsequently compared with the mechanically extracted
Wikisource slices; English was checked against OCR and the enlarged scan. The
adjudications and corrected readings are saved page by page. Enlarged crops
confirmed deficient דַּלֹּתִי, stresses in תַּגְמוּלֽוֹהִי and עֹֽשָׂה, and
יִסְּרַֽנִּי יָהּ. Unprinted stresses were removed from the two לָנוּ occurrences
in 115:1 and the two הַצְלִיחָה occurrences. Printed English misspellings
“Similiarly” and “similiar” are retained. Psalm 117 has no final “Hallelujah” in
this English printing. The logical holam beside shin in שֹׁמֵר is retained.

Psalms 113–118 have biblical chapter and verse URNs. Earlier quotations in Yehi
Khevod and Ashrei now carry local correspondence milestones with biblical source
references, preventing duplicate canonical verse addresses. Hallel's performance
wrapper preserves the repeated half-verses of 118:25 while the canonical biblical
verse contains each half once. Printed repetition instructions for 118:21–24 and
26–29 remain instructions. The opening and closing blessings are reusable prayers.
Whole-Hallel availability and the all-occasion shivah-house omission belong to the
siddur caller; the following Kaddish is a sibling section. Rosh Hodesh during
Hanukkah uses full Hallel and Full Kaddish.

All 41 changed XML files pass RelaxNG and Schematron. Registry checks have zero
errors or warnings. All 12 Hebrew/English biblical chapters read back exactly
against the adjudicated data, and both printed Ana repetitions occur twice.
Nine compiled calendar/observance scenarios cover full, half, absent, overlapping
Rosh Hodesh/Hanukkah, Israel/diaspora Pesach and shivah-house omissions on Rosh
Hodesh, Hanukkah and a festival. Calendar boundary tests additionally cover both
Kislev lengths, two-day Rosh Hodesh and unknown inputs. They caught pyluach's
absolute date subtraction; Hallel now uses a signed Julian-day difference.

The focused parallel proof is output/birnbaum_hallel_parallel.pdf. All seven
commentary notes occur exactly once (nine-word fingerprints). All six Psalm
headings and HALLEL paint left to right; Hebrew direction is checked using glyph
coordinates and a deliberately reversed control. The bookmarks nest Psalms 113–118
under Hallel and keep the following Kaddish outside it. The full-book PDF has not
been regenerated for this installment.

The complete suite passes: 2,747 tests, 12 skipped and 3,222 subtests. The only
warning is a pre-existing Python string-escape warning in an exporter test.

## Rosh Hodesh Musaf: printed 575–584 (Internet Archive n599–n608)

Read all ten scan pages directly, with independent Hebrew and English second
readings and a mechanical Hebrew transcription comparison after the primary
reading. The Hebrew reviewer supplied 39 findings; the primary reader inspected
the disputed crops before applying corrections. Five differing meteg readings
were checked individually; this is not a claim that every agreed meteg received
an independent crop review. Page readings, rubrics, notes and adjudications are
saved in `sourcetexts/sources/birnbaum_siddur/scan_reading/`.

The 32 aligned text passages reuse 15 existing correspondences that match in both
languages. Other printings retain their differences: English “Shield.” and
“Praise the Lord.”, “three tenths”, the response's “thou has kept us”, and the
Hanukkah paragraph's “temple” and “appointed”. Hebrew corrections include the
rain vowel, punctuation, deficient/plene spellings and individual dagesh/meteg
readings. Divine-name normalization and logical holam beside shin follow project
policy. Modim and its congregational response continue independently across the
page turn. New correspondence boundaries use milestones; whole prayers and
sections retain divisions. Variant quotations identify their underlying prayer
or biblical source.

The address `urn:x-opensiddur:text:siddur:rosh_chodesh/musaf` contains a separately
addressable `/amidah`, weekday Kedushah and the Rosh Hodesh middle blessing. The
weekday Rosh Hodesh gate is in the caller, leaving the Amidah reusable; Sabbath
Rosh Hodesh retains its existing Musaf. The leap-year addition applies throughout
the leap year. Rain, Hanukkah, Reader-only passages and private meditation use
existing features, with no printed-parenthesis duplication. The ending retains
the directions to Psalm 104 and Aleinu; neither is expanded here. No Kaddish is
printed in this installment.

Regeneration previously lost two hand-authored conditions in `notes_amidah.xml`.
The importer now preserves them: the nineteen-blessing essay is restricted away
from Sabbath, Yom Tov and Musaf, and the ordinal “eighteenth” in the Modim response
commentary uses the same restriction. The Rosh Hodesh Musaf proof consequently
omits the nineteen-blessing essay while shared general commentary remains.

Validation: all 70 changed XML files pass RelaxNG/Schematron; the registry has no
errors or warnings. The full suite passed 2,750 tests (12 skipped; 3,259 subtests)
before the final note-condition change; afterward all 252 Birnbaum importer tests
and 1,372 subtests pass, including both note regressions. Seven dated compilations
exercise both days of a two-day Rosh Hodesh, summer/winter, leap-year Elul,
Hanukkah, Reader/private/no-minyan, an ordinary day, and Sabbath Rosh Hodesh.
Dated leap-year derivation uses Gregorian date and location as required by the
calendar implementation. All 32 passages in each language match the adjudicated
readings in the MAYBE parallel compile, allowing markup-boundary whitespace.

The focused parallel PDF has nine pages with nested service/Amidah/Kedushah and
middle-blessing bookmarks. Its new commentary and four new source citations
appear once, and all nine printed biblical citations are present through the new
and shared apparatus. Latin headings paint left to right. All 311 Hebrew glyph
runs pass the direction check; the reversed control flags all 311. The full-book
PDF has not been regenerated for this installment.

## Festival prayers, IA n609–n624 (printed585–600)

Read all sixteen page images directly, Hebrew and English, then compared the Hebrew
with mechanically produced Wikisource slices. Independent readers supplied English
alignment and a second Hebrew reading. The source repository preserves the corrected
page readings, mechanical slices, provisional comparison records, and crop decisions.
The initial second reading omitted many metegs; those omissions were not accepted as
absence. English OCR files at the mapped scan keys contain other leaves, so those files
were not used to supply words or to claim an English OCR agreement score.

The primary reading required corrections in spelling, pointing and punctuation,
including יְהֵא שְׁרֵא, צָרְכָּנָא, defective תִּשְׁכֹּן, וַתַּנְחִילֵֽנוּ,
סָבְרֵי and לֵשֵׁב. Crops also corrected several commas and the Sabbath parenthesis
boundary in Kiddush. Two tentative secondary suggestions (נָגִיד and plene שבועות)
were rejected after tighter crops. The English period in “have pity on us. and save us”
and tight “fathers,that” are retained. The logical holam in מֹשֶׁה is encoded.
The secondary transcription's added translation of the eruv declaration, morid hatal,
and expanded priestly ritual are absent from these printed pages and are not imported.

The section includes Eruv Tavshilin, festival candle lighting, the festival Amidah,
and festival Kiddush, with all six commentary notes. Sabbath insertions use functional
conditions without the diplomatic parentheses. Candle-lighting Shehecheyanu follows
the user's first-two-nights diaspora / first-night Israel decision, excluding the final
Pesach days. “In the Sukkah” has an explicit manual presence feature with no default.
Shacharit and Mincha retain their different Kedushah texts; Sim Shalom is for Shacharit,
Shalom Rav for Mincha and Maariv. Vatodienu is restricted to Maariv after Shabbat.
The earlier services now call the festival Amidah and return to their existing Kaddish;
Kaddish remains outside the Amidah. Shabbat Chol Hamoed retains the Sabbath Amidah.

Exact bilingual matches reuse existing addresses. Eight shared leaf divisions were
extracted into independent files because the compiler otherwise inherited surrounding
weekday rubrics. Their earlier callers retain their conditions. The festival Amidah
explicitly supplies its Yom Tov context so weekday-only commentary stays out of an
undated proof. The Sabbath Arvit variant lookup now finds its source by correspondence
rather than assuming the source remains embedded in the Hodaah container.

Validation and proof:

- All 66 aligned rows read back from compiled XML in both languages (Savri has no
  printed English translation); conditional parentheses and page markers are excluded
  from this comparison, with Hebrew points and punctuation retained.
- Thirteen dated compiles cover the four festivals, reader/private/no-minyan settings,
  morning/afternoon/evening, Saturday-night additions, candle-lighting location boundaries,
  and the final days of Pesach. All pass.
- All 157 changed/new XML files pass RelaxNG and Schematron. Registry check reports
  0 errors and 0 warnings.
- Full regression suite before shared-passage extraction: 2757 passed, 12 skipped;
  importer regressions after extraction and the final guard test: 258 passed,
  1488 subtests passed.
- `output/birnbaum_festival_parallel.pdf`: 15 pages, hierarchical bookmarks, all six
  new commentary notes exactly once, no inherited weekday instructions or nineteen-
  blessing essay. English headings are left to right by glyph coordinates. Hebrew
  direction check: 0/490 reversed runs; reversed-run control flags 487/490.
- Six paired instruction starts were measured in the PDF. The proof and compiled XML
  remain untracked output artifacts.

Follow-up: removed the duplicated Eruv Tavshilin rubric from the occasion gate.
The reusable Eruv unit retains the printed instruction beneath its heading. Both
caller files validate; compiled XML and PDF now contain one instruction per column,
confirmed by the PDF word positions.

### Yizkor — IA n625–n632, printed pages 601–608

Read all eight images before consulting the Hebrew transcription, with independent
Hebrew and English second readings. Added the opening eight biblical verses,
Psalm 91, the father/mother/husband/wife and martyrs prayers, both forms of El Male
Rachamim, and Av Harachamim. All three printed commentary blocks (including the
607–608 continuation), four source citations, name-placeholder instructions, and
speaker cues are retained. English El Male Rachamim deliberately lacks the Hebrew
charity-pledge clause: that is the printed translation. The Reader cue within Av
Harachamim occurs only in the Hebrew column.

Eight primary-reading corrections were verified against enlarged crops: the
maqqef in ben-enosh; the space in ure’eh yashar; the meteg in veharuach; the comma
after tidrokh; the meteg in noderet; the absence of a yod dagesh in hayekarah; the
comma after rabbah; and the patach in Av Harachamim. Crop coordinates, provisional
readings, independent readings and corrected page texts are saved in sourcetexts.
The primary meteg in asbi‘ehu and the pointing of yastireha survived review. The
logical holam in Moshe is retained under the project’s combined-dot policy.

Mechanical Wikisource page slices were compared after reading. The differences
include plene yizkor, supplied generic names replacing printed dots, gan-eden
maqqefs, an added kol in the martyrs prayer, and divine-name conventions. Only
qamats-qatan-only differences were settled mechanically. Page 607 contains later
Shoah/IDF additions absent from the scan and requests a missing foundation span,
`קריאת התורה / יזכור לקדושי השואה יד ושם`. Its raw partial result is retained as a
**diagnostic** in `comparisons/yizkor-607.json`, not written as a complete
`transcription/607.txt`. That snapshot limitation does not affect the directly
read printed text; no completeness claim is made for the modern additions.

The occasion gate is in `yizkor.xml`, outside the reusable
`urn:x-opensiddur:text:prayer:yizkor`. The user confirmed Israel adaptation:
Pesach day 7 and Shavuot day 1 in Israel; days 8 and 2 respectively in the
diaspora; Yom Kippur and Shemini Atzeret in both. The shared Sabbath/festival
Torah service calls it before returning to Ashrei. The full siddur also retains
its printed position after the festival prayers. The printed diaspora rubric
appears once per column. Independent Boolean settings under `opensiddur:yizkor`
are `father`, `mother`, `husband`, `wife`, `el-male-man`, and `el-male-woman`;
unset values remain MAYBE and multiple selections can be true together.
`yizkor_service.xml` provides the reusable service without the occasion gate.

Psalm 91’s English differs from the earlier occurrence. Local occurrence
milestones retain biblical source URNs rather than replacing either wording.
Av Harachamim also has different Hebrew pointing, punctuation, and an omitted
le‘eineinu in its opening. Its biblical quotations have their own milestones
and source URNs. Two short text-identical leaves remain local because referencing
the earlier enclosing document inherited its Reader rubric and Crusades note.
The Yizkor proof contains only the notes printed with this occurrence.

Dated integration checks uncovered a calendar defect: `simchat_torah` was always
mapped to day 2 of `shmini-atzeret`, including Israel’s combined festival on
22 Tishrei. The mapping now derives the day from the Hebrew date. A regression
test covers 21–24 Tishrei in both locations. All 13 actual-date compilations pass,
including Israel/diaspora final Pesach and Shavuot days, Yom Kippur, Shemini
Atzeret, diaspora Simchat Torah, and an ordinary day. The father and mother can
both be enabled while the other individual prayers are disabled.

Validation and proof: 77 changed/new XML files pass RelaxNG and Schematron; both
projects pass URN/contributor-reference validation. The importer and calendar
suite passes 334 tests and 1,862 subtests. Compiled readback matches all 32 primary
passages in both languages (NFC and whitespace normalization only, with printed
name dots and the Reader marker handled explicitly). The seven-page focused
parallel PDF has six text pages and one metadata page. Its three commentaries
and four source citations each appear once; the inherited Crusades note is absent.
Hebrew direction: 0 of 213 runs reversed; the reversed-run control flags 211.
English heading glyph order passes. Eight paired rubric starts align within 5pt;
56 sampled margin numbers lie outside the columns and reset to 5 on each text
page. No note markers share a position. Moving the introductory commentary from
the service wrapper to the opening text eliminated a 13.55pt rubric offset;
separating the source citations from commentary anchors eliminated overlapping
note marks. Bookmarks nest the opening verses and Psalm 91 beneath the memorial
service.

Proof: `output/birnbaum_yizkor_parallel.pdf` (compiled XML and TeX alongside it).

## Festival Musaf, priestly blessing, morning Kiddush and Tal (n633–n660)

Printed609–636 was read directly, with independent Hebrew and English readers,
then compared against mechanically resolved page slices. The source audit is in
`sourcetexts/sources/birnbaum_siddur/scan_reading/festival_musaf/`. It preserves the
initial readings, raw mechanical differences, final aligned readings, and the
corrections rather than reporting a misleading zero-error initial transcription.
Enlargement corrected several initial Tal consonants and vowels, the pausal rain
vowel, Shavuot spelling, and individual dagesh/meteg readings. The first-half
second reader's omitted metegs were not accepted as a bulk correction.

119 bilingual alignment rows preserve the edition's text, including missing
English Savri, the condensed English dream prayer, and Tal's verse lines.
Compound biblical passages have per-verse milestones and biblical source URNs;
local occurrence URNs retain edition wording. Exact bilingual reuse is limited
to independently checked passages. Gevurot and Atah Vechartanu stay local because
transclusion also imported commentary absent from these pages. The printed
Numbers29:41–61 citation is preserved as an apparent print error.

The editor confirmed longer Kedushah for Shabbat Chol Hamoed and a separate MAYBE
custom for repeating Uminchatam. Tal replaces the Reader's first two blessing
openings on Pesach day1, then resumes Mekhalkel. The Kohanim ceremony branches at
the end of Retzeh, returns through Modim, and rejoins Sim Shalom. Its availability
is separate from minyan/repetition. Occasion conditions remain in callers; the
standalone Tal, priestly ceremony and morning Kiddush remain addressable.

Verification:269 importer tests; both XML projects validated, including final
verse-boundary changes; registry zero errors and warnings. Actual-date compiles
exercise Pesach silent/repetition, no minyan, Israel/diaspora Sukkot, optional
Uminchatam, and Shabbat Chol Hamoed. The parallel proofs match all119 Hebrew and
English rows and contain all34 printed notes exactly once. PDF glyph-position
checks found no reversed Hebrew runs and rejected deliberately reversed controls.
Measured line numbers sit outside adjacent text; sampled opening rubrics align.


## Sefirat HaOmer and Akdamut (n661–n678)

Printed637–654 was read directly with independent Hebrew and English readers,
then compared with mechanically resolved page slices. The source audit under
`scan_reading/omer_akdamut/` preserves the initial readings, 332 individual
second-reader proposals, final readings, and adjudicated comparison differences.
Initial Akdamut readings required substantial consonant and vowel corrections;
several confident initial crop reports were overturned. Parent enlargement also
found a shared omission: the holam in לְתַלּוֹתֵי. Metegs were reviewed individually,
not inferred as a class. Defective שמנה in all five count occurrences, full
בנגינות/מישור, and the edition's other verified spellings are retained.

The encoding contains all49 daily formulas and the prayers before and after them,
plus all90 Akdamut lines in45 aligned pairs. Biblical passages retain source URNs
with bounded verse milestones; reused liturgical lines also carry source identity.
Whole-section occasion conditions are in callers; daily count conditions select
within the reusable Omer text. Unknown dates retain MAYBE. Akdamut is gated to
Shavuot day1 in both locations. The two sections are included in the siddur index.

Actual-date compilation exposed an existing calendar adapter bug: `hdate.omer.day`
is the remainder within the week, not the Omer count. The adapter now uses
`total_days`; regression coverage exercises all49 days and the adjacent dates in
Israel and diaspora. Sixteen actual-date parallel compilations cover the season
boundaries, days7/8, and both Shavuot dates.

Verification:273 scan-importer tests and72 calendar tests pass. All29 changed/new
XML files validate; the URN registry reports zero errors and warnings. Compiled
text matches all101 bilingual units exactly, and all16 printed notes appear at
their intended occurrences. Hebrew glyph checks report0/233 reversed Omer runs
and0/131 reversed Akdamut runs; deliberately reversed controls flag all364.
English heading glyph order passes. Four sampled paired rubric starts align
exactly;124 sampled margin numbers sit outside adjacent text and numbering
restarts at5 on all34 populated column-pages. The Omer bookmark contains the
counting section and Psalm67; Akdamut has its own bookmark.

Review proof: `output/birnbaum_omer_akdamut_parallel.pdf` (individual compiled XML,
TeX, and PDFs are retained alongside it).
