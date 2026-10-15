"""PDF checks compare reading text with the corrected form the exporter sets by default."""
import json
import tempfile
import unittest
from pathlib import Path

from opensiddur.importer.asher_selichot.check_pdf import corrected


class CorrectedReadingTests(unittest.TestCase):
    def test_reading_text_is_read_with_its_corrections(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            (source / 'scan_reading').mkdir()
            (source / 'scan_reading/corrections.json').write_text(json.dumps({'corrections': [
                {'id': 'cite', 'before': 'Jer. iii. ', 'sic': '2.', 'corr': '3.', 'after': ''},
                {'id': 'exact', 'exact': True, 'sic': 'x', 'corr': 'y'},
                {'id': 'follows', 'follows': 'z', 'sic': '”', 'corr': ''}]}))
            self.assertEqual('See Jer. iii. 3. and x”', corrected('See Jer. iii. 2. and x”', source))

    def test_without_a_corrections_file_the_text_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual('Jer. iii. 2.', corrected('Jer. iii. 2.', Path(temp)))


if __name__ == '__main__':
    unittest.main()
