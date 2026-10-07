"""Compiled JLPTEI to an electronic book: one self-contained HTML file.

The book is a document and a program at once. Its text is html.xslt's rendering of the compiled
file; its program resolves the passages the compile left undecided, on the reader's device,
against the reader's own settings (assets/condition.js, assets/reader.js). Styles, scripts and
data are all inline, so the one file is the whole book: it opens from a disk, a USB stick or
an email, offline, and needs nothing else.

Read without scripts, the page is the printed book: <style id="os-cond-default"> holds the
rules a compile of the same settings file would have applied, computed here.

Compile with `--destination electronic` first, so that the settings a reader supplies are left
for the reader:

    python -m opensiddur.exporter.compiler -s SETTINGS --destination electronic -o book.xml
    python -m opensiddur.exporter.html.html book.xml book.html -s SETTINGS
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml
from lxml import etree

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.common.xslt import xslt_transform_string
from opensiddur.exporter.client_settings import is_reader_supplied, resolve
from opensiddur.exporter.condition_eval import TriState, condition_features, condition_from_json, value_to_json
from opensiddur.exporter.constants import PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.derived_settings import STATIC_DEFAULTS
from opensiddur.exporter.html.css import typography_css, xslt_parameters
from opensiddur.exporter.html.markers import BookConditions, prepare
from opensiddur.exporter.metadata import (
    _role_name,
    _role_order,
    extract_credits,
    extract_licenses,
    get_file_references,
    group_credits,
    group_licenses,
)
from opensiddur.exporter.typography import TypographyConfig

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
ASSETS = HERE / "assets"
XSLT_FILE = HERE / "html.xslt"

P_DESTINATION = f"{{{PROCESSING_NAMESPACE}}}destination"
P_PROJECT = f"{{{PROCESSING_NAMESPACE}}}project"
P_FILE_NAME = f"{{{PROCESSING_NAMESPACE}}}file_name"


# ── Settings ────────────────────────────────────────────────────────────────

def read_settings_data(settings_file: Path | None) -> dict[str, Any]:
    """The settings file, as YAML. Only its typography is validated: like the PDF stage, this
    one runs without the projects the file names being checked out."""
    if settings_file is None:
        return {}
    with open(settings_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def book_defaults(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """What the book starts from, for the settings a reader supplies.

    The static defaults, overlaid with the settings file's declarations: the values a compile
    for print would have used, which an electronic compile left for the reader to change.
    """
    defaults: dict[str, dict[str, Any]] = {}
    for fs_type, features in STATIC_DEFAULTS.items():
        if is_reader_supplied(fs_type):
            for name, value in features.items():
                defaults.setdefault(fs_type, {})[name] = value_to_json(value)
    for fs_type, features in (settings.get("declarations") or {}).items():
        if is_reader_supplied(fs_type):
            for name, value in (features or {}).items():
                defaults.setdefault(fs_type, {})[name] = value
    return defaults


# ── Conditions ──────────────────────────────────────────────────────────────

def expression_states(
    book: BookConditions, defaults: dict, reader: dict | None = None,
) -> list[TriState]:
    """How each of the book's expressions resolves, for the given reader settings."""
    return [
        resolve(expression["cond"], pinned=expression["pinned"], reader=reader or {},
                defaults=defaults)
        for expression in book.expressions
    ]


def scope_css(book: BookConditions, states: list[TriState]) -> str:
    """The rules that show and hide the book's scopes. condition.js's scopeCss writes the same
    rules on the device; a test holds the two to it."""
    hidden: list[str] = []
    settled: list[str] = []
    for cid, expression in enumerate(book.scopes):
        state = states[expression]
        if state == TriState.FALSE:
            hidden += [f".c{cid}", f".m{cid}"]
        elif state == TriState.TRUE:
            settled += [f".m{cid}.cm-close", f".m{cid}.cm-norubric", f".m{cid} .cm-br"]
    css = ""
    if hidden:
        css += ",".join(hidden) + "{display:none}\n"
    if settled:
        css += ",".join(settled) + "{display:none}\n"
    return css


def calendar_scopes(book: BookConditions) -> int:
    """How many scopes turn on the calendar, which the device does not answer yet."""
    turning: list[bool] = []
    for expression in book.expressions:
        features = condition_features(condition_from_json(expression["cond"]))
        turning.append(any(
            not is_reader_supplied(fs) and name not in expression["pinned"].get(fs, {})
            for fs, name in features))
    return sum(1 for expression in book.scopes if turning[expression])


# ── About the book ──────────────────────────────────────────────────────────

def book_title(root: etree.ElementBase, settings: dict[str, Any]) -> str:
    title = ((settings.get("book") or {}).get("title") or "").strip()
    if title:
        return title
    found = root.find(f".//{{{TEI_NS}}}titleStmt/{{{TEI_NS}}}title")
    return " ".join("".join(found.itertext()).split()) if found is not None else "Open Siddur"


def book_id(root: etree.ElementBase, title: str) -> str:
    """A stable name for the book, under which the reader's settings are kept."""
    source = f"{root.get(P_PROJECT, '')}/{root.get(P_FILE_NAME, '')}/{title}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def generator() -> str:
    try:
        return f"opensiddur-ai {version('opensiddur-ai')}"
    except PackageNotFoundError:
        return "opensiddur-ai"


def about_html(title: str, compiled_file: Path, project_directory: Path) -> str:
    """The book's colophon: what it is, and whose work it is under which licences."""
    escape = html.escape
    sources = get_file_references(compiled_file, project_directory)
    licenses = group_licenses(extract_licenses(sources, project_directory))
    credits = group_credits(extract_credits(sources))
    parts = [f"<h2>{escape(title)}</h2>",
             f"<p>An electronic edition from the Open Siddur Project, built by {escape(generator())}.</p>"]
    if credits:
        parts.append("<h2>Contributors</h2>")
        for role in sorted(credits, key=_role_order):
            names = sorted({credit.name_text for group in credits[role].values() for credit in group})
            parts.append(f"<p><strong>{escape(_role_name(role, credits[role]))}:</strong> "
                         f"{escape(', '.join(names))}</p>")
    if licenses:
        parts.append("<h2>Licences</h2><p>This book includes texts under these licences:</p><ul>")
        parts += [f'<li><a href="{escape(lic.url)}">{escape(lic.name or lic.url)}</a></li>'
                  for lic in licenses]
        parts.append("</ul>")
    return "\n".join(parts)


# ── The book ────────────────────────────────────────────────────────────────

def _inline(text: str, closing: str) -> str:
    """Text to go inside an element that ends at `closing`, which it must not contain."""
    if closing in text.lower():
        raise ValueError(f"cannot inline text containing {closing!r}")
    return text


def book_json(book: BookConditions, book_identifier: str, defaults: dict) -> str:
    data = {
        "version": 1,
        "id": book_identifier,
        "expressions": book.expressions,
        "scopes": book.scopes,
        "defaults": defaults,
        "features": [
            {"fs": f.fs, "name": f.name, "values": f.values, "scopes": f.scopes}
            for f in book.features
        ],
        "calendarScopes": calendar_scopes(book),
    }
    # "</" cannot appear in a script element; "<\/" is the same JSON string.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build_book(
    compiled_file: Path,
    settings_file: Path | None = None,
    project_directory: Path | None = None,
) -> str:
    """The electronic book, as one HTML document."""
    project_directory = Path(project_directory or PROJECT_DIRECTORY).resolve()
    settings = read_settings_data(settings_file)
    typography = TypographyConfig.model_validate(settings.get("typography") or {})

    root = etree.parse(str(compiled_file)).getroot()
    if root.get(P_DESTINATION) != "electronic":
        logger.warning(
            "%s was not compiled with --destination electronic: the settings a reader would "
            "choose were decided when it was compiled", compiled_file)

    book = prepare(root)
    main = xslt_transform_string(
        XSLT_FILE, etree.tostring(root, encoding="unicode"),
        xslt_params=xslt_parameters(typography))
    defaults = book_defaults(settings)
    title = book_title(root, settings)

    replacements = {
        "@@GENERATOR@@": html.escape(generator()),
        "@@TITLE@@": html.escape(title),
        "@@STYLE@@": _inline(
            (ASSETS / "reader.css").read_text(encoding="utf-8") + typography_css(typography),
            "</style"),
        "@@DEFAULT_CONDITIONS@@": scope_css(book, expression_states(book, defaults)),
        "@@MAIN@@": main,
        "@@ABOUT@@": about_html(title, compiled_file, project_directory),
        "@@BOOK@@": book_json(book, book_id(root, title), defaults),
        "@@CONDITION_JS@@": _inline(
            (ASSETS / "condition.js").read_text(encoding="utf-8"), "</script"),
        "@@READER_JS@@": _inline(
            (ASSETS / "reader.js").read_text(encoding="utf-8"), "</script"),
    }
    page = (ASSETS / "book.html").read_text(encoding="utf-8")
    for token, value in replacements.items():
        page = page.replace(token, value)
    return page


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Render a compiled JLPTEI file as a self-contained electronic book.")
    parser.add_argument("input_file", type=Path, help="Compiled XML (--destination electronic).")
    parser.add_argument("output_file", type=Path, help="The book, an .html file.")
    parser.add_argument("-s", "--settings", type=Path, help="The settings file it was compiled with.")
    parser.add_argument("--project-directory", type=Path, default=PROJECT_DIRECTORY,
                        help="Where the projects are, for licences and credits.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    page = build_book(args.input_file, args.settings, args.project_directory)
    args.output_file.write_text(page, encoding="utf-8")
    print(f"Electronic book written to: {args.output_file}", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    main()
