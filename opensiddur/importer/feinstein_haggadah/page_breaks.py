"""Hand-verified page-break data for the 1822 Heidenheim print.

``@n`` values are the foliation printed in the top outer corner of the Rödelheim edition,
running from folio 2 to folio 40. Each folio carries its number twice: as a Hebrew numeral
on the recto and as an Arabic numeral on the verso. Recto is designated ``2r``, verso ``2v``.

This is deliberately *not* the sequence number added at the foot of every page by the
HebrewBooks scan (#21779), which runs 10-88 and is an artifact of the digitisation.

The table is curated by hand against the facsimile; ``align_page_breaks`` is only a rough
first pass and is not authoritative. See :func:`find_break_offset` for how a recorded break
is located in the transcription.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from opensiddur.importer.util.hebrew import normalize_hebrew, normalize_with_offsets

PAGE_BREAKS_FILE = Path(__file__).parent / "page_breaks_1822.json"


class PageBreakError(ValueError):
    """A curated page break could not be located unambiguously in the text."""


@dataclass(frozen=True)
class PageBreak:
    """One page of the 1822 print.

    ``page`` is the folio designation (``"5r"``). ``section`` is the slug of the section the
    page turn falls inside. ``before_text``/``after_text`` are the words on either side of
    the turn; when both are ``None`` the page opens at the very start of the section.
    """

    page: str
    section: str
    before_text: str | None = None
    after_text: str | None = None

    @property
    def at_section_start(self) -> bool:
        return self.before_text is None and self.after_text is None


def _load(path: Path | None = None) -> dict:
    return json.loads((path or PAGE_BREAKS_FILE).read_text(encoding="utf-8"))


def load_page_breaks(path: Path | None = None) -> list[PageBreak]:
    """Load the curated table, in book order."""
    return [
        PageBreak(
            page=entry["page"],
            section=entry["section"],
            before_text=entry.get("before_text"),
            after_text=entry.get("after_text"),
        )
        for entry in _load(path)["pages"]
    ]


def load_section_ranges(path: Path | None = None) -> dict[str, tuple[str, str]]:
    """Explicit page ranges for sections whose content is not contiguous in the print.

    Ranges are otherwise derived from the page breaks; see the file's own comment for why
    an override is needed at all.
    """
    return {
        slug: (value["from"], value["to"])
        for slug, value in _load(path).get("section_ranges", {}).items()
    }


def page_breaks_by_section(
    breaks: list[PageBreak] | None = None,
) -> dict[str, list[PageBreak]]:
    """Group the table by section slug, preserving book order within each section."""
    grouped: dict[str, list[PageBreak]] = {}
    for entry in breaks if breaks is not None else load_page_breaks():
        grouped.setdefault(entry.section, []).append(entry)
    return grouped


def find_break_offset(text: str, before_text: str, after_text: str) -> int:
    """Return the offset in ``text`` where ``before_text`` ends and ``after_text`` begins.

    Matching is on the consonant skeleton, so the recorded anchors may be written without
    vowels or cantillation and need not reproduce the transcription's punctuation.

    Raises :class:`PageBreakError` rather than guessing: a break that cannot be pinned to
    exactly one position means the curated table and the text have diverged, and that must
    stop the conversion instead of silently landing in the wrong place.
    """
    normalized, offsets = normalize_with_offsets(text)
    before = normalize_hebrew(before_text)
    after = normalize_hebrew(after_text)
    if not before or not after:
        raise PageBreakError("before_text and after_text must each contain Hebrew letters")

    needle = before + after
    first = normalized.find(needle)
    if first < 0:
        # Report which side is at fault; that is what tells the curator how to fix it.
        found_before = normalized.find(before) >= 0
        found_after = normalized.find(after) >= 0
        if found_before and found_after:
            raise PageBreakError(
                f"{before_text!r} and {after_text!r} both occur but are not adjacent"
            )
        missing = "after_text" if found_before else "before_text"
        if not found_before and not found_after:
            missing = "before_text and after_text"
        raise PageBreakError(f"{missing} not found in the text")
    if normalized.find(needle, first + 1) >= 0:
        raise PageBreakError(
            f"{before_text!r} + {after_text!r} occurs more than once; lengthen the anchor"
        )

    return offsets[first + len(before)]
