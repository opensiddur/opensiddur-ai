import json
import shutil
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.opensiddur_org.convert import (
    convert_post,
    load_context,
    plan_post,
    register_urns,
    select_posts,
)
from opensiddur.importer.opensiddur_org.licences import load_decisions
from opensiddur.importer.opensiddur_org.parse_post import parse_post
from opensiddur.importer.opensiddur_org.urns import PostUrns, save_post_urns
from opensiddur.tests.importer.opensiddur_org.support import (
    FIXTURES,
    NEW_PERSON,
    TRANSLATOR,
    make_post,
    write_data_dir,
)

URN = "urn:x-opensiddur:text:prayer:a_song"


class ConvertTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.registry = root / "registry"
        self.registry.mkdir()
        shutil.copy(FIXTURES / "contributor.jsonl", self.registry / "contributor.jsonl")
        (self.registry / "prayer.jsonl").write_text("", encoding="utf-8")
        self.projects = root / "project"
        self.projects.mkdir()
        self.post_urns = root / "post_urns.jsonl"
        self.posts = [
            make_post(101),
            make_post(102, slug="needs-urn"),
            make_post(103, slug="new-person", coauthors=[TRANSLATOR, NEW_PERSON]),
            make_post(104, slug="unlicensed", licence=""),
            make_post(502, slug="rejected"),
        ]
        self.data_dir = write_data_dir(root / "sources", self.posts)
        save_post_urns({pid: PostUrns(pid, "new", f"{URN}_{pid}") for pid in (101, 103, 104, 502)}, self.post_urns)
        self.context = load_context(
            self.data_dir, post_urns_path=self.post_urns, registry_directory=self.registry,
            decisions=load_decisions(FIXTURES / "licence_decisions.yaml"),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def plan(self, index: int):
        return plan_post(parse_post(self.posts[index]), self.context)


class TestPlans(ConvertTestCase):
    def test_standard(self) -> None:
        plan = self.plan(0)
        self.assertTrue(plan.standard, plan.reasons)
        self.assertEqual([column.lang for _, column, _ in plan.columns], ["he", "en"])

    def test_no_urn_decision(self) -> None:
        self.assertIn("no URN decision", self.plan(1).reasons)

    def test_unregistered_contributor(self) -> None:
        plan = self.plan(2)
        self.assertIn("unregistered contributor(s): new-person-transcription", plan.reasons)
        self.assertEqual(len(plan.candidates), 1)

    def test_undecided_licence_imports_nothing(self) -> None:
        plan = self.plan(3)
        self.assertEqual(plan.columns, [])
        self.assertTrue(plan.reasons[0].startswith("no column may be imported"))

    def test_rejected_post(self) -> None:
        self.assertEqual(set(self.plan(4).skipped_columns.values()), {"reject: Rejected after review."})

    def test_select_posts(self) -> None:
        self.assertEqual(select_posts(self.data_dir, posts=[101, 999], categories=None), [101])
        self.assertEqual(select_posts(self.data_dir, posts=None, categories=[201]), [103, 104])
        self.assertEqual(len(select_posts(self.data_dir, posts=None, categories=None)), 5)


class TestConversion(ConvertTestCase):
    def test_writes_valid_projects(self) -> None:
        written = convert_post(self.plan(0), self.context, self.projects, registry_directory=self.registry)
        self.assertEqual(written, ["osp-101-he", "osp-101-en"])
        self.assertEqual(sorted(p.name for p in (self.projects / "osp-101-en").iterdir()), ["a-song.xml", "index.xml"])

    def test_removes_languages_the_post_no_longer_has(self) -> None:
        stale = self.projects / "osp-101-de"
        stale.mkdir()
        (stale / "index.xml").write_text("<x/>", encoding="utf-8")
        (self.projects / "osp-1010-de").mkdir()  # another post's project is left alone
        convert_post(self.plan(0), self.context, self.projects, registry_directory=self.registry)
        self.assertFalse(stale.exists())
        self.assertTrue((self.projects / "osp-1010-de").exists())

    def test_rerun_is_identical(self) -> None:
        convert_post(self.plan(0), self.context, self.projects, registry_directory=self.registry)
        before = {p: p.read_bytes() for p in self.projects.rglob("*.xml")}
        convert_post(self.plan(0), self.context, self.projects, registry_directory=self.registry)
        self.assertEqual(before, {p: p.read_bytes() for p in self.projects.rglob("*.xml")})

    def test_register_new_urns_once(self) -> None:
        self.assertEqual(register_urns([self.plan(0)], self.context, self.registry), 3)
        self.assertEqual(register_urns([self.plan(0)], self.context, self.registry), 0)
        lines = [json.loads(l) for l in (self.registry / "prayer.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([l["urn"] for l in lines], [f"{URN}_101", f"{URN}_101/1", f"{URN}_101/2"])
        self.assertEqual((lines[0]["label_en"], lines[0]["label_he"]), ("A Song", "שִׁירָה"))


if __name__ == "__main__":
    unittest.main()
