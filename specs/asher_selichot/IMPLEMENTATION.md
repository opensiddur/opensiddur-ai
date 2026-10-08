# Asher selichot encoding and reusable scan workflow

Issue: https://github.com/opensiddur/opensiddur-ai/issues/207

The skill entrypoint dynamically loads the selected edition subsection. Shared tools
accept explicit book profiles; Asher uses scan-based identity because both languages
repeat printed labels. Archive page labels remain candidates until image verified.

Current coverage: title n1/n2 and the first five complete days through n83/n84.
Daily scope files record image-verified boundaries; the first day ends at n51/n52. Readings are derived from these images; OCR and independent readings check
those readings. The source README records editorial additions and target ranges.

`readings.abbreviations` selects abbreviated (default) or expanded during compilation,
including inline transclusion. Schema adds expan; PDF emits the selected branch.
Documentary/expanded service roots reuse source modules; expanded adds the referenced
prayers in place of the concluding instruction. Expanded output also omits the
fulfilled refrain-repetition rubric; documentary output retains both instructions. Settings here are deliberately not
in release-book settings. Images and render artifacts stay in output/asher_selichot.

Acceptance: synthetic shared-tool and compiler tests; schema and URN validation;
page/language reverse check; paired PDF builds with direction, text, footnote and
reference-boundary checks; checks fail on broken controls; full regression suite.

## First-day continuation

The documentary `index.xml` entrypoints cover title n1/n2 and all first-day
text through Hebrew n51 / English n52. `first_day.xml` directly assembles independently named text modules by canonical
URN, retaining printed rubrics. It reuses the
original El Melekh, Vayaavor and Bemotzaei Menuhah modules at their source positions.

Canonical readings retain immutable scan-first fragments, source page identity,
complete bilingual prayer groups, printed rubrics and anchored footnotes. XML
verification compares each unit with its reading and checks source page order and
the final Kaddish boundary. Synthetic fixtures check crossed page breaks, repeated
footnote anchors, missing anchors, litanies and mixed-language closing instructions.
`first-day.yaml` renders the full documentary day; automatic releases remain
excluded. Independent Hebrew pointing review and the remaining book are pending.

## Piyyut invocation correction

Treat the shared אלהינו ואלהי אבותינו invocation as opening text in each
piyyut, together with its English translation. Preserve the Hebrew invocation as
an introductory line within `tei:lg` and the English within its prose paragraph;
remove the former heading heuristic. Record the distinctive following Hebrew
incipit in source metadata and URN labels, without adding a printed heading or
claiming a separately established formal title. Source words remain unchanged; reusable text identities use common names or distinctive incipits. The scan-specific skill and reverse verifier enforce this rule.

## Expanded complete first day and secondary-source settings

Generate documentary and expanded book entrypoints referencing the same bilingual
`first_day.xml` service assembly.
Conditional branches retain printed cues for documentary output and replace them
with unqualified target URNs when repetitions are present. Register bounded
repeat-range milestones within the two source prose prayers. Supply the poem’s
concluding prayers in a true conditional branch next to its printed conclusion cue. Add reusable Birnbaum Full Kaddish
`prayer:kaddish/shalem`, assembled from six edition-bound existing passages.
`default.yaml` selects the expanded book entrypoint `expanded.xml`, Asher-first primary priorities,
and Asher/Birnbaum English parallel priorities, outside release settings.

Parallel subcompilation must retain the remaining configured parallel projects as
fallback priorities rather than reducing its priority list to a singleton. Restore
priorities after the scope ends. Verify documentary branches against primary
readings after separately auditing expansion targets and branch polarity; compile
both views and check repeated-passage counts, omitted fulfilled cues, complete
Kaddish, source provenance, direction, footnotes and first-day boundary.

Marker-mode external transclusions must honor false conditional scopes before
resolving a target or emitting suspension markers. This is required for the
shared documentary modules to compile without a configured secondary source.
A regression fixture uses an absent target inside a false scope and checks that
the documentary text after the scope survives.

The generic conditional/fallback corrections and regression tests were merged in
opensiddur-ai PR #217. The apparatus paragraph-direction fix and tests were merged
separately in PR #218. The Asher code PR targets main.

The first-day PDF check also groups small Latin apparatus glyphs by font and
baseline across MuPDF’s fragmented lines. Reject decreasing x coordinates, and
reverse a complete note run as a failing control. The original PDF’s backwards
English explanation on page 9 fails this check. Source words and XML paragraph
language declarations are unchanged by the renderer correction.

The final Full Kaddish is first-day Selichot, never Ten Days of Repentance. Before
its transclusion, declare `asher:selichot/first_day=true` and the standard holiday
aggregate `aseret-ymei-tshuva=false`; close the declaration after the prayer.
This local source context overrides unrelated export defaults and restores them
afterward. A synthetic compilation fixture starts with the Ten Days aggregate
true, confirms the final addition is excluded, and verifies the caller’s setting
is restored. Reverse verification audits the declaration; PDF verification rejects
the Ten Days rubric and includes a deliberately injected failing control.


## Final-book module organization

Treat this work as the foundation of the final book. `index.xml` holds documentary
book metadata and both title pages; `expanded.xml` provides the expanded book view.
Both reference the same first-day service assembly. Independent prayers and piyyutim
live in named files, with source-independent URNs and publication `@project`
suffixes recording the edition. The printed first-day service retains its rubrics and directly transcludes those files. Ashrei and Half Kaddish are independent modules.

`identities.py` maps evidence IDs to semantic filenames and canonical registry
identities. Existing common prayer/part names take precedence; other texts use
incipits without claiming unverified formal titles. Repeated Ashamnu and scriptural
ranges point to reusable prayer identities. Active structured readings use
`refrain-and-prayers.json`; immutable original evidence is retained.

Remove artificial opening, preface, before-piyyut and closing subdivision files,
and the redundant expanded first-day assembly. Delete their obsolete URNs and
prune exactly these known generated files after replacement XML validates.
Internal reading batches do not define source divisions.

Reverse verification follows direct service references in source order, then checks
individual modules against the original reading units. It audits publication
identities, source boundaries and editorial context separately. Regenerate both
views, resolve URNs, and render both PDFs after the reorganization. The full book
and independent Hebrew pointing review remain pending; do not encode temporary
coverage status in canonical text identities.


## Second day and generated contents

Extend the existing book assemblies with the printed second-day range n51–n60,
ending before the third-day heading. Four new canonical incipit modules and one
second-day assembly per language preserve bilingual verse/prose structure and
seven English footnotes. Expand the source-verified opening, repeated verses,
three prayer pairs, closing range and secondary Full Kaddish; omit fulfilled
instructions. Both day headers must be top-level bookmarks above their pizmons.
All four local export settings enable a generated TOC through heading level two.
Reverse verification follows printed order, selects abbreviation branches and
checks footnotes and page boundaries separately from supplied text. The book PDF
checker uses outline destinations to scope legacy first-day checks and checks
second-day stanza alignment, footnote occurrences, expansion branches and
bookmark hierarchy with failing controls.


## Third-day continuation

Extend both book entrypoints through n67/n68, before the fourth-day heading.
Follow verified printed page order 29, 30, 31, 32, 33: the Archive openings for
31 and 32 are swapped. Preserve actual facsimile identities and bilingual
pairing separately. Three new reusable poem modules and `third_day.xml` bring
the projects to 59 files per language (54 independent texts, five assemblies).
Generalize numbered-day authoring and reverse checks, retaining day-two wrappers.
Preserve Hebrew-only verse instructions and all eight English notes. Use six
stanza alignment ranges, four refrain choices and one complete-opening choice
for Shahar qamti. Expanded cues use the verified existing ranges with a separate
third-day Kaddish declaration. Exclude fourth-day material.

Remove the first pizmon's miscategorized English running page header from the
body and contents while retaining source evidence and the Hebrew printed heading.
Synthetic checks exercise reordered page identities, closed day-specific scopes,
Hebrew-only rubric direction, and running-header exclusion. Render checks audit
day-three stanzas, notes, expansions and day boundaries with broken controls.
