import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from opensiddur.importer.util.pages import get_page, get_credits
from opensiddur.importer.util.constants import Page


class TestGetPage(unittest.TestCase):
    """Test the get_page function"""
    
    @patch('builtins.open', new_callable=mock_open, read_data='Page content here')
    def test_get_page_success_with_integer(self, mock_file):
        """Test get_page successfully reads a page with integer input"""
        result = get_page(25)
        
        # Should return a Page object
        self.assertIsInstance(result, Page)
        self.assertEqual(result.number, 25)
        self.assertEqual(result.content, 'Page content here')
        
        # Should open the correct file
        expected_path = Path(__file__).parent.parent.parent.parent.parent / "sources/jps1917/text/0025.txt"
        mock_file.assert_called_once()
        # Check that the path used ends with the expected filename
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('0025.txt'), f"Expected path ending with 0025.txt, got: {actual_call}")
    
    @patch('builtins.open', new_callable=mock_open, read_data='First page content')
    def test_get_page_success_with_string(self, mock_file):
        """Test get_page successfully reads a page with string input"""
        result = get_page('1')
        
        # Should return a Page object
        self.assertIsInstance(result, Page)
        self.assertEqual(result.number, 1)
        self.assertEqual(result.content, 'First page content')
        
        # Should open the correct file (0001.txt)
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('0001.txt'), f"Expected path ending with 0001.txt, got: {actual_call}")
    
    @patch('builtins.open', new_callable=mock_open, read_data='Large page number')
    def test_get_page_with_large_page_number(self, mock_file):
        """Test get_page with large page numbers (4+ digits)"""
        result = get_page(1234)
        
        # Should return a Page object
        self.assertIsInstance(result, Page)
        self.assertEqual(result.number, 1234)
        self.assertEqual(result.content, 'Large page number')
        
        # Should format correctly (1234.txt not 01234.txt - only 4 digits with :04d)
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('1234.txt'), f"Expected path ending with 1234.txt, got: {actual_call}")
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_page_file_not_found_returns_none(self, mock_file):
        """Test get_page returns None when file doesn't exist"""
        result = get_page(999)
        
        # Should return None on FileNotFoundError
        self.assertIsNone(result)
    
    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_page_with_empty_file(self, mock_file):
        """Test get_page with empty file returns Page with empty content"""
        result = get_page(5)
        
        # Should return Page with empty content
        self.assertIsInstance(result, Page)
        self.assertEqual(result.number, 5)
        self.assertEqual(result.content, '')
    
    @patch('builtins.open', new_callable=mock_open, read_data='Content with\nmultiple\nlines')
    def test_get_page_preserves_multiline_content(self, mock_file):
        """Test get_page preserves multiline content"""
        result = get_page(10)
        
        # Should preserve all content including newlines
        self.assertIsInstance(result, Page)
        self.assertIn('\n', result.content)
        self.assertIn('multiple', result.content)
        self.assertIn('lines', result.content)
    
    @patch('builtins.open', new_callable=mock_open, read_data='Hebrew: שלום')
    def test_get_page_preserves_unicode(self, mock_file):
        """Test get_page preserves Unicode characters"""
        result = get_page(15)
        
        # Should preserve Unicode
        self.assertIsInstance(result, Page)
        self.assertIn('שלום', result.content)


class TestGetCredits(unittest.TestCase):
    """Test the get_credits function"""
    
    @patch('builtins.open', new_callable=mock_open, read_data='Credit line 1\nCredit line 2\nCredit line 3')
    def test_get_credits_success_with_integer(self, mock_file):
        """Test get_credits successfully reads credits with integer input"""
        result = get_credits(25)
        
        # Should return list of credit lines
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIn('Credit line 1', result)
        self.assertIn('Credit line 2', result)
        self.assertIn('Credit line 3', result)
        
        # Should open the correct file
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('credits/0025.txt'), f"Expected path ending with credits/0025.txt, got: {actual_call}")
    
    @patch('builtins.open', new_callable=mock_open, read_data='Line 1\nLine 2')
    def test_get_credits_success_with_string(self, mock_file):
        """Test get_credits successfully reads credits with string input"""
        result = get_credits('1')
        
        # Should return list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # Should open the correct file (0001.txt)
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('credits/0001.txt'), f"Expected path ending with credits/0001.txt, got: {actual_call}")
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_credits_file_not_found_returns_none(self, mock_file):
        """Test get_credits returns None when file doesn't exist"""
        result = get_credits(999)
        
        # Should return None on FileNotFoundError
        self.assertIsNone(result)
    
    @patch('builtins.open', new_callable=mock_open, read_data='')
    def test_get_credits_with_empty_file(self, mock_file):
        """Test get_credits with empty file returns empty list"""
        result = get_credits(5)
        
        # Should return empty list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('builtins.open', new_callable=mock_open, read_data='Line 1\n\nLine 2\n\n\nLine 3')
    def test_get_credits_strips_empty_lines(self, mock_file):
        """Test get_credits filters out empty lines"""
        result = get_credits(10)
        
        # Should only have 3 lines (empty lines filtered out)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result, ['Line 1', 'Line 2', 'Line 3'])
    
    @patch('builtins.open', new_callable=mock_open, read_data='  Padded line  \n\tTabbed\t\n')
    def test_get_credits_strips_whitespace(self, mock_file):
        """Test get_credits strips leading/trailing whitespace from each line"""
        result = get_credits(20)
        
        # Should strip whitespace
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'Padded line')
        self.assertEqual(result[1], 'Tabbed')
    
    @patch('builtins.open', new_callable=mock_open, read_data='Credit 1\n\n\nCredit 2\n  \n\t\nCredit 3')
    def test_get_credits_handles_blank_lines(self, mock_file):
        """Test get_credits handles various types of blank lines"""
        result = get_credits(30)
        
        # Should filter all blank lines (empty, spaces, tabs)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result, ['Credit 1', 'Credit 2', 'Credit 3'])
    
    @patch('builtins.open', new_callable=mock_open, read_data='Hebrew credit: שלום')
    def test_get_credits_preserves_unicode(self, mock_file):
        """Test get_credits preserves Unicode characters"""
        result = get_credits(15)
        
        # Should preserve Unicode
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn('שלום', result[0])


class TestPageNumberFormatting(unittest.TestCase):
    """Test that page numbers are formatted correctly in filenames"""
    
    @patch('builtins.open', new_callable=mock_open, read_data='test')
    def test_single_digit_page_number(self, mock_file):
        """Test that single digit page numbers are zero-padded to 4 digits"""
        get_page(1)
        
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('0001.txt'))
    
    @patch('builtins.open', new_callable=mock_open, read_data='test')
    def test_two_digit_page_number(self, mock_file):
        """Test that two digit page numbers are zero-padded to 4 digits"""
        get_page(42)
        
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('0042.txt'))
    
    @patch('builtins.open', new_callable=mock_open, read_data='test')
    def test_three_digit_page_number(self, mock_file):
        """Test that three digit page numbers are zero-padded to 4 digits"""
        get_page(123)
        
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('0123.txt'))
    
    @patch('builtins.open', new_callable=mock_open, read_data='test')
    def test_four_digit_page_number(self, mock_file):
        """Test that four digit page numbers are not padded"""
        get_page(5678)
        
        actual_call = str(mock_file.call_args[0][0])
        self.assertTrue(actual_call.endswith('5678.txt'))


if __name__ == '__main__':
    unittest.main()

