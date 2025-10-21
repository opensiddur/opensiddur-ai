#!/usr/bin/env python3
"""
Tests for opensiddur.exporter.tex.xelatex module
"""

import unittest
import tempfile
from pathlib import Path
from lxml import etree

from opensiddur.exporter.tex.xelatex import (
    extract_licenses,
    group_licenses,
    licenses_to_tex,
    extract_credits,
    group_credits,
    credits_to_tex,
    get_file_references,
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


if __name__ == '__main__':
    unittest.main()

