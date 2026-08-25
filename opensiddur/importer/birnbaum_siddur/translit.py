"""Transliterate vocalised Hebrew into the Latin names URNs use.

The scheme is the table in ``schema/JLPTEI-3.md``, under "URNs and linkages". It is a
naming convention rather than a phonetic system: the point is that two people naming the
same prayer independently arrive at the same string, not that the string can be read
aloud.

**This seeds names; it does not decide them.** Where a text has a settled English
spelling that wins (``aleinu``, not ``alynu``), and the registry is the record of what a
name actually is. Output here is a proposal for review.

One genuine approximation, flagged rather than hidden: **sheva**. The table gives sheva
na as ``e`` and sheva nach as nothing, but which one a sheva is depends on rules the
pointing does not mark. :func:`transliterate` applies the ordinary heuristics and
:func:`uncertain` reports where it had to guess, so a reviewer can look at those names
rather than all of them.
"""

from __future__ import annotations

import re
import unicodedata

# Consonants. Aleph and ayin are not transliterated; the letter's effect is carried by
# the vowel that follows it.
CONSONANTS = {
    "א": "",    # alef
    "ב": "b",   # bet (vet handled by dagesh below)
    "ג": "g",
    "ד": "d",
    "ה": "h",
    "ו": "v",
    "ז": "z",
    "ח": "ch",
    "ט": "t",
    "י": "y",
    "ך": "kh", "כ": "k",   # final kaf, kaf
    "ל": "l",
    "ם": "m", "מ": "m",
    "ן": "n", "נ": "n",
    "ס": "s",
    "ע": "",    # ayin
    "ף": "f", "פ": "p",
    "ץ": "tz", "צ": "tz",
    "ק": "q",
    "ר": "r",
    "ש": "sh",  # shin; sin distinguished by its dot below
    "ת": "t",
}

# Letters whose sound the dagesh qal changes.
BEGADKEFAT_WITH_DAGESH = {"ב": "b", "כ": "k", "פ": "p"}
BEGADKEFAT_WITHOUT = {"ב": "v", "כ": "kh", "פ": "f"}

VOWELS = {
    "ַ": "a",   # patah
    "ָ": "a",   # qamats
    "ׇ": "o",   # qamats qatan -- a distinct vowel, not a qamats
    "ִ": "i",   # hiriq
    "ֶ": "e",   # segol
    "ֵ": "ay",  # tsere
    "ֹ": "o",   # holam
    "ֺ": "o",   # holam haser for vav
    "ֻ": "u",   # qubuts
    "ֲ": "a",   # hataf patah
    "ֳ": "o",   # hataf qamats
    "ֱ": "e",   # hataf segol
}

SHEVA = "ְ"
DAGESH = "ּ"
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"
MAQAF = "־"

# Long vowels: a sheva following one is normally na.
LONG_VOWELS = {"ָ", "ֵ", "ֹ", "ֺ"}

_MARKS = re.compile(r"[֑-ֽֿ֯׀׃-׆]")


def _words(text: str) -> list[str]:
    """Split into words, treating maqaf as a space and dropping cantillation."""
    text = unicodedata.normalize("NFKD", text)
    text = _MARKS.sub("", text).replace(MAQAF, " ")
    text = re.sub(r'["״׳\'()\[\].,:;!?]', "", text)
    return [w for w in re.split(r"\s+", text) if w]


def _sheva_is_na(word: str, index: int) -> tuple[bool, bool]:
    """Whether the sheva at ``index`` is vocal, and whether that was a guess.

    The ordinary rules: a sheva under the first letter of a word is na; a sheva after a
    long vowel is na; the first of two adjacent shevas is nach and the second na; a
    sheva under a letter with dagesh chazaq is na. What none of them settle is a sheva
    after a short vowel in an open syllable, which is where the guessing happens.
    """
    letters_before = sum(1 for c in word[:index] if c in CONSONANTS)
    if letters_before == 0:
        return True, False                      # under the word's first letter

    preceding = word[:index]
    previous_vowel = next((c for c in reversed(preceding) if c in VOWELS or c == SHEVA), None)
    if previous_vowel in LONG_VOWELS:
        return True, False
    if previous_vowel == SHEVA:
        return True, False                      # second of a pair
    if DAGESH in _marks_after(word, index):
        # A dagesh chazaq in the letter *carrying* the sheva makes it vocal. Looking at
        # the preceding letter instead catches the dagesh qal in an initial bet, kaf or
        # peh, which says nothing about this sheva.
        return True, False

    return False, True                          # short vowel: the ambiguous case


#: Names with a settled English spelling. The table is a fallback, not an authority:
#: nobody writes "halayl" or "hazkarat_neshamot", and a scheme that produced them would
#: be quietly ignored. Keyed on what the table produces, so the override is visible.
COMMON_SPELLINGS = {
    "halayl": "hallel",
    "hazkarat_neshamot": "yizkor",
    "alaynu": "aleinu",
    "qadish": "kaddish",
    "pirqay": "pirkei",
    "shemoneh_esrayh": "shemoneh_esreh",
    "qabalat": "kabbalat",
    "shabat": "shabbat",
    # Whole-name overrides, where the settled English is not a transliteration at all.
    "hazkarat_neshamot": "yizkor",
}


def transliterate(text: str) -> str:
    """A URN-safe Latin name for vocalised Hebrew.

    Applies :data:`COMMON_SPELLINGS` word by word, so a settled English spelling wins
    wherever the text has one.
    """
    name = _transliterate(text)[0]
    # Whole name first: some settled spellings replace the phrase, not a word in it.
    if name in COMMON_SPELLINGS:
        return COMMON_SPELLINGS[name]
    return "_".join(COMMON_SPELLINGS.get(word, word) for word in name.split("_"))


def uncertain(text: str) -> bool:
    """Whether any sheva in ``text`` had to be guessed at."""
    return _transliterate(text)[1]


def _marks_after(word: str, index: int) -> str:
    """The combining marks attached to the letter at ``index``."""
    marks = []
    for char in word[index + 1 :]:
        if char in VOWELS or char in (SHEVA, DAGESH, SHIN_DOT, SIN_DOT):
            marks.append(char)
        else:
            break
    return "".join(marks)


def _transliterate(text: str) -> tuple[str, bool]:
    out: list[str] = []
    guessed = False

    for word in _words(text):
        piece: list[str] = []
        # The last vowel emitted, so a following vav or yod can be recognised as a
        # mater lectionis rather than a consonant.
        last_vowel: str | None = None

        for index, char in enumerate(word):
            if char not in CONSONANTS:
                continue
            marks = _marks_after(word, index)
            own_vowel = next((m for m in marks if m in VOWELS), None)

            # Matres lectionis: a vav or yod that spells a vowel rather than sounding
            # as a consonant. Without this, "אָבוֹת" comes out "avvot" and "עֲמִידָה"
            # comes out "amiydah".
            if char == "ו" and own_vowel is None and SHEVA not in marks:
                if DAGESH in marks:
                    piece.append("u")           # shuruq
                    last_vowel = "u"
                    continue
                if last_vowel == "o":
                    continue                    # holam male: the holam already spoke
                piece.append("v")
                last_vowel = None
                continue
            if char == "ו" and own_vowel in ("ֹ", "ֺ"):
                # A vav carrying a holam is written the same way whether it spells the
                # previous letter's vowel or sounds as a consonant of its own. What
                # separates them is the previous letter: if it has no vowel at all the
                # vav supplies one and is silent; if it has a vowel or a sheva closing
                # its syllable, the vav is a consonant. Without the distinction
                # "מצוות" comes out "mitzot".
                previous = next(
                    (word[i] for i in range(index - 1, -1, -1)
                     if word[i] in CONSONANTS), None
                )
                if previous is not None:
                    previous_index = "".join(word).rindex(previous, 0, index)
                    previous_marks = _marks_after(word, previous_index)
                else:
                    previous_marks = ""
                # Only a vowel or a sheva shows the previous letter's syllable is
                # already supplied. A dagesh or a shin dot says nothing about it, and
                # counting them turned "שופר" into "shvofar".
                if any(m in VOWELS or m == SHEVA for m in previous_marks):
                    piece.append("v")           # consonantal vav
                piece.append("o")
                last_vowel = "o"
                continue
            if char == "י" and own_vowel is None and SHEVA not in marks:
                # Only after hiriq or tsere. A yod after a sheva is a consonant, so
                # "ויום טוב" is veyom_tov, not veom_tov.
                if last_vowel in ("i", "ay"):
                    continue                    # hiriq male / tsere male
                piece.append("y")
                last_vowel = None
                continue

            if char == "ש":
                piece.append("s" if SIN_DOT in marks else "sh")
            elif char in BEGADKEFAT_WITH_DAGESH:
                table = BEGADKEFAT_WITH_DAGESH if DAGESH in marks else BEGADKEFAT_WITHOUT
                piece.append(table[char])
            else:
                piece.append(CONSONANTS[char])

            if own_vowel is not None:
                piece.append(VOWELS[own_vowel])
                last_vowel = VOWELS[own_vowel]
            elif SHEVA in marks:
                vocal, was_guess = _sheva_is_na(word, index)
                guessed = guessed or was_guess
                if vocal:
                    piece.append("e")
                last_vowel = "e" if vocal else None
            else:
                last_vowel = None

        joined = "".join(piece)
        if joined:
            out.append(joined)

    name = "_".join(out)
    name = re.sub(r"[^a-z0-9_]", "", name.lower())
    name = re.sub(r"_+", "_", name).strip("_")
    return name, guessed
