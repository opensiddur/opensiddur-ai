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
