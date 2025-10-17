"""Tests for the UrnResolver class."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from lxml import etree
from opensiddur.exporter.urn import UrnResolver, ResolvedUrn, ResolvedUrnRange


class TestUrnResolverBasics(unittest.TestCase):
    """Test basic URN resolver functionality."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)

    def test_database_initialization(self):
        """Test that database and tables are created properly."""
        # Check that database file exists
        self.assertTrue(self.db_path.exists())
        
        # Check that table exists
        cursor = self.resolver.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urn_mappings'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'urn_mappings')

    def test_add_mapping(self):
        """Test adding a URN mapping."""
        urn = "urn:x-opensiddur:test:doc1"
        project = "test_project"
        file_name = "doc1.xml"
        
        self.resolver.add_mapping(urn, project, file_name)
        
        # Verify it was added
        cursor = self.resolver.conn.cursor()
        cursor.execute('SELECT * FROM urn_mappings WHERE urn = ?', (urn,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['urn'], urn)
        self.assertEqual(row['project'], project)
        self.assertEqual(row['file_name'], file_name)

    def test_add_mapping_update(self):
        """Test updating an existing URN mapping."""
        urn = "urn:x-opensiddur:test:doc1"
        project = "test_project"
        
        # Add initial mapping
        self.resolver.add_mapping(urn, project, "file1.xml")
        
        # Update with new file name
        self.resolver.add_mapping(urn, project, "file2.xml")
        
        # Verify it was updated
        cursor = self.resolver.conn.cursor()
        cursor.execute('SELECT file_name FROM urn_mappings WHERE urn = ? AND project = ?', 
                      (urn, project))
        row = cursor.fetchone()
        self.assertEqual(row['file_name'], "file2.xml")

    def test_add_mapping_multiple_projects(self):
        """Test that same URN can exist in multiple projects."""
        urn = "urn:x-opensiddur:test:doc1"
        
        self.resolver.add_mapping(urn, "project1", "file1.xml")
        self.resolver.add_mapping(urn, "project2", "file2.xml")
        
        # Verify both exist
        cursor = self.resolver.conn.cursor()
        cursor.execute('SELECT project, file_name FROM urn_mappings WHERE urn = ? ORDER BY project', 
                      (urn,))
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['project'], "project1")
        self.assertEqual(rows[1]['project'], "project2")


class TestUrnResolverResolve(unittest.TestCase):
    """Test URN resolution functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)
        
        # Add test data
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1", "wlc", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1", "jps1917", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc2", "wlc", "doc2.xml")

    def test_resolve_without_project(self):
        """Test resolving URN without project specifier returns all matches."""
        results = self.resolver.resolve("urn:x-opensiddur:test:doc1")
        
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ResolvedUrn)
        self.assertIsInstance(results[1], ResolvedUrn)
        
        # Check both projects are present
        projects = {r.project for r in results}
        self.assertEqual(projects, {"wlc", "jps1917"})
        
        # Check URN is correct
        for result in results:
            self.assertEqual(result.urn, "urn:x-opensiddur:test:doc1")
            self.assertEqual(result.file_name, "doc1.xml")

    def test_resolve_with_project(self):
        """Test resolving URN with @project specifier."""
        results = self.resolver.resolve("urn:x-opensiddur:test:doc1@wlc")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].urn, "urn:x-opensiddur:test:doc1")
        self.assertEqual(results[0].project, "wlc")
        self.assertEqual(results[0].file_name, "doc1.xml")

    def test_resolve_with_nonexistent_project(self):
        """Test resolving URN with non-existent project returns empty list."""
        results = self.resolver.resolve("urn:x-opensiddur:test:doc1@nonexistent")
        
        self.assertEqual(results, [])

    def test_resolve_nonexistent_urn(self):
        """Test resolving non-existent URN returns empty list."""
        results = self.resolver.resolve("urn:x-opensiddur:test:nonexistent")
        
        self.assertEqual(results, [])

    def test_resolve_returns_list(self):
        """Test that resolve always returns a list."""
        # Existing URN
        result = self.resolver.resolve("urn:x-opensiddur:test:doc1")
        self.assertIsInstance(result, list)
        
        # Non-existing URN
        result = self.resolver.resolve("urn:x-opensiddur:test:nonexistent")
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])


class TestUrnResolverGetByProject(unittest.TestCase):
    """Test get_urns_by_project functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)
        
        # Add test data
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1", "wlc", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc2", "wlc", "doc2.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc3", "jps1917", "doc3.xml")

    def test_get_urns_by_project(self):
        """Test getting all URNs for a project."""
        results = self.resolver.get_urns_by_project("wlc")
        
        self.assertEqual(len(results), 2)
        urns = {r.urn for r in results}
        self.assertEqual(urns, {"urn:x-opensiddur:test:doc1", "urn:x-opensiddur:test:doc2"})
        
        # All should be in wlc project
        for result in results:
            self.assertEqual(result.project, "wlc")

    def test_get_urns_by_nonexistent_project(self):
        """Test getting URNs for non-existent project returns empty list."""
        results = self.resolver.get_urns_by_project("nonexistent")
        
        self.assertEqual(results, [])
    
    def test_get_files_by_project(self):
        """Test getting list of files in a project."""
        files = self.resolver.get_files_by_project("wlc")
        
        self.assertEqual(len(files), 2)
        self.assertIn("doc1.xml", files)
        self.assertIn("doc2.xml", files)
    
    def test_get_files_by_project_sorted(self):
        """Test that files are returned in sorted order."""
        files = self.resolver.get_files_by_project("wlc")
        
        self.assertEqual(files, ["doc1.xml", "doc2.xml"])
    
    def test_get_files_by_project_single_file(self):
        """Test getting files for project with single file."""
        files = self.resolver.get_files_by_project("jps1917")
        
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "doc3.xml")
    
    def test_get_files_by_nonexistent_project(self):
        """Test getting files for non-existent project returns empty list."""
        files = self.resolver.get_files_by_project("nonexistent")
        
        self.assertEqual(files, [])
    
    def test_get_files_by_project_no_duplicates(self):
        """Test that files list contains no duplicates."""
        # Add multiple URNs to same file
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1/new", "wlc", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1/another", "wlc", "doc1.xml")
        
        files = self.resolver.get_files_by_project("wlc")
        
        # Should still be 2 files (doc1.xml and doc2.xml), not more
        self.assertEqual(len(files), 2)
        self.assertEqual(files.count("doc1.xml"), 1)  # No duplicates
    
    def test_list_projects(self):
        """Test listing all projects in the database."""
        projects = self.resolver.list_projects()
        
        self.assertEqual(len(projects), 2)
        self.assertIn("wlc", projects)
        self.assertIn("jps1917", projects)
    
    def test_list_projects_sorted(self):
        """Test that projects are returned in sorted order."""
        projects = self.resolver.list_projects()
        
        self.assertEqual(projects, ["jps1917", "wlc"])
    
    def test_list_projects_single(self):
        """Test listing when only one project exists."""
        # Remove jps1917 project
        self.resolver.remove_project("jps1917")
        
        projects = self.resolver.list_projects()
        
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], "wlc")
    
    def test_list_projects_empty(self):
        """Test listing projects when database is empty."""
        # Remove all projects
        self.resolver.remove_project("wlc")
        self.resolver.remove_project("jps1917")
        
        projects = self.resolver.list_projects()
        
        self.assertEqual(projects, [])


class TestUrnResolverRange(unittest.TestCase):
    """Test URN range resolution functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)
        
        # Add test data - chapter/verse structure
        for chapter in range(1, 4):
            for verse in range(1, 11):
                urn = f"urn:x-opensiddur:test:bible:genesis/{chapter}/{verse}"
                self.resolver.add_mapping(urn, "wlc", "genesis.xml")
                self.resolver.add_mapping(urn, "jps1917", "genesis.xml")
        
        # Add chapter-level URNs
        for chapter in range(1, 4):
            urn = f"urn:x-opensiddur:test:bible:genesis/{chapter}"
            self.resolver.add_mapping(urn, "wlc", "genesis.xml")
            self.resolver.add_mapping(urn, "jps1917", "genesis.xml")

    def test_resolve_range_simple(self):
        """Test resolving a simple verse range."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1-2")
        
        self.assertEqual(len(results), 2)  # wlc and jps1917
        
        for result in results:
            self.assertIsInstance(result, ResolvedUrnRange)
            self.assertEqual(result.start.urn, "urn:x-opensiddur:test:bible:genesis/1/1")
            self.assertEqual(result.end.urn, "urn:x-opensiddur:test:bible:genesis/1/2")
            self.assertEqual(result.start.project, result.end.project)
            self.assertEqual(result.start.file_name, result.end.file_name)

    def test_resolve_range_with_project(self):
        """Test resolving range with @project specifier."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1-2@wlc")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].start.project, "wlc")
        self.assertEqual(results[0].end.project, "wlc")

    def test_resolve_range_multi_component(self):
        """Test resolving range with multi-component end (e.g., 1/1-2/3)."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1-2/3")
        
        self.assertEqual(len(results), 2)
        
        for result in results:
            self.assertEqual(result.start.urn, "urn:x-opensiddur:test:bible:genesis/1/1")
            self.assertEqual(result.end.urn, "urn:x-opensiddur:test:bible:genesis/2/3")

    def test_resolve_range_chapter(self):
        """Test resolving chapter range."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1-2")
        
        self.assertEqual(len(results), 2)
        
        for result in results:
            self.assertEqual(result.start.urn, "urn:x-opensiddur:test:bible:genesis/1")
            self.assertEqual(result.end.urn, "urn:x-opensiddur:test:bible:genesis/2")

    def test_resolve_range_nonexistent_start(self):
        """Test resolving range with non-existent start returns empty list."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/99/1-2")
        
        self.assertEqual(results, [])

    def test_resolve_range_nonexistent_end(self):
        """Test resolving range with non-existent end returns empty list."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1-99")
        
        self.assertEqual(results, [])

    def test_resolve_range_not_a_range(self):
        """Test resolving URN without dash calls resolve() and returns results."""
        results = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1")
        
        # Should call resolve() and return ResolvedUrn objects (not ResolvedUrnRange)
        self.assertEqual(len(results), 2)  # wlc and jps1917
        for result in results:
            self.assertIsInstance(result, ResolvedUrn)
            self.assertEqual(result.urn, "urn:x-opensiddur:test:bible:genesis/1/1")

    def test_resolve_range_returns_list(self):
        """Test that resolve_range always returns a list."""
        # Valid range
        result = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1-2")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        
        # Non-ranged URN (calls resolve())
        result = self.resolver.resolve_range("urn:x-opensiddur:test:bible:genesis/1/1")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)  # Should return resolved URNs, not empty list

    def test_resolve_range_dash_not_in_last_part(self):
        """Test that a dash not in the last part is not treated as a range.
        
        For example:
        - "urn:x-opensiddur:text:bible:genesis/1" is NOT a range (dash is in "x-opensiddur")
        - "urn:x-opensiddur:text:bible:genesis/1-2" IS a range (dash is in last part)
        """
        # Add test data with URN containing dash in non-range position
        self.resolver.add_mapping("urn:x-opensiddur:text:bible:genesis/1", "test", "genesis.xml")
        
        # This should NOT be treated as a range, but should call resolve()
        results = self.resolver.resolve_range("urn:x-opensiddur:text:bible:genesis/1")
        self.assertEqual(len(results), 1, 
                        "URN with dash in 'x-opensiddur' should call resolve() and return results")
        self.assertIsInstance(results[0], ResolvedUrn)
        self.assertEqual(results[0].urn, "urn:x-opensiddur:text:bible:genesis/1")
        
        # Add range test data
        self.resolver.add_mapping("urn:x-opensiddur:text:bible:genesis/1", "test", "genesis.xml")
        self.resolver.add_mapping("urn:x-opensiddur:text:bible:genesis/2", "test", "genesis.xml")
        
        # This SHOULD be treated as a range because the dash is in the last part
        results = self.resolver.resolve_range("urn:x-opensiddur:text:bible:genesis/1-2")
        self.assertEqual(len(results), 1, 
                        "URN with dash in last part should be treated as a range")
        self.assertIsInstance(results[0], ResolvedUrnRange)
        self.assertEqual(results[0].start.urn, "urn:x-opensiddur:text:bible:genesis/1")
        self.assertEqual(results[0].end.urn, "urn:x-opensiddur:text:bible:genesis/2")

    def test_resolve_range_dash_in_path_components(self):
        """Test that dashes in non-final path components are not treated as ranges.
        
        For example:
        - "urn:x-opensiddur:text:some-book/1" should NOT be a range (dash in book name)
        - "urn:x-opensiddur:text:some-book/1-2" should be a range (dash in last component)
        """
        # Add test data for book with dash in name
        self.resolver.add_mapping("urn:x-opensiddur:text:some-book/1", "test", "some-book.xml")
        self.resolver.add_mapping("urn:x-opensiddur:text:some-book/2", "test", "some-book.xml")
        self.resolver.add_mapping("urn:x-opensiddur:text:some-book/3", "test", "some-book.xml")
        
        # URN with dash in book name (not last component) should call resolve()
        results = self.resolver.resolve_range("urn:x-opensiddur:text:some-book/1")
        self.assertEqual(len(results), 1, 
                        "URN with dash in book name should call resolve() and return results")
        self.assertIsInstance(results[0], ResolvedUrn)
        self.assertEqual(results[0].urn, "urn:x-opensiddur:text:some-book/1")
        
        # URN with dash in LAST component should be treated as range
        results = self.resolver.resolve_range("urn:x-opensiddur:text:some-book/1-2")
        self.assertEqual(len(results), 1, 
                        "URN with dash in last component should be treated as a range")
        self.assertIsInstance(results[0], ResolvedUrnRange)
        self.assertEqual(results[0].start.urn, "urn:x-opensiddur:text:some-book/1")
        self.assertEqual(results[0].end.urn, "urn:x-opensiddur:text:some-book/2")
        
        # Test with deeper nesting: dash in middle component
        # Note: When there's a dash in a middle component like "chapter-1",
        # it WILL be treated as a potential range, but will fail to resolve
        # because "chapter" and "chapter-1" URNs don't exist
        self.resolver.add_mapping("urn:x-opensiddur:text:some-book/chapter-1/1", "test", "some-book.xml")
        self.resolver.add_mapping("urn:x-opensiddur:text:some-book/chapter-1/2", "test", "some-book.xml")
        
        # URN ending without dash in last component
        # The dash in "chapter-1" will be found and treated as a range, but will fail to resolve
        results = self.resolver.resolve_range("urn:x-opensiddur:text:some-book/chapter-1/1")
        self.assertEqual(len(results), 0, 
                        "URN with dash in middle component is treated as range but fails to resolve")
        
        # URN with dash in last component should be range
        results = self.resolver.resolve_range("urn:x-opensiddur:text:some-book/chapter-1/1-2")
        self.assertEqual(len(results), 1, 
                        "URN with dash in last component should be treated as a range")
        self.assertIsInstance(results[0], ResolvedUrnRange)
        self.assertEqual(results[0].start.urn, "urn:x-opensiddur:text:some-book/chapter-1/1")
        self.assertEqual(results[0].end.urn, "urn:x-opensiddur:text:some-book/chapter-1/2")

    @patch('opensiddur.exporter.urn.UrnResolver.resolve')
    def test_resolve_range_calls_resolve_for_non_ranged_urn(self, mock_resolve):
        """Test that resolve_range calls resolve() when given a non-ranged URN."""
        # Setup mock to return a known result
        expected_result = [ResolvedUrn(project="test", file_name="test.xml", urn="urn:x-opensiddur:test:doc")]
        mock_resolve.return_value = expected_result
        
        # Call resolve_range with a non-ranged URN
        result = self.resolver.resolve_range("urn:x-opensiddur:test:doc")
        
        # Verify resolve() was called with the correct URN
        mock_resolve.assert_called_once_with("urn:x-opensiddur:test:doc")
        
        # Verify the result is what resolve() returned
        self.assertEqual(result, expected_result)

    @patch('opensiddur.exporter.urn.UrnResolver.resolve')
    def test_resolve_range_calls_resolve_for_non_ranged_urn_with_project(self, mock_resolve):
        """Test that resolve_range calls resolve() with @project for non-ranged URN."""
        # Setup mock to return a known result
        expected_result = [ResolvedUrn(project="wlc", file_name="test.xml", urn="urn:x-opensiddur:test:doc")]
        mock_resolve.return_value = expected_result
        
        # Call resolve_range with a non-ranged URN with @project
        result = self.resolver.resolve_range("urn:x-opensiddur:test:doc@wlc")
        
        # Verify resolve() was called with the correct URN including @project
        mock_resolve.assert_called_once_with("urn:x-opensiddur:test:doc@wlc")
        
        # Verify the result is what resolve() returned
        self.assertEqual(result, expected_result)

    @patch('opensiddur.exporter.urn.UrnResolver.resolve')
    def test_resolve_range_calls_resolve_for_urn_with_dash_not_in_last_part(self, mock_resolve):
        """Test that resolve_range calls resolve() for URNs with dash in non-final component."""
        # Setup mock
        expected_result = [ResolvedUrn(project="test", file_name="some-book.xml", urn="urn:x-opensiddur:text:some-book/1")]
        mock_resolve.return_value = expected_result
        
        # URN with dash in book name (not in last component)
        result = self.resolver.resolve_range("urn:x-opensiddur:text:some-book/1")
        
        # Verify resolve() was called
        mock_resolve.assert_called_once_with("urn:x-opensiddur:text:some-book/1")
        self.assertEqual(result, expected_result)


class TestUrnResolverIndexing(unittest.TestCase):
    """Test URN indexing functionality."""

    def setUp(self):
        """Set up temporary database and XML files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.project_dir = Path(self.temp_dir.name) / 'projects'
        self.test_project_dir = self.project_dir / 'test_project'
        self.test_project_dir.mkdir(parents=True)
        
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)

    def _create_test_xml(self, filename, urns):
        """Helper to create a test XML file with URNs."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        root.set("{http://www.w3.org/XML/1998/namespace}id", "test")
        
        for urn in urns:
            elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
            elem.set("corresp", urn)
        
        xml_path = self.test_project_dir / filename
        tree = etree.ElementTree(root)
        tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
        return xml_path

    def test_index_file(self):
        """Test indexing a single XML file."""
        urns = [
            "urn:x-opensiddur:test:doc1",
            "urn:x-opensiddur:test:doc1/1",
            "urn:x-opensiddur:test:doc1/1/1",
        ]
        xml_path = self._create_test_xml("doc1.xml", urns)
        
        count = self.resolver.index_file(xml_path, "test_project", "doc1.xml")
        
        self.assertEqual(count, 3)
        
        # Verify URNs were indexed
        for urn in urns:
            results = self.resolver.resolve(urn)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].project, "test_project")
            self.assertEqual(results[0].file_name, "doc1.xml")

    def test_index_file_ignores_non_opensiddur_urns(self):
        """Test that indexing ignores URNs not starting with urn:x-opensiddur:."""
        urns = [
            "urn:x-opensiddur:test:doc1",
            "urn:other:test:doc2",  # Should be ignored
            "http://example.com",   # Should be ignored
        ]
        xml_path = self._create_test_xml("doc1.xml", urns)
        
        count = self.resolver.index_file(xml_path, "test_project", "doc1.xml")
        
        self.assertEqual(count, 1)  # Only one valid URN

    def test_index_urns(self):
        """Test indexing all XML files in a project directory."""
        # Create multiple XML files
        self._create_test_xml("doc1.xml", ["urn:x-opensiddur:test:doc1"])
        self._create_test_xml("doc2.xml", ["urn:x-opensiddur:test:doc2"])
        self._create_test_xml("doc3.xml", ["urn:x-opensiddur:test:doc3"])
        
        total = self.resolver.index_urns("test_project", self.project_dir)
        
        self.assertEqual(total, 3)
        
        # Verify all were indexed
        results = self.resolver.get_urns_by_project("test_project")
        self.assertEqual(len(results), 3)

    def test_index_urns_nonexistent_project(self):
        """Test indexing non-existent project raises ValueError."""
        with self.assertRaises(ValueError):
            self.resolver.index_urns("nonexistent_project", self.project_dir)

    def test_index_file_with_namespaces(self):
        """Test indexing file with multiple namespaces."""
        # Create XML with both tei and j namespaces
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem1 = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem1.set("corresp", "urn:x-opensiddur:test:tei")
        
        elem2 = etree.SubElement(root, "{http://jewishliturgy.org/ns/jlptei/2}ptr")
        elem2.set("corresp", "urn:x-opensiddur:test:jlptei")
        
        xml_path = self.test_project_dir / "test.xml"
        tree = etree.ElementTree(root)
        tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
        
        count = self.resolver.index_file(xml_path, "test_project", "test.xml")
        
        self.assertEqual(count, 2)


class TestUrnResolverRemoval(unittest.TestCase):
    """Test URN removal functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)
        
        # Add test data
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1/1", "wlc", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1/2", "wlc", "doc1.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc2/1", "wlc", "doc2.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc3/1", "jps1917", "doc3.xml")
        self.resolver.add_mapping("urn:x-opensiddur:test:doc4/1", "jps1917", "doc4.xml")

    def test_remove_file(self):
        """Test removing all URNs for a specific file."""
        # Remove doc1.xml from wlc project
        removed_count = self.resolver.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify doc1.xml URNs are gone
        results = self.resolver.resolve("urn:x-opensiddur:test:doc1/1")
        self.assertEqual(results, [])
        
        # Verify other files still exist
        results = self.resolver.resolve("urn:x-opensiddur:test:doc2/1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_name, "doc2.xml")

    def test_remove_file_nonexistent(self):
        """Test removing non-existent file returns 0."""
        removed_count = self.resolver.remove_file("nonexistent.xml", "wlc")
        
        self.assertEqual(removed_count, 0)

    def test_remove_file_only_affects_specified_project(self):
        """Test that removing a file only affects the specified project."""
        # Add same file name in different project
        self.resolver.add_mapping("urn:x-opensiddur:test:doc1/1", "jps1917", "doc1.xml")
        
        # Remove from wlc only
        removed_count = self.resolver.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify jps1917 version still exists
        results = self.resolver.resolve("urn:x-opensiddur:test:doc1/1@jps1917")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].project, "jps1917")

    def test_remove_project(self):
        """Test removing all URNs for an entire project."""
        # Remove entire wlc project
        removed_count = self.resolver.remove_project("wlc")
        
        self.assertEqual(removed_count, 3)  # doc1/1, doc1/2, doc2/1
        
        # Verify wlc URNs are gone
        results = self.resolver.get_urns_by_project("wlc")
        self.assertEqual(results, [])
        
        # Verify jps1917 still exists
        results = self.resolver.get_urns_by_project("jps1917")
        self.assertEqual(len(results), 2)

    def test_remove_project_nonexistent(self):
        """Test removing non-existent project returns 0."""
        removed_count = self.resolver.remove_project("nonexistent")
        
        self.assertEqual(removed_count, 0)

    def test_remove_project_all_files(self):
        """Test that removing project removes all files in that project."""
        # Remove jps1917 project
        removed_count = self.resolver.remove_project("jps1917")
        
        self.assertEqual(removed_count, 2)  # doc3/1, doc4/1
        
        # Verify all jps1917 URNs are gone
        for urn in ["urn:x-opensiddur:test:doc3/1", "urn:x-opensiddur:test:doc4/1"]:
            results = self.resolver.resolve(f"{urn}@jps1917")
            self.assertEqual(results, [])


class TestUrnResolverSync(unittest.TestCase):
    """Test URN synchronization functionality."""

    def setUp(self):
        """Set up temporary database and file system."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.project_dir = Path(self.temp_dir.name) / 'projects'
        self.project_dir.mkdir()
        
        self.resolver = UrnResolver(self.db_path)
        self.addCleanup(self.resolver.close)

    def _create_xml_file(self, project: str, file_name: str, urns: list[str]):
        """Helper to create an XML file with URNs."""
        project_path = self.project_dir / project
        project_path.mkdir(exist_ok=True)
        
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        for urn in urns:
            elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
            elem.set("corresp", urn)
        
        file_path = project_path / file_name
        tree = etree.ElementTree(root)
        tree.write(str(file_path), encoding='utf-8', xml_declaration=True)
        return file_path

    def test_sync_file_add_new(self):
        """Test syncing a new file adds it to database."""
        # Create file on disk
        self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        
        # Sync the file
        result = self.resolver.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'added')
        self.assertEqual(result['urns'], 1)
        
        # Verify it's in database
        urns = self.resolver.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 1)

    def test_sync_file_unchanged(self):
        """Test syncing unchanged file skips it."""
        import time
        import os
        
        # Create and index file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        
        # Set file modification time to the past
        past_time = time.time() - 10
        os.utime(file_path, (past_time, past_time))
        
        # Index the file
        self.resolver.index_file(file_path, "test_proj", "doc1.xml")
        
        # Sync again without modifications
        result = self.resolver.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'skipped')
        self.assertEqual(result['urns'], 0)

    def test_sync_file_updated(self):
        """Test syncing modified file updates database."""
        import time
        import os
        
        # Create and index file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self.resolver.index_file(file_path, "test_proj", "doc1.xml")
        
        # Wait to ensure different timestamp (1 second to be safe)
        time.sleep(1.1)
        
        # Modify file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1", "urn:x-opensiddur:test:2"])
        
        # Explicitly update file modification time to current time
        now = time.time()
        os.utime(file_path, (now, now))
        
        # Sync the modified file
        result = self.resolver.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(result['urns'], 2)
        
        # Verify updated content
        urns = self.resolver.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 2)

    def test_sync_file_removed(self):
        """Test syncing removed file deletes from database."""
        # Index a file that doesn't exist
        self.resolver.add_mapping("urn:x-opensiddur:test:1", "test_proj", "doc1.xml")
        
        # Sync (file doesn't exist)
        result = self.resolver.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'removed')
        self.assertEqual(result['urns'], 1)
        
        # Verify removed from database
        urns = self.resolver.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 0)

    def test_sync_project_add_files(self):
        """Test syncing project adds new files."""
        # Create files on disk
        self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self._create_xml_file("test_proj", "doc2.xml", ["urn:x-opensiddur:test:2"])
        
        # Sync project
        result = self.resolver.sync_project("test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'project_synced')
        self.assertEqual(result['added'], 2)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(result['removed'], 0)
        self.assertEqual(result['skipped'], 0)

    def test_sync_project_remove_orphaned(self):
        """Test syncing project removes orphaned files."""
        # Add file to database that doesn't exist on disk
        self.resolver.add_mapping("urn:x-opensiddur:test:orphan", "test_proj", "orphan.xml")
        
        # Create one real file
        self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        
        # Sync project
        result = self.resolver.sync_project("test_proj", self.project_dir)
        
        self.assertEqual(result['removed'], 1)  # orphan.xml removed
        self.assertEqual(result['added'], 1)    # doc1.xml added
        
        # Verify orphan is gone
        files = self.resolver.get_files_by_project("test_proj")
        self.assertNotIn("orphan.xml", files)
        self.assertIn("doc1.xml", files)

    def test_sync_project_nonexistent(self):
        """Test syncing non-existent project removes it from database."""
        # Add project to database
        self.resolver.add_mapping("urn:x-opensiddur:test:1", "nonexistent", "doc1.xml")
        
        # Sync non-existent project
        result = self.resolver.sync_project("nonexistent", self.project_dir)
        
        self.assertEqual(result['action'], 'project_removed')
        self.assertGreater(result['removed'], 0)
        
        # Verify project is gone
        projects = self.resolver.list_projects()
        self.assertNotIn("nonexistent", projects)

    def test_sync_projects_all(self):
        """Test syncing all projects."""
        # Create projects on disk
        self._create_xml_file("proj1", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self._create_xml_file("proj2", "doc2.xml", ["urn:x-opensiddur:test:2"])
        
        # Add orphaned project to database
        self.resolver.add_mapping("urn:x-opensiddur:test:orphan", "orphaned_proj", "orphan.xml")
        
        # Sync all projects
        result = self.resolver.sync_projects(self.project_dir)
        
        self.assertEqual(result['action'], 'projects_synced')
        self.assertEqual(result['total_added'], 2)
        self.assertEqual(result['orphaned_projects_removed'], 1)
        
        # Verify projects
        projects = self.resolver.list_projects()
        self.assertIn("proj1", projects)
        self.assertIn("proj2", projects)
        self.assertNotIn("orphaned_proj", projects)

    def test_sync_projects_empty_directory(self):
        """Test syncing with empty project directory."""
        # Add some data to database
        self.resolver.add_mapping("urn:x-opensiddur:test:1", "proj1", "doc1.xml")
        
        # Sync with empty directory
        result = self.resolver.sync_projects(self.project_dir)
        
        self.assertEqual(result['orphaned_projects_removed'], 1)
        
        # Database should be empty
        projects = self.resolver.list_projects()
        self.assertEqual(projects, [])


class TestUrnResolverContextManager(unittest.TestCase):
    """Test URN resolver context manager functionality."""

    def test_context_manager(self):
        """Test using resolver as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'test_urn.db'
            
            with UrnResolver(db_path) as resolver:
                resolver.add_mapping("urn:x-opensiddur:test:doc1", "test", "doc1.xml")
                results = resolver.resolve("urn:x-opensiddur:test:doc1")
                self.assertEqual(len(results), 1)
            
            # Connection should be closed after context
            # Note: We can't easily test this without accessing internals


if __name__ == '__main__':
    unittest.main()

