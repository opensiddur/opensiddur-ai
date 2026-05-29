import argparse
import logging
import sys
from pathlib import Path
from zipfile import ZipFile

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _default_sourcetexts_root() -> Path:
    return _repo_root() / "sources"


def download_and_unzip_tanach(sourcetexts_root: Path | None = None) -> None:
    """Download and unzip the latest Tanach XML file from tanach.us into <sourcetexts-root>/wlc."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else _default_sourcetexts_root()
    )
    target_dir = root / "wlc"
    target_dir.mkdir(parents=True, exist_ok=True)

    url = "https://tanach.us/Books/Tanach.xml.zip"

    logger.info("Downloading %s...", url)
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    zip_path = target_dir / "Tanach.xml.zip"
    with open(zip_path, "wb") as f:
        f.write(response.content)

    logger.info("Downloaded file saved to %s", zip_path)

    logger.info("Unzipping %s...", zip_path)
    with ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(target_dir)

    logger.info("Successfully extracted files to %s", target_dir)

    zip_path.unlink()
    logger.info("Removed temporary zip file")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download WLC Tanach XML from tanach.us into the sourcetexts tree."
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=_default_sourcetexts_root(),
        help=(
            "Root of the opensiddur/sourcetexts repository; files are written under "
            "<root>/wlc (default: <repo>/sources so output matches legacy sources/wlc)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    download_and_unzip_tanach(args.sourcetexts_root)
    return 0


def _run_cli() -> None:  # pragma: no cover
    try:
        sys.exit(main())
    except Exception as e:
        logger.error("Error downloading/unzipping Tanach: %s", e)
        raise


if __name__ == "__main__":  # pragma: no cover
    _run_cli()
