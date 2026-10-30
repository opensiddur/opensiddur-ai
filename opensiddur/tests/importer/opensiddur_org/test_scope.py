import json
import unittest

from opensiddur.importer.opensiddur_org.parse_post import parse_post
from opensiddur.importer.opensiddur_org.scope import (
    content_scope,
    descendant_categories,
    imported_columns,
    irregularities,
    is_heading_row,
    posts_in_categories,
)
from opensiddur.tests.importer.opensiddur_org.support import FIXTURES, cell, make_post, table


class TestCategories(unittest.TestCase):
    def setUp(self) -> None:
        self.categories = json.loads((FIXTURES / "categories.json").read_text(encoding="utf-8"))

    def test_descendants(self) -> None:
        self.assertEqual(descendant_categories(self.categories, {1132}), {1132, 200, 201})
        self.assertEqual(descendant_categories(self.categories, {200}), {200, 201})

    def test_posts(self) -> None:
        self.assertEqual(posts_in_categories(self.categories, {200, 201}), {101, 102, 103, 104, 105})


class TestContentScope(unittest.TestCase):
    def test_table_with_text(self) -> None:
        self.assertTrue(content_scope(parse_post(make_post())).in_scope)

    def test_index_post(self) -> None:
        scope = content_scope(parse_post(make_post(slug="list-of-prayers")))
        self.assertEqual((scope.in_scope, scope.reason), (False, "index post"))

    def test_prose_body(self) -> None:
        post = parse_post(make_post(content='<div class="english" lang="eng-Latn">A prayer</div>'))
        self.assertEqual(content_scope(post).reason, "prose")

    def test_file_link_only(self) -> None:
        post = parse_post(make_post(content='<p>See <a class="mtli_pdf" href="https://x/y.pdf">the PDF</a>.</p>'))
        self.assertEqual((content_scope(post).in_scope, content_scope(post).reason), (False, "file link only"))

    def test_embed_only(self) -> None:
        post = parse_post(make_post(content='<iframe src="https://archive.org/embed/x"></iframe>'))
        self.assertEqual(content_scope(post).reason, "embed only")

    def test_essay(self) -> None:
        post = parse_post(make_post(content="<p>Some thoughts on prayer.</p>"))
        self.assertEqual(content_scope(post).reason, "no prayer text")

    def test_only_an_empty_contribute_column_is_not_text(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", "")]]
        post = parse_post(make_post(content=table(["Contribute a translation"], rows)))
        self.assertFalse(content_scope(post).in_scope)


class TestIrregularities(unittest.TestCase):
    def test_standard_post(self) -> None:
        self.assertEqual(irregularities(parse_post(make_post())), [])

    def test_source_only_post_is_standard(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", ""), cell("eng-Latn", "english", "A prayer")]]
        post = parse_post(make_post(content=table(["Contribute a translation", "Source (English)"], rows)))
        self.assertEqual(irregularities(post), [])
        self.assertEqual([c.lang for _, c in imported_columns(post)], ["en"])

    def test_header_and_markup_disagree(self) -> None:
        rows = [[cell("heb-Hebr", "liturgy", "שלום"), cell("eng-Latn", "romanized-transliteration", "shalom")]]
        post = parse_post(make_post(content=table(["Source (Hebrew)", "Transliteration (romanized Hebrew)"], rows)))
        self.assertTrue(any("markup says" in r for r in irregularities(post)))

    def test_two_columns_in_one_language(self) -> None:
        rows = [[cell("eng-Latn", "english", "One"), cell("eng-Latn", "english", "Two")]]
        post = parse_post(make_post(content=table(["Translation (English)", "Translation (English)"], rows)))
        self.assertIn("two columns in en", irregularities(post))

    def test_verse_and_prose_in_one_column(self) -> None:
        rows = [[cell("eng-Latn", "english", "A line<br />another")],
                [cell("eng-Latn", "english", "<p>A paragraph.</p>")]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertTrue(any("mixes verse and prose" in r for r in irregularities(post)))

    def test_heading_rows_are_sections(self) -> None:
        rows = [[cell("eng-Latn", "english", "<h3>Part One</h3>")], [cell("eng-Latn", "english", "Text")]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertTrue(is_heading_row(post, 0))
        self.assertEqual(irregularities(post), [])

    def test_heading_beside_text_is_irregular(self) -> None:
        rows = [[cell("eng-Latn", "english", "<h3>Part One</h3><p>Text</p>")]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertIn("a heading inside a cell of text", irregularities(post))

    def test_prose_without_a_table(self) -> None:
        post = parse_post(make_post(content='<div class="english" lang="eng-Latn">A prayer</div>'))
        self.assertEqual(irregularities(post), ["prose with no table"])

    def test_colour_alignment(self) -> None:
        rows = [[cell("eng-Latn", "english", '<span style="color: red">x</span>')]]
        post = parse_post(make_post(content=table(["Source (English)"], rows)))
        self.assertIn("colour-coded alignment", irregularities(post))


if __name__ == "__main__":
    unittest.main()
