---
name: scan-to-jlptei
description: Convert a scanned book into JLPTEI by reading its pages — fetching and enlarging leaves, reading the print, measuring a transcription against it, authoring the TEI, and checking the rendered PDF. Use when converting a scan, especially a facing-page bilingual one (Hebrew opposite English), or when a parallel PDF looks wrong.
---

# Reading a scan into JLPTEI

The page is the evidence. A transcription of the book, however good, is a proofreading
check on the reading and never its source — `specs/BIRNBAUM_FROM_SCAN.md` opens with why,
and `opensiddur/importer/birnbaum_scan/__init__.py` states it in three lines.

Everything below is what those documents do not already say. Where this file and a
document disagree, **the document wins and this file is wrong** — fix it.

## Order of work

| | | |
|---|---|---|
| 1 | Fetch and cut the leaf | `python -m opensiddur.importer.birnbaum_scan.pages 81 82 83` |
| 2 | Read the page into prose | by hand, into `readings/{printed}.md` |
| 3 | Diff against a transcription | `compare` — build the slice with `transcription.resolve`, never by stripping markup |
| 4 | Adjudicate each difference | go back to the image; record in `verdicts/{printed}.json` |
| 5 | Author the TEI | hand-written, one function per prayer |
| 6 | Compile and render | `exporter.compiler`, then `exporter.pdf.pdf` |
| 7 | **Measure** the PDF | `reference/measuring-the-pdf.md` |

Steps 1 and 3 explain themselves: the module docstrings of `opensiddur/importer/birnbaum_scan/pages.py` and `compare.py`
carry the reasoning — why a page is fetched once, why bands overlap and are enlarged, why
differences are counted in three buckets and not merely resolved. Read them rather than a
summary of them.

A printed page number is not a leaf number is not a scan page. `pages.json` is the only
place that correspondence lives; never re-derive it.

## What two languages change

**The alignment unit is the `p:parallel` block, and you choose it.** Two sides join on
*exact URN equality* — `schema/JLPTEI-3.md`, `### Alignment`. So granularity is an
authoring decision, not a rendering one: two passages line up because you gave them their
own matching `@corresp`, and inside a block the columns drift and only resync at the next
block boundary. If a passage must start level with its translation, give it a URN of its
own. A `@corresp` repeated within one document breaks the join **silently**.

The compiler's own invariants are in `specs/COMPILER_SPECIFICATION.md`, `## Parallel
Compilation`.

**A rubric can sit on different rows in the two columns, and be correct.** A rubric whose
direction differs from the text around it cannot share a line with it, so it takes a line
of its own; in the facing column, where it does not cross, the same rubric runs in. The
result is one rubric on two different rows. That is the layout working, not failing.

Set `typography.instructions.from: both` when rubrics fall mid-passage rather than at
alignment boundaries — anything else needs them *at* boundaries, or a column ends up with
a rubric nowhere near the words it governs. `doc/typography.md`, ``## `instructions` ``.

**Column geometry means nothing by itself.** Which column is left tells you nothing about
which is read first; the two sides of an opening invert. The linearised order must
preserve *reading* order — `specs/BIRNBAUM_FROM_SCAN.md`, `## What the print does, that
the encoding has to carry`, which sets out the rest of these (asterisk means substitution,
simultaneous columns, bare day-names, a page turn mid-sentence).

**When order or geometry is in doubt, crop the block and look at it.** Inferring column
order from surrounding text is how a page gets read backwards. Cropping costs a minute.

## Verifying the rendered PDF

**Measure it; do not look at it.** A parallel-layout defect is a geometric fact — a row
nobody used, a rubric split across a blank line, a number inside its own column — and the
eye is unreliable about all three, in both directions. Recipes and the specific
measurements that have caught real defects are in `reference/measuring-the-pdf.md`.

One rule generalises past this project: **an assertion that cannot fail proves nothing.**
When a measurement passes, feed the pre-fix state back into it and confirm it goes red. A
check that silently measures nothing is worse than no check, because it is believed.

## Traps

**Encoding**
- **A division must earn its level.** Emit one only when it carries a `@corresp`, or when
  it groups several children that belong together (a heading with the passages under it).
  A division that names nothing and groups nothing — one URN-bearing `tei:div` holding a
  single bare `tei:div` holding the words — is a level for every reader and every
  stylesheet to see through, and the validator will not object to it. Words go directly
  inside the division that names them:

  ```xml
  <tei:div corresp="urn:x-opensiddur:text:prayer:modeh_ani">
    <tei:p>…</tei:p>          <!-- right: the naming division holds the words -->
  </tei:div>
  ```

  The rule it is easy to over-apply is that *a division holds content or subdivisions but
  never both*. That is real, and it bites when words would sit alongside a
  `j:conditional`; the fix there is to give those words a division **with a URN**, not an
  anonymous one. If you find yourself writing an unnamed wrapper, ask what it names or
  what it groups — and if the answer is neither, delete it.
- One instruction URN per distinct rubric *text*. Sharing a URN between rubrics that say
  different things makes the compiler print one where the other belongs.
- A page turn falls mid-sentence; `tei:pb` is valid inside `tei:p`.
- Slugs are unique per foundation page, not globally.
- Chapter and verse are separated by a colon.

**Reading**
- **Bands are reliable for consonants and not for points.** In the first 479 words the
  consonantal skeleton was never once wrong, and seven readings of the *pointing* had to
  be corrected before committing. At 3x a semicolon and a comma are one mark, a patach and
  a qamats differ by a tail a pixel or two long, and a dagesh in a wide letter is a dot the
  neighbouring letter can lend it.
- **So the transcription is the instrument that finds pointing errors, not a formality
  run afterwards.** Six of those seven were caught by the diff rather than by looking
  harder. Where it disagrees about a point, the presumption is a 12x crop — not that the
  reading stands. Where it flags a variant in a `{{נוסח}}` template it has been right
  every time.
- **Do not reach for "the scan cannot settle it" when what is missing is the word.** An
  `unresolved` verdict is a claim about the image, and it is the wrong one whenever the
  reading follows from knowing the text: a sin dot that will not resolve in the crop is
  still settled if the word is עָשָׂה. From inside the crop the two failure modes look
  identical, so ask what the word is before blaming the scan.
- **A meteg is decided on the image, one at a time, never in bulk.** On a single page the
  disputed metegs have fallen in both directions at once -- some the reading invented, some
  it missed -- so any rule of thumb gets half of them wrong. There is no shortcut here and
  the queue should keep surfacing them individually.
- **A comma read off a band at 3x is not evidence.** This print uses commas *and*
  semicolons, sometimes in one line, and at band magnification the semicolon's upper dot
  merges into the comma's body. Two of the first three misreadings on printed page 3 were
  exactly this. Where punctuation carries a sense break, crop it and look at 12x.
- **The same goes for a dagesh in a wide letter.** A mem or a bet with nothing in it reads
  at 3x much like one with a point, and a neighbouring letter's dagesh is easily annexed
  to it. Page 3's third catch was a dagesh in מאד that is not there; what looked like it
  belonged to the tav of the word before.
- **In verse, the lineation *is* the text.** The rule below is for prose. A poem's lines
  are its structure — Birnbaum's own footnote says Adon Olam "is composed of ten lines" —
  so keep them, and settle the whitespace differences they produce as `print` rather than
  carrying them to a person. Where such a poem is set in two columns, the columns are the
  two halves of one line: splitting on the column would give twenty lines and contradict
  the book's statement about itself.
- **Lift the Hebrew as paragraphs, not as printed lines.** `compare` counts a line break
  against a space as a whitespace difference, so a `hebrew/{printed}.txt` that preserves
  the print's line wrapping reports a difference per line and buries the real ones. The
  print's lineation belongs in `readings/`, which is prose about the page, not in the
  slice being diffed.
- **Correct the reading before committing it, and say so in `accuracy.md`.** A difference
  the image settles *for the transcription* vanishes from the tally once the reading is
  fixed, so the tally alone will always report zero misreadings. The prose is the only
  place the method's real error rate survives.

**A second reader**
- **The diff can only surface a disagreement, never a shared error.** Where the reading
  and the transcription are wrong in the same way, nothing in the comparison fires and the
  page looks settled. Both of the worst errors found on this book so far were of that kind,
  and neither could have come out of `compare`.
- **A blind second reader is the only thing that finds them.** Put a fresh agent on the
  page image with the two candidates and tell it plainly that both may be wrong. Asked that
  way it has returned "neither", correctly, on a word where the reading and the
  transcription agreed with each other and the print disagreed with both.
- **Its prose is not evidence, even when its answer is right.** Of fourteen justifications
  checked, one invented a corroborating detail outright — a "reddish ink cast" on the ink,
  where measurement puts ink and blank paper at the same R−B — and one described the right
  feature in the wrong place. Verify every claim that would change a file: crop the
  coordinates it gives, or measure the pixels it cites.
- **A high score on an easy page proves nothing.** A page whose answers follow from knowing
  Biblical Hebrew — metegs in stress positions, `אֶל־מֹשֶׁה` taking a maqqef — can be
  answered perfectly without reading the image at all. Test a second reader on a question
  where both candidates are wrong; that is the only kind that separates reading from
  priors.
- **Never let it decide.** Use it to triage and to escalate: it says "neither", it claims
  an absence, or it disagrees with the reading. Those three go to a person.

**The transcription**
- **A wall of consonantal differences is a boundary problem, not a finding.** A real
  disagreement about consonants is rare — none survived in the first two thousand words
  once the slices were right — so a page reporting them by the dozen has a section missing
  or duplicated on one side. The signature is a word-count gap plus that wall. Find the
  section before anyone looks at a crop; a passage may have no section of its own and live
  inside a variant one, named `א` or `ב` rather than for its words.
- **Resolve `{{נוסח}}`; never strip it.** The Wikisource foundation text marks the places
  its editors knew the print differs from what they set, and names Birnbaum's own reading
  in the template. Stripping it as markup throws away precisely what the comparison is
  for, *and* manufactures differences: a stripped template reads as a word the
  transcription dropped. Use
  `opensiddur.importer.birnbaum_scan.transcription.resolve`.
- **One of the four conventions inverts.** `{{נוסח|X|=בירנבוים|אחרים=Y}}` and
  `{{נוסח|X|=בירנבוים ועבו"י|אחרים=Y}}` make **X** the reading and `אחרים=` the variant.
  A rule that simply prefers a `בירנבוים=` parameter takes the wrong side of every one of
  them.
- **A `בירנבוים=` value is not always a word.** At least one is a sentence about how he
  sets two Torah portions. Substituting it drops a line of Hebrew prose into the middle of
  a prayer, where the diff then reports it as the print's own words.

**The apparatus**
- **A note keys to the nearest canonical URN.** An `#id` target resolves only inside the
  one file that declares it — `refdb.get_references_to` scopes id lookups by project *and*
  file name — so an apparatus in its own file can reach the text only by URN. That is also
  what lets one edition's notes be swapped or combined with another's.
- **Where the lemma falls mid-paragraph, give the phrase a `tei:seg` with its own URN.**
  Never reach for a `tei:anchor` to place a note more precisely; the seg is what the
  alignment of the two columns wants anyway.
- **Set `annotations:` in the settings, or no standoff note exists.** It defaults to
  empty, and an unset apparatus is not an error — the compile simply comes out with no
  notes and says nothing about it.
- **A note attached to a parallel text is found while compiling both columns.** Both sides
  realise the same URNs, which is what makes them parallel, so the apparatus prints twice
  per opening unless each column drops the projects that are themselves columns. Narrowing
  only the facing column does not fix it: the primary column still holds the configured
  list, and naming the apparatus project is that list's whole purpose.

**Attribution**
- The reading is ours. A transcription used as a check is not a source, and the people who
  made it are not this text's transcribers.
- The author of the book gets no `respStmt` — he is a source. `schema/JLPTEI-3.md`,
  `#### Contributors and contributor URNs`.
- Every `opensiddur.org` contributor URN must be registered in
  `specs/urn_registry/contributor.jsonl`; this is validated, and an unregistered one is a
  typo that credits a different person.

**Tooling**
- Never run the test suite while a build is running: both use the reference database at `database/reference.db`, and
  the collision shows up as an unrelated test failing.
- Refresh `refdb` for the project directory you are building, or sources and licences
  quietly come out thinner than they should — the compiled XML is identical either way, so
  nothing warns you.
- `--` inside an XML comment is illegal, and in `opensiddur/exporter/tex/reledmac.xslt` it fails *every*
  transform-based test at once, which reads as catastrophe rather than typo. Use an em
  dash.
- A comment that loses its opening `<!--` is still well-formed XML: the prose becomes a
  text node and lands in the LaTeX preamble. `TestPreambleIsAllTeX` guards this.

## Where things are written down

| Document | Covers |
|---|---|
| `specs/BIRNBAUM_FROM_SCAN.md` | The procedure end to end, and what this print does that the encoding must carry |
| `schema/JLPTEI-3.md` | The schema: alignment, contributors, conditionals, transclusion, URN scope |
| `specs/COMPILER_SPECIFICATION.md` | Transclusion, conditionals, parallel-compilation invariants |
| `doc/typography.md` | Every typography setting, including `parallel` and `instructions` |
| `doc/exporter-settings.example.yaml` | A complete annotated settings file |
| `AGENTS.md` | Repository layout, JLPTEI authoring rules, testing conventions |
| `specs/birnbaum_scan/accuracy.md` | How far one transcription stood from this print, measured |
| `sourcetexts`, `sources/birnbaum_siddur/scan_reading/` | The reading itself, page by page |

`schema/jlptei.odd.xml` is authoritative where the prose disagrees with it. Run the
validator.
