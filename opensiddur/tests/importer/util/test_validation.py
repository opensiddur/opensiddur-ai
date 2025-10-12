import unittest
import tempfile
from pathlib import Path
from lxml import etree

from opensiddur.importer.util.validation import schematron_validate, relaxng_validate, validate


class TestSchematronValidate(unittest.TestCase):
    """Test the schematron_validate function"""
    
    def test_schematron_validation_success(self):
        """Test successful schematron validation (no failed asserts)"""
        # Create a simple schematron XSLT that checks for required element
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:output method="xml" indent="yes"/>
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <!-- No failed-assert means valid -->
            <xsl:if test="not(//required)">
                <svrl:failed-assert location="root">
                    <svrl:text>Missing required element</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # XML that should pass (has required element)
        valid_xml = '<root><required>present</required></root>'
        
        # Test with string input (no temp file needed)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(schematron_xslt)
            f.flush()
            
            is_valid, errors = schematron_validate(valid_xml, Path(f.name))
            
            # Should be valid with no errors
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])
    
    def test_schematron_validation_failure(self):
        """Test failed schematron validation (with failed asserts)"""
        # Create a schematron XSLT that requires a specific attribute
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:output method="xml" indent="yes"/>
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <xsl:if test="not(//item[@required='yes'])">
                <svrl:failed-assert location="/root/item">
                    <svrl:text>Item must have required='yes' attribute</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # XML that should fail (missing required attribute)
        invalid_xml = '<root><item>content</item></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(schematron_xslt)
            f.flush()
            
            is_valid, errors = schematron_validate(invalid_xml, Path(f.name))
            
            # Should be invalid with errors
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
            self.assertIn('/root/item', errors[0])
            self.assertIn('required', errors[0])
    
    def test_schematron_multiple_errors(self):
        """Test schematron validation with multiple failed asserts"""
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:output method="xml" indent="yes"/>
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <xsl:if test="not(//title)">
                <svrl:failed-assert location="/root">
                    <svrl:text>Missing title element</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
            <xsl:if test="not(//author)">
                <svrl:failed-assert location="/root">
                    <svrl:text>Missing author element</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # XML missing both title and author
        invalid_xml = '<root><content>data</content></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(schematron_xslt)
            f.flush()
            
            is_valid, errors = schematron_validate(invalid_xml, Path(f.name))
            
            # Should have 2 errors
            self.assertFalse(is_valid)
            self.assertEqual(len(errors), 2)
            # Both errors should mention /root
            self.assertTrue(all('/root' in err for err in errors))
    
    def test_schematron_successful_report(self):
        """Test schematron with successful-report (also indicates error)"""
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:output method="xml" indent="yes"/>
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <!-- successful-report also counts as a validation issue -->
            <xsl:if test="//deprecated">
                <svrl:successful-report location="/root/deprecated">
                    <svrl:text>Deprecated element found</svrl:text>
                </svrl:successful-report>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # XML with deprecated element
        xml_with_issue = '<root><deprecated>old stuff</deprecated></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as f:
            f.write(schematron_xslt)
            f.flush()
            
            is_valid, errors = schematron_validate(xml_with_issue, Path(f.name))
            
            # Should be invalid
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
            self.assertIn('Deprecated', errors[0])


class TestRelaxNGValidate(unittest.TestCase):
    """Test the relaxng_validate function"""
    
    def test_relaxng_validation_success_with_string_schema(self):
        """Test successful RelaxNG validation with schema as string"""
        # Create a simple RelaxNG schema
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="child">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Valid XML according to schema
        valid_xml = '<root><child>content</child></root>'
        
        is_valid, errors = relaxng_validate(valid_xml, relaxng_schema)
        
        # Should be valid
        self.assertTrue(is_valid, f"Expected valid but got errors: {errors}")
        self.assertEqual(errors, [])
    
    def test_relaxng_validation_failure_with_string_schema(self):
        """Test failed RelaxNG validation with schema as string"""
        # Create a RelaxNG schema requiring specific structure
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="required">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Invalid XML (missing required element)
        invalid_xml = '<root><optional>content</optional></root>'
        
        is_valid, errors = relaxng_validate(invalid_xml, relaxng_schema)
        
        # Should be invalid with errors
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_relaxng_validation_success_with_etree(self):
        """Test RelaxNG validation with lxml ElementTree input"""
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="child">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Valid XML as ElementTree
        valid_xml = '<root><child>content</child></root>'
        xml_doc = etree.fromstring(valid_xml)
        
        is_valid, errors = relaxng_validate(xml_doc, relaxng_schema)
        
        # Should be valid
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
    
    def test_relaxng_with_attributes(self):
        """Test RelaxNG validation with required attributes"""
        # Schema requiring specific attribute
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <attribute name="id"/>
            <text/>
        </element>
    </start>
</grammar>'''
        
        # Valid XML with attribute
        valid_xml = '<root id="123">content</root>'
        is_valid, errors = relaxng_validate(valid_xml, relaxng_schema)
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
        
        # Invalid XML without attribute
        invalid_xml = '<root>content</root>'
        is_valid, errors = relaxng_validate(invalid_xml, relaxng_schema)
        
        # Should be invalid
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_relaxng_with_file_path(self):
        """Test RelaxNG validation with schema file path"""
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <text/>
        </element>
    </start>
</grammar>'''
        
        valid_xml = '<root>content</root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rng') as schema_f:
            schema_f.write(relaxng_schema)
            schema_f.flush()
            
            is_valid, errors = relaxng_validate(valid_xml, Path(schema_f.name))
            
            # Should be valid
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])


class TestValidateFunction(unittest.TestCase):
    """Test the main validate function that combines both validators"""
    
    def test_validate_success_both_schemas_as_strings(self):
        """Test that validate passes when both RelaxNG and Schematron pass"""
        # Simple RelaxNG schema
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="item">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Simple Schematron that passes if item has content
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <xsl:if test="string-length(//item/text()) = 0">
                <svrl:failed-assert location="/root/item">
                    <svrl:text>Item must have content</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # Valid XML
        valid_xml = '<root><item>content</item></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                valid_xml,
                schema=relaxng_schema,
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be valid
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])
    
    def test_validate_fails_on_relaxng_error(self):
        """Test that validate fails if RelaxNG validation fails"""
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="required">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Passing schematron
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output/>
    </xsl:template>
</xsl:stylesheet>'''
        
        # Invalid for RelaxNG (missing required element)
        invalid_xml = '<root><optional>content</optional></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                invalid_xml,
                schema=relaxng_schema,
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be invalid due to RelaxNG
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
    
    def test_validate_fails_on_schematron_error(self):
        """Test that validate fails if Schematron validation fails"""
        # Simple RelaxNG that allows root with optional child
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <zeroOrMore>
                <element name="optional">
                    <text/>
                </element>
            </zeroOrMore>
        </element>
    </start>
</grammar>'''
        
        # Strict schematron
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <xsl:if test="not(//mandatory)">
                <svrl:failed-assert location="/root">
                    <svrl:text>Missing mandatory element</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # Invalid for Schematron (missing mandatory)
        invalid_xml = '<root><optional>content</optional></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                invalid_xml,
                schema=relaxng_schema,
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be invalid due to Schematron
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
            self.assertIn('mandatory', errors[0])
    
    def test_validate_combines_errors_from_both(self):
        """Test that validate combines errors from both validators"""
        # RelaxNG requiring 'required' element
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="required">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        # Schematron requiring 'mandatory' element
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output>
            <xsl:if test="not(//mandatory)">
                <svrl:failed-assert location="/root">
                    <svrl:text>Missing mandatory</svrl:text>
                </svrl:failed-assert>
            </xsl:if>
        </svrl:schematron-output>
    </xsl:template>
</xsl:stylesheet>'''
        
        # Invalid for both validators
        invalid_xml = '<root><other>content</other></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                invalid_xml,
                schema=relaxng_schema,
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be invalid with errors from both
            self.assertFalse(is_valid)
            # Should have errors from both validators
            self.assertGreater(len(errors), 1)
    
    def test_validate_with_file_path(self):
        """Test validate with XML file path instead of string"""
        # Simple schema
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <text/>
        </element>
    </start>
</grammar>'''
        
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output/>
    </xsl:template>
</xsl:stylesheet>'''
        
        valid_xml = '<?xml version="1.0"?><root>content</root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as xml_f, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            
            xml_f.write(valid_xml)
            xml_f.flush()
            
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                Path(xml_f.name),
                schema=relaxng_schema,
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be valid
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])
    
    def test_validate_with_schema_files(self):
        """Test validate with both schemas as file paths"""
        relaxng_schema = '''<?xml version="1.0" encoding="UTF-8"?>
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
    <start>
        <element name="root">
            <element name="item">
                <text/>
            </element>
        </element>
    </start>
</grammar>'''
        
        schematron_xslt = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
    
    <xsl:template match="/">
        <svrl:schematron-output/>
    </xsl:template>
</xsl:stylesheet>'''
        
        valid_xml = '<root><item>content</item></root>'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rng') as rng_f, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.xslt') as sch_f:
            
            rng_f.write(relaxng_schema)
            rng_f.flush()
            
            sch_f.write(schematron_xslt)
            sch_f.flush()
            
            is_valid, errors = validate(
                valid_xml,
                schema_file=Path(rng_f.name),
                schematron_xslt_file=Path(sch_f.name)
            )
            
            # Should be valid
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
