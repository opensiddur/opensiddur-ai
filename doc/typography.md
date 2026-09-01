# Typography settings

Everything about how an exported document looks. This is the `typography:` section of a
settings file, read by the output stage only; the linear-XML compiler ignores it.

**Every setting is optional and every default reproduces the output this exporter has always
produced.** A settings file with no `typography:` section, or one that sets a single key, gets
the same document it always got in every other respect.

**Invalid settings fail before anything is rendered.** Unknown keys, values outside a closed
list, malformed lengths and font chains with nothing installed are all errors naming the
offending key and its path. Nothing is silently ignored and nothing silently falls back —
a setting that was quietly dropped would leave a document missing what was asked for, with
nothing to say why.

Settings are renderer-agnostic: they describe the document, not the commands that typeset it.
There is no TeX in a settings file, and there is no place to put any.

```yaml
typography:
  page:
    paper: a5paper
    margins: {inner: 25mm, outer: 18mm}
  paragraphs:
    line_spacing: 1.3
  styles:
    heading1: {size: x-large, weight: bold, align: center}
    note: {size: 9pt, weight: normal}
  line_numbers:
    enabled: false
```

## Value types

| Type | Written as | Notes |
| --- | --- | --- |
| length | `12pt`, `1.5em`, `25mm`, `0.75in` | Units: `pt`, `bp`, `mm`, `cm`, `in`, `pc`, `em`, `ex`. `em` and `ex` are relative to the font in force where the length is used. |
| absolute length | `12pt`, `25mm` | The same without `em`/`ex`. Required where the length is itself defining a font size. |
| percentage | `43%` | Of the enclosing measure. |
| size | `x-large` or `10pt` | See the ladder below. |

### The size ladder

A named size follows `page.base_font_size`, so raising the document from 11pt to 12pt scales
every named size with it. An absolute length pins a role to an exact size regardless. Each
step of the ladder is roughly 1.2 times the one below it.

| Name | Relative size | | Name | Relative size |
| --- | --- | --- | --- | --- |
| `xxx-small` | smallest | | `large` | one step up |
| `xx-small` | | | `x-large` | |
| `x-small` | | | `xx-large` | |
| `small` | one step down | | `xxx-large` | |
| `normal` | the base size | | `xxxx-large` | largest |

## `fonts`

Named font families. Each is a **chain of names tried in order**; the first one installed on
the machine building the document is used. If none of them is installed, that is an error —
falling back to whatever the renderer would have picked produces a document that is quietly
not the one that was asked for, and for Hebrew it is usually one with no vowels or
cantillation. A bare string is shorthand for a one-name chain.

Two families always exist, because the exporter refers to them by role rather than by name:
`latin` for Latin-script text and `hebrew` for Hebrew-script text. Declaring one **replaces**
its default chain rather than extending it. You may declare families of your own and point a
style at them by name.

```yaml
typography:
  fonts:
    hebrew: ["Frank Ruehl CLM", "Ezra SIL", "SBL Hebrew", "FreeSerif"]   # the default chain
    latin: "Linux Libertine O"                                           # the default
    note-sans: ["DejaVu Sans"]                                           # your own
```

**Only a chain you write is checked.** The two defaults are not: a document that asked for
nothing must still export on a machine that does not have this project's house fonts, so the
renderer falls back for them on its own. Writing a chain down — even one whose names happen to
be the defaults — opts it into the check.

That makes a one-name chain a deliberate assertion: name a single font and a machine without it
fails the build rather than quietly substituting another. Give the chain a widely available last
resort, as the default `hebrew` chain ends in `FreeSerif`, if you would rather it degrade.

The check needs `fontconfig` (`fc-list`). On a machine without it the check is skipped and the
chain is handed to the renderer to resolve at build time instead.

## `page`

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `page.paper` | `a4paper` \| `letterpaper` \| `legalpaper` \| `a5paper` \| `b5paper` \| `executivepaper` \| `custom` | `letterpaper` | Sheet size. |
| `page.width` | absolute length | — | Sheet width. Required with `paper: custom`, an error otherwise. |
| `page.height` | absolute length | — | Sheet height. Same. |
| `page.orientation` | `portrait` \| `landscape` | `portrait` | |
| `page.sides` | `one` \| `two` | `two` | `two` mirrors margins and running heads between recto and verso. |
| `page.chapter_start` | `recto` \| `any` | `recto` | `recto` opens each book on a right-hand page, inserting a blank if needed. |
| `page.base_font_size` | `10pt` \| `11pt` \| `12pt` | `11pt` | The size named sizes are relative to. Only these three exist; anything else would silently become one of them. |

### `page.margins`

Every margin defaults to the document class's own, which is what the exporter produced before
margins were configurable. Margins are named for the **binding**, not for the page edge, so
`inner` and `outer` mean the same thing on a recto and a verso. On a one-sided document
`inner` is the left margin and `outer` the right.

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `page.margins.top` | length | class default | Space above the text block. |
| `page.margins.bottom` | length | class default | Space below the text block. |
| `page.margins.inner` | length | class default | Margin at the binding edge. |
| `page.margins.outer` | length | class default | Margin at the fore edge. |
| `page.margins.binding_offset` | length | class default | Added at the binding edge and taken off the fore edge, for the part of the page a binding swallows. |

## `paragraphs`

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `paragraphs.indent` | length | `0pt` | First-line indent. |
| `paragraphs.spacing` | length | `0.75em` | Vertical space between paragraphs, in addition to normal line spacing. Defaults to at least half a line so a new paragraph reads as distinct from an ordinary wrapped line. |
| `paragraphs.line_spacing` | number, 0.5–3.0 | `1.0` | Multiple of single spacing. Hebrew with vowels and cantillation needs more leading than unpointed text. |
| `paragraphs.alignment` | `justify` \| `left` \| `right` \| `center` | `justify` | |

## `styles`

The appearance of each kind of text the exporter distinguishes. Setting one changes only that
role; the rest keep their defaults.

### Style attributes

Every role takes the same eight keys. All are optional, and an omitted one leaves that aspect
as the surrounding text has it.

| Key | Type | Effect |
| --- | --- | --- |
| `font` | a family declared in `fonts` | Omit to let the text keep the font its script selects. |
| `size` | size | See the ladder above. |
| `weight` | `normal` \| `bold` | |
| `style` | `normal` \| `italic` | |
| `variant` | `normal` \| `small-caps` | |
| `align` | `left` \| `right` \| `center` \| `justify` | Physical positions on the page, so they mean the same in a Hebrew and an English stream. Block-level roles only. |
| `space_before` | length | Vertical space above. Block-level roles only. |
| `space_after` | length | Vertical space below. Block-level roles only. |

### Roles

| Role | Default | What it sets |
| --- | --- | --- |
| `styles.body` | inherits | Ordinary running text. |
| `styles.heading1` | `xx-large`, bold, centered | Top-level section heading. |
| `styles.heading2` | `x-large`, bold, centered | Second-level heading. |
| `styles.heading3` | `large`, bold, centered | Third-level heading. |
| `styles.heading4` | `normal`, bold, centered | Fourth-level heading; the deepest there is. |
| `styles.title_main` | `xxxx-large`, bold, centered, `1.5ex` after | The main title on the title page. |
| `styles.title_sub` | `x-large`, centered, `1.5ex` before | The subtitle. |
| `styles.title_alt` | `large`, centered, `1ex` after | An alternative title, usually the title in the other language. |
| `styles.byline` | `large`, centered, `3ex` before | The author/editor line. |
| `styles.edition` | centered, `2ex` before | The edition statement. |
| `styles.imprint` | centered, `4ex` before | The publisher/place/date block at the foot of the title page. |
| `styles.epigraph` | `small`, italic, centered, `2ex` before | An epigraph on the title page. |
| `styles.imprimatur` | `small`, italic, centered, `2ex` before | An imprimatur or approbation. |
| `styles.title_page_block` | centered | Any other paragraph on the title page. |
| `styles.citation` | italic, centered | A scriptural citation on a line of its own, naming where a reading begins or resumes. |
| `styles.parsha` | `large`, bold | A parsha name, run in at the head of the text it opens. |
| `styles.aliyah` | bold | An aliyah or maftir marker, inline at the verse it begins on. |
| `styles.verse_number` | inherits | The verse number at the start of each verse. |
| `styles.chapter_number` | `large`, bold | The chapter number, inline at the start of a chapter. |
| `styles.instruction` | bold | An instruction to the reader, in the note apparatus. |
| `styles.note` | bold | The text of an editorial note. |
| `styles.note_mark` | `xx-small` | The mark that anchors a note, in the text and where the note is printed. |
| `styles.line_number` | inherits | Marginal line numbers. |
| `styles.section_separator` | centered | The separator between unheaded sections. |

## `line_numbers`

Marginal line numbers, as a critical edition uses to cite a passage.

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `line_numbers.enabled` | boolean | `true` | When false no number is printed. The numbering machinery still runs, so cross-references and the apparatus are unaffected. |
| `line_numbers.unit` | `page` \| `section` | `page` | What numbering restarts at. |
| `line_numbers.increment` | integer ≥ 1 | `5` | Print a number every nth line. |
| `line_numbers.first` | integer ≥ 1 | `5` | The first line number printed, so the numbers run 5, 10, 15 rather than 1, 5, 10. |
| `line_numbers.margin` | `inner` \| `outer` \| `left` \| `right` | `outer` | `inner`/`outer` are relative to the binding; `left`/`right` are fixed. In a `pairs` parallel layout each column takes the nearer outer margin regardless, since the alternative is numbers in the gutter between the columns. |
| `line_numbers.separation` | length | `1em` | Space between the number and the text block. |
| `line_numbers.numerals` | `arabic` \| `hebrew` | `arabic` | |

## `notes`

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `notes.placement` | `footnote` \| `endnote` \| `none` | `footnote` | Where the text of a note is printed. `none` drops notes entirely, anchor and all, and is an error if a note style is also set — the two cannot both hold and the one that silently wins deletes the notes. |
| `notes.anchor` | `interlinear` \| `superscript` \| `inline` | `interlinear` | How the mark that points at a note is set. `interlinear` raises it above the line and gives it no width, so the text it annotates is not respaced — which is what keeps two sides of a parallel text aligned. |
| `notes.mark` | `numeric` \| `alpha` \| `roman` \| `symbol` | `numeric` | The series marks are drawn from. The symbol series has six members and repeats the symbol past the sixth, as a printed apparatus does. |

There is deliberately no setting for showing the *lemma* — the words a note is attached to,
repeated where the note is printed. A note anchors at a point rather than over a range, so
there are no such words: the apparatus entry's lemma is the mark itself, and printing it would
give "∗ ] ∗ the note text".

## `markers`

The small marks that structure a text without being part of it.

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `markers.section_separator` | text | `* * * *` | Printed between sections that carry no heading. An empty string leaves nothing but the space. |
| `markers.verse_numbers` | `shown` \| `hidden` | `shown` | |
| `markers.chapter_numbers` | `shown` \| `hidden` | `shown` | |

### `markers.conditional`

Only conditions the compiler could not decide survive into the output, so a marker means "say
this only if …", and the reader has to be able to see where the passage starts and stops.

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `markers.conditional.inline_open` | text | `[` | Opens a conditional run inside a paragraph. |
| `markers.conditional.inline_close` | text | `]` | Closes it. |
| `markers.conditional.block` | `rule` \| `brackets` \| `none` | `rule` | How a whole conditional paragraph is delimited. Brackets several lines apart do not read as a pair, hence the rule. |
| `markers.conditional.rule_width` | percentage | `25%` | Width of the rule, as a percentage of the measure. |
| `markers.conditional.rule_thickness` | length | `0.4pt` | |

## `parallel`

The geometry of a parallel-text layout.

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `parallel.layout` | `pairs` \| `pages` | `pairs` | `pairs` puts two columns on the same page; `pages` sets the texts on facing pages, which gives each a full measure and suits a long work. |
| `parallel.column_width` | percentage | `43%` | Width of each column as a percentage of the text block, in `pairs` layout. The two columns and the gap share 100%, so well under 50% each — the remainder leaves the outer margins room for line numbers. |
| `parallel.column_position` | `left` \| `center` \| `right` | `center` | Where the pair of columns sits in the text block, in `pairs` layout. |

**Which text goes on which side is not set here.** It is `parallel.column_order` in the
compiler section of the settings file — `primary_first` puts the primary stream on the left,
`primary_last` swaps them — because the compiler is what decides the order the streams are
emitted in.

## `table_of_contents`

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `table_of_contents.enabled` | boolean | `false` | Print a table of contents. |
| `table_of_contents.depth` | integer 1–4 | `4` | Heading levels shown. Independent of the PDF bookmark depth, which is always four levels deep. |

## `page_header` and `page_footer`

Running heads and feet. Empty by default, which leaves the document class's own page style
alone. Each takes either `all` — the same content on every page — or `odd` and/or `even` to
differentiate them; combining `all` with either is an error.

```yaml
typography:
  page_header:
    odd:
      left: "{book-title}"                                    # bare string = just text
      right: {text: "Page {page}", language: en}
    even:
      left: {text: "{page-hebrew}", language: he}
      center: {text: "Chapter {chapter-number}", language: en, if: "{chapter-number}"}
  page_footer:
    all:
      center: "{page}"
```

`left`, `center` and `right` are *physical* positions on the page, not logical ones: `left` is
the left edge whichever way the text runs. Each is either a bare string or a mapping with:

- `text` — the template.
- `language` — the slot's base direction, which decides the order its runs are laid out in,
  and the font for content that declares nothing else. Defaults to the document's own
  `xml:lang`; only Hebrew (`he`, `he-*`) versus everything else is distinguished. Every run
  carries its own direction inside that, so a mixed title like "רות RUTH" reads correctly in a
  slot of either direction and digits are never reversed.
- `if` — a second template. When it expands to nothing the whole position is dropped, literal
  text included, so `"Chapter {chapter-number}"` leaves no orphaned "Chapter" on a page before
  the first chapter.

Anything outside braces is literal text; `{{` and `}}` are literal braces. The codes are a
closed list, and an unrecognized one is a settings error:

| Code | Expands to |
| --- | --- |
| `{page}` | the page number as the document numbers it (roman in front matter) |
| `{page-hebrew}` | the page number in Hebrew numerals |
| `{document-title}` | the title from the TEI header, fixed for the whole document |
| `{book-title}` | the head of the enclosing `tei:div[@type='book']` |
| `{chapter-number}` | the `n` of the last `tei:milestone[@unit='chapter']` |
| `{chapter-number-hebrew}` | the same, in Hebrew numerals |
| `{head1}` … `{head4}` | the last heading at that level |
| `{section-title}` | the last heading at any level |
| `{book-title-alt}`, `{head1-alt}` … `{head4-alt}`, `{section-title-alt}` | the same, from the *second* parallel column |

Everything but `{page}`, `{page-hebrew}` and `{document-title}` names whatever was in force at
the *end* of the page, so a heading starting partway down a page names that page. The `-alt`
codes are what let a running head name the second language of a parallel volume; in a
non-parallel document they expand to nothing.

Title pages never carry a running head or foot, nor do the blank pages inserted to keep a
title page on a recto.

## How this reaches the renderer

`opensiddur/exporter/typography.py` holds the models above and knows nothing about any
renderer. `opensiddur/exporter/tex/typography_tex.py` turns a validated settings tree into a
block of LuaLaTeX, which `tex/reledmac.xslt` emits after all of its own definitions — so the
stylesheet keeps every default it ever had and the settings override them. A directive is
emitted only for a setting the file actually wrote, which is what keeps an unconfigured
document byte-for-byte what it was.

Adding a setting means adding a field to the model, a case to the emitter, a row to this
document, and a test. `opensiddur/tests/exporter/test_typography_doc.py` fails if the row is
missing.
