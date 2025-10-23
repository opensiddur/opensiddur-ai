""" Reference Database """

from pathlib import Path
import re
import sqlite3
from typing import Optional

from lxml import etree
from lxml.etree import ElementBase
from pydantic import BaseModel
from opensiddur.common.constants import PROJECT_DIRECTORY, INDEX_DB_DIRECTORY

INDEX_DB_FILE = INDEX_DB_DIRECTORY / "reference.db"

class UrnMapping(BaseModel):
    project: str
    file_name: str
    urn: str

class Reference(BaseModel):
    element_path: str
    element_tag: str
    element_type: Optional[str]
    target_start: str
    target_end: Optional[str]
    target_is_id: bool
    corresponding_urn: Optional[str]
    project: str
    file_name: str

class ReferenceDatabase:
    """Database to store references to URNs and IDs."""

    def __init__(self, database_path: str | Path = INDEX_DB_FILE):
        """Initialize the SQLite database.
        
        Args:
            database_path: Path to the SQLite database file
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.database_path))
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urn_mappings (
                urn TEXT NOT NULL,
                project TEXT NOT NULL,
                file_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (urn, project)
            )
        ''')
        # Create index on urn alone for faster lookups without project
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_urn 
            ON urn_mappings(urn)
        ''')
        # Create index on project for faster project-based queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_project 
            ON urn_mappings(project)
        ''')

        # Create table for element_references
        # This table indicates that an element of the given tag and type 
        # at the given path in the project/file
        # references a target (via @target attribute) or a target range (@targetEnd)
        # 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS element_references (
                element_path TEXT NOT NULL,
                element_tag TEXT NOT NULL,
                element_type TEXT,
                target_start TEXT NOT NULL,
                target_end TEXT,
                target_is_id BOOLEAN NOT NULL,
                corresponding_urn TEXT,
                project TEXT NOT NULL,
                file_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ref_target_start 
            ON element_references(target_start)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ref_target_end 
            ON element_references(target_end)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ref_project 
            ON element_references(project)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ref_corresponding_urn 
            ON element_references(corresponding_urn)
        ''')
        self.conn.commit()

    def get_urn_mappings(self, urn: Optional[str] = None, project: Optional[str] = None) -> list[UrnMapping]:
        """Get all URN mappings for a specific URN.
        
        Args:
            urn: The URN identifier
            project: The project/directory name

        Returns:
            List of UrnMapping objects
        """
        cursor = self.conn.cursor()
        if urn and project:
            cursor.execute('''
                SELECT project, file_name, urn FROM urn_mappings WHERE urn = ? AND project = ?''', (urn, project))
        elif urn:
            cursor.execute('''
                SELECT project, file_name, urn FROM urn_mappings WHERE urn = ?''', (urn,))
        elif project:
            cursor.execute('''
                SELECT project, file_name, urn FROM urn_mappings WHERE project = ?''', (project,))
        else:
            cursor.execute('''
                SELECT project, file_name, urn FROM urn_mappings''')
        return [
            UrnMapping(project=row['project'], file_name=row['file_name'], urn=row['urn']) 
            for row in cursor.fetchall()]
    
    def get_references_to(self, urn: Optional[str] = None, id: Optional[str] = None, project: Optional[str] = None, file_name: Optional[str] = None) -> list[Reference]:
        """Get a list of all references to a specific URN or ID/file combination.
        
        Args:
            urn: The URN identifier
            id: The ID identifier (with or without # prefix)
            project: The project name (for id)
            file_name: The file name (for id)
        Returns:
            List of Reference objects
        """
        cursor = self.conn.cursor()
        if urn:
            cursor.execute('''
                SELECT * FROM element_references WHERE target_start = ?''', (urn,))
            by_urn = cursor.fetchall()
        else:
            by_urn = []
        if id and project and file_name:
            # Ensure ID has # prefix for query
            id_with_hash = id if id.startswith('#') else f"#{id}"
            cursor.execute('''
                SELECT * FROM element_references WHERE target_start = ? AND target_is_id = true AND project = ? AND file_name = ?''', (id_with_hash, project, file_name))
            by_id = cursor.fetchall()
        else:
            by_id = []

        by_both = []
        paths = set()
        for row in by_urn + by_id:
            if row['element_path'] in paths:
                continue
            paths.add(row['element_path'])
            by_both.append(row)

        return [Reference(element_path=row['element_path'], element_tag=row['element_tag'], element_type=row['element_type'], target_start=row['target_start'], target_end=row['target_end'], target_is_id=row['target_is_id'], corresponding_urn=row['corresponding_urn'], project=row['project'], file_name=row['file_name']) for row in by_both]

    def add_urn_mapping(self, urn: str, project: str, file_name: str):
        """Add or update a URN mapping.
        
        Args:
            urn: The URN identifier
            project: The project/directory name
            file_name: The file name containing the element
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO urn_mappings (urn, project, file_name)
            VALUES (?, ?, ?)
            ON CONFLICT(urn, project) DO UPDATE SET
                file_name = excluded.file_name,
                updated_at = CURRENT_TIMESTAMP
        ''', (urn, project, file_name))
        self.conn.commit()

    def add_reference(self, project: str, file_name: str, element: ElementBase):
        """ Add a reference to the database.
        
        Args:
            element: The element that has the reference
        """
        cursor = self.conn.cursor()

        target = element.get('target')
        if not target:
            return
        element_path = element.getroottree().getpath(element)
        corresponding_urn = element.get('corresp')
        tag = element.tag
        element_type = element.get('type')
        
        for target_start in re.split(r'\s+', target):
            target_end = element.get('targetEnd', target_start)
            target_is_id = target_start.startswith('#')
            cursor.execute('''
                INSERT INTO element_references (element_path, element_tag, element_type, target_start, target_end, target_is_id, corresponding_urn, project, file_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (element_path, tag, element_type, target_start, target_end, target_is_id, corresponding_urn, project, file_name))
        self.conn.commit()
    
    def get_urns_by_project(self, project: str) -> list[UrnMapping]:
        """Get all URN mappings for a specific project.
        
        Args:
            project: The project name to filter by
            
        Returns:
            List of dictionaries containing urn, project, and file_name
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT urn, project, file_name FROM urn_mappings WHERE project = ?',
            (project,)
        )
        return [UrnMapping(project=row['project'], file_name=row['file_name'], urn=row['urn']) for row in cursor.fetchall()]
    
    def get_files_by_project(self, project: str) -> list[str]:
        """Get a list of all distinct file names in a project.
        
        Args:
            project: The project name to filter by
            
        Returns:
            List of file names (sorted alphabetically)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT DISTINCT file_name FROM urn_mappings WHERE project = ? ORDER BY file_name',
            (project,)
        )
        return [row['file_name'] for row in cursor.fetchall()]
    

    def get_references_by_project(self, project: str) -> list[Reference]:
        """Get a list of all references for a specific project.
        
        Args:
            project: The project name to filter by
            
        Returns:
            List of Reference objects
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM element_references WHERE project = ? ORDER BY element_path',
            (project,)
        )
        return [Reference(element_path=row['element_path'], element_tag=row['element_tag'], element_type=row['element_type'], target_start=row['target_start'], target_end=row['target_end'], target_is_id=row['target_is_id'], corresponding_urn=row['corresponding_urn'], project=row['project'], file_name=row['file_name']) for row in cursor.fetchall()]
    
    def list_projects(self) -> list[str]:
        """Get a list of all distinct projects in the database.
        
        Returns:
            List of project names (sorted alphabetically)
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT project FROM urn_mappings ORDER BY project')
        return [row['project'] for row in cursor.fetchall()]
    
    def index_file(self, file_path: Path | str, project: str, file_name: str) -> int:
        """Index all URNs/references from a single XML file.
        
        Args:
            file_path: Full path to the XML file to index
            project: The project name this file belongs to
            file_name: The file name (without path) for the mapping
            
        Returns:
            Number of URNs/references indexed from this file
        """
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
            
            # Find all elements with corresp attribute
            # Handle multiple namespaces (tei and j)
            namespaces = {
                'tei': 'http://www.tei-c.org/ns/1.0',
                'j': 'http://jewishliturgy.org/ns/jlptei/2'
            }
            
            # XPath to find all elements with corresp attribute
            elements_with_corresp = root.xpath('//*[@corresp]', namespaces=namespaces)
            
            count = 0
            for element in elements_with_corresp:
                corresp = element.get('corresp')
                if corresp and corresp.startswith('urn:x-opensiddur:'):
                    self.add_urn_mapping(corresp, project, file_name)
                    count += 1
            
            elements_with_reference = root.xpath('//*[@target]', namespaces=namespaces)

            for element in elements_with_reference:
                self.add_reference(project, file_name, element)
                count += 1

            return count
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return 0
    
    def index_project(self, project: str, project_directory: Path = PROJECT_DIRECTORY) -> int:
        """Index all URNs/references from XML files in a project directory.
        
        Args:
            project: The project name (e.g., 'wlc', 'jps1917')
            project_directory: Base directory containing project subdirectories
                              (defaults to PROJECT_DIRECTORY constant)
            
        Returns:
            Total number of URNs/references indexed
        """
        project_path = Path(project_directory) / project
        
        if not project_path.exists():
            raise ValueError(f"Project directory does not exist: {project_path}")
        
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")
        
        total_urns = 0
        xml_files = list(project_path.glob('*.xml'))
        
        for xml_file in xml_files:
            file_name = xml_file.name
            count = self.index_file(xml_file, project, file_name)
            total_urns += count
            print(f"Indexed {count} URNs/references from {file_name}")
        
        return total_urns
    
    def remove_file(self, file_name: str, project: str) -> int:
        """Remove all URN mappings for a specific file in a project.
        
        Args:
            file_name: The file name to remove
            project: The project name
            
        Returns:
            Number of URNs removed
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM urn_mappings WHERE file_name = ? AND project = ?',
            (file_name, project)
        )
        deleted_count = cursor.rowcount
        
        cursor.execute(
            'DELETE FROM element_references WHERE file_name = ? AND project = ?',
            (file_name, project)
        )
        deleted_count += cursor.rowcount
        self.conn.commit()
        return deleted_count
    
    def remove_project(self, project: str) -> int:
        """Remove all URN/references mappings for an entire project.
        
        Args:
            project: The project name to remove
            
        Returns:
            Number of URNs/references removed
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM urn_mappings WHERE project = ?',
            (project,)
        )
        deleted_count = cursor.rowcount

        cursor.execute(
            'DELETE FROM element_references WHERE project = ?',
            (project,)
        )
        deleted_count += cursor.rowcount

        self.conn.commit()
        return deleted_count
    
    def _get_file_last_updated(self, file_name: str, project: str) -> float | None:
        """Get the last updated timestamp for a file in the database.
        
        Args:
            file_name: The file name
            project: The project name
            
        Returns:
            Timestamp (as float seconds since epoch, in UTC) or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            '''SELECT MAX(updated_at) as last_updated FROM urn_mappings WHERE file_name = ? AND project = ?
            UNION ALL
            SELECT MAX(updated_at) as last_updated FROM element_references WHERE file_name = ? AND project = ?''',
            (file_name, project, file_name, project)
        )
        rows = cursor.fetchall()
        dts = []
        for row in rows:
            if row and row['last_updated']:
                # Parse SQLite timestamp to seconds since epoch
                # SQLite's CURRENT_TIMESTAMP returns UTC time
                from datetime import datetime, timezone
                timestamp_str = row['last_updated']
                # Handle SQLite's default timestamp format
                # Try to parse with space separator first, then 'T' separator
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                except ValueError:
                    dt = datetime.fromisoformat(timestamp_str)
                # Assume UTC if no timezone info
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dts.append(dt.timestamp())
        if not dts:
            return None
        return max(dts)
            
    
    def sync_file(self, file_name: str, project: str, project_directory: Path = PROJECT_DIRECTORY) -> dict:
        """Synchronize a file with the database.
        
        Checks if the file exists and if it's been modified since last indexing.
        If modified, removes old entries and re-indexes. If doesn't exist, removes from database.
        
        Args:
            file_name: The file name (e.g., 'genesis.xml')
            project: The project name
            project_directory: Base directory containing project subdirectories
            
        Returns:
            Dictionary with 'action' (added/updated/removed/skipped) and 'references' count
        """
        project_path = Path(project_directory) / project
        file_path = project_path / file_name
        
        # Check if file exists on disk
        if not file_path.exists():
            # File doesn't exist, remove from database
            removed = self.remove_file(file_name, project)
            return {'action': 'removed', 'references': removed}
        
        # Get file modification time
        file_mtime = file_path.stat().st_mtime
        
        # Get last updated time from database
        db_last_updated = self._get_file_last_updated(file_name, project)
        
        # If not in database or file is newer, (re)index it
        if db_last_updated is None:
            # File not in database, add it
            count = self.index_file(file_path, project, file_name)
            return {'action': 'added', 'references': count}
        elif file_mtime > db_last_updated:
            # File modified since last index, re-index
            self.remove_file(file_name, project)
            count = self.index_file(file_path, project, file_name)
            return {'action': 'updated', 'references': count}
        else:
            # File unchanged
            return {'action': 'skipped', 'references': 0}
    
    def sync_project(self, project: str, project_directory: Path = PROJECT_DIRECTORY) -> dict:
        """Synchronize a project with the database.
        
        Checks if project directory exists, removes orphaned files from database,
        and syncs all files in the directory.
        
        Args:
            project: The project name
            project_directory: Base directory containing project subdirectories
            
        Returns:
            Dictionary with counts: added, updated, removed, skipped
        """
        project_path = Path(project_directory) / project
        
        # Check if project directory exists
        if not project_path.exists() or not project_path.is_dir():
            # Project doesn't exist, remove from database
            removed = self.remove_project(project)
            return {'action': 'project_removed', 'references': removed, 
                   'added': 0, 'updated': 0, 'removed': removed, 'skipped': 0}
        
        # Get list of XML files on disk
        disk_files = {f.name for f in project_path.glob('*.xml')}
        
        # Get list of files in database
        db_files = set(self.get_files_by_project(project))
        
        # Remove files that are in database but not on disk
        orphaned_files = db_files - disk_files
        removed_count = 0
        for file_name in orphaned_files:
            removed_count += self.remove_file(file_name, project)
        
        # Sync all files that exist on disk
        added_count = 0
        updated_count = 0
        skipped_count = 0
        
        for file_name in disk_files:
            result = self.sync_file(file_name, project, project_directory)
            if result['action'] == 'added':
                added_count += result['references']
            elif result['action'] == 'updated':
                updated_count += result['references']
            elif result['action'] == 'skipped':
                skipped_count += 1
        
        return {
            'action': 'project_synced',
            'added': added_count,
            'updated': updated_count,
            'removed': removed_count,
            'skipped': skipped_count
        }
    
    def sync_projects(self, project_directory: Path = PROJECT_DIRECTORY) -> dict:
        """Synchronize all projects with the database.
        
        Checks all project directories, removes orphaned projects from database,
        and syncs all existing projects.
        
        Args:
            project_directory: Base directory containing project subdirectories
            
        Returns:
            Dictionary with overall counts and per-project results
        """
        project_dir_path = Path(project_directory)
        
        if not project_dir_path.exists():
            raise ValueError(f"Project directory does not exist: {project_dir_path}")
        
        # Get list of project directories on disk (directories only)
        disk_projects = {p.name for p in project_dir_path.iterdir() if p.is_dir()}
        
        # Get list of projects in database
        db_projects = set(self.list_projects())
        
        # Remove projects that are in database but not on disk
        orphaned_projects = db_projects - disk_projects
        total_removed = 0
        for project in orphaned_projects:
            total_removed += self.remove_project(project)
        
        # Sync all projects that exist on disk
        total_added = 0
        total_updated = 0
        total_skipped = 0
        project_results = {}
        
        for project in disk_projects:
            result = self.sync_project(project, project_directory)
            project_results[project] = result
            total_added += result.get('added', 0)
            total_updated += result.get('updated', 0)
            total_removed += result.get('removed', 0)
            total_skipped += result.get('skipped', 0)
        
        return {
            'action': 'projects_synced',
            'total_added': total_added,
            'total_updated': total_updated,
            'total_removed': total_removed,
            'total_skipped': total_skipped,
            'projects': project_results,
            'orphaned_projects_removed': len(orphaned_projects)
        }
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()


def main():
    """Synchronize the reference database with the project directory.
    
    Opens the default database and syncs all projects, printing a summary
    of the changes made.
    """
    print(f"Synchronizing reference database: {INDEX_DB_FILE}")
    print(f"Project directory: {PROJECT_DIRECTORY}\n")
    
    with ReferenceDatabase(INDEX_DB_FILE) as refdb:
        try:
            result = refdb.sync_projects(PROJECT_DIRECTORY)
            
            # Print summary
            print("=" * 70)
            print("Synchronization Complete")
            print("=" * 70)
            print(f"Total references added:   {result['total_added']}")
            print(f"Total references updated: {result['total_updated']}")
            print(f"Total references removed: {result['total_removed']}")
            print(f"Total references skipped: {result['total_skipped']}")
            print(f"Orphaned projects removed: {result['orphaned_projects_removed']}")
            
            # Print per-project details
            if result['projects']:
                print("\nPer-Project Summary:")
                print("-" * 70)
                for project, proj_result in sorted(result['projects'].items()):
                    print(f"  {project}:")
                    print(f"    Added: {proj_result.get('added', 0)}, "
                          f"Updated: {proj_result.get('updated', 0)}, "
                          f"Removed: {proj_result.get('removed', 0)}, "
                          f"Skipped: {proj_result.get('skipped', 0)}")
            
            # Print final database state
            print("\nDatabase State:")
            print("-" * 70)
            projects = refdb.list_projects()
            if projects:
                for project in projects:
                    files = refdb.get_files_by_project(project)
                    urns = refdb.get_urns_by_project(project)
                    references = refdb.get_references_by_project(project)
                    print(f"  {project}: {len(files)} files, {len(urns)} URNs, {len(references)} references")
            else:
                print("  (empty)")
            
            print()
            
        except Exception as e:
            print(f"Error during synchronization: {e}")
            raise


if __name__ == '__main__':
    main()
