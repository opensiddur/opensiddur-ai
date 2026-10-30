"""Project identifiers for posts: ``<title>-<author>-<date>-<lang>`` (``specs/NAMING_SCHEME.md``).

A post is named by what it is, not by its number on the site:

- ``title``: the Latin-script part of the post's title, up to the first comma or "by", with
  anything in brackets left out, folded to ASCII. A post that romanizes its own name keeps its
  romanization; only the style guide's diacritics are mapped onto the table's digraphs. A post
  whose title has no Latin part is named from its slug.
- ``author``: whoever made this column what it is. A translation is its translator's, and has
  no author when its translator is unknown; any other column is the original author's. The
  credits do not always say which is which -- a translator who has died is credited as an
  author, and so is a congregation -- so the title's "by" settles it where it names one of
  them: "... by Penina Moïse", "trans. by Frederick de Sola Mendes". A name with a patronymic
  or a place (``Yosef ben Shlomo of Carcassonne``) is given by its first name, any other by
  its surname.
- ``date``: the year of the original work, else of the post. A translation has none: when it
  was made is rarely recorded, and the post's date would say something false.
- ``lang``: the column's language.

Two posts that would share an identifier are told apart by their post IDs, added before the
language. The older post, by ID, keeps the plain identifier, so adding a post never renames an
older one. A post's projects are found again by the post ID in their ``index.xml``, not by
their names.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lxml import etree

from opensiddur.common.validate_names import PROJECT_ID_RE
from opensiddur.importer.opensiddur_org.contributors import PLACEHOLDER_SLUGS, role_key
from opensiddur.importer.opensiddur_org.parse_post import Column, Post

#: The longest a title field may be, cut back to a whole word.
TITLE_LENGTH = 60

#: The style guide's romanization, onto the table's (schema/JLPTEI-3.md#transliteration).
#: Letters the table writes without a diacritic lose theirs when folded.
_LETTERS = {
    "ḥ": "ch", "Ḥ": "ch", "ẓ": "tz", "Ẓ": "tz", "ƙ": "kh", "Ƙ": "kh", "š": "sh", "Š": "sh",
    "ḳ": "q", "Ḳ": "q", "ḇ": "v", "þ": "t", "Þ": "t", "ʝ": "j", "Ʝ": "j", "ß": "ss",
    "æ": "ae", "Æ": "ae", "ø": "o", "Ø": "o", "ł": "l", "Ł": "l",
}
#: Marks for an aleph or an ayin, and apostrophes, which the table does not write.
_DROPPED = "ʼʾʿ'’‘`ʻȝȜŋŊ"

_BRACKETED = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")
_TITLE_END = re.compile(r",|\s(?:by|von|par|por)\s|\s[–—]\s", re.IGNORECASE)

#: Words before a name that are not part of it.
_HONORIFICS = frozenset({
    "rabbi", "rabbis", "rebbe", "reb", "r", "rav", "kohenet", "cantor", "hazzan", "chazzan",
    "dr", "rev", "phd", "ph", "d", "mr", "mrs", "ms",
})
#: Words that make a name a patronymic or an epithet, so that its first word names the person.
_PATRONYMIC = frozenset({"ben", "bar", "bat", "b", "of", "ha", "halevi", "hakohen"})

#: "by" and who follows it, up to a comma or a bracket; and whether a translation is meant.
_BY = re.compile(r"(?P<pre>[\w.]+\s+)?\bby\s+(?P<who>[^,()\[\];|]+)", re.IGNORECASE)
_TRANSLATED = re.compile(r"trans|adapt|interpret|render", re.IGNORECASE)

TRANSLATION_ROLES = frozenset({"translation", "adaptation"})


def fold(text: str) -> list[str]:
    """``text``'s words in the identifier alphabet: lowercase ASCII letters and digits."""
    # Composed first: the post's text arrives decomposed, Ḥ as H and a combining dot.
    text = unicodedata.normalize("NFC", text)
    for letter, replacement in _LETTERS.items():
        text = text.replace(letter, replacement)
    text = "".join(c for c in text if c not in _DROPPED)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", text.lower())


def _joined(words: list[str], limit: int | None = None) -> str:
    field = "_".join(words)
    if limit is not None and len(field) > limit:
        field = field[: limit + 1].rsplit("_", 1)[0] if "_" in field[:limit] else field[:limit]
    return field


def latin_title(post: Post) -> str | None:
    """The part of the post's title written in Latin letters, if any."""
    from opensiddur.importer.opensiddur_org.tei_builder import titles_by_language

    return next((title for lang, title in titles_by_language(post) if lang == "en"), None)


def title_field(post: Post) -> str:
    title = latin_title(post)
    if title is not None:
        name = _BRACKETED.sub(" ", title)
        name = _TITLE_END.split(name, 1)[0]
        words = fold(name) or fold(title)
    else:
        words = []
    if not words:
        # The site's slug is already romanized; its attribution starts at "by".
        slug = re.split(r"-by-", post.slug, 1)[0]
        words = fold(slug.replace("-", " ")) or ["post"]
    return _joined(words, TITLE_LENGTH)


def name_field(name: str) -> str:
    """The word(s) that name a person in an identifier: a surname, or a first name."""
    words = [w for w in re.split(r"\s+", re.sub(r"[.,]", " ", name).replace("'", " ")) if w]
    words = [w for w in words if w.lower() not in _HONORIFICS]
    if not words:
        return ""
    parts = {part.lower() for w in words for part in [w, *w.split("-")]}
    chosen = words[0] if len(words) > 1 and parts & _PATRONYMIC else words[-1]
    return _joined(fold(chosen))


def _named(post: Post) -> tuple[list[str], list[str]]:
    """The people the post credits: (translators, everyone credited with no role)."""
    translators: list[str] = []
    others: list[str] = []
    for coauthor in post.coauthors:
        if coauthor.name.lower() in PLACEHOLDER_SLUGS or coauthor.profile_slug in PLACEHOLDER_SLUGS:
            continue
        role = role_key(coauthor.qualifier)
        if role is None:
            others.append(coauthor.name)
        elif role[0] == "trl":
            translators.append(coauthor.name)
    return translators, others


def _attributions(post: Post) -> tuple[list[set[str]], list[set[str]]]:
    """The words of each name the title gives after "by": (as translator, as author)."""
    translated: list[set[str]] = []
    authored: list[set[str]] = []
    for match in _BY.finditer(latin_title(post) or ""):
        words = set(fold(match.group("who")))
        (translated if _TRANSLATED.search(match.group("pre") or "") else authored).append(words)
    return translated, authored


def _in(name: str, attributions: list[set[str]]) -> bool:
    words = set(fold(name_field(name).replace("_", " ")))
    return bool(words) and any(words <= named for named in attributions)


def author_field(post: Post, column: Column) -> str:
    translators, others = _named(post)
    translated, authored = _attributions(post)
    if column.role in TRANSLATION_ROLES:
        chosen = ([n for n in translators if _in(n, translated + authored)][:1] or translators[:1]
                  or [n for n in others if _in(n, translated)][:1])
    else:
        originals = [n for n in others if n not in translators and not _in(n, translated)]
        chosen = [n for n in originals if _in(n, authored)][:1] or originals[:1]
    return name_field(chosen[0]) if chosen else ""


def _year(date: str) -> str:
    """``1240-00-00`` -> ``1240``; ``-0515-00-00`` -> ``515bce``; nothing for no year."""
    match = re.match(r"^(-?)0*(\d+)", date or "")
    if not match or match.group(2) == "0":
        return ""
    return f"{match.group(2)}bce" if match.group(1) else match.group(2)


def date_field(post: Post, column: Column) -> str:
    if column.role in TRANSLATION_ROLES:
        return ""
    return _year(post.date_src_start) or _year(post.date)


def base_project_id(post: Post, column: Column) -> str:
    fields = [title_field(post), author_field(post, column), date_field(post, column)]
    return "-".join(f for f in fields if f)


@dataclass(frozen=True)
class Candidate:
    """One column of one post that will be a project."""

    post: Post
    column: Column


def assign_project_ids(candidates: Iterable[Candidate], taken: Iterable[str] = ()) -> dict[tuple[int, str], str]:
    """Each candidate's project identifier, keyed by ``(post_id, lang)``.

    ``taken`` are identifiers already in use by projects no post made. A candidate whose plain
    identifier is taken -- by them, or by a post with a lower ID -- adds its post ID.
    """
    used = set(taken)
    ids: dict[tuple[int, str], str] = {}
    for candidate in sorted(candidates, key=lambda c: (c.post.post_id, c.column.lang)):
        lang = candidate.column.lang.lower()
        base = base_project_id(candidate.post, candidate.column)
        pid = f"{base}-{lang}"
        if pid in used:
            pid = f"{base}-{candidate.post.post_id}-{lang}"
        if not PROJECT_ID_RE.match(pid):
            raise ValueError(f"post {candidate.post.post_id}: {pid!r} is not a project identifier")
        used.add(pid)
        ids[(candidate.post.post_id, candidate.column.lang)] = pid
    return ids


def imported_projects(project_directory: Path) -> dict[int, list[Path]]:
    """The projects converted from posts, by post ID, read from each ``index.xml``."""
    found: dict[int, list[Path]] = {}
    for index in sorted(Path(project_directory).glob("*/index.xml")):
        try:
            root = etree.parse(str(index)).getroot()
        except etree.XMLSyntaxError:
            continue
        ids = root.xpath(
            "/tei:TEI/tei:teiHeader//tei:idno[@type='opensiddur.org']/text()",
            namespaces={"tei": "http://www.tei-c.org/ns/1.0"},
        )
        if ids and ids[0].strip().isdigit():
            found.setdefault(int(ids[0].strip()), []).append(index.parent)
    return found
