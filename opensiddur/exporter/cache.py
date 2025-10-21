from pathlib import Path
from typing import Optional
from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY

class XMLCache:
    def __init__(self, base_path: Path = PROJECT_DIRECTORY):
        self.base_path = base_path
        self.cache: dict[tuple[str, str], etree._ElementTree] = {}

    def _path_of_file(self, project: str, file_name: str) -> Path:
        return self.base_path / project / file_name

    def parse_xml(self, project: str, file_name: str) -> Optional[etree._ElementTree]:
        cached = self.cache.get((project, file_name))
        if cached is not None:
            return cached
        path = self._path_of_file(project, file_name)
        if not path.exists():
            raise FileNotFoundError(f"File {path} not found")
        
        parsed = etree.parse(str(path))
        self.cache[(project, file_name)] = parsed
        return parsed
