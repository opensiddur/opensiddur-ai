"""Hebrew text normalization shared by the importers."""

from __future__ import annotations

import re
import unicodedata


def strip_marks(text: str) -> str:
    """Drop combining marks (vowel points, cantillation, meteg, etc.)."""
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def normalize_hebrew(text: str) -> str:
    """Reduce text to its bare consonant skeleton.

    Everything that is not a Hebrew letter is removed: vowels, cantillation, spaces,
    punctuation, Latin characters and parenthetical editorial insertions. This makes
    comparisons insensitive to the orthographic differences between the Open Siddur
    transcription and the 1822 print.
    """
    return re.sub(r"[^א-ת]", "", strip_marks(text))


def normalize_with_offsets(text: str) -> tuple[str, list[int]]:
    """Normalize ``text`` and return the map from normalized index -> original index.

    ``offsets[i]`` is the index in ``text`` of the character that produced
    ``normalized[i]``. ``len(offsets) == len(normalized)``.
    """
    normalized: list[str] = []
    offsets: list[int] = []
    for index, char in enumerate(text):
        if unicodedata.category(char) == "Mn":
            continue
        if "א" <= char <= "ת":
            normalized.append(char)
            offsets.append(index)
    return "".join(normalized), offsets


def normalize_latin(text: str) -> str:
    """Reduce Latin-script text to letters and digits, lowercased.

    The counterpart of :func:`normalize_hebrew` for the English translation: dropping spacing,
    punctuation and case makes an anchor insensitive to the typographic quotes, line breaks
    and stray spacing the scraped source is full of.
    """
    return "".join(c for c in text.casefold() if c.isalnum())


def normalize_latin_with_offsets(text: str) -> tuple[str, list[int]]:
    """:func:`normalize_latin`, with the map from normalized index -> original index."""
    normalized: list[str] = []
    offsets: list[int] = []
    for index, char in enumerate(text):
        folded = char.casefold()
        if not folded.isalnum():
            continue
        # Case folding can expand one character into several ("ß" -> "ss"); each of them maps
        # back to the same source index, keeping offsets parallel to normalized.
        normalized.append(folded)
        offsets.extend([index] * len(folded))
    return "".join(normalized), offsets
