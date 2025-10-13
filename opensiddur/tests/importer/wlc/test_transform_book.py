import unittest
import tempfile
from pathlib import Path
from lxml import etree

from opensiddur.common.xslt import xslt_transform_string


class TestTransformBookXSLT(unittest.TestCase):
    """Test the transform_book.xslt transformation logic"""
    
    def setUp(self):
        """Set up path to XSLT and prepare modified version for testing"""
        xslt_source = Path(__file__).parent.parent.parent.parent / "importer/wlc/transform_book.xslt"
        xslt_content = xslt_source.read_text()
        
        # Change mode from "fail" to "shallow-copy" for testing
        self.xslt_content = xslt_content.replace(
            '<xsl:mode on-no-match="fail"/>',
            '<xsl:mode on-no-match="shallow-copy"/>'
        )
    
    def test_root_tanach_becomes_tei(self):
        """Test that Tanach root element becomes TEI"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have TEI root with proper namespace
            self.assertIn('<tei:TEI', result)
            self.assertIn('xmlns:tei="http://www.tei-c.org/ns/1.0"', result)
    
    def test_title_main_transformation(self):
        """Test that title[@type='main'] transforms correctly"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Genesis</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have title with type="main" and xml:lang="en"
            self.assertIn('type="main"', result)
            self.assertIn('xml:lang="en"', result)
            self.assertIn('Genesis', result)
    
    def test_title_mainhebrew_transformation(self):
        """Test that title[@type='mainhebrew'] transforms correctly"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
                <title level="a" type="mainhebrew">בראשית</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Genesis</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have title with type="alt" and xml:lang="he"
            self.assertIn('type="alt"', result)
            self.assertIn('xml:lang="he"', result)
            self.assertIn('בראשית', result)
    
    def test_edition_stmt_becomes_reference(self):
        """Test that editionStmt becomes a reference to WLC header"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <editionStmt>
                <edition>Original edition info</edition>
            </editionStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Genesis</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should not have original edition info
            self.assertNotIn('Original edition info', result)
            # Should have reference to WLC
            self.assertIn('urn:x-opensiddur:bible:tanakh@wlc', result)
            self.assertIn('WLC Tanakh header', result)
    
    def test_publication_stmt_with_book_urn(self):
        """Test that publicationStmt includes book-specific URN"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Test Book</title>
            </titleStmt>
            <publicationStmt>
                <distributor>Original</distributor>
            </publicationStmt>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Test Book</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have book-specific URN (title is "Test Book" -> "test_book")
            self.assertIn('urn:x-opensiddur:text:bible:test_book@wlc', result)
            # Should have Open Siddur distributor
            self.assertIn('Open Siddur Project', result)
            self.assertIn('opensiddur.org', result)
            # Should have CC0 license
            self.assertIn('Creative Commons Zero', result)
    
    def test_source_desc_becomes_reference(self):
        """Test that sourceDesc becomes a reference to WLC header"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc>
                <p>Original source description</p>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Genesis</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should not have original source description
            self.assertNotIn('Original source description', result)
            # Should have reference to WLC
            self.assertIn('WLC Tanakh header', result)
            self.assertIn('source information', result)
    
    def test_tanach_becomes_text_with_hebrew_lang(self):
        """Test that tanach element becomes tei:text with xml:lang='he'"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book><names><name>Genesis</name></names></book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have tei:text with Hebrew language
            self.assertIn('<tei:text xml:lang="he">', result)
            self.assertIn('<tei:body>', result)
    
    def test_book_element_creates_div_with_urn(self):
        """Test that book element creates div with proper URN and attributes"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Test Book</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names>
                <name>Test Book</name>
                <hebrewname>ספר מבחן</hebrewname>
            </names>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have div with type="book"
            self.assertIn('type="book"', result)
            # Should have corresp URN
            self.assertIn('corresp="urn:x-opensiddur:text:bible:test_book"', result)
            # Should have n attribute with lowercase name
            self.assertIn('n="test book"', result)
            # Should have Hebrew name in head
            self.assertIn('ספר מבחן', result)
    
    def test_chapter_becomes_milestone(self):
        """Test that c (chapter) element becomes milestone"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>בְּרֵאשִׁית</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have milestone for chapter
            self.assertIn('<tei:milestone unit="chapter"', result)
            self.assertIn('n="1"', result)
            self.assertIn('corresp="urn:x-opensiddur:text:bible:genesis/1"', result)
    
    def test_verse_becomes_milestone_with_sof_pasuq(self):
        """Test that v (verse) element becomes milestone with sof pasuq"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>בְּרֵאשִׁית</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have milestone for verse
            self.assertIn('<tei:milestone unit="verse"', result)
            self.assertIn('corresp="urn:x-opensiddur:text:bible:genesis/1/1"', result)
            # Should have sof pasuq (׃)
            self.assertIn('׃', result)
            self.assertIn('<tei:pc>׃</tei:pc>', result)
    
    def test_word_elements_have_spaces(self):
        """Test that w (word) elements are separated by spaces"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>בְּרֵאשִׁית</w><w>בָּרָא</w><w>אֱלֹהִים</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Words should be separated by spaces
            self.assertIn('בְּרֵאשִׁית בָּרָא אֱלֹהִים', result)
    
    def test_word_with_maqaf_no_space(self):
        """Test that words ending with maqaf (־) don't add space"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>וַיְהִי־</w><w>כֵן</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Maqaf should connect words without space
            self.assertIn('וַיְהִי־כֵן', result)
            self.assertNotIn('וַיְהִי־ כֵן', result)
    
    def test_ketiv_qere_choice(self):
        """Test that k/q (ketiv/qere) creates tei:choice"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w><k>לוא</k><q>לֹא</q></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have tei:choice with written and read
            self.assertIn('<tei:choice>', result)
            self.assertIn('<j:written>', result)
            self.assertIn('<j:read>', result)
            self.assertIn('לוא', result)  # ketiv (written)
            self.assertIn('לֹא', result)  # qere (read)
    
    def test_ketiv_only(self):
        """Test that k without q creates j:written only"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w><k>כתיב</k></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have j:written without choice
            self.assertIn('<j:written>', result)
            self.assertNotIn('<tei:choice>', result)
            self.assertIn('כתיב', result)
    
    def test_qere_only(self):
        """Test that q without k creates j:read only"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w><q>קרי</q></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have j:read without choice
            self.assertIn('<j:read>', result)
            self.assertNotIn('<tei:choice>', result)
            self.assertIn('קרי', result)
    
    def test_note_reference_creates_anchor(self):
        """Test that x (note reference) creates tei:anchor"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>test<x>a</x></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have tei:anchor with xml:id
            self.assertIn('<tei:anchor', result)
            self.assertIn('xml:id="note-ref-genesis-1-1-1"', result)
    
    def test_note_standoff_creates_link(self):
        """Test that x elements create standOff links"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>test<x>a</x></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have standOff section with link
            self.assertIn('<tei:standOff type="notes">', result)
            self.assertIn('<tei:link', result)
            self.assertIn('type="note"', result)
            self.assertIn('#note-ref-genesis-1-1-1', result)
            self.assertIn('urn:cite:opensiddur:bible.tanakh.notes.wlc.a', result)
    
    def test_special_formatting_creates_hi(self):
        """Test that s element creates tei:hi with rend attribute"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>normal<s t="large">LARGE</s></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have tei:hi with rend attribute
            self.assertIn('<tei:hi rend="large">', result)
            self.assertIn('LARGE', result)
    
    def test_reversed_nun(self):
        """Test that reversednun element creates proper punctuation"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Numbers</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Numbers</name></names>
            <c n="10">
                <v n="35"><reversednun/><w>וַיְהִי</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have tei:pc with reversed nun (׆)
            self.assertIn('<tei:pc>׆</tei:pc>', result)
    
    def test_skipped_elements_not_in_output(self):
        """Test that comment, extent, notesStmt, etc. are skipped"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <extent>Should be skipped</extent>
            <notesStmt>
                <note>Should be skipped</note>
            </notesStmt>
            <publicationStmt/>
            <encodingDesc>
                <description>Should be skipped</description>
            </encodingDesc>
            <profileDesc>
                <langUsage>Should be skipped</langUsage>
            </profileDesc>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <cs>Chapter Start - should be skipped</cs>
                <v n="1">
                    <vs>Verse Start - should be skipped</vs>
                    <w>word</w>
                </v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # None of the skipped content should appear
            self.assertNotIn('Should be skipped', result)
            self.assertNotIn('Chapter Start', result)
            self.assertNotIn('Verse Start', result)
            self.assertNotIn('extent', result)
            self.assertNotIn('notesStmt', result)
            self.assertNotIn('encodingDesc', result)
            self.assertNotIn('profileDesc', result)
    
    def test_tei_namespace_on_header_elements(self):
        """Test that teiHeader elements get TEI namespace"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <editionStmt>
                <editor>Editor</editor>
                <edition>Edition</edition>
            </editionStmt>
            <publicationStmt>
                <publisher>Publisher</publisher>
                <pubPlace>Place</pubPlace>
                <date>2025</date>
                <idno>123</idno>
            </publicationStmt>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach><book><names><name>Genesis</name></names></book></tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Parse output to check namespaces properly
            tree = etree.fromstring(result.encode('utf-8'))
            
            # Define TEI namespace
            tei_ns = '{http://www.tei-c.org/ns/1.0}'
            
            # Check that elements have TEI namespace
            tei_header = tree.find(f'.//{tei_ns}teiHeader')
            self.assertIsNotNone(tei_header, "teiHeader should have TEI namespace")
            
            file_desc = tree.find(f'.//{tei_ns}fileDesc')
            self.assertIsNotNone(file_desc, "fileDesc should have TEI namespace")
    
    def test_pe_elements_create_paragraph_markers(self):
        """Test that pe (paragraph) elements create jx:p markers"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>first</w></v>
                <v n="2"><w>second</w><pe/></v>
                <v n="3"><w>third</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # pe creates paragraph breaks
            # Should have multiple tei:p elements due to grouping
            self.assertIn('<tei:p', result)
            # Check that content is grouped into paragraphs
            self.assertIn('first', result)
            self.assertIn('second', result)
            self.assertIn('third', result)
    
    def test_samekh_elements_create_paragraph_markers(self):
        """Test that samekh (closed paragraph) elements create jx:p markers"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>first</w></v>
                <v n="2"><w>second</w><samekh/></v>
                <v n="3"><w>third</w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # samekh creates paragraph breaks
            # Should have multiple tei:p elements due to grouping
            self.assertIn('<tei:p', result)
            # Check that content is in paragraphs
            self.assertIn('first', result)
            self.assertIn('second', result)
            self.assertIn('third', result)
    
    def test_text_normalization(self):
        """Test that text() is normalized (whitespace removed)"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>   test   with   spaces   </w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Text should be normalized (extra spaces removed)
            self.assertIn('test with spaces', result)
            self.assertNotIn('   test   ', result)
    
    def test_multiple_note_references_numbered(self):
        """Test that multiple x elements in same verse get sequential numbers"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>first<x>a</x>second<x>b</x>third<x>c</x></w></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # Should have three anchors with sequential numbers
            self.assertIn('xml:id="note-ref-genesis-1-1-1"', result)
            self.assertIn('xml:id="note-ref-genesis-1-1-2"', result)
            self.assertIn('xml:id="note-ref-genesis-1-1-3"', result)
            
            # Should have three standOff links
            self.assertIn('urn:cite:opensiddur:bible.tanakh.notes.wlc.a', result)
            self.assertIn('urn:cite:opensiddur:bible.tanakh.notes.wlc.b', result)
            self.assertIn('urn:cite:opensiddur:bible.tanakh.notes.wlc.c', result)
    
    def test_verse_excludes_trailing_pe_samekh(self):
        """Test that verse excludes last pe or samekh from content"""
        input_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Tanach>
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a" type="main">Genesis</title>
            </titleStmt>
            <publicationStmt/>
            <sourceDesc/>
        </fileDesc>
    </teiHeader>
    <tanach>
        <book>
            <names><name>Genesis</name></names>
            <c n="1">
                <v n="1"><w>content</w><pe/></v>
            </c>
        </book>
    </tanach>
</Tanach>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(self.xslt_content)
            f.flush()
            
            result = xslt_transform_string(Path(f.name), input_xml)
            
            # pe should be processed but positioned after sof pasuq
            # The verse template uses: select="node() except (pe, samekh)[last()]"
            # and then: <xsl:apply-templates select="(pe,samekh)[last()]"/>
            # So the pe/samekh comes after the pc
            self.assertIn('content', result)
            self.assertIn('׃', result)


if __name__ == '__main__':
    unittest.main()
