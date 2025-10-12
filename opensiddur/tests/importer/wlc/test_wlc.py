import unittest
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from opensiddur.importer.wlc.wlc import (
    make_project_directory,
    get_source_directory,
    get_xslt_directory,
    main
)


class TestWLCPathFunctions(unittest.TestCase):
    """Test path-related utility functions in wlc module"""
    
    @patch('pathlib.Path.mkdir')
    def test_make_project_directory(self, mock_mkdir):
        """Test that make_project_directory creates the correct directory"""
        result = make_project_directory()
        
        # Verify mkdir was called with the correct arguments
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Verify the returned path ends with project/wlc
        self.assertTrue(str(result).endswith('project/wlc'))
        
        # Verify it's a Path object
        self.assertIsInstance(result, Path)
    
    def test_get_source_directory(self):
        """Test that get_source_directory returns the correct path"""
        result = get_source_directory()
        
        # Verify it returns a Path object
        self.assertIsInstance(result, Path)
        
        # Verify it points to sources/wlc (should be under opensiddur project)
        self.assertTrue(str(result).endswith('sources/wlc'))
        
        # Verify the path contains 'opensiddur-ai' (the project root)
        self.assertIn('opensiddur-ai', str(result))
    
    def test_get_xslt_directory(self):
        """Test that get_xslt_directory returns the wlc module directory"""
        result = get_xslt_directory()
        
        # Verify it returns a Path object
        self.assertIsInstance(result, Path)
        
        # Verify it points to the wlc importer directory (handle both Unix and Windows paths)
        path_str = str(result)
        self.assertTrue(
            path_str.endswith('importer/wlc') or path_str.endswith('importer\\wlc'),
            f"Expected path to end with 'importer/wlc', got: {path_str}"
        )
        
        # Verify the path is under the opensiddur directory
        self.assertIn('opensiddur', str(result))


class TestWLCMain(unittest.TestCase):
    """Test the main function that orchestrates the WLC transformation"""
    
    @patch('opensiddur.importer.wlc.wlc.validate')
    @patch('opensiddur.importer.wlc.wlc.os.listdir')
    @patch('opensiddur.importer.wlc.wlc.xslt_transform')
    @patch('opensiddur.importer.wlc.wlc.get_xslt_directory')
    @patch('opensiddur.importer.wlc.wlc.get_source_directory')
    @patch('opensiddur.importer.wlc.wlc.make_project_directory')
    def test_main_transforms_and_validates_all_files(
        self, 
        mock_make_project_dir, 
        mock_get_source_dir, 
        mock_get_xslt_dir,
        mock_xslt_transform,
        mock_listdir,
        mock_validate
    ):
        """Test that main transforms index and books, then validates all output files"""
        
        # Set up mock paths
        mock_project_dir = Path('/mock/project/wlc')
        mock_source_dir = Path('/mock/sources/wlc')
        mock_xslt_dir = Path('/mock/opensiddur/importer/wlc')
        
        mock_make_project_dir.return_value = mock_project_dir
        mock_get_source_dir.return_value = mock_source_dir
        mock_get_xslt_dir.return_value = mock_xslt_dir
        
        # Mock os.listdir to return different values for different calls
        # First call: source_directory / "Books" - return book files
        # Second call: project_directory - return transformed files
        source_books = [
            'Genesis.xml',
            'Exodus.xml', 
            'Leviticus.xml',
            'TanachHeader.xml',  # Should be skipped
            'TanachIndex.xml',   # Should be skipped
            'Genesis.DH.xml'     # Should be skipped (ends with .DH.xml)
        ]
        
        project_files = [
            'index.xml',
            'genesis.xml',
            'exodus.xml',
            'leviticus.xml'
        ]
        
        mock_listdir.side_effect = [source_books, project_files]
        
        # Mock validate to return success
        mock_validate.return_value = (True, [])
        
        # Run main
        result = main()
        
        # Verify return value
        self.assertEqual(result, 0)
        
        # Verify xslt_transform was called for index
        expected_index_call = call(
            mock_xslt_dir / "transform_index.xslt",
            mock_source_dir / "TanachHeader.xml",
            mock_project_dir / "index.xml"
        )
        self.assertIn(expected_index_call, mock_xslt_transform.call_args_list)
        
        # Verify xslt_transform was called for each valid book (not the excluded ones)
        expected_book_calls = [
            call(
                mock_xslt_dir / "transform_book.xslt",
                mock_source_dir / "Genesis.xml",
                mock_project_dir / "genesis.xml"
            ),
            call(
                mock_xslt_dir / "transform_book.xslt",
                mock_source_dir / "Exodus.xml",
                mock_project_dir / "exodus.xml"
            ),
            call(
                mock_xslt_dir / "transform_book.xslt",
                mock_source_dir / "Leviticus.xml",
                mock_project_dir / "leviticus.xml"
            )
        ]
        
        for expected_call in expected_book_calls:
            self.assertIn(expected_call, mock_xslt_transform.call_args_list)
        
        # Verify total number of xslt_transform calls (1 index + 3 books)
        self.assertEqual(mock_xslt_transform.call_count, 4)
        
        # Verify validate was called for every .xml file in project directory
        expected_validate_calls = [
            call(mock_project_dir / "index.xml"),
            call(mock_project_dir / "genesis.xml"),
            call(mock_project_dir / "exodus.xml"),
            call(mock_project_dir / "leviticus.xml")
        ]
        
        for expected_call in expected_validate_calls:
            self.assertIn(expected_call, mock_validate.call_args_list)
        
        # Verify validate was called for each file
        self.assertEqual(mock_validate.call_count, 4)
    
    @patch('opensiddur.importer.wlc.wlc.validate')
    @patch('opensiddur.importer.wlc.wlc.os.listdir')
    @patch('opensiddur.importer.wlc.wlc.xslt_transform')
    @patch('opensiddur.importer.wlc.wlc.get_xslt_directory')
    @patch('opensiddur.importer.wlc.wlc.get_source_directory')
    @patch('opensiddur.importer.wlc.wlc.make_project_directory')
    def test_main_handles_validation_errors(
        self, 
        mock_make_project_dir, 
        mock_get_source_dir, 
        mock_get_xslt_dir,
        mock_xslt_transform,
        mock_listdir,
        mock_validate
    ):
        """Test that main handles validation errors gracefully"""
        
        # Set up mock paths
        mock_project_dir = Path('/mock/project/wlc')
        mock_source_dir = Path('/mock/sources/wlc')
        mock_xslt_dir = Path('/mock/opensiddur/importer/wlc')
        
        mock_make_project_dir.return_value = mock_project_dir
        mock_get_source_dir.return_value = mock_source_dir
        mock_get_xslt_dir.return_value = mock_xslt_dir
        
        # Mock os.listdir
        source_books = ['Genesis.xml']
        project_files = ['index.xml', 'genesis.xml']
        mock_listdir.side_effect = [source_books, project_files]
        
        # Mock validate to return an error for one file
        mock_validate.side_effect = [
            (True, []),  # index.xml is valid
            (False, ['Error: Invalid XML structure'])  # genesis.xml has errors
        ]
        
        # Run main - should not raise an exception
        result = main()
        
        # Should still return 0 even with validation errors
        self.assertEqual(result, 0)
        
        # Verify validate was called for both files
        self.assertEqual(mock_validate.call_count, 2)


if __name__ == '__main__':
    unittest.main()

