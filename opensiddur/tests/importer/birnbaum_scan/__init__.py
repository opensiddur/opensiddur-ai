"""Fixtures shared by the Birnbaum scan tests.

The reading of the book lives in the sourcetexts submodule, which a plain checkout does
not have and CI does not initialise. Nothing here may depend on it: these are tests of the
code, and a test that read the committed reading would be testing the data instead --
failing whenever a reading is corrected, and passing for reasons of its own.
"""
from pathlib import Path

TEI_NS = 'xmlns:tei="http://www.tei-c.org/ns/1.0"'


def write_synthetic_front(directory: Path) -> Path:
    """Stand in for `scan_reading/front/`: one fragment per section, no words of the book."""
    from opensiddur.importer.birnbaum_scan.build import front

    directory.mkdir(parents=True, exist_ok=True)
    for section in front.SECTIONS:
        (directory / section["fragment"]).write_text(
            f'<tei:div {TEI_NS} corresp="urn:x-opensiddur:text:front:{section["slug"]}">'
            f"<tei:p>words</tei:p></tei:div>\n", encoding="utf-8")
    for _, name in (pair for pairs in front.TITLE_LEAVES.values() for pair in pairs):
        (directory / name).write_text(
            f'<tei:titlePage {TEI_NS} corresp="urn:x-opensiddur:text:front:title_page">'
            f"<tei:docTitle><tei:titlePart>t</tei:titlePart></tei:docTitle>"
            f"</tei:titlePage>\n", encoding="utf-8")
    return directory
