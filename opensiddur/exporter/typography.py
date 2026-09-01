""" Typography settings: the user-facing description of how a document should look.

This module is deliberately renderer-agnostic. Nothing here knows about TeX —
sizes are a named ladder or a length with a unit, not ``\\LARGE``; a page has
``inner`` and ``outer`` margins, not ``\\geometry`` options. The translation into
one renderer's commands lives beside that renderer; for the PDF stage that is
``opensiddur/exporter/tex/typography_tex.py``.

Two rules shape the models:

*Every setting has a default, and the defaults reproduce the output the exporter
produced before any of this was configurable.* A settings file that omits the
``typography`` section, or any part of it, gets exactly what it got before.

*Invalid settings fail at load time, not in the renderer.* Every model forbids
unknown keys, every vocabulary is a closed enum, and lengths are pattern-checked,
so a typo names itself and its YAML path instead of surfacing as a LaTeX error
several minutes into a build — or, worse, as a silently wrong page.

The one part of the settings tree that lives elsewhere is
``page_header``/``page_footer``: their model and their TeX generator are a single
piece of logic, and both are in ``tex/running_heads.py``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    model_validator,
)

from opensiddur.exporter.tex.running_heads import RunningHeadConfig


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

# Units a length may carry. `em`/`ex` are relative to the font in force where the
# length is used, which is what makes a setting like `paragraphs.spacing: 0.5em`
# survive a change of base font size. The rest are absolute.
_LENGTH_PATTERN = r"^-?(?:\d+(?:\.\d+)?|\.\d+)(?:pt|bp|mm|cm|in|pc|em|ex)$"

Length = Annotated[
    str,
    StringConstraints(pattern=_LENGTH_PATTERN),
    Field(
        description=(
            "A length with a unit: pt, bp, mm, cm, in, pc, em or ex. "
            "em and ex are relative to the font in force."
        ),
    ),
]

# A font size given as a length must be absolute: a size in `em` would be
# relative to the size it is itself defining. Use a NamedSize for a size
# relative to the base.
_ABSOLUTE_LENGTH_PATTERN = r"^(?:\d+(?:\.\d+)?|\.\d+)(?:pt|bp|mm|cm|in|pc)$"

AbsoluteLength = Annotated[
    str,
    StringConstraints(pattern=_ABSOLUTE_LENGTH_PATTERN),
    Field(
        description=(
            "A positive length in an absolute unit: pt, bp, mm, cm, in or pc. "
            "Relative units are not allowed where the length defines a font size."
        ),
    ),
]

_PERCENT_PATTERN = r"^(?:\d+(?:\.\d+)?|\.\d+)%$"

Percent = Annotated[
    str,
    StringConstraints(pattern=_PERCENT_PATTERN),
    Field(description="A percentage of the enclosing measure, e.g. `43%`."),
]


class NamedSize(StrEnum):
    """ A font size relative to the document's base size.

    A named size follows ``page.base_font_size``, so raising the document from
    11pt to 12pt scales every heading with it. Use an absolute
    :data:`Length` instead when a role needs an exact size regardless.

    The ladder is symmetric around ``normal`` and each step is roughly 1.2x.
    """

    XXX_SMALL = "xxx-small"
    XX_SMALL = "xx-small"
    X_SMALL = "x-small"
    SMALL = "small"
    NORMAL = "normal"
    LARGE = "large"
    X_LARGE = "x-large"
    XX_LARGE = "xx-large"
    XXX_LARGE = "xxx-large"
    XXXX_LARGE = "xxxx-large"


FontSize = Union[NamedSize, AbsoluteLength]


class FontWeight(StrEnum):
    NORMAL = "normal"
    BOLD = "bold"


class FontStyle(StrEnum):
    NORMAL = "normal"
    ITALIC = "italic"


class FontVariant(StrEnum):
    NORMAL = "normal"
    SMALL_CAPS = "small-caps"


class Alignment(StrEnum):
    """ Horizontal alignment.

    ``left`` and ``right`` are physical positions on the page, so they mean the
    same thing in a Hebrew and an English stream; ``start``/``end`` semantics are
    deliberately not offered, because a bilingual document would need both at
    once and could not say so.
    """

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"


class Sides(StrEnum):
    """ Whether the document is printed on one or both sides of the leaf. """

    ONE = "one"
    TWO = "two"


class ChapterStart(StrEnum):
    """ Where a new book or chapter is allowed to begin. """

    RECTO = "recto"  # always on a right-hand page, inserting a blank if needed
    ANY = "any"


class Orientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class Numerals(StrEnum):
    ARABIC = "arabic"
    HEBREW = "hebrew"


class BaseFontSize(StrEnum):
    """ The document's base font size.

    Only these three are available: they are the sizes the underlying document
    class ships font-size tables for, and asking for anything else silently gets
    one of them. Set individual roles in ``styles`` for other sizes.
    """

    PT10 = "10pt"
    PT11 = "11pt"
    PT12 = "12pt"


class PaperType(StrEnum):
    """ Paper size.

    ``custom`` requires ``page.width`` and ``page.height``; every other value
    forbids them.
    """

    A4PAPER = "a4paper"
    LETTERPAPER = "letterpaper"
    LEGALPAPER = "legalpaper"
    A5PAPER = "a5paper"
    B5PAPER = "b5paper"
    EXECUTIVEPAPER = "executivepaper"
    CUSTOM = "custom"


class ParallelLayout(StrEnum):
    """ Parallel-text page layout.

    pages: facing pages — best for full critical editions.
    pairs: two columns on the same page — best for short documents.
    """

    PAGES = "pages"
    PAIRS = "pairs"


class LineationUnit(StrEnum):
    """ What line numbering counts within before restarting. """

    PAGE = "page"
    SECTION = "section"


class LineNumberMargin(StrEnum):
    """ Which margin line numbers sit in.

    ``inner``/``outer`` are relative to the binding and therefore swap between
    recto and verso; ``left``/``right`` are fixed physical positions.
    """

    INNER = "inner"
    OUTER = "outer"
    LEFT = "left"
    RIGHT = "right"


class NotePlacement(StrEnum):
    """ Where the text of a note is printed.

    footnote: at the foot of the page the note is anchored on.
    endnote:  collected at the end of the document.
    none:     notes are dropped entirely, anchor and all.
    """

    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    NONE = "none"


class NoteAnchor(StrEnum):
    """ How the mark that points at a note is set in the text.

    interlinear: raised into the space above the line, taking no width, so the
                 text it annotates is not respaced.
    superscript: an ordinary superscript attached to the preceding word.
    inline:      at full size on the baseline.
    """

    INTERLINEAR = "interlinear"
    SUPERSCRIPT = "superscript"
    INLINE = "inline"


class NoteMark(StrEnum):
    """ The series a note's mark is drawn from. """

    NUMERIC = "numeric"
    ALPHA = "alpha"
    ROMAN = "roman"
    SYMBOL = "symbol"


class ConditionalBlock(StrEnum):
    """ How a whole conditional paragraph is delimited.

    Only conditions the compiler could not decide survive into the output, so a
    marker means "say this only if ...", and a reader has to see where the
    passage starts and stops.
    """

    RULE = "rule"
    BRACKETS = "brackets"
    NONE = "none"


class Visibility(StrEnum):
    SHOWN = "shown"
    HIDDEN = "hidden"


class ColumnPosition(StrEnum):
    """ Where the pair of columns sits within the text block. """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------


class ForbidExtra(BaseModel):
    """ Base for every settings model: an unknown key is an error.

    Silently ignoring a key the user wrote means the setting they asked for is
    simply absent from the output, with nothing to say why. Forbidding extras
    turns every typo into a message that names the key and its path.
    """

    model_config = ConfigDict(extra="forbid")


class FontFamily(ForbidExtra):
    """ A font, given as a chain of names tried in order.

    The chain exists because the faces this project sets Hebrew in are not
    installed everywhere: naming several lets one settings file work on a
    machine that has ``Frank Ruehl CLM`` and on one that only has ``FreeSerif``.
    The first name that is installed wins. If *none* of them is, that is an
    error — a fallback to whatever the renderer would have picked produces a
    document that is quietly not the one that was asked for, and for Hebrew it
    is usually one with no vowels or cantillation.

    A bare string is accepted as shorthand for a one-element chain.
    """

    names: list[str] = Field(
        min_length=1,
        description="Font names, most preferred first. The first one installed is used.",
    )

    @model_validator(mode="before")
    @classmethod
    def accept_bare_string_or_list(cls, value: object) -> object:
        if isinstance(value, str):
            return {"names": [value]}
        if isinstance(value, list):
            return {"names": value}
        return value


# Families that always exist, because the stylesheet refers to them by role
# rather than by name: every Hebrew run is set in `hebrew` and everything else
# in `latin`. Users may add more and point a style at them.
LATIN_FAMILY = "latin"
HEBREW_FAMILY = "hebrew"

_DEFAULT_FONTS = {
    LATIN_FAMILY: ["Linux Libertine O"],
    # Frank Ruehl CLM is the house face; Ezra SIL and SBL Hebrew are the usual
    # scholarly substitutes; FreeSerif is the last resort that is present on
    # essentially every Linux TeX installation.
    HEBREW_FAMILY: ["Frank Ruehl CLM", "Ezra SIL", "SBL Hebrew", "FreeSerif"],
}


@lru_cache(maxsize=1)
def _installed_font_families() -> Optional[frozenset[str]]:
    """ Every font family fontconfig knows about, or None if it cannot be asked.

    Cached: a settings file declares a handful of chains and each would
    otherwise re-run the same query. Returning None rather than an empty set
    keeps "fontconfig said there are no fonts" distinguishable from "there is no
    fontconfig", which is the difference between failing and deferring the check
    to the renderer.
    """
    if shutil.which("fc-list") is None:
        return None
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    families = set()
    for line in result.stdout.splitlines():
        # fc-list reports a family's aliases comma-separated on one line.
        for name in line.split(","):
            name = name.strip()
            if name:
                families.add(name.casefold())
    return frozenset(families)


def resolve_font(names: list[str]) -> Optional[str]:
    """ The first installed name in a chain.

    Returns None when fontconfig is unavailable, which means "undecidable here";
    the caller leaves the choice to the renderer in that case. Raises when
    fontconfig is available and none of the names is installed.
    """
    installed = _installed_font_families()
    if installed is None:
        return None
    for name in names:
        if name.casefold() in installed:
            return name
    raise ValueError(
        "none of these fonts is installed: "
        + ", ".join(repr(name) for name in names)
        + ". Install one of them, or name a font that is present "
        "(`fc-list : family` lists them)."
    )


# ---------------------------------------------------------------------------
# Text styles
# ---------------------------------------------------------------------------


class TextStyle(ForbidExtra):
    """ How one kind of text is set.

    Every field is optional and ``None`` means "leave it as the surrounding text
    has it", so a style says only what it changes. The defaults on the roles in
    :class:`Styles` spell out the appearance the exporter has always produced.
    """

    font: Optional[str] = Field(
        default=None,
        description=(
            "A family declared in `typography.fonts`. Omit to let the text keep "
            "the font its script selects (`hebrew` for Hebrew, `latin` otherwise)."
        ),
    )
    size: Optional[FontSize] = Field(
        default=None,
        description=(
            "A named size (xxx-small ... xxxx-large), which follows "
            "`page.base_font_size`, or an absolute length such as `9pt`."
        ),
    )
    weight: Optional[FontWeight] = Field(default=None, description="normal | bold")
    style: Optional[FontStyle] = Field(default=None, description="normal | italic")
    variant: Optional[FontVariant] = Field(
        default=None, description="normal | small-caps"
    )
    align: Optional[Alignment] = Field(
        default=None,
        description="left | right | center | justify. Only meaningful for block-level roles.",
    )
    space_before: Optional[Length] = Field(
        default=None, description="Vertical space above. Block-level roles only."
    )
    space_after: Optional[Length] = Field(
        default=None, description="Vertical space below. Block-level roles only."
    )

    def is_empty(self) -> bool:
        return all(value is None for value in self.__dict__.values())


class Styles(ForbidExtra):
    """ The appearance of each kind of text the exporter distinguishes.

    The defaults are the appearance the stylesheet has always produced. Changing
    one changes only that role.
    """

    body: TextStyle = Field(
        default_factory=TextStyle,
        description="Ordinary running text.",
    )
    heading1: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.XX_LARGE, weight=FontWeight.BOLD, align=Alignment.CENTER
        ),
        description="Top-level section heading.",
    )
    heading2: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.X_LARGE, weight=FontWeight.BOLD, align=Alignment.CENTER
        ),
        description="Second-level section heading.",
    )
    heading3: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.LARGE, weight=FontWeight.BOLD, align=Alignment.CENTER
        ),
        description="Third-level section heading.",
    )
    heading4: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.NORMAL, weight=FontWeight.BOLD, align=Alignment.CENTER
        ),
        description="Fourth-level section heading; the deepest level there is.",
    )
    title_main: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.XXXX_LARGE,
            weight=FontWeight.BOLD,
            align=Alignment.CENTER,
            space_after="1.5ex",
        ),
        description="The main title on the title page.",
    )
    title_sub: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.X_LARGE, align=Alignment.CENTER, space_before="1.5ex"
        ),
        description="The subtitle on the title page.",
    )
    title_alt: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.LARGE, align=Alignment.CENTER, space_after="1ex"
        ),
        description="An alternative title, usually the title in the other language.",
    )
    byline: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.LARGE, align=Alignment.CENTER, space_before="3ex"
        ),
        description="The author/editor line on the title page.",
    )
    edition: TextStyle = Field(
        default_factory=lambda: TextStyle(align=Alignment.CENTER, space_before="2ex"),
        description="The edition statement on the title page.",
    )
    imprint: TextStyle = Field(
        default_factory=lambda: TextStyle(align=Alignment.CENTER, space_before="4ex"),
        description="The publisher/place/date block at the foot of the title page.",
    )
    epigraph: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.SMALL,
            style=FontStyle.ITALIC,
            align=Alignment.CENTER,
            space_before="2ex",
        ),
        description="An epigraph on the title page.",
    )
    imprimatur: TextStyle = Field(
        default_factory=lambda: TextStyle(
            size=NamedSize.SMALL,
            style=FontStyle.ITALIC,
            align=Alignment.CENTER,
            space_before="2ex",
        ),
        description="An imprimatur or approbation on the title page.",
    )
    title_page_block: TextStyle = Field(
        default_factory=lambda: TextStyle(align=Alignment.CENTER),
        description="Any other paragraph on the title page.",
    )
    citation: TextStyle = Field(
        default_factory=lambda: TextStyle(
            style=FontStyle.ITALIC, align=Alignment.CENTER
        ),
        description=(
            "A scriptural citation set on a line of its own, naming where a "
            "reading begins or resumes."
        ),
    )
    parsha: TextStyle = Field(
        default_factory=lambda: TextStyle(size=NamedSize.LARGE, weight=FontWeight.BOLD),
        description="A parsha name, run in at the head of the text it opens.",
    )
    aliyah: TextStyle = Field(
        default_factory=lambda: TextStyle(weight=FontWeight.BOLD),
        description="An aliyah or maftir marker, inline at the verse it begins on.",
    )
    verse_number: TextStyle = Field(
        default_factory=TextStyle,
        description="The verse number at the start of each verse.",
    )
    chapter_number: TextStyle = Field(
        default_factory=lambda: TextStyle(size=NamedSize.LARGE, weight=FontWeight.BOLD),
        description="The chapter number, inline at the start of a chapter.",
    )
    instruction: TextStyle = Field(
        default_factory=lambda: TextStyle(weight=FontWeight.BOLD),
        description="An instruction to the reader, in the note apparatus.",
    )
    note: TextStyle = Field(
        default_factory=lambda: TextStyle(weight=FontWeight.BOLD),
        description="The text of an editorial note.",
    )
    note_mark: TextStyle = Field(
        default_factory=lambda: TextStyle(size=NamedSize.XX_SMALL),
        description=(
            "The mark that anchors a note, both in the text and where the note "
            "is printed."
        ),
    )
    line_number: TextStyle = Field(
        default_factory=TextStyle,
        description="Marginal line numbers.",
    )
    section_separator: TextStyle = Field(
        default_factory=lambda: TextStyle(align=Alignment.CENTER),
        description="The separator between unheaded sections.",
    )


# ---------------------------------------------------------------------------
# Page, paragraphs, and the rest
# ---------------------------------------------------------------------------


class Margins(ForbidExtra):
    """ The white space around the text block.

    Every margin defaults to None, which leaves the renderer's own default in
    place — for the PDF stage that is the document class's, which is what the
    exporter produced before margins were configurable.

    Margins are always named ``inner`` and ``outer`` rather than left and right.
    On a two-sided document the inner margin is the one at the binding, so it
    changes sides between recto and verso; on a one-sided document inner is left
    and outer is right, and the renderer maps them.
    """

    top: Optional[Length] = Field(default=None, description="Space above the text block.")
    bottom: Optional[Length] = Field(
        default=None, description="Space below the text block."
    )
    inner: Optional[Length] = Field(
        default=None,
        description="Margin at the binding edge (the left margin when `sides: one`).",
    )
    outer: Optional[Length] = Field(
        default=None,
        description="Margin at the fore edge (the right margin when `sides: one`).",
    )
    binding_offset: Optional[Length] = Field(
        default=None,
        description=(
            "Extra space added at the binding edge and taken off the fore edge, "
            "for the part of the page a binding swallows."
        ),
    )

    def is_empty(self) -> bool:
        return all(value is None for value in self.__dict__.values())


class PageConfig(ForbidExtra):
    """ The sheet itself: its size, which way up it is, and how it is bound. """

    paper: PaperType = Field(
        default=PaperType.LETTERPAPER,
        description=(
            "a4paper | letterpaper | legalpaper | a5paper | b5paper | "
            "executivepaper | custom. `custom` requires `width` and `height`."
        ),
    )
    width: Optional[Length] = Field(
        default=None, description="Sheet width. Only with `paper: custom`."
    )
    height: Optional[Length] = Field(
        default=None, description="Sheet height. Only with `paper: custom`."
    )
    orientation: Orientation = Field(
        default=Orientation.PORTRAIT, description="portrait | landscape"
    )
    sides: Sides = Field(
        default=Sides.TWO,
        description=(
            "two: printed on both sides, with margins and running heads that "
            "mirror between recto and verso. one: printed on one side only."
        ),
    )
    chapter_start: ChapterStart = Field(
        default=ChapterStart.RECTO,
        description=(
            "recto: a book always opens on a right-hand page, with a blank "
            "inserted if needed. any: it opens on whichever page comes next."
        ),
    )
    base_font_size: BaseFontSize = Field(
        default=BaseFontSize.PT11,
        description="10pt | 11pt | 12pt. Named sizes in `styles` are relative to this.",
    )
    margins: Margins = Field(
        default_factory=Margins,
        description="Margins around the text block. Omitted margins keep the renderer's default.",
    )

    @model_validator(mode="after")
    def validate_custom_paper(self) -> "PageConfig":
        if self.paper is PaperType.CUSTOM:
            missing = [
                name
                for name in ("width", "height")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    "`paper: custom` requires " + " and ".join(missing)
                )
        elif self.width is not None or self.height is not None:
            raise ValueError(
                f"`width` and `height` may only be set with `paper: custom`, "
                f"not `paper: {self.paper.value}`"
            )
        return self


class ParagraphConfig(ForbidExtra):
    """ How paragraphs of running text are set. """

    indent: Length = Field(
        default="0pt", description="First-line indent. `0pt` for unindented paragraphs."
    )
    spacing: Length = Field(
        default="0.75em",
        description=(
            "Vertical space between paragraphs, in addition to normal line "
            "spacing. Defaults to at least half a line so a new paragraph "
            "reads as distinct from an ordinary wrapped line."
        ),
    )
    line_spacing: float = Field(
        default=1.0,
        ge=0.5,
        le=3.0,
        description=(
            "Multiple of single spacing. 1.0 is set solid, 1.5 is one-and-a-half "
            "spaced. Note that Hebrew with vowels and cantillation needs more "
            "leading than unpointed text."
        ),
    )
    alignment: Alignment = Field(
        default=Alignment.JUSTIFY,
        description="justify | left | right | center",
    )


class LineNumberConfig(ForbidExtra):
    """ Marginal line numbers, as a critical edition uses to cite a passage. """

    enabled: bool = Field(
        default=True, description="Whether line numbers are printed at all."
    )
    unit: LineationUnit = Field(
        default=LineationUnit.PAGE,
        description="page | section — what numbering restarts at.",
    )
    increment: int = Field(
        default=5, ge=1, description="Print a number every nth line."
    )
    first: int = Field(
        default=5,
        ge=1,
        description=(
            "The first line number to print. The default matches `increment`, so "
            "the numbers run 5, 10, 15 rather than 1, 5, 10."
        ),
    )
    margin: LineNumberMargin = Field(
        default=LineNumberMargin.OUTER,
        description=(
            "inner | outer | left | right. In a two-column parallel layout each "
            "column takes the nearer outer margin regardless of this setting, "
            "since the alternative is numbers in the gutter between the columns."
        ),
    )
    separation: Length = Field(
        default="1em",
        description="Space between the number and the text block.",
    )
    numerals: Numerals = Field(
        default=Numerals.ARABIC, description="arabic | hebrew"
    )


class NoteConfig(ForbidExtra):
    """ Editorial notes and instructions: where they go and how they are marked. """

    placement: NotePlacement = Field(
        default=NotePlacement.FOOTNOTE,
        description="footnote | endnote | none",
    )
    anchor: NoteAnchor = Field(
        default=NoteAnchor.INTERLINEAR,
        description=(
            "interlinear | superscript | inline. `interlinear` raises the mark "
            "above the line and gives it no width, so the text it annotates is "
            "not respaced — which matters when both sides of a parallel text "
            "have to stay aligned."
        ),
    )
    mark: NoteMark = Field(
        default=NoteMark.NUMERIC,
        description="numeric | alpha | roman | symbol — the series marks are drawn from.",
    )
    # There is deliberately no setting for showing the lemma — the words a note
    # is attached to, repeated where the note is printed. A note in this schema
    # anchors at a point rather than over a range, so there are no such words to
    # repeat: the apparatus entry's lemma is the mark itself, and printing it
    # would give "* ] * the note text".


class ConditionalMarkerConfig(ForbidExtra):
    """ How an undecided conditional passage is delimited.

    A condition the compiler could decide is resolved away, so anything marked
    here is a passage the reader has to choose to say or skip.
    """

    inline_open: str = Field(
        default="[", description="Opens a conditional run inside a paragraph."
    )
    inline_close: str = Field(
        default="]", description="Closes a conditional run inside a paragraph."
    )
    block: ConditionalBlock = Field(
        default=ConditionalBlock.RULE,
        description=(
            "rule | brackets | none — how a whole conditional paragraph is "
            "delimited. Brackets several lines apart do not read as a pair, "
            "hence the rule."
        ),
    )
    rule_width: Percent = Field(
        default="25%", description="Width of the rule, as a percentage of the measure."
    )
    rule_thickness: Length = Field(default="0.4pt", description="Thickness of the rule.")


class MarkerConfig(ForbidExtra):
    """ The small marks that structure a text without being part of it. """

    section_separator: str = Field(
        default="* * * *",
        description=(
            "Printed between sections that have no heading. Set to an empty "
            "string to leave nothing but the space."
        ),
    )
    verse_numbers: Visibility = Field(
        default=Visibility.SHOWN, description="shown | hidden"
    )
    chapter_numbers: Visibility = Field(
        default=Visibility.SHOWN, description="shown | hidden"
    )
    conditional: ConditionalMarkerConfig = Field(
        default_factory=ConditionalMarkerConfig,
        description="Markers around passages whose condition could not be decided.",
    )


class ParallelTypographyConfig(ForbidExtra):
    """ The geometry of a parallel-text layout.

    Which text goes on which side is not set here: it is `parallel.column_order`
    in the compiler section of the settings file, because the compiler is what
    decides the order the streams are emitted in.
    """

    layout: ParallelLayout = Field(
        default=ParallelLayout.PAIRS,
        description=(
            "pairs: two columns on the same page. pages: facing pages, which "
            "gives each text a full measure and suits a long work."
        ),
    )
    column_width: Percent = Field(
        default="43%",
        description=(
            "Width of each column as a percentage of the text block, in `pairs` "
            "layout. The two columns and the gap between them share 100%, so "
            "well under 50% each — the remainder leaves the outer margins room "
            "for line numbers."
        ),
    )
    column_position: ColumnPosition = Field(
        default=ColumnPosition.CENTER,
        description=(
            "left | center | right — where the pair of columns sits in the text "
            "block, in `pairs` layout."
        ),
    )


class TableOfContentsConfig(ForbidExtra):
    """ An auto-generated table of contents.

    ``depth`` is independent of the PDF bookmark depth, which is always four
    levels deep regardless of this setting.
    """

    enabled: bool = Field(
        default=False, description="Whether to print a table of contents."
    )
    depth: int = Field(
        default=4, ge=1, le=4, description="Heading levels shown, 1-4."
    )


# ---------------------------------------------------------------------------
# The whole tree
# ---------------------------------------------------------------------------


class TypographyConfig(ForbidExtra):
    """ Everything about how the exported document looks.

    Read by the output stage only; the linear-XML compiler ignores it. Every
    section is optional and every default reproduces the exporter's long-standing
    output, so a settings file need only say what it wants changed.

    See ``doc/typography.md`` for the full reference.
    """

    fonts: dict[str, FontFamily] = Field(
        default_factory=dict,
        description=(
            "Named font families, each a chain of names tried in order. "
            "`latin` and `hebrew` always exist and are used for Latin-script and "
            "Hebrew-script text respectively; add your own and point a style at "
            "them by name."
        ),
    )
    page: PageConfig = Field(
        default_factory=PageConfig, description="Paper size, sides, base font size, margins."
    )
    paragraphs: ParagraphConfig = Field(
        default_factory=ParagraphConfig, description="Indent, spacing, leading, alignment."
    )
    styles: Styles = Field(
        default_factory=Styles, description="The appearance of each kind of text."
    )
    line_numbers: LineNumberConfig = Field(
        default_factory=LineNumberConfig, description="Marginal line numbers."
    )
    notes: NoteConfig = Field(
        default_factory=NoteConfig, description="Placement and marking of notes."
    )
    markers: MarkerConfig = Field(
        default_factory=MarkerConfig,
        description="Section separators, verse and chapter numbers, conditional markers.",
    )
    parallel: ParallelTypographyConfig = Field(
        default_factory=ParallelTypographyConfig,
        description="Geometry of a parallel-text layout.",
    )
    table_of_contents: TableOfContentsConfig = Field(
        default_factory=TableOfContentsConfig,
        description="An auto-generated table of contents.",
    )
    page_header: RunningHeadConfig = Field(
        default_factory=RunningHeadConfig,
        description=(
            "Running head. Empty by default, which leaves the renderer's own "
            "page style alone. See doc/typography.md for the template codes."
        ),
    )
    page_footer: RunningHeadConfig = Field(
        default_factory=RunningHeadConfig, description="Running foot; same shape as `page_header`."
    )

    # Which families the settings file actually named, as opposed to the ones
    # filled in below. The renderer emits a font declaration only for the
    # former, so an unmentioned `hebrew` keeps whatever the renderer already
    # does — which for the PDF stage is the same chain, chosen at TeX time.
    _declared_fonts: frozenset[str] = PrivateAttr(default=frozenset())

    @property
    def declared_fonts(self) -> frozenset[str]:
        """ The font families the settings file named itself. """
        return self._declared_fonts

    @model_validator(mode="after")
    def apply_font_defaults(self) -> "TypographyConfig":
        """ Fill in `latin` and `hebrew` and check every chain resolves.

        A user-declared `latin` or `hebrew` replaces the default outright rather
        than extending it: someone who names a Hebrew face and gets Frank Ruehl
        anyway, because their name was misspelled and the old chain was still
        underneath, has been told nothing.
        """
        self._declared_fonts = frozenset(self.fonts)
        for family, names in _DEFAULT_FONTS.items():
            self.fonts.setdefault(family, FontFamily(names=list(names)))
        # Only a chain the settings file named is checked. A default the user
        # never asked for must not fail on a machine that happens not to have
        # it: the renderer already falls back for those — for the PDF stage,
        # the stylesheet's own \IfFontExistsTF chain — and refusing to build at
        # all would mean nobody could export anything without first installing
        # this project's house fonts.
        for family in self._declared_fonts:
            try:
                resolve_font(self.fonts[family].names)
            except ValueError as e:
                raise ValueError(f"font `{family}`: {e}") from e
        return self

    @model_validator(mode="after")
    def validate_style_font_references(self) -> "TypographyConfig":
        for role, style in self.styles.__dict__.items():
            if style.font is not None and style.font not in self.fonts:
                known = ", ".join(sorted(self.fonts))
                raise ValueError(
                    f"styles.{role}.font names `{style.font}`, which is not "
                    f"declared in typography.fonts (declared: {known})"
                )
        return self

    @model_validator(mode="after")
    def validate_notes_are_not_styled_away(self) -> "TypographyConfig":
        """ Styling notes that are switched off is a contradiction, not a no-op.

        Someone who sets a note style and `placement: none` in the same file has
        two intentions that cannot both hold, and the one that silently wins
        deletes their notes.
        """
        if self.notes.placement is NotePlacement.NONE:
            # Only an explicitly written style is a contradiction; the defaults
            # are always present and say nothing about what the user wants.
            for role in ("note", "note_mark"):
                if role in self.styles.model_fields_set:
                    raise ValueError(
                        f"styles.{role} is set but notes.placement is `none`, "
                        "so no notes are printed. Remove one of the two."
                    )
        return self
