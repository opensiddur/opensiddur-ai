# Open questions

3 unsettled, over 1 page(s). Everything already decided is left out on purpose.

Write the form the print carries on the `answer:` line -- or `print` to keep the reading, `reading` to take the transcription. Then:

    python -m opensiddur.importer.birnbaum_scan.open_questions --apply specs/birnbaum_scan/OPEN_QUESTIONS.md

## Printed page 11

### 11.1  (consonants)

    context        … מִבְּכוֹר אָדָם וְעַד בְּכוֹר בְּהֵמָה, …
    reading        מִבְּכוֹר
    transcription  מִבְּכֹר

    differs by     the letters differ, not just the points

What to look at: a letter: the skeleton differs, so this is a different word.

*No entry in the verdict file — this one was never written down, only left out.*

    key: consonants:0:מִבְּכוֹר|מִבְּכֹר
    answer:

### 11.2  (vowels)

    context        … סוֹף לְאַחְדוּתוֹ. אֵין לוֹ דְּמוּת הַגּוּף וְאֵינוֹ גוּף לֹא …
    reading        דְּמוּת
    transcription  דְמוּת

    differs by     reading has DAGESH OR MAPIQ

What to look at: a point: crop it at 12x, and ask what the word is before blaming the scan.

*No entry in the verdict file — this one was never written down, only left out.*

    key: vowels:123:דְּמוּת|דְמוּת
    answer:

### 11.3  (whitespace)

    context        … אֲדוֹן עוֹלָם אֲשֶׁר מָלַךְ בְּטֶֽרֶם כָּל יְצִיר נִבְרָא. לְעֵת …
    reading        '־'
    transcription  ' '

    differs by     the letters differ, not just the points

What to look at: spacing or a line break.

*No entry in the verdict file — this one was never written down, only left out.*

    key: whitespace:35:'־'|' '
    answer:

