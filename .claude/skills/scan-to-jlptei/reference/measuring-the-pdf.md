# Measuring a rendered PDF

Load this shared subsection when compiling and verifying output. Load the selected
scan subsection for evidence about its typography and historical defect examples.

Keep the emitted TeX with `--tex-output`: it helps explain a defect but cannot prove
where text lands. Use `pdftotext -bbox` for word boxes and `mutool draw -F stext` for
glyph coordinates. Derive row advances, column spans, header exclusions, and baseline
clustering tolerances from the current output’s typography, not another scan’s values.

## Check observable behavior

- At shared semantic alignment boundaries, corresponding passages begin on the same
  row. Inside a block, verse and prose can legitimately drift. Check the boundary,
  not arbitrary words within it.
- Each rubric’s own lines are contiguous. A rubric crossing language direction needs
  explicit direction wrappers; different line counts across columns can be correct.
- Margin line numbers lie outside text columns and restart according to the selected
  settings. Distinguish inline verse numbers by geometry, not an integer regex.
- Every requested apparatus note appears, with intended occurrence count and anchor.
  Use sufficiently distinctive phrases; short fingerprints can match unrelated text.
- Expanded forms appear only in expanded output; documentary cues remain in the
  documentary output. Check exact repeated-passage boundaries for accidental extras.
- Hebrew glyph runs read right to left and Latin runs left to right, including
  mixed-language rubrics, labels, catchwords and footnotes. Extractor logical text
  can conceal reversed visual order. Sort glyphs by their actual x coordinates.

The shared `python -m opensiddur.importer.scan.pdf_direction PDF TEX --control`
checks Hebrew glyph direction against source n-grams. It must examine nonzero runs;
its reversed control must flag failures. Also inspect specific Latin runs by x order.

## Avoid misleading measurements

- RTL starts at the right edge, not a word’s `xMin`. Measure whole-line extents.
- Extractors can attach a margin number to a text line. Separate it by geometry.
- Do not apply column heuristics to full-width metadata, front matter or licence pages.
- Match balanced braces when inspecting TeX macro arguments; a fixed window or
  one-line capture can silently inspect the wrong content.
- Pagination changes after a fix. Match content, not page number, for before/after
  comparisons. Isolate a real failing construct when geometric behavior is sensitive
  to content lengths.
- Counts of alignment blocks cannot prove that their words actually render. Verify
  presence as well as geometry, especially paragraphs starting with brackets, which
  TeX can consume as optional macro arguments.
- A passing check proves nothing unless a deliberately broken control fails. Report
  what was measured, the sample size, thresholds, and remaining limitations.
