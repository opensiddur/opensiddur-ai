"""The typography settings an electronic book can honour, as CSS.

A settings file's `typography` describes the document, not a renderer (doc/typography.md), but
most of it is about paper: page size, margins, running heads, line numbers. A reflowing book
has none of those. What carries over is set here:

- `fonts` -- the `latin` and `hebrew` chains become the font stacks for each script;
- `markers` -- verse and chapter numbers shown or hidden, the section separator, and how an
  undecided conditional passage is delimited (passed to html.xslt as parameters, and drawn
  here);
- `paragraphs.line_spacing`, `paragraphs.spacing` and `paragraphs.alignment`.

Everything else is ignored. The fonts are named, not embedded: a reader without them gets the
next in the chain, and then the browser's own serif.
"""

from __future__ import annotations

from opensiddur.exporter.typography import (
    HEBREW_FAMILY,
    LATIN_FAMILY,
    Alignment,
    ConditionalBlock,
    TypographyConfig,
    Visibility,
)

_DEFAULT_CHAINS = {
    LATIN_FAMILY: ["Linux Libertine O", "Linux Libertine", "Libertinus Serif"],
    HEBREW_FAMILY: ["Frank Ruehl CLM", "Ezra SIL", "SBL Hebrew", "FreeSerif"],
}


def css_string(text: str) -> str:
    """A CSS string literal."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\a ")
    return f'"{escaped}"'


def _stack(typography: TypographyConfig, family: str) -> str:
    chain = typography.fonts.get(family)
    names = chain.names if chain is not None else _DEFAULT_CHAINS[family]
    return ", ".join([*(css_string(name) for name in names), "serif"])


_ALIGN = {
    Alignment.JUSTIFY: "justify",
    Alignment.LEFT: "left",
    Alignment.RIGHT: "right",
    Alignment.CENTER: "center",
}


def xslt_parameters(typography: TypographyConfig) -> dict[str, str]:
    """The settings html.xslt reads: the characters that bracket a conditional run."""
    conditional = typography.markers.conditional
    return {
        "inline-open": conditional.inline_open,
        "inline-close": conditional.inline_close,
        "block": conditional.block.value,
    }


def typography_css(typography: TypographyConfig) -> str:
    """The book's own styles, layered over reader.css."""
    markers = typography.markers
    conditional = markers.conditional
    rules = [
        ":root {",
        f"  --font-latin: {_stack(typography, LATIN_FAMILY)};",
        f"  --font-hebrew: {_stack(typography, HEBREW_FAMILY)};",
        f"  --line-spacing: {typography.paragraphs.line_spacing * 1.35:.3g};",
        f"  --text-align: {_ALIGN[typography.paragraphs.alignment]};",
        f"  --paragraph-spacing: {typography.paragraphs.spacing};",
        f"  --cond-rule-width: {conditional.rule_width};",
        f"  --cond-rule-thickness: {conditional.rule_thickness};",
        "}",
        f".section-separator::before {{ content: {css_string(markers.section_separator)}; }}",
    ]
    if markers.verse_numbers == Visibility.HIDDEN:
        rules.append(".v { display: none; }")
    if markers.chapter_numbers == Visibility.HIDDEN:
        rules.append(".ch { display: none; }")
    if conditional.block != ConditionalBlock.RULE:
        rules.append(".cm-block .cm-br { border: 0; width: auto; }")
    return "\n".join(rules) + "\n"
