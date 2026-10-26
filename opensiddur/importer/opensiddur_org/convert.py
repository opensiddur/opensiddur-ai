"""Convert opensiddur.org posts from ``sourcetexts`` into JLPTEI projects.

Only standard posts are converted (see :mod:`scope`). For each one, every column with text
becomes a project ``osp-<post_id>-<lang>``, unless its licence is rejected or undecided.
Every file is validated before it is written; stale files in the post's projects, and
projects for languages the post no longer has, are removed.

A post needs a URN decision in ``specs/opensiddur_org/post_urns.jsonl`` (see
:mod:`match`) and every person it credits registered in
``specs/urn_registry/contributor.jsonl``. ``--register`` adds the registry records a post's
new URNs need; ``--emit-contributor-candidates`` writes the lines for unregistered people to
``output/`` for review, and never registers anyone.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from opensiddur.common.constants import OUTPUT_DIRECTORY, PROJECT_DIRECTORY
from opensiddur.common.urn_registry import REGISTRY_DIRECTORY
from opensiddur.exporter.validate_urn_references import (
    validate_project_contributor_references,
    validate_project_urn_references,
)
from opensiddur.importer.opensiddur_org.contributors import (
    Contributors,
    candidate_line,
    post_credits,
    registered_contributors,
    unregistered,
)
from opensiddur.importer.opensiddur_org.download import MANIFEST_NAME, load_manifest
from opensiddur.importer.opensiddur_org.licences import LicenceDecisions, load_decisions
from opensiddur.importer.opensiddur_org.parse_post import Post, load_post
from opensiddur.importer.opensiddur_org.scope import (
    content_scope,
    descendant_categories,
    imported_columns,
    irregularities,
    posts_in_categories,
)
from opensiddur.importer.opensiddur_org.tei_builder import (
    build_project,
    front_language,
    project_id,
    row_numbers,
    titles_by_language,
)
from opensiddur.importer.opensiddur_org.urns import (
    POST_URNS_PATH,
    PostUrns,
    load_post_urns,
    registry_lines,
)
from opensiddur.importer.util.pages import opensiddur_org_data_directory
from opensiddur.importer.util.tei_project import prune_stale_files, validate_and_write

logger = logging.getLogger(__name__)

CANDIDATES_PATH = OUTPUT_DIRECTORY / "opensiddur_org_contributor_candidates.jsonl"


@dataclass
class PostPlan:
    """What converting one post would do, or why it cannot be done."""

    post: Post
    reasons: list[str] = field(default_factory=list)
    columns: list[tuple[int, object, object]] = field(default_factory=list)
    skipped_columns: dict[str, str] = field(default_factory=dict)
    candidates: list[str] = field(default_factory=list)

    @property
    def standard(self) -> bool:
        return not self.reasons


@dataclass
class Context:
    data_dir: Path
    contributors: Contributors
    decisions: LicenceDecisions
    post_urns: dict[int, PostUrns]
    registered: set[str]
    upstream_commit: str
    upstream_commit_date: str


def load_context(
    data_dir: Path,
    *,
    post_urns_path: Path = POST_URNS_PATH,
    registry_directory: Path = REGISTRY_DIRECTORY,
    decisions: LicenceDecisions | None = None,
) -> Context:
    manifest = load_manifest(data_dir)
    if not manifest:
        raise SystemExit(f"No {MANIFEST_NAME} in {data_dir}; run the download first.")
    return Context(
        data_dir=data_dir,
        contributors=Contributors.load(data_dir / "contributors_by_id.json"),
        decisions=decisions or load_decisions(),
        post_urns=load_post_urns(post_urns_path),
        registered=registered_contributors(registry_directory),
        upstream_commit=manifest["upstream_commit"],
        upstream_commit_date=manifest["upstream_commit_date"],
    )


def plan_post(post: Post, context: Context) -> PostPlan:
    plan = PostPlan(post)
    scope = content_scope(post)
    if not scope.in_scope:
        plan.reasons.append(f"out of scope: {scope.reason}")
        return plan
    plan.reasons.extend(irregularities(post))

    credits = post_credits(post, context.contributors)
    missing = unregistered(credits, context.registered)
    if missing:
        plan.reasons.append("unregistered contributor(s): " + ", ".join(c.slug for c in missing))
        plan.candidates = [candidate_line(c) for c in missing]

    urns = context.post_urns.get(post.post_id)
    if urns is None:
        plan.reasons.append("no URN decision")
    elif urns.kind == "existing":
        unmapped = [n for n in row_numbers(post).values() if not urns.rows.get(n)]
        if unmapped:
            plan.reasons.append(f"existing URN {urns.urn}: rows {unmapped} are not mapped")

    for index, column in imported_columns(post):
        decision = context.decisions.for_column(post, column)
        if decision.status == "allow":
            plan.columns.append((index, column, decision))
        else:
            plan.skipped_columns[column.lang] = f"{decision.status}: {decision.basis}"
    if not plan.columns and not plan.reasons:
        plan.reasons.append("no column may be imported: " + "; ".join(
            f"{lang} {why}" for lang, why in sorted(plan.skipped_columns.items())))
    return plan


def _compact(document: str) -> str:
    """Drop the newlines between tags that the document template puts there, so that the
    pretty-printer can indent while keeping meaningful spaces between inline elements."""
    return re.sub(r">\s*\n\s*<", "><", document)


def convert_post(
    plan: PostPlan, context: Context, project_directory: Path, *, registry_directory: Path = REGISTRY_DIRECTORY
) -> list[str]:
    """Write the post's projects. Returns their IDs."""
    post = plan.post
    urns = context.post_urns[post.post_id]
    credits = post_credits(post, context.contributors)
    languages = [column.lang for _, column, _ in plan.columns]
    front_lang = front_language(post, languages)
    written_projects: list[str] = []
    for index, column, decision in plan.columns:
        files = build_project(
            post, index, column,
            urns=urns, credits=credits, licence=decision,
            upstream_commit=context.upstream_commit,
            upstream_commit_date=context.upstream_commit_date,
            with_front=column.lang == front_lang,
        )
        project_dir = project_directory / files.project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        for stem, document in files.files.items():
            validate_and_write(_compact(document), stem, project_dir, keep_blank_text=True)
        prune_stale_files(project_dir, set(files.files))
        written_projects.append(files.project_id)

    # A language the post no longer has (or may no longer import) leaves no project behind.
    prefix = f"osp-{post.post_id}-"
    for stale in sorted(project_directory.glob(f"{prefix}*")):
        if stale.is_dir() and stale.name not in written_projects:
            shutil.rmtree(stale)

    for pid in written_projects:
        problems = validate_project_urn_references(pid, project_directory=project_directory, check_urns=False)
        problems += validate_project_contributor_references(
            pid, project_directory=project_directory, registry_directory=registry_directory
        )
        if problems:
            raise RuntimeError(f"{pid}: {problems}")
    return written_projects


def register_urns(plans: list[PostPlan], context: Context, registry_directory: Path) -> int:
    """Append the registry records the converted posts' new URNs need. Returns how many."""
    existing: set[str] = set()
    for path in registry_directory.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["urn"])
    added = 0
    for plan in plans:
        urns = context.post_urns[plan.post.post_id]
        titles = dict(titles_by_language(plan.post))
        lines = registry_lines(
            urns, len(row_numbers(plan.post)),
            label_en=titles.get("en", ""), label_he=titles.get("he", ""),
        )
        if not lines:
            continue
        namespace = urns.urn.split(":")[3]
        path = registry_directory / f"{namespace}.jsonl"
        new = [line for line in lines if line["urn"] not in existing]
        if not new:
            continue
        with path.open("a", encoding="utf-8") as handle:
            for line in new:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")
                existing.add(str(line["urn"]))
                added += 1
    return added


def select_posts(data_dir: Path, *, posts: list[int] | None, categories: list[int] | None) -> list[int]:
    manifest = load_manifest(data_dir)
    available = sorted(int(k) for k in manifest.get("posts", {}))
    if posts:
        return [p for p in posts if p in available]
    if categories:
        category_list = json.loads((data_dir / "categories.json").read_text(encoding="utf-8"))
        wanted = posts_in_categories(category_list, descendant_categories(category_list, set(categories)))
        return [p for p in available if p in wanted]
    return available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--post", type=int, action="append", help="convert this post; repeatable")
    parser.add_argument("--category", type=int, action="append", help="convert posts in this category and below")
    parser.add_argument("--sourcetexts-root", type=Path, default=None)
    parser.add_argument("--project-directory", type=Path, default=PROJECT_DIRECTORY)
    parser.add_argument("--register", action="store_true",
                        help="append the registry records new post URNs need")
    parser.add_argument("--emit-contributor-candidates", action="store_true",
                        help=f"write lines for unregistered contributors to {CANDIDATES_PATH}")
    parser.add_argument("--dry-run", action="store_true", help="report what would be converted; write nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data_dir = opensiddur_org_data_directory(args.sourcetexts_root)
    context = load_context(data_dir)
    plans = [
        plan_post(load_post(data_dir / "posts" / f"{post_id}.json"), context)
        for post_id in select_posts(data_dir, posts=args.post, categories=args.category)
    ]
    standard = [plan for plan in plans if plan.standard]

    if args.emit_contributor_candidates:
        lines = sorted({line for plan in plans for line in plan.candidates})
        CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        CANDIDATES_PATH.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        print(f"{len(lines)} contributor candidate(s) written to {CANDIDATES_PATH}")

    converted = 0
    for plan in standard:
        if not args.dry_run:
            convert_post(plan, context, args.project_directory)
            if args.register:
                register_urns([plan], context, REGISTRY_DIRECTORY)
        converted += 1
        for lang, why in sorted(plan.skipped_columns.items()):
            print(f"{plan.post.post_id}: {lang} not imported ({why})")
    for plan in plans:
        if not plan.standard:
            print(f"{plan.post.post_id}: skipped: {'; '.join(plan.reasons)}")
    print(f"{'Would convert' if args.dry_run else 'Converted'} {converted} of {len(plans)} post(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
