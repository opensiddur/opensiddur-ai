"""Each post's URNs, decided once and recorded in ``specs/opensiddur_org/post_urns.jsonl``.

A post that is a version of a text already in the collection — a psalm, the Birkat
Hamazon, a prayer in Birnbaum — uses that text's URNs, so that it can be set in parallel with
the other versions. Only a post that matches nothing gets URNs of its own. Either way the
decision is recorded by post ID, so a later change of title, slug or category never changes a
post's URNs:

    {"post_id": 123, "kind": "existing", "urn": "urn:x-opensiddur:text:bible:psalms/29",
     "rows": {"1": "urn:x-opensiddur:text:bible:psalms/29/1", ...}}
    {"post_id": 456, "kind": "new", "urn": "urn:x-opensiddur:text:prayer:some_prayer"}

A ``new`` post's rows are ``<urn>/<n>``, numbered from 1 over the rows that are not
headings, except where ``rows`` names an existing URN: a post that strings together prayers
already in the collection (the Ḥanukkah blessings, say) is new as a whole but shares its
parts. An ``existing`` post names each row's URN, or null for a row that matches no part of
the existing text; such a post is irregular until every row is mapped.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from opensiddur.common.constants import REPO_ROOT

POST_URNS_PATH = REPO_ROOT / "specs" / "opensiddur_org" / "post_urns.jsonl"
TEXT_PREFIX = "urn:x-opensiddur:text:"

#: Tags that make a post a poem rather than a prayer.
POEM_TAGS = ("piyyut", "piyyuṭ", "פיוט", "poem", "poetry", "hymn", "zemer", "zemirot", "qinah", "ḳinah")


@dataclass
class PostUrns:
    post_id: int
    kind: str
    urn: str
    rows: dict[int, str | None] = field(default_factory=dict)

    def row_urn(self, n: int) -> str | None:
        if self.kind == "new":
            return self.rows.get(n) or f"{self.urn}/{n}"
        return self.rows.get(n)

    def to_json(self) -> str:
        data: dict[str, object] = {"post_id": self.post_id, "kind": self.kind, "urn": self.urn}
        rows = {str(n): urn for n, urn in sorted(self.rows.items()) if urn or self.kind == "existing"}
        if rows:
            data["rows"] = rows
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "PostUrns":
        data = json.loads(line)
        rows = {int(n): urn for n, urn in (data.get("rows") or {}).items()}
        return cls(post_id=int(data["post_id"]), kind=data["kind"], urn=data["urn"], rows=rows)


def load_post_urns(path: Path = POST_URNS_PATH) -> dict[int, PostUrns]:
    if not path.exists():
        return {}
    records = [PostUrns.from_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {record.post_id: record for record in records}


def save_post_urns(records: dict[int, PostUrns], path: Path = POST_URNS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(records[k].to_json() + "\n" for k in sorted(records))
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def urn_component(text: str) -> str:
    """A registry path component: lowercase ASCII letters, digits and underscores."""
    component = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return re.sub(r"_+", "_", component)


def is_poem(tags: list[str]) -> bool:
    lowered = " ".join(tags).lower()
    return any(tag in lowered for tag in POEM_TAGS)


def mint(post_id: int, slug: str, tags: list[str], taken: set[str]) -> PostUrns:
    """A new URN for a post that matches nothing in the collection.

    The name is the post's slug. If that name is already taken (by an unrelated text, since
    a related one would have matched), the post ID is appended.
    """
    namespace = "poem" if is_poem(tags) else "prayer"
    name = urn_component(slug) or f"post_{post_id}"
    urn = f"{TEXT_PREFIX}{namespace}:{name}"
    if urn in taken:
        urn = f"{urn}_{post_id}"
    return PostUrns(post_id=post_id, kind="new", urn=urn)


def registry_lines(
    record: PostUrns, rows: Iterable[int], *, label_en: str, label_he: str = ""
) -> list[dict[str, object]]:
    """The registry records a ``new`` post's URNs need: the post and each of ``rows`` (the
    row numbers that have text in some imported column)."""
    if record.kind != "new":
        return []
    label_en = label_en or record.urn.rsplit(":", 1)[-1]
    top: dict[str, object] = {"urn": record.urn, "status": "canonical", "label_en": label_en}
    if label_he:
        top["label_he"] = label_he
    lines: list[dict[str, object]] = [top]
    for n in sorted(rows):
        if record.rows.get(n):
            continue  # an existing text's URN, registered already
        lines.append(
            {"urn": f"{record.urn}/{n}", "status": "canonical", "parent": record.urn,
             "label_en": f"{label_en} / {n}"}
        )
    return lines
