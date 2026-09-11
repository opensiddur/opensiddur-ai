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
| 1 | 111 | 0 | 2 | 1 | 0 (1 caught before committing) |
| 3 | 94 | 0 | 0 | 4 | 0 (3 caught before committing) |
| 5 | 110 | 0 | 0 | 3 | 0 (3 caught before committing) |
| 7 | 162 | 0 | 0 | 9 | 0 (6 caught before committing) |
| 81 | 39 | 0 | 0 | 0 | 0 |
| 83 | 125 | 0 | 6 | 6 | 0 (1 caught **after** committing) |
| **total** | **641** | **0** | **8** | **23** | **0** |

**No misreading survives in 641 words.** But the second number in that column has grown
faster than the first, and it is now the one that matters: **ten readings have been
corrected, all of them points, and nine of the ten were caught by the
transcription rather than by looking harder.**

That revises what the first three pages concluded. Reading this scan in enlarged bands is
reliable *for consonants* — the skeleton has not been wrong once in 641 words. It is not
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

## Corrections are data now, not prose

`corrections.jsonl` records every reading corrected so far -- what it was, what the print
carries, what settled it, and whether it was caught before or after committing. Fourteen
entries.

It exists because a correction has nowhere else to live. Once a reading is fixed the
difference disappears from the comparison, so the `reading` verdict that recorded it
matches nothing and `compare` rightly warns about it. Verdict files describe live
differences; corrections describe ones that are gone. Keeping them in the same file made
the second kind either noisy or invisible.

The counts in the table above are therefore checkable rather than asserted: thirteen of
the fourteen were caught before committing, and the fourteenth is page 83's.

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

Page 7's two catches were `זְרוֹעַ` for **זְרוֹעוֹ** and, in the blessing, `לְהָנִֽיחַ`
for **לְהַנִּֽיחַ** — the same word page 5 had to correct, so the spelling is his and
consistent. Worth noting that the page's two occurrences are genuinely different:
the blessing sets לְהַנִּֽיחַ and the meditation sets לְהָנִיחַ, and the transcription
distinguishes them too. Flattening them would be a correction, not a reading.

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
