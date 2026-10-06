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
