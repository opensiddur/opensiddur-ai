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
    end_element_path: Optional[str] = None
    end_includes_tail: bool = False


class ResolvedUrnRange(BaseModel):
    start: ResolvedUrn
    end: ResolvedUrn

    @property
    def project(self) -> str:
        return self.start.project


def split_range(ranged_urn: str) -> Optional[tuple[str, str]]:
    """Split a ranged URN into its start and end URNs.

    A range is written with '-' in a path component. The part before the dash closes the
    start URN; what follows names the end. There are two ways to name the end:

    **Relative** — the end replaces that many trailing components of the start, which leaves
    it at the same depth::

        genesis/1/1-2      → genesis/1/1  … genesis/1/2
        genesis/1/1-2/3    → genesis/1/1  … genesis/2/3
        nahum/2/2/b-2/3/a  → nahum/2/2/b  … nahum/2/3/a

    **Absolute** — an end that begins with '/' replaces the whole path below the component
    carrying the namespace and the work, so the two ends need not be at the same depth::

        nahum/2/2/b-/2/5   → nahum/2/2/b  … nahum/2/5
        genesis/1/1-/3     → genesis/1/1  … genesis/3

    Write the absolute form whenever the ends are at different depths: a sub-verse start
    with a whole-verse end has no relative spelling, since a relative end always lands at
    the start's own depth. This is also why a range cannot cross works — the absolute form
    keeps the start's namespace-and-work component, and the relative form never touches it.

    Args:
        ranged_urn: A URN, with or without range notation. Any '@project' suffix must
                    already have been stripped.

    Returns:
        (start_urn, end_urn), or None if `ranged_urn` names no range at all.

    Raises:
        ValueError: if it names a range but not a well-formed one.
    """
    parts = ranged_urn.split('/')

    # Index 0 holds the scheme, namespace and work ("urn:x-opensiddur:text:bible:genesis"),
    # whose dashes ("x-opensiddur") never mark a range. Only the path components below it
    # are candidates, and the last dash-bearing one wins.
    range_start_idx = None
    for i in range(len(parts) - 1, 0, -1):
        if '-' in parts[i]:
            range_start_idx = i
            break

    if range_start_idx is None:
        return None

    start_value, end_spec_start = parts[range_start_idx].split('-', 1)
    if not start_value:
        raise ValueError(f"Range has no start: {ranged_urn!r}")
    start_urn = '/'.join(parts[:range_start_idx] + [start_value])

    remaining_parts = parts[range_start_idx + 1:]
    end_spec = end_spec_start
    if remaining_parts:
        end_spec += '/' + '/'.join(remaining_parts)

    if end_spec.startswith('/'):
        end_components = end_spec[1:].split('/')
        if not all(end_components):
            raise ValueError(f"Absolute range end is empty: {ranged_urn!r}")
        end_parts = [parts[0]] + end_components
    else:
        if not end_spec:
            raise ValueError(f"Range has no end: {ranged_urn!r}")
        end_components = end_spec.split('/')
        # A relative end replaces trailing components of the start, so it can never be
        # deeper than the start is. Before the absolute form existed this case built an end
        # URN with the scheme sliced off it, which then resolved to nothing, silently.
        base = range_start_idx - len(end_components) + 1
        if base < 1:
            raise ValueError(
                f"Relative range end {end_spec!r} is deeper than the start it replaces in "
                f"{ranged_urn!r}; state it absolutely as -/{end_spec}"
            )
        end_parts = parts[:base] + end_components

    return start_urn, '/'.join(end_parts)


def coarsen(urn: str) -> Optional[str]:
    """`urn` with its last path component dropped, or None if it has only one.

    A project need not carry every division another project does: a translation has no
    accents, so it can place no half-verses, and a reference to one has to fall back on the
    verse that contains it or the translation drops out of the page altogether. Reading a
    whole verse where half was asked for is the behaviour that was there before sub-verse
    URNs existed; what is new is that the caller knows it happened and can say so.

    Ranges are coarsened at both ends, and the result is stated absolutely so that ends
    which no longer sit at the same depth still resolve.
    """
    project_specifier = None
    if '@' in urn:
        urn, project_specifier = urn.rsplit('@', 1)

    try:
        split = split_range(urn)
    except ValueError:
        return None

    def drop(one: str) -> Optional[str]:
        head, _, tail = one.rpartition('/')
        return head if head and tail else None

    if split is None:
        coarsened = drop(urn)
    else:
        start, end = (drop(part) for part in split)
        if start is None or end is None:
            return None
        # The absolute form, since the two ends may no longer be at the same depth.
        _work, _, below = end.partition('/')
        coarsened = f"{start}-/{below}" if below else None

    if coarsened is None:
        return None
    return f"{coarsened}@{project_specifier}" if project_specifier else coarsened


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
        
        return [
            ResolvedUrn(
                project=row.project,
                file_name=row.file_name,
                urn=actual_urn,
                element_path=row.element_path,
                end_element_path=row.end_element_path,
                end_includes_tail=row.end_includes_tail
            )
            for row in mappings
        ]
    
    def resolve_range(self, ranged_urn: str) -> list[ResolvedUrnRange | ResolvedUrn]:
        """Resolve a ranged URN to start and end URNs, or a non-ranged URN.
        
        The range notation itself is parsed by `split_range`, which documents the relative
        and absolute forms of a range end.

        If the URN names no range, it is treated as a non-ranged URN and resolve() is
        called instead.

        Args:
            ranged_urn: A URN with range notation (e.g., 'urn:.../1/1-2', 'urn:.../1/1-2/3@project'
                       or 'urn:.../2/2/b-/2/5') or a non-ranged URN (e.g., 'urn:.../genesis/1/1')

        Returns:
            List of ResolvedUrnRange objects for ranged URNs, or list of ResolvedUrn objects
            for non-ranged URNs. May contain multiple entries if the URN exists in multiple
            projects (when no project specifier is provided).
            Returns empty list if start and end don't resolve to any matching project/file
            combinations.

        Raises:
            ValueError: if the URN names a range but not a well-formed one.
        """
        # Handle @project notation
        project_specifier = None
        if '@' in ranged_urn:
            ranged_urn, project_specifier = ranged_urn.rsplit('@', 1)

        split = split_range(ranged_urn)

        if split is None:
            # Not a range. Add back the project specifier if present and resolve it alone.
            urn_to_resolve = ranged_urn
            if project_specifier:
                urn_to_resolve = f"{ranged_urn}@{project_specifier}"
            return self.resolve(urn_to_resolve)

        start_urn, end_urn = split

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
            ResolvedUrn(
                project=mapping.project,
                file_name=mapping.file_name,
                urn=mapping.urn,
                element_path=mapping.element_path,
                end_element_path=mapping.end_element_path,
                end_includes_tail=mapping.end_includes_tail
            )
            for mapping in mappings
        ]
    
    
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
            return urn.project
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


