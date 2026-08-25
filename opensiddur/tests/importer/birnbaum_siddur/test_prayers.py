"""Tests for the prayer grouping that names the shared texts.

Foundation pages are synthesised here; nothing reads the real source tree.
"""

import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.birnbaum_siddur.prayers import (
    FOUNDATION_DIR,
    gather,
    load_boundary_fixes,
    main,
    parse_spans,
    report,
    strip_roles,
)
from opensiddur.importer.util.pages import birnbaum_siddur_source_text_directory


def span(name, body=""):
    return f"<קטע התחלה={name}/>{body}<קטע סוף={name}/>"


class StripRolesTestCase(unittest.TestCase):
    """A prayer is spread over sections that differ in role, not in content."""

    def test_role_suffixes_are_removed(self):
        for name in ("זכרנו לחיים הכל", "זכרנו לחיים מילים", "זכרנו לחיים הוראה"):
            with self.subTest(name=name):
                self.assertEqual(strip_roles(name), "זכרנו לחיים")

    def test_role_prefixes_are_removed(self):
        self.assertEqual(strip_roles("הערה על מוריד הטל"), "מוריד הטל")

    def test_a_prefix_ending_in_a_prepositional_letter_runs_into_the_name(self):
        # "כותרת לפרק א" is the heading of chapter one. Requiring a space after the
        # prefix left the name as "לפרק".
        self.assertEqual(strip_roles("כותרת לפרק א"), "פרק א")

    def test_a_trailing_number_is_an_edition_division(self):
        self.assertEqual(strip_roles("ברכת אבות 2"), "ברכת אבות")

    def test_a_trailing_hebrew_letter_is_kept(self):
        # The source uses it both ways: these are different chapters, while other pairs
        # are halves of one blessing. Stripping it fused six chapters into one group, so
        # they stay separate and review decides.
        self.assertEqual(strip_roles("פרק א"), "פרק א")
        self.assertNotEqual(strip_roles("פרק א"), strip_roles("פרק ב"))

    def test_stripping_never_empties_a_name(self):
        self.assertTrue(strip_roles("כותרת"))


class ParseSpansTestCase(unittest.TestCase):
    def test_nesting_is_recorded(self):
        spans, problems = parse_spans(
            f"<קטע התחלה=outer/>{span('inner')}<קטע סוף=outer/>"
        )
        self.assertEqual(problems, [])
        inner = next(s for s in spans if s.name == "inner")
        self.assertEqual(inner.parent, "outer")
        self.assertEqual(inner.depth, 1)

    def test_page_spans_are_excluded(self):
        # A page turn falls where it falls, so page spans cross prayer boundaries by
        # nature and are a separate layer.
        spans, _ = parse_spans(span("עמוד 81") + span("מחזור עמוד 104 ליום ראשון")
                               + span("אמת ויציב"))
        self.assertEqual([s.name for s in spans], ["אמת ויציב"])

    def test_an_unclosed_span_is_recovered_and_reported(self):
        spans, problems = parse_spans("<קטע התחלה=פתוח/>text")
        self.assertEqual(len(spans), 1)
        self.assertTrue(any("never closed" in p for p in problems))

    def test_overlapping_spans_are_recovered_and_reported(self):
        spans, problems = parse_spans(
            "<קטע התחלה=a/>x<קטע התחלה=b/>y<קטע סוף=a/>z<קטע סוף=b/>"
        )
        self.assertEqual(len(spans), 2)
        self.assertTrue(any("overlaps" in p for p in problems))

    def test_a_close_without_an_open_is_reported(self):
        _, problems = parse_spans("<קטע סוף=רפאים/>")
        self.assertTrue(any("without being opened" in p for p in problems))


class GatherTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        directory = birnbaum_siddur_source_text_directory(self.root) / FOUNDATION_DIR
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "תפילת העמידה.txt").write_text(
            span("כותרת לברכת אבות", "{{כותרת|x}}בִּרְכַּת אָבוֹת")
            + span("ברכת אבות הכל", span("ברכת אבות 1", "a") + span("ברכת אבות 2", "b"))
            + span("פרשת שמע מקור", "[[דברים ו/טעמים|דברים ו, ד-ט]]")
            + span("פרק א", "x")
            + span("פרק ב", "y"),
            encoding="utf-8",
        )
        self.prayers, self.problems = gather(self.root)
        self.by = {p.base: p for p in self.prayers}

    def test_sections_of_one_prayer_are_grouped(self):
        self.assertIn("ברכת אבות", self.by)
        self.assertEqual(len(self.by["ברכת אבות"].spans), 4)

    def test_a_heading_supplies_the_display_name(self):
        # The name somebody chose, rather than the section label.
        self.assertEqual(self.by["ברכת אבות"].heading, "בִּרְכַּת אָבוֹת")
        self.assertEqual(self.by["ברכת אבות"].slug, "birkat_avot")

    def test_chapters_are_not_fused(self):
        self.assertIn("פרק א", self.by)
        self.assertIn("פרק ב", self.by)

    def test_a_citation_is_captured(self):
        self.assertTrue(self.by["פרשת שמע"].citations)

    def test_headed_and_cited_groups_need_review(self):
        self.assertTrue(self.by["ברכת אבות"].needs_review)
        self.assertTrue(self.by["פרשת שמע"].needs_review)

    def test_a_missing_foundation_directory_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            gather(self.root / "nowhere")


class ReportTestCase(GatherTestCase):
    def test_the_report_separates_what_needs_review(self):
        text = report(self.prayers, self.problems)
        self.assertIn("Named by a heading in the source", text)
        self.assertIn("Scriptural citations", text)
        self.assertIn("Derived mechanically", text)

    def test_malformed_sections_are_reported(self):
        text = report(self.prayers, {"page": ["x: never closed"]})
        self.assertIn("Malformed sections in the source", text)

    def test_main_writes_the_report(self):
        out = self.root / "PRAYERS.md"
        self.assertEqual(main(["--sourcetexts-root", str(self.root),
                               "--report", "--output", str(out)]), 0)
        self.assertTrue(out.is_file())

    def test_main_reports_a_missing_tree(self):
        self.assertEqual(main(["--sourcetexts-root", str(self.root / "nowhere")]), 1)


if __name__ == "__main__":
    unittest.main()


class BoundaryFixTestCase(unittest.TestCase):
    """A hand correction closes a section the source never closed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        # An unclosed section, then a following one that would otherwise bound it.
        self.text = ("<קטע התחלה=פתוח/>אָלֶף בֵּית גִּימֶל דָּלֶת"
                     "<קטע התחלה=הבא/>x<קטע סוף=הבא/>")

    def test_without_a_correction_the_end_is_guessed(self):
        spans, problems = parse_spans(self.text)
        span = next(s for s in spans if s.name == "פתוח")
        self.assertTrue(span.end_inferred)
        self.assertTrue(any("never closed" in p for p in problems))

    def test_a_correction_closes_it_after_the_named_words(self):
        spans, problems = parse_spans(self.text, {"פתוח": "אלף בית"})
        span = next(s for s in spans if s.name == "פתוח")
        self.assertFalse(span.end_inferred)
        self.assertIn("בֵּית", self.text[span.start : span.end])
        self.assertNotIn("גִּימֶל", self.text[span.start : span.end])
        self.assertEqual(problems, [])

    def test_a_correction_matches_through_different_pointing(self):
        # Written from the printed page, which may point the words differently.
        spans, _ = parse_spans(self.text, {"פתוח": "אָלֶף בֵּית"})
        self.assertFalse(next(s for s in spans if s.name == "פתוח").end_inferred)

    def test_a_correction_that_does_not_match_is_reported_not_silent(self):
        spans, problems = parse_spans(self.text, {"פתוח": "nothing like this"})
        self.assertTrue(next(s for s in spans if s.name == "פתוח").end_inferred)
        self.assertTrue(any("not found" in p for p in problems))

    def test_corrections_load_from_disk(self):
        path = self.root / "fixes.jsonl"
        path.write_text(
            '{"page": "p", "section": "s", "ends_after": "words"}\n'
            "\n"
            "{not json}\n",
            encoding="utf-8",
        )
        loaded = load_boundary_fixes(path)
        self.assertEqual(loaded, {("p", "s"): "words"})

    def test_a_missing_corrections_file_is_not_an_error(self):
        self.assertEqual(load_boundary_fixes(self.root / "nope.jsonl"), {})
