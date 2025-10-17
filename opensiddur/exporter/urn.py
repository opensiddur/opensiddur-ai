""" Resolver for urn:x-opensiddur: URIs.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from lxml import etree
from pydantic import BaseModel

from opensiddur.common.constants import PROJECT_DIRECTORY, INDEX_DB_DIRECTORY

INDEX_DB_FILE = INDEX_DB_DIRECTORY / "urn.db"

class ResolvedUrn(BaseModel):
    project: str
    file_name: str
    urn: str


class ResolvedUrnRange(BaseModel):
    start: ResolvedUrn
    end: ResolvedUrn


class UrnResolver:
    """Resolves URNs to their corresponding project and file paths."""
    
    def __init__(self, database_path: str | Path = INDEX_DB_FILE):
        """Initialize the URN resolver with a SQLite database.
        
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
        self.conn.commit()
    
    def resolve(self, urn: str) -> list[ResolvedUrn]:
        """Resolve a URN to its project and file name.
        
        Args:
            urn: The URN to resolve (from corresp attribute).
                 Can include project specifier: 'urn@project'
            
        Returns:
            List of ResolvedUrn objects. Empty list if not found.
            May contain multiple entries if URN exists in multiple projects
            (when no project specifier is provided).
        """
        cursor = self.conn.cursor()
        
        # Handle URNs with '@' sign: 'urn@project'
        if '@' in urn:
            actual_urn, project = urn.rsplit('@', 1)
            cursor.execute(
                'SELECT project, file_name FROM urn_mappings WHERE urn = ? AND project = ?',
                (actual_urn, project)
            )
        else:
            actual_urn = urn
            cursor.execute(
                'SELECT project, file_name FROM urn_mappings WHERE urn = ?',
                (urn,)
            )
        
        rows = cursor.fetchall()
        return [ResolvedUrn(project=row['project'], file_name=row['file_name'], urn=actual_urn) 
                for row in rows]
    
    def resolve_range(self, ranged_urn: str) -> list[ResolvedUrnRange | ResolvedUrn]:
        """Resolve a ranged URN to start and end URNs, or a non-ranged URN.
        
        A range URN uses '-' to indicate a range in the final components:
        - 'urn:.../genesis/1/1-2' resolves to start='...genesis/1/1', end='...genesis/1/2'
        - 'urn:.../genesis/1/1-2/3' resolves to start='...genesis/1/1', end='...genesis/2/3'
        
        The end specification replaces the last N components of the start URN, where N is
        the number of components (slash-delimited) in the end specification.
        
        If the URN does not contain a dash in the last path component, it is treated as a
        non-ranged URN and resolve() is called instead.
        
        Args:
            ranged_urn: A URN with range notation (e.g., 'urn:.../1/1-2' or 'urn:.../1/1-2/3@project')
                       or a non-ranged URN (e.g., 'urn:.../genesis/1/1')
        
        Returns:
            List of ResolvedUrnRange objects for ranged URNs, or list of ResolvedUrn objects
            for non-ranged URNs. May contain multiple entries if the URN exists in multiple
            projects (when no project specifier is provided).
            Returns empty list if the URN cannot be parsed as a range, or if start and end 
            don't resolve to any matching project/file combinations.
        """
        # Handle @project notation
        project_specifier = None
        if '@' in ranged_urn:
            ranged_urn, project_specifier = ranged_urn.rsplit('@', 1)
        
        # Find the '-' that indicates the range
        # It should be in the path portion (after the scheme and initial parts)
        # Split to find where the range starts
        # We look for '-' that's in a path component (contains '/')
        
        # Find the first '-' that appears after a '/' or at the start of a path component
        parts = ranged_urn.split('/')
        
        # Only check path components (not the scheme part) for a dash
        # For example, "urn:x-opensiddur:test:doc" splits to ["urn:x-opensiddur:test:doc"]
        # and we should NOT treat the dash in "x-opensiddur" as a range indicator
        # But "urn:x-opensiddur:test:doc/1-2" splits to ["urn:x-opensiddur:test:doc", "1-2"]
        # and we SHOULD treat the dash in "1-2" as a range indicator
        
        # For a URN to be ranged, we need at least 2 parts when split by '/' 
        # (meaning there's at least one '/' in the URN, so we have actual path components)
        
        if len(parts) < 2:
            # No '/' in the URN, so no range possible (dash would be in scheme part)
            # Call resolve() instead and return the results
            urn_to_resolve = ranged_urn
            if project_specifier:
                urn_to_resolve = f"{ranged_urn}@{project_specifier}"
            return self.resolve(urn_to_resolve)
        
        # Search from the end backwards through path components (not the first component which is the scheme)
        # to find the first component containing a dash
        # Start from parts[1:] to skip the scheme component
        range_start_idx = None
        for i in range(len(parts) - 1, 0, -1):  # Search from the end, but skip index 0 (scheme)
            if '-' in parts[i]:
                range_start_idx = i
                break
        
        # If no dash found in any path component, this is not a ranged URN
        # Call resolve() instead and return the results
        if range_start_idx is None:
            # Add back the project specifier if present
            urn_to_resolve = ranged_urn
            if project_specifier:
                urn_to_resolve = f"{ranged_urn}@{project_specifier}"
            return self.resolve(urn_to_resolve)
        
        # Split at the '-' within that component
        range_part = parts[range_start_idx]
        if '-' not in range_part:
            return []
        
        start_value, end_spec_start = range_part.split('-', 1)
        
        # Build the start URN
        start_parts = parts[:range_start_idx] + [start_value]
        start_urn = '/'.join(start_parts)
        
        # Build the end URN
        # The end spec includes everything after '-', plus remaining path components
        # For "genesis/1/1-2/3", after finding "1-2", we need end_spec = "2/3"
        remaining_parts = parts[range_start_idx + 1:]
        if remaining_parts:
            end_spec = end_spec_start + '/' + '/'.join(remaining_parts)
        else:
            end_spec = end_spec_start
        
        # Split end_spec to get individual components
        end_spec_parts = end_spec.split('/')
        num_components = len(end_spec_parts)
        
        # Replace the last num_components components with end_spec_parts
        end_parts = parts[:range_start_idx - num_components + 1] + end_spec_parts
        end_urn = '/'.join(end_parts)
        
        # Add back the project specifier if present
        if project_specifier:
            start_urn = f"{start_urn}@{project_specifier}"
            end_urn = f"{end_urn}@{project_specifier}"
        
        # Resolve both URNs
        start_resolved_list = self.resolve(start_urn)
        end_resolved_list = self.resolve(end_urn)
        
        # Check if both resolved
        if not start_resolved_list or not end_resolved_list:
            return []
        
        # Find all matching project/file combinations
        # Create a dict to map (project, file_name) -> end_resolved
        end_dict = {(end_resolved.project, end_resolved.file_name): end_resolved 
                    for end_resolved in end_resolved_list}
        ranges = [ResolvedUrnRange(start=start_resolved, end=end_dict.get((start_resolved.project, start_resolved.file_name)))
                  for start_resolved in start_resolved_list
                  if (start_resolved.project, start_resolved.file_name) in end_dict]
        
        return ranges
    
    def add_mapping(self, urn: str, project: str, file_name: str):
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
    
    def get_urns_by_project(self, project: str) -> list[ResolvedUrn]:
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
        return [ResolvedUrn(project=row['project'], file_name=row['file_name'], urn=row['urn']) for row in cursor.fetchall()]
    
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
    
    def list_projects(self) -> list[str]:
        """Get a list of all distinct projects in the database.
        
        Returns:
            List of project names (sorted alphabetically)
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT project FROM urn_mappings ORDER BY project')
        return [row['project'] for row in cursor.fetchall()]
    
    def index_file(self, file_path: Path | str, project: str, file_name: str) -> int:
        """Index all URNs from a single XML file.
        
        Args:
            file_path: Full path to the XML file to index
            project: The project name this file belongs to
            file_name: The file name (without path) for the mapping
            
        Returns:
            Number of URNs indexed from this file
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
                    self.add_mapping(corresp, project, file_name)
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return 0
    
    def index_urns(self, project: str, project_directory: Path = PROJECT_DIRECTORY) -> int:
        """Index all URNs from XML files in a project directory.
        
        Args:
            project: The project name (e.g., 'wlc', 'jps1917')
            project_directory: Base directory containing project subdirectories
                              (defaults to PROJECT_DIRECTORY constant)
            
        Returns:
            Total number of URNs indexed
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
            print(f"Indexed {count} URNs from {file_name}")
        
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
        self.conn.commit()
        return deleted_count
    
    def remove_project(self, project: str) -> int:
        """Remove all URN mappings for an entire project.
        
        Args:
            project: The project name to remove
            
        Returns:
            Number of URNs removed
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM urn_mappings WHERE project = ?',
            (project,)
        )
        deleted_count = cursor.rowcount
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
            'SELECT MAX(updated_at) as last_updated FROM urn_mappings WHERE file_name = ? AND project = ?',
            (file_name, project)
        )
        row = cursor.fetchone()
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
            return dt.timestamp()
        return None
    
    def sync_file(self, file_name: str, project: str, project_directory: Path = PROJECT_DIRECTORY) -> dict:
        """Synchronize a file with the database.
        
        Checks if the file exists and if it's been modified since last indexing.
        If modified, removes old entries and re-indexes. If doesn't exist, removes from database.
        
        Args:
            file_name: The file name (e.g., 'genesis.xml')
            project: The project name
            project_directory: Base directory containing project subdirectories
            
        Returns:
            Dictionary with 'action' (added/updated/removed/skipped) and 'urns' count
        """
        project_path = Path(project_directory) / project
        file_path = project_path / file_name
        
        # Check if file exists on disk
        if not file_path.exists():
            # File doesn't exist, remove from database
            removed = self.remove_file(file_name, project)
            return {'action': 'removed', 'urns': removed}
        
        # Get file modification time
        file_mtime = file_path.stat().st_mtime
        
        # Get last updated time from database
        db_last_updated = self._get_file_last_updated(file_name, project)
        
        # If not in database or file is newer, (re)index it
        if db_last_updated is None:
            # File not in database, add it
            count = self.index_file(file_path, project, file_name)
            return {'action': 'added', 'urns': count}
        elif file_mtime > db_last_updated:
            # File modified since last index, re-index
            self.remove_file(file_name, project)
            count = self.index_file(file_path, project, file_name)
            return {'action': 'updated', 'urns': count}
        else:
            # File unchanged
            return {'action': 'skipped', 'urns': 0}
    
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
            return {'action': 'project_removed', 'urns': removed, 
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
                added_count += result['urns']
            elif result['action'] == 'updated':
                updated_count += result['urns']
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
    
    @classmethod
    def prioritize_range(cls, 
        resolved_urns: list[ResolvedUrn | ResolvedUrnRange],
        project_priority: list[str]) -> Optional[ResolvedUrn | ResolvedUrnRange]:
        """Prioritize a list of resolved URNs or URN ranges based on a project priority list.
        
        Args:
            resolved_urns: List of ResolvedUrn or ResolvedUrnRange objects
            project_priority: List of project names in priority order
            
        Returns:
            The most prioritized ResolvedUrn or ResolvedUrnRange object.
            If none of the URNs are prioritized, return None.
        """
        # map a numeric priority to a project name
        priorities = dict(zip(project_priority, range(len(project_priority))))
        def _project_name(urn: ResolvedUrn | ResolvedUrnRange) -> str:
            return urn.project if isinstance(urn, ResolvedUrn) else urn.start.project
        sorted_urns = sorted([
            r for r in resolved_urns 
            if priorities.get(_project_name(r)) is not None
            ], 
            key=lambda x: priorities.get(_project_name(x)))
        if len(sorted_urns) > 0:
            return sorted_urns[0]
        return None

    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()


def main():
    """Synchronize the URN database with the project directory.
    
    Opens the default database and syncs all projects, printing a summary
    of the changes made.
    """
    print(f"Synchronizing URN database: {INDEX_DB_FILE}")
    print(f"Project directory: {PROJECT_DIRECTORY}\n")
    
    with UrnResolver(INDEX_DB_FILE) as resolver:
        try:
            result = resolver.sync_projects(PROJECT_DIRECTORY)
            
            # Print summary
            print("=" * 70)
            print("Synchronization Complete")
            print("=" * 70)
            print(f"Total URNs added:   {result['total_added']}")
            print(f"Total URNs updated: {result['total_updated']}")
            print(f"Total URNs removed: {result['total_removed']}")
            print(f"Total files skipped: {result['total_skipped']}")
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
            projects = resolver.list_projects()
            if projects:
                for project in projects:
                    files = resolver.get_files_by_project(project)
                    urns = resolver.get_urns_by_project(project)
                    print(f"  {project}: {len(files)} files, {len(urns)} URNs")
            else:
                print("  (empty)")
            
            print()
            
        except Exception as e:
            print(f"Error during synchronization: {e}")
            raise


if __name__ == '__main__':
    main()
