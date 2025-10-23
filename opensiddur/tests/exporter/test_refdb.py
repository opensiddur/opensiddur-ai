"""Tests for the ReferenceDatabase class."""

import unittest
import tempfile
from pathlib import Path
import time
import os
from lxml import etree
from opensiddur.exporter.refdb import ReferenceDatabase, UrnMapping, Reference


class TestReferenceDatabaseBasics(unittest.TestCase):
    """Test basic Reference Database functionality."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / 'test_urn.db'
        self.db = ReferenceDatabase(self.db_path)
        self.addCleanup(self.db.close)

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
        urn = "urn:x-opensiddur:test:doc1"
        project = "test_project"
        file_name = "doc1.xml"
        
        self.db.add_urn_mapping(urn, project, file_name)
        
        # Verify it was added
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM urn_mappings WHERE urn = ?', (urn,))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['urn'], urn)
        self.assertEqual(row['project'], project)
        self.assertEqual(row['file_name'], file_name)

    def test_add_urn_mapping_update(self):
        """Test updating an existing URN mapping."""
        urn = "urn:x-opensiddur:test:doc1"
        project = "test_project"
        
        # Add initial mapping
        self.db.add_urn_mapping(urn, project, "file1.xml")
        
        # Update with new file name
        self.db.add_urn_mapping(urn, project, "file2.xml")
        
        # Verify it was updated
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT file_name FROM urn_mappings WHERE urn = ? AND project = ?', 
                      (urn, project))
        row = cursor.fetchone()
        self.assertEqual(row['file_name'], "file2.xml")

    def test_add_urn_mapping_multiple_projects(self):
        """Test that same URN can exist in multiple projects."""
        urn = "urn:x-opensiddur:test:doc1"
        
        self.db.add_urn_mapping(urn, "project1", "file1.xml")
        self.db.add_urn_mapping(urn, "project2", "file2.xml")
        
        # Verify both exist
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT project, file_name FROM urn_mappings WHERE urn = ? ORDER BY project', 
                      (urn,))
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
        
        # Add test data
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1", "wlc", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1", "jps1917", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc2", "wlc", "doc2.xml")

    def test_get_urn_mappings_without_filters(self):
        """Test getting all URN mappings."""
        results = self.db.get_urn_mappings()
        
        self.assertEqual(len(results), 3)
        
    def test_get_urn_mappings_with_urn(self):
        """Test getting URN mappings filtered by URN."""
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:test:doc1")
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.urn, "urn:x-opensiddur:test:doc1")
        
    def test_get_urn_mappings_with_project(self):
        """Test getting URN mappings filtered by project."""
        results = self.db.get_urn_mappings(project="wlc")
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.project, "wlc")
            
    def test_get_urn_mappings_with_urn_and_project(self):
        """Test getting URN mappings filtered by both URN and project."""
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:test:doc1", project="wlc")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].urn, "urn:x-opensiddur:test:doc1")
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
        
        # Add test data
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1", "wlc", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc2", "wlc", "doc2.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc3", "jps1917", "doc3.xml")

    def test_get_urns_by_project(self):
        """Test getting all URNs for a project."""
        results = self.db.get_urns_by_project("wlc")
        
        self.assertEqual(len(results), 2)
        urns = {r.urn for r in results}
        self.assertEqual(urns, {"urn:x-opensiddur:test:doc1", "urn:x-opensiddur:test:doc2"})
        
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1/new", "wlc", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1/another", "wlc", "doc1.xml")
        
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
            "urn:x-opensiddur:test:doc1",
            "urn:x-opensiddur:test:doc1/1",
            "urn:x-opensiddur:test:doc1/1/1",
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
            "urn:x-opensiddur:test:doc1",
            "urn:other:test:doc2",  # Should be ignored
            "http://example.com",   # Should be ignored
        ]
        xml_path = self._create_test_xml("doc1.xml", urns)
        
        count = self.db.index_file(xml_path, "test_project", "doc1.xml")
        
        self.assertEqual(count, 1)  # Only one valid URN

    def test_index_urns(self):
        """Test indexing all XML files in a project directory."""
        # Create multiple XML files
        self._create_test_xml("doc1.xml", ["urn:x-opensiddur:test:doc1"])
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
        
        # Add test data
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1/1", "wlc", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1/2", "wlc", "doc1.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc2/1", "wlc", "doc2.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc3/1", "jps1917", "doc3.xml")
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc4/1", "jps1917", "doc4.xml")

    def test_remove_file(self):
        """Test removing all URNs for a specific file."""
        # Remove doc1.xml from wlc project
        removed_count = self.db.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify doc1.xml URNs are gone
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:test:doc1/1")
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:doc1/1", "jps1917", "doc1.xml")
        
        # Remove from wlc only
        removed_count = self.db.remove_file("doc1.xml", "wlc")
        
        self.assertEqual(removed_count, 2)
        
        # Verify jps1917 version still exists
        results = self.db.get_urn_mappings(urn="urn:x-opensiddur:test:doc1/1", project="jps1917")
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:1", "test_proj", "doc1.xml")
        
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:orphan", "test_proj", "orphan.xml")
        
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:1", "nonexistent", "doc1.xml")
        
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:orphan", "orphaned_proj", "orphan.xml")
        
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
        self.db.add_urn_mapping("urn:x-opensiddur:test:1", "proj1", "doc1.xml")
        
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

    def test_add_reference_with_urn_target(self):
        """Test adding a reference with URN target."""
        elem = self._create_element_with_target(
            target="urn:x-opensiddur:test:doc1",
            element_type="transclude",
            corresp="urn:x-opensiddur:ref:1"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify it was added
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:test:doc1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['target_start'], "urn:x-opensiddur:test:doc1")
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
            target="urn:x-opensiddur:test:doc1/1",
            target_end="urn:x-opensiddur:test:doc1/5",
            element_type="range"
        )
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify range was stored
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:test:doc1/1",))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['target_end'], "urn:x-opensiddur:test:doc1/5")

    def test_add_reference_with_multiple_targets(self):
        """Test adding a reference with space-separated targets."""
        elem = self._create_element_with_target(
            target="urn:x-opensiddur:test:doc1 urn:x-opensiddur:test:doc2",
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
        self.assertEqual(targets, {"urn:x-opensiddur:test:doc1", "urn:x-opensiddur:test:doc2"})

    def test_add_reference_stores_element_path(self):
        """Test that element path is correctly stored."""
        elem = self._create_element_with_target(target="urn:x-opensiddur:test:doc1")
        
        self.db.add_reference("test_project", "test.xml", elem)
        
        # Verify element path was stored
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT element_path FROM element_references WHERE target_start = ?', 
                      ("urn:x-opensiddur:test:doc1",))
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
        elem1 = self._create_element_with_target(target="urn:x-opensiddur:test:doc1")
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
        div.set("corresp", "urn:x-opensiddur:test:doc1")
        
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
        elem = self._create_element_with_target(target="urn:x-opensiddur:test:doc1")
        self.db.add_reference("proj1", "file1.xml", elem)
        
        # Also add a URN mapping
        self.db.add_urn_mapping("urn:x-opensiddur:test:urn1", "proj1", "file1.xml")
        
        # Remove the file
        removed_count = self.db.remove_file("file1.xml", "proj1")
        
        # Should have removed both URN and reference
        self.assertEqual(removed_count, 2)
        
        # Verify references are gone
        refs = self.db.get_references_by_project("proj1")
        self.assertEqual(len(refs), 0)

    def test_remove_project_removes_references(self):
        """Test that removing a project also removes its references."""
        elem = self._create_element_with_target(target="urn:x-opensiddur:test:doc1")
        self.db.add_reference("proj1", "file1.xml", elem)
        self.db.add_urn_mapping("urn:x-opensiddur:test:urn1", "proj1", "file1.xml")
        
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


class TestReferenceDatabaseContextManager(unittest.TestCase):
    """Test Reference Database context manager functionality."""

    def test_context_manager(self):
        """Test using database as context manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'test_urn.db'
            
            with ReferenceDatabase(db_path) as db:
                db.add_urn_mapping("urn:x-opensiddur:test:doc1", "test", "doc1.xml")
                results = db.get_urn_mappings(urn="urn:x-opensiddur:test:doc1")
                self.assertEqual(len(results), 1)
            
            # Connection should be closed after context


if __name__ == '__main__':
    unittest.main()

