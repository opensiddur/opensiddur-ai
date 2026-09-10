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
| 81 | 39 | 0 | 0 | 0 | 0 |
| 83 | 125 | 0 | 6 | 7 | 0 |
| **total** | **275** | **0** | **8** | **8** | **0** |

**No misreading survives in 275 words**, and every difference that does is the
transcription departing from the print. Reading pointed Hebrew off a 1541 px scan, in
enlarged bands, is reliable — the 4x crop is doing the work, and the band upscaling does
not need raising.

But page 1 is the first page on which the check earned its keep in the other direction.
The first draft of the reading had `יָחֹֽלוּ` where the transcription had `יָחֻֽלוּ`; going
back to the image settled it **for the transcription** — three dots set diagonally under
the ḥet, and no dot above it. The reading was corrected before it was committed, so the
difference is not in the table above; recording it here is the only way it is not simply
lost. One catch in 275 words is the honest error rate of this method, and it is not
zero. It also shows the check working as designed: the transcription is not a source,
but it is a competent second reader.

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
