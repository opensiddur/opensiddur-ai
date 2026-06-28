"""Page-break alignment data for 1822 Heidenheim facsimile."""

from __future__ import annotations

import json
from pathlib import Path

from opensiddur.importer.util.pages import heidenheim_haggadah_data_directory


def page_breaks_path(sourcetexts_root: Path | None = None) -> Path:
    return heidenheim_haggadah_data_directory(sourcetexts_root) / "page_breaks.json"


def load_page_breaks(sourcetexts_root: Path | None = None) -> dict[str, int]:
    """Map section slug -> 1822 printed page number (HebrewBooks #4909)."""
    path = page_breaks_path(sourcetexts_root)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(k): int(v)
        for k, v in data.items()
        if not str(k).startswith("_") and isinstance(v, int)
    }


def write_empty_page_breaks_template(sourcetexts_root: Path | None = None) -> Path:
    path = page_breaks_path(sourcetexts_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "_comment": (
                        "Map section slug to physical page number in HebrewBooks #4909. "
                        "Used to emit tei:pb milestones during conversion."
                    )
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return path
