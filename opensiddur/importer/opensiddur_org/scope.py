"""Which posts are prayers this importer takes, and which of those it can take unaided.

A post is **in scope** when it is filed under "Prayers & Praxes" (category 1132) or below,
and the site itself sets its prayer text: a ``toggleable-table`` with text in it, or liturgy
set in ``div[lang]`` blocks. Index posts, essays, and posts that only link to a file, embed a
scan or play audio are out of scope.

An in-scope post is **standard** when the converter can encode it without help, and
**irregular** otherwise, with the reasons. Irregular posts wait for a per-post override (see
``specs/OPENSIDDUR_ORG_IMPORT.md``, "A skill for irregular posts").
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from opensiddur.importer.opensiddur_org.languages import UNKNOWN_LANGUAGE
from opensiddur.importer.opensiddur_org.parse_post import Cell, Column, Post

PRAYERS_CATEGORY = 1132


def descendant_categories(categories: list[dict[str, Any]], roots: set[int]) -> set[int]:
    """``roots`` and every category below them."""
    children: dict[int, list[int]] = {}
    for category in categories:
        children.setdefault(int(category.get("parent_id") or 0), []).append(int(category["id"]))
    found: set[int] = set()
    pending = list(roots)
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(children.get(current, []))
    return found


def posts_in_categories(categories: list[dict[str, Any]], category_ids: set[int]) -> set[int]:
    """The IDs of posts filed in any of ``category_ids``."""
    post_ids: set[int] = set()
    for category in categories:
        if int(category["id"]) in category_ids:
            post_ids.update(int(p) for p in category.get("post_ids") or [])
    return post_ids


def category_names(categories: list[dict[str, Any]]) -> dict[int, str]:
    return {int(c["id"]): html.unescape(c.get("name", "")).strip() for c in categories}


def _cell_has_text(cell: Cell) -> bool:
    return not cell.is_empty


@dataclass(frozen=True)
class Scope:
    in_scope: bool
    reason: str


def content_scope(post: Post) -> Scope:
    """Whether the post sets prayer text itself (the category test is separate)."""
    if post.slug.startswith("list-of-"):
        return Scope(False, "index post")
    if post.columns and any(
        _cell_has_text(row.cells[i])
        for row in post.rows
        for i, column in enumerate(post.columns)
        if column.role != "contribute"
    ):
        return Scope(True, "table")
    if any(_cell_has_text(cell) for cell in post.loose_cells):
        return Scope(True, "prose")
    if post.file_links:
        return Scope(False, "file link only")
    if post.embeds:
        return Scope(False, "embed only")
    return Scope(False, "no prayer text")


def imported_columns(post: Post) -> list[tuple[int, Column]]:
    """The columns that become projects: every column with text, other than an empty
    "Contribute a translation" column (a source-only post is one project)."""
    return [
        (index, column)
        for index, column in enumerate(post.columns)
        if any(_cell_has_text(row.cells[index]) for row in post.rows)
    ]


def column_mode(post: Post, index: int) -> set[str]:
    """The kinds of block a column holds, ignoring headings."""
    return {
        block.kind
        for row in post.rows
        for block in row.cells[index].blocks
        if block.kind != "heading"
    }


def is_heading_row(post: Post, row_index: int) -> bool:
    """Whether every cell of a row with text holds just one heading."""
    cells = [cell for cell in post.rows[row_index].cells if not cell.is_empty]
    return bool(cells) and all(
        len(cell.blocks) == 1 and cell.blocks[0].kind == "heading" for cell in cells
    )


def irregularities(post: Post) -> list[str]:
    """Why the converter cannot encode this post unaided, from the post's own structure.

    Licence, contributor and URN problems are added by the caller, which knows the decisions
    and registries.
    """
    reasons: list[str] = []
    if not post.columns:
        reasons.append("prose with no table")
        return reasons
    if post.table_count > 1:
        reasons.append("more than one table")
    if post.has_colour_alignment:
        reasons.append("colour-coded alignment")
    columns = imported_columns(post)
    seen_langs: set[str] = set()
    for index, column in columns:
        if column.mismatch:
            reasons.append(f"column {column.header!r}: {column.mismatch}")
        if not column.role:
            reasons.append(f"column {column.header!r}: unknown role")
        if column.lang == UNKNOWN_LANGUAGE:
            reasons.append(f"column {column.header!r}: unknown language")
        if column.lang in seen_langs:
            reasons.append(f"two columns in {column.lang}")
        seen_langs.add(column.lang)
        if len(column_mode(post, index)) > 1:
            reasons.append(f"column {column.header!r}: mixes verse and prose")
    for row_index, row in enumerate(post.rows):
        if is_heading_row(post, row_index):
            continue
        if any(block.kind == "heading" for cell in row.cells for block in cell.blocks):
            reasons.append("a heading inside a cell of text")
            break
    return reasons
