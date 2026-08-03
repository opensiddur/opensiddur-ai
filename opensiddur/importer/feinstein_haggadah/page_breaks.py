"""Hand-verified page-break data for the 1822 Heidenheim print.

``@n`` values are the foliation printed in the top outer corner of the Rödelheim edition,
running from folio 2 to folio 40. Each folio carries its number twice: as a Hebrew numeral
on the recto and as an Arabic numeral on the verso. Recto is designated ``2r``, verso ``2v``.

This is deliberately *not* the sequence number added at the foot of every page by the
HebrewBooks scan, which runs 10-88 and is an artifact of the digitisation, nor the page's
position in the scan. For the latter see :func:`facsimile_page`, which converts a folio
designation into a page of the scan so that :func:`facsimile_url` can link to it.

The table is curated by hand against the facsimile; ``align_page_breaks`` is only a rough
first pass and is not authoritative. See :func:`find_break_offset` for how a recorded break
is located in the transcription.

The facsimile is HebrewBooks #4909, ``sources/heidenheim_haggadah_1822/Hebrewbooks_org_4909.pdf``.
Its pagination and the page viewer's ``pgnum`` agree: page 1 is the title page, folio 2r is
page 3, and folio 40v is page 80, the last.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from opensiddur.importer.util.hebrew import normalize_hebrew, normalize_with_offsets

PAGE_BREAKS_FILE = Path(__file__).parent / "page_breaks_1822.json"

#: HebrewBooks catalogue id of the facsimile every page break was verified against.
HEBREWBOOKS_SEFER_ID = 4909

#: Anchor for the folio-to-scan-page mapping, counted the way the site's page viewer counts:
#: pgnum 1 is the title page and folio 2r, where the text begins, is pgnum 3. The recto/verso
#: alternation is regular from there through folio 40v, the scan's last page at pgnum 80.
FACSIMILE_FIRST_FOLIO = 2
FACSIMILE_FIRST_PAGE = 3

_FOLIO_RE = re.compile(r"^([0-9]+)([rv])$")


def facsimile_page(page: str) -> int:
    """The page of the scan showing the folio side designated by ``page``.

    This is both the page viewer's ``pgnum`` parameter and the page number of the downloaded
    PDF, which are the same for ``Hebrewbooks_org_4909.pdf``. Beware that some copies of this
    scan carry an inserted copyright page and so run one page ahead; checking a link against
    such a copy makes a correct mapping look off by one.

    ``page`` is a folio designation such as ``"5v"``. Raises :class:`ValueError` on anything
    that is not one, rather than silently producing a page number that would link to the
    wrong image.
    """
    match = _FOLIO_RE.match(page)
    if match is None:
        raise ValueError(f"not a folio designation: {page!r}")
    folio = int(match.group(1))
    if folio < FACSIMILE_FIRST_FOLIO:
        raise ValueError(f"folio {folio} precedes the start of the facsimile mapping")
    verso = match.group(2) == "v"
    return FACSIMILE_FIRST_PAGE + 2 * (folio - FACSIMILE_FIRST_FOLIO) + int(verso)


#: Last page of the scan, folio 40v. Pages 1-2 are the title page and its verso; the text
#: runs from FACSIMILE_FIRST_PAGE to here.
FACSIMILE_LAST_PAGE = 80


def folio_at_facsimile_page(page: int) -> str:
    """The folio designation shown on page ``page`` of the scan: the inverse of
    :func:`facsimile_page`.

    Raises :class:`ValueError` for the front matter and for anything past the end, which
    carry no folio.
    """
    if not FACSIMILE_FIRST_PAGE <= page <= FACSIMILE_LAST_PAGE:
        raise ValueError(f"scan page {page} is outside the foliated text")
    offset = page - FACSIMILE_FIRST_PAGE
    folio = FACSIMILE_FIRST_FOLIO + offset // 2
    return f"{folio}{'v' if offset % 2 else 'r'}"


def facsimile_url(page: str) -> str:
    """A deep link to the facsimile page showing the folio side designated by ``page``."""
    return (
        f"https://www.hebrewbooks.org/pdfpager.aspx"
        f"?req={HEBREWBOOKS_SEFER_ID}&pgnum={facsimile_page(page)}"
    )


#: Edition designator carried on every tei:pb, distinguishing the 1822 foliation from the
#: page numbering the HebrewBooks scan adds.
PAGE_EDITION = "1822"


def pb_markup(page: str) -> str:
    """Serialise one page break.

    ``@n`` is the 1822 foliation and ``@facs`` links to the same page in the facsimile the
    break was verified against, so the foliation stays citable while the digital edition
    remains linkable. This is the only place a ``tei:pb`` is written; the psalm
    transcriptions carry the markup inline and are normalised through
    :func:`normalize_pb_markup` so they cannot drift from it.
    """
    url = html.escape(facsimile_url(page), quote=True)
    return f'<tei:pb n="{page}" ed="{PAGE_EDITION}" facs="{url}"/>'


_PB_RE = re.compile(r'<tei:pb\b[^>]*\bn="([^"]+)"[^>]*/>')


def normalize_pb_markup(text: str) -> str:
    """Rewrite every ``tei:pb`` in ``text`` into the canonical serialisation.

    Hand-curated transcriptions record page breaks with ``@n`` alone; regenerating them here
    keeps the computed ``@facs`` link out of the curated data.
    """
    return _PB_RE.sub(lambda match: pb_markup(match.group(1)), text)


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

    @property
    def facsimile_page(self) -> int:
        """The page of the scan this folio side appears on, as the viewer numbers it."""
        return facsimile_page(self.page)


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
