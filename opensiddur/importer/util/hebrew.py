"""Hebrew text normalization shared by the importers.

Two different jobs live here, and confusing them causes quiet damage:

* **Storage normalization** — :func:`to_nfkd`, the form JLPTEI requires text to be
  written in. It is loss-free and belongs on every string on its way into a project
  file.
* **Comparison normalization** — :func:`normalize_hebrew` and friends, which throw away
  vowels, cantillation and punctuation to make two spellings of the same words match.
  Useful for anchoring and collation, never for anything that gets written out.
"""

from __future__ import annotations

import re
import unicodedata

#: The decomposition JLPTEI stores text in. From ``schema/JLPTEI-3.md``: "Text should be
#: stored as Unicode, UTF-8 encoded, with NFKD decomposition."
STORAGE_FORM = "NFKD"


def to_nfkd(text: str) -> str:
    """Normalize text to the decomposition JLPTEI stores.

    This does two things that matter for Hebrew, both of them loss-free:

    * **Decomposes presentation forms.** The Hebrew presentation block (U+FB1D-FB4F)
      holds precomposed letter+point pairs — vav with holam, shin with shin dot, the
      alef-lamed ligature — that a scraped source uses inconsistently. NFKD replaces
      each with its letter and mark, so one spelling reaches the file.
    * **Puts combining marks in canonical order.** Hebrew points and accents carry
      distinct combining classes, so a dagesh and a vowel typed in either order compare
      unequal until they are normalized and identical afterwards.

    What it deliberately does *not* do is fold characters that look alike but mean
    different things. Qamats (U+05B8) and qamats qatan (U+05C7) stay distinct, as do
    holam (U+05B9) and holam haser for vav (U+05BA); they are separate vowels, not
    encoding variants, and merging them would silently rewrite the text.
    """
    return unicodedata.normalize(STORAGE_FORM, text)


def is_nfkd(text: str) -> bool:
    """Whether ``text`` is already in the storage form."""
    return unicodedata.is_normalized(STORAGE_FORM, text)


def describe_normalization(text: str) -> list[str]:
    """Human-readable summary of what :func:`to_nfkd` would change, for auditing.

    Reports the distinct characters that would be rewritten rather than the positions,
    because the useful question about a source is *which* spellings it mixes, not how
    many times.
    """
    changes: dict[str, str] = {}
    for char in text:
        normalized = unicodedata.normalize(STORAGE_FORM, char)
        if normalized != char:
            changes[char] = normalized
    return [
        f"U+{ord(char):04X} {unicodedata.name(char, '?')} -> "
        + " ".join(f"U+{ord(c):04X}" for c in replacement)
        for char, replacement in sorted(changes.items())
    ]


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
