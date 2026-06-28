"""TEI XML builders for haggadah projects."""

from __future__ import annotations

import html
from pathlib import Path

from opensiddur.importer.feinstein_haggadah.sections import (
    INDEX_CHILDREN,
    SectionContent,
    TextBlock,
    urn_for_section,
)
from opensiddur.importer.util.prettify import prettify_xml
from opensiddur.importer.util.validation import validate


def _xml_escape(text: str) -> str:
    return html.escape(text, quote=False)


def tei_document(
    header_xml: str,
    body_xml: str,
    *,
    lang: str,
) -> str:
    return f"""<tei:TEI xml:lang="{lang}" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
{header_xml}
<tei:text>
{body_xml}
</tei:text>
</tei:TEI>
"""


def _paragraph_xml(text: str) -> str:
    parts: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        inner = _xml_escape(block).replace("\n", " ")
        parts.append(f"<tei:p>{inner}</tei:p>")
    if not parts and text.strip():
        parts.append(f"<tei:p>{_xml_escape(text.strip())}</tei:p>")
    return "\n".join(parts)


def _render_blocks(
    slug: str,
    blocks: list[TextBlock],
    *,
    lang: str,
) -> str:
    parts: list[str] = []
    paragraph_number = 0
    text_attr = "hebrew" if lang == "he" else "english"
    for block in blocks:
        text = getattr(block, text_attr).strip()
        if block.kind == "head":
            if text:
                parts.append(f"<tei:head>{_xml_escape(text)}</tei:head>")
            continue
        if not text:
            continue
        if block.starts_paragraph:
            paragraph_number += 1
            urn = urn_for_section(slug, paragraph=paragraph_number)
            parts.append(
                f'<tei:milestone unit="paragraph" n="{paragraph_number}" corresp="{urn}"/>'
            )
        if block.kind == "instruction":
            if text:
                parts.append(
                    f'<tei:note type="instruction">{_xml_escape(text.replace(chr(10), " "))}</tei:note>'
                )
            continue
        parts.append(_paragraph_xml(text))
    return "\n".join(parts)


def section_body(
    slug: str,
    section: SectionContent | None,
    *,
    lang: str,
    page_number: int | None = None,
    child_slugs: list[str] | None = None,
) -> str:
    urn = urn_for_section(slug)
    pb = f'    <tei:pb n="{page_number}"/>\n' if page_number else ""
    content = ""
    if section and section.blocks:
        rendered = _render_blocks(slug, section.blocks, lang=lang)
        if rendered:
            content = f"    {rendered.replace(chr(10), chr(10) + '    ')}\n"
    transcludes = ""
    if child_slugs:
        transcludes = "\n".join(
            f'    <j:transclude type="external" target="{urn_for_section(child)}"/>'
            for child in child_slugs
        )
        if transcludes:
            transcludes += "\n"
    return f"""<tei:body>
  <tei:div corresp="{urn}">
{pb}{content}{transcludes}  </tei:div>
</tei:body>"""


def content_body(
    slug: str,
    section: SectionContent | None,
    *,
    lang: str,
    page_number: int | None = None,
) -> str:
    return section_body(slug, section, lang=lang, page_number=page_number)


def index_body(
    index_slug: str,
    child_slugs: list[str],
    section: SectionContent | None = None,
    *,
    lang: str,
) -> str:
    return section_body(
        index_slug,
        section,
        lang=lang,
        child_slugs=child_slugs,
    )


def validate_and_write(tei_content: str, file_name: str, project_dir: Path) -> Path:
    out_path = project_dir / f"{file_name}.xml"
    pretty_xml = prettify_xml(tei_content, remove_xml_declaration=True)
    is_valid, errors = validate(pretty_xml)
    if not is_valid:
        raise RuntimeError(f"JLPTEI validation failed for {file_name}: {errors}")
    out_path.write_text(pretty_xml, encoding="utf-8")
    is_valid_on_disk, disk_errors = validate(out_path)
    if not is_valid_on_disk:
        raise RuntimeError(f"JLPTEI validation failed after write for {file_name}: {disk_errors}")
    return out_path


def validate_project_directory(project_dir: Path) -> None:
    """Validate every XML file in a project directory against RelaxNG and Schematron."""
    xml_files = sorted(project_dir.glob("*.xml"))
    if not xml_files:
        raise RuntimeError(f"No XML files found in {project_dir}")

    failures: dict[str, list[str]] = {}
    for path in xml_files:
        is_valid, errors = validate(path)
        if not is_valid:
            failures[path.name] = errors

    if failures:
        summary = "; ".join(
            f"{name}: {errs[0]}" for name, errs in sorted(failures.items())
        )
        raise RuntimeError(
            f"JLPTEI validation failed for {len(failures)} file(s) in {project_dir.name}: {summary}"
        )


def validate_header_stub(stub_name: str, *, lang: str) -> None:
    """Validate a header stub as part of a well-formed TEI document."""
    header = read_header_stub(stub_name)
    sample = tei_document(header, index_body("index", ["pre_seder"], lang=lang), lang=lang)
    is_valid, errors = validate(sample)
    if not is_valid:
        raise RuntimeError(f"JLPTEI validation failed for header stub {stub_name}: {errors}")


def read_header_stub(stub_name: str) -> str:
    stub_path = Path(__file__).parent / stub_name
    return stub_path.read_text(encoding="utf-8").strip()


def minimal_index_header(
    title: str,
    *,
    project_id: str,
    urn_suffix: str,
    lang: str = "he",
) -> str:
    return f"""<tei:teiHeader xmlns:tei="http://www.tei-c.org/ns/1.0">
  <tei:fileDesc>
    <tei:titleStmt>
      <tei:title type="main" xml:lang="{lang}">{_xml_escape(title)}</tei:title>
    </tei:titleStmt>
    <tei:publicationStmt>
      <tei:distributor>
        <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
      </tei:distributor>
      <tei:idno type="urn">urn:x-opensiddur:text:haggadah:{urn_suffix}@{project_id}</tei:idno>
    </tei:publicationStmt>
    <tei:sourceDesc>
      <tei:bibl>
        <tei:ptr target="urn:x-opensiddur:text:haggadah:haggadah@{project_id}"/>
      </tei:bibl>
    </tei:sourceDesc>
  </tei:fileDesc>
</tei:teiHeader>"""
