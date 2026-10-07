# Asher selichot pilot and reusable scan workflow

Issue: https://github.com/opensiddur/opensiddur-ai/issues/207

The skill entrypoint dynamically loads the selected edition subsection. Shared tools
accept explicit book profiles; Asher uses scan-based identity because both languages
repeat printed labels. Archive page labels remain candidates until image verified.

Pilot: title n2; במוצאי מנוחה n31–32; dependency ranges אל מלך יושב and ויעבור
n23–26. All readings are from these images; OCR and independent readings only check
those readings. Source README records editorial expansions and transclusion scope.

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

The documentary `first_day.xml` entrypoints now cover title n1/n2 and all first-day
text through Hebrew n51 / English n52. Three additional modules per language
encode the preface, intervening selichot and closing prayers. They reuse the
original El Melekh, Vayaavor and Bemotzaei Menuhah modules at their source positions.

Canonical readings retain immutable scan-first fragments, source page identity,
complete bilingual prayer groups, printed rubrics and anchored footnotes. XML
verification compares each unit with its reading and checks source page order and
the final Kaddish boundary. Synthetic fixtures check crossed page breaks, repeated
footnote anchors, missing anchors, litanies and mixed-language closing instructions.
`first-day.yaml` renders the full documentary day; automatic releases remain
excluded. Independent Hebrew pointing review and the remaining book are pending.
