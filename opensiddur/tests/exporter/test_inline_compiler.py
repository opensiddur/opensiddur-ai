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

