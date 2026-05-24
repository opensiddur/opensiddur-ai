from pathlib import Path
from typing import Optional

from opensiddur.importer.util.constants import BASE_PATH, Page


def default_sourcetexts_root() -> Path:
    """Default opensiddur/sourcetexts checkout root (legacy layout: <repo>/sources)."""
    return BASE_PATH / "sources"


def jps1917_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """JPS 1917 raw dumps: <sourcetexts-root>/jps1917."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "jps1917"


def jps1917_text_directory(sourcetexts_root: Path | None = None) -> Path:
    """Directory of per-page .txt wikitext files."""
    return jps1917_data_directory(sourcetexts_root) / "text"


def jps1917_credits_directory(sourcetexts_root: Path | None = None) -> Path:
    """Directory of per-page contributor credit files."""
    return jps1917_data_directory(sourcetexts_root) / "credits"


def get_page(page_number: str | int, sourcetexts_root: Path | None = None) -> Optional[Page]:
    """Return the wikitext of the given Page, or None if it does not exist."""
    page_num = int(page_number)
    page_file_name = f"{page_num:04d}.txt"
    path = jps1917_text_directory(sourcetexts_root) / page_file_name
    try:
        with open(path, "r", encoding="utf-8") as f:
            return Page.model_validate(dict(number=page_num, content=f.read()))
    except FileNotFoundError:
        return None


def get_credits(page_number: str | int, sourcetexts_root: Path | None = None) -> Optional[list[str]]:
    """Return the credits of the given Page, or None if it does not exist."""
    page_num = int(page_number)
    page_file_name = f"{page_num:04d}.txt"
    path = jps1917_credits_directory(sourcetexts_root) / page_file_name
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.read().split("\n") if line.strip()]
    except FileNotFoundError:
        return None
