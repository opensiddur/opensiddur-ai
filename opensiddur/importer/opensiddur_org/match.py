"""Find the texts already in the collection that an opensiddur.org post is a version of.

A post that sets a psalm, the Birkat Hamazon or a prayer already encoded from Birnbaum must
use that text's URNs, so that it can be set beside the other versions. Three kinds of
evidence are used:

- **Hebrew incipits.** The opening words of each row of the post's Hebrew column are looked
  up in an index of the opening words of every ``@corresp`` scope in the collection's Hebrew
  projects. A row whose opening matches exactly one unit maps to it. A row that runs on into
  the next unit (its text contains that unit's opening) is left unmapped, because one row
  milestone cannot stand for two units.
- **The Bible.** A slug or title naming a psalm restricts the candidates to that chapter.
- **Registry labels.** The post's title compared with ``label_en``/``label_he`` of the
  registry's top-level prayers and poems.

Nothing here is recorded automatically except a decision there is nothing to decide: a post
with no candidate at all is given a new URN (:func:`urns.mint`). Every proposal is written
to ``output/`` and recorded in ``specs/opensiddur_org/post_urns.jsonl`` only once it has been
reviewed (``--accept``).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from opensiddur.common.constants import OUTPUT_DIRECTORY, PROJECT_DIRECTORY
from opensiddur.common.urn_registry import REGISTRY_DIRECTORY
from opensiddur.importer.opensiddur_org.convert import select_posts
from opensiddur.importer.opensiddur_org.parse_post import Post, load_post, node_text, normalize_key
from opensiddur.importer.opensiddur_org.scope import content_scope, imported_columns
from opensiddur.importer.opensiddur_org.tei_builder import row_numbers, titles_by_language
from opensiddur.importer.opensiddur_org.urns import (
    POST_URNS_PATH,
    TEXT_PREFIX,
    PostUrns,
    load_post_urns,
    mint,
    save_post_urns,
)
from opensiddur.importer.util.hebrew import normalize_hebrew
from opensiddur.importer.util.pages import opensiddur_org_data_directory

logger = logging.getLogger(__name__)

TEI = "http://www.tei-c.org/ns/1.0"
INCIPIT_WORDS = 6
#: Words collected after each scope opens: an incipit, and as much again after a blessing
#: formula.
COLLECTED_WORDS = 16
#: After a blessing formula, the words that tell the blessings apart, and the shorter key
#: tried when there are fewer (``להדליק נר`` opens three blessings; ``של חנוכה`` decides).
AFTER_FORMULA_WORDS = (10, INCIPIT_WORDS)
MIN_AFTER_FORMULA_WORDS = 3
#: A shorter opening is used only when it is unique: four words are often a formula
#: ("ברוך אתה ה׳ אלהינו") that opens dozens of blessings.
SHORT_INCIPIT_WORDS = 4
#: Only texts are candidates: a ``siddur:`` URN is a position in a book, not a text.
INDEXED_NAMESPACES = ("prayer:", "poem:", "bible:")
#: Share of a post's rows (and at least two) that must map for an incipit match to be proposed
#: on its own, without a title or slug to support it.
MIN_MAPPED_SHARE = 0.5
PROPOSALS_PATH = OUTPUT_DIRECTORY / "opensiddur_org_urn_proposals.jsonl"
HEBREW_LANGUAGES = ("he", "arc", "jpa", "tmr")


#: Spellings of the Tetragrammaton, as consonant skeletons: written out, abbreviated, or
#: substituted. They are made one word so that a blessing's opening formula is recognised as
#: the formula whichever spelling a source uses, rather than as a unique opening.
DIVINE_NAME_SPELLINGS = frozenset({"יהוה", "יי", "ייי", "ה", "יקוק", "ידוד", "השם"})


def _key_word(skeleton: str) -> str:
    """A word as compared: the divine name made one spelling, and every ו and י after the
    first letter dropped, so that full and defective spellings (כרות, כרת) agree."""
    if skeleton in DIVINE_NAME_SPELLINGS:
        return "יהוה"
    return skeleton[:1] + skeleton[1:].replace("ו", "").replace("י", "")


def _words(text: str) -> list[str]:
    return [_key_word(w) for w in (normalize_hebrew(word) for word in text.split()) if w]


#: The opening every blessing shares. A blessing is told apart by what follows it.
BLESSING_FORMULA = tuple(_words("ברוך אתה יהוה אלהינו מלך העולם"))
_AFTER_FORMULA = "§"


def _keys(words: list[str]) -> list[tuple[str, ...]]:
    """The keys an opening is indexed and looked up by, most specific first: the words after a
    blessing formula, then the incipit."""
    keys: list[tuple[str, ...]] = []
    n = len(BLESSING_FORMULA)
    if tuple(words[:n]) == BLESSING_FORMULA:
        rest = words[n:]
        lengths = [length for length in AFTER_FORMULA_WORDS if len(rest) >= length]
        if not lengths and len(rest) >= MIN_AFTER_FORMULA_WORDS:
            lengths = [len(rest)]  # a short blessing: all of it (שהחינו וקימנו והגיענו לזמן הזה)
        keys.extend((_AFTER_FORMULA, *rest[:length]) for length in lengths)
    keys.append(tuple(words[:INCIPIT_WORDS]))
    return keys


@dataclass
class IncipitIndex:
    """Opening words of every ``@corresp`` scope in the collection's Hebrew projects."""

    by_incipit: dict[tuple[str, ...], set[str]] = field(default_factory=dict)
    incipit_of: dict[str, tuple[str, ...]] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)

    def add(self, urn: str, words: list[str]) -> None:
        if len(words) < SHORT_INCIPIT_WORDS or urn in self.incipit_of:
            return
        if not urn[len(TEXT_PREFIX):].startswith(INDEXED_NAMESPACES):
            return
        self.incipit_of[urn] = tuple(words[:COLLECTED_WORDS])
        for key in _keys(words):
            self.by_incipit.setdefault(key, set()).add(urn)
        key = tuple(words[:INCIPIT_WORDS])
        if len(key) > SHORT_INCIPIT_WORDS:
            self.by_incipit.setdefault(key[:SHORT_INCIPIT_WORDS], set()).add(urn)
        self.children.setdefault(_parent(urn), []).append(urn)

    def lookup(self, words: list[str]) -> set[str]:
        for key in _keys(words):
            if len(key) >= SHORT_INCIPIT_WORDS:
                found = self.by_incipit.get(key, set())
                if found:
                    return self._longest_opening(found, words)
        if len(words) >= SHORT_INCIPIT_WORDS:
            found = self.by_incipit.get(tuple(words[:SHORT_INCIPIT_WORDS]), set())
            if len(found) == 1:
                return found
        return set()

    def _longest_opening(self, found: set[str], words: list[str]) -> set[str]:
        """Of several candidates, the one whose opening goes on agreeing with ``words``
        longest, when one does. A text and its first part open alike; the part is kept,
        because what is matched is a row, a part of a post."""
        found = {urn for urn in found if not any(other.startswith(urn + "/") for other in found)}
        if len(found) < 2:
            return found

        def agreement(urn: str) -> int:
            count = 0
            for a, b in zip(self.incipit_of[urn], words):
                if a != b:
                    break
                count += 1
            return count

        ranked = sorted(found, key=agreement, reverse=True)
        if agreement(ranked[0]) > agreement(ranked[1]):
            return {ranked[0]}
        return found

    def to_json(self) -> dict[str, list[str]]:
        return {urn: list(words) for urn, words in sorted(self.incipit_of.items())}

    @classmethod
    def from_json(cls, data: dict[str, list[str]]) -> "IncipitIndex":
        index = cls()
        for urn, words in data.items():
            index.add(urn, words)
        return index


def index_document(index: IncipitIndex, root: etree._Element) -> None:
    """Add the opening words of each ``@corresp`` scope in one document."""
    pending: list[tuple[str, list[str]]] = []

    def feed(text: str | None) -> None:
        if not text or not pending:
            return
        words = _words(text)
        if not words:
            return
        still: list[tuple[str, list[str]]] = []
        for urn, collected in pending:
            collected.extend(words)
            if len(collected) >= COLLECTED_WORDS:
                index.add(urn, collected)
            else:
                still.append((urn, collected))
        pending[:] = still

    def flush() -> None:
        # A scope shorter than a full incipit still has an opening.
        for urn, collected in pending:
            index.add(urn, collected)
        pending.clear()

    def walk(element: etree._Element) -> None:
        if not isinstance(element.tag, str):
            feed(element.tail)
            return
        local = etree.QName(element).localname
        if local in ("teiHeader", "standOff", "note"):
            feed(element.tail)
            return
        corresp = element.get("corresp", "")
        if corresp.startswith(TEXT_PREFIX):
            pending.append((corresp.split("@", 1)[0], []))
        feed(element.text)
        for child in element:
            walk(child)
        feed(element.tail)

    walk(root)
    flush()


def build_incipit_index(project_directory: Path = PROJECT_DIRECTORY) -> IncipitIndex:
    index = IncipitIndex()
    for project in sorted(p for p in project_directory.iterdir() if p.is_dir()):
        if project.name.startswith("osp-"):
            continue
        index_file = project / "index.xml"
        if not index_file.exists():
            continue
        lang = etree.parse(str(index_file)).getroot().get("{http://www.w3.org/XML/1998/namespace}lang", "")
        if lang.split("-")[0] not in HEBREW_LANGUAGES:
            continue
        for xml_file in sorted(project.glob("*.xml")):
            index_document(index, etree.parse(str(xml_file)).getroot())
    return index


def load_incipit_index(cache: Path, project_directory: Path = PROJECT_DIRECTORY) -> IncipitIndex:
    """The index, from ``cache`` when no project file is newer than it."""
    newest = max(
        (f.stat().st_mtime for f in project_directory.glob("*/*.xml") if not f.parent.name.startswith("osp-")),
        default=0.0,
    )
    if cache.exists() and cache.stat().st_mtime >= newest:
        return IncipitIndex.from_json(json.loads(cache.read_text(encoding="utf-8")))
    index = build_incipit_index(project_directory)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(index.to_json(), ensure_ascii=False), encoding="utf-8")
    return index


# --------------------------------------------------------------------------------------------
# Proposals
# --------------------------------------------------------------------------------------------


@dataclass
class Proposal:
    """Existing URNs for a post. ``urn`` is None when the rows match texts that share no
    parent: the post then gets a new URN of its own, with those rows mapped to the texts."""

    post_id: int
    urn: str | None
    rows: dict[int, str | None]
    evidence: list[str]

    def to_json(self) -> str:
        return json.dumps(
            {"post_id": self.post_id, "urn": self.urn,
             "rows": {str(n): u for n, u in sorted(self.rows.items())}, "evidence": self.evidence},
            ensure_ascii=False,
        )

    def as_post_urns(self, new_urn: PostUrns) -> PostUrns:
        """The record this proposal stands for, given the URN the post would be minted."""
        if self.urn is None:
            rows = {n: u for n, u in self.rows.items() if u}
            return PostUrns(post_id=self.post_id, kind="new", urn=new_urn.urn, rows=rows)
        return PostUrns(post_id=self.post_id, kind="existing", urn=self.urn, rows=dict(self.rows))


def _parent(urn: str) -> str:
    """The URN one level up, or "" for a top-level text."""
    return urn.rsplit("/", 1)[0] if "/" in urn.split(":", 3)[-1] else ""


def _common_prefix(urns: list[str]) -> str:
    split = [u.split("/") for u in urns]
    prefix: list[str] = []
    for parts in zip(*split):
        if len(set(parts)) != 1:
            break
        prefix.append(parts[0])
    return "/".join(prefix)


_PSALM_RE = re.compile(r"\bpsalms?[-\s]+0*(\d{1,3})\b", re.IGNORECASE)


def bible_hint(post: Post) -> str | None:
    for text in (post.slug, post.title):
        match = _PSALM_RE.search(text)
        if match:
            return f"{TEXT_PREFIX}bible:psalms/{int(match.group(1))}"
    return None


def label_matches(post: Post, labels: dict[str, set[str]]) -> set[str]:
    found: set[str] = set()
    for _lang, title in titles_by_language(post):
        found |= labels.get(normalize_key(title), set())
    return found


def registry_labels(registry_directory: Path = REGISTRY_DIRECTORY) -> dict[str, set[str]]:
    """Normalized label -> top-level prayer and poem URNs."""
    labels: dict[str, set[str]] = {}
    for name in ("prayer.jsonl", "poem.jsonl"):
        path = registry_directory / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("parent") or record.get("status") != "canonical":
                continue
            for key in ("label_en", "label_he"):
                if record.get(key):
                    labels.setdefault(normalize_key(record[key]), set()).add(record["urn"])
    return labels


def _hebrew_column(post: Post) -> int | None:
    for index, column in imported_columns(post):
        if column.lang.split("-")[0] in HEBREW_LANGUAGES:
            return index
    return None


def propose(post: Post, index: IncipitIndex, labels: dict[str, set[str]]) -> Proposal | None:
    numbers = row_numbers(post)
    hint = bible_hint(post)
    evidence: list[str] = []
    rows: dict[int, str | None] = {n: None for n in numbers.values()}
    candidates_by_row: dict[int, set[str]] = {}

    column = _hebrew_column(post)
    if column is not None:
        for row_index, n in numbers.items():
            cell = post.rows[row_index].cells[column]
            text = " ".join(node_text(line) for block in cell.blocks for line in block.lines)
            candidates = index.lookup(_words(text))
            if hint:
                candidates = {c for c in candidates if c.startswith(hint + "/")}
            if candidates:
                candidates_by_row[n] = candidates

    # The work the unambiguous rows point into decides between ambiguous candidates; an
    # ambiguous row is mapped only when exactly one of its candidates is in that work.
    parents = Counter(
        _parent(next(iter(c))) for c in candidates_by_row.values() if len(c) == 1 and _parent(next(iter(c)))
    )
    dominant = parents.most_common(1)[0][0] if parents else None
    for n, candidates in candidates_by_row.items():
        if len(candidates) == 1:
            rows[n] = next(iter(candidates))
        elif dominant:
            in_work = [c for c in candidates if _parent(c) == dominant]
            if len(in_work) == 1:
                rows[n] = in_work[0]
    _unmap_rows_running_on(post, column, numbers, rows, index)
    # One URN marks one place in a document: a repeat (a refrain, the reader's repetition)
    # would be dropped by refdb with a warning, so only its first row keeps it.
    used: set[str] = set()
    for n in sorted(rows):
        if rows[n] in used:
            rows[n] = None
        elif rows[n]:
            used.add(rows[n])

    mapped = [u for u in rows.values() if u]
    # The post is the work its rows are parts of, never one of the rows.
    top = hint or (_common_prefix([_parent(u) for u in mapped]) if mapped else "")
    if mapped:
        evidence.append(f"{len(mapped)} of {len(rows)} row(s) open like a unit under {top or 'several texts'}")
    labelled = label_matches(post, labels)
    if labelled:
        evidence.append("title matches the registry label of " + ", ".join(sorted(labelled)))
        if not top:
            top = sorted(labelled)[0]
    if hint:
        evidence.insert(0, f"slug or title names {hint.rsplit(':', 1)[-1]}")
    if not mapped and not (hint or labelled):
        return None
    if not top or top.endswith(":") or top == TEXT_PREFIX.rstrip(":"):
        # The rows open texts that share no parent: a new post made of existing parts.
        evidence.append("the mapped rows belong to different texts; the post would be new")
        return Proposal(post.post_id, None, rows, evidence)
    if not (hint or labelled) and len(mapped) < max(2, MIN_MAPPED_SHARE * len(rows)):
        evidence.append("too few rows map for the post to be that text; the post would be new")
        return Proposal(post.post_id, None, rows, evidence)
    return Proposal(post.post_id, top, rows, evidence)


def _unmap_rows_running_on(
    post: Post, column: int | None, numbers: dict[int, int], rows: dict[int, str | None], index: IncipitIndex
) -> None:
    """Unmap a row whose text runs on into another unit of the same work."""
    if column is None:
        return
    for row_index, n in numbers.items():
        urn = rows.get(n)
        if not urn:
            continue
        cell = post.rows[row_index].cells[column]
        skeleton = "".join(_words(" ".join(node_text(line) for b in cell.blocks for line in b.lines)))
        rest = skeleton[len("".join(index.incipit_of[urn][:INCIPIT_WORDS])):]
        for other in index.children.get(_parent(urn), []):
            if other != urn and "".join(index.incipit_of[other][:INCIPIT_WORDS]) in rest:
                rows[n] = None
                break


# --------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------


def taken_urns(registry_directory: Path, records: dict[int, PostUrns]) -> set[str]:
    taken = {record.urn for record in records.values()}
    for path in registry_directory.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                taken.add(json.loads(line)["urn"])
    return taken


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--post", type=int, action="append")
    parser.add_argument("--category", type=int, action="append")
    parser.add_argument("--sourcetexts-root", type=Path, default=None)
    parser.add_argument("--project-directory", type=Path, default=PROJECT_DIRECTORY)
    parser.add_argument("--accept", type=int, action="append", default=[],
                        help="record the reviewed proposal for this post; repeatable")
    parser.add_argument("--new", type=int, action="append", default=[],
                        help="reject the proposal for this post and give it a new URN; repeatable")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    data_dir = opensiddur_org_data_directory(args.sourcetexts_root)
    records = load_post_urns()
    proposals: dict[int, Proposal] = {}
    if PROPOSALS_PATH.exists():
        for line in PROPOSALS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                proposals[int(data["post_id"])] = Proposal(
                    int(data["post_id"]), data["urn"],
                    {int(n): u for n, u in data["rows"].items()}, data["evidence"])
    taken = taken_urns(REGISTRY_DIRECTORY, records)

    for post_id in args.accept:
        post = load_post(data_dir / "posts" / f"{post_id}.json")
        records[post_id] = proposals.pop(post_id).as_post_urns(mint(post.post_id, post.slug, post.tags, taken))
        taken.add(records[post_id].urn)
    for post_id in args.new:
        post = load_post(data_dir / "posts" / f"{post_id}.json")
        proposals.pop(post_id, None)
        records[post_id] = mint(post.post_id, post.slug, post.tags, taken)
        taken.add(records[post_id].urn)

    index = load_incipit_index(OUTPUT_DIRECTORY / "opensiddur_org_incipits.json", args.project_directory)
    labels = registry_labels()
    minted = 0
    for post_id in select_posts(data_dir, posts=args.post, categories=args.category):
        if post_id in records:
            continue
        post = load_post(data_dir / "posts" / f"{post_id}.json")
        if not content_scope(post).in_scope:
            continue
        proposal = propose(post, index, labels)
        if proposal is None:
            records[post_id] = mint(post.post_id, post.slug, post.tags, taken)
            taken.add(records[post_id].urn)
            minted += 1
        else:
            proposals[post_id] = proposal

    save_post_urns(records, POST_URNS_PATH)
    PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROPOSALS_PATH.write_text("".join(proposals[k].to_json() + "\n" for k in sorted(proposals)), encoding="utf-8")
    print(f"Minted {minted} new URN(s); {len(proposals)} proposal(s) awaiting review in {PROPOSALS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
