"""The download against a synthetic export: a git repository made in a temporary directory."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.opensiddur_org.download import (
    CATEGORIES_PATH,
    CONTRIBUTORS_PATH,
    Upstream,
    download,
    load_manifest,
)
from opensiddur.tests.importer.opensiddur_org.support import FIXTURES, make_post


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.org", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


class TestDownload(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.export = root / "export"
        self.export.mkdir()
        git(self.export, "init", "-q", "-b", "master")
        for target, source in ((CATEGORIES_PATH, "categories.json"), (CONTRIBUTORS_PATH, "contributors_by_id.json")):
            path = self.export / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text((FIXTURES / source).read_text(encoding="utf-8"), encoding="utf-8")
        self.write_post("prayers/festivals", make_post(101))
        self.write_post("prayers/festivals", make_post(102, slug="essay", content="<p>Thoughts.</p>"))
        self.write_post("prayers/hanukkah", make_post(103, slug="lights"))
        self.write_post("essays", make_post(901, slug="not-a-prayer"))
        self.first = self.commit("2026-09-01")
        self.clone = Upstream(root / "clone")
        self.clone.ensure(fetch=False, url=str(self.export))
        self.data_dir = root / "sources" / "opensiddur_org"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_post(self, folder: str, post: dict) -> None:
        path = self.export / "posts" / folder / f"{post['slug']}_({post['post_id']}).json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(post, ensure_ascii=False), encoding="utf-8")

    def commit(self, message: str) -> str:
        git(self.export, "add", "-A")
        git(self.export, "commit", "-q", "-m", message)
        return git(self.export, "rev-parse", "HEAD")

    def run_download(self, **kwargs):
        self.clone.ensure(fetch=True)
        return download(upstream=self.clone, ref="origin/master", data_dir=self.data_dir, **kwargs)

    def test_copies_in_scope_posts_flat(self) -> None:
        result = self.run_download()
        self.assertEqual(sorted(p.name for p in (self.data_dir / "posts").iterdir()), ["101.json", "103.json"])
        self.assertEqual(result.out_of_scope, {102: "no prayer text"})
        manifest = load_manifest(self.data_dir)
        self.assertEqual(manifest["upstream_commit"], self.first)
        self.assertEqual(manifest["posts"]["103"]["path"], "posts/prayers/hanukkah/lights_(103).json")
        self.assertTrue((self.data_dir / "contributors_by_id.json").is_file())

    def test_same_commit_is_a_no_op(self) -> None:
        self.run_download()
        before = {p: p.stat().st_mtime_ns for p in self.data_dir.rglob("*")}
        self.assertTrue(self.run_download().noop)
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in self.data_dir.rglob("*")})

    def test_only_a_changed_last_updated_rewrites_a_post(self) -> None:
        self.run_download()
        # A re-save that changes the file but not last_updated is not a change.
        resaved = make_post(101)
        resaved["excerpt"] = "re-saved"
        self.write_post("prayers/festivals", resaved)
        self.write_post("prayers/hanukkah", make_post(103, slug="lights", last_updated="2026-09-30"))
        self.commit("2026-10-01")
        result = self.run_download()
        self.assertEqual(result.written, [103])
        stored = json.loads((self.data_dir / "posts" / "101.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["excerpt"], "")

    def test_moved_and_deleted_posts(self) -> None:
        self.run_download()
        (self.export / "posts" / "prayers" / "festivals" / "a-song_(101).json").rename(
            self.export / "posts" / "prayers" / "hanukkah" / "a-song_(101).json")
        (self.export / "posts" / "prayers" / "hanukkah" / "lights_(103).json").unlink()
        self.commit("2026-10-01")
        result = self.run_download()
        self.assertEqual((result.written, result.removed), ([], [103]))
        self.assertFalse((self.data_dir / "posts" / "103.json").exists())
        self.assertEqual(load_manifest(self.data_dir)["posts"]["101"]["path"],
                         "posts/prayers/hanukkah/a-song_(101).json")

    def test_category_selection_is_remembered(self) -> None:
        self.run_download(categories=[201])
        self.assertEqual([p.name for p in (self.data_dir / "posts").iterdir()], ["103.json"])
        self.assertEqual(load_manifest(self.data_dir)["categories"], [201])
        self.assertTrue(self.run_download().noop)

    def test_dry_run_writes_nothing(self) -> None:
        result = self.run_download(dry_run=True)
        self.assertEqual(result.written, [101, 103])
        self.assertFalse(self.data_dir.exists())


if __name__ == "__main__":
    unittest.main()
