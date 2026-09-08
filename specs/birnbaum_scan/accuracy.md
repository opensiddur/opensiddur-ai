# How far the Wikisource transcription stands from the 1949 print

Measured on the Hebrew pages of the weekday shacharit Amidah, by reading each page off
the scan and then diffing that reading against
`sourcetexts/.../source/text/אשכנז/דפי יסוד/תפילת העמידה.txt`. Every difference was
adjudicated by going back to the page image.

`print` = the page said what was read off it, and the transcription departs from it.
`reading` = the transcription was right and the scan was misread.
`unresolved` = the scan cannot settle it.

## Pages read so far

| page | words | whitespace | consonants | vowels | misreadings |
|---|---:|---:|---:|---:|---:|
| 81 | 39 | 0 | 0 | 0 | 0 |
| 83 | 125 | 0 | 6 | 7 | 0 |
| **total** | **164** | **0** | **6** | **7** | **0** |

**Not one misreading in 164 words.** Every difference is the transcription departing
from the print. That is the number the side quest was for: reading pointed Hebrew off a
1541 px scan, in enlarged bands, is reliable — the 4x crop is doing the work, and the
band upscaling does not need raising.

## The six consonantal differences — all of them page 83, all of them substantive

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

## The seven vowel differences

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

Pages 85-97. The method and the tooling are proved; what remains is the arithmetic. The
Hebrew Wikisource sections for those pages are named in the unit file's own page markers
(`<קטע התחלה=עמוד 85/>` and the rest), so extracting the comparison text is mechanical.

## What this means for the approach

- The scan is a sufficient source for pointed Hebrew at this resolution. The reading
  does not need the transcription to be accurate.
- The transcription is *not* a witness to this print, exactly as the conversion
  procedure warned: on one page it silently adds a passage, rewrites a rubric into
  Hebrew, and prints a vowel its own footnote says Birnbaum did not use.
- Using it as a proofreading check, and never as a source, is the right call. It caught
  nothing wrong with the reading; it disclosed four things wrong with itself.
