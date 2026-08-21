"""Tests for the TeX side of typography settings.

``opensiddur/exporter/tex/typography_tex.py`` is a pure function of the settings,
so it is tested directly rather than through the XSLT.

The property most of these tests are protecting: **a directive is emitted only
for a setting the file actually wrote.** The stylesheet keeps every default it
ever had and this block overrides them, so anything emitted for an unwritten
setting is a change to a document that asked for none.
"""

import unittest
from unittest.mock import patch

from opensiddur.exporter import typography as typography_module
from opensiddur.exporter.typography import NamedSize, TextStyle, TypographyConfig
from opensiddur.exporter.tex.typography_tex import (
    build_typography_preamble,
    documentclass_options,
    style_tokens,
)


def _no_fontconfig():
    """A machine that cannot be asked which fonts are installed.

    Font resolution then defers to the renderer, which is the branch that emits
    a fallback chain — the one worth testing, since it does not depend on which
    fonts this machine happens to have. Both validation and emission consult
    fontconfig, so both have to run inside this.
    """
    return patch.object(typography_module, "_installed_font_families", return_value=None)


def _config(data: dict) -> TypographyConfig:
    with _no_fontconfig():
        return TypographyConfig.model_validate(data)


def _tex(data: dict, has_parallel: bool = False) -> str:
    with _no_fontconfig():
        return build_typography_preamble(
            TypographyConfig.model_validate(data), has_parallel
        )


class TestNothingConfigured(unittest.TestCase):
    def test_an_empty_settings_section_emits_nothing_at_all(self):
        """The whole point: an unconfigured document is the document this
        exporter has always produced."""
        self.assertEqual(_tex({}), "")

    def test_default_class_options_are_what_they_have_always_been(self):
        self.assertEqual(documentclass_options(_config({})), "11pt,letterpaper")


class TestDocumentClassOptions(unittest.TestCase):
    def test_paper_and_base_size(self):
        options = documentclass_options(_config({"page": {"paper": "a5paper", "base_font_size": "12pt"}}))
        self.assertEqual(options, "12pt,a5paper")

    def test_one_sided_and_open_anywhere(self):
        options = documentclass_options(
            _config({"page": {"sides": "one", "chapter_start": "any"}})
        )
        self.assertEqual(options, "11pt,letterpaper,oneside,openany")

    def test_the_class_defaults_are_left_unsaid(self):
        """twoside and openright are the class's own, so saying them would
        change the option list of a document that configured nothing."""
        options = documentclass_options(
            _config({"page": {"sides": "two", "chapter_start": "recto"}})
        )
        self.assertEqual(options, "11pt,letterpaper")

    def test_custom_paper_is_left_out_of_the_class_options(self):
        """There is no class option for it; geometry sets the dimensions."""
        config = _config({"page": {"paper": "custom", "width": "6in", "height": "9in"}})
        self.assertEqual(documentclass_options(config), "11pt")
        tex = build_typography_preamble(config)
        self.assertIn(r"\geometry{paperwidth=6in,paperheight=9in}", tex)


class TestGeometry(unittest.TestCase):
    def test_margins_are_emitted_only_when_written(self):
        tex = _tex({"page": {"margins": {"top": "2cm", "inner": "25mm"}}})
        self.assertIn("top=2cm", tex)
        self.assertIn("inner=25mm", tex)
        self.assertNotIn("bottom=", tex)
        self.assertNotIn("outer=", tex)

    def test_inner_and_outer_become_left_and_right_on_a_one_sided_document(self):
        """geometry only understands inner/outer for a two-sided document; on a
        one-sided one they are simply the left and right margins."""
        tex = _tex({"page": {"sides": "one", "margins": {"inner": "1in", "outer": "2in"}}})
        self.assertIn("left=1in", tex)
        self.assertIn("right=2in", tex)
        self.assertNotIn("inner=", tex)

    def test_binding_offset(self):
        self.assertIn("bindingoffset=5mm", _tex({"page": {"margins": {"binding_offset": "5mm"}}}))

    def test_landscape(self):
        self.assertIn(r"\geometry{landscape}", _tex({"page": {"orientation": "landscape"}}))

    def test_no_geometry_call_when_the_page_is_not_configured(self):
        self.assertNotIn(r"\geometry", _tex({"page": {"base_font_size": "12pt"}}))


class TestFonts(unittest.TestCase):
    def test_an_undeclared_family_is_left_to_the_stylesheet(self):
        """The stylesheet already declares latin and hebrew with the same chain,
        so re-emitting it would be noise at best."""
        self.assertNotIn(r"\setmainfont", _tex({}))

    def test_a_declared_latin_family_sets_the_main_font(self):
        """One name is not a chain: it is named outright, with no test around
        it, so a font that is not there fails the build rather than quietly
        becoming something else."""
        tex = _tex({"fonts": {"latin": "TeX Gyre Pagella"}})
        self.assertIn(r"\setmainfont{TeX Gyre Pagella}", tex)
        self.assertNotIn(r"\IfFontExistsTF", tex)

    def test_a_declared_hebrew_family_renews_rather_than_declares(self):
        """\\hebrewfont already exists — the stylesheet declared it — so a
        \\newfontfamily here would be a "command already defined" error."""
        tex = _tex({"fonts": {"hebrew": ["Ezra SIL"]}})
        self.assertIn(r"\renewfontfamily\hebrewfont", tex)
        self.assertNotIn(r"\newfontfamily\hebrewfont", tex)
        self.assertIn("Renderer=HarfBuzz", tex)
        self.assertIn(r"\let\hebrewfontsf\hebrewfont", tex)

    def test_a_chain_becomes_nested_tests_when_fontconfig_cannot_choose(self):
        tex = _tex({"fonts": {"latin": ["First", "Second", "Third"]}})
        self.assertIn(r"\IfFontExistsTF{First}", tex)
        self.assertIn(r"\IfFontExistsTF{Second}", tex)
        # The last name is the fallback, not another test.
        self.assertNotIn(r"\IfFontExistsTF{Third}", tex)
        self.assertIn(r"\setmainfont{Third}", tex)

    def test_a_resolved_chain_names_one_font_outright(self):
        with patch.object(
            typography_module,
            "_installed_font_families",
            return_value=frozenset({"second", "freeserif"}),
        ):
            config = TypographyConfig.model_validate({"fonts": {"latin": ["First", "Second"]}})
            tex = build_typography_preamble(config)
        self.assertIn(r"\setmainfont{Second}", tex)
        self.assertNotIn(r"\IfFontExistsTF", tex)

    def test_a_user_family_gets_a_command_named_after_its_key(self):
        tex = _tex({"fonts": {"note-sans": "DejaVu Sans"}})
        self.assertIn(r"\newfontfamily\OSfontNoteSans{DejaVu Sans}", tex)

    def test_a_style_selects_a_user_family_by_that_command(self):
        tex = _tex(
            {"fonts": {"note-sans": "DejaVu Sans"}, "styles": {"note": {"font": "note-sans"}}}
        )
        self.assertIn(r"\renewcommand{\notenote}[1]{{\OSfontNoteSans #1}}", tex)


class TestStyleTokens(unittest.TestCase):
    def test_the_named_ladder_maps_onto_the_size_commands(self):
        for name, command in (
            (NamedSize.XXX_SMALL, r"\tiny"),
            (NamedSize.SMALL, r"\small"),
            (NamedSize.NORMAL, r"\normalsize"),
            (NamedSize.XX_LARGE, r"\LARGE"),
            (NamedSize.XXXX_LARGE, r"\Huge"),
        ):
            self.assertEqual(style_tokens(TextStyle(size=name)), command)

    def test_an_absolute_size_carries_a_baseline_too(self):
        """\\fontsize sets both, so a size given alone would leave the leading
        of whatever font was in force."""
        self.assertEqual(
            style_tokens(TextStyle(size="10pt")), r"\fontsize{10pt}{12pt}\selectfont"
        )

    def test_line_spacing_scales_the_baseline_of_an_absolute_size(self):
        self.assertEqual(
            style_tokens(TextStyle(size="10pt"), line_spacing=1.5),
            r"\fontsize{10pt}{18pt}\selectfont",
        )

    def test_weight_style_and_variant(self):
        self.assertEqual(
            style_tokens(TextStyle(weight="bold", style="italic", variant="small-caps")),
            r"\bfseries\itshape\scshape",
        )

    def test_normal_is_stated_rather_than_implied(self):
        """A role whose default is bold needs a way to say "not bold"."""
        self.assertEqual(style_tokens(TextStyle(weight="normal")), r"\mdseries")


class TestStyles(unittest.TestCase):
    def test_only_the_written_roles_are_emitted(self):
        tex = _tex({"styles": {"heading1": {"size": "large"}}})
        self.assertIn(r"\renewcommand{\OSheadA}", tex)
        self.assertNotIn(r"\OSheadB", tex)

    def test_headings_are_aligned_with_fill_glue_not_a_paragraph(self):
        """reledmac captures numbered text one \\par-delimited line at a time, so
        a \\par here would escape that capture and, under reledpar, land outside
        its column."""
        tex = _tex({"styles": {"heading1": {"size": "large", "align": "center"}}})
        self.assertIn(r"\mbox{}\hfill{\normalfont\large #1}\hfill\mbox{}", tex)
        self.assertNotIn(r"\centering", tex)

    def test_left_and_right_alignment_use_one_sided_fill(self):
        self.assertIn(
            r"\renewcommand{\OSheadA}[1]{{\normalfont\large #1}\hfill\mbox{}}",
            _tex({"styles": {"heading1": {"size": "large", "align": "left"}}}),
        )
        self.assertIn(
            r"\renewcommand{\OSheadA}[1]{\mbox{}\hfill{\normalfont\large #1}}",
            _tex({"styles": {"heading1": {"size": "large", "align": "right"}}}),
        )

    def test_title_page_roles_are_real_paragraphs(self):
        """A title page is set outside all numbering, so it can have proper
        centred paragraphs with line breaking."""
        tex = _tex({"styles": {"title_main": {"size": "xxxx-large", "align": "center"}}})
        self.assertIn(r"{\centering\normalfont\Huge #1\par}", tex)

    def test_space_before_and_after_sit_outside_the_group(self):
        tex = _tex({"styles": {"byline": {"space_before": "3ex", "space_after": "1ex"}}})
        self.assertIn(r"\renewcommand{\OSByline}[1]{\vspace{3ex}{", tex)
        self.assertTrue(tex.rstrip().endswith(r"\par}\vspace{1ex}}"))

    def test_verse_and_chapter_numbers_stay_left_to_right(self):
        """Digits laid out in an RTL context come out reversed: 50 reads 05."""
        for role, macro in (("verse_number", r"\vno"), ("chapter_number", r"\chno")):
            tex = _tex({"styles": {role: {"size": "small"}}})
            self.assertIn(rf"\renewcommand{{{macro}}}[1]{{", tex)
            self.assertIn(r"\textdir TLT\selectlanguage{english}", tex)

    def test_body_style_goes_through_the_document_wide_hook(self):
        self.assertIn(
            r"\renewcommand{\OSBodyStyle}{\small}", _tex({"styles": {"body": {"size": "small"}}})
        )

    def test_notes_and_instructions(self):
        self.assertIn(
            r"\renewcommand{\notenote}[1]{{\mdseries #1}}",
            _tex({"styles": {"note": {"weight": "normal"}}}),
        )
        self.assertIn(
            r"\renewcommand{\instructionnote}[1]{{\itshape #1}}",
            _tex({"styles": {"instruction": {"style": "italic"}}}),
        )


class TestParagraphs(unittest.TestCase):
    def test_indent_spacing_and_leading(self):
        tex = _tex({"paragraphs": {"indent": "1em", "spacing": "1ex", "line_spacing": 1.5}})
        self.assertIn(r"\setlength{\parindent}{1em}", tex)
        self.assertIn(r"\setlength{\parskip}{1ex}", tex)
        self.assertIn(r"\linespread{1.5}\selectfont", tex)

    def test_alignment_is_applied_where_it_takes_effect(self):
        """\\raggedright in a preamble is a no-op; it has to be applied once the
        document has started."""
        self.assertIn(r"\AtBeginDocument{\raggedright}", _tex({"paragraphs": {"alignment": "left"}}))

    def test_justified_is_the_absence_of_raggedness(self):
        self.assertEqual(_tex({"paragraphs": {"alignment": "justify"}}), "")


class TestLineNumbers(unittest.TestCase):
    def test_switching_them_off_uses_reledmacs_own_switch(self):
        """The numbering machinery still runs, so cross-references and the
        apparatus are unaffected; only the printing stops."""
        self.assertIn(r"\numberlinefalse", _tex({"line_numbers": {"enabled": False}}))

    def test_switching_them_off_makes_the_rest_of_the_section_moot(self):
        tex = _tex({"line_numbers": {"enabled": False, "increment": 2}})
        self.assertNotIn(r"\linenumincrement", tex)

    def test_increment_first_and_separation(self):
        tex = _tex({"line_numbers": {"increment": 2, "first": 1, "separation": "2em"}})
        self.assertIn(r"\linenumincrement{2}", tex)
        self.assertIn(r"\firstlinenum{1}", tex)
        self.assertIn(r"\setlength{\linenumsep}{2em}", tex)

    def test_the_right_hand_stream_is_configured_only_in_a_parallel_document(self):
        """\\linenumincrementR does not exist unless reledpar is loaded, and it is
        loaded only for a document with two aligned streams."""
        self.assertNotIn(r"\linenumincrementR", _tex({"line_numbers": {"increment": 2}}))
        self.assertIn(
            r"\linenumincrementR{2}", _tex({"line_numbers": {"increment": 2}}, has_parallel=True)
        )

    def test_lineation_unit_and_margin(self):
        tex = _tex({"line_numbers": {"unit": "section", "margin": "inner"}})
        self.assertIn(r"\lineation{section}", tex)
        self.assertIn(r"\linenummargin{inner}", tex)

    def test_hebrew_numerals_need_no_left_to_right_wrapper(self):
        """Their output is Hebrew letters, which belong in the surrounding
        direction; only digits have to be forced."""
        tex = _tex({"line_numbers": {"numerals": "hebrew"}})
        self.assertIn(r"\hebrewnumeral{#1}", tex)
        self.assertNotIn(r"\textdir TLT", tex)

    def test_the_number_is_formatted_through_linenumrep(self):
        """\\linenumberstyle is a declaration whose only job is to define
        \\linenumrep, and reledmac calls it once as it loads — so redefining it
        afterwards silently does nothing."""
        tex = _tex({"line_numbers": {"numerals": "hebrew"}})
        self.assertIn(r"\renewcommand*{\linenumrep}", tex)
        self.assertNotIn(r"\linenumberstyle", tex)

    def test_a_line_number_style_and_the_numeral_system_share_one_macro(self):
        """Emitting them separately would let the second silently discard the
        first."""
        tex = _tex(
            {
                "styles": {"line_number": {"size": "small"}},
                "line_numbers": {"numerals": "hebrew"},
            }
        )
        self.assertEqual(tex.count(r"\renewcommand*{\linenumrep}"), 1)
        self.assertIn(r"\small\hebrewnumeral{#1}", tex)

    def test_the_right_hand_stream_is_formatted_only_in_a_parallel_document(self):
        settings = {"styles": {"line_number": {"size": "small"}}}
        self.assertNotIn(r"\linenumrepR", _tex(settings))
        self.assertIn(r"\linenumrepR", _tex(settings, has_parallel=True))


class TestNotes(unittest.TestCase):
    def test_the_default_anchor_is_raised_and_zero_width(self):
        """Zero width is what keeps the annotated text from being respaced, and
        with it the two sides of a parallel text aligned."""
        tex = _tex({"notes": {"anchor": "interlinear"}})
        self.assertIn(r"\hbox to 0pt", tex)
        self.assertIn(r"\raisebox{1.5ex}", tex)

    def test_a_superscript_anchor(self):
        tex = _tex({"notes": {"anchor": "superscript"}})
        self.assertIn(r"\renewcommand{\OSInterlinearNotemark}[1]{", tex)
        self.assertIn(r"\textsuperscript", tex)
        self.assertNotIn(r"\hbox to 0pt", tex)

    def test_an_inline_anchor(self):
        tex = _tex({"notes": {"anchor": "inline"}})
        self.assertNotIn(r"\textsuperscript", tex)
        self.assertNotIn(r"\raisebox", tex)

    def test_the_mark_keeps_its_sans_face_unless_a_font_is_asked_for(self):
        """Changing the anchor should not silently change the face too."""
        self.assertIn(r"\sffamily", _tex({"notes": {"anchor": "inline"}}))
        tex = _tex(
            {"fonts": {"serif": "FreeSerif"}, "styles": {"note_mark": {"font": "serif"}}}
        )
        self.assertNotIn(r"\sffamily", tex)
        self.assertIn(r"\OSfontSerif", tex)

    def test_the_lemma_is_not_a_setting(self):
        """A note anchors at a point, so there are no annotated words to repeat;
        the apparatus lemma is the mark itself."""
        with self.assertRaises(Exception):
            _tex({"notes": {"show_lemma": True}})


class TestMarkers(unittest.TestCase):
    def test_the_section_separator_is_escaped(self):
        tex = _tex({"markers": {"section_separator": "~ & ~"}})
        self.assertIn(r"\textasciitilde{}", tex)
        self.assertIn(r"\&", tex)

    def test_an_empty_separator_leaves_nothing_but_the_space(self):
        self.assertIn(r"\renewcommand{\OSSectionSeparator}{}", _tex({"markers": {"section_separator": ""}}))

    def test_hiding_verse_and_chapter_numbers(self):
        tex = _tex({"markers": {"verse_numbers": "hidden", "chapter_numbers": "hidden"}})
        self.assertIn(r"\renewcommand{\vno}[1]{}", tex)
        self.assertIn(r"\renewcommand{\chno}[1]{}", tex)

    def test_showing_them_is_the_stylesheet_default_and_emits_nothing(self):
        self.assertEqual(_tex({"markers": {"verse_numbers": "shown"}}), "")

    def test_conditional_inline_markers(self):
        tex = _tex({"markers": {"conditional": {"inline_open": "(", "inline_close": ")"}}})
        self.assertIn(r"\renewcommand{\OSCondStartInline}{{\bfseries(}}", tex)
        self.assertIn(r"\renewcommand{\OSCondEndInline}{{\bfseries)}}", tex)

    def test_the_conditional_block_rule(self):
        tex = _tex({"markers": {"conditional": {"rule_width": "50%", "rule_thickness": "1pt"}}})
        self.assertIn(r"\rule{0.5\linewidth}{1pt}", tex)

    def test_a_bracketed_conditional_block_reuses_the_inline_markers(self):
        tex = _tex({"markers": {"conditional": {"block": "brackets"}}})
        self.assertIn(r"\renewcommand{\OSCondStartBlock}{\OSCondStartInline}", tex)

    def test_conditional_blocks_can_be_left_unmarked(self):
        tex = _tex({"markers": {"conditional": {"block": "none"}}})
        self.assertIn(r"\renewcommand{\OSCondStartBlock}{}", tex)
        self.assertIn(r"\renewcommand{\OSCondEndBlock}{}", tex)


class TestParallelColumns(unittest.TestCase):
    def test_column_geometry_needs_two_columns_on_one_page(self):
        settings = {"parallel": {"column_width": "40%", "column_position": "left"}}
        self.assertEqual(_tex(settings), "")
        tex = _tex(settings, has_parallel=True)
        self.assertIn(r"\setlength{\Lcolwidth}{0.4\textwidth}", tex)
        self.assertIn(r"\setlength{\Rcolwidth}{0.4\textwidth}", tex)
        self.assertIn(r"\columnsposition{L}", tex)

    def test_facing_pages_have_no_columns_to_size(self):
        tex = _tex(
            {"parallel": {"layout": "pages", "column_width": "40%"}}, has_parallel=True
        )
        self.assertNotIn(r"\Lcolwidth", tex)


if __name__ == "__main__":
    unittest.main()
