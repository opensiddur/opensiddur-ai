# Asher Selichoth: open questions

Decisions the encoding cannot make from the scan. Each has what is printed, what the encoding
did, and the options, with the decision on its `answer:` line. All 19 were answered on
2026-10-16: misprints are in sourcetexts `scan_reading/corrections.json`, and editorial notes in
`scan_reading/editorial_notes.json`, each beginning "Editor:". Scan pages are `s<N>`
(the Archive leaf is `n<N-1>`); printed pages are the book's own numbers. Files are in
opensiddur-projects `project/selichoth-asher-1912-{he,en}/`; evidence is in sourcetexts
`sources/asher_selichot/`.

Clear misprints are not here: they are corrected as `tei:sic`/`tei:corr`, listed in sourcetexts
`scan_reading/corrections.json`. Printed note markers with no note anywhere in the scan are a
known, unresolvable issue and are not listed either.

## Ambiguous abbreviated citations

### 1. Tzom Gedaliah opening: כי רבו (s184/s185, printed 91)

- **Printed:** Hebrew "…till כִּי רַבּוּ page 7"; English "till 'for it is great,' page 7".
  כי רבו can end either at Shomea tefillah ("for it is great") or after the Selah lanu that
  follows it.
- **Now:** the expansion ends at Shomea tefillah; the following printed Selah lanu is kept once,
  not duplicated. The printed citation is unchanged. The second penitential day prints the same
  abbreviation and is expanded the same way.
- **Evidence:** `tzom-gedaliah-adjudication.json` (corrections, "End at Shomea tefillah");
  `scan_reading/tzom-gedaliah/opening_instruction.json`; `penitential-second-day-adjudication.json`.
- **Options:** keep (end at Shomea tefillah) · include the Selah lanu in the expansion.

answer: keep: end at Shomea tefillah (2026-10-16).

### 2. Erev Yom Kippur opening: conflicting ranges (s308/s309, printed 153)

- **Printed:** Hebrew "Say from אַשְׁרֵי page 1, till שׁוֹמֵעַ תְּפִלָּה page 4"; English "Say from
  'for thou hearest prayer,' page 2, till 'for it is great,' page 7".
- **Now:** both languages expand Ashrei through Shomea tefillah, as the Hebrew says; the Selah
  lanu reprint is excluded.
- **Evidence:** `erev-yom-kippur-adjudication.json` (editorial 3, unresolved 1–2);
  `scan_reading/erev-yom-kippur/opening_instruction.json`.
- **Options:** keep (follow the Hebrew) · follow the English range in the English column.

answer: keep: Ashrei through Shomea tefillah in both languages, as in every other service (2026-10-16).

### 3. Erev Yom Kippur: "page 7" and a raised mark (s309, printed 153)

- **Printed:** "page 7" followed by a small raised mark like a superscript c, then "after which".
- **Now:** encoded as "page 7c". It is probably a mis-set comma or a stray sort.
- **Options:** keep "7c" · print "7," (as a correction) · drop the mark.

answer: drop the mark; the reading is "page 7 after which" (2026-10-16).

## Wording and fact, kept as printed

These are the translator's words or facts, not compositor's errors, so they stay as printed
unless decided otherwise. Options for each: keep · keep with an editorial note · correct.

### 4. "seven names" for eight gates (s233, printed 115, second penitential day)

The note on Shaarei shamayim calls the gates seven; the poem enumerates eight.

answer: keep: not an error. Hagigah 12b names seven heavens; Shamayim, the poem's first stanza, is the general term (2026-10-16).

### 5. "recited has thirteen attributes" (s297, printed 147, fifth penitential day)

Ungrammatical: probably "recited his thirteen attributes", or a word is missing.

answer: misprint: "has" corrected to "his" (2026-10-16).

### 6. The gallows note gives inconsistent feet and yards (Fast of Esther, s365, printed 181)

answer: keep as printed (2026-10-16).

### 7. Yom Kippur Katan psalm rubrics disagree (s382/s383, printed 190; s406/s407, printed 202)

One rubric says "when the New Moon is on Sabbath or Sunday", the other "If the Eve of New Moon
is on Sabbath or Sunday". Both stay printed instructions.

answer: keep both, with an editorial note on the second. When these rubrics become calendar conditionals, follow the first: the New Moon on Sabbath or Sunday (2026-10-16).

### 8. Seventh day: refrain limits named in reverse (Hebrew, seventh_day.xml)

The repetition rubric says "from נשענו till עזרנו". The expansion already follows the verified
refrain.

answer: misprint: the two words swapped, "from עָזְרֵנוּ till נִשְׁעָנוּ" (2026-10-16).

### 9. "the sighing of the prisoner coming before thee" (s29, printed 13, first day)

Ps. 79:11 reads "come before thee", and every other printing in the book has "come".

answer: misprint: "coming" corrected to "come" (2026-10-16).

### 10. "unto thy holy mountain" (s37, printed 17; s151; s333)

Misquotes Isa. 56:7 ("my holy mountain"). Printed identically all three times, so it is the
translator's text.

answer: keep, with an editorial note giving "my", in all three places (2026-10-16).

### 11. "Hazariah" for Azariah (s47, printed 22; s175, printed 86)

Printed the same both times, so a transliteration choice rather than a typo.

answer: keep as printed (2026-10-16).

### 12. "the event on Horeb" with the note "Zion." (s207, printed 102, Tzom Gedaliah)

The Hebrew reads חורב; the note conflicts with its anchor. It may be a gloss, a misplaced
marker or an error.

answer: keep, with an editorial note that Horeb is Sinai (2026-10-16).

### 13. "the people saved by thee meets with iniquity" (s295, printed 146, fifth penitential day)

Awkward wording rather than a letter-level typo.

answer: keep: the translator's wording (2026-10-16).

### 14. "God of our Father!" (s57, printed 27, second day)

Possibly "fathers" with the s dropped, possibly a deliberate singular.

answer: misprint: "Father!" corrected to "fathers!" (2026-10-16).

### 15. "ardent pass" (s269, printed 133, fourth penitential day)

The word is cut off. "passion" or "passions" are both possible, so it is not corrected.

answer: misprint: "pass" corrected to "passion" (2026-10-16).

### 16. "beneficence. and" (s69 and s77, third and fourth days)

A full stop where the reprint on s303 has a comma.

answer: misprints: both full stops corrected to commas (2026-10-16).

### 17. "And the Lord, said I" (fifth day, s81)

Probably "And the Lord said, I": a misplaced comma.

answer: misprints: "Lord, said I" to "Lord said, I" (fifth day); "said I" to "said, I" (fourth day); "according as" to "according to" (Erev Rosh Hashanah, s107) (2026-10-16).

## Other questions

### 18. "They cast lots" quotation is never closed (s87, printed 42, sixth day)

"…even as it is said in Holy Writ. “They cast lots for us as for a waif in the wilderness, …"
has no closing quote. Where it should end (after "wilderness," or after "gracious rule.") is a
judgement, so it is not a mechanical correction.

answer: close the quotation after the scriptural words, "They cast lots for us”" (2026-10-16).

### 19. Erev Rosh Hashanah s111: notes that look attached to the wrong words

Note 1 after "unclean" says "Thy laws"; note 2 after "clean" says "idolatry". If the printed
markers are interchanged, the notes would attach by content, as on Tammuz printed 184.

answer: misprint: the English words transposed; corrected to "the clean [Thy laws] for the unclean [idolatry]" (2026-10-16).
