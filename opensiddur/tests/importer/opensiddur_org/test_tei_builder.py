import re
import unittest

from lxml import etree

from opensiddur.importer.opensiddur_org.contributors import Contributors, post_credits
from opensiddur.importer.opensiddur_org.licences import LICENCES, LicenceDecision
from opensiddur.importer.opensiddur_org.parse_post import parse_post
from opensiddur.importer.opensiddur_org.scope import imported_columns
from opensiddur.importer.opensiddur_org.tei_builder import (
    build_project,
    front_language,
    iso_date,
    text_file_stem,
)
from opensiddur.importer.opensiddur_org.urns import PostUrns
from opensiddur.importer.util.prettify import prettify_xml
from opensiddur.importer.util.validation import validate
from opensiddur.tests.importer.opensiddur_org.support import (
    FIXTURES,
    PRINT_TRANSLATOR,
    TRANSCRIBER,
    TRANSLATOR,
    cell,
    make_post,
    table,
    two_column_content,
)

NS = {"tei": "http://www.tei-c.org/ns/1.0", "j": "http://jewishliturgy.org/ns/jlptei/2"}
URN = "urn:x-opensiddur:text:prayer:a_song"
ALLOW = LicenceDecision("allow", LICENCES["cc-by-sa-4.0"])


def project_id(lang: str) -> str:
    return f"a_song-poet-2020-{lang.lower()}"


def build(post_data=None, *, urns: PostUrns | None = None, licence: LicenceDecision = ALLOW, with_front=None):
    post = parse_post(post_data or make_post())
    contributors = Contributors.load(FIXTURES / "contributors_by_id.json")
    credits = post_credits(post, contributors)
    urns = urns or PostUrns(post.post_id, "new", URN)
    out = {}
    for index, column in imported_columns(post):
        files = build_project(
            post, index, column, urns=urns, credits=credits, licence=licence,
            upstream_commit="0123456789abcdef", upstream_commit_date="2026-10-01",
            with_front=column.lang == "en" if with_front is None else with_front,
            project_id=project_id(column.lang),
        )
        out[column.lang] = files
    return post, out


def compact(document: str) -> str:
    return re.sub(r">\s*\n\s*<", "><", document)


def tree(document: str):
    return etree.fromstring(prettify_xml(compact(document), keep_blank_text=True).encode("utf-8"))


class TestDocuments(unittest.TestCase):
    def setUp(self) -> None:
        self.post, self.projects = build()

    def text_of(self, lang: str):
        files = self.projects[lang].files
        return tree(files[text_file_stem(URN)])

    def test_project_per_language(self) -> None:
        self.assertEqual(sorted(self.projects), ["en", "he"])
        self.assertEqual(self.projects["en"].project_id, "a_song-poet-2020-en")
        self.assertEqual(sorted(self.projects["en"].files), ["a_song", "index"])

    def test_text_file_is_named_from_the_urn(self) -> None:
        self.assertEqual(text_file_stem(URN), "a_song")
        self.assertEqual(text_file_stem("urn:x-opensiddur:text:poem:maoz_tzur/1@p-he#x"), "maoz_tzur_1")

    def test_every_document_validates(self) -> None:
        for lang, files in self.projects.items():
            for name, document in files.files.items():
                valid, errors = validate(prettify_xml(compact(document), remove_xml_declaration=True, keep_blank_text=True))
                self.assertTrue(valid, f"{lang}/{name}: {errors}")

    def test_rows_align_across_languages(self) -> None:
        def milestones(lang):
            return [m.get("corresp") for m in self.text_of(lang).iterfind(".//tei:milestone", NS)]

        self.assertEqual(milestones("he"), [f"{URN}/1", f"{URN}/2"])
        self.assertEqual(milestones("he"), milestones("en"))

    def test_stanza_gap_splits_line_groups(self) -> None:
        self.assertEqual(len(self.text_of("he").findall(".//tei:lg", NS)), 3)

    def test_inline_markup(self) -> None:
        english = self.text_of("en")
        self.assertEqual([d.text for d in english.iterfind(".//j:divineName", NS)], ["Adonai", "our God"])
        # The space between two adjacent names survives pretty-printing.
        line = english.find(".//tei:l[2]", NS)
        self.assertEqual("".join(line.itertext()), "Adonai our God")
        self.assertEqual(english.find(".//tei:hi[@rend='italic']", NS).text, "sing")
        self.assertEqual(english.find(".//tei:body//tei:bibl", NS).text, "(Psalms 1:1)")
        self.assertEqual(self.text_of("he").find(".//tei:seg[@type='acrostic']", NS).text, "א")

    def test_header_points_at_the_index(self) -> None:
        ptr = self.text_of("en").find(".//tei:sourceDesc/tei:bibl/tei:ptr", NS)
        self.assertEqual(ptr.get("target"), "/a_song-poet-2020-en/index#project_source_bibl")

    def test_index_bibl(self) -> None:
        index = tree(self.projects["en"].files["index"])
        bibl = index.find(".//tei:bibl[@{http://www.w3.org/XML/1998/namespace}id='project_source_bibl']", NS)
        self.assertEqual(bibl.find("tei:author", NS).text, "Yehudah Poet")
        # Cited by post ID first, so the bibliography's link survives a category move.
        self.assertEqual(bibl.find("tei:idno[@type='url']", NS).text, "https://opensiddur.org/?p=101")
        self.assertEqual(bibl.find("tei:idno[@type='opensiddur.org']", NS).text, "101")
        # The permalink changes when the post moves category, so it is not kept.
        self.assertIsNone(bibl.find("tei:idno[@type='permalink']", NS))
        self.assertEqual(len(bibl.findall("tei:idno[@type='url']", NS)), 1)
        self.assertEqual(bibl.find("tei:date[@type='accessed']", NS).get("when"), "2026-10-01")
        transclude = index.find(".//j:transclude", NS)
        self.assertEqual(transclude.get("target"), URN)

    def test_titles(self) -> None:
        titles = tree(self.projects["en"].files["index"]).findall(".//tei:titleStmt/tei:title", NS)
        self.assertEqual([(t.get("type"), t.text) for t in titles], [("alt", "שִׁירָה"), ("main", "A Song")])

    def test_front_matter_is_gated_paratext(self) -> None:
        index = tree(self.projects["en"].files["index"])
        condition = index.find(".//tei:front/j:conditional//tei:fs", NS)
        self.assertEqual(condition.get("type"), "opensiddur:paratext")
        self.assertIsNone(tree(self.projects["he"].files["index"]).find(".//tei:front", NS))

    def test_the_posts_own_words_are_a_colophon(self) -> None:
        post, projects = build(make_post(content=two_column_content(notes="<p>First published in 1842.</p>")))
        divs = tree(projects["en"].files["index"]).findall(".//tei:front/tei:div", NS)
        self.assertEqual([(d.get("type"), d.get("subtype")) for d in divs],
                         [("colophon", "introduction"), ("colophon", "notes")])


class TestCredits(unittest.TestCase):
    def resp(self, files):
        return [(r.find("tei:resp", NS).get("key"), r.find("tei:name", NS).get("ref"))
                for r in tree(files.files["index"]).findall(".//tei:titleStmt/tei:respStmt", NS)]

    def test_credits_by_column(self) -> None:
        _, projects = build(make_post(coauthors=[TRANSLATOR, TRANSCRIBER]))
        person = "urn:x-opensiddur:contributor:opensiddur.org/rivka-translator"
        self.assertEqual(self.resp(projects["en"]), [("trl", person)])
        self.assertEqual(self.resp(projects["he"]), [("trc", person)])

    def test_print_translator_is_credited_in_the_bibl(self) -> None:
        _, projects = build(make_post(coauthors=[PRINT_TRANSLATOR]))
        index = tree(projects["en"].files["index"])
        self.assertEqual(self.resp(projects["en"]), [])
        self.assertEqual(index.find(".//tei:sourceDesc//tei:respStmt/tei:name", NS).text, "Old Print Translator")


class TestOther(unittest.TestCase):
    def test_existing_urns(self) -> None:
        urns = PostUrns(101, "existing", "urn:x-opensiddur:text:poem:song",
                        {1: "urn:x-opensiddur:text:poem:song/1", 2: "urn:x-opensiddur:text:poem:song/2"})
        post, projects = build(urns=urns)
        text = tree(projects["he"].files["song"])
        self.assertEqual(text.find(".//tei:div", NS).get("corresp"), "urn:x-opensiddur:text:poem:song")
        self.assertEqual([m.get("corresp") for m in text.iterfind(".//tei:milestone", NS)],
                         ["urn:x-opensiddur:text:poem:song/1", "urn:x-opensiddur:text:poem:song/2"])

    def test_footnotes_are_standoff(self) -> None:
        body = 'You<span class="footnote_referrer"><a><sup>[1]</sup></a><span class="footnote_tooltip">A note.</span></span>'
        post, projects = build(make_post(content=table(["Translation (English)"], [[cell("eng-Latn", "english", body)]])))
        text = tree(projects["en"].files[text_file_stem(URN)])
        self.assertIsNotNone(text.find(".//tei:l/tei:anchor[@{http://www.w3.org/XML/1998/namespace}id='note_1']", NS))
        note = text.find("tei:standOff[@type='notes']/tei:note", NS)
        self.assertEqual((note.get("target"), note.find("tei:p", NS).text), ("#note_1", "A note."))

    def test_heading_rows_open_sections(self) -> None:
        rows = [[cell("eng-Latn", "english", "<h3>Part One</h3>")], [cell("eng-Latn", "english", "Text")]]
        post, projects = build(make_post(content=table(["Source (English)"], rows)))
        text = tree(projects["en"].files[text_file_stem(URN)])
        self.assertEqual(text.find(".//tei:div/tei:div/tei:head", NS).text, "Part One")
        self.assertEqual([m.get("corresp") for m in text.iterfind(".//tei:milestone", NS)], [f"{URN}/1"])

    def test_prose_uses_paragraph_milestones(self) -> None:
        rows = [[cell("eng-Latn", "english", "<p>One.</p>")]]
        post, projects = build(make_post(content=table(["Source (English)"], rows)))
        text = tree(projects["en"].files[text_file_stem(URN)])
        self.assertEqual(text.find(".//tei:milestone", NS).get("unit"), "paragraph")

    def test_licence_basis(self) -> None:
        decision = LicenceDecision("allow", LICENCES["pd-mark-1.0"], "United States Government work")
        _, projects = build(licence=decision)
        availability = tree(projects["he"].files["index"]).find(".//tei:availability", NS)
        self.assertEqual(availability.find("tei:licence", NS).get("target"), LICENCES["pd-mark-1.0"].url)
        self.assertEqual(availability.find("tei:p", NS).text, "United States Government work")

    def test_partial_dates(self) -> None:
        self.assertEqual(iso_date("1440-00-00"), "1440")
        self.assertEqual(iso_date("1834-05-00"), "1834-05")
        self.assertEqual(iso_date("2013-08-07"), "2013-08-07")
        self.assertEqual(iso_date(""), "")

    def test_front_language(self) -> None:
        post = parse_post(make_post())
        self.assertEqual(front_language(post, ["he", "en"]), "en")
        self.assertEqual(front_language(post, ["he"]), "he")

    def test_output_is_deterministic(self) -> None:
        _, first = build()
        _, second = build()
        self.assertEqual({k: v.files for k, v in first.items()}, {k: v.files for k, v in second.items()})



class TestReviewRegressions(unittest.TestCase):
    def test_title_scripts(self) -> None:
        from opensiddur.importer.opensiddur_org.tei_builder import titles_by_language

        post = parse_post(make_post(title="يَا حَنُكَّة | Ya Hanukkah"))
        self.assertEqual([lang for lang, _ in titles_by_language(post)], ["und-Arab", "en"])

    def test_front_matter_in_a_latin_language_other_than_english(self) -> None:
        post = parse_post(make_post())
        self.assertEqual(front_language(post, ["he", "de"]), "de")

    def test_footnote_inside_an_instruction_is_anchored_after_it(self) -> None:
        body = ('<span class="instruction">Stand<span class="footnote_referrer"><a><sup>[1]</sup></a>'
                '<span class="footnote_tooltip">Why.</span></span></span> and pray')
        post, projects = build(make_post(content=table(["Translation (English)"], [[cell("eng-Latn", "english", body)]])))
        text = tree(projects["en"].files[text_file_stem(URN)])
        line = text.find(".//tei:l", NS)
        self.assertEqual([etree.QName(c).localname for c in line], ["note", "anchor"])
        self.assertIsNotNone(text.find("tei:standOff/tei:note[@target='#note_1']", NS))

    def test_heading_keeps_every_line(self) -> None:
        rows = [[cell("eng-Latn", "english", "<h3>Part One<br />The Beginning</h3>")], [cell("eng-Latn", "english", "Text")]]
        post, projects = build(make_post(content=table(["Source (English)"], rows)))
        head = tree(projects["en"].files[text_file_stem(URN)]).find(".//tei:div/tei:div/tei:head", NS)
        self.assertEqual("".join(head.itertext()), "Part One The Beginning")


if __name__ == "__main__":
    unittest.main()
