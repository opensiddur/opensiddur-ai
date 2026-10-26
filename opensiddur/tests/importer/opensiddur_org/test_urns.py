import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.opensiddur_org.urns import (
    PostUrns,
    load_post_urns,
    mint,
    registry_lines,
    save_post_urns,
    urn_component,
)


class TestMinting(unittest.TestCase):
    def test_prayer_from_slug(self) -> None:
        record = mint(7, "a-prayer-for-rain", [], set())
        self.assertEqual(record.urn, "urn:x-opensiddur:text:prayer:a_prayer_for_rain")

    def test_poem_from_tags(self) -> None:
        self.assertIn(":poem:", mint(7, "x", ["פיוטים piyyuṭim"], set()).urn)

    def test_taken_name_gets_the_post_id(self) -> None:
        taken = {"urn:x-opensiddur:text:prayer:kaddish"}
        self.assertEqual(mint(7, "kaddish", [], taken).urn, "urn:x-opensiddur:text:prayer:kaddish_7")

    def test_component(self) -> None:
        self.assertEqual(urn_component("Ma'oz Tsur -- 1893!"), "ma_oz_tsur_1893")


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
