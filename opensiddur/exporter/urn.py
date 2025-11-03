""" Resolver for urn:x-opensiddur: URIs.
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from opensiddur.exporter.refdb import Reference, ReferenceDatabase
from opensiddur.common.constants import PROJECT_DIRECTORY

class ResolvedUrn(BaseModel):
    project: str
    file_name: str
    urn: str
    element_path: str


class ResolvedUrnRange(BaseModel):
    start: ResolvedUrn
    end: ResolvedUrn


class UrnResolver:
    """Resolves URNs to their corresponding project and file paths."""
    
    def __init__(self, reference_database: Optional[ReferenceDatabase] = None):
        """Initialize the URN resolver with a SQLite database.
        
        Args:
            database_path: Path to the SQLite database file
        """
        self.database = reference_database or ReferenceDatabase()
        
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
        # Handle URNs with '@' sign: 'urn@project'
        if '@' in urn:
            actual_urn, project = urn.rsplit('@', 1)
            mappings = self.database.get_urn_mappings(actual_urn, project)
        else:
            actual_urn = urn
            mappings = self.database.get_urn_mappings(urn)
        
        return [ResolvedUrn(project=row.project, file_name=row.file_name, urn=actual_urn, element_path=row.element_path) 
                for row in mappings]
    
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
    
    def get_urns_by_project(self, project: str) -> list[ResolvedUrn]:
        """Get all URN mappings for a specific project.
        
        Args:
            project: The project name to filter by
            
        Returns:
            List of dictionaries containing urn, project, and file_name
        """
        mappings = self.database.get_urn_mappings(project=project)
        return [
            ResolvedUrn(project=mapping.project, file_name=mapping.file_name, urn=mapping.urn, element_path=mapping.element_path) 
            for mapping in mappings]
    
    
    @classmethod
    def prioritize_range(cls, 
        resolved_urns: list[ResolvedUrn | ResolvedUrnRange | Reference],
        project_priority: list[str],
        return_all: bool = False) -> Optional[ResolvedUrn | ResolvedUrnRange | Reference | list[ResolvedUrn | ResolvedUrnRange | Reference]]:
        """Prioritize a list of resolved URNs or URN ranges based on a project priority list.
        
        Args:
            resolved_urns: List of ResolvedUrn or ResolvedUrnRange objects
            project_priority: List of project names in priority order
            return_all: If True, return all resolved URNs or URN ranges, otherwise return the most prioritized one
        Returns:
            The most prioritized ResolvedUrn or ResolvedUrnRange object.
            If none of the URNs are prioritized, return None.
        """
        # map a numeric priority to a project name
        priorities = dict(zip(project_priority, range(len(project_priority))))
        def _project_name(urn) -> str:
            return urn.project if hasattr(urn, 'project') else urn.start.project
        sorted_urns = sorted([
            r for r in resolved_urns 
            if priorities.get(_project_name(r)) is not None
            ], 
            key=lambda x: priorities.get(_project_name(x)))
        if len(sorted_urns) > 0:
            return sorted_urns[0] if not return_all else sorted_urns
        return None

    @classmethod
    def get_path_from_urn(cls, resolved_urn: ResolvedUrn, project_directory: Path = PROJECT_DIRECTORY) -> Path:
        """Get the path from a URN.
    
        Args:
            resolved_urn: The ResolvedUrn
            
        Returns:
            The path
        """
        return project_directory / resolved_urn.project / resolved_urn.file_name


