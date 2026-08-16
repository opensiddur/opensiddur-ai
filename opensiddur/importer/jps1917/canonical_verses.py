"""Split JPS 1917's verses onto the canonical verse division.

JPS follows the common printed numbering, which reads the four short commandments of the
Decalogue as a single verse -- Exodus 20:13 and Deuteronomy 5:17. Canonically those are four
verses each, so a JPS verse milestone there would carry a URN that denotes four times as
much text as the same URN does in WLC, and the parallel compiler would pair it against only
the first of them.

JPS sets the four commandments as separate paragraphs, so the canonical boundaries are
already in the source; this pass promotes the paragraph breaks inside a merged verse to
verse boundaries. How many canonical verses a JPS verse covers comes from
:mod:`opensiddur.common.versification`, and the paragraph breaks found here must supply
exactly that many.
"""

from __future__ import annotations

from lxml import etree

from opensiddur.common.versification import (
    NUMBERING_COMMON,
    UnknownVerse,
    to_canonical,
)


class CanonicalVerseError(ValueError):
    """The paragraph breaks in the source disagree with the versification table."""


def _following_boundaries(verse: etree._Element) -> list[etree._Element]:
    """The ``p`` breaks inside this verse that have text after them.

    A break is a verse boundary only when more of the verse follows it. The break that
    closes the verse -- the one with nothing but the next verse marker after it -- is a
    paragraph boundary and nothing more, so it is excluded.
    """
    candidates: list[etree._Element] = []
    for node in verse.itersiblings():
        if node.tag == "verse":
            break
        if node.tag == "p":
            candidates.append(node)
    return [p for p in candidates if _content_follows(p)]


def _content_follows(node: etree._Element) -> bool:
    """True when text follows ``node`` before the next paragraph break or verse marker."""
    if (node.tail or "").strip():
        return True
    for sibling in node.itersiblings():
        if sibling.tag in ("p", "verse"):
            return False
        if "".join(sibling.itertext()).strip() or (sibling.tail or "").strip():
            return True
    return False


def annotate_canonical_verses(intermediate_xml: str, book: str) -> str:
    """Renumber ``verse`` markers onto canonical numbering, splitting merged verses.

    Every ``verse`` element ends up with ``@verse`` in canonical numbering and
    ``@editionVerse`` in JPS's own, so the importer can mint one canonical URN per verse and
    still show JPS's numbering.

    Args:
        intermediate_xml: the mediawiki intermediate document.
        book: the book's opensiddur slug, e.g. ``"exodus"``.

    Raises:
        CanonicalVerseError: when a verse covers several canonical verses but the source
            does not offer the right number of paragraph breaks to split it at.
    """
    root = etree.fromstring(intermediate_xml.encode("utf-8"))

    for verse in list(root.iter("verse")):
        chapter_raw, verse_raw = verse.get("chapter", ""), verse.get("verse", "")
        if not chapter_raw.isdigit() or not verse_raw.isdigit():
            continue
        chapter, edition_verse = int(chapter_raw), int(verse_raw)

        try:
            first, last = to_canonical(NUMBERING_COMMON, book, chapter, edition_verse)
        except UnknownVerse as exc:
            raise CanonicalVerseError(
                f"{book} {chapter}:{edition_verse} is in the source but not in the "
                f"versification table for {NUMBERING_COMMON!r}"
            ) from exc

        verse.set("editionVerse", str(edition_verse))
        verse.set("verse", str(first.verse))
        verse.set("chapter", str(first.chapter))
        if first.verse == last.verse:
            continue

        wanted = last.verse - first.verse
        boundaries = _following_boundaries(verse)
        if len(boundaries) != wanted:
            raise CanonicalVerseError(
                f"{book} {chapter}:{edition_verse} covers {wanted + 1} canonical verses but "
                f"the source offers {len(boundaries)} paragraph breaks inside it"
            )
        for offset, boundary in enumerate(boundaries, start=1):
            marker = etree.Element("verse")
            marker.set("chapter", str(first.chapter))
            marker.set("verse", str(first.verse + offset))
            # The continuation carries no edition number: it is the same JPS verse, so a
            # renderer showing JPS's numbering must not print a new one here.
            marker.tail = boundary.tail
            boundary.tail = None
            boundary.addnext(marker)

    return etree.tostring(root, encoding="unicode")
