# -*- coding: utf-8 -*-
"""Tests for the envelope the hand-authored Birnbaum TEI is written into.

What is checked here is the scaffolding: that a header is well-formed, that a
conditional wraps its test the way the schema expects, that the writers put a file
where they say they do. The prayer texts themselves are data read off the scan --
`he_prayers` and `en_prayers` are lists of Hebrew and English, and asserting on their
contents would be transcribing the book a second time into a test. Where a prayer
list is used at all, it is a synthetic one.
"""

import unittest
from pathlib import Path
from unittest import mock
from tempfile import TemporaryDirectory

from lxml import etree

from opensiddur.importer.birnbaum_scan.build import common, front

NS = {"tei": "http://www.tei-c.org/ns/1.0", "j": "http://jewishliturgy.org/ns/jlptei/2"}

#: A fragment on its own has no namespace declarations, so parsing one means supplying
#: them. The writers only ever emit fragments into `document`, which does declare them.
WRAPPER = ('<root xmlns:tei="http://www.tei-c.org/ns/1.0" '
           'xmlns:j="http://jewishliturgy.org/ns/jlptei/2">%s</root>')


def fragment(text: str):
    return etree.fromstring(WRAPPER % text)


class FakeLeaf:
    """The one thing `pb` wants out of pages.json."""

    def __init__(self, leaf):
        self.leaf = leaf


#: A synthetic leaf table, so these tests do not turn into tests of pages.json.
LEAVES = {"81": FakeLeaf(105), "s2": FakeLeaf(1), "XI": FakeLeaf(12)}


def with_fake_leaves(case):
    """Point `common.pb` at LEAVES for the duration of one test."""
    patch = mock.patch.object(common, "_leaves", lambda: LEAVES)
    patch.start()
    case.addCleanup(patch.stop)


class TestPageBreak(unittest.TestCase):

    def setUp(self):
        with_fake_leaves(self)

    def test_deep_links_to_the_leaf_the_page_falls_on(self):
        element = fragment(common.pb("81"))[0]
        self.assertEqual(element.tag, "{%s}pb" % NS["tei"])
        self.assertEqual(element.get("n"), "81")
        self.assertEqual(element.get("ed"), common.SIGIL)
        self.assertEqual(element.get("facs"), f"{common.IA}/n105_medium.jpg")

    def test_front_matter_names_no_printing_and_may_be_designated_apart(self):
        """A leaf addressed as sN carries the designation the book's sequence implies,
        and no second @ed token: front matter is printed once."""
        element = fragment(common.pb("s2", sigil=common.FRONT_SIGIL, n="[2]"))[0]
        self.assertEqual(element.get("n"), "[2]")
        self.assertEqual(element.get("ed"), common.FRONT_SIGIL)
        self.assertEqual(element.get("facs"), f"{common.IA}/n1_medium.jpg")


class TestHeader(unittest.TestCase):

    def _header(self, **overrides):
        kw = dict(title_he="כותרת", title_en="Title", urn="urn:x-opensiddur:text:prayer:x",
                  project="test_project", first=1, last=2, lang="he")
        kw.update(overrides)
        return fragment(common.header(**kw))[0]

    def test_carries_the_urn_of_the_text_in_its_project(self):
        header = self._header()
        idno = header.find(".//tei:idno[@type='urn']", NS)
        self.assertEqual(idno.text, "urn:x-opensiddur:text:prayer:x@test_project")

    def test_points_at_the_project_source_bibl_with_a_page_range(self):
        header = self._header(first=81, last=97)
        self.assertEqual(header.find(".//tei:bibl/tei:ptr", NS).get("target"),
                         "/test_project/index#project_source_bibl")
        scope = header.find(".//tei:biblScope", NS)
        self.assertEqual((scope.get("from"), scope.get("to")), ("81", "97"))

    def test_omits_the_page_range_when_there_is_no_first_page(self):
        header = self._header(first=0, last=0)
        self.assertIsNone(header.find(".//tei:biblScope", NS))

    def test_a_hebrew_title_takes_an_english_one_as_its_alternate(self):
        titles = self._header().findall(".//tei:titleStmt/tei:title", NS)
        self.assertEqual([(t.get("type"), t.get("{http://www.w3.org/XML/1998/namespace}lang"))
                          for t in titles],
                         [("main", "he"), ("alt", "en")])

    def test_an_english_only_file_titles_itself_in_english(self):
        titles = self._header(title_he="").findall(".//tei:titleStmt/tei:title", NS)
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0].get("{http://www.w3.org/XML/1998/namespace}lang"), "en")

    def test_birnbaum_is_not_credited_as_a_contributor(self):
        """A respStmt records who digitised a text; he is the author of the one digitised."""
        names = [n.text for n in self._header().findall(".//tei:respStmt/tei:name", NS)]
        self.assertNotIn("Philip Birnbaum", names)


class TestDocument(unittest.TestCase):

    def test_wraps_a_body_in_a_tei_document_in_the_given_language(self):
        text = common.document(
            body="<tei:div/>", lang="en", title_he="", title_en="T",
            urn="urn:x-opensiddur:text:prayer:x", project="p", first=1, last=1)
        root = etree.fromstring(text.encode("utf-8"))
        self.assertEqual(root.tag, "{%s}TEI" % NS["tei"])
        self.assertEqual(root.get("{http://www.w3.org/XML/1998/namespace}lang"), "en")
        self.assertEqual(len(root.findall("./tei:text/tei:body/tei:div", NS)), 1)


class TestConditional(unittest.TestCase):

    def test_states_the_rubric_the_edition_prints_and_the_test_it_stands_for(self):
        element = fragment(common.cond(
            "c1", note="On a fast day add:",
            fs=common.feature(common.AGG, "taanit")))[0]
        self.assertEqual(element.get("{http://www.w3.org/XML/1998/namespace}id"), "c1")
        note = element.find("tei:note", NS)
        self.assertEqual((note.get("type"), note.text), ("instruction", "On a fast day add:"))
        feature = element.find("tei:fs/tei:f", NS)
        self.assertEqual(feature.get("name"), "taanit")
        self.assertEqual(feature.find("tei:binary", NS).get("value"), "true")

    def test_a_negated_condition_wraps_its_test_in_j_none(self):
        element = fragment(common.cond(
            "c2", fs=common.feature(common.HOL, "shabbat"), negate=True))[0]
        self.assertEqual(len(element.findall("j:none/tei:fs", NS)), 1)
        self.assertIsNone(element.find("tei:fs", NS))

    def test_a_condition_without_a_rubric_carries_no_note(self):
        element = fragment(common.cond("c3", fs=common.feature(common.AGG, "x")))[0]
        self.assertIsNone(element.find("tei:note", NS))

    def test_the_end_marker_targets_the_conditional_it_closes(self):
        element = fragment(common.endcond("c1"))[0]
        self.assertEqual(element.tag, "{%s}endConditional" % NS["j"])
        self.assertEqual(element.get("target"), "#c1")

    def test_a_feature_can_carry_a_value_other_than_a_binary(self):
        element = fragment(common.feature(
            common.HOL, "hanukkah", '<tei:numeric value="1" max="8"/>'))[0]
        numeric = element.find("tei:f/tei:numeric", NS)
        self.assertEqual((numeric.get("value"), numeric.get("max")), ("1", "8"))


class TestWrite(unittest.TestCase):

    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(common.set_project_directory, common.DEFAULT_PROJECT_DIRECTORY)

    def test_writes_the_named_file_into_the_project_it_is_pointed_at(self):
        directory = common.set_project_directory(self.temp_dir.name)
        self.assertEqual(directory, Path(self.temp_dir.name))
        path = common.write("a_project", "a_file", "<tei:TEI/>")
        self.assertEqual(path, directory / "a_project" / "a_file.xml")
        self.assertEqual(path.read_text(encoding="utf-8"), "<tei:TEI/>")


class TestUnitAssembly(unittest.TestCase):
    """The unit file holds document order and declares the service it is said at."""

    def setUp(self):
        from opensiddur.importer.birnbaum_scan.build import build_en, build_he

        self.build_he, self.build_en = build_he, build_en

    def test_every_service_is_declared_and_only_shaharit_is_true(self):
        """An undeclared setting is undefined, and undefined keeps the text: declaring
        shaharit alone would leave every other service's readings standing."""
        declaration = fragment(self.build_he.declaration())[0]
        service = declaration.find("tei:fs[@type='%s']" % common.SERVICE, NS)
        values = {f.get("name"): f.find("tei:binary", NS).get("value")
                  for f in service.findall("tei:f", NS)}
        self.assertEqual(values.pop("shaharit"), "true")
        self.assertTrue(values)
        self.assertEqual(set(values.values()), {"false"})

    def test_the_unit_transcludes_each_prayer_in_order_once(self):
        for build in (self.build_he, self.build_en):
            with self.subTest(build=build.__name__):
                body = fragment(build.unit_body())[0]
                targets = [t.get("target")
                           for t in body.findall(".//j:transclude", NS)]
                expected = [build.BY_NAME[name]["urn"] for name in self.build_he.ORDER]
                self.assertEqual(targets[:len(expected)], expected)
                self.assertEqual(len(targets), len(expected) + 1,
                                 "the abridged Amidah follows the ordered prayers")
                self.assertEqual(len(set(targets)), len(targets))

    def test_the_two_projects_transclude_the_same_urns(self):
        """Identical URNs under two project ids is what aligns the columns."""
        def targets(build):
            return [t.get("target")
                    for t in fragment(build.unit_body())[0].findall(".//j:transclude", NS)]

        self.assertEqual(targets(self.build_he), targets(self.build_en))


class TestBuilders(unittest.TestCase):

    def setUp(self):
        from opensiddur.importer.birnbaum_scan.build import build_en, build_he

        self.build_he, self.build_en = build_he, build_en
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(common.set_project_directory, common.DEFAULT_PROJECT_DIRECTORY)
        self.directory = Path(self.temp_dir.name)

    def test_each_builder_writes_an_index_a_unit_and_one_file_per_prayer(self):
        for build, project in ((self.build_he, common.PROJECT_HE),
                               (self.build_en, common.PROJECT_EN)):
            with self.subTest(project=project):
                build.main(["--project-directory", str(self.directory)])
                written = sorted(p.name for p in (self.directory / project).glob("*.xml"))
                self.assertIn("index.xml", written)
                self.assertIn("chol_shacharit_amidah.xml", written)
                # index, the unit, one file per prayer -- and, in the English
                # project, one per front-matter section Birnbaum wrote only in English.
                extra = len(front.SECTIONS) if project == common.PROJECT_EN else 0
                self.assertEqual(len(written), len(build.PRAYERS) + 2 + extra)

    def test_everything_written_parses_and_names_its_own_project(self):
        self.build_he.main(["--project-directory", str(self.directory)])
        for path in (self.directory / common.PROJECT_HE).glob("*.xml"):
            with self.subTest(file=path.name):
                root = etree.parse(str(path)).getroot()
                idno = root.find(".//tei:publicationStmt/tei:idno[@type='urn']", NS)
                self.assertTrue(idno.text.endswith("@" + common.PROJECT_HE))

    def test_the_english_index_records_whose_translation_it_is(self):
        """Birnbaum's authorship of the English is said beside the citation, not as a
        respStmt, which would credit him with digitising his own book."""
        from opensiddur.importer.birnbaum_scan.build.index import index as build_index
        index = etree.fromstring(build_index(
            project=common.PROJECT_EN, lang="en", front="").encode("utf-8"))
        notes = [n.text for n in index.findall(".//tei:sourceDesc//tei:note", NS)]
        self.assertTrue(any("translation" in (n or "") for n in notes))
        names = [n.text for n in index.findall(".//tei:respStmt/tei:name", NS)]
        self.assertNotIn("Philip Birnbaum", names)


if __name__ == "__main__":
    unittest.main()
