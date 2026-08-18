"""Cut a release: `uv run python -m opensiddur.release [--minor] [--dry-run]`.

See RELEASE_PROCEDURE.md for what to do before and after running this.
"""

import argparse
import logging
import sys
from pathlib import Path

from opensiddur.common.constants import REPO_ROOT
from opensiddur.release.release import ReleaseError, Repository, release
from opensiddur.release.version import Version

logger = logging.getLogger(__name__)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m opensiddur.release",
        description=(
            "Bump the version, pin the sourcetexts and opensiddur-projects submodules to "
            "their tracked branches, roll the changelog, tag, push, and publish a GitHub "
            "release. Below 1.0.0 the default bump is the minor version."
        ),
    )
    level = parser.add_mutually_exclusive_group()
    level.add_argument(
        "--major", dest="level", action="store_const", const="major",
        help="Bump the major version (incompatible changes).",
    )
    level.add_argument(
        "--minor", dest="level", action="store_const", const="minor",
        help="Bump the minor version (the default below 1.0.0).",
    )
    level.add_argument(
        "--patch", dest="level", action="store_const", const="patch",
        help="Bump the patch version (fixes only).",
    )
    level.add_argument(
        "--version", dest="explicit", type=Version.parse, metavar="X.Y.Z",
        help="Release exactly this version instead of bumping.",
    )
    parser.add_argument(
        "--repo", type=Path, default=REPO_ROOT,
        help="The opensiddur-ai checkout to release from (default: this one).",
    )
    parser.add_argument(
        "--no-publish", dest="publish", action="store_false",
        help="Tag and push, but do not create the GitHub release.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print every command and file that would change, and change nothing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    repo = Repository(root=args.repo.resolve(), dry_run=args.dry_run)
    try:
        plan = release(
            repo, level=args.level, explicit=args.explicit, publish=args.publish
        )
    except (ReleaseError, ValueError) as error:
        logger.error("%s", error)
        return 1

    verb = "would release" if args.dry_run else "released"
    logger.info("")
    logger.info("%s %s -> %s", verb, plan.current, plan.version)
    for path, commit in sorted(plan.pinned.items()):
        logger.info("  %s pinned at %s", path, commit)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
