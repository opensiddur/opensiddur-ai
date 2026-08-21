from pathlib import Path
from typing import Optional

from opensiddur.common.constants import SOURCETEXTS_ROOT
from opensiddur.importer.util.constants import Page


def default_sourcetexts_root() -> Path:
    """Default opensiddur/sourcetexts checkout root (the sourcetexts submodule)."""
    return SOURCETEXTS_ROOT


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


def birnbaum_siddur_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """Birnbaum ha-Siddur ha-Shalem raw dumps: <sourcetexts-root>/birnbaum_siddur."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "birnbaum_siddur"


def birnbaum_siddur_text_directory(sourcetexts_root: Path | None = None) -> Path:
    """Directory of per-page .txt wikitext files."""
    return birnbaum_siddur_data_directory(sourcetexts_root) / "text"


def birnbaum_siddur_credits_directory(sourcetexts_root: Path | None = None) -> Path:
    """Directory of per-page contributor credit files."""
    return birnbaum_siddur_data_directory(sourcetexts_root) / "credits"


def hebcal_leyning_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """hebcal leyning raw data: <sourcetexts-root>/hebcal_leyning."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "hebcal_leyning"


def miqra_al_pi_hamasorah_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """Miqra al pi ha-Masorah raw dumps: <sourcetexts-root>/miqra_al_pi_hamasorah."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "miqra_al_pi_hamasorah"


def miqra_al_pi_hamasorah_sheets_directory(sourcetexts_root: Path | None = None) -> Path:
    """Per-tab TSV files from the Google Sheet export."""
    return miqra_al_pi_hamasorah_data_directory(sourcetexts_root) / "sheets"


def feinstein_haggadah_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """Open Siddur Feinstein haggadah compilation dumps: <sourcetexts-root>/feinstein_haggadah_2009."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "feinstein_haggadah_2009"


def heidenheim_haggadah_data_directory(sourcetexts_root: Path | None = None) -> Path:
    """1822 Heidenheim reference facsimile: <sourcetexts-root>/heidenheim_haggadah_1822."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else default_sourcetexts_root()
    )
    return root / "heidenheim_haggadah_1822"


def heidenheim_pdf_path(sourcetexts_root: Path | None = None) -> Path | None:
    """Return the 1822 Heidenheim facsimile PDF if present."""
    data_dir = heidenheim_haggadah_data_directory(sourcetexts_root)
    for name in ("heidenheim_1822.pdf", "Hebrewbooks_org_4909.pdf"):
        path = data_dir / name
        if path.is_file():
            return path
    pdfs = sorted(data_dir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def _read_page(directory: Path, page_number: str | int, digits: int) -> Optional[Page]:
    """Return the wikitext of a page file in `directory`, or None if absent."""
    page_num = int(page_number)
    path = directory / f"{page_num:0{digits}d}.txt"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return Page.model_validate(dict(number=page_num, content=f.read()))
    except FileNotFoundError:
        return None


def _read_credits(directory: Path, page_number: str | int, digits: int) -> Optional[list[str]]:
    """Return the contributor names in a credits file, or None if absent."""
    page_num = int(page_number)
    path = directory / f"{page_num:0{digits}d}.txt"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.read().split("\n") if line.strip()]
    except FileNotFoundError:
        return None


def get_page(page_number: str | int, sourcetexts_root: Path | None = None) -> Optional[Page]:
    """Return the wikitext of the given Page, or None if it does not exist."""
    return _read_page(jps1917_text_directory(sourcetexts_root), page_number, 4)


def get_credits(page_number: str | int, sourcetexts_root: Path | None = None) -> Optional[list[str]]:
    """Return the credits of the given Page, or None if it does not exist."""
    return _read_credits(jps1917_credits_directory(sourcetexts_root), page_number, 4)


def get_birnbaum_page(page_number: str | int, sourcetexts_root: Path | None = None) -> Optional[Page]:
    """Return the wikitext of the given Birnbaum page, or None if it does not exist."""
    return _read_page(birnbaum_siddur_text_directory(sourcetexts_root), page_number, 3)


def get_birnbaum_credits(
    page_number: str | int, sourcetexts_root: Path | None = None
) -> Optional[list[str]]:
    """Return the credits of the given Birnbaum page, or None if it does not exist."""
    return _read_credits(birnbaum_siddur_credits_directory(sourcetexts_root), page_number, 3)
