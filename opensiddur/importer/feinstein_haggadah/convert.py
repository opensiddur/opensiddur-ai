"""Convert downloaded Open Siddur haggadah compilation to JLPTEI projects."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from opensiddur.common.constants import PROJECT_DIRECTORY
from opensiddur.importer.feinstein_haggadah.page_breaks import (
    load_page_breaks,
    write_empty_page_breaks_template,
)
from opensiddur.importer.feinstein_haggadah.parse_compilation import (
    build_section_contents,
    load_compilation_json,
    parse_rows,
)
from opensiddur.importer.feinstein_haggadah.sections import INDEX_CHILDREN, document_order_slugs, leaf_slugs
from opensiddur.importer.feinstein_haggadah.tei_builder import (
    content_body,
    index_body,
    minimal_index_header,
    read_header_stub,
    tei_document,
    validate_and_write,
    validate_header_stub,
    validate_project_directory,
)
from opensiddur.importer.util.pages import (
    default_sourcetexts_root,
    feinstein_haggadah_data_directory,
    heidenheim_pdf_path,
)

INDEX_TITLES: dict[str, str] = {
    "index": "Haggadah",
    "pre_seder": "Pre-Seder",
    "seder": "Seder",
    "magid": "Magid",
    "nirtzah": "Nirtzah",
}


def make_project_directory(project_dir: Path) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def convert_project(
    *,
    project_id: str,
    lang: str,
    header_stub: str,
    sourcetexts_root: Path | None,
    project_dir: Path,
    include_page_breaks: bool = False,
) -> None:
    json_path = feinstein_haggadah_data_directory(sourcetexts_root) / "compilation.json"
    compilation = load_compilation_json(json_path)
    rows = parse_rows(compilation)
    contents = build_section_contents(rows)
    page_milestones: dict[str, int | None] = {}
    if include_page_breaks:
        page_milestones = _emit_page_breaks(load_page_breaks(sourcetexts_root))

    validate_header_stub(header_stub, lang=lang)
    main_header = read_header_stub(header_stub)

    for index_slug, children in INDEX_CHILDREN.items():
        section = contents.get(index_slug)
        body = index_body(index_slug, children, section, lang=lang)
        if index_slug == "index":
            header = main_header
        else:
            header = minimal_index_header(
                INDEX_TITLES.get(index_slug, index_slug),
                project_id=project_id,
                urn_suffix=index_slug,
                lang=lang,
            )
        xml = tei_document(header, body, lang=lang)
        validate_and_write(xml, index_slug, project_dir)

    for slug in leaf_slugs():
        section = contents.get(slug)
        page_no = page_milestones.get(slug)
        body = content_body(slug, section, lang=lang, page_number=page_no)
        xml = tei_document(main_header, body, lang=lang)
        validate_and_write(xml, slug, project_dir)

    validate_project_directory(project_dir)


def _emit_page_breaks(page_breaks: dict[str, int]) -> dict[str, int | None]:
    """Return page numbers only where a new printed page begins."""
    emitted: dict[str, int | None] = {}
    previous: int | None = None
    for slug in document_order_slugs():
        page = page_breaks.get(slug)
        if page is not None and page != previous:
            emitted[slug] = page
            previous = page
        else:
            emitted[slug] = None
    return emitted

def convert_all(
    *,
    sourcetexts_root: Path | None = None,
    project_root: Path | None = None,
) -> None:
    write_empty_page_breaks_template(sourcetexts_root)
    if not load_page_breaks(sourcetexts_root) and heidenheim_pdf_path(sourcetexts_root):
        from opensiddur.importer.feinstein_haggadah.align_page_breaks import (
            align_page_breaks,
            write_page_breaks,
        )

        write_page_breaks(align_page_breaks(sourcetexts_root=sourcetexts_root), sourcetexts_root)
    root = project_root or PROJECT_DIRECTORY

    he_dir = make_project_directory(root / "heidenheim_haggadah_1822")
    convert_project(
        project_id="heidenheim_haggadah_1822",
        lang="he",
        header_stub="heidenheim_haggadah_1822_header_stub.xml",
        sourcetexts_root=sourcetexts_root,
        project_dir=he_dir,
        include_page_breaks=True,
    )

    en_dir = make_project_directory(root / "feinstein_haggadah_translation_2009")
    convert_project(
        project_id="feinstein_haggadah_translation_2009",
        lang="en",
        header_stub="feinstein_haggadah_translation_2009_header_stub.xml",
        sourcetexts_root=sourcetexts_root,
        project_dir=en_dir,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Feinstein/Heidenheim haggadah sources to JLPTEI projects."
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=default_sourcetexts_root(),
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=PROJECT_DIRECTORY,
        help="Parent directory containing project subdirectories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    convert_all(sourcetexts_root=args.sourcetexts_root, project_root=args.project_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
