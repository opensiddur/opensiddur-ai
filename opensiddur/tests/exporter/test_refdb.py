"""Tests for the ReferenceDatabase class."""

import unittest
import tempfile
from pathlib import Path
import time
import os
from lxml import etree
from lxml.etree import ElementBase
from opensiddur.exporter.refdb import (
    DuplicateUrnError,
    ReferenceDatabase,
    UrnMapping,
    Reference,
    find_end_of_mapping,
)


class TestReferenceDatabaseBasics(unittest.TestCase):
    """Test basic Reference Database functionality."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem

    def test_database_initialization(self):
        """Test that database and tables are created properly."""
        # Check that database file exists
        self.assertTrue(self.db_path.exists())
        
        # Check that urn_mappings table exists
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urn_mappings'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'urn_mappings')
        
        # Check that element_references table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='element_references'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'element_references')

    def test_add_urn_mapping(self):
        """Test adding a URN mapping."""
        project = "test_project"
        file_name = "doc1.xml"
        elem = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        
        self.db.add_urn_mapping(project, file_name, elem)
        
        # Verify it was added
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM urn_mappings WHERE urn = ?', ("urn:x-opensiddur:text:doc1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['urn'], "urn:x-opensiddur:text:doc1")
        self.assertEqual(row['project'], project)
        self.assertEqual(row['file_name'], file_name)

    def test_reindexing_the_same_element_is_idempotent(self):
        """Re-indexing a project must not fail on mappings it already holds."""
        project = "test_project"
        elem = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")

        self.db.add_urn_mapping(project, "file1.xml", elem)
        self.db.add_urn_mapping(project, "file1.xml", elem)

        cursor = self.db.conn.cursor()
        cursor.execute('SELECT COUNT(*) AS n FROM urn_mappings WHERE urn = ? AND project = ?',
                      ("urn:x-opensiddur:text:doc1", project))
        self.assertEqual(cursor.fetchone()['n'], 1)

    def test_the_same_urn_twice_in_one_project_is_an_error(self):
        """A URN names one stretch of text, so a second mapping for it is a data error.

        Resolving the conflict silently is how MAM's repeated Decalogue milestones went
        unnoticed: the row kept the first location and the rest became unreachable by URN.
        """
        project = "test_project"
        elem1 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        self.db.add_urn_mapping(project, "file1.xml", elem1)

        elem2 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        with self.assertRaises(DuplicateUrnError) as caught:
            self.db.add_urn_mapping(project, "file2.xml", elem2)
        self.assertIn("urn:x-opensiddur:text:doc1", str(caught.exception))

    def test_a_second_location_in_the_same_file_is_an_error(self):
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        first = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        first.set("corresp", "urn:x-opensiddur:text:doc1")
        second = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        second.set("corresp", "urn:x-opensiddur:text:doc1")

        self.db.add_urn_mapping("test_project", "file1.xml", first)
        with self.assertRaises(DuplicateUrnError):
            self.db.add_urn_mapping("test_project", "file1.xml", second)

    def test_add_urn_mapping_multiple_projects(self):
        """Test that same URN can exist in multiple projects."""
        elem1 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        elem2 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        
        self.db.add_urn_mapping("project1", "file1.xml", elem1)
        self.db.add_urn_mapping("project2", "file2.xml", elem2)
        
        # Verify both exist
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT project, file_name FROM urn_mappings WHERE urn = ? ORDER BY project', 
                      ("urn:x-opensiddur:text:doc1",))
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['project'], "project1")
        self.assertEqual(rows[1]['project'], "project2")


class TestReferenceDatabaseGetUrnMappings(unittest.TestCase):
    """Test get_urn_mappings functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)
        self._setup_test_data()
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem
    
    def _setup_test_data(self):
        """Set up test data after helper method is defined."""
        # Add test data
        elem1 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        elem2 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        elem3 = self._create_element_with_corresp("urn:x-opensiddur:test:doc2", "chapter")
        self.db.add_urn_mapping("wlc", "doc1.xml", elem1)
        self.db.add_urn_mapping("jps1917", "doc1.xml", elem2)
        self.db.add_urn_mapping("wlc", "doc2.xml", elem3)

    def test_get_urn_mappings_without_filters(self):
        """Test getting all URN mappings."""
        results = self.db.get_urn_mappings()
        
        self.assertEqual(len(results), 3)
        
    def test_get_urn_mappings_with_urn(self):
        """Test getting URN mappings filtered by URN."""
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:text:doc1")
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.urn, "urn:x-opensiddur:text:doc1")
        
    def test_get_urn_mappings_with_project(self):
        """Test getting URN mappings filtered by project."""
        results = self.db.get_urn_mappings(project="wlc")
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.project, "wlc")
            
    def test_get_urn_mappings_with_urn_and_project(self):
        """Test getting URN mappings filtered by both URN and project."""
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:text:doc1", project="wlc")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].urn, "urn:x-opensiddur:text:doc1")
        self.assertEqual(results[0].project, "wlc")


class TestReferenceDatabaseGetByProject(unittest.TestCase):
    """Test project-level query functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)
        self._setup_test_data()
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem
    
    def _setup_test_data(self):
        """Set up test data after helper method is defined."""
        # Add test data
        elem1 = self._create_element_with_corresp("urn:x-opensiddur:text:doc1", "chapter")
        elem2 = self._create_element_with_corresp("urn:x-opensiddur:test:doc2", "chapter")
        elem3 = self._create_element_with_corresp("urn:x-opensiddur:test:doc3", "chapter")
        self.db.add_urn_mapping("wlc", "doc1.xml", elem1)
        self.db.add_urn_mapping("wlc", "doc2.xml", elem2)
        self.db.add_urn_mapping("jps1917", "doc3.xml", elem3)

    def test_get_urns_by_project(self):
        """Test getting all URNs for a project."""
        results = self.db.get_urns_by_project("wlc")
        
        self.assertEqual(len(results), 2)
        urns = {r.urn for r in results}
        self.assertEqual(urns, {"urn:x-opensiddur:text:doc1", "urn:x-opensiddur:test:doc2"})
        
        # All should be in wlc project
        for result in results:
            self.assertEqual(result.project, "wlc")

    def test_get_urns_by_nonexistent_project(self):
        """Test getting URNs for non-existent project returns empty list."""
        results = self.db.get_urns_by_project("nonexistent")
        
        self.assertEqual(results, [])
    
    def test_get_files_by_project(self):
        """Test getting list of files in a project."""
        files = self.db.get_files_by_project("wlc")
        
        self.assertEqual(len(files), 2)
        self.assertIn("doc1.xml", files)
        self.assertIn("doc2.xml", files)
    
    def test_get_files_by_project_sorted(self):
        """Test that files are returned in sorted order."""
        files = self.db.get_files_by_project("wlc")
        
        self.assertEqual(files, ["doc1.xml", "doc2.xml"])
    
    def test_get_files_by_project_single_file(self):
        """Test getting files for project with single file."""
        files = self.db.get_files_by_project("jps1917")
        
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "doc3.xml")
    
    def test_get_files_by_nonexistent_project(self):
        """Test getting files for non-existent project returns empty list."""
        files = self.db.get_files_by_project("nonexistent")
        
        self.assertEqual(files, [])
    
    def test_get_files_by_project_no_duplicates(self):
        """Test that files list contains no duplicates."""
        # Add multiple URNs to same file
        self.db.add_urn_mapping("wlc", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:text:doc1/new", "chapter"))
        self.db.add_urn_mapping("wlc", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:text:doc1/another", "chapter"))
        
        files = self.db.get_files_by_project("wlc")
        
        # Should still be 2 files (doc1.xml and doc2.xml), not more
        self.assertEqual(len(files), 2)
        self.assertEqual(files.count("doc1.xml"), 1)  # No duplicates
    
    def test_list_projects(self):
        """Test listing all projects in the database."""
        projects = self.db.list_projects()
        
        self.assertEqual(len(projects), 2)
        self.assertIn("wlc", projects)
        self.assertIn("jps1917", projects)
    
    def test_list_projects_sorted(self):
        """Test that projects are returned in sorted order."""
        projects = self.db.list_projects()
        
        self.assertEqual(projects, ["jps1917", "wlc"])
    
    def test_list_projects_single(self):
        """Test listing when only one project exists."""
        # Remove jps1917 project
        self.db.remove_project("jps1917")
        
        projects = self.db.list_projects()
        
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], "wlc")
    
    def test_list_projects_empty(self):
        """Test listing projects when database is empty."""
        # Remove all projects
        self.db.remove_project("wlc")
        self.db.remove_project("jps1917")
        
        projects = self.db.list_projects()
        
        self.assertEqual(projects, [])


class TestReferenceDatabaseIndexing(unittest.TestCase):
    """Test URN indexing functionality."""

    def setUp(self):
        """Set up temporary database and XML files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.project_dir = Path(self.temp_dir.name) / 'projects'
        self.test_project_dir = self.project_dir / 'test_project'
        self.test_project_dir.mkdir(parents=True)
        
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)

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
            "urn:x-opensiddur:text:doc1",
            "urn:x-opensiddur:text:doc1/1",
            "urn:x-opensiddur:text:doc1/1/1",
        ]
        xml_path = self._create_test_xml("doc1.xml", urns)
        
        count = self.db.index_file(xml_path, "test_project", "doc1.xml")
        
        self.assertEqual(count, 3)
        
        # Verify URNs were indexed
        for urn in urns:
            results = self.db.get_urn_mappings(urn=urn)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].project, "test_project")
            self.assertEqual(results[0].file_name, "doc1.xml")

    def test_index_file_ignores_non_opensiddur_urns(self):
        """Test that indexing ignores URNs not starting with urn:x-opensiddur:."""
        urns = [
            "urn:x-opensiddur:text:doc1",
            "urn:other:test:doc2",  # Should be ignored
            "http://example.com",   # Should be ignored
        ]
        xml_path = self._create_test_xml("doc1.xml", urns)
        
        count = self.db.index_file(xml_path, "test_project", "doc1.xml")
        
        self.assertEqual(count, 1)  # Only one valid URN

    def test_index_urns(self):
        """Test indexing all XML files in a project directory."""
        # Create multiple XML files
        self._create_test_xml("doc1.xml", ["urn:x-opensiddur:text:doc1"])
        self._create_test_xml("doc2.xml", ["urn:x-opensiddur:test:doc2"])
        self._create_test_xml("doc3.xml", ["urn:x-opensiddur:test:doc3"])
        
        total = self.db.index_project("test_project", self.project_dir)
        
        self.assertEqual(total, 3)
        
        # Verify all were indexed
        results = self.db.get_urns_by_project("test_project")
        self.assertEqual(len(results), 3)

    def test_index_urns_nonexistent_project(self):
        """Test indexing non-existent project raises ValueError."""
        with self.assertRaises(ValueError):
            self.db.index_project("nonexistent_project", self.project_dir)

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
        
        count = self.db.index_file(xml_path, "test_project", "test.xml")
        
        self.assertEqual(count, 2)


class TestReferenceDatabaseRemoval(unittest.TestCase):
    """Test URN removal functionality."""

    def setUp(self):
        """Set up a temporary database with test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)
        self._setup_test_data()
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem
    
    def _setup_test_data(self):
        """Set up test data after helper method is defined."""
        # Add test data
        self.db.add_urn_mapping("wlc", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:text:doc1/1", "chapter"))
        self.db.add_urn_mapping("wlc", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:text:doc1/2", "chapter"))
        self.db.add_urn_mapping("wlc", "doc2.xml", self._create_element_with_corresp("urn:x-opensiddur:test:doc2/1", "chapter"))
        self.db.add_urn_mapping("jps1917", "doc3.xml", self._create_element_with_corresp("urn:x-opensiddur:test:doc3/1", "chapter"))
        self.db.add_urn_mapping("jps1917", "doc4.xml", self._create_element_with_corresp("urn:x-opensiddur:test:doc4/1", "chapter"))

    def test_remove_file(self):
        """Test removing all URNs for a specific file."""
        # Remove doc1.xml from wlc project
        removed_count = self.db.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify doc1.xml URNs are gone
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:text:doc1/1")
        self.assertEqual(results, [])
        
        # Verify other files still exist
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:test:doc2/1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_name, "doc2.xml")

    def test_remove_file_nonexistent(self):
        """Test removing non-existent file returns 0."""
        removed_count = self.db.remove_file("nonexistent.xml", "wlc")
        
        self.assertEqual(removed_count, 0)

    def test_remove_file_only_affects_specified_project(self):
        """Test that removing a file only affects the specified project."""
        # Add same file name in different project
        self.db.add_urn_mapping("jps1917", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:text:doc1/1", "chapter"))
        
        # Remove from wlc only
        removed_count = self.db.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify jps1917 version still exists
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:text:doc1/1", project="jps1917")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].project, "jps1917")

    def test_remove_project(self):
        """Test removing all URNs for an entire project."""
        # Remove entire wlc project
        removed_count = self.db.remove_project("wlc")
        
        self.assertEqual(removed_count, 3)  # doc1/1, doc1/2, doc2/1
        
        # Verify wlc URNs are gone
        results = self.db.get_urns_by_project("wlc")
        self.assertEqual(results, [])
        
        # Verify jps1917 still exists
        results = self.db.get_urns_by_project("jps1917")
        self.assertEqual(len(results), 2)

    def test_remove_project_nonexistent(self):
        """Test removing non-existent project returns 0."""
        removed_count = self.db.remove_project("nonexistent")
        
        self.assertEqual(removed_count, 0)

    def test_remove_project_all_files(self):
        """Test that removing project removes all files in that project."""
        # Remove jps1917 project
        removed_count = self.db.remove_project("jps1917")
        
        self.assertEqual(removed_count, 2)  # doc3/1, doc4/1
        
        # Verify all jps1917 URNs are gone
        for urn in ["urn:x-opensiddur:test:doc3/1", "urn:x-opensiddur:test:doc4/1"]:
            results = self.db.get_urn_mappings(urn=urn, project="jps1917")
            self.assertEqual(results, [])


class TestReferenceDatabaseSync(unittest.TestCase):
    """Test URN synchronization functionality."""

    def setUp(self):
        """Set up temporary database and file system."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.project_dir = Path(self.temp_dir.name) / 'projects'
        self.project_dir.mkdir()
        
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem

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
        result = self.db.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'added')
        self.assertEqual(result['references'], 1)
        
        # Verify it's in database
        urns = self.db.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 1)

    def test_sync_file_unchanged(self):
        """Test syncing unchanged file skips it."""
        # Create and index file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        
        # Set file modification time to the past
        past_time = time.time() - 10
        os.utime(file_path, (past_time, past_time))
        
        # Index the file
        self.db.index_file(file_path, "test_proj", "doc1.xml")
        
        # Sync again without modifications
        result = self.db.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'skipped')
        self.assertEqual(result['references'], 0)

    def test_sync_file_updated(self):
        """Test syncing modified file updates database."""
        # Create and index file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self.db.index_file(file_path, "test_proj", "doc1.xml")
        
        # Wait to ensure different timestamp (1 second to be safe)
        time.sleep(1.1)
        
        # Modify file
        file_path = self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1", "urn:x-opensiddur:test:2"])
        
        # Explicitly update file modification time to current time
        now = time.time()
        os.utime(file_path, (now, now))
        
        # Sync the modified file
        result = self.db.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'updated')
        self.assertEqual(result['references'], 2)
        
        # Verify updated content
        urns = self.db.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 2)

    def test_sync_file_removed(self):
        """Test syncing removed file deletes from database."""
        # Index a file that doesn't exist
        self.db.add_urn_mapping("test_proj", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:test:1", "chapter"))
        
        # Sync (file doesn't exist)
        result = self.db.sync_file("doc1.xml", "test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'removed')
        self.assertEqual(result['references'], 1)
        
        # Verify removed from database
        urns = self.db.get_urns_by_project("test_proj")
        self.assertEqual(len(urns), 0)

    def test_sync_project_add_files(self):
        """Test syncing project adds new files."""
        # Create files on disk
        self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self._create_xml_file("test_proj", "doc2.xml", ["urn:x-opensiddur:test:2"])
        
        # Sync project
        result = self.db.sync_project("test_proj", self.project_dir)
        
        self.assertEqual(result['action'], 'project_synced')
        self.assertEqual(result['added'], 2)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(result['removed'], 0)
        self.assertEqual(result['skipped'], 0)

    def test_sync_project_remove_orphaned(self):
        """Test syncing project removes orphaned files."""
        # Add file to database that doesn't exist on disk
        self.db.add_urn_mapping("test_proj", "orphan.xml", self._create_element_with_corresp("urn:x-opensiddur:test:orphan", "chapter"))
        
        # Create one real file
        self._create_xml_file("test_proj", "doc1.xml", ["urn:x-opensiddur:test:1"])
        
        # Sync project
        result = self.db.sync_project("test_proj", self.project_dir)
        
        self.assertEqual(result['removed'], 1)  # orphan.xml removed
        self.assertEqual(result['added'], 1)    # doc1.xml added
        
        # Verify orphan is gone
        files = self.db.get_files_by_project("test_proj")
        self.assertNotIn("orphan.xml", files)
        self.assertIn("doc1.xml", files)

    def test_sync_project_nonexistent(self):
        """Test syncing non-existent project removes it from database."""
        # Add project to database
        self.db.add_urn_mapping("nonexistent", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:test:1", "chapter"))
        
        # Sync non-existent project
        result = self.db.sync_project("nonexistent", self.project_dir)
        
        self.assertEqual(result['action'], 'project_removed')
        self.assertGreater(result['removed'], 0)
        
        # Verify project is gone
        projects = self.db.list_projects()
        self.assertNotIn("nonexistent", projects)

    def test_sync_projects_all(self):
        """Test syncing all projects."""
        # Create projects on disk
        self._create_xml_file("proj1", "doc1.xml", ["urn:x-opensiddur:test:1"])
        self._create_xml_file("proj2", "doc2.xml", ["urn:x-opensiddur:test:2"])
        
        # Add orphaned project to database
        self.db.add_urn_mapping("orphaned_proj", "orphan.xml", self._create_element_with_corresp("urn:x-opensiddur:test:orphan", "chapter"))
        
        # Sync all projects
        result = self.db.sync_projects(self.project_dir)
        
        self.assertEqual(result['action'], 'projects_synced')
        self.assertEqual(result['total_added'], 2)
        self.assertEqual(result['orphaned_projects_removed'], 1)
        
        # Verify projects
        projects = self.db.list_projects()
        self.assertIn("proj1", projects)
        self.assertIn("proj2", projects)
        self.assertNotIn("orphaned_proj", projects)

    def test_sync_projects_empty_directory(self):
        """Test syncing with empty project directory."""
        # Add some data to database
        self.db.add_urn_mapping("proj1", "doc1.xml", self._create_element_with_corresp("urn:x-opensiddur:test:1", "chapter"))
        
        # Sync with empty directory
        result = self.db.sync_projects(self.project_dir)
        
        self.assertEqual(result['orphaned_projects_removed'], 1)
        
        # Database should be empty
        projects = self.db.list_projects()
        self.assertEqual(projects, [])


class TestReferenceDatabaseReferences(unittest.TestCase):
    """Test reference tracking functionality."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_ref.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)

    def _create_element_with_target(self, target: str, element_type: str = None, 
                                   target_end: str = None, corresp: str = None):
        """Helper to create an element with target attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}ptr")
        elem.set("target", target)
        if element_type:
            elem.set("type", element_type)
        if target_end:
            elem.set("targetEnd", target_end)
        if corresp:
            elem.set("corresp", corresp)
        return elem
    
    def _create_element_with_corresp(self, corresp: str, element_type: str = None) -> ElementBase:
        """Helper method to create an element with a corresp attribute."""
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        elem.set("corresp", corresp)
        if element_type:
            elem.set("type", element_type)
        return elem

    def test_add_reference_with_urn_target(self):
        """Test adding a reference with URN target."""
        elem = self._create_element_with_target(
            target="urn:x-opensiddur:text:doc1",
            element_type="transclude",
            corresp="urn:x-opensiddur:ref:1"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify it was added
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:text:doc1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['target_start'], "urn:x-opensiddur:text:doc1")
        self.assertEqual(row['element_type'], "transclude")
        self.assertEqual(row['corresponding_urn'], "urn:x-opensiddur:ref:1")
        self.assertFalse(row['target_is_id'])
        self.assertEqual(row['project'], "test_project")
        self.assertEqual(row['file_name'], "test.xml")

    def test_add_reference_with_id_target(self):
        """Test adding a reference with ID target (#id format)."""
        elem = self._create_element_with_target(
            target="#verse1",
            element_type="link"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify it was added
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE target_start = ?', ("#verse1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['target_start'], "#verse1")
        self.assertTrue(row['target_is_id'])

    def test_add_reference_with_target_range(self):
        """Test adding a reference with targetEnd."""
        elem = self._create_element_with_target(
            target="urn:x-opensiddur:text:doc1/1",
            target_end="urn:x-opensiddur:text:doc1/5",
            element_type="range"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify range was stored
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:text:doc1/1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['target_end'], "urn:x-opensiddur:text:doc1/5")

    def test_add_reference_with_multiple_targets(self):
        """Test adding a reference with space-separated targets."""
        elem = self._create_element_with_target(
            target="urn:x-opensiddur:text:doc1 urn:x-opensiddur:test:doc2",
            element_type="multi"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify both targets were added as separate rows
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE project = ? AND file_name = ?', 
                      ("test_project", "test.xml"))
        rows = cursor.fetchall()
        
        self.assertEqual(len(rows), 2)
        targets = {row['target_start'] for row in rows}
        self.assertEqual(targets, {"urn:x-opensiddur:text:doc1", "urn:x-opensiddur:test:doc2"})

    def test_add_reference_stores_element_path(self):
        """Test that element path is correctly stored."""
        elem = self._create_element_with_target(target="urn:x-opensiddur:text:doc1")
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify element path was stored
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT element_path FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:text:doc1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        # Path should be like /ns0:TEI/ns0:ptr or /TEI[1]/ptr[1]
        # Just verify it has "ptr" in it
        self.assertIn("ptr", row['element_path'])

    def test_get_references_to_urn(self):
        """Test retrieving references to a URN."""
        # Create two different XML trees so elements have different paths
        root1 = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        elem1 = etree.SubElement(root1, "{http://www.tei-c.org/ns/1.0}ptr")
        elem1.set("target", "urn:x-opensiddur:test:target")
        elem1.set("type", "type1")
        elem1.set("corresp", "urn:x-opensiddur:ref:1")
        
        root2 = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        div = etree.SubElement(root2, "{http://www.tei-c.org/ns/1.0}div")
        elem2 = etree.SubElement(div, "{http://www.tei-c.org/ns/1.0}ptr")
        elem2.set("target", "urn:x-opensiddur:test:target")
        elem2.set("type", "type2")
        elem2.set("corresp", "urn:x-opensiddur:ref:2")
        
        self.db.add_reference("proj1", "file1.xml", elem1)
        self.db.add_reference("proj1", "file2.xml", elem2)
        
        # Get references to the target URN
        results = self.db.get_references_to(urn="urn:x-opensiddur:test:target")
        
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], Reference)
        element_types = {r.element_type for r in results}
        self.assertEqual(element_types, {"type1", "type2"})

    def test_get_references_to_id(self):
        """Test retrieving references to an ID."""
        elem = self._create_element_with_target(target="#verse1")
        self.db.add_reference("proj1", "file1.xml", elem)
        
        # Get references to the ID
        results = self.db.get_references_to(id="verse1", project="proj1", file_name="file1.xml")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].target_start, "#verse1")
        self.assertTrue(results[0].target_is_id)

    def test_get_references_by_project(self):
        """Test retrieving all references for a project."""
        elem1 = self._create_element_with_target(target="urn:x-opensiddur:text:doc1")
        elem2 = self._create_element_with_target(target="urn:x-opensiddur:test:doc2")
        elem3 = self._create_element_with_target(target="urn:x-opensiddur:test:doc3")
        
        self.db.add_reference("proj1", "file1.xml", elem1)
        self.db.add_reference("proj1", "file2.xml", elem2)
        self.db.add_reference("proj2", "file3.xml", elem3)
        
        # Get references for proj1
        results = self.db.get_references_by_project("proj1")
        
        self.assertEqual(len(results), 2)
        projects = {r.project for r in results}
        self.assertEqual(projects, {"proj1"})

    def test_index_file_with_references(self):
        """Test that indexing a file also indexes references."""
        # Create XML with both URNs and references
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        
        # Element with corresp (URN)
        div = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        div.set("corresp", "urn:x-opensiddur:text:doc1")
        
        # Element with target (reference)
        ptr = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}ptr")
        ptr.set("target", "urn:x-opensiddur:test:target")
        ptr.set("type", "link")
        
        # Write to file
        xml_path = Path(self.temp_dir.name) / "test.xml"
        tree = etree.ElementTree(root)
        tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
        
        # Index the file
        count = self.db.index_file(xml_path, "test_project", "test.xml")
        
        # Should have indexed both URN and reference
        self.assertEqual(count, 2)
        
        # Verify URN was indexed
        urns = self.db.get_urn_mappings(project="test_project")
        self.assertEqual(len(urns), 1)
        
        # Verify reference was indexed
        refs = self.db.get_references_by_project("test_project")
        self.assertEqual(len(refs), 1)

    def test_remove_file_removes_references(self):
        """Test that removing a file also removes its references."""
        elem = self._create_element_with_target(target="urn:x-opensiddur:text:doc1")
        self.db.add_reference("proj1", "file1.xml", elem)
        
        # Also add a URN mapping
        self.db.add_urn_mapping("proj1", "file1.xml", self._create_element_with_corresp("urn:x-opensiddur:test:urn1", "chapter"))
        
        # Remove the file
        removed_count = self.db.remove_file("file1.xml", "proj1")
        
        # Should have removed both URN and reference
        self.assertEqual(removed_count, 2)
        
        # Verify references are gone
        refs = self.db.get_references_by_project("proj1")
        self.assertEqual(len(refs), 0)

    def test_remove_project_removes_references(self):
        """Test that removing a project also removes its references."""
        elem = self._create_element_with_target(target="urn:x-opensiddur:text:doc1")
        self.db.add_reference("proj1", "file1.xml", elem)
        self.db.add_urn_mapping("proj1", "file1.xml", self._create_element_with_corresp("urn:x-opensiddur:test:urn1", "chapter"))
        
        # Remove the project
        removed_count = self.db.remove_project("proj1")
        
        # Should have removed both URN and reference
        self.assertEqual(removed_count, 2)
        
        # Verify references are gone
        refs = self.db.get_references_by_project("proj1")
        self.assertEqual(len(refs), 0)

    def test_integration_get_references_to_id(self):
        """Integration test: Verify get_references_to finds references to elements with xml:id."""
        # Create XML structure with:
        # 1. An element with xml:id="verse1"
        # 2. Another element with target="#verse1" that references it
        
        root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
        
        # Create the target element with xml:id
        target_div = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
        target_div.set("{http://www.w3.org/XML/1998/namespace}id", "verse1")
        target_div.text = "This is verse 1"
        
        # Create a referencing element
        ref_ptr = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}ptr")
        ref_ptr.set("target", "#verse1")
        ref_ptr.set("type", "link")
        
        # Create another referencing element to the same ID
        ref_note = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}note")
        ref_note.set("target", "#verse1")
        ref_note.set("type", "comment")
        ref_note.text = "This references verse 1"
        
        # Create a reference to a different ID that doesn't exist
        ref_missing = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}ptr")
        ref_missing.set("target", "#nonexistent")
        ref_missing.set("type", "link")
        
        # Write to file and index it using the real workflow
        xml_path = Path(self.temp_dir.name) / "test.xml"
        tree = etree.ElementTree(root)
        tree.write(str(xml_path), encoding='utf-8', xml_declaration=True)
        
        # Use index_file() to process the XML file
        count = self.db.index_file(xml_path, "test_project", "test.xml")
        self.assertEqual(count, 3, "Should have indexed 3 references")
        
        # Test 1: Get references to "verse1" by ID (without # prefix)
        results = self.db.get_references_to(id="verse1", project="test_project", file_name="test.xml")
        self.assertEqual(len(results), 2, "Should find 2 references to verse1")
        
        # Verify the results contain the expected references
        element_types = {r.element_type for r in results}
        self.assertEqual(element_types, {"link", "comment"})
        
        # Verify all references point to the correct target
        for result in results:
            self.assertEqual(result.target_start, "#verse1")
            self.assertTrue(result.target_is_id)
            self.assertEqual(result.project, "test_project")
            self.assertEqual(result.file_name, "test.xml")
        
        # Test 2: Get references to "verse1" by ID (with # prefix)
        results_with_hash = self.db.get_references_to(id="#verse1", project="test_project", file_name="test.xml")
        self.assertEqual(len(results_with_hash), 2, "Should find 2 references with # prefix too")
        
        # Test 3: Get references to nonexistent ID
        results_nonexistent = self.db.get_references_to(id="nonexistent", project="test_project", file_name="test.xml")
        self.assertEqual(len(results_nonexistent), 1, "Should find 1 reference to nonexistent ID")
        
        # Verify it's the reference to #nonexistent
        self.assertEqual(results_nonexistent[0].target_start, "#nonexistent")
        
        # Test 4: Get references to a completely different ID
        results_different = self.db.get_references_to(id="different", project="test_project", file_name="test.xml")
        self.assertEqual(len(results_different), 0, "Should find no references to different ID")
        
        # Test 5: Verify element paths are stored and are unique
        paths = {r.element_path for r in results}
        self.assertEqual(len(paths), 2, "Should have 2 unique element paths")
        
        # Test 6: Verify we can get all references for the project
        all_project_refs = self.db.get_references_by_project("test_project")
        self.assertEqual(len(all_project_refs), 3, "Should have 3 total references in project")
        
        # Test 7: Verify the references contain the expected element tags
        element_tags = {r.element_tag for r in all_project_refs}
        self.assertEqual(element_tags, {"{http://www.tei-c.org/ns/1.0}ptr", "{http://www.tei-c.org/ns/1.0}note"})


class TestMilestoneScoping(unittest.TestCase):
    """Test that a milestone's URN scope ends at the right following milestone.

    A milestone scopes to the next milestone of the same unit, or of a unit that contains it.
    Reading divisions overlap on purpose, so they must not terminate each other.
    """

    TEI = "http://www.tei-c.org/ns/1.0"

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = ReferenceDatabase(Path(self.temp_dir.name) / 'test_urn.db')
        self.addCleanup(self.db.close)

    def _document(self, *milestones: tuple[str, str, str]) -> list[ElementBase]:
        """Build a doc of `(unit, n, corresp)` milestones separated by text-bearing segs.

        Returns the milestone elements in document order.
        """
        root = etree.Element(f"{{{self.TEI}}}TEI")
        text = etree.SubElement(root, f"{{{self.TEI}}}text")
        body = etree.SubElement(text, f"{{{self.TEI}}}body")
        created = []
        for index, (unit, n, corresp) in enumerate(milestones):
            milestone = etree.SubElement(body, f"{{{self.TEI}}}milestone")
            if unit is not None:
                milestone.set("unit", unit)
            milestone.set("n", n)
            milestone.set("corresp", corresp)
            created.append(milestone)
            seg = etree.SubElement(body, f"{{{self.TEI}}}seg")
            seg.set("{http://www.w3.org/XML/1998/namespace}id", f"seg{index}")
            seg.text = f"text {index}"
        return created

    def _scope_end(self, milestone: ElementBase) -> str:
        end_path, _ = find_end_of_mapping(milestone)
        return end_path

    def test_verse_ends_at_next_verse(self):
        verse1, _verse2 = self._document(
            ("verse", "1", "urn:x-opensiddur:text:bible:genesis/1/1"),
            ("verse", "2", "urn:x-opensiddur:text:bible:genesis/1/2"),
        )
        self.assertTrue(self._scope_end(verse1).endswith("seg[1]"))

    def test_verse_ends_at_next_chapter(self):
        """A chapter contains verses, so it closes the last verse of the previous chapter.

        Without this, a range ending on a chapter boundary would swallow the following
        chapter milestone and render a spurious chapter number.
        """
        verse, _chapter = self._document(
            ("verse", "31", "urn:x-opensiddur:text:bible:genesis/1/31"),
            ("chapter", "2", "urn:x-opensiddur:text:bible:genesis/2"),
        )
        self.assertTrue(self._scope_end(verse).endswith("seg[1]"))

    def test_chapter_does_not_end_at_verse(self):
        """Containment is one-directional: a verse must not close the chapter holding it."""
        chapter, _verse, _next_chapter = self._document(
            ("chapter", "1", "urn:x-opensiddur:text:bible:genesis/1"),
            ("verse", "1", "urn:x-opensiddur:text:bible:genesis/1/1"),
            ("chapter", "2", "urn:x-opensiddur:text:bible:genesis/2"),
        )
        # Ends just before chapter 2, i.e. after the second seg, not the first.
        self.assertTrue(self._scope_end(chapter).endswith("seg[2]"))

    def test_verse_does_not_end_at_a_half_verse_inside_it(self):
        """A verse holding sub-verse milestones still runs to the next verse.

        If the halves closed the verse, every verse carrying them would silently shrink to
        its first half wherever it were transcluded.
        """
        verse, _a, _b, _next_verse = self._document(
            ("verse", "31", "urn:x-opensiddur:text:bible:genesis/1/31"),
            ("half-verse", "a", "urn:x-opensiddur:text:bible:genesis/1/31/a"),
            ("half-verse", "b", "urn:x-opensiddur:text:bible:genesis/1/31/b"),
            ("verse", "1", "urn:x-opensiddur:text:bible:genesis/2/1"),
        )
        self.assertTrue(self._scope_end(verse).endswith("seg[3]"))

    def test_half_verse_ends_at_the_next_half_verse(self):
        verse_a = self._document(
            ("verse", "31", "urn:x-opensiddur:text:bible:genesis/1/31"),
            ("half-verse", "a", "urn:x-opensiddur:text:bible:genesis/1/31/a"),
            ("half-verse", "b", "urn:x-opensiddur:text:bible:genesis/1/31/b"),
        )[1]
        self.assertTrue(self._scope_end(verse_a).endswith("seg[2]"))

    def test_half_verse_ends_at_the_next_verse(self):
        """The second half runs to the end of its verse and no further."""
        verse_b = self._document(
            ("verse", "31", "urn:x-opensiddur:text:bible:genesis/1/31"),
            ("half-verse", "b", "urn:x-opensiddur:text:bible:genesis/1/31/b"),
            ("verse", "1", "urn:x-opensiddur:text:bible:genesis/2/1"),
        )[1]
        self.assertTrue(self._scope_end(verse_b).endswith("seg[2]"))

    def test_a_verse_part_is_not_ended_by_a_half_verse(self):
        """The two sub-verse divisions cut at different points and must not close each other.

        The Thirteen Attributes end one word past the etnachta of Exodus 34:7, so a named
        part really does straddle the accentual boundary.
        """
        venakeh = self._document(
            ("verse", "7", "urn:x-opensiddur:text:bible:exodus/34/7"),
            ("verse-part", "venakeh", "urn:x-opensiddur:text:bible:exodus/34/7/venakeh"),
            ("half-verse", "b", "urn:x-opensiddur:text:bible:exodus/34/7/b"),
            ("verse-part", "lo_yenakeh", "urn:x-opensiddur:text:bible:exodus/34/7/lo_yenakeh"),
        )[1]
        self.assertTrue(self._scope_end(venakeh).endswith("seg[3]"))

    def test_maftir_does_not_end_the_seventh_aliyah(self):
        """Maftir re-reads the close of aliyah 7; it opens inside it rather than ending it."""
        aliyah7, _maftir, _parsha = self._document(
            ("aliyah.annual", "7", "urn:x-opensiddur:text:bible:parsha/bereshit/aliyah/7"),
            ("maftir.annual", "maftir", "urn:x-opensiddur:text:bible:parsha/bereshit/maftir"),
            ("parsha.annual", "noach", "urn:x-opensiddur:text:bible:parsha/noach"),
        )
        # Runs past the maftir milestone to the end of the parsha.
        self.assertTrue(self._scope_end(aliyah7).endswith("seg[2]"))

    def test_overlapping_reading_schemes_do_not_terminate_each_other(self):
        """Weekday and triennial aliyot subdivide/cut across the annual ones."""
        annual1, _weekday2, _triennial1, _annual2 = self._document(
            ("aliyah.annual", "1", "urn:x-opensiddur:text:bible:parsha/bereshit/aliyah/1"),
            ("aliyah.weekday", "2", "urn:x-opensiddur:text:bible:parsha/bereshit/weekday/2"),
            ("aliyah.triennial", "1", "urn:x-opensiddur:text:bible:parsha/bereshit/triennial/1/1"),
            ("aliyah.annual", "2", "urn:x-opensiddur:text:bible:parsha/bereshit/aliyah/2"),
        )
        self.assertTrue(self._scope_end(annual1).endswith("seg[3]"))

    def test_parsha_ends_an_aliyah(self):
        """Aliyot do not cross parsha boundaries."""
        aliyah7, _parsha = self._document(
            ("aliyah.annual", "7", "urn:x-opensiddur:text:bible:parsha/bereshit/aliyah/7"),
            ("parsha.annual", "noach", "urn:x-opensiddur:text:bible:parsha/noach"),
        )
        self.assertTrue(self._scope_end(aliyah7).endswith("seg[1]"))

    def test_a_combined_aliyah_crosses_the_parsha_it_runs_into(self):
        """Two parshiyot read together divide as one reading, across the boundary between them."""
        combined1, _second_parsha, _combined2 = self._document(
            ("aliyah.combined", "4",
             "urn:x-opensiddur:text:bible:parsha/vayakhel_pekudei/aliyah_combined/4"),
            ("parsha.annual", "pekudei", "urn:x-opensiddur:text:bible:parsha/pekudei"),
            ("aliyah.combined", "5",
             "urn:x-opensiddur:text:bible:parsha/vayakhel_pekudei/aliyah_combined/5"),
        )
        # Runs past where Pekudei begins, to the next combined aliyah.
        self.assertTrue(self._scope_end(combined1).endswith("seg[2]"))

    def test_a_combined_reading_ends_the_divisions_it_contains(self):
        combined_aliyah, _pair = self._document(
            ("aliyah.combined", "7",
             "urn:x-opensiddur:text:bible:parsha/vayakhel_pekudei/aliyah_combined/7"),
            ("parsha.combined", "chukat_balak",
             "urn:x-opensiddur:text:bible:parsha/chukat_balak"),
        )
        self.assertTrue(self._scope_end(combined_aliyah).endswith("seg[1]"))

    def test_a_triennial_variation_is_scoped_by_the_pair_not_by_either_parshah(self):
        """Behar read alone in one cycle runs into Bechukotai, so the pair is what ends it."""
        variation, _second_parsha, _pair = self._document(
            ("aliyah.triennial.behar.IL3.2", "IL3.2.7",
             "urn:x-opensiddur:text:bible:parsha/behar/aliyah_triennial_behar_IL3_2/il3.2.7"),
            ("parsha.annual", "bechukotai", "urn:x-opensiddur:text:bible:parsha/bechukotai"),
            ("parsha.combined", "behar_bechukotai",
             "urn:x-opensiddur:text:bible:parsha/behar_bechukotai"),
        )
        self.assertTrue(self._scope_end(variation).endswith("seg[2]"))

    def test_falls_back_to_urn_depth_without_units(self):
        """Milestones with no @unit keep the original URN-depth heuristic."""
        verse, _chapter = self._document(
            (None, "1", "urn:x-opensiddur:text:prayer:ashrei/1/1"),
            (None, "2", "urn:x-opensiddur:text:prayer:ashrei/2"),
        )
        self.assertTrue(self._scope_end(verse).endswith("seg[1]"))

    def test_unknown_unit_falls_back_to_urn_depth(self):
        """A unit absent from the containment table still terminates by URN depth."""
        first, _second = self._document(
            ("stanza", "1", "urn:x-opensiddur:text:poem:example/1"),
            ("stanza", "2", "urn:x-opensiddur:text:poem:example/2"),
        )
        self.assertTrue(self._scope_end(first).endswith("seg[1]"))

    def test_scope_runs_to_end_of_file_when_nothing_terminates(self):
        only, = self._document(
            ("aliyah.annual", "1", "urn:x-opensiddur:text:bible:parsha/bereshit/aliyah/1"),
        )
        # A lone seg carries no positional predicate in the lxml path.
        self.assertTrue(self._scope_end(only).endswith("seg"))


class TestReferenceDatabaseContextManager(unittest.TestCase):
    """Test Reference Database context manager functionality."""

    def test_context_manager(self):
        """Test using database as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'test_urn.db'
            
            with ReferenceDatabase(db_path) as db:
                # Create element with corresp attribute
                root = etree.Element("{http://www.tei-c.org/ns/1.0}TEI")
                elem = etree.SubElement(root, "{http://www.tei-c.org/ns/1.0}div")
                elem.set("corresp", "urn:x-opensiddur:text:doc1")
                elem.set("type", "chapter")
                
                db.add_urn_mapping("test", "doc1.xml", elem)
                results = db.get_urn_mappings(urn="urn:x-opensiddur:text:doc1")
                self.assertEqual(len(results), 1)
            
            # Connection should be closed after context


class TestFindEndOfMapping(unittest.TestCase):
    """Test the end-of-range computation that backs milestone-scoped URNs."""

    def _end_of(self, xml: str, corresp: str) -> tuple[str, bool]:
        """Return (end path, include_tail) for the element carrying `corresp`."""
        root = etree.fromstring(xml.encode('utf-8'))
        element = root.xpath(f"//*[@corresp='{corresp}']")[0]
        return find_end_of_mapping(element)

    def test_non_milestone_ends_at_itself(self):
        """A non-milestone URN scopes to its own element and excludes its tail."""
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div corresp="urn:a"><tei:p>text</tei:p></tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:a")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div")
        self.assertFalse(include_tail)

    def test_ends_at_preceding_sibling_of_next_milestone(self):
        """A milestone scopes up to the element just before the next same-level one."""
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div>
        <tei:milestone unit="verse" corresp="urn:book/1/1"/> one
        <tei:seg>segment</tei:seg> more
        <tei:milestone unit="verse" corresp="urn:book/1/2"/> two
    </tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:book/1/1")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div/tei:seg")
        self.assertTrue(include_tail)

    def test_ends_at_the_element_whose_tail_is_the_last_text(self):
        """The end is the preceding sibling itself, never a node nested inside it.

        Ending at the deepest preceding element would drop the text between that
        element's close and the next milestone -- here, ' more'.
        """
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div>
        <tei:milestone unit="verse" corresp="urn:book/1/1"/> one
        <tei:choice><tei:abbr>abbr</tei:abbr><tei:expan>expansion</tei:expan></tei:choice> more
        <tei:milestone unit="verse" corresp="urn:book/1/2"/> two
    </tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:book/1/1")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div/tei:choice")
        self.assertTrue(include_tail)

    def test_next_milestone_in_another_parent_ends_at_that_parents_predecessor(self):
        """When the next milestone opens a paragraph, the range ends with the previous one."""
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div>
        <tei:p><tei:milestone unit="verse" corresp="urn:book/1/1"/> one</tei:p>
        <tei:p><tei:milestone unit="verse" corresp="urn:book/1/2"/> two</tei:p>
        <tei:p><tei:milestone unit="verse" corresp="urn:book/1/3"/> three</tei:p>
    </tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:book/1/2")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div/tei:p[2]")
        self.assertTrue(include_tail)

    def test_higher_level_milestone_ends_the_range(self):
        """A chapter milestone terminates a verse range."""
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div>
        <tei:milestone unit="verse" corresp="urn:book/1/1"/> one
        <tei:seg>segment</tei:seg> more
        <tei:milestone unit="chapter" corresp="urn:book/2"/> next chapter
    </tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:book/1/1")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div/tei:seg")
        self.assertTrue(include_tail)

    def test_no_following_milestone_ends_at_the_last_sibling(self):
        """The last milestone in a file scopes to the end of its parent."""
        xml = '''<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text><tei:body><tei:div>
        <tei:milestone unit="verse" corresp="urn:book/1/1"/> one
        <tei:seg>segment</tei:seg>
        <tei:p>last</tei:p>
    </tei:div></tei:body></tei:text>
</tei:TEI>'''
        end_path, include_tail = self._end_of(xml, "urn:book/1/1")
        self.assertEqual(end_path, "/tei:TEI/tei:text/tei:body/tei:div/tei:p")
        self.assertTrue(include_tail)


if __name__ == '__main__':
    unittest.main()

