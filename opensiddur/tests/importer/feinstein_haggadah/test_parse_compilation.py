import unittest

SAMPLE_HTML = """
<table>
<tr>
<td><div class="liturgy"><h>קַדֵּשׁ</h></div></td>
<td><div class="english"><h3>Sanctification of the Day</h3><p>Kadesh</p></div></td>
</tr>
<tr>
<td><div class="liturgy">וַֽיְהִי־עֶ֥רֶב</div></td>
<td><div class="english"><p>Evening came</p></div></td>
</tr>
</table>
"""

HALLEL_NIRTZAH_HTML = """
<table>
<tr>
<td><div class="liturgy">הַלֵּל<br /></div></td>
<td><div class="english"><h3>Songs of Praise</h3></div></td>
</tr>
<tr>
<td><div class="liturgy">לֹא לָנוּ</div></td>
<td><div class="english"><p>Not unto us</p></div></td>
</tr>
<tr>
<td><div class="liturgy">נִרְצָה<br /></div></td>
<td><div class="english"><h3>Concluding Songs</h3></div></td>
</tr>
<tr>
<td><div class="liturgy">חֲסַל סִדּוּר פֶּסַח<br />כְּכָׇל מִשְׁפָּטוֹ</div></td>
<td><div class="english"><p>Completed</p><p>According to law</p></div></td>
</tr>
</table>
"""


class TestParseCompilation(unittest.TestCase):
    def test_parse_rows_extracts_h3_and_content(self) -> None:
        from opensiddur.importer.feinstein_haggadah.parse_compilation import (
            build_section_contents,
            parse_rows,
        )

        rows = parse_rows({"content": SAMPLE_HTML})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].h3_title, "Sanctification of the Day")
        self.assertIn("קַדֵּשׁ", rows[0].hebrew)
        self.assertIn("Evening came", rows[1].english)

        contents = build_section_contents(rows)
        self.assertIn("kadesh", contents)
        kadesh = contents["kadesh"]
        self.assertEqual(kadesh.blocks[0].kind, "head")
        self.assertIn("קַדֵּשׁ", kadesh.blocks[0].hebrew)
        self.assertEqual(kadesh.blocks[1].kind, "paragraph")

    def test_nirtzah_heading_goes_to_nirtzah_not_hallel(self) -> None:
        from opensiddur.importer.feinstein_haggadah.parse_compilation import (
            build_section_contents,
            parse_rows,
        )

        contents = build_section_contents(parse_rows({"content": HALLEL_NIRTZAH_HTML}))
        hallel = contents["hallel"]
        nirtzah = contents["nirtzah"]
        self.assertEqual(hallel.blocks[0].kind, "head")
        self.assertEqual(hallel.blocks[0].hebrew, "הַלֵּל")
        self.assertFalse(any("נִרְצָה" in block.hebrew for block in hallel.blocks))
        self.assertEqual(nirtzah.blocks[0].kind, "head")
        self.assertEqual(nirtzah.blocks[0].hebrew, "נִרְצָה")
        chasal = contents["chasal_siddur_pesach"]
        self.assertEqual(chasal.blocks[0].kind, "paragraph")
        self.assertTrue(chasal.blocks[0].hebrew.startswith("חֲסַל סִדּוּר פֶּסַח"))

    def test_subsection_incipit_is_not_head(self) -> None:
        from opensiddur.importer.feinstein_haggadah.parse_compilation import (
            build_section_contents,
            parse_rows,
            load_compilation_json,
        )

        contents = build_section_contents(parse_rows(load_compilation_json()))
        matzah = contents["matzah_zu"]
        self.assertEqual(matzah.blocks[0].kind, "paragraph")
        self.assertIn("מַצָּה זוּ", matzah.blocks[0].hebrew)
        vanitzak = contents["vanitzak_hashem"]
        self.assertFalse(any(block.kind == "head" for block in vanitzak.blocks))

    def test_english_instructions_become_notes(self) -> None:
        from opensiddur.importer.feinstein_haggadah.parse_compilation import (
            build_section_contents,
            load_compilation_json,
            parse_rows,
            split_parenthetical_instructions,
        )

        parts = split_parenthetical_instructions(
            "(On Shabbat begin here.) (Recite quietly:) And there was evening"
        )
        self.assertEqual(parts[0], ("instruction", "On Shabbat begin here."))
        self.assertEqual(parts[1], ("instruction", "Recite quietly:"))
        self.assertEqual(parts[2][0], "paragraph")

        contents = build_section_contents(parse_rows(load_compilation_json()))
        kadesh = contents["kadesh"]
        instructions = [b for b in kadesh.blocks if b.kind == "instruction"]
        self.assertTrue(instructions)
        self.assertIn("Shabbat", instructions[0].english)


class TestTeiBuilder(unittest.TestCase):
    def test_index_body_includes_head_and_transcludes(self) -> None:
        from opensiddur.importer.feinstein_haggadah.sections import SectionContent, TextBlock
        from opensiddur.importer.feinstein_haggadah.tei_builder import index_body

        section = SectionContent(
            slug="nirtzah",
            blocks=[TextBlock(kind="head", hebrew="נִרְצָה")],
        )
        body = index_body("nirtzah", ["chasal_siddur_pesach"], section, lang="he")
        self.assertIn("<tei:head>נִרְצָה</tei:head>", body)
        self.assertIn("nirtzah/chasal_siddur_pesach", body)
        self.assertNotIn("<tei:p>נִרְצָה</tei:p>", body)

    def test_content_body_emits_milestone_urns(self) -> None:
        from opensiddur.importer.feinstein_haggadah.sections import SectionContent, TextBlock
        from opensiddur.importer.feinstein_haggadah.tei_builder import content_body

        section = SectionContent(
            slug="kadesh",
            blocks=[
                TextBlock(kind="head", hebrew="קַדֵּשׁ"),
                TextBlock(
                    kind="paragraph",
                    hebrew="בָּרוּךְ",
                    starts_paragraph=True,
                ),
            ],
        )
        body = content_body("kadesh", section, lang="he")
        self.assertIn('<tei:milestone unit="paragraph" n="1" corresp="urn:x-opensiddur:text:haggadah:kadesh/1"/>', body)
        self.assertIn("<tei:head>קַדֵּשׁ</tei:head>", body)

    def test_content_body_emits_instruction_notes(self) -> None:
        from opensiddur.importer.feinstein_haggadah.sections import SectionContent, TextBlock
        from opensiddur.importer.feinstein_haggadah.tei_builder import content_body

        section = SectionContent(
            slug="kadesh",
            blocks=[
                TextBlock(kind="head", english="Sanctification of the Day"),
                TextBlock(
                    kind="instruction",
                    english="On Shabbat begin here.",
                    starts_paragraph=True,
                ),
                TextBlock(
                    kind="paragraph",
                    english="Blessed are You",
                    starts_paragraph=False,
                ),
            ],
        )
        body = content_body("kadesh", section, lang="en")
        self.assertIn('<tei:note type="instruction">On Shabbat begin here.</tei:note>', body)
        self.assertNotIn("(On Shabbat begin here.)", body)


if __name__ == "__main__":
    unittest.main()
