import argparse
import os
import sys
from pathlib import Path

from opensiddur.common.xslt import xslt_transform
from opensiddur.importer.util.validation import validate


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def make_project_directory(project_dir: Path | None = None) -> Path:
    """Create the WLC project directory if missing; return its path."""
    directory = (
        project_dir.resolve() if project_dir is not None else _repo_root() / "project" / "wlc"
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_source_directory(sourcetexts_root: Path | None = None) -> Path:
    """Directory containing WLC Books/ (i.e. <sourcetexts-root>/wlc)."""
    root = (
        sourcetexts_root.resolve()
        if sourcetexts_root is not None
        else _repo_root() / "sources"
    )
    return root / "wlc"


def get_xslt_directory() -> Path:
    return Path(__file__).resolve().parent


def _wlc_directory_uri(wlc_directory: Path) -> str:
    """File URI of the WLC tree root, with trailing slash, for XSLT resolve-uri base."""
    u = wlc_directory.resolve().as_uri()
    return u if u.endswith("/") else u + "/"


def _build_arg_parser() -> argparse.ArgumentParser:
    repo = _repo_root()
    parser = argparse.ArgumentParser(
        description="Transform WLC UXLC XML from sourcetexts into JLPTEI project files."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=repo / "project" / "wlc",
        help="Output directory for generated JLPTEI (default: <repo>/project/wlc).",
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=repo / "sources",
        help=(
            "Root of the opensiddur/sourcetexts repository; WLC files are read from "
            "<root>/wlc/Books (default: <repo>/sources so legacy layout stays <repo>/sources/wlc)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    project_directory = make_project_directory(args.project_dir)
    wlc_directory = get_source_directory(args.sourcetexts_root)
    xslt_directory = get_xslt_directory()

    xslt_transform(
        xslt_directory / "transform_index.xslt",
        wlc_directory / "Books" / "TanachHeader.xml",
        project_directory / "index.xml",
        xslt_params={"wlc-root-uri": _wlc_directory_uri(wlc_directory)},
    )
    for book in os.listdir(wlc_directory / "Books"):
        if book not in ["TanachHeader.xml", "TanachIndex.xml"] and not book.endswith(".DH.xml"):
            print(f"Transforming {book}")
            xslt_transform(
                xslt_directory / "transform_book.xslt",
                wlc_directory / "Books" / book,
                project_directory / book.lower(),
            )

    for book in os.listdir(project_directory):
        if book.endswith(".xml"):
            print(f"Validating {book}")
            is_valid, errors = validate(project_directory / book)
            if not is_valid:
                print(f"Errors in {book}: {errors}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
