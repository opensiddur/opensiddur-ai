import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.opensiddur_org.parse_post import parse_post
from opensiddur.importer.opensiddur_org.urns import (
    PostUrns,
    load_post_urns,
    mint,
    registry_lines,
    save_post_urns,
)
from opensiddur.tests.importer.opensiddur_org.support import make_post

PREFIX = "urn:x-opensiddur:text:"
#: A spelling list of the tests' own, so that these do not change with the real one.
VARIANTS = {"tsur": "tzur", "chanukkah": "chanukah"}
POET = {"name": "Yehudah Poet", "profile_link": "https://opensiddur.org/profile/yehudah-poet"}


def post(title: str, *, slug: str = "a-slug-the-urn-does-not-use", tags=None, post_id: int = 7):
    return parse_post(make_post(post_id, title=title, slug=slug, tags=tags, coauthors=[POET]))


class TestMinting(unittest.TestCase):
    def test_named_from_the_title_not_the_slug(self) -> None:
        record = mint(post("A Prayer for Rain, by Yehudah Poet"), set(), VARIANTS)
        self.assertEqual(record.urn, f"{PREFIX}prayer:a_prayer_for_rain")

    def test_respelled_by_the_spelling_list(self) -> None:
        record = mint(post("מעוז צור | Maoz Tsur for Ḥanukkah"), set(), VARIANTS)
        self.assertEqual(record.urn, f"{PREFIX}prayer:maoz_tzur_for_chanukah")

    def test_a_hebrew_only_title_is_named_from_the_slug(self) -> None:
        record = mint(post("שירה", slug="shirah-by-someone"), set(), VARIANTS)
        self.assertEqual(record.urn, f"{PREFIX}prayer:shirah")

    def test_poem_from_tags(self) -> None:
        self.assertIn(":poem:", mint(post("A Song", tags=["פיוטים piyyuṭim"]), set(), VARIANTS).urn)

    def test_a_taken_name_gets_the_author_then_the_post_id(self) -> None:
        taken = {f"{PREFIX}prayer:kaddish"}
        self.assertEqual(mint(post("Kaddish"), taken, VARIANTS).urn, f"{PREFIX}prayer:kaddish_poet")
        taken.add(f"{PREFIX}prayer:kaddish_poet")
        self.assertEqual(mint(post("Kaddish"), taken, VARIANTS).urn, f"{PREFIX}prayer:kaddish_7")


class TestRecords(unittest.TestCase):
    def test_new_rows(self) -> None:
        record = PostUrns(1, "new", "urn:x-opensiddur:text:prayer:p")
        self.assertEqual(record.row_urn(3), "urn:x-opensiddur:text:prayer:p/3")

    def test_new_post_with_existing_parts(self) -> None:
        record = PostUrns(1, "new", "urn:x-opensiddur:text:prayer:p", {2: "urn:x-opensiddur:text:prayer:shehecheyanu"})
        self.assertEqual(record.row_urn(2), "urn:x-opensiddur:text:prayer:shehecheyanu")
        self.assertEqual(record.row_urn(1), "urn:x-opensiddur:text:prayer:p/1")
        lines = registry_lines(record, [1, 2, 3], label_en="P")
        self.assertEqual([line["urn"] for line in lines], [
            "urn:x-opensiddur:text:prayer:p", "urn:x-opensiddur:text:prayer:p/1", "urn:x-opensiddur:text:prayer:p/3"])

    def test_existing_rows(self) -> None:
        record = PostUrns(1, "existing", "urn:x-opensiddur:text:poem:maoz_tzur",
                          {1: "urn:x-opensiddur:text:poem:maoz_tzur/1", 2: None})
        self.assertEqual(record.row_urn(1), "urn:x-opensiddur:text:poem:maoz_tzur/1")
        self.assertIsNone(record.row_urn(2))
        self.assertEqual(registry_lines(record, [1, 2], label_en="x"), [])

    def test_registry_labels(self) -> None:
        lines = registry_lines(PostUrns(1, "new", "urn:x-opensiddur:text:prayer:p"), [1], label_en="P", label_he="פ")
        self.assertEqual((lines[0]["label_en"], lines[0]["label_he"]), ("P", "פ"))
        self.assertEqual(lines[1]["parent"], "urn:x-opensiddur:text:prayer:p")

    def test_round_trip(self) -> None:
        records = {
            2: PostUrns(2, "existing", "urn:x-opensiddur:text:poem:a", {1: "urn:x-opensiddur:text:poem:a/1", 2: None}),
            1: PostUrns(1, "new", "urn:x-opensiddur:text:prayer:b", {3: "urn:x-opensiddur:text:prayer:c"}),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "post_urns.jsonl"
            save_post_urns(records, path)
            self.assertEqual(load_post_urns(path), records)
            # Sorted by post ID, so the file is stable.
            self.assertTrue(path.read_text().startswith('{"post_id": 1,'))


if __name__ == "__main__":
    unittest.main()
