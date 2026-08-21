"""Download the Birnbaum ha-Siddur ha-Shalem from Hebrew Wikisource into sourcetexts.

Writes one wikitext file and one credits file per scan page, mirroring the layout the
JPS 1917 importer uses, plus a manifest recording each page's revision id so later
runs only refetch what actually changed.

The HTTP etiquette — batching, pacing, maxlag, backoff, identification — lives in
:mod:`opensiddur.importer.util.wikisource`, along with the reasoning for reading the
Action API rather than the monthly dumps.

Note that the Wikisource edition is not a faithful transcription of the 1949
printing: it renders the English rubrics into Hebrew, adds Eretz Yisrael customs and
makes textual corrections. Anything describing this source downstream should call it
the Wikisource edition, not Birnbaum 1949.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opensiddur.importer.util.pages import (
    birnbaum_siddur_credits_directory,
    birnbaum_siddur_data_directory,
    birnbaum_siddur_text_directory,
    default_sourcetexts_root,
)
from opensiddur.importer.util.wikisource import (
    CONTACT_EMAIL_ENV_VAR,
    Wiki,
    WikisourceError,
    connect,
    fetch_contributors,
    fetch_revisions,
    list_book_pages,
    resolve_contact_email,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER = "he.wikisource.org"
WIKI_NAMESPACE = "עמוד"  # ProofreadPage namespace 104, as named on he.wikisource
BOOK_NAME = "Philip Birnbaum - ha-Siddur ha-Shalem (The Daily Prayer Book,1949).pdf"

MANIFEST_NAME = "manifest.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def manifest_path(sourcetexts_root: Path | None = None) -> Path:
    return birnbaum_siddur_data_directory(sourcetexts_root) / MANIFEST_NAME


def load_manifest(sourcetexts_root: Path | None = None) -> dict[str, Any]:
    """Read the manifest, or return an empty one if this is a first run."""
    try:
        with open(manifest_path(sourcetexts_root), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        logger.warning(
            "Manifest at %s is unreadable (%s); treating every page as new. "
            "Use --force to rewrite it cleanly.",
            manifest_path(sourcetexts_root),
            exc,
        )
        return {}


def save_manifest(manifest: dict[str, Any], sourcetexts_root: Path | None = None) -> None:
    path = manifest_path(sourcetexts_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def page_key(page_num: int, digits: int) -> str:
    """Zero-padded page identifier, used for both filenames and manifest keys."""
    return f"{page_num:0{digits}d}"


def _needs_download(
    key: str,
    revid: int,
    manifest_pages: dict[str, Any],
    text_dir: Path,
    credits_dir: Path,
) -> bool:
    """Whether a page must be fetched: unknown, changed, or missing on disk.

    The on-disk check matters because a manifest entry alone does not prove the files
    survived — someone may have deleted or partially written them.
    """
    recorded = manifest_pages.get(key)
    if recorded is None or recorded.get("revid") != revid:
        return True
    return not (
        (text_dir / f"{key}.txt").is_file() and (credits_dir / f"{key}.txt").is_file()
    )


def download_book(
    contact_email: str,
    sourcetexts_root: Path | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    wiki: Wiki | None = None,
) -> dict[str, Any]:
    """Download every transcribed page of the book, skipping unchanged ones.

    Returns the manifest that was written (or, on a dry run, would have been).
    """
    if wiki is None:
        wiki = connect(SERVER, contact_email)

    data_dir = birnbaum_siddur_data_directory(sourcetexts_root)
    text_dir = birnbaum_siddur_text_directory(sourcetexts_root)
    credits_dir = birnbaum_siddur_credits_directory(sourcetexts_root)

    logger.info("Enumerating pages of %s ...", BOOK_NAME)
    titles_by_number = list_book_pages(wiki, BOOK_NAME)
    if not titles_by_number:
        raise WikisourceError(
            f"No transcribed pages found for {BOOK_NAME!r} on {wiki.server}. "
            "Has the book been moved or renamed?"
        )

    page_numbers = sorted(titles_by_number)
    digits = len(str(page_numbers[-1]))
    logger.info(
        "Found %d transcribed pages (%d-%d)",
        len(page_numbers),
        page_numbers[0],
        page_numbers[-1],
    )

    manifest = load_manifest(sourcetexts_root)
    manifest_pages: dict[str, Any] = {} if force else dict(manifest.get("pages") or {})

    # A revision-id-only probe: no wikitext is serialised, so this stays cheap even
    # when nothing has changed.
    logger.info("Checking which pages have changed ...")
    latest = fetch_revisions(
        wiki, [titles_by_number[n] for n in page_numbers], include_content=False
    )

    stale: list[int] = []
    for number in page_numbers:
        title = titles_by_number[number]
        revision = latest.get(title)
        if revision is None:
            logger.warning("No revision reported for %s; skipping", title)
            continue
        if force or _needs_download(
            page_key(number, digits), revision.revid, manifest_pages, text_dir, credits_dir
        ):
            stale.append(number)

    logger.info("%d of %d pages need downloading", len(stale), len(page_numbers))

    if not stale:
        logger.info("Everything is already up to date.")
        return manifest

    if dry_run:
        logger.info(
            "Dry run: would download %d pages into %s and update %s",
            len(stale),
            data_dir,
            manifest_path(sourcetexts_root),
        )
        return manifest

    stale_titles = [titles_by_number[n] for n in stale]
    logger.info("Fetching wikitext ...")
    contents = fetch_revisions(wiki, stale_titles, include_content=True)
    logger.info("Fetching contributors ...")
    contributors = fetch_contributors(wiki, stale_titles)

    text_dir.mkdir(parents=True, exist_ok=True)
    credits_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for number in stale:
        title = titles_by_number[number]
        revision = contents.get(title)
        if revision is None or revision.content is None:
            logger.warning("No wikitext returned for %s; leaving it for the next run", title)
            continue

        key = page_key(number, digits)
        credits_text = "\n".join(contributors.get(title, []))

        (text_dir / f"{key}.txt").write_text(revision.content, encoding="utf-8")
        (credits_dir / f"{key}.txt").write_text(credits_text, encoding="utf-8")

        manifest_pages[key] = {
            "revid": revision.revid,
            "timestamp": revision.timestamp,
            "text_sha256": _sha256(revision.content),
            "credits_sha256": _sha256(credits_text),
        }
        written += 1
        if written % 50 == 0:
            logger.info("Wrote %d/%d pages", written, len(stale))

    manifest = {
        "source": wiki.server,
        "book_name": BOOK_NAME,
        "namespace": WIKI_NAMESPACE,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "pages": manifest_pages,
    }
    # Written once, at the end. A crash mid-run then leaves the previous manifest
    # intact and the interrupted pages simply look stale next time, which is safer
    # than a per-page write that could claim a page is current when its file was
    # only half written.
    save_manifest(manifest, sourcetexts_root)
    logger.info("Wrote %d pages; manifest updated at %s", written, manifest_path(sourcetexts_root))
    return manifest


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download the Birnbaum ha-Siddur ha-Shalem from Hebrew Wikisource into the "
            "sourcetexts tree, refetching only pages that have changed."
        )
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=default_sourcetexts_root(),
        help=(
            "Root of the opensiddur/sourcetexts repository; pages are written under "
            "<root>/birnbaum_siddur (default: <repo>/sourcetexts/sources)."
        ),
    )
    parser.add_argument(
        "--contact-email",
        default=None,
        help=(
            "Contact address for the User-Agent header, as Wikimedia's User-Agent "
            f"policy requires. Falls back to ${CONTACT_EMAIL_ENV_VAR}."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report what would be downloaded without writing anything. Still performs "
            "the read-only enumeration and change check."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refetch every page, ignoring the manifest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        contact_email = resolve_contact_email(args.contact_email)
        download_book(
            contact_email,
            args.sourcetexts_root,
            dry_run=args.dry_run,
            force=args.force,
        )
    except WikisourceError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
