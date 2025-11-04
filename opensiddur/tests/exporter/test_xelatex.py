#!/usr/bin/env python3
"""
Tests for opensiddur.exporter.tex.xelatex module
"""

import unittest
import tempfile
from pathlib import Path
from lxml import etree
from io import StringIO
from unittest.mock import patch, MagicMock
import sys

from opensiddur.exporter.tex.xelatex import (
    extract_licenses,
    group_licenses,
    licenses_to_tex,
    extract_credits,
    group_credits,
    credits_to_tex,
    get_file_references,
    extract_sources,
    transform_xml_to_tex,
    LicenseRecord,
    CreditRecord,
)


class TestExtractLicenses(unittest.TestCase):
    """Test license extraction from XML files."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name) / "project"
        self.test_dir.mkdir(parents=True)

    def _create_xml_file(self, filename: str, content: bytes) -> Path:
        """Helper to create an XML file in a project subdirectory."""
        # Create in a test_project subdirectory to mimic real structure
        project_dir = self.test_dir / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_extract_single_license(self):
        """Test extracting a single license from an XML file."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:publicationStmt>
                <tei:availability>
                    <tei:licence target="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</tei:licence>
                </tei:availability>
            </tei:publicationStmt>
        </tei:fileDesc>
    </tei:teiHeader>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        
        # Patch projects_source_root to use our temp directory
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file_path])
        
        self.assertEqual(len(result), 1)
        license_record = list(result.values())[0]
        self.assertIsInstance(license_record, LicenseRecord)
        self.assertEqual(license_record.url, "http://creativecommons.org/licenses/by/4.0/")
        self.assertEqual(license_record.name, "Creative Commons Attribution 4.0")

    def test_extract_multiple_licenses_from_multiple_files(self):
        """Test extracting licenses from multiple XML files."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml1 = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:availability>
            <tei:licence target="http://license1.com">License 1</tei:licence>
        </tei:availability>
    </tei:teiHeader>
</root>'''
        
        xml2 = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:availability>
            <tei:licence target="http://license2.com">License 2</tei:licence>
        </tei:availability>
    </tei:teiHeader>
</root>'''
        
        file1 = self._create_xml_file("file1.xml", xml1)
        file2 = self._create_xml_file("file2.xml", xml2)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file1, file2])
        
        self.assertEqual(len(result), 2)
        self.assertIn("License 1", [lic.name for lic in result.values()])
        self.assertIn("License 2", [lic.name for lic in result.values()])

    def test_extract_license_with_no_url(self):
        """Test that a license without URL is not extracted (URL is required)."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:licence>Public Domain</tei:licence>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file_path])
        
        # License without URL should not be extracted
        self.assertEqual(len(result), 0)

    def test_extract_license_with_no_text(self):
        """Test extracting a license with only URL, no text."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:licence target="http://example.com/license"/>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file_path])
        
        self.assertEqual(len(result), 1)
        license_record = list(result.values())[0]
        self.assertEqual(license_record.url, "http://example.com/license")
        self.assertEqual(license_record.name, "")

    def test_extract_no_licenses(self):
        """Test extracting from file with no licenses."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:p>Some text</tei:p>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file_path])
        
        self.assertEqual(len(result), 0)

    def test_extract_license_handles_invalid_xml(self):
        """Test that invalid XML is handled gracefully."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        file_path = self._create_xml_file("invalid.xml", b"not valid xml")
        
        # Should not raise exception, just skip the file
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = extract_licenses([file_path])
        self.assertEqual(len(result), 0)


class TestGroupLicenses(unittest.TestCase):
    """Test license grouping."""

    def test_group_single_license(self):
        """Test grouping a single license."""
        licenses = {
            Path("file1.xml"): LicenseRecord(url="http://license.com", name="License 1")
        }
        
        result = group_licenses(licenses)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, "http://license.com")
        self.assertEqual(result[0].name, "License 1")

    def test_group_deduplicates_same_url(self):
        """Test that licenses with same URL are deduplicated."""
        licenses = {
            Path("file1.xml"): LicenseRecord(url="http://license.com", name="License 1"),
            Path("file2.xml"): LicenseRecord(url="http://license.com", name="License 1"),
            Path("file3.xml"): LicenseRecord(url="http://license.com", name="License 1"),
        }
        
        result = group_licenses(licenses)
        
        # Should only have 1 unique license
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, "http://license.com")

    def test_group_different_licenses(self):
        """Test grouping different licenses."""
        licenses = {
            Path("file1.xml"): LicenseRecord(url="http://license1.com", name="License 1"),
            Path("file2.xml"): LicenseRecord(url="http://license2.com", name="License 2"),
            Path("file3.xml"): LicenseRecord(url="http://license3.com", name="License 3"),
        }
        
        result = group_licenses(licenses)
        
        self.assertEqual(len(result), 3)
        urls = [lic.url for lic in result]
        self.assertIn("http://license1.com", urls)
        self.assertIn("http://license2.com", urls)
        self.assertIn("http://license3.com", urls)


class TestLicensesToTex(unittest.TestCase):
    """Test LaTeX generation from licenses."""

    def test_single_license_to_tex(self):
        """Test converting a single license to LaTeX."""
        licenses = [
            LicenseRecord(url="http://creativecommons.org/licenses/by/4.0/", name="CC BY 4.0")
        ]
        
        result = licenses_to_tex(licenses)
        
        self.assertIn(r'\chapter{Legal}', result)
        self.assertIn('CC BY 4.0', result)
        self.assertIn(r'\url{http://creativecommons.org/licenses/by/4.0/}', result)
        self.assertIn(r'\begin{itemize}', result)
        self.assertIn(r'\end{itemize}', result)

    def test_multiple_licenses_to_tex(self):
        """Test converting multiple licenses to LaTeX."""
        licenses = [
            LicenseRecord(url="http://license1.com", name="License 1"),
            LicenseRecord(url="http://license2.com", name="License 2"),
        ]
        
        result = licenses_to_tex(licenses)
        
        self.assertIn('License 1', result)
        self.assertIn('License 2', result)
        self.assertIn(r'\url{http://license1.com}', result)
        self.assertIn(r'\url{http://license2.com}', result)
        # Should have \item for each license
        self.assertEqual(result.count(r'\item'), 2)


class TestExtractCredits(unittest.TestCase):
    """Test credit extraction from XML files."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name) / "project"
        self.test_dir.mkdir(parents=True)

    def _create_xml_file(self, filename: str, content: bytes) -> Path:
        """Helper to create an XML file in a project subdirectory."""
        project_dir = self.test_dir / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_extract_single_credit(self):
        """Test extracting a single credit from an XML file."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:respStmt>
                    <tei:resp key="trc">Transcriber</tei:resp>
                    <tei:name ref="urn:x-opensiddur:namespace/contributor">John Doe</tei:name>
                </tei:respStmt>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        result = extract_credits([file_path])
        
        self.assertEqual(len(result), 1)
        credits = result[file_path]
        self.assertEqual(len(credits), 1)
        self.assertIsInstance(credits[0], CreditRecord)
        self.assertEqual(credits[0].role, "trc")
        self.assertEqual(credits[0].resp_text, "Transcriber")
        self.assertEqual(credits[0].name_text, "John Doe")
        self.assertEqual(credits[0].namespace, "namespace")
        self.assertEqual(credits[0].contributor, "contributor")

    def test_extract_multiple_credits(self):
        """Test extracting multiple credits from a file."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:titleStmt>
            <tei:respStmt>
                <tei:resp key="aut">Author</tei:resp>
                <tei:name ref="urn:x-opensiddur:ns1/person1">Author Name</tei:name>
            </tei:respStmt>
            <tei:respStmt>
                <tei:resp key="edt">Editor</tei:resp>
                <tei:name ref="urn:x-opensiddur:ns2/person2">Editor Name</tei:name>
            </tei:respStmt>
        </tei:titleStmt>
    </tei:teiHeader>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        result = extract_credits([file_path])
        
        credits = result[file_path]
        self.assertEqual(len(credits), 2)
        self.assertEqual(credits[0].role, "aut")
        self.assertEqual(credits[1].role, "edt")

    def test_extract_credits_handles_missing_elements(self):
        """Test that respStmt with missing name element is skipped (ref is required)."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:respStmt>
            <tei:resp key="trc">Transcriber</tei:resp>
        </tei:respStmt>
    </tei:teiHeader>
</root>'''
        
        file_path = self._create_xml_file("test.xml", xml_content)
        result = extract_credits([file_path])
        
        # Should have 0 credits because name (and therefore ref) is required
        credits = result[file_path]
        self.assertEqual(len(credits), 0)


class TestGroupCredits(unittest.TestCase):
    """Test credit grouping."""

    def test_group_single_credit(self):
        """Test grouping a single credit."""
        credits = {
            Path("file1.xml"): [
                CreditRecord(
                    role="aut",
                    resp_text="Author",
                    ref="urn:x-opensiddur:namespace/contributor",
                    name_text="John Doe",
                    namespace="namespace",
                    contributor="contributor"
                )
            ]
        }
        
        result = group_credits(credits)
        
        self.assertIn("aut", result)
        self.assertIn("namespace", result["aut"])
        self.assertEqual(len(result["aut"]["namespace"]), 1)
        self.assertEqual(result["aut"]["namespace"][0].name_text, "John Doe")

    def test_group_deduplicates_same_contributor(self):
        """Test that same contributor with same role is deduplicated."""
        credit1 = CreditRecord(
            role="aut",
            resp_text="Author",
            ref="urn:x-opensiddur:ns/person",
            name_text="John Doe",
            namespace="ns",
            contributor="person"
        )
        
        credits = {
            Path("file1.xml"): [credit1],
            Path("file2.xml"): [credit1],  # Same credit
        }
        
        result = group_credits(credits)
        
        # Should only appear once
        self.assertEqual(len(result["aut"]["ns"]), 1)

    def test_group_multiple_roles(self):
        """Test grouping credits with different roles."""
        credits = {
            Path("file1.xml"): [
                CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/p1", 
                           name_text="Person 1", namespace="ns", contributor="p1"),
                CreditRecord(role="edt", resp_text="Editor", ref="urn:x-opensiddur:ns/p2",
                           name_text="Person 2", namespace="ns", contributor="p2"),
            ]
        }
        
        result = group_credits(credits)
        
        self.assertIn("aut", result)
        self.assertIn("edt", result)
        self.assertEqual(len(result["aut"]["ns"]), 1)
        self.assertEqual(len(result["edt"]["ns"]), 1)

    def test_group_multiple_namespaces(self):
        """Test grouping credits from different namespaces."""
        credits = {
            Path("file1.xml"): [
                CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns1/p1",
                           name_text="Person 1", namespace="ns1", contributor="p1"),
                CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns2/p2",
                           name_text="Person 2", namespace="ns2", contributor="p2"),
            ]
        }
        
        result = group_credits(credits)
        
        self.assertIn("aut", result)
        self.assertIn("ns1", result["aut"])
        self.assertIn("ns2", result["aut"])
        self.assertEqual(len(result["aut"]["ns1"]), 1)
        self.assertEqual(len(result["aut"]["ns2"]), 1)


class TestCreditsToTex(unittest.TestCase):
    """Test LaTeX generation from credits."""

    def test_single_credit_to_tex(self):
        """Test converting a single credit to LaTeX."""
        credits = {
            "aut": {
                "namespace": [
                    CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/p",
                               name_text="John Doe", namespace="ns", contributor="p")
                ]
            }
        }
        
        result = credits_to_tex(credits)
        
        self.assertIn(r'\chapter{Contributor credits}', result)
        self.assertIn(r'\section{Author}', result)  # singular
        self.assertIn(r'\subsection{From namespace}', result)
        self.assertIn('John Doe', result)

    def test_multiple_credits_plural(self):
        """Test that role names are pluralized correctly."""
        credits = {
            "aut": {
                "namespace": [
                    CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/p1",
                               name_text="Person 1", namespace="ns", contributor="p1"),
                    CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/p2",
                               name_text="Person 2", namespace="ns", contributor="p2"),
                ]
            }
        }
        
        result = credits_to_tex(credits)
        
        self.assertIn(r'\section{Authors}', result)  # plural

    def test_credits_sorted_by_contributor(self):
        """Test that credits are sorted alphabetically by contributor."""
        credits = {
            "aut": {
                "namespace": [
                    CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/zebra",
                               name_text="Zebra", namespace="ns", contributor="zebra"),
                    CreditRecord(role="aut", resp_text="Author", ref="urn:x-opensiddur:ns/apple",
                               name_text="Apple", namespace="ns", contributor="apple"),
                ]
            }
        }
        
        result = credits_to_tex(credits)
        
        # Apple should come before Zebra
        apple_pos = result.find("Apple")
        zebra_pos = result.find("Zebra")
        self.assertLess(apple_pos, zebra_pos)


class TestGetFileReferences(unittest.TestCase):
    """Test file reference extraction from compiled XML."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)
        self.project_dir = self.test_dir / "project"
        self.project_dir.mkdir(parents=True)

    def _create_xml_file(self, filename: str, content: bytes) -> Path:
        """Helper to create an XML file."""
        file_path = self.project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_get_file_references_no_transclusions(self):
        """Test getting file references from XML with no transclusions."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                               xmlns:p="http://jewishliturgy.org/ns/processing"
                               p:project="test_project"
                               p:file_name="main.xml">
    <tei:text>
        <tei:p>Some text</tei:p>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("main.xml", xml_content)
        result = get_file_references(file_path, self.project_dir)
        
        # Should include the main file and its index
        self.assertIn(self.project_dir / "test_project" / "main.xml", result)
        self.assertIn(self.project_dir / "test_project" / "index.xml", result)

    def test_get_file_references_with_transclusion(self):
        """Test getting file references from XML with transclusions."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                               xmlns:p="http://jewishliturgy.org/ns/processing"
                               p:project="main_project"
                               p:file_name="main.xml">
    <tei:text>
        <p:transclude target="#fragment" 
                      type="external"
                      p:project="external_project"
                      p:file_name="external.xml">
            <tei:p>Transcluded content</tei:p>
        </p:transclude>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("main.xml", xml_content)
        result = get_file_references(file_path, self.project_dir)
        
        # Should include main file, external file, and both index files
        self.assertIn(self.project_dir / "main_project" / "main.xml", result)
        self.assertIn(self.project_dir / "main_project" / "index.xml", result)
        self.assertIn(self.project_dir / "external_project" / "external.xml", result)
        self.assertIn(self.project_dir / "external_project" / "index.xml", result)

    def test_get_file_references_deduplicates(self):
        """Test that duplicate file references are deduplicated."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                               xmlns:p="http://jewishliturgy.org/ns/processing"
                               p:project="project1"
                               p:file_name="main.xml">
    <tei:text>
        <p:transclude p:project="project2" p:file_name="file.xml"/>
        <p:transclude p:project="project2" p:file_name="file.xml"/>
        <p:transclude p:project="project2" p:file_name="file.xml"/>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("main.xml", xml_content)
        result = get_file_references(file_path, self.project_dir)
        
        # Count how many times project2/file.xml appears
        file_count = sum(1 for p in result if str(p).endswith("project2/file.xml"))
        self.assertEqual(file_count, 1, "Duplicate files should be deduplicated")

    def test_get_file_references_multiple_projects(self):
        """Test getting references from multiple projects."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                               xmlns:p="http://jewishliturgy.org/ns/processing"
                               p:project="project1"
                               p:file_name="main.xml">
    <tei:text>
        <p:transclude p:project="project2" p:file_name="file2.xml"/>
        <p:transclude p:project="project3" p:file_name="file3.xml"/>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("main.xml", xml_content)
        result = get_file_references(file_path, self.project_dir)
        
        # Should include files from 3 projects
        self.assertIn(self.project_dir / "project1" / "main.xml", result)
        self.assertIn(self.project_dir / "project2" / "file2.xml", result)
        self.assertIn(self.project_dir / "project3" / "file3.xml", result)
        # And 3 index files
        self.assertIn(self.project_dir / "project1" / "index.xml", result)
        self.assertIn(self.project_dir / "project2" / "index.xml", result)
        self.assertIn(self.project_dir / "project3" / "index.xml", result)

    def test_get_file_references_nested_transclusions(self):
        """Test getting references with nested transclusions."""
        xml_content = b'''<root xmlns:tei="http://www.tei-c.org/ns/1.0"
                               xmlns:p="http://jewishliturgy.org/ns/processing"
                               p:project="project1"
                               p:file_name="main.xml">
    <tei:text>
        <p:transclude p:project="project2" p:file_name="file2.xml">
            <p:transclude p:project="project3" p:file_name="file3.xml"/>
        </p:transclude>
    </tei:text>
</root>'''
        
        file_path = self._create_xml_file("main.xml", xml_content)
        result = get_file_references(file_path, self.project_dir)
        
        # Should find all nested references
        self.assertIn(self.project_dir / "project1" / "main.xml", result)
        self.assertIn(self.project_dir / "project2" / "file2.xml", result)
        self.assertIn(self.project_dir / "project3" / "file3.xml", result)


class TestExtractSources(unittest.TestCase):
    """Test source extraction from index.xml files."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name) / "project"
        self.test_dir.mkdir(parents=True)

    def _create_xml_file(self, project: str, filename: str, content: bytes) -> Path:
        """Helper to create an XML file in a project subdirectory."""
        project_dir = self.test_dir / project
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_extract_sources_with_valid_index(self):
        """Test extracting sources from a valid index.xml file with bibl elements."""
        index_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Test Book</tei:title>
            <tei:author>Test Author</tei:author>
            <tei:date>2023</tei:date>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        # Create a file in project1
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", index_content)
        
        result = extract_sources([file1])
        
        preamble, postamble = result
        self.assertIn(r'\begin{filecontents*}{job.bib}', preamble)
        self.assertIn(r'\addbibresource{job.bib}', preamble)
        self.assertIn(r'\printbibliography', postamble)
        self.assertIn(r'\renewcommand{\refname}{Sources}', postamble)
        # Should contain BibTeX entry with the actual source information
        self.assertIn('@', preamble)
        self.assertIn('Test Book', preamble)
        self.assertIn('Test Author', preamble)
        self.assertIn('2023', preamble)

    def test_extract_sources_no_bibl_elements(self):
        """Test handling of index.xml with no bibl elements."""
        index_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>No bibliography</tei:text>
</root>'''
        
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", index_content)
        
        preamble, postamble = extract_sources([file1])
        
        # Should return empty strings when no bibliography
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_extract_sources_missing_index_file(self):
        """Test handling of missing index.xml file (graceful skipping)."""
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        # Don't create index.xml
        
        # Should not raise exception
        preamble, postamble = extract_sources([file1])
        
        # Should return empty strings
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_extract_sources_invalid_xml(self):
        """Test handling of invalid XML in index file."""
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", b"not valid xml <")
        
        # Should not raise exception, should skip gracefully
        preamble, postamble = extract_sources([file1])
        
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_extract_sources_multiple_projects(self):
        """Test extracting sources from multiple projects with index files."""
        index1_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Book 1</tei:title>
            <tei:author>Author 1</tei:author>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        index2_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Book 2</tei:title>
            <tei:author>Author 2</tei:author>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        file2 = self._create_xml_file("project2", "doc2.xml", b"<root/>")
        index1 = self._create_xml_file("project1", "index.xml", index1_content)
        index2 = self._create_xml_file("project2", "index.xml", index2_content)
        
        result = extract_sources([file1, file2])
        
        preamble, postamble = result
        # Should contain bibliography entries from both projects
        self.assertIn(r'\begin{filecontents*}{job.bib}', preamble)
        # Should contain entries from both index files
        self.assertIn('Book 1', preamble)
        self.assertIn('Author 1', preamble)
        self.assertIn('Book 2', preamble)
        self.assertIn('Author 2', preamble)
        # Should have exactly 2 BibTeX entries (one from each project)
        bibtex_count = preamble.count('@')
        self.assertEqual(bibtex_count, 2, 
                         f"Expected exactly 2 BibTeX entries (one per project), but found {bibtex_count}")

    def test_extract_sources_deduplicates_index_files(self):
        """Test that same index.xml is only processed once."""
        index_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Test Book</tei:title>
            <tei:author>Test Author</tei:author>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        # Multiple files from same project should reference same index
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        file2 = self._create_xml_file("project1", "doc2.xml", b"<root/>")
        file3 = self._create_xml_file("project1", "doc3.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", index_content)
        
        result = extract_sources([file1, file2, file3])
        
        preamble, postamble = result
        # Should have bibliography
        self.assertIn(r'\begin{filecontents*}{job.bib}', preamble)
        # BibTeX should appear exactly once (deduplicated by set)
        # Count '@' symbols which appear at the start of each BibTeX entry
        bibtex_count = preamble.count('@')
        # Should have exactly one entry since all files reference the same index
        self.assertEqual(bibtex_count, 1, 
                         f"Expected exactly 1 BibTeX entry, but found {bibtex_count}")


class TestTransformXmlToTex(unittest.TestCase):
    """Test the main transform_xml_to_tex function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name) / "project"
        self.test_dir.mkdir(parents=True)

    def _create_xml_file(self, project: str, filename: str, content: bytes) -> Path:
        """Helper to create an XML file in a project subdirectory."""
        project_dir = self.test_dir / project
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_transform_xml_to_tex_basic(self):
        """Test basic XML to LaTeX transformation."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Hello World</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should produce LaTeX output
        self.assertIsInstance(result, str)
        self.assertIn(r'\documentclass{book}', result)
        self.assertIn(r'\begin{document}', result)
        self.assertIn('Hello World', result)
        self.assertIn(r'\end{document}', result)

    def test_transform_xml_to_tex_with_output_file(self):
        """Test transformation with output file specified."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Test content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        output_file = Path(self.temp_dir.name) / "output.tex"
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            with patch('sys.stdout'):
                transform_xml_to_tex(input_file, output_file=str(output_file))
        
        # Check that output file was created
        self.assertTrue(output_file.exists())
        content = output_file.read_text(encoding='utf-8')
        self.assertIn(r'\documentclass{book}', content)
        self.assertIn('Test content', content)

    def test_transform_xml_to_tex_integrates_licenses(self):
        """Test that transform integrates license extraction."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:publicationStmt>
                <tei:availability>
                    <tei:licence target="http://example.com/license">Test License</tei:licence>
                </tei:availability>
            </tei:publicationStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:text>
        <tei:body>
            <tei:p>Content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should include license section in postamble
        self.assertIn(r'\chapter{Legal}', result)
        self.assertIn('Test License', result)

    def test_transform_xml_to_tex_integrates_credits(self):
        """Test that transform integrates credit extraction."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:teiHeader>
        <tei:fileDesc>
            <tei:titleStmt>
                <tei:respStmt>
                    <tei:resp key="aut">Author</tei:resp>
                    <tei:name ref="urn:x-opensiddur:ns/contrib">Author Name</tei:name>
                </tei:respStmt>
            </tei:titleStmt>
        </tei:fileDesc>
    </tei:teiHeader>
    <tei:text>
        <tei:body>
            <tei:p>Content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should include credits section in postamble
        self.assertIn(r'\chapter{Contributor credits}', result)
        self.assertIn('Author Name', result)

    def test_transform_xml_to_tex_integrates_sources(self):
        """Test that transform integrates source extraction."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        index_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Source Book</tei:title>
            <tei:author>Source Author</tei:author>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        index_file = self._create_xml_file("project1", "index.xml", index_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should include bibliography in preamble and postamble
        self.assertIn(r'\addbibresource{job.bib}', result)
        self.assertIn(r'\printbibliography', result)

    def test_transform_xml_to_tex_handles_invalid_xml(self):
        """Test error handling for invalid XML."""
        from unittest.mock import patch, Mock
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        input_file = self._create_xml_file("project1", "invalid.xml", b"not valid xml <")
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            mock_exit = Mock()
            with patch('sys.exit', mock_exit):
                # The function should catch the exception and call sys.exit(1)
                transform_xml_to_tex(input_file)
                # Verify that sys.exit was called with exit code 1
                mock_exit.assert_called_once_with(1)

    def test_transform_xml_to_tex_with_stdout(self):
        """Test transformation output to stdout when output_file is None."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        mock_stdout = StringIO()
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            with patch('sys.stdout', mock_stdout):
                transform_xml_to_tex(input_file, output_file=None)
                output = mock_stdout.getvalue()
        
        # Should have written to stdout
        self.assertIn(r'\documentclass{book}', output)
        self.assertIn('Content', output)


class TestXSLTTransformation(unittest.TestCase):
    """Test XSLT transformation directly."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.xslt_file = Path(__file__).parent.parent.parent / "exporter" / "tex" / "xelatex.xslt"

    def test_xslt_tei_div(self):
        """Test div element conversion."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:div>
            <tei:head>Chapter Title</tei:head>
            <tei:p>Content</tei:p>
        </tei:div>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\part{Chapter Title}', result)
        self.assertIn('Content', result)

    def test_xslt_tei_p(self):
        """Test paragraph element conversion."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Paragraph text</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn('Paragraph text', result)

    def test_xslt_tei_milestone_chapter(self):
        """Test milestone with chapter unit."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:milestone unit="chapter" n="1"/>
            <tei:p>Text</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\chapter{1}', result)

    def test_xslt_tei_milestone_verse(self):
        """Test milestone with verse unit."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:milestone unit="verse" n="5"/>
            <tei:p>Text</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\textsuperscript{5}', result)

    def test_xslt_tei_choice(self):
        """Test choice element (kri/ktiv)."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:choice>
                    <j:read>read</j:read>
                    <j:written>written</j:written>
                </tei:choice>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\textit{read}', result)
        self.assertIn('(written)', result)

    def test_xslt_tei_emph(self):
        """Test emphasis element."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:emph>emphasized</tei:emph>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\emph{emphasized}', result)

    def test_xslt_rend_italic(self):
        """Test rend attribute with italic value."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:hi rend="italic">italic text</tei:hi>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\textit{italic text}', result)

    def test_xslt_rend_small_caps(self):
        """Test rend attribute with small-caps value."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:hi rend="small-caps">small caps</tei:hi>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\textsc{small caps}', result)

    def test_xslt_rend_superscript(self):
        """Test rend attribute with superscript value."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:hi rend="superscript">superscript</tei:hi>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\textsuperscript{superscript}', result)

    def test_xslt_rend_align_right(self):
        """Test rend attribute with align-right value."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:hi rend="align-right">right aligned</tei:hi>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\begin{flushright}', result)
        self.assertIn(r'\end{flushright}', result)

    def test_xslt_hebrew_language_inline(self):
        """Test Hebrew language handling for inline text."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:hi xml:lang="he">עברית</tei:hi>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\texthebrew{', result)
        self.assertIn('עברית', result)

    def test_xslt_hebrew_language_block(self):
        """Test Hebrew language handling for block elements."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
    <tei:text>
        <tei:body>
            <tei:div xml:lang="he">
                <tei:p>עברית</tei:p>
            </tei:div>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\begin{hebrew}', result)
        self.assertIn(r'\end{hebrew}', result)

    def test_xslt_tei_foreign(self):
        """Test foreign text element."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
    <tei:text>
        <tei:body>
            <tei:p>
                <tei:foreign xml:lang="he">עברית</tei:foreign>
                <tei:foreign xml:lang="la">Latin</tei:foreign>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\texthebrew{עברית}', result)
        self.assertIn(r'\textit{Latin}', result)

    def test_xslt_tei_note(self):
        """Test note element conversion to footnote."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                Text<tei:note>Note content</tei:note>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\footnote{Note content}', result)

    def test_xslt_tei_lb(self):
        """Test line break element."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                Line 1<tei:lb/>Line 2
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\\', result)

    def test_xslt_tei_pb(self):
        """Test page break element (should be skipped)."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>
                Text<tei:pb/>
            </tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        # Should not contain pb-related content
        self.assertIn('Text', result)

    def test_xslt_tei_lg_l(self):
        """Test line group and line elements (poetry)."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:lg>
                <tei:l>Line 1</tei:l>
                <tei:l>Line 2</tei:l>
            </tei:lg>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={"additional-preamble": "", "additional-postamble": ""})
        
        self.assertIn(r'\begin{verse}', result)
        self.assertIn(r'\end{verse}', result)
        self.assertIn('Line 1', result)
        self.assertIn('Line 2', result)

    def test_xslt_additional_preamble_postamble(self):
        """Test that additional-preamble and additional-postamble parameters work."""
        from opensiddur.common.xslt import xslt_transform_string
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Content</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        preamble = "\\usepackage{testpackage}\n"
        postamble = "\\chapter{Appendix}\nAppendix content\n"
        
        result = xslt_transform_string(self.xslt_file, xml_content,
            xslt_params={
                "additional-preamble": preamble,
                "additional-postamble": postamble
            })
        
        self.assertIn(preamble, result)
        self.assertIn(postamble, result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name) / "project"
        self.test_dir.mkdir(parents=True)

    def _create_xml_file(self, project: str, filename: str, content: bytes) -> Path:
        """Helper to create an XML file."""
        project_dir = self.test_dir / project
        project_dir.mkdir(parents=True, exist_ok=True)
        file_path = project_dir / filename
        file_path.write_bytes(content)
        return file_path

    def test_extract_sources_empty_xml(self):
        """Test extract_sources with empty XML file."""
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", b"<root/>")
        
        preamble, postamble = extract_sources([file1])
        
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_transform_xml_to_tex_minimal_structure(self):
        """Test transform with minimal valid XML structure."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text/>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should still produce valid LaTeX structure
        self.assertIn(r'\documentclass{book}', result)
        self.assertIn(r'\begin{document}', result)
        self.assertIn(r'\end{document}', result)

    def test_transform_xml_to_tex_special_characters(self):
        """Test transform with special characters that need LaTeX escaping."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Text with $special &amp; characters</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should handle special characters (XSLT will pass through)
        self.assertIn('Text with', result)

    def test_extract_sources_files_outside_project(self):
        """Test extract_sources with files outside project directory."""
        # Create a file outside the project structure
        outside_file = Path(self.temp_dir.name) / "outside.xml"
        outside_file.write_bytes(b"<root/>")
        
        # Should not crash, but skip the file gracefully
        # Note: extract_sources expects files in project directories, 
        # so outside files will be skipped
        preamble, postamble = extract_sources([outside_file])
        
        self.assertEqual(preamble, "")
        self.assertEqual(postamble, "")

    def test_transform_xml_to_tex_complex_nested_structure(self):
        """Test transform with complex nested divs."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:div>
                <tei:head>Section 1</tei:head>
                <tei:div>
                    <tei:head>Subsection</tei:head>
                    <tei:p>Nested content</tei:p>
                </tei:div>
            </tei:div>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should handle nested structures
        self.assertIn(r'\part{Section 1}', result)
        self.assertIn('Nested content', result)

    def test_transform_xml_to_tex_mixed_languages(self):
        """Test transform with mixed English and Hebrew content."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
    <tei:text>
        <tei:body>
            <tei:p>English text <tei:hi xml:lang="he">עברית</tei:hi> more English</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''.encode('utf-8')
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should handle mixed languages
        self.assertIn('English text', result)
        self.assertIn(r'\texthebrew{', result)
        self.assertIn('עברית', result)

    def test_extract_sources_multiple_files_same_project(self):
        """Test extract_sources with multiple files from same project."""
        index_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:listBibl>
        <tei:bibl>
            <tei:title>Book</tei:title>
            <tei:author>Author</tei:author>
        </tei:bibl>
    </tei:listBibl>
</root>'''
        
        file1 = self._create_xml_file("project1", "doc1.xml", b"<root/>")
        file2 = self._create_xml_file("project1", "doc2.xml", b"<root/>")
        index_file = self._create_xml_file("project1", "index.xml", index_content)
        
        preamble, postamble = extract_sources([file1, file2])
        
        # Should extract from same index file (deduplicated)
        self.assertIn(r'\begin{filecontents*}{job.bib}', preamble)

    def test_transform_xml_to_tex_empty_licenses_credits(self):
        """Test transform with no licenses or credits."""
        from unittest.mock import patch
        import opensiddur.exporter.tex.xelatex as xelatex_module
        
        xml_content = b'''<?xml version="1.0" encoding="UTF-8"?>
<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
    <tei:text>
        <tei:body>
            <tei:p>Content only</tei:p>
        </tei:body>
    </tei:text>
</tei:TEI>'''
        
        input_file = self._create_xml_file("project1", "input.xml", xml_content)
        
        with patch.object(xelatex_module, 'projects_source_root', self.test_dir):
            result = transform_xml_to_tex(input_file)
        
        # Should still produce valid LaTeX even without licenses/credits
        self.assertIn(r'\documentclass{book}', result)
        # Should not have empty metadata sections
        # (The postamble will be empty if no licenses/credits/sources)


if __name__ == '__main__':
    unittest.main()

