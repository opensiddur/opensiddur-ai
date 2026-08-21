"""Tests for the typography settings models (opensiddur/exporter/typography.py).

Two things are being checked throughout: that every default reproduces the
output this exporter produced before any of it was configurable, and that
anything invalid is refused at load time rather than passed to the renderer.

Font resolution shells out to fontconfig, so it is mocked here — a test that
depended on which fonts this machine has installed would pass or fail for
reasons that have nothing to do with the code.
"""

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from opensiddur.exporter import typography as typography_module
from opensiddur.exporter.typography import (
    Alignment,
    BaseFontSize,
    ConditionalBlock,
    FontFamily,
    FontWeight,
    LineationUnit,
    NamedSize,
    NoteAnchor,
    NoteMark,
    NotePlacement,
    PaperType,
    ParallelLayout,
    Sides,
    TextStyle,
    TypographyConfig,
    Visibility,
    resolve_font,
)


def _validate(data: dict) -> TypographyConfig:
    """Validate a settings fragment with fontconfig reporting nothing installed.

    ``None`` from the query means "cannot be asked", which is how a machine
    without fontconfig behaves, so no font chain is rejected and the tests stay
    about the setting under test.
    """
    with patch.object(typography_module, "_installed_font_families", return_value=None):
        return TypographyConfig.model_validate(data)


class TestDefaults(unittest.TestCase):
    """An empty settings section has to mean "what it has always looked like"."""

    def setUp(self):
        self.config = _validate({})

    def test_page_defaults(self):
        self.assertEqual(self.config.page.paper, PaperType.LETTERPAPER)
        self.assertEqual(self.config.page.base_font_size, BaseFontSize.PT11)
        self.assertEqual(self.config.page.sides, Sides.TWO)
        self.assertTrue(self.config.page.margins.is_empty())

    def test_paragraph_defaults_match_the_stylesheet(self):
        self.assertEqual(self.config.paragraphs.indent, "0pt")
        self.assertEqual(self.config.paragraphs.spacing, "0.5em")
        self.assertEqual(self.config.paragraphs.line_spacing, 1.0)

    def test_heading_defaults_step_down_by_one_rung_each(self):
        sizes = [
            self.config.styles.heading1.size,
            self.config.styles.heading2.size,
            self.config.styles.heading3.size,
            self.config.styles.heading4.size,
        ]
        self.assertEqual(
            sizes,
            [
                NamedSize.XX_LARGE,
                NamedSize.X_LARGE,
                NamedSize.LARGE,
                NamedSize.NORMAL,
            ],
        )
        for style in (
            self.config.styles.heading1,
            self.config.styles.heading4,
        ):
            self.assertEqual(style.weight, FontWeight.BOLD)
            self.assertEqual(style.align, Alignment.CENTER)

    def test_line_number_defaults_match_reledmac(self):
        self.assertTrue(self.config.line_numbers.enabled)
        self.assertEqual(self.config.line_numbers.unit, LineationUnit.PAGE)
        # 5 and 5, so the numbers run 5, 10, 15 as they always have.
        self.assertEqual(self.config.line_numbers.increment, 5)
        self.assertEqual(self.config.line_numbers.first, 5)
        self.assertEqual(self.config.line_numbers.separation, "1em")

    def test_note_defaults(self):
        self.assertEqual(self.config.notes.placement, NotePlacement.FOOTNOTE)
        self.assertEqual(self.config.notes.anchor, NoteAnchor.INTERLINEAR)
        self.assertEqual(self.config.notes.mark, NoteMark.NUMERIC)

    def test_marker_defaults(self):
        self.assertEqual(self.config.markers.section_separator, "* * * *")
        self.assertEqual(self.config.markers.verse_numbers, Visibility.SHOWN)
        self.assertEqual(self.config.markers.conditional.inline_open, "[")
        self.assertEqual(self.config.markers.conditional.block, ConditionalBlock.RULE)
        self.assertEqual(self.config.markers.conditional.rule_width, "25%")

    def test_parallel_defaults(self):
        self.assertEqual(self.config.parallel.layout, ParallelLayout.PAIRS)
        self.assertEqual(self.config.parallel.column_width, "43%")

    def test_table_of_contents_defaults_to_disabled(self):
        self.assertFalse(self.config.table_of_contents.enabled)
        self.assertEqual(self.config.table_of_contents.depth, 4)

    def test_running_heads_default_to_nothing(self):
        self.assertTrue(self.config.page_header.is_empty())
        self.assertTrue(self.config.page_footer.is_empty())


class TestUnknownKeysAreRefused(unittest.TestCase):
    """A key nobody reads is a setting that silently did not happen."""

    def test_unknown_key_at_the_top_level(self):
        with self.assertRaises(ValidationError) as caught:
            _validate({"pgae": {}})
        self.assertIn("pgae", str(caught.exception))

    def test_unknown_key_in_a_section(self):
        with self.assertRaises(ValidationError) as caught:
            _validate({"page": {"papper": "a4paper"}})
        self.assertIn("papper", str(caught.exception))

    def test_unknown_role_in_styles(self):
        with self.assertRaises(ValidationError) as caught:
            _validate({"styles": {"heading5": {"size": "large"}}})
        self.assertIn("heading5", str(caught.exception))

    def test_unknown_attribute_in_a_style(self):
        with self.assertRaises(ValidationError) as caught:
            _validate({"styles": {"body": {"colour": "red"}}})
        self.assertIn("colour", str(caught.exception))

    def test_unknown_key_in_a_nested_section(self):
        with self.assertRaises(ValidationError) as caught:
            _validate({"markers": {"conditional": {"inline_middle": "-"}}})
        self.assertIn("inline_middle", str(caught.exception))


class TestClosedVocabularies(unittest.TestCase):
    def test_paper_must_be_a_known_size(self):
        with self.assertRaises(ValidationError):
            _validate({"page": {"paper": "tabloid"}})

    def test_base_font_size_is_restricted_to_the_three_that_exist(self):
        """Anything else silently becomes one of these, so asking is an error."""
        for size in ("10pt", "11pt", "12pt"):
            _validate({"page": {"base_font_size": size}})
        for size in ("13pt", "11", "large"):
            with self.assertRaises(ValidationError, msg=size):
                _validate({"page": {"base_font_size": size}})

    def test_note_placement_alignment_and_layout_are_closed(self):
        for section, key, bad in (
            ("notes", "placement", "margin"),
            ("notes", "anchor", "raised"),
            ("notes", "mark", "dingbat"),
            ("paragraphs", "alignment", "middle"),
            ("parallel", "layout", "columns"),
            ("line_numbers", "unit", "paragraph"),
            ("line_numbers", "numerals", "greek"),
            ("markers", "verse_numbers", "maybe"),
        ):
            with self.assertRaises(ValidationError, msg=f"{section}.{key}"):
                _validate({section: {key: bad}})

    def test_style_attributes_are_closed(self):
        for key, bad in (
            ("weight", "semibold"),
            ("style", "oblique"),
            ("variant", "all-caps"),
            ("align", "start"),
        ):
            with self.assertRaises(ValidationError, msg=key):
                _validate({"styles": {"body": {key: bad}}})


class TestLengths(unittest.TestCase):
    def test_accepted_lengths(self):
        for length in ("0pt", "12pt", "1.5em", "25mm", ".5in", "-3pt", "2ex", "1pc"):
            _validate({"paragraphs": {"indent": length}})

    def test_rejected_lengths(self):
        for length in ("12", "12 pt", "large", "12px", "", "pt"):
            with self.assertRaises(ValidationError, msg=repr(length)):
                _validate({"paragraphs": {"indent": length}})

    def test_a_size_may_be_a_named_rung_or_an_absolute_length(self):
        config = _validate({"styles": {"note": {"size": "9pt"}, "body": {"size": "small"}}})
        self.assertEqual(config.styles.note.size, "9pt")
        self.assertEqual(config.styles.body.size, NamedSize.SMALL)

    def test_a_size_may_not_be_relative_to_the_size_it_defines(self):
        for size in ("1.2em", "2ex"):
            with self.assertRaises(ValidationError, msg=size):
                _validate({"styles": {"note": {"size": size}}})

    def test_percentages(self):
        _validate({"parallel": {"column_width": "40%"}})
        for bad in ("40", "40 %", "%40"):
            with self.assertRaises(ValidationError, msg=bad):
                _validate({"parallel": {"column_width": bad}})

    def test_bounded_numbers(self):
        _validate({"paragraphs": {"line_spacing": 1.5}})
        for bad in (0.1, 4.0):
            with self.assertRaises(ValidationError, msg=str(bad)):
                _validate({"paragraphs": {"line_spacing": bad}})
        with self.assertRaises(ValidationError):
            _validate({"line_numbers": {"increment": 0}})
        with self.assertRaises(ValidationError):
            _validate({"table_of_contents": {"depth": 5}})


class TestCustomPaper(unittest.TestCase):
    def test_custom_paper_needs_both_dimensions(self):
        _validate({"page": {"paper": "custom", "width": "6in", "height": "9in"}})
        with self.assertRaises(ValidationError) as caught:
            _validate({"page": {"paper": "custom", "width": "6in"}})
        self.assertIn("height", str(caught.exception))

    def test_dimensions_without_custom_paper_are_an_error(self):
        """Silently ignoring them would print a document at the wrong size."""
        with self.assertRaises(ValidationError) as caught:
            _validate({"page": {"paper": "a4paper", "width": "6in", "height": "9in"}})
        self.assertIn("custom", str(caught.exception))


class TestFontFamilies(unittest.TestCase):
    def test_latin_and_hebrew_always_exist(self):
        config = _validate({})
        self.assertEqual(config.fonts["latin"].names, ["Linux Libertine O"])
        self.assertIn("FreeSerif", config.fonts["hebrew"].names)

    def test_a_bare_string_is_a_one_name_chain(self):
        config = _validate({"fonts": {"latin": "TeX Gyre Pagella"}})
        self.assertEqual(config.fonts["latin"].names, ["TeX Gyre Pagella"])

    def test_declaring_a_family_replaces_its_default_chain(self):
        """Leaving the old chain underneath would answer a misspelled font name
        with the house font and no complaint."""
        config = _validate({"fonts": {"hebrew": ["Ezra SIL"]}})
        self.assertEqual(config.fonts["hebrew"].names, ["Ezra SIL"])

    def test_declared_families_are_distinguished_from_filled_in_ones(self):
        config = _validate({"fonts": {"hebrew": "Ezra SIL"}})
        self.assertEqual(config.declared_fonts, frozenset({"hebrew"}))

    def test_an_empty_chain_is_refused(self):
        with self.assertRaises(ValidationError):
            _validate({"fonts": {"latin": []}})

    def test_a_style_may_only_name_a_declared_family(self):
        _validate({"fonts": {"sans": "DejaVu Sans"}, "styles": {"note": {"font": "sans"}}})
        with self.assertRaises(ValidationError) as caught:
            _validate({"styles": {"note": {"font": "sans"}}})
        self.assertIn("sans", str(caught.exception))


class TestDefaultFontsOnAMachineWithoutThem(unittest.TestCase):
    """The default chains must never be the reason a build fails.

    The house fonts are not installed everywhere — they are not on CI — and a
    document that asked for nothing must still export. The renderer falls back
    for the defaults; only a chain the settings file named is an error.
    """

    def _installed(self, *families):
        return patch.object(
            typography_module,
            "_installed_font_families",
            return_value=frozenset(name.casefold() for name in families),
        )

    def test_defaults_validate_where_none_of_them_is_installed(self):
        with self._installed("DejaVu Sans"):
            config = TypographyConfig()
        self.assertEqual(config.fonts["latin"].names, ["Linux Libertine O"])

    def test_a_settings_file_that_names_no_fonts_validates_too(self):
        with self._installed("DejaVu Sans"):
            TypographyConfig.model_validate({"page": {"paper": "a4paper"}})

    def test_but_a_named_font_that_is_missing_still_fails(self):
        with self._installed("DejaVu Sans"):
            with self.assertRaises(ValidationError):
                TypographyConfig.model_validate({"fonts": {"latin": "No Such Face"}})

    def test_naming_a_default_chain_explicitly_opts_into_the_check(self):
        """Writing it down is asking for it, whatever its value happens to be."""
        with self._installed("DejaVu Sans"):
            with self.assertRaises(ValidationError):
                TypographyConfig.model_validate(
                    {"fonts": {"latin": ["Linux Libertine O"]}}
                )


class TestFontResolution(unittest.TestCase):
    """The first installed name in a chain wins; none installed is an error."""

    def setUp(self):
        typography_module._installed_font_families.cache_clear()
        self.addCleanup(typography_module._installed_font_families.cache_clear)

    def _installed(self, *families):
        return patch.object(
            typography_module,
            "_installed_font_families",
            return_value=frozenset(name.casefold() for name in families),
        )

    def test_first_installed_name_wins(self):
        with self._installed("Ezra SIL", "FreeSerif"):
            self.assertEqual(
                resolve_font(["Frank Ruehl CLM", "Ezra SIL", "FreeSerif"]), "Ezra SIL"
            )

    def test_matching_ignores_case(self):
        with self._installed("freeserif"):
            self.assertEqual(resolve_font(["FreeSerif"]), "FreeSerif")

    def test_nothing_installed_is_an_error_naming_what_was_tried(self):
        with self._installed("DejaVu Sans"):
            with self.assertRaises(ValueError) as caught:
                resolve_font(["Frank Ruehl CLM", "Ezra SIL"])
        message = str(caught.exception)
        self.assertIn("Frank Ruehl CLM", message)
        self.assertIn("Ezra SIL", message)

    def test_no_fontconfig_defers_the_choice_to_the_renderer(self):
        with patch.object(typography_module.shutil, "which", return_value=None):
            self.assertIsNone(resolve_font(["A Font That Does Not Exist"]))

    def test_an_unresolvable_chain_fails_validation_naming_the_family(self):
        with self._installed("DejaVu Sans"):
            with self.assertRaises(ValidationError) as caught:
                TypographyConfig.model_validate({"fonts": {"hebrew": ["No Such Face"]}})
        message = str(caught.exception)
        self.assertIn("hebrew", message)
        self.assertIn("No Such Face", message)


class TestContradictorySettings(unittest.TestCase):
    def test_styling_notes_that_are_switched_off_is_an_error(self):
        """Both intentions cannot hold, and the one that silently wins deletes
        the notes."""
        with self.assertRaises(ValidationError) as caught:
            _validate({"notes": {"placement": "none"}, "styles": {"note": {"size": "9pt"}}})
        self.assertIn("placement", str(caught.exception))

    def test_switching_notes_off_alone_is_fine(self):
        config = _validate({"notes": {"placement": "none"}})
        self.assertEqual(config.notes.placement, NotePlacement.NONE)

    def test_running_head_all_cannot_be_combined_with_odd_or_even(self):
        with self.assertRaises(ValidationError):
            _validate({"page_header": {"all": {"left": "x"}, "odd": {"left": "y"}}})


class TestWhatTheUserWrote(unittest.TestCase):
    """The renderer emits a directive only for a setting that was written, so
    "written" has to stay distinguishable from "left at its default"."""

    def test_an_unwritten_field_is_not_in_fields_set(self):
        config = _validate({"line_numbers": {"increment": 10}})
        self.assertIn("increment", config.line_numbers.model_fields_set)
        self.assertNotIn("margin", config.line_numbers.model_fields_set)

    def test_a_field_written_at_its_default_value_still_counts_as_written(self):
        config = _validate({"line_numbers": {"increment": 5}})
        self.assertIn("increment", config.line_numbers.model_fields_set)


class TestTextStyle(unittest.TestCase):
    def test_an_empty_style_says_nothing(self):
        self.assertTrue(TextStyle().is_empty())
        self.assertFalse(TextStyle(weight=FontWeight.BOLD).is_empty())

    def test_a_font_family_accepts_a_list_or_a_string(self):
        self.assertEqual(FontFamily.model_validate("One").names, ["One"])
        self.assertEqual(FontFamily.model_validate(["One", "Two"]).names, ["One", "Two"])


if __name__ == "__main__":
    unittest.main()
