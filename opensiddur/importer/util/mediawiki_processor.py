"""
MediaWiki/Wikitext to intermediate XML processor.

This module contains the reusable MediaWiki processing framework originally built
for the JPS1917 importer. Other importers (e.g. Miqra al pi ha‑Masorah) can reuse
it by adding/overriding template and tag handlers.
"""

# NOTE: The initial implementation is intentionally a direct move of the existing
# processor to provide a stable API surface (`MediaWikiProcessor`, `create_processor`)
# for multiple importers. Importer-specific specializations should be layered on
# top by registering handlers.

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

import mwparserfromhell


class ProcessingStage(Enum):
    """Stages of MediaWiki processing"""

    PREPROCESS = "preprocess"
    TEMPLATES = "templates"
    TAGS = "tags"
    POSTPROCESS = "postprocess"


@dataclass
class ConversionResult:
    """Result of a conversion operation"""

    xml_content: str
    metadata: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    wikilinks: List[Dict[str, Any]]


class MediaWikiProcessor:
    """
    Modular MediaWiki to XML processor.

    Provides a modular framework for converting MediaWiki syntax to an
    intermediate XML that can be transformed to TEI via XSLT.
    """

    def __init__(self):
        self.template_handlers = {}
        self.tag_handlers = {}
        self.preprocessors = []
        self.postprocessors = []
        self.wikilinks = []  # Store captured wikilinks
        self._initialize_handlers()

    def _initialize_handlers(self):
        """Initialize all template and tag handlers"""
        self._initialize_template_handlers()
        self._initialize_tag_handlers()
        self._initialize_preprocessors()
        self._initialize_postprocessors()
        self._initialize_wikilink_handlers()

    # -------------------------------------------------------------------------
    # Default handler initialization
    #
    # These defaults match the original JPS1917 processor behavior. Other
    # importers can clear/override and register their own handlers as needed.
    # -------------------------------------------------------------------------

    def _initialize_template_handlers(self):
        """Initialize handlers for MediaWiki templates"""

        # Text Formatting Templates
        self.template_handlers["sc"] = self._handle_small_caps
        self.template_handlers["larger"] = self._handle_larger_text
        self.template_handlers["x-larger"] = self._handle_x_larger_text
        self.template_handlers["xx-larger"] = self._handle_xx_larger_text
        self.template_handlers["xxx-larger"] = self._handle_xxx_larger_text
        self.template_handlers["smaller"] = self._handle_smaller_text

        # Layout Templates
        self.template_handlers["c"] = self._handle_center
        self.template_handlers["right"] = self._handle_right_align
        self.template_handlers["rule"] = self._handle_horizontal_rule
        self.template_handlers["nop"] = self._handle_no_paragraph

        # Biblical Content Templates
        self.template_handlers["verse"] = self._handle_verse
        self.template_handlers["rh"] = self._handle_right_header
        self.template_handlers["dropinitial"] = self._handle_drop_initial
        self.template_handlers["dhr"] = self._handle_double_horizontal_rule

        # Navigation Templates
        self.template_handlers["anchor"] = self._handle_anchor
        self.template_handlers["anchor+"] = self._handle_anchor_plus

        # Language Templates
        self.template_handlers["lang"] = self._handle_language

        # Reference Templates
        self.template_handlers["smallrefs"] = self._handle_small_refs

        # Special Templates
        self.template_handlers["hws"] = self._handle_hws
        self.template_handlers["hwe"] = self._handle_hwe
        self.template_handlers["***"] = self._handle_asterisks
        self.template_handlers["reconstruct"] = self._handle_reconstruct
        self.template_handlers["SIC"] = self._handle_sic
        self.template_handlers["sic"] = self._handle_sic
        self.template_handlers["sup"] = self._handle_superscript
        self.template_handlers["bar"] = self._handle_bar
        self.template_handlers["gap"] = self._handle_gap
        self.template_handlers["overfloat left"] = self._handle_overfloat_left
        self.template_handlers["float right"] = self._handle_float_right
        self.template_handlers["smaller block/s"] = self._handle_smaller_block_start
        self.template_handlers["smaller block/e"] = self._handle_smaller_block_end

    def _initialize_tag_handlers(self):
        """Initialize handlers for HTML/XML tags"""

        # Structural Tags
        self.tag_handlers["section"] = self._handle_section
        self.tag_handlers["table"] = self._handle_table
        self.tag_handlers["tr"] = self._handle_table_row
        self.tag_handlers["td"] = self._handle_table_cell

        # Text Formatting Tags
        self.tag_handlers["i"] = self._handle_italic
        self.tag_handlers["br"] = self._handle_line_break
        self.tag_handlers["span"] = self._handle_span

        # Content Tags
        self.tag_handlers["dd"] = self._handle_definition_description
        self.tag_handlers["ref"] = self._handle_reference

        # MediaWiki Specific Tags
        self.tag_handlers["noinclude"] = self._handle_noinclude
        self.tag_handlers["pagequality"] = self._handle_pagequality

    def _initialize_preprocessors(self):
        """Initialize preprocessing functions"""
        self.preprocessors = [
            self._fix_noinclude_line_breaks,
            self._convert_paragraph_breaks,
            self._normalize_whitespace,
            self._handle_special_characters,
            self._extract_metadata,
        ]

    def _initialize_postprocessors(self):
        """Initialize postprocessing functions"""
        self.postprocessors = [
            self._validate_xml_structure,
            self._finalize_metadata,
        ]

    def _initialize_wikilink_handlers(self):
        """Initialize wikilink processing"""
        pass

    # -------------------------------------------------------------------------
    # Core processing
    # -------------------------------------------------------------------------

    def _process_nested_content(self, content: str, depth: int = 0) -> str:
        """Recursively process nested templates and other elements"""
        if depth > 10:
            return content

        parsed = mwparserfromhell.parse(content)
        nodes_to_replace = []

        for node in parsed.nodes:
            if hasattr(node, "name"):  # Template
                template_name = str(node.name).strip()
                if template_name in self.template_handlers:
                    try:
                        processed_node = self._process_template_with_nesting(node, depth + 1)
                        replacement = self.template_handlers[template_name](processed_node)
                        nodes_to_replace.append((node, replacement))
                    except Exception:
                        replacement = self.template_handlers[template_name](node)
                        nodes_to_replace.append((node, replacement))
                else:
                    processed_content = self._process_nested_content(str(node), depth + 1)
                    nodes_to_replace.append((node, processed_content))

            elif hasattr(node, "tag"):  # Tag
                tag_name = str(node.tag).strip().lower()
                if tag_name in self.tag_handlers:
                    try:
                        processed_node = self._process_tag_with_nesting(node, depth + 1)
                        replacement = self.tag_handlers[tag_name](processed_node)
                        nodes_to_replace.append((node, replacement))
                    except Exception:
                        replacement = self.tag_handlers[tag_name](node)
                        nodes_to_replace.append((node, replacement))
                else:
                    processed_content = self._process_nested_content(str(node), depth + 1)
                    nodes_to_replace.append((node, processed_content))

            elif hasattr(node, "__class__") and "Wikilink" in str(node.__class__):
                try:
                    replacement = self._handle_wikilink(node)
                    nodes_to_replace.append((node, replacement))
                except Exception:
                    nodes_to_replace.append((node, str(node)))

        for node, replacement in nodes_to_replace:
            parsed.replace(node, replacement)

        return str(parsed)

    def _process_template_with_nesting(self, template, depth: int = 0) -> object:
        import copy

        processed_template = copy.deepcopy(template)
        for param in processed_template.params:
            if hasattr(param, "value"):
                processed_value = self._process_nested_content(str(param.value), depth + 1)
                param.value = processed_value
        return processed_template

    def _process_tag_with_nesting(self, tag, depth: int = 0) -> object:
        import copy

        processed_tag = copy.deepcopy(tag)
        if hasattr(processed_tag, "contents") and processed_tag.contents:
            processed_contents = self._process_nested_content(
                str(processed_tag.contents), depth + 1
            )
            processed_tag.contents = processed_contents
        return processed_tag

    # -------------------------------------------------------------------------
    # Template handlers (JPS1917 defaults)
    # -------------------------------------------------------------------------

    def _handle_small_caps(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<sc>{content}</sc>"

    def _handle_larger_text(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<larger>{content}</larger>"

    def _handle_x_larger_text(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<x-larger>{content}</x-larger>"

    def _handle_xx_larger_text(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<xx-larger>{content}</xx-larger>"

    def _handle_xxx_larger_text(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<xxx-larger>{content}</xxx-larger>"

    def _handle_smaller_text(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<smaller>{content}</smaller>"

    def _handle_center(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<c>{content}</c>"

    def _handle_right_align(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<right>{content}</right>"

    def _handle_horizontal_rule(self, template) -> str:
        return "<rule/>"

    def _handle_double_horizontal_rule(self, template) -> str:
        return "<dhr/>"

    def _handle_no_paragraph(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<nop>{content}</nop>"

    def _handle_verse(self, template) -> str:
        chapter = str(template.get(1, "")).strip()
        verse = str(template.get(2, "")).strip()
        content = str(template.get(3, ""))
        return f'<verse chapter="{chapter}" verse="{verse}">{content}</verse>'

    def _handle_right_header(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<rh>{content}</rh>"

    def _handle_drop_initial(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<dropinitial>{content}</dropinitial>"

    def _handle_anchor(self, template) -> str:
        name = str(template.get(1, "")).strip()
        return f'<anchor name="{name}"/>'

    def _handle_anchor_plus(self, template) -> str:
        name = str(template.get(1, "")).strip()
        return f'<anchor-plus name="{name}"/>'

    def _handle_language(self, template) -> str:
        code = str(template.get(1, "")).strip()
        content = str(template.get(2, ""))
        return f'<lang code="{code}">{content}</lang>'

    def _handle_small_refs(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<smallrefs>{content}</smallrefs>"

    def _handle_hws(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<hws>{content}</hws>"

    def _handle_hwe(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<hwe>{content}</hwe>"

    def _handle_asterisks(self, template) -> str:
        return "<asterisks/>"

    def _handle_reconstruct(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<reconstruct>{content}</reconstruct>"

    def _handle_sic(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<sic>{content}</sic>"

    def _handle_superscript(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<sup>{content}</sup>"

    def _handle_bar(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<bar>{content}</bar>"

    def _handle_gap(self, template) -> str:
        return "<gap/>"

    def _handle_overfloat_left(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<overfloat_left>{content}</overfloat_left>"

    def _handle_float_right(self, template) -> str:
        content = str(template.get(1, ""))
        return f"<float_right>{content}</float_right>"

    def _handle_smaller_block_start(self, template) -> str:
        return "<smaller_block_start/>"

    def _handle_smaller_block_end(self, template) -> str:
        return "<smaller_block_end/>"

    # -------------------------------------------------------------------------
    # Tag handlers (JPS1917 defaults)
    # -------------------------------------------------------------------------

    def _handle_section(self, tag) -> str:
        begin = getattr(tag, "attributes", {}).get("begin", "")
        return f'<section begin="{begin}"/>'

    def _handle_table(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<table>{contents}</table>"

    def _handle_table_row(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<tr>{contents}</tr>"

    def _handle_table_cell(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<td>{contents}</td>"

    def _handle_italic(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<i>{contents}</i>"

    def _handle_line_break(self, tag) -> str:
        return "<br/>"

    def _handle_span(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<span>{contents}</span>"

    def _handle_definition_description(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<dd>{contents}</dd>"

    def _handle_reference(self, tag) -> str:
        name = getattr(tag, "attributes", {}).get("name", "")
        contents = getattr(tag, "contents", "") or ""
        return f'<ref name="{name}">{contents}</ref>'

    def _handle_noinclude(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<noinclude>{contents}</noinclude>"

    def _handle_pagequality(self, tag) -> str:
        contents = getattr(tag, "contents", "") or ""
        return f"<pagequality>{contents}</pagequality>"

    # -------------------------------------------------------------------------
    # Pre/post processing (JPS1917 defaults)
    # -------------------------------------------------------------------------

    def _fix_noinclude_line_breaks(self, text: str, metadata: Dict[str, Any]) -> str:
        return re.sub(r"</noinclude>\n", "</noinclude>", text)

    def _convert_paragraph_breaks(self, text: str, metadata: Dict[str, Any]) -> str:
        return text.replace("\n\n", "<p/>")

    def _normalize_whitespace(self, text: str, metadata: Dict[str, Any]) -> str:
        return re.sub(r"[ \t]+", " ", text)

    def _handle_special_characters(self, text: str, metadata: Dict[str, Any]) -> str:
        # Preserve only minimal escaping at this stage.
        return text

    def _extract_metadata(self, text: str, metadata: Dict[str, Any]) -> str:
        metadata.setdefault("length", len(text))
        return text

    def _validate_xml_structure(self, xml_content: str, metadata: Dict[str, Any]) -> str:
        # Lightweight sanity check; TEI validation happens later.
        return xml_content

    def _finalize_metadata(self, xml_content: str, metadata: Dict[str, Any]) -> str:
        metadata["processed"] = True
        return xml_content

    # -------------------------------------------------------------------------
    # Wikilinks
    # -------------------------------------------------------------------------

    def _handle_wikilink(self, node) -> str:
        try:
            title = str(getattr(node, "title", "")).strip()
            text = str(getattr(node, "text", "")).strip() if getattr(node, "text", None) else ""
            self.wikilinks.append({"title": title, "text": text})
            if text:
                return f'<__link__ title="{title}">{text}</__link__>'
            return f'<__link__ title="{title}"/>'
        except Exception:
            return str(node)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def process_wikitext(self, wikitext: str) -> ConversionResult:
        warnings: List[str] = []
        errors: List[str] = []
        metadata: Dict[str, Any] = {}

        text = wikitext or ""
        for pre in self.preprocessors:
            try:
                text = pre(text, metadata)
            except Exception as e:
                errors.append(str(e))

        try:
            xml_content = self._process_nested_content(text)
        except Exception as e:
            xml_content = text
            errors.append(str(e))

        for post in self.postprocessors:
            try:
                xml_content = post(xml_content, metadata)
            except Exception as e:
                errors.append(str(e))

        return ConversionResult(
            xml_content=xml_content,
            metadata=metadata,
            warnings=warnings,
            errors=errors,
            wikilinks=self.wikilinks.copy(),
        )

    def add_template_handler(self, template_name: str, handler_func):
        self.template_handlers[template_name] = handler_func

    def add_tag_handler(self, tag_name: str, handler_func):
        self.tag_handlers[tag_name] = handler_func

    def add_preprocessor(self, preprocessor_func):
        self.preprocessors.append(preprocessor_func)

    def add_postprocessor(self, postprocessor_func):
        self.postprocessors.append(postprocessor_func)

    def get_wikilinks(self) -> List[Dict[str, Any]]:
        return self.wikilinks.copy()

    def clear_wikilinks(self):
        self.wikilinks.clear()


def create_processor() -> MediaWikiProcessor:
    return MediaWikiProcessor()


def process_page(page_content: str) -> ConversionResult:
    processor = create_processor()
    return processor.process_wikitext(page_content)

