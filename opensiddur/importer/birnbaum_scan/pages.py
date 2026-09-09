"""Getting one printed page of the scan onto disk, legibly.

The scan is 1541x2291 for every leaf -- that is not a derivative but the scan itself,
which ``ia/derivatives/*_scandata.xml`` states and the live JPEG headers confirm. The
488 MB PDF holds the same pixels, so there is nothing better to fetch. At that size a
qamats is a few pixels tall, which is legible only once the page has been cut up and
enlarged; hence :func:`bands`.

Two rules this module exists to keep:

**A page is fetched once.** Images land in the untracked ``output/`` directory beside
the repositories, so they survive a worktree being removed and are never committed,
and a page already there is never fetched again. Reading a unit means going back to
the same nine pages many times.

**A printed page number is not a leaf number.** ``pages.json`` is the only place that
correspondence is recorded -- printed page to scan page to leaf, plus which side of
the opening the page is and what its facing page is -- and it is read here rather than
re-derived. Printed page numbers are strings because the front matter numbers itself
in Roman numerals.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from opensiddur.common.constants import OUTPUT_DIRECTORY, SOURCETEXTS_ROOT
from opensiddur.importer.birnbaum_siddur.internet_archive import IA_IDENTIFIER
from opensiddur.importer.util.internet_archive import (
    Archive,
    connect,
    http_get,
    page_image_url,
    resolve_agent_model,
)

logger = logging.getLogger(__name__)

BOOK_DIRECTORY = SOURCETEXTS_ROOT / "birnbaum_siddur"
PAGES_JSON = BOOK_DIRECTORY / "pages.json"

# Untracked, and outside every repository, so the cache outlives a worktree.
SCAN_DIRECTORY = OUTPUT_DIRECTORY / "birnbaum_scan"
PAGE_DIRECTORY = SCAN_DIRECTORY / "pages"
BAND_DIRECTORY = SCAN_DIRECTORY / "bands"

CONTACT_EMAIL_ENV_VAR = "OPENSIDDUR_CONTACT_EMAIL"

# Prefix for addressing a leaf by scan page rather than by the number the book prints
# on it. The front matter needs it: only twelve of its twenty-five leaves are numbered,
# and the title page is not among them.
SCAN_PAGE_PREFIX = "s"

# Bands overlap so that no line of type is cut in half by a boundary: a line landing
# on the seam is whole in one of the two bands that share it.
DEFAULT_BANDS = 4
DEFAULT_OVERLAP = 0.12
DEFAULT_SCALE = 3


class ScanError(RuntimeError):
    """A page could not be located in pages.json, or could not be fetched."""


@dataclass(frozen=True)
class PageRef:
    """Where one leaf is, in every numbering that matters.

    ``printed_page`` is ``None`` for a leaf the print does not number, which is most
    of the front matter.
    """

    printed_page: str | None
    scan_page: int
    leaf: int
    side: str | None
    facing_scan_page: int | None
    facs: str

    @property
    def image_url(self) -> str:
        """The full-resolution image, as against the ``facs`` deep link.

        ``pages.json`` records the ``_medium`` URL because that is what belongs in
        ``tei:pb/@facs`` -- a link for a person to follow. Reading the page needs
        every pixel the scan has.
        """
        return page_image_url(IA_IDENTIFIER, self.leaf, size="")

    @property
    def designation(self) -> str:
        """The canonical name for this leaf: what the book prints, else the scan page.

        The cache is keyed by this rather than by whatever the caller typed, so that
        ``XI`` and ``s13`` name one file instead of fetching the same leaf twice.
        """
        if self.printed_page is not None:
            return self.printed_page
        return f"{SCAN_PAGE_PREFIX}{self.scan_page}"


def scan_page_designation(scan_page: int) -> str:
    """The token that addresses a leaf the print does not number."""
    return f"{SCAN_PAGE_PREFIX}{scan_page}"


def load_pages(pages_json: Path | None = None) -> dict[str, PageRef]:
    """Read ``pages.json`` into a table keyed by every designation a leaf answers to.

    A numbered leaf is keyed by its printed number *and* by ``s{scan page}``; a leaf
    the print does not number -- blanks, plates, the whole of the front matter before
    the Roman sequence begins -- is keyed by the scan-page token alone. Front matter
    has to be reachable somehow, and the scan page is the only number every leaf has.

    ``PageRef.designation`` is the one the cache is named after, so asking for ``XI``
    and asking for ``s13`` share a single image on disk rather than fetching twice.
    """
    path = Path(pages_json) if pages_json is not None else PAGES_JSON
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScanError(
            f"{path} is missing. The sourcetexts submodule may not be initialised: "
            "run `git submodule update --init`."
        ) from exc

    table: dict[str, PageRef] = {}
    for page in payload.get("pages", []):
        printed = page.get("printed_page")
        scan_page = page["scan_page"]
        reference = PageRef(
            printed_page=None if printed is None else str(printed),
            scan_page=scan_page,
            leaf=page["ia_leaf"],
            side=page.get("side"),
            facing_scan_page=page.get("facing_scan_page"),
            facs=page["facs"],
        )
        table[scan_page_designation(scan_page)] = reference
        if printed is not None:
            table[str(printed)] = reference
    return table


def lookup(printed_page: str | int, pages_json: Path | None = None) -> PageRef:
    """The one leaf answering to this designation, or a named failure."""
    table = load_pages(pages_json)
    key = str(printed_page)
    if key not in table:
        raise ScanError(
            f"No page of the scan answers to {key!r}. Pages are addressed by the "
            f"number the book prints on them, or as {SCAN_PAGE_PREFIX}N by scan page."
        )
    return table[key]


def image_path(designation: str | int) -> Path:
    """Where the leaf with this designation is cached."""
    return PAGE_DIRECTORY / f"{designation}.jpg"


def band_path(designation: str | int, index: int) -> Path:
    """Where one band of this leaf is written."""
    return BAND_DIRECTORY / f"{designation}_{index}.png"


def fetch(
    printed_page: str | int,
    *,
    archive: Archive | None = None,
    pages_json: Path | None = None,
    contact_email: str | None = None,
    force: bool = False,
) -> Path:
    """Put one printed page's full-resolution image on disk, and return its path.

    A page already cached is returned untouched unless ``force`` is set. Streams to
    a temporary sibling and renames, so an interrupted fetch cannot leave a truncated
    file looking like a complete one.
    """
    reference = lookup(printed_page, pages_json)
    destination = image_path(reference.designation)
    if destination.is_file() and not force:
        logger.debug("%s is already on disk", destination)
        return destination

    if archive is None:
        email = contact_email or os.environ.get(CONTACT_EMAIL_ENV_VAR, "").strip()
        if not email:
            raise ScanError(
                "Fetching from archive.org needs a reachable contact address: set "
                f"${CONTACT_EMAIL_ENV_VAR} or pass contact_email."
            )
        archive = connect(email, model=resolve_agent_model())

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    logger.info("Fetching page %s (leaf %d)", reference.designation, reference.leaf)
    response = http_get(archive, reference.image_url, stream=True)
    try:
        with open(temporary, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
    finally:
        response.close()

    if temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise ScanError(f"archive.org returned an empty image for leaf {reference.leaf}.")
    temporary.replace(destination)
    return destination


def bands(
    printed_page: str | int,
    *,
    count: int = DEFAULT_BANDS,
    overlap: float = DEFAULT_OVERLAP,
    scale: int = DEFAULT_SCALE,
    source: Path | None = None,
) -> list[Path]:
    """Cut a cached page into overlapping horizontal bands, enlarged.

    ``count`` bands each covering ``1/count`` of the page's height plus ``overlap``
    of that band's height on either side, resampled up by ``scale`` with Lanczos.
    The overlap is what keeps a line of type that falls on a boundary whole in one
    band or the other; the enlargement is what makes nikkud visible at all.

    Returns the band paths in reading order, top of the page first.
    """
    from PIL import Image  # imported here so the module loads without Pillow

    if count < 1:
        raise ValueError("A page must be cut into at least one band.")
    if not 0 <= overlap < 0.5:
        raise ValueError("Overlap is a fraction of a band's height, below one half.")

    # A caller supplying its own image is naming the bands itself; otherwise the leaf
    # is canonicalised so that `XI` and `s13` cut bands over one cached image.
    designation = (
        str(printed_page) if source is not None else lookup(printed_page).designation
    )
    origin = Path(source) if source is not None else image_path(designation)
    if not origin.is_file():
        raise ScanError(f"{origin} has not been fetched yet.")

    BAND_DIRECTORY.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with Image.open(origin) as image:
        width, height = image.size
        band_height = height / count
        margin = band_height * overlap
        for index in range(count):
            top = max(0, int(round(index * band_height - margin)))
            bottom = min(height, int(round((index + 1) * band_height + margin)))
            crop = image.crop((0, top, width, bottom))
            enlarged = crop.resize(
                (crop.width * scale, crop.height * scale), Image.LANCZOS
            )
            destination = band_path(designation, index)
            enlarged.save(destination)
            written.append(destination)
    return written


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch pages of the Birnbaum scan and cut them into bands "
            "legible enough to read nikkud from."
        )
    )
    parser.add_argument(
        "pages",
        nargs="+",
        help=(
            "Pages, as the book prints them (81 82 ... or XI), or as sN by scan page "
            "for a leaf the print does not number (s1 s2 ... -- the front matter)."
        ),
    )
    parser.add_argument(
        "--no-bands",
        action="store_true",
        help="Fetch the page images only; do not cut them up.",
    )
    parser.add_argument(
        "--bands", type=int, default=DEFAULT_BANDS, help="How many bands per page."
    )
    parser.add_argument(
        "--scale", type=int, default=DEFAULT_SCALE, help="Enlargement factor."
    )
    parser.add_argument(
        "--force", action="store_true", help="Refetch pages already cached."
    )
    parser.add_argument(
        "--contact-email",
        default=None,
        help=f"Contact address for archive.org (default: ${CONTACT_EMAIL_ENV_VAR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for printed in arguments.pages:
        path = fetch(
            printed, contact_email=arguments.contact_email, force=arguments.force
        )
        print(path)
        if not arguments.no_bands:
            for band in bands(printed, count=arguments.bands, scale=arguments.scale):
                print(f"  {band}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
