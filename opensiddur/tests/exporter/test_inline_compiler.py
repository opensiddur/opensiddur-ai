"""Tests for the InlineCompilerProcessor class."""

import re
from typing import Optional
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from lxml import etree
from opensiddur.exporter.inline_compiler import InlineCompilerProcessor
from opensiddur.exporter.linear import LinearData, reset_linear_data, get_linear_data
from opensiddur.exporter.refdb import Reference, ReferenceDatabase, UrnMapping
from opensiddur.exporter.urn import ResolvedUrn

PROCESSING_NAMESPACE = 'http://jewishliturgy.org/ns/processing'
TEI_NAMESPACE = 'http://www.tei-c.org/ns/1.0'
NS = {'tei': TEI_NAMESPACE, 'p': PROCESSING_NAMESPACE}


class TestInlineCompilerProcessorTextExtraction(unittest.TestCase):
    """Test basic text extraction by InlineCompilerProcessor."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name) / 'test_project'
        self.test_project_dir.mkdir(parents=True)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)

        # Annotation-free mock: no references, no URN mappings
        self.refdb = MagicMock(spec=ReferenceDatabase)
        self.refdb.get_references_to.return_value = []
        self.refdb.get_urn_mappings.return_value = []

    def _create_test_file(self, file_name: str, content: bytes) -> str:
        """Write an XML file to the test project directory and return file_name."""
        file_path = self.test_project_dir / file_name
        file_path.write_bytes(content)
        return file_name

    def _get_paths(self, xml_bytes: bytes, start_xpath: str, end_xpath: str) -> tuple[str, str]:
        """Parse xml_bytes and return XPaths of start and end elements."""
        root = etree.fromstring(xml_bytes)
        start = root.xpath(start_xpath, namespaces=NS)[0]
        end = root.xpath(end_xpath, namespaces=NS)[0]
        return (
            start.getroottree().getpath(start),
            end.getroottree().getpath(end),
        )

    def _run(self, file_name: str, start_path: str, end_path: str,
             include_tail_after_end: bool = False) -> etree._Element:
        """Run InlineCompilerProcessor and return the p:transcludeInline result."""
        processor = InlineCompilerProcessor(
            'test_project', file_name, start_path, end_path,
            include_tail_after_end=include_tail_after_end,
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        return processor.process()

    # ------------------------------------------------------------------ #
    # Single-element range (start == end)
    # ------------------------------------------------------------------ #

    def test_single_element_returns_transclude_inline(self):
        """Result is always a p:transcludeInline element."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p corresp="urn:target">Hello world</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('single.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        self.assertEqual(result.tag, f'{{{PROCESSING_NAMESPACE}}}transcludeInline')

    def test_single_element_extracts_text(self):
        """Text of a single-element range is extracted into p:transcludeInline."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p>Before (excluded)</tei:p>
                <tei:p corresp="urn:target">Target text</tei:p>
                <tei:p>After (excluded)</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('single_text.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        self.assertIn('Target text', result.text)

    def test_single_element_excludes_siblings(self):
        """Content from sibling elements outside the range is absent."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p>Before (excluded)</tei:p>
                <tei:p corresp="urn:target">Target text</tei:p>
                <tei:p>After (excluded)</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('single_exclude.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertNotIn('Before (excluded)', result_text)
        self.assertNotIn('After (excluded)', result_text)

    # ------------------------------------------------------------------ #
    # Sibling range (start and end are different siblings)
    # ------------------------------------------------------------------ #

    def test_sibling_range_concatenates_text(self):
        """Text from start, middle, and end siblings is all present in the result."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p>Before (excluded)</tei:p>
                <tei:p corresp="urn:start">Start text</tei:p>
                <tei:p xml:id="middle">Middle text</tei:p>
                <tei:p corresp="urn:end">End text</tei:p>
                <tei:p>After (excluded)</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('siblings.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertIn('Start text', result_text)
        self.assertIn('Middle text', result_text)
        self.assertIn('End text', result_text)

    def test_sibling_range_excludes_before_start(self):
        """Content from elements before the start element is not present."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p>Excluded before</tei:p>
                <tei:p corresp="urn:start">Start text</tei:p>
                <tei:p corresp="urn:end">End text</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('exclude_before.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertNotIn('Excluded before', result_text)

    def test_sibling_range_excludes_after_end(self):
        """Content from elements after the end element is not present."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p corresp="urn:start">Start text</tei:p>
                <tei:p corresp="urn:end">End text</tei:p>
                <tei:p>Excluded after</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('exclude_after.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertNotIn('Excluded after', result_text)

    def test_sibling_range_includes_tail_text_between_elements(self):
        """Tail text between in-range elements is captured in the result."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p corresp="urn:start">Start</tei:p> between-tail
                <tei:p corresp="urn:end">End</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('tail_between.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertIn('between-tail', result_text)

    # ------------------------------------------------------------------ #
    # Nested element text flattening
    # ------------------------------------------------------------------ #

    def test_nested_element_text_is_extracted(self):
        """Text inside child elements of an in-range element is included."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p corresp="urn:start">Outer start <tei:seg>inner seg</tei:seg> outer end</tei:p>
                <tei:p corresp="urn:end">End element</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('nested.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        result = self._run(file_name, start_path, end_path)
        result_text = etree.tostring(result, encoding='unicode')

        self.assertIn('Outer start', result_text)
        self.assertIn('inner seg', result_text)
        self.assertIn('outer end', result_text)

    # ------------------------------------------------------------------ #
    # Language propagation
    # ------------------------------------------------------------------ #

    def test_language_from_root_element_propagates_to_result(self):
        """xml:lang on the document root is reflected on the returned p:transcludeInline."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                        xml:lang="he">
            <tei:div>
                <tei:p corresp="urn:target">&#x5E9;&#x5DC;&#x5D5;&#x5DD;</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('lang_root.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        self.assertEqual(result.get(lang_attr), 'he')

    def test_language_on_element_propagates_to_result(self):
        """xml:lang set directly on an in-range element is set on its p:transcludeInline."""
        # The range element itself carries xml:lang (not just inherited).
        # When it is the ONLY element in the range its p:transcludeInline should carry the lang.
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:div>
                <tei:p xml:lang="he" corresp="urn:target">Hebrew text</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('lang_elem.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        # The child p:transcludeInline for the he element is kept nested (different from
        # the root text_element which has no lang), and that nested element carries xml:lang="he".
        ti_tag = f'{{{PROCESSING_NAMESPACE}}}transcludeInline'
        he_nodes = [n for n in result.iter(ti_tag) if n.get(lang_attr) == 'he']
        self.assertTrue(he_nodes, "Expected a p:transcludeInline with xml:lang='he'")
        self.assertIn('Hebrew text', he_nodes[0].text)

    # ------------------------------------------------------------------ #
    # Mixed-language content: different-language child stays nested
    # ------------------------------------------------------------------ #

    def test_same_language_child_text_is_flattened(self):
        """A child element sharing the context language has its text merged into the parent."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
            <tei:div>
                <tei:p corresp="urn:target">Before <tei:seg>inline seg</tei:seg> after</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('same_lang.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        # All text is flat — no nested p:transcludeInline children
        ti_tag = f'{{{PROCESSING_NAMESPACE}}}transcludeInline'
        nested = [c for c in result if c.tag == ti_tag]
        self.assertEqual(nested, [], "Same-language child should be flattened, not nested")
        result_text = etree.tostring(result, encoding='unicode')
        self.assertIn('Before', result_text)
        self.assertIn('inline seg', result_text)
        self.assertIn('after', result_text)

    def test_different_language_child_becomes_nested_element(self):
        """A child element with a different xml:lang is kept as a nested p:transcludeInline."""
        xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
            <tei:div>
                <tei:p corresp="urn:target">English <tei:seg xml:lang="he">&#x5E2;&#x5D1;&#x5E8;&#x5D9;&#x5EA;</tei:seg> English again</tei:p>
            </tei:div>
        </root>'''
        file_name = self._create_test_file('mixed_lang.xml', xml)
        start_path, end_path = self._get_paths(xml,
            "//tei:p[@corresp='urn:target']",
            "//tei:p[@corresp='urn:target']")

        result = self._run(file_name, start_path, end_path)

        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        ti_tag = f'{{{PROCESSING_NAMESPACE}}}transcludeInline'

        # There should be exactly one nested p:transcludeInline with xml:lang="he"
        he_nodes = [n for n in result.iter(ti_tag) if n.get(lang_attr) == 'he']
        self.assertEqual(len(he_nodes), 1)
        self.assertIn('\u05e2\u05d1\u05e8\u05d9\u05ea', he_nodes[0].text)

        # English text is in the outer element (root or its direct text), not nested
        result_text = etree.tostring(result, encoding='unicode')
        self.assertIn('English', result_text)

    # ------------------------------------------------------------------ #
    # Inline transclusion (j:transclude inside an inline range)
    # ------------------------------------------------------------------ #

    @patch('opensiddur.exporter.urn.UrnResolver.resolve_range')
    def test_inline_transclusion_produces_p_transclude_child(self, mock_resolve_range):
        """A j:transclude within an inline range produces a p:transclude child element."""
        # Source file — the target of the transclusion
        source_xml = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
            <tei:p corresp="urn:source">Transcluded text</tei:p>
        </root>'''
        self._create_test_file('source.xml', source_xml)
        source_root = etree.fromstring(source_xml)
        source_elem = source_root.xpath(
            "//tei:p[@corresp='urn:source']", namespaces={'tei': TEI_NAMESPACE})[0]
        source_path = source_elem.getroottree().getpath(source_elem)

        # Main file: j:transclude is a child of the in-range element
        main_xml = (
            b'<root xmlns:tei="http://www.tei-c.org/ns/1.0"'
            b' xmlns:j="http://jewishliturgy.org/ns/jlptei/2">'
            b'<tei:div>'
            b'<tei:p corresp="urn:start">Before '
            b'<j:transclude type="inline" target="urn:source"/>'
            b' after</tei:p>'
            b'<tei:p corresp="urn:end">End</tei:p>'
            b'</tei:div></root>'
        )
        file_name = self._create_test_file('main.xml', main_xml)
        start_path, end_path = self._get_paths(main_xml,
            "//tei:p[@corresp='urn:start']",
            "//tei:p[@corresp='urn:end']")

        # URN resolution: map "urn:source" to the element in source.xml
        from opensiddur.exporter.urn import ResolvedUrn
        resolved = ResolvedUrn(
            project='test_project',
            file_name='source.xml',
            urn='urn:source',
            element_path=source_path,
            end_element_path=source_path,
            end_includes_tail=False,
        )
        mock_resolve_range.return_value = [resolved]

        # project_priority must list 'test_project' so prioritize_range picks it up
        self.linear_data.project_priority = ['test_project']

        result = self._run(file_name, start_path, end_path)

        # The result should contain a p:transclude child (the inlined transclusion)
        transclude_tag = f'{{{PROCESSING_NAMESPACE}}}transclude'
        transclude_nodes = list(result.iter(transclude_tag))
        self.assertTrue(transclude_nodes, "Expected at least one p:transclude element")

        # The transcluded text must appear somewhere in the output
        result_text = etree.tostring(result, encoding='unicode')
        self.assertIn('Transcluded text', result_text)

        # Text from before/after the transclusion is also present
        self.assertIn('Before', result_text)
        self.assertIn('after', result_text)


def make_resolved_urn(
    *,
    urn: str,
    project: str,
    file_name: str,
    element_path: str,
    end_element_path: str | None = None,
    end_includes_tail: bool = False,
) -> ResolvedUrn:
    """Helper to create ResolvedUrn instances with default end path fields."""
    return ResolvedUrn(
        urn=urn,
        project=project,
        file_name=file_name,
        element_path=element_path,
        end_element_path=end_element_path or element_path,
        end_includes_tail=end_includes_tail,
    )


def make_urn_mapping(
    *,
    urn: str,
    project: str,
    file_name: str,
    element_path: str,
    element_tag: str,
    element_type: str | None = None,
    end_element_path: str | None = None,
    end_includes_tail: bool = False,
) -> UrnMapping:
    """Helper to create UrnMapping instances with default end path fields."""
    return UrnMapping(
        urn=urn,
        project=project,
        file_name=file_name,
        element_path=element_path,
        element_tag=element_tag,
        element_type=element_type,
        end_element_path=end_element_path or element_path,
        end_includes_tail=end_includes_tail,
    )


class TestInlineCompilerAnnotationReplace(unittest.TestCase):
    """Tests covering _AnnotationCommand.REPLACE and language-setting in the KEEP branch."""

    def setUp(self):
        reset_linear_data()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.linear_data = get_linear_data()
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)

        self.refdb = MagicMock(spec=ReferenceDatabase)
        self.refdb.get_references_to.return_value = []
        self.refdb.get_urn_mappings.return_value = []

    def _write_file(self, project: str, file_name: str, content: bytes) -> Path:
        project_dir = Path(self.temp_dir.name) / project
        project_dir.mkdir(parents=True, exist_ok=True)
        path = project_dir / file_name
        path.write_bytes(content)
        return path

    def test_instruction_note_with_corresp_is_replaced(self):
        """Line 122: when _annotate returns REPLACE, _process_element returns the replacement."""
        INSTRUCTION_URN = 'urn:example:instruction/1'

        # Replacement file lives in a higher-priority project
        replacement_xml = (
            f'<TEI xmlns:tei="{TEI_NAMESPACE}">'
            f'<tei:text><tei:body>'
            f'<tei:note type="instruction">REPLACEMENT TEXT</tei:note>'
            f'</tei:body></tei:text></TEI>'
        ).encode()
        self._write_file('instruction_project', 'replacement.xml', replacement_xml)

        # Discover the element_path of the replacement note
        replacement_root = etree.fromstring(replacement_xml)
        repl_note = replacement_root.xpath(
            '//tei:note[@type="instruction"]',
            namespaces={'tei': TEI_NAMESPACE}
        )[0]
        repl_path = repl_note.getroottree().getpath(repl_note)

        # Main file: instruction note with corresp inside the range
        main_xml = (
            f'<TEI xmlns:tei="{TEI_NAMESPACE}" xml:lang="en">'
            f'<tei:text><tei:body>'
            f'<tei:ab corresp="urn:start">Start</tei:ab>'
            f'<tei:note type="instruction" corresp="{INSTRUCTION_URN}">Default instruction</tei:note>'
            f'<tei:ab corresp="urn:end">End</tei:ab>'
            f'</tei:body></tei:text></TEI>'
        ).encode()
        self._write_file('test_project', 'main.xml', main_xml)

        main_root = etree.fromstring(main_xml)
        ns = {'tei': TEI_NAMESPACE}
        start_path = main_root.xpath("//tei:ab[@corresp='urn:start']", namespaces=ns)[0] \
            .getroottree().getpath(
                main_root.xpath("//tei:ab[@corresp='urn:start']", namespaces=ns)[0])
        end_path = main_root.xpath("//tei:ab[@corresp='urn:end']", namespaces=ns)[0] \
            .getroottree().getpath(
                main_root.xpath("//tei:ab[@corresp='urn:end']", namespaces=ns)[0])

        # URN resolution: instruction corresp → replacement note in instruction_project
        self.refdb.get_urn_mappings.return_value = [
            make_urn_mapping(
                urn=INSTRUCTION_URN,
                project='instruction_project',
                file_name='replacement.xml',
                element_path=repl_path,
                element_tag=f'{{{TEI_NAMESPACE}}}note',
                end_element_path=repl_path,
            )
        ]
        self.linear_data.instruction_priority = ['instruction_project', 'test_project']

        processor = InlineCompilerProcessor(
            'test_project', 'main.xml', start_path, end_path,
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        result = processor.process()
        result_text = etree.tostring(result, encoding='unicode')

        self.assertIn('REPLACEMENT TEXT', result_text,
                      "Replacement instruction should appear in output")
        self.assertNotIn('Default instruction', result_text,
                         "Original default instruction should be replaced")

    @patch('opensiddur.exporter.inline_compiler.ExternalCompilerProcessor')
    def test_keep_annotation_sets_xml_lang_when_language_differs(self, mock_ext_cls):
        """Lines 133-136: xml:lang is set on the kept note when root_language != context_lang."""
        # Main file with xml:lang="en" at root; instruction note has no corresp → KEEP
        main_xml = (
            f'<TEI xmlns:tei="{TEI_NAMESPACE}" xml:lang="en">'
            f'<tei:text><tei:body>'
            f'<tei:ab corresp="urn:start">Start</tei:ab>'
            f'<tei:note type="instruction">Hebrew note</tei:note>'
            f'<tei:ab corresp="urn:end">End</tei:ab>'
            f'</tei:body></tei:text></TEI>'
        ).encode()
        self._write_file('test_project', 'main.xml', main_xml)

        main_root = etree.fromstring(main_xml)
        ns = {'tei': TEI_NAMESPACE}
        start_path = main_root.xpath("//tei:ab[@corresp='urn:start']", namespaces=ns)[0] \
            .getroottree().getpath(
                main_root.xpath("//tei:ab[@corresp='urn:start']", namespaces=ns)[0])
        end_path = main_root.xpath("//tei:ab[@corresp='urn:end']", namespaces=ns)[0] \
            .getroottree().getpath(
                main_root.xpath("//tei:ab[@corresp='urn:end']", namespaces=ns)[0])

        # Build a processed element without xml:lang that the mock will return
        processed_note = etree.Element(f'{{{TEI_NAMESPACE}}}note')
        processed_note.set('type', 'instruction')
        processed_note.text = 'Hebrew note'

        # ExternalCompilerProcessor reports root_language="he", differing from doc "en"
        mock_instance = mock_ext_cls.return_value
        mock_instance.root_language = 'he'
        mock_instance.process.return_value = [processed_note]

        processor = InlineCompilerProcessor(
            'test_project', 'main.xml', start_path, end_path,
            linear_data=self.linear_data,
            reference_database=self.refdb,
        )
        processor.process()

        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        self.assertEqual(processed_note.get(lang_attr), 'he',
                         "xml:lang='he' should be set on the kept element when language differs")


class TestInlineCompilerProcessorAnnotations(unittest.TestCase):
    """Test annotation inclusion functionality in InlineCompilerProcessor."""

    def setUp(self):
        """Set up test fixtures and reset linear data."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_project_dir = Path(self.temp_dir.name) / "test_project"
        self.test_project_dir.mkdir(parents=True)
        
        # Create priority project directory
        self.priority_project_dir = Path(self.temp_dir.name) / "priority_project"
        self.priority_project_dir.mkdir(parents=True)
        
        # Patch the xml_cache base_path to use our temp directory
        self.linear_data = LinearData(
            instruction_priority=["priority_project", "test_project"],
            annotation_projects=["priority_project", "test_project"]
        )
        self.linear_data.xml_cache.base_path = Path(self.temp_dir.name)

        self.refdb = MagicMock(spec=ReferenceDatabase)
        # Each test needs to set its own refdb results

    def _create_test_file(self, project: str, file_name: str, content: bytes) -> tuple[str, str, etree._ElementTree]:
        """Create a test XML file and return (project, file_name, tree) tuple."""
        project_dir = Path(self.temp_dir.name) / project
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / file_name
        with open(file_path, 'wb') as f:
            f.write(content)
        xml = etree.parse(file_path)
        return project, file_name, xml

    def _create_file_with_element_for_annotation(self, project: str, file_name: str, 
                                                   start_urn: str, end_urn: str,
                                                   element_with_note: str = "") -> tuple[str, str]:
        """Create a file with elements that can be targeted for annotation."""
        xml_content = f'''<TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:title>Test Document</tei:title>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:text>
        <tei:body>
            <tei:div>
                <tei:p>Before start</tei:p>
                <tei:p corresp="{start_urn}">Start element</tei:p>
                Before the note.
                {element_with_note}
                After the note.
                <tei:p corresp="{end_urn}">End element</tei:p>
                <tei:p>After end</tei:p>
            </tei:div>
        </tei:body>
    </tei:text>
    <tei:standOff>
    </tei:standOff>
</TEI>'''.encode('utf-8')
        return self._create_test_file(project, file_name, xml_content)

    def _create_note_file(self, project: str, file_name: str, target_urn: str, 
                          note_content: str, note_type: str = "editorial") -> tuple[str, str, etree._ElementTree]:
        """Create a file with an editorial or instructional note."""
        if note_type == "instructional":
            xml_content = f'''<TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:title>Note Document</tei:title>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:text>
        <tei:body>
            <tei:div>
                <tei:note type="instruction" corresp="{target_urn}">
                    {note_content}
                </tei:note>
            </tei:div>
        </tei:body>
    </tei:text>
</TEI>'''.encode('utf-8')
        else:  # editorial
            xml_content = f'''<TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:title>Note Document</tei:title>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:standOff>
        <tei:note type="editorial" target="{target_urn}">
            {note_content}
        </tei:note>
    </tei:standOff>
</TEI>'''.encode('utf-8')
        return self._create_test_file(project, file_name, xml_content)

    def test_editorial_note_in_range(self):
        """Test that an editorial note targeting an element within the range is included."""
        start_urn = "urn:test:start"
        end_urn = "urn:test:end"
        target_urn = "urn:test:target"
        
        # Create main file with element that has a corresp and falls within range
        project, file_name, main_tree = self._create_file_with_element_for_annotation(
            "test_project", "main.xml", start_urn, end_urn,
            f'<tei:p corresp="{target_urn}">Targeted element</tei:p>'
        )
        
        # Get element paths from the main file
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        main_root = main_tree.getroot()
        start_elem = main_root.xpath(f"//tei:p[@corresp='{start_urn}']", namespaces=ns)[0]
        end_elem = main_root.xpath(f"//tei:p[@corresp='{end_urn}']", namespaces=ns)[0]
        start_path = start_elem.getroottree().getpath(start_elem)
        end_path = end_elem.getroottree().getpath(end_elem)
        
        # Create note file with editorial note
        note_project, note_file, note_tree = self._create_note_file(
            "test_project", "notes.xml", target_urn, "This is an editorial note", "editorial"
        )
        
        # Get the note element from the tree
        note_element = note_tree.xpath('//tei:note[@type="editorial"]', namespaces=ns)[0]
        note_path = note_element.getroottree().getpath(note_element)
        
        # Mock the reference database to return the note
        from opensiddur.exporter.refdb import Reference
        mock_reference = Reference(
            project=note_project,
            file_name=note_file,
            element_path=note_path,
            element_tag="{http://www.tei-c.org/ns/1.0}note",
            element_type=None,
            target_start=target_urn,
            target_end=None,
            target_is_id=False,
            corresponding_urn=target_urn
        )
        # 3 urns: start, target, end
        self.refdb.get_references_to.side_effect = [[], [mock_reference], []]
        
        # Process with InlineCompilerProcessor
        processor = InlineCompilerProcessor(
            project, file_name, start_path, end_path,
            linear_data=self.linear_data,
            reference_database=self.refdb
        )
        result = processor.process()
        
        # The note should be inserted before the targeted element (which is within the range)
        # In InlineCompilerProcessor, the note gets inserted into the inline text result
        # Since the targeted element is within the range, the note should appear in the result
        notes = result.xpath(".//tei:note[@type='editorial']", namespaces=ns)
        # Should find at least one editorial note (the one targeting the element in the range)
        self.assertEqual(len(notes), 1, "Should find one editorial note")
        # At least one of the notes should be the one we created
        note = notes[0]
        note_texts = note.text.strip()
        self.assertIn("This is an editorial note", note_texts)
        self.assertIn("After the note.", note.tail.strip())
        self.assertIn("Before the note.", note.getparent().text.strip())


    def test_instructional_note_in_range(self):
        """Test that an instructional note within the range is included."""
        start_urn = "urn:test:start"
        end_urn = "urn:test:end"
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        # Create main file with element that has a corresp and falls within range
        project, file_name, main_tree = self._create_file_with_element_for_annotation(
            "test_project", "main.xml", start_urn, end_urn,
            f'<tei:note type="instruction">Inline instruction note</tei:note>'
        )
        
        # Get element paths from the main file
        main_root = main_tree.getroot()
        start_elem = main_root.xpath(f"//tei:p[@corresp='{start_urn}']", namespaces=ns)[0]
        end_elem = main_root.xpath(f"//tei:p[@corresp='{end_urn}']", namespaces=ns)[0]
        start_path = start_elem.getroottree().getpath(start_elem)
        end_path = end_elem.getroottree().getpath(end_elem)

        self.refdb.get_references_to.return_value = []
                
        # Process with InlineCompilerProcessor
        processor = InlineCompilerProcessor(
            project, file_name, start_path, end_path,
            linear_data=self.linear_data,
            reference_database=self.refdb
        )
        result = processor.process()
        
        # The note should be inserted before the targeted element (which is within the range)
        # In InlineCompilerProcessor, the note gets inserted into the inline text result
        # Since the targeted element is within the range, the note should appear in the result
        notes = result.xpath(".//tei:note[@type='instruction']", namespaces=ns)
        # Should find exactly one note
        self.assertEqual(len(notes), 1, "Should find one inline instruction note")
        
        note = notes[0]
        note_texts = note.text.strip()
        self.assertIn("Inline instruction note", note_texts)
        self.assertIn("After the note.", note.tail.strip())
        self.assertIn("Before the note.", note.getparent().text.strip())

