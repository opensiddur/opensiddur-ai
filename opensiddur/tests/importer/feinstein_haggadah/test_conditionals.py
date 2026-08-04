"""Tests for the haggadah's conditional passages."""

import re
import unittest

from opensiddur.importer.feinstein_haggadah.conditionals import (
    ALTERNATES,
    Alternate,
    CONDITIONALS,
    CONDITIONS,
    RUBRIC_CONDITIONS,
    VARIANT_RUBRIC_SECTIONS,
    Conditional,
    ConditionalError,
    Inline,
    Paragraphs,
    Transclusion,
    condition_for_rubric,
    variant_urn,
)
from opensiddur.importer.feinstein_haggadah.parse_compilation import (
    build_section_contents,
    load_compilation_json,
    parse_rows,
)
from opensiddur.importer.feinstein_haggadah.sections import (
    SectionContent,
    TextBlock,
    urn_for_section,
)
from opensiddur.importer.feinstein_haggadah.tei_builder import (
    _alternate_xml,
    section_body,
    tei_document,
)
from opensiddur.importer.util.validation import validate


def _sections():
    return build_section_contents(parse_rows(load_compilation_json()))


def _strip_conditions(xml: str) -> str:
    """Collapse each condition to a marker, so the shape of the output is readable."""
    xml = re.sub(r"\s*<tei:fs.*?</tei:fs>\s*", "", xml, flags=re.DOTALL)
    xml = re.sub(r'<j:conditional xml:id="cond_([^"]+)">\s*</j:conditional>', r"[\1[", xml)
    xml = re.sub(r'<j:endConditional target="#cond_([^"]+)"/>', r"]\1]", xml)
    return xml


class TestConditionTable(unittest.TestCase):
    def test_cond_ids_are_unique(self):
        ids = [entry.cond_id for entry in CONDITIONALS]
        self.assertCountEqual(ids, set(ids))

    def test_every_entry_has_a_scope_in_at_least_one_language(self):
        for entry in CONDITIONALS:
            with self.subTest(entry.cond_id):
                self.assertTrue(
                    entry.scope_he is not None or entry.scope_en is not None,
                    "an entry with no scope in either language is never emitted",
                )

    def test_every_condition_validates_in_a_document(self):
        """A malformed feature structure would only surface as a jing error at write time."""
        for name, fragment in CONDITIONS.items():
            with self.subTest(name):
                self.assertTrue(self._validates(fragment), f"{name} did not validate")

    def test_variant_conditions_validate(self):
        for entry in CONDITIONALS:
            if entry.condition in CONDITIONS:
                continue
            with self.subTest(entry.cond_id):
                self.assertTrue(self._validates(entry.condition))

    @staticmethod
    def _validates(condition: str) -> bool:
        body = f"""<tei:body>
          <tei:div corresp="urn:x-opensiddur:text:haggadah:kadesh">
            <j:conditional xml:id="cond_test">{condition}</j:conditional>
            <tei:p>text</tei:p>
            <j:endConditional target="#cond_test"/>
          </tei:div>
        </tei:body>"""
        header = (
            '<tei:teiHeader xmlns:tei="http://www.tei-c.org/ns/1.0"><tei:fileDesc>'
            '<tei:titleStmt><tei:title type="main">t</tei:title></tei:titleStmt>'
            "<tei:publicationStmt><tei:distributor>d</tei:distributor>"
            '<tei:idno type="urn">urn:x-opensiddur:text:haggadah:kadesh@p</tei:idno>'
            "</tei:publicationStmt><tei:sourceDesc><tei:bibl>"
            '<tei:ptr target="urn:x-opensiddur:text:haggadah:kadesh@p"/>'
            "</tei:bibl></tei:sourceDesc></tei:fileDesc></tei:teiHeader>"
        )
        is_valid, _ = validate(tei_document(header, body, lang="he"))
        return is_valid


class TestVariantUrns(unittest.TestCase):
    def test_variant_urn_mirrors_the_text_urn(self):
        self.assertEqual(
            variant_urn("lefikach", "shira_chadasha"),
            urn_for_section("lefikach").replace(
                "urn:x-opensiddur:text:", "urn:x-opensiddur:condition:"
            )
            + "/shira_chadasha",
        )

    def test_variant_urn_carries_no_project(self):
        """A variant belongs to the text, not to the edition that prints it."""
        self.assertNotIn("@", variant_urn("korech", "pesach"))


class TestRubricConditions(unittest.TestCase):
    def test_unknown_rubric_raises(self):
        with self.assertRaises(ConditionalError) as caught:
            condition_for_rubric("on Tuesdays say:", "kadesh")
        self.assertIn("RUBRIC_CONDITIONS", str(caught.exception))

    def test_variant_rubric_without_a_section_entry_raises(self):
        with self.assertRaises(ConditionalError) as caught:
            condition_for_rubric("some add:", "kadesh")
        self.assertIn("VARIANT_RUBRIC_SECTIONS", str(caught.exception))

    def test_every_governing_rubric_in_the_source_is_known(self):
        """The conversion must not meet a conditional it cannot name."""
        for slug, section in _sections().items():
            for block in section.blocks:
                if block.governs:
                    with self.subTest(slug=slug, rubric=block.english):
                        condition_for_rubric(block.english, slug)

    def test_variant_rubric_sections_resolve(self):
        for slug in VARIANT_RUBRIC_SECTIONS:
            with self.subTest(slug):
                self.assertIn("opensiddur:variant", condition_for_rubric("some add:", slug))

    def test_rubric_table_has_no_unreachable_entries(self):
        """A rubric no longer in the source is a table entry that has gone stale."""
        seen = {
            block.english.strip()
            for section in _sections().values()
            for block in section.blocks
            if block.governs
        }
        self.assertEqual(set(RUBRIC_CONDITIONS) - seen, set())


class TestEmission(unittest.TestCase):
    """Each scope kind places its markers where it should."""

    def _body(self, slug: str, lang: str) -> str:
        return _strip_conditions(section_body(slug, _sections().get(slug), lang=lang))

    def test_inline_scope_replaces_the_brackets(self):
        body = self._body("lefikach", "he")
        self.assertIn("[lefikach_shira_chadasha[שִׁירָה חֲדָשָׁה]lefikach_shira_chadasha]", body)
        self.assertNotIn("(שִׁירָה חֲדָשָׁה)", body)

    def test_inline_scope_keeps_the_text_around_it(self):
        body = self._body("kadesh", "he")
        self.assertIn("וְנֹּאמַר", self._body("lefikach", "he"))
        self.assertIn("בְּאַהֲבָה", body)
        self.assertIn("מוֹעֲדִים לְשִׁמְחָה", body)

    def test_paragraph_scope_brackets_whole_paragraphs(self):
        body = self._body("kadesh", "he")
        opening = body.index("[kadesh_vayechulu[")
        closing = body.index("]kadesh_vayechulu]")
        between = body[opening:closing]
        self.assertIn('unit="paragraph" n="1"', between)
        self.assertNotIn('unit="paragraph" n="2"', between)

    def test_paragraph_range_covers_every_paragraph_in_it(self):
        body = self._body("barech", "he")
        between = body[body.index("[barech_zimmun["):body.index("]barech_zimmun]")]
        for number in range(1, 7):
            with self.subTest(paragraph=number):
                self.assertIn(f'unit="paragraph" n="{number}"', between)
        self.assertNotIn('unit="paragraph" n="7"', between)

    def test_transclusion_scope_wraps_only_its_own_child(self):
        body = _strip_conditions(
            section_body(
                "nirtzah",
                _sections().get("nirtzah"),
                lang="he",
                child_slugs=["it_happened_at_midnight", "ki_lo_na_eh"],
            )
        )
        between = body[
            body.index("[nirtzah_first_night["):body.index("]nirtzah_first_night]")
        ]
        self.assertIn("it_happened_at_midnight", between)
        self.assertNotIn("ki_lo_na_eh", between)

    def test_a_rubric_sits_inside_the_scope(self):
        """JLPTEI-3.md: a conditional-reading instruction goes inside the text it controls."""
        body = self._body("kadesh", "he")
        between = body[body.index("[kadesh_vayechulu["):body.index("]kadesh_vayechulu]")]
        self.assertIn('<tei:note type="instruction">בשבת מתחילין כאן</tei:note>', between)

    def test_an_editorial_note_sits_on_the_conditional_itself(self):
        """Shown only when the condition cannot be decided, unlike a source rubric."""
        body = section_body(
            "pre_seder",
            _sections().get("pre_seder"),
            lang="en",
            child_slugs=["eruv_tavshilin"],
        )
        marker = re.search(
            r'<j:conditional xml:id="cond_pre_seder_eruv_tavshilin">(.*?)</j:conditional>',
            body,
            re.DOTALL,
        )
        self.assertIsNotNone(marker)
        self.assertIn('<tei:note type="instruction">', marker.group(1))

    def test_markers_are_balanced_in_every_section(self):
        sections = _sections()
        for lang in ("he", "en"):
            for slug in sorted({entry.slug for entry in CONDITIONALS}):
                with self.subTest(lang=lang, slug=slug):
                    body = section_body(
                        slug,
                        sections.get(slug),
                        lang=lang,
                        child_slugs=[
                            scope.child_slug
                            for entry in CONDITIONALS
                            if entry.slug == slug
                            and isinstance(scope := entry.scope_for(lang), Transclusion)
                        ],
                    )
                    opened = re.findall(r'<j:conditional xml:id="cond_([^"]+)"', body)
                    closed = re.findall(r'<j:endConditional target="#cond_([^"]+)"', body)
                    self.assertCountEqual(opened, closed)


class TestAlternates(unittest.TestCase):
    def test_alternate_becomes_a_choice_of_options(self):
        body = section_body("barech", _sections().get("barech"), lang="he")
        choice = re.search(r"<tei:choice>.*?</tei:choice>", body, re.DOTALL)
        self.assertIsNotNone(choice)
        self.assertEqual(choice.group().count("<j:option"), 2)
        self.assertIn('xml:lang="yi"', choice.group())

    def test_alternate_wording_absent_from_the_source_raises(self):
        """A hand-written option must not stand in for wording no longer in the source."""
        alternate = Alternate(
            slug="barech",
            lang="he",
            paragraph=1,
            options=(("he", "הב לן ונברך"), ("yi", "מלה שאיננה שם")),
        )
        with self.assertRaises(ConditionalError) as caught:
            _alternate_xml(alternate, "הב לן ונברך", "barech")
        self.assertIn("not in the source text", str(caught.exception))

    def test_every_alternate_names_a_real_section(self):
        sections = _sections()
        for entry in ALTERNATES:
            with self.subTest(entry.slug):
                self.assertIn(entry.slug, sections)


class TestAnchorsResolve(unittest.TestCase):
    """Every curated anchor must still match. A source rewording must fail, not go quiet."""

    def test_every_scope_resolves_against_the_source(self):
        sections = _sections()
        for lang in ("he", "en"):
            for slug in sorted({entry.slug for entry in CONDITIONALS}):
                with self.subTest(lang=lang, slug=slug):
                    section_body(slug, sections.get(slug), lang=lang)

    def test_an_unmatched_anchor_raises(self):
        section = SectionContent(
            slug="lefikach",
            blocks=[
                TextBlock(kind="paragraph", hebrew="אין כאן שום דבר", starts_paragraph=True)
            ],
        )
        with self.assertRaises(Exception) as caught:
            section_body("lefikach", section, lang="he")
        self.assertIn("lefikach_shira_chadasha", str(caught.exception))


class TestScopeKinds(unittest.TestCase):
    def test_paragraphs_through_defaults_to_first(self):
        self.assertEqual(Paragraphs(4).through, 4)
        self.assertEqual(Paragraphs(4, 9).through, 9)

    def test_inline_is_bracketed_unless_told_otherwise(self):
        self.assertTrue(Inline("a", "b", "c", "d").bracketed)
        self.assertFalse(Inline("a", "b", "c", "d", bracketed=False).bracketed)

    def test_scope_for_selects_by_language(self):
        entry = Conditional(
            slug="x",
            cond_id="x",
            condition="shabbat",
            scope_he=Paragraphs(1),
            scope_en=Paragraphs(2),
        )
        self.assertEqual(entry.scope_for("he"), Paragraphs(1))
        self.assertEqual(entry.scope_for("en"), Paragraphs(2))


if __name__ == "__main__":
    unittest.main()
