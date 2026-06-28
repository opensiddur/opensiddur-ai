import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opensiddur.importer.feinstein_haggadah.align_page_breaks import (
    _enforce_monotonic,
    _interpolate_missing,
    _normalize_hebrew,
    _subseq_ratio,
)
from opensiddur.importer.feinstein_haggadah.convert import _emit_page_breaks
from opensiddur.importer.feinstein_haggadah.sections import document_order_slugs


class TestAlignPageBreaksHelpers(unittest.TestCase):
    def test_normalize_hebrew_strips_marks_and_non_letters(self) -> None:
        self.assertEqual(_normalize_hebrew("קַדֵּשׁ!"), "קדש")

    def test_subseq_ratio(self) -> None:
        self.assertEqual(_subseq_ratio("קדש", "xxקxxדxxש"), 1.0)
        self.assertLess(_subseq_ratio("קדש", "שדק"), 0.5)

    def test_interpolate_missing_uses_neighbors(self) -> None:
        slugs = ["a", "b", "c"]
        filled = _interpolate_missing({"a": 11, "c": 13}, slugs)
        self.assertEqual(filled["b"], 11)

    def test_enforce_monotonic(self) -> None:
        slugs = ["a", "b", "c"]
        result = _enforce_monotonic({"a": 11, "b": 10, "c": 12}, slugs)
        self.assertEqual(result, {"a": 11, "b": 11, "c": 12})

    def test_emit_page_breaks_only_on_change(self) -> None:
        slugs = document_order_slugs()[:4]
        mapping = {slugs[0]: 11, slugs[1]: 12, slugs[2]: 12, slugs[3]: 15}
        emitted = _emit_page_breaks(mapping)
        self.assertEqual(emitted[slugs[0]], 11)
        self.assertEqual(emitted[slugs[1]], 12)
        self.assertIsNone(emitted[slugs[2]])
        self.assertEqual(emitted[slugs[3]], 15)


class TestAlignPageBreaksIntegration(unittest.TestCase):
    def test_align_writes_json_when_pdf_present(self) -> None:
        pdf_path = Path("sources/heidenheim_haggadah_1822/Hebrewbooks_org_21779.pdf")
        if not pdf_path.is_file():
            self.skipTest("1822 PDF not available locally")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "feinstein_haggadah_2009").mkdir()
            (root / "heidenheim_haggadah_1822").mkdir()
            (root / "feinstein_haggadah_2009" / "compilation.json").write_text(
                Path("sources/feinstein_haggadah_2009/compilation.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            pdf_dest = root / "heidenheim_haggadah_1822" / "heidenheim_1822.pdf"
            pdf_dest.write_bytes(pdf_path.read_bytes())

            from opensiddur.importer.feinstein_haggadah.align_page_breaks import (
                align_page_breaks,
                write_page_breaks,
            )

            mapping = align_page_breaks(sourcetexts_root=root, pdf_path=pdf_dest)
            self.assertGreaterEqual(len(mapping), 50)
            self.assertEqual(mapping["bedikat_chametz"], 11)
            self.assertLess(mapping["ha_lachma_anya"], mapping["avadim_hayinu"])

            out = write_page_breaks(mapping, root)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("bedikat_chametz", data)
            self.assertNotIn("_only", data)


if __name__ == "__main__":
    unittest.main()
