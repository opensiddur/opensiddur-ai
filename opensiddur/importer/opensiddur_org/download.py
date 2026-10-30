"""Copy opensiddur.org posts from the site's monthly GitHub export into ``sourcetexts``.

The whole site is exported at the start of each month to
https://github.com/aharonium/opensiddur.org. That repository is cloned once, as a sister of
``opensiddur-ai`` and ``sourcetexts`` (``opensiddur-repos/opensiddur.org/``), and files are
read from it at a commit with ``git show``, so whatever is checked out there is never
touched.

What is written, under ``sourcetexts/sources/opensiddur_org/``:

- ``posts/<post_id>.json``: each in-scope post, verbatim. Posts are stored flat by ID, so a
  post that moves category upstream keeps its path here.
- ``categories.json`` and ``contributors_by_id.json``: the export's indexes the converter
  reads (scope, and contributor slugs and roles).
- ``manifest.json``: the upstream commit and its date, the categories selected, and for each
  post its upstream path, ``last_updated`` and sha256.

A post is rewritten only when its ``last_updated`` differs from the manifest's: the export's
diffs are noisy, and a bulk re-save on the site touches thousands of files without changing
them. A run at the commit already recorded writes nothing at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opensiddur.common.constants import REPO_ROOT
from opensiddur.importer.opensiddur_org.parse_post import parse_post, post_id_from_path
from opensiddur.importer.opensiddur_org.scope import (
    PRAYERS_CATEGORY,
    content_scope,
    descendant_categories,
    posts_in_categories,
)
from opensiddur.importer.util.internet_archive import write_if_changed
from opensiddur.importer.util.pages import opensiddur_org_data_directory

logger = logging.getLogger(__name__)

UPSTREAM_URL = "https://github.com/aharonium/opensiddur.org.git"
DEFAULT_REF = "origin/master"
UPSTREAM_ENV = "OPENSIDDUR_ORG_UPSTREAM"

CATEGORIES_PATH = "categories and tags/categories.json"
CONTRIBUTORS_PATH = "contributors/contributors_by_id.json"
INDEX_FILES = {
    "categories.json": CATEGORIES_PATH,
    "contributors_by_id.json": CONTRIBUTORS_PATH,
}
MANIFEST_NAME = "manifest.json"


def default_upstream_directory() -> Path:
    """``opensiddur-repos/opensiddur.org``, beside this repository's worktrees."""
    override = os.environ.get(UPSTREAM_ENV)
    if override:
        return Path(override)
    return REPO_ROOT.parent.parent / "opensiddur.org"


@dataclass
class Upstream:
    """A clone of the export, read at a commit without checking anything out."""

    directory: Path

    def _git(self, *args: str, binary: bool = False) -> Any:
        result = subprocess.run(
            ["git", "-C", str(self.directory), *args],
            check=True,
            capture_output=True,
        )
        return result.stdout if binary else result.stdout.decode("utf-8")

    def ensure(self, *, fetch: bool = True, url: str = UPSTREAM_URL) -> None:
        if not (self.directory / ".git").exists():
            logger.info("Cloning %s into %s", url, self.directory)
            self.directory.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--no-checkout", url, str(self.directory)],
                check=True,
            )
        elif fetch:
            self._git("fetch", "--quiet", "origin")

    def resolve(self, ref: str) -> str:
        return self._git("rev-parse", "--verify", f"{ref}^{{commit}}").strip()

    def commit_date(self, commit: str) -> str:
        return self._git("show", "-s", "--format=%cs", commit).strip()

    def list_files(self, commit: str, prefix: str) -> list[str]:
        output = self._git("ls-tree", "-r", "--name-only", "-z", commit, "--", prefix)
        return [name for name in output.split("\0") if name]

    def read(self, commit: str, path: str) -> bytes:
        return self._git("show", f"{commit}:{path}", binary=True)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(data_dir: Path) -> dict[str, Any]:
    try:
        return json.loads((data_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _manifest_text(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def post_paths(upstream: Upstream, commit: str) -> dict[int, str]:
    """Post ID -> upstream path. IDs come from the ``_(<id>).json`` suffix, never the path."""
    paths: dict[int, str] = {}
    for path in upstream.list_files(commit, "posts/"):
        post_id = post_id_from_path(path)
        if post_id is not None:
            paths[post_id] = path
    return paths


@dataclass
class DownloadResult:
    commit: str
    written: list[int]
    removed: list[int]
    kept: int
    out_of_scope: dict[int, str]
    noop: bool = False


def download(
    *,
    upstream: Upstream,
    ref: str = DEFAULT_REF,
    data_dir: Path | None = None,
    categories: list[int] | None = None,
    fetch: bool = True,
    dry_run: bool = False,
) -> DownloadResult:
    """Copy the in-scope posts of ``categories`` (default: as last recorded, else 1132) at
    ``ref`` into ``data_dir``. Posts no longer selected or in scope are removed."""
    data_dir = data_dir or opensiddur_org_data_directory()
    upstream.ensure(fetch=fetch)
    commit = upstream.resolve(ref)
    manifest = load_manifest(data_dir)
    selected = sorted(categories or manifest.get("categories") or [PRAYERS_CATEGORY])
    recorded_posts: dict[str, Any] = manifest.get("posts", {})

    if (
        manifest.get("upstream_commit") == commit
        and manifest.get("categories") == selected
        and all((data_dir / "posts" / f"{pid}.json").is_file() for pid in recorded_posts)
    ):
        return DownloadResult(commit, [], [], len(recorded_posts), {}, noop=True)

    category_list = json.loads(upstream.read(commit, CATEGORIES_PATH))
    wanted = posts_in_categories(category_list, descendant_categories(category_list, set(selected)))
    paths = post_paths(upstream, commit)

    new_posts: dict[str, Any] = {}
    written: list[int] = []
    out_of_scope: dict[int, str] = {}
    for post_id in sorted(wanted):
        path = paths.get(post_id)
        if path is None:
            continue  # filed in a category but not exported (e.g. a page, or unpublished)
        raw = upstream.read(commit, path)
        data = json.loads(raw)
        scope = content_scope(parse_post(data))
        if not scope.in_scope:
            out_of_scope[post_id] = scope.reason
            continue
        key = str(post_id)
        entry = {"path": path, "last_updated": data.get("last_updated", ""), "sha256": _sha256(raw)}
        target = data_dir / "posts" / f"{post_id}.json"
        previous = recorded_posts.get(key)
        if previous and previous.get("last_updated") == entry["last_updated"] and target.is_file():
            # Unchanged: keep the copy and the record we have, even if the export re-saved it.
            new_posts[key] = {**previous, "path": path}
            continue
        new_posts[key] = entry
        written.append(post_id)
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

    removed = sorted(int(k) for k in recorded_posts if k not in new_posts)
    if not dry_run:
        for post_id in removed:
            (data_dir / "posts" / f"{post_id}.json").unlink(missing_ok=True)
        for name, path in INDEX_FILES.items():
            write_if_changed(data_dir / name, upstream.read(commit, path).decode("utf-8"))
        write_if_changed(
            data_dir / MANIFEST_NAME,
            _manifest_text(
                {
                    "upstream_repo": UPSTREAM_URL,
                    "upstream_commit": commit,
                    "upstream_commit_date": upstream.commit_date(commit),
                    "categories": selected,
                    "posts": new_posts,
                }
            ),
        )
    return DownloadResult(commit, written, removed, len(new_posts) - len(written), out_of_scope)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ref", default=DEFAULT_REF, help="upstream commit or ref (default: %(default)s)")
    parser.add_argument("--upstream-dir", type=Path, default=None,
                        help=f"the export's clone (default: ${UPSTREAM_ENV} or opensiddur-repos/opensiddur.org)")
    parser.add_argument("--sourcetexts-root", type=Path, default=None)
    parser.add_argument("--category", type=int, action="append",
                        help="copy only posts in this category and below; repeatable "
                             "(default: as last recorded, else 1132, Prayers & Praxes)")
    parser.add_argument("--no-fetch", action="store_true", help="do not fetch the upstream first")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    upstream = Upstream(args.upstream_dir or default_upstream_directory())
    result = download(
        upstream=upstream,
        ref=args.ref,
        data_dir=opensiddur_org_data_directory(args.sourcetexts_root),
        categories=args.category,
        fetch=not args.no_fetch,
        dry_run=args.dry_run,
    )
    if result.noop:
        print(f"Already at {result.commit[:10]}; nothing to do.")
        return 0
    print(
        f"{result.commit[:10]}: wrote {len(result.written)} post(s), kept {result.kept}, "
        f"removed {len(result.removed)}; {len(result.out_of_scope)} out of scope."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
