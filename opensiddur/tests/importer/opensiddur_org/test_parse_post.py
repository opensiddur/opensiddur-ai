import unittest

from opensiddur.importer.opensiddur_org.parse_post import (
    FootnoteRef,
    Span,
    Text,
    licence_url,
    node_text,
    parse_coauthor,
    parse_post,
    post_id_from_path,
    split_title,
)
from opensiddur.tests.importer.opensiddur_org.support import (
    HEBREW_EN_ROWS,
    cell,
    make_post,
    table,
    two_column_content,
)


def kinds(nodes) -> list[str]:
    return [n.kind for n in nodes if isinstance(n, Span)]


class TestMetadata(unittest.TestCase):
    def test_title_parts_drop_emoji(self) -> None:
        self.assertEqual(split_title("&#x1F4AC; שִׁירָה | A Song"), ["שִׁירָה", "A Song"])

    def test_licence_url(self) -> None:
        self.assertEqual(
            licence_url("<a href='https://creativecommons.org/licenses/by/4.0/'>CC BY</a>"),
            "https://creativecommons.org/licenses/by/4.0/",
        )
        self.assertEqual(licence_url(""), "")
        self.assertEqual(licence_url("<a href='//creativecommons.org/x/'>x</a>"), "https://creativecommons.org/x/")

    def test_coauthor_qualifier(self) -> None:
        coauthor = parse_coauthor({"name": "Rivka (transcription &amp; naqdanut)",
                                   "profile_link": "https://opensiddur.org/profile/rivka-t"})
        self.assertEqual(coauthor.name, "Rivka")
        self.assertEqual(coauthor.qualifier, "transcription & naqdanut")
        self.assertEqual(coauthor.profile_slug, "rivka-t")

    def test_post_id_from_export_path(self) -> None:
        self.assertEqual(post_id_from_path("posts/prayers/x/some-slug_(12345).json"), 12345)
        self.assertIsNone(post_id_from_path("posts/posts.json"))

    def test_source_dates(self) -> None:
        post = parse_post(make_post(date_src=("1440-00-00", "1500-00-00")))
        self.assertEqual((post.date_src_start, post.date_src_end), ("1440-00-00", "1500-00-00"))


class TestTable(unittest.TestCase):
    def setUp(self) -> None:
        self.post = parse_post(make_post())

    def test_columns(self) -> None:
        self.assertEqual([(c.role, c.lang) for c in self.post.columns], [("source", "he"), ("translation", "en")])

    def test_lines_and_stanza_gaps(self) -> None:
        hebrew = self.post.rows[1].cells[0]
        self.assertEqual([b.kind for b in hebrew.blocks], ["stanza", "stanza"])
        self.assertEqual([node_text(line) for line in hebrew.blocks[0].lines], ["אשִׁירָה", "לְךָ"])
        self.assertEqual([node_text(line) for line in hebrew.blocks[1].lines], ["שִׁיר שֵׁנִי"])

    def test_semantic_spans(self) -> None:
        english = self.post.rows[0].cells[1].blocks[0]
        self.assertEqual(kinds(english.lines[1]), ["divine", "divine"])
        self.assertEqual(node_text(english.lines[1]), "Adonai our God")
        self.assertEqual(kinds(self.post.rows[1].cells[0].blocks[0].lines[0]), ["acrostic"])
        self.assertIn("citation", kinds(self.post.rows[1].cells[1].blocks[1].lines[0]))
        self.assertEqual(kinds(self.post.rows[1].cells[1].blocks[0].lines[0]), ["italic"])

    def test_intro(self) -> None:
        self.assertEqual([node_text(line) for line in self.post.intro], ["An introduction."])

    def test_text_is_stored_decomposed(self) -> None:
        import unicodedata

        text = node_text(self.post.rows[0].cells[0].blocks[0].lines[0])
        self.assertEqual(text, unicodedata.normalize("NFKD", text))


class TestFootnotes(unittest.TestCase):
    def test_footnote_text_comes_from_the_tooltip(self) -> None:
        body = (
            'To You<span class="footnote_referrer"><a><sup>[1]</sup></a>'
            '<span class="footnote_tooltip"> A <em>note</em>.&nbsp;</span></span>'
            "<script type=\"text/javascript\"> jQuery('#x').tooltip({ tip: '#y' });</script>"
        )
        post = parse_post(make_post(content=table(["Translation (English)"], [[cell("eng-Latn", "english", body)]])))
        line = post.rows[0].cells[0].blocks[0].lines[0]
        notes = [n for n in line if isinstance(n, FootnoteRef)]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].number, 1)
        self.assertEqual(node_text(notes[0].note), "A note.")
        self.assertEqual(node_text(line), "To You")
        self.assertNotIn("jQuery", node_text(line))


class TestIrregularLayouts(unittest.TestCase):
    def test_three_columns_with_transliteration(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", "שָׁלוֹם"),
                 cell("eng-Latn", "romanized-transliteration", "shalom"),
                 cell("eng-Latn", "english", "peace")]]
        post = parse_post(make_post(content=table(
            ["Source (Hebrew)", "Transliteration (romanized Hebrew)", "Translation (English)"], rows)))
        self.assertEqual([c.lang for c in post.columns], ["he", "he-Latn", "en"])
        # The header names a language the markup contradicts.
        self.assertTrue(post.columns[1].mismatch)

    def test_transliteration_markup_without_its_script(self) -> None:
        rows = [[cell("jrb", "romanized-transliteration", "salam")]]
        post = parse_post(make_post(content=table(["Transliteration (Judeo-Arabic)"], rows)))
        self.assertEqual(post.columns[0].lang, "jrb-Latn")
        self.assertEqual(post.columns[0].mismatch, "")

    def test_empty_contribute_column(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", ""), cell("eng-Latn", "english", "A prayer")]]
        post = parse_post(make_post(content=table(["Contribute a translation", "Source (English)"], rows)))
        self.assertEqual(post.columns[0].role, "contribute")
        self.assertTrue(post.rows[0].cells[0].is_empty)

    def test_contribute_column_with_text_is_a_source(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", "שָׁלוֹם"), cell("eng-Latn", "english", "Peace")]]
        post = parse_post(make_post(content=table(["Contribute a translation", "Source (English)"], rows)))
        self.assertEqual((post.columns[0].role, post.columns[0].lang), ("source", "he"))

    def test_paragraph_cells_are_prose(self) -> None:
        rows = [[cell("eng-Latn", "english", "<p>One paragraph.</p><p>Another.</p>")]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertEqual([b.kind for b in post.rows[0].cells[0].blocks], ["paragraph", "paragraph"])

    def test_heading_in_a_cell(self) -> None:
        rows = [[cell("eng-Latn", "english", "<h3>Part One</h3>")], [cell("eng-Latn", "english", "Text")]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertEqual(post.rows[0].cells[0].blocks[0].kind, "heading")

    def test_short_rows_are_padded(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", "שָׁלוֹם")]]
        post = parse_post(make_post(content=table(["Source (Hebrew)", "Translation (English)"], rows)))
        self.assertEqual(len(post.rows[0].cells), 2)
        self.assertTrue(post.rows[0].cells[1].is_empty)

    def test_colour_alignment_is_noticed(self) -> None:
        rows = [[cell("eng-Latn", "english", '<span style="color: #f00">red</span> words')]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertTrue(post.has_colour_alignment)


class TestSurroundings(unittest.TestCase):
    def test_notes_and_sources(self) -> None:
        content = two_column_content(notes="<p>Published in 1842.</p>") + (
            "<h3>Source(s)</h3>"
            '<div class="wp-caption"><a href="https://opensiddur.org/scan.jpg"><img src="t.jpg" /></a>'
            '<p class="wp-caption-text">Page 21</p></div>'
            "<style>.x{}</style><script>var x;</script>"
            '<iframe src="https://archive.org/stream/book#page/20"></iframe>'
        )
        post = parse_post(make_post(content=content))
        self.assertEqual([node_text(line) for line in post.notes], ["Published in 1842."])
        self.assertEqual([(s.caption, s.url) for s in post.sources], [
            ("Page 21", "https://opensiddur.org/scan.jpg"),
            ("", "https://archive.org/stream/book#page/20"),
        ])

    def test_prose_post_without_a_table(self) -> None:
        post = parse_post(make_post(content='<p>Intro</p><div class="english" lang="eng-Latn">A prayer<br />in lines</div>'))
        self.assertEqual(post.columns, [])
        self.assertEqual(len(post.loose_cells), 1)

    def test_file_links_and_embeds(self) -> None:
        post = parse_post(make_post(content='<p><a class="mtli_attachment mtli_pdf" href="https://x/y.pdf">PDF</a></p>'))
        self.assertEqual(post.file_links, ["https://x/y.pdf"])

    def test_rows_fixture_is_unchanged(self) -> None:
        # Guards the shared fixture the other tests rely on.
        self.assertEqual(len(HEBREW_EN_ROWS), 2)
        self.assertIsInstance(parse_post(make_post()).rows[0].cells[0].blocks[0].lines[0][0], Text)


if __name__ == "__main__":
    unittest.main()
