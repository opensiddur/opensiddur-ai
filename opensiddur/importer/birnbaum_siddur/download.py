"""Download every source of the Birnbaum siddur, in the order they depend on.

Four stages, three of them fetching and the fourth reconciling what they fetched::

    Hebrew Wikisource  ->  text/ credits/ source/ external/ structure.json
    English Wikisource ->  en/
    Internet Archive   ->  ia/derivatives/ ia/ocr/ ia/metadata.json
    correspondence     ->  pages.json

The order matters only at the end: ``pages.json`` is built by reading all three
layers off disk, so it has to run last, and running the four commands by hand in the
wrong order produces a table that quietly describes a book that is no longer there.
That is the whole reason this module exists.

Each stage is independently skippable, and each is already a no-op when its source has
not changed, so re-running the lot is cheap.

Run as::

    uv run python -m opensiddur.importer.birnbaum_siddur.download
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from opensiddur.importer.birnbaum_siddur import correspondence as correspondence_stage
from opensiddur.importer.birnbaum_siddur import en_wikisource, internet_archive
from opensiddur.importer.birnbaum_siddur import wikisource as he_wikisource
from opensiddur.importer.util.internet_archive import (
    AGENT_MODEL_ENV_VAR,
    InternetArchiveError,
    resolve_agent_model,
)
from opensiddur.importer.util.pages import default_sourcetexts_root
from opensiddur.importer.util.wikisource import (
    CONTACT_EMAIL_ENV_VAR,
    WikisourceError,
    resolve_contact_email,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_all(
    contact_email: str,
    sourcetexts_root: Path | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    skip_he: bool = False,
    skip_en: bool = False,
    skip_ia: bool = False,
    skip_correspondence: bool = False,
    with_djvu: bool = False,
    fetch_pdf: bool = False,
    agent_model: str | None = None,
) -> None:
    """Run every stage that was not skipped, in dependency order."""
    if not skip_he:
        logger.info("=== Hebrew Wikisource ===")
        he_wikisource.download_book(
            contact_email, sourcetexts_root, dry_run=dry_run, force=force
        )

    if not skip_en:
        logger.info("=== English Wikisource ===")
        en_wikisource.download_book(
            contact_email, sourcetexts_root, dry_run=dry_run, force=force
        )

    if not skip_ia:
        logger.info("=== Internet Archive ===")
        internet_archive.download_ia(
            contact_email,
            sourcetexts_root,
            dry_run=dry_run,
            force=force,
            with_djvu=with_djvu,
            fetch_pdf=fetch_pdf,
            agent_model=agent_model,
        )

    if skip_correspondence:
        return

    logger.info("=== Page correspondence ===")
    if dry_run:
        # The three layers may not be on disk at all, and a table built over a
        # partial tree would describe a book that does not exist.
        logger.info("Dry run: skipping pages.json.")
        return

    table = correspondence_stage.build_correspondence(sourcetexts_root)
    for line in correspondence_stage.report(table):
        logger.info("%s", line)
    logger.info("Wrote %s", correspondence_stage.save_correspondence(table, sourcetexts_root))


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download the Birnbaum siddur from all three of its sources and rebuild "
            "the page correspondence table. Each stage skips what has not changed."
        )
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=default_sourcetexts_root(),
        help=(
            "Root of the opensiddur/sourcetexts repository; everything is written "
            "under <root>/birnbaum_siddur (default: <repo>/sourcetexts/sources)."
        ),
    )
    parser.add_argument(
        "--contact-email",
        default=None,
        help=(
            "Contact address for the User-Agent header, which both Wikimedia's and "
            f"the Archive's policies require. Falls back to ${CONTACT_EMAIL_ENV_VAR}."
        ),
    )
    parser.add_argument(
        "--agent-model",
        default=None,
        help=(
            "Model name to add to the User-Agent for archive.org, which its bot "
            f"policy asks of AI-agent clients. Falls back to ${AGENT_MODEL_ENV_VAR}."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Write nothing.")
    parser.add_argument(
        "--force", action="store_true", help="Refetch everything, ignoring manifests."
    )
    parser.add_argument(
        "--with-djvu",
        action="store_true",
        help="Also fetch the Archive's word-coordinate file, for page segmentation.",
    )
    parser.add_argument(
        "--fetch-pdf",
        action="store_true",
        help="Also fetch the full scan PDF into the untracked output directory.",
    )
    for stage, help_text in (
        ("he", "Hebrew Wikisource"),
        ("en", "English Wikisource"),
        ("ia", "the Internet Archive"),
        ("correspondence", "the pages.json rebuild"),
    ):
        parser.add_argument(
            f"--skip-{stage}",
            action="store_true",
            help=f"Skip {help_text}.",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        download_all(
            resolve_contact_email(args.contact_email),
            args.sourcetexts_root,
            dry_run=args.dry_run,
            force=args.force,
            skip_he=args.skip_he,
            skip_en=args.skip_en,
            skip_ia=args.skip_ia,
            skip_correspondence=args.skip_correspondence,
            with_djvu=args.with_djvu,
            fetch_pdf=args.fetch_pdf,
            agent_model=resolve_agent_model(args.agent_model),
        )
    except (WikisourceError, InternetArchiveError, FileNotFoundError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
