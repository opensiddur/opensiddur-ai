# -*- coding: utf-8 -*-
"""Resolve the Hebrew Wikisource foundation text to the reading *this* book prints.

The Wikisource edition is not a reproduction of the 1949 print: it renders Birnbaum's
English rubrics into Hebrew, adds Eretz Yisrael customs, and corrects the text. Where its
editors knew the print differs from what they set, they said so in a `{{נוסח}}` template
rather than silently choosing -- so the template is the most useful thing in the file, and
stripping it throws away exactly the evidence the comparison is for.

Four conventions are in use, and one of them inverts:

    {{נוסח|X|בירנבוים=Y}}                 X is the default, Y is what Birnbaum prints
    {{נוסח|X|=מסורה|בירנבוים=Y}}           X is the Masorah's, Y is what Birnbaum prints
    {{נוסח|X|=בירנבוים|אחרים=Y}}           *X* is what Birnbaum prints, Y is everyone else
    {{נוסח|X|=בירנבוים ועבו"י|אחרים=Y}}     likewise, X, shared with another edition

So a `בירנבוים=` parameter cannot simply be preferred: where the unnamed attribution
already credits the first positional to Birnbaum, that positional is the reading and
`אחרים=` is the variant to discard.

A `בירנבוים=` value is not always a reading. One in the morning blessings is a sentence
about how he sets two Torah portions, with no word to substitute. A value that does not
look like a short run of pointed Hebrew is treated as a comment: the positional stands,
and the comment is reported so the reading can record it.
"""
import re
from dataclasses import dataclass, field

#: The template, and the attribution that names Birnbaum rather than contrasting with him.
TEMPLATE = re.compile(r"\{\{נוסח\|(.*?)\}\}", re.S)
BIRNBAUM = "בירנבוים"

#: A value is a reading if it is short and made of Hebrew letters, points and separators.
READING = re.compile(r"^[֐-׿‏\s/\[\]|,.;׳״־-]+$")
MAX_READING_WORDS = 4


@dataclass
class Resolution:
    """The resolved text, and what was set aside to get it."""
    text: str
    comments: list[str] = field(default_factory=list)
    substitutions: list[tuple[str, str]] = field(default_factory=list)


def _split_params(body: str) -> tuple[str, dict[str, str], str]:
    """A template body into its first positional, its named parameters, and the
    unnamed attribution written as a bare `=value`."""
    parts = body.split("|")
    positional = parts[0].strip()
    named: dict[str, str] = {}
    attribution = ""
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key, value = key.strip(), value.strip()
        if not key:
            attribution = value
        else:
            named[key] = value
    return positional, named, attribution


def _is_reading(value: str, positional: str = "") -> bool:
    """Whether a parameter is a variant reading or a note about one.

    A variant replaces the text it is given against, so it is about as long. The word
    cap alone is not enough: a four-word Hebrew sentence saying a full stop is missing
    passed it, and was substituted into the middle of a blessing as though the print
    said it.
    """
    if not value or not READING.match(value):
        return False
    if len(value.split()) > MAX_READING_WORDS:
        return False
    if positional and len(value.split()) > len(positional.split()) + 1:
        return False
    return True


def resolve(text: str) -> Resolution:
    """Replace every `{{נוסח}}` with the reading the 1949 print carries."""
    result = Resolution(text="")
    def _one(match: re.Match) -> str:
        positional, named, attribution = _split_params(match.group(1))
        # The attribution credits the positional to Birnbaum: it is already the reading.
        if BIRNBAUM in attribution:
            return positional
        value = named.get(BIRNBAUM)
        if value is None:
            return positional
        if not _is_reading(value, positional):
            result.comments.append(value)
            return positional
        if value != positional:
            result.substitutions.append((positional, value))
        return value
    result.text = TEMPLATE.sub(_one, text)
    return result


def strip_markup(text: str) -> str:
    """What is left after the variants are resolved: plain pointed Hebrew.

    `compare` tokenises whatever it is given and would count a stray brace as a word, so
    nothing may survive here but the text and its separators.
    """
    # Removed markup leaves a space, never nothing. A `<קטע סוף=.../>` between two words
    # is a boundary, and deleting it outright joins them into one token -- which `compare`
    # then reports as two consonantal differences, and the misalignment cascades through
    # everything after it. One missing space produced twenty-five phantom differences on
    # printed page 11 before this was found.
    text = re.sub(r"\{\{#קטע:[^}]*\}\}", " ", text)
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"'{2,}", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def section(page_text: str, name: str) -> str | None:
    """One named `<קטע>` span out of a foundation page."""
    m = re.search(r"<קטע התחלה=" + re.escape(name) + r"/>(.*?)<קטע סוף=", page_text, re.S)
    return m.group(1) if m else None
