import unittest
from unittest.mock import patch

from opensiddur.importer.jps1917.convert_wikisource import get_credits_pages


class TestGetCreditsPages(unittest.TestCase):
    """Tests for get_credits_pages function."""

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_normal_case(self, mock_get_credits):
        """Test normal case with different credits on each page."""
        # Mock get_credits to return different lists for each page
        mock_get_credits.side_effect = [
            ["Alice", "Bob"],
            ["Charlie"],
            ["David", "Eve"],
        ]
        
        result = get_credits_pages(1, 3)
        
        # Should be sorted and unique
        self.assertEqual(result, ["Alice", "Bob", "Charlie", "David", "Eve"])
        
        # Verify get_credits was called for each page
        self.assertEqual(mock_get_credits.call_count, 3)
        mock_get_credits.assert_any_call(1)
        mock_get_credits.assert_any_call(2)
        mock_get_credits.assert_any_call(3)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_repeated_strings(self, mock_get_credits):
        """Test that repeated strings across pages are deduplicated."""
        # Mock get_credits to return overlapping credits
        mock_get_credits.side_effect = [
            ["Alice", "Bob"],
            ["Bob", "Charlie"],
            ["Charlie", "Alice"],
        ]
        
        result = get_credits_pages(1, 3)
        
        # Should contain each name only once, sorted
        self.assertEqual(result, ["Alice", "Bob", "Charlie"])
        self.assertEqual(mock_get_credits.call_count, 3)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_nonexistent_pages(self, mock_get_credits):
        """Test handling of nonexistent pages (get_credits returns None)."""
        # Mock get_credits to return None for some pages
        mock_get_credits.side_effect = [
            ["Alice", "Bob"],
            None,  # Nonexistent page
            ["Charlie"],
            None,  # Another nonexistent page
        ]
        
        result = get_credits_pages(1, 4)
        
        # Should only include credits from existing pages
        self.assertEqual(result, ["Alice", "Bob", "Charlie"])
        self.assertEqual(mock_get_credits.call_count, 4)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_all_nonexistent_pages(self, mock_get_credits):
        """Test when all pages are nonexistent."""
        mock_get_credits.return_value = None
        
        result = get_credits_pages(1, 3)
        
        # Should return empty list
        self.assertEqual(result, [])
        self.assertEqual(mock_get_credits.call_count, 3)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_empty_credits(self, mock_get_credits):
        """Test when pages return empty credit lists."""
        mock_get_credits.side_effect = [
            [],
            ["Alice"],
            [],
        ]
        
        result = get_credits_pages(1, 3)
        
        # Should only include the one credit
        self.assertEqual(result, ["Alice"])
        self.assertEqual(mock_get_credits.call_count, 3)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_single_page(self, mock_get_credits):
        """Test with a single page range."""
        mock_get_credits.return_value = ["Alice", "Bob"]
        
        result = get_credits_pages(5, 5)
        
        # Should return sorted credits from single page
        self.assertEqual(result, ["Alice", "Bob"])
        self.assertEqual(mock_get_credits.call_count, 1)
        mock_get_credits.assert_called_once_with(5)

    @patch('opensiddur.importer.jps1917.convert_wikisource.get_credits')
    def test_sorting(self, mock_get_credits):
        """Test that results are properly sorted alphabetically."""
        mock_get_credits.side_effect = [
            ["Zebra", "Alpha"],
            ["Charlie", "Beta"],
        ]
        
        result = get_credits_pages(1, 2)
        
        # Should be alphabetically sorted
        self.assertEqual(result, ["Alpha", "Beta", "Charlie", "Zebra"])


if __name__ == '__main__':
    unittest.main()

