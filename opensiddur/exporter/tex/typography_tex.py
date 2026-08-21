""" Translating typography settings into LuaLaTeX.

``opensiddur/exporter/typography.py`` describes how a document should look in
renderer-agnostic terms. This module turns that description into TeX for the
reledmac pipeline. All the TeX is here; none of it is in the settings models,
and none of it is in a settings file.

Two products come out of a :class:`TypographyConfig`:

``documentclass_options`` — the bracketed options on ``\\documentclass``, which
have to be there and nowhere else.

``build_typography_preamble`` — a block of ``\\renewcommand`` and ``\\setlength``
that ``reledmac.xslt`` emits *after* all of its own definitions. The stylesheet
keeps every default it ever had; this block overrides them. So a settings file
that says nothing produces an empty block and, with it, exactly the document the
exporter produced before any of this existed.

**A directive is emitted only for a setting the user actually wrote.** Not for
one that merely equals its default. Some of the stylesheet's behaviour is
contextual — line numbers sit in the outer margin in a parallel document and
wherever reledmac puts them otherwise — and no single default value can stand
for that. Keying on what was written keeps the untouched cases untouched.
"""

from __future__ import annotations

from typing import Optional

from opensiddur.exporter.tex.escape import escape_tex
from opensiddur.exporter.typography import (
    Alignment,
    ChapterStart,
    ColumnPosition,
    ConditionalBlock,
    FontStyle,
    FontVariant,
    FontWeight,
    HEBREW_FAMILY,
    LATIN_FAMILY,
    NamedSize,
    NoteAnchor,
    Numerals,
    Orientation,
    PaperType,
    ParallelLayout,
    Sides,
    TextStyle,
    TypographyConfig,
    Visibility,
    resolve_font,
)


# ---------------------------------------------------------------------------
# Size and style tokens
# ---------------------------------------------------------------------------

# The named ladder, in the order it is documented. LaTeX's size commands are a
# ten-step scale whose steps are roughly 1.2x, which is where the ladder's shape
# comes from; each name is pinned to one step so that a document's sizes stay
# proportional when its base size changes.
_NAMED_SIZE_COMMANDS: dict[NamedSize, str] = {
    NamedSize.XXX_SMALL: r"\tiny",
    NamedSize.XX_SMALL: r"\scriptsize",
    NamedSize.X_SMALL: r"\footnotesize",
    NamedSize.SMALL: r"\small",
    NamedSize.NORMAL: r"\normalsize",
    NamedSize.LARGE: r"\large",
    NamedSize.X_LARGE: r"\Large",
    NamedSize.XX_LARGE: r"\LARGE",
    NamedSize.XXX_LARGE: r"\huge",
    NamedSize.XXXX_LARGE: r"\Huge",
}

_WEIGHT_COMMANDS = {FontWeight.NORMAL: r"\mdseries", FontWeight.BOLD: r"\bfseries"}
_SHAPE_COMMANDS = {FontStyle.NORMAL: r"\upshape", FontStyle.ITALIC: r"\itshape"}
_VARIANT_COMMANDS = {FontVariant.NORMAL: "", FontVariant.SMALL_CAPS: r"\scshape"}


def _size_command(size: Optional[str], line_spacing: float) -> str:
    """The TeX command that selects a size.

    A named size is one of the ten scale commands. An absolute length needs an
    explicit baseline too, since ``\\fontsize`` sets both; the conventional 1.2x
    leading is scaled by the document's line spacing so that a role given an
    exact size still respects ``paragraphs.line_spacing``.
    """
    if size is None:
        return ""
    if size in _NAMED_SIZE_COMMANDS:
        return _NAMED_SIZE_COMMANDS[NamedSize(size)]
    value, unit = _split_length(size)
    baseline = value * 1.2 * line_spacing
    return rf"\fontsize{{{_format_number(value)}{unit}}}{{{_format_number(baseline)}{unit}}}\selectfont"


def _split_length(length: str) -> tuple[float, str]:
    for position, character in enumerate(length):
        if character.isalpha():
            return float(length[:position]), length[position:]
    raise ValueError(f"length without a unit: {length!r}")  # pragma: no cover


def _format_number(value: float) -> str:
    """Trim a float to something TeX reads cleanly: 12.0 -> 12, 14.4 -> 14.4."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _font_command(family: Optional[str]) -> str:
    """The command that selects a declared family.

    ``latin`` is the document's main font, so selecting it is just returning to
    the normal font; ``hebrew`` is polyglossia's, which the stylesheet declares.
    Anything else is a family this module declared, named after its key.
    """
    if family is None:
        return ""
    if family == LATIN_FAMILY:
        return r"\normalfont"
    if family == HEBREW_FAMILY:
        return r"\hebrewfont"
    return "\\" + _family_macro_name(family)


def _family_macro_name(family: str) -> str:
    """A TeX control-sequence name for a user-declared family key.

    Control sequences are letters only, so digits, hyphens and underscores in
    the key are dropped and each word is capitalised: ``note-sans`` becomes
    ``OSfontNoteSans``.
    """
    words = "".join(character if character.isalnum() else " " for character in family)
    return "OSfont" + "".join(word.capitalize() for word in words.split())


def style_tokens(style: TextStyle, line_spacing: float = 1.0) -> str:
    """The font-switching commands for a style, in the order TeX wants them.

    The font comes first because it may reset the shape and series, then the
    size, then the attributes that survive a size change.
    """
    return "".join(
        (
            _font_command(style.font),
            _size_command(style.size, line_spacing),
            _WEIGHT_COMMANDS.get(style.weight, "") if style.weight else "",
            _SHAPE_COMMANDS.get(style.style, "") if style.style else "",
            _VARIANT_COMMANDS.get(style.variant, "") if style.variant else "",
        )
    )


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

# Two ways to align, because two contexts.
#
# Anything that can appear inside a reledmac \pstart is aligned with balanced
# \hfill inside the line. reledmac captures numbered text one \par-delimited
# line at a time, so a \par inside a group escapes that capture and, under
# reledpar's \Columns, lands outside its column; and a \parbox sizes itself from
# \linewidth, which is wider than a reledpar column. Fill glue works against the
# current measure, so it is correct in single-text and in either column.
_INLINE_ALIGNMENT: dict[Alignment, tuple[str, str]] = {
    Alignment.CENTER: (r"\mbox{}\hfill", r"\hfill\mbox{}"),
    Alignment.LEFT: ("", r"\hfill\mbox{}"),
    Alignment.RIGHT: (r"\mbox{}\hfill", ""),
    Alignment.JUSTIFY: ("", ""),
}

# Title-page material is set outside all numbering, so it can use real
# paragraph alignment and get proper line breaking.
_BLOCK_ALIGNMENT: dict[Alignment, str] = {
    Alignment.CENTER: r"\centering",
    Alignment.LEFT: r"\raggedright",
    Alignment.RIGHT: r"\raggedleft",
    Alignment.JUSTIFY: "",
}


def _inline_aligned(style: TextStyle, content: str) -> str:
    before, after = _INLINE_ALIGNMENT[style.align or Alignment.JUSTIFY]
    return before + content + after


def _vspace(length: Optional[str]) -> str:
    return rf"\vspace{{{length}}}" if length else ""


def _block_paragraph(style: TextStyle, body: str, line_spacing: float) -> str:
    """A centred (or otherwise aligned) paragraph with space around it."""
    alignment = _BLOCK_ALIGNMENT[style.align or Alignment.JUSTIFY]
    tokens = style_tokens(style, line_spacing)
    return (
        _vspace(style.space_before)
        + "{"
        + alignment
        + r"\normalfont"
        + tokens
        + " "
        + body
        + r"\par}"
        + _vspace(style.space_after)
    )


# ---------------------------------------------------------------------------
# Document class options
# ---------------------------------------------------------------------------


def documentclass_options(config: TypographyConfig) -> str:
    """The options for ``\\documentclass[...]{book}``.

    Only what the class itself has to be told: everything else is a package
    option or a declaration, and can be set later in the preamble where it is
    easier to reason about. ``twoside`` and ``openright`` are the class's own
    defaults and are left unsaid, so an unconfigured document keeps the exact
    option list it always had.
    """
    page = config.page
    options = [page.base_font_size.value]
    if page.paper is not PaperType.CUSTOM:
        options.append(page.paper.value)
    if page.sides is Sides.ONE:
        options.append("oneside")
    if page.chapter_start is ChapterStart.ANY:
        options.append("openany")
    return ",".join(options)


# ---------------------------------------------------------------------------
# Preamble sections
# ---------------------------------------------------------------------------


def _font_declaration(command: str, options: str, names: list[str]) -> list[str]:
    """Declare a font family, falling back through the chain if need be.

    When fontconfig can tell us which of the names is installed, the declaration
    names it outright. When it cannot — no fontconfig on this machine — the
    chain is emitted as nested ``\\IfFontExistsTF`` so TeX makes the same choice
    at compile time. The chain is known to contain an installed font either way:
    settings validation refuses one that does not.
    """
    resolved = resolve_font(names)
    if resolved is not None:
        return [f"{command}{options}{{{resolved}}}"]

    lines: list[str] = []
    for depth, name in enumerate(names[:-1]):
        lines.append("  " * depth + rf"\IfFontExistsTF{{{name}}}{{")
        lines.append("  " * (depth + 1) + f"{command}{options}{{{name}}}")
        lines.append("  " * depth + "}{")
    lines.append("  " * (len(names) - 1) + f"{command}{options}{{{names[-1]}}}")
    lines.extend("  " * depth + "}" for depth in reversed(range(len(names) - 1)))
    return lines


# Hebrew faces in common use have no bold companion, so \bfseries would silently
# do nothing and a bold heading would be indistinguishable from body text.
# BoldFont={*} with AutoFakeBold synthesizes one. HarfBuzz shaping is what gets
# vowels and cantillation placed correctly.
_HEBREW_FONT_OPTIONS = "[Renderer=HarfBuzz,Script=Hebrew,BoldFont={*},AutoFakeBold=2]"


def _fonts_section(config: TypographyConfig) -> list[str]:
    lines: list[str] = []
    for family, spec in sorted(config.fonts.items()):
        if family in (LATIN_FAMILY, HEBREW_FAMILY) and family not in config.declared_fonts:
            # The stylesheet already declares these, with the same chain.
            continue
        if family == LATIN_FAMILY:
            lines.extend(_font_declaration(r"\setmainfont", "", spec.names))
        elif family == HEBREW_FAMILY:
            # \hebrewfont already exists — the stylesheet declared it — so this
            # has to renew rather than declare.
            lines.extend(
                _font_declaration(r"\renewfontfamily\hebrewfont", _HEBREW_FONT_OPTIONS, spec.names)
            )
            lines.append(r"\let\hebrewfontsf\hebrewfont")
        else:
            lines.extend(
                _font_declaration(
                    "\\newfontfamily\\" + _family_macro_name(family), "", spec.names
                )
            )
    return lines


def _geometry_section(config: TypographyConfig) -> list[str]:
    """Page size and margins, as ``geometry`` options.

    The stylesheet loads ``geometry`` with no options at all, so an unconfigured
    document gets the document class's own margins. Only what was asked for is
    said here.
    """
    page = config.page
    options: list[str] = []
    if page.paper is PaperType.CUSTOM:
        options.append(f"paperwidth={page.width}")
        options.append(f"paperheight={page.height}")
    if page.orientation is Orientation.LANDSCAPE:
        options.append("landscape")

    margins = page.margins
    # inner/outer are geometry's names for the binding and fore edges, and it
    # only understands them on a two-sided document. On a one-sided one they are
    # simply the left and right margins.
    two_sided = page.sides is Sides.TWO
    for name, option in (
        ("top", "top"),
        ("bottom", "bottom"),
        ("inner", "inner" if two_sided else "left"),
        ("outer", "outer" if two_sided else "right"),
        ("binding_offset", "bindingoffset"),
    ):
        value = getattr(margins, name)
        if name in margins.model_fields_set and value is not None:
            options.append(f"{option}={value}")

    return [rf"\geometry{{{','.join(options)}}}"] if options else []


def _paragraph_section(config: TypographyConfig) -> list[str]:
    paragraphs = config.paragraphs
    written = paragraphs.model_fields_set
    lines: list[str] = []
    if "indent" in written:
        lines.append(rf"\setlength{{\parindent}}{{{paragraphs.indent}}}")
    if "spacing" in written:
        lines.append(rf"\setlength{{\parskip}}{{{paragraphs.spacing}}}")
    if "line_spacing" in written:
        lines.append(rf"\linespread{{{_format_number(paragraphs.line_spacing)}}}\selectfont")
    if "alignment" in written:
        alignment = _BLOCK_ALIGNMENT[paragraphs.alignment]
        # \AtBeginDocument because the raggedness has to survive the class's own
        # \normalfont setup, and because \raggedright in a preamble is a no-op.
        lines.append(rf"\AtBeginDocument{{{alignment}}}" if alignment else "")
    return [line for line in lines if line]


# Each role, the macro that renders it, and how that macro is built. The
# stylesheet defines every one of these with the same shape, so overriding one
# is a matter of substituting the style's tokens for the hardcoded ones.
def _styles_section(config: TypographyConfig) -> list[str]:
    styles = config.styles
    spacing = config.paragraphs.line_spacing
    written = styles.model_fields_set
    lines: list[str] = []

    def tokens(style: TextStyle) -> str:
        return style_tokens(style, spacing)

    def emit(role: str, definition_of) -> None:
        if role in written:
            lines.append(definition_of(getattr(styles, role)))

    # Body text has no macro of its own; the stylesheet applies \OSBodyStyle at
    # the start of the document, where it is in force for everything.
    emit("body", lambda s: rf"\renewcommand{{\OSBodyStyle}}{{{tokens(s)}}}")

    # Headings: plain paragraph content inside a \pstart, hence inline alignment.
    for role, macro in (
        ("heading1", r"\OSheadA"),
        ("heading2", r"\OSheadB"),
        ("heading3", r"\OSheadC"),
        ("heading4", r"\OSheadD"),
    ):
        emit(
            role,
            lambda s, macro=macro: rf"\renewcommand{{{macro}}}[1]{{"
            + _inline_aligned(s, r"{\normalfont" + tokens(s) + " #1}")
            + "}",
        )

    # Title page: set outside all numbering, so real paragraphs are safe.
    for role, macro in (
        ("title_main", r"\OSTitleMain"),
        ("title_sub", r"\OSTitleSub"),
        ("title_alt", r"\OSTitleAlt"),
        ("byline", r"\OSByline"),
        ("edition", r"\OSDocEdition"),
        ("imprint", r"\OSDocImprint"),
        ("epigraph", r"\OSEpigraph"),
        ("imprimatur", r"\OSImprimatur"),
        ("title_page_block", r"\OSTitlePageBlock"),
    ):
        emit(
            role,
            lambda s, macro=macro: rf"\renewcommand{{{macro}}}[1]{{"
            + _block_paragraph(s, "#1", spacing)
            + "}",
        )

    # Verse and chapter numbers force LTR: digits laid out in an RTL context
    # come out reversed, so 50 would read 05.
    emit(
        "verse_number",
        lambda s: r"\renewcommand{\vno}[1]{\textsuperscript{{\textdir TLT"
        r"\selectlanguage{english}" + tokens(s) + r"#1}}\,}",
    )
    emit(
        "chapter_number",
        lambda s: r"\renewcommand{\chno}[1]{{" + tokens(s)
        + r"{\textdir TLT\selectlanguage{english}#1}}\,}",
    )
    emit(
        "citation",
        lambda s: r"\renewcommand{\OScitation}[1]{"
        + _inline_aligned(s, r"{\normalfont" + tokens(s) + " #1}")
        + "}",
    )
    emit(
        "aliyah",
        lambda s: r"\renewcommand{\OSaliyah}[1]{{" + tokens(s) + r"[#1]}\,}",
    )
    emit(
        "parsha",
        lambda s: r"\renewcommand{\OSParsha}[1]{{\normalfont" + tokens(s) + r" #1}\quad}",
    )
    emit(
        "instruction",
        lambda s: r"\renewcommand{\instructionnote}[1]{{" + tokens(s) + " #1}}",
    )
    emit("note", lambda s: r"\renewcommand{\notenote}[1]{{" + tokens(s) + " #1}}")
    # styles.line_number is emitted by _line_numbers_section: the style and
    # the numeral system write the same macro, so they have to be combined.
    emit(
        "section_separator",
        lambda s: r"\renewcommand{\OSSectionSeparatorStyle}[1]{"
        + _block_paragraph(s, "#1", spacing)
        + "}",
    )
    return lines


def _note_mark_tex(style: TextStyle, anchor: NoteAnchor, spacing: float) -> list[str]:
    """The in-text anchor and the mark repeated where the note is printed.

    ``\\OSInterlinearNotemark`` keeps its name whichever anchor is chosen: it is
    what the stylesheet emits, and the setting decides only what it does.
    """
    # The stylesheet sets note marks in a sans face so they read as editorial
    # apparatus rather than as part of the text. Keep that unless the settings
    # name a font of their own — changing the anchor should not silently change
    # the face too.
    tokens = (r"\sffamily" if style.font is None else "") + style_tokens(style, spacing)
    if anchor is NoteAnchor.INTERLINEAR:
        # Raised, zero-width and centred on the anchor, so the mark sits in the
        # interlinear band and the text it annotates is not respaced — which is
        # what keeps two sides of a parallel text aligned.
        body = (
            r"\leavevmode\hbox to 0pt{\hss{\textdir TLT\raisebox{1.5ex}"
            r"{{\selectlanguage{english}\kern0.05em\normalfont"
            + tokens
            + r" #1\kern0.05em}}}\hss}"
        )
    elif anchor is NoteAnchor.SUPERSCRIPT:
        body = (
            r"\textsuperscript{{\textdir TLT\selectlanguage{english}\normalfont"
            + tokens
            + " #1}}"
        )
    else:
        body = r"{\textdir TLT\selectlanguage{english}\normalfont" + tokens + " #1}"
    return [
        r"\renewcommand{\OSInterlinearNotemark}[1]{%",
        "  " + body + "%",
        "}",
        r"\renewcommand{\OSFootnotemark}[1]{%",
        r"  {\textdir TLT\selectlanguage{english}\normalfont" + tokens + r" #1}\space",
        "}",
    ]


def _notes_section(config: TypographyConfig) -> list[str]:
    notes = config.notes
    lines: list[str] = []
    if "note_mark" in config.styles.model_fields_set or "anchor" in notes.model_fields_set:
        lines.extend(
            _note_mark_tex(
                config.styles.note_mark, notes.anchor, config.paragraphs.line_spacing
            )
        )
    return lines


def _line_numbers_section(config: TypographyConfig, has_parallel: bool) -> list[str]:
    line_numbers = config.line_numbers
    written = line_numbers.model_fields_set
    lines: list[str] = []
    if not line_numbers.enabled:
        # reledmac's own switch, the one \skipnumbering sets for a single
        # paragraph. Setting it in the preamble applies it to all of them: the
        # numbering machinery still runs, so cross-references and the apparatus
        # are unaffected, but no number is printed. Nothing else in this section
        # would have anything to configure.
        return [r"\numberlinefalse"]
    if "unit" in written:
        lines.append(rf"\lineation{{{line_numbers.unit.value}}}")
    if "increment" in written:
        lines.append(rf"\linenumincrement{{{line_numbers.increment}}}")
        if has_parallel:
            lines.append(rf"\linenumincrementR{{{line_numbers.increment}}}")
    if "first" in written:
        lines.append(rf"\firstlinenum{{{line_numbers.first}}}")
        if has_parallel:
            lines.append(rf"\firstlinenumR{{{line_numbers.first}}}")
    if "margin" in written:
        margin = line_numbers.margin.value
        lines.append(rf"\linenummargin{{{margin}}}")
        if has_parallel:
            lines.append(rf"\linenummarginR{{{margin}}}")
    if "separation" in written:
        lines.append(rf"\setlength{{\linenumsep}}{{{line_numbers.separation}}}")
    if "numerals" in written or "line_number" in config.styles.model_fields_set:
        lines.extend(_line_number_format_tex(config, has_parallel))
    return lines


def _line_number_format_tex(config: TypographyConfig, has_parallel: bool) -> list[str]:
    """How a line number is set.

    The macro is ``\\linenumrep``, not ``\\linenumberstyle``: the latter is a
    declaration whose only job is to define the former, and reledmac calls it
    once, as it loads. Redefining it afterwards has no effect at all.

    Hebrew numerals are letters, so unlike digits they belong in the surrounding
    direction and need no left-to-right wrapper. Digits do: laid out in an RTL
    context they come out reversed, 50 reading as 05.
    """
    tokens = style_tokens(config.styles.line_number, config.paragraphs.line_spacing)
    if config.line_numbers.numerals is Numerals.HEBREW:
        body = tokens + r"\hebrewnumeral{#1}"
    else:
        body = r"\textdir TLT\selectlanguage{english}" + tokens + r"\@arabic{#1}"
    # \@arabic is internal; the \hbox keeps the direction and language switches
    # from leaking into reledmac's aux-file writes.
    lines = [r"\makeatletter", r"\renewcommand*{\linenumrep}[1]{\hbox{" + body + "}}"]
    if has_parallel:
        lines.append(r"\renewcommand*{\linenumrepR}[1]{\hbox{" + body + "}}")
    lines.append(r"\makeatother")
    return lines


def _markers_section(config: TypographyConfig) -> list[str]:
    markers = config.markers
    written = markers.model_fields_set
    lines: list[str] = []
    if "section_separator" in written:
        separator = escape_tex(markers.section_separator)
        lines.append(
            r"\renewcommand{\OSSectionSeparator}{"
            + (rf"\OSSectionSeparatorStyle{{{separator}}}" if separator else "")
            + "}"
        )
    if "verse_numbers" in written and markers.verse_numbers is Visibility.HIDDEN:
        lines.append(r"\renewcommand{\vno}[1]{}")
    if "chapter_numbers" in written and markers.chapter_numbers is Visibility.HIDDEN:
        lines.append(r"\renewcommand{\chno}[1]{}")

    conditional = markers.conditional
    conditional_written = conditional.model_fields_set
    if "inline_open" in conditional_written:
        lines.append(
            r"\renewcommand{\OSCondStartInline}{{\bfseries"
            + escape_tex(conditional.inline_open)
            + "}}"
        )
    if "inline_close" in conditional_written:
        lines.append(
            r"\renewcommand{\OSCondEndInline}{{\bfseries"
            + escape_tex(conditional.inline_close)
            + "}}"
        )
    if conditional_written & {"block", "rule_width", "rule_thickness"}:
        width = _percent_of(conditional.rule_width, r"\linewidth")
        if conditional.block is ConditionalBlock.RULE:
            # A full-width box rather than \par-separated material: these rules
            # sit inside reledmac \pstart groups, where \par does not reliably
            # break the line.
            lines.append(
                r"\renewcommand{\OSCondRule}{\leavevmode\hbox to \linewidth{\hss\rule{"
                + width
                + "}{"
                + conditional.rule_thickness
                + r"}\hss}}"
            )
            lines.append(r"\renewcommand{\OSCondStartBlock}{\OSCondRule}")
            lines.append(r"\renewcommand{\OSCondEndBlock}{\OSCondRule}")
        elif conditional.block is ConditionalBlock.BRACKETS:
            lines.append(r"\renewcommand{\OSCondStartBlock}{\OSCondStartInline}")
            lines.append(r"\renewcommand{\OSCondEndBlock}{\OSCondEndInline}")
        else:
            lines.append(r"\renewcommand{\OSCondStartBlock}{}")
            lines.append(r"\renewcommand{\OSCondEndBlock}{}")
    return lines


def _percent_of(percent: str, dimension: str) -> str:
    """``43%`` of ``\\textwidth`` is ``0.43\\textwidth``."""
    return _format_number(float(percent.rstrip("%")) / 100) + dimension


def _parallel_section(config: TypographyConfig, has_parallel: bool) -> list[str]:
    parallel = config.parallel
    written = parallel.model_fields_set
    if not has_parallel or parallel.layout is not ParallelLayout.PAIRS:
        # Column geometry exists only where there are two columns on one page.
        return []
    lines: list[str] = []
    if "column_width" in written:
        width = _percent_of(parallel.column_width, r"\textwidth")
        lines.append(rf"\setlength{{\Lcolwidth}}{{{width}}}")
        lines.append(rf"\setlength{{\Rcolwidth}}{{{width}}}")
    if "column_position" in written:
        lines.append(
            rf"\columnsposition{{{_COLUMN_POSITIONS[parallel.column_position]}}}"
        )
    return lines


_COLUMN_POSITIONS = {
    ColumnPosition.LEFT: "L",
    ColumnPosition.CENTER: "C",
    ColumnPosition.RIGHT: "R",
}


# ---------------------------------------------------------------------------
# The whole block
# ---------------------------------------------------------------------------


def build_typography_preamble(
    config: TypographyConfig, has_parallel: bool = False
) -> str:
    """Everything the settings ask for, as TeX, in preamble order.

    Returns the empty string when the settings ask for nothing, which leaves the
    stylesheet's own defaults untouched.

    ``has_parallel`` says whether the document has two aligned streams. Several
    reledpar declarations do not exist unless the package is loaded, and the
    package is loaded only for such a document, so emitting them unconditionally
    would break every other one.
    """
    sections = [
        ("Fonts", _fonts_section(config)),
        ("Page geometry", _geometry_section(config)),
        ("Paragraphs", _paragraph_section(config)),
        ("Text styles", _styles_section(config)),
        ("Notes", _notes_section(config)),
        ("Line numbers", _line_numbers_section(config, has_parallel)),
        ("Markers", _markers_section(config)),
        ("Parallel columns", _parallel_section(config, has_parallel)),
    ]
    lines: list[str] = []
    for title, section in sections:
        if section:
            lines.append(f"% --- {title} (typography settings) ---")
            lines.extend(section)
    return "\n".join(lines) + "\n" if lines else ""
