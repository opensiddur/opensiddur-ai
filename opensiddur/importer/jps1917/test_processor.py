#!/usr/bin/env python3
"""
Test script for the MediaWiki processor

This script demonstrates the conversion of various MediaWiki templates and tags
to XML based on the analysis of the 1917 JPS Wikisource content.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from opensiddur.importer.jps1917.mediawiki_processor import create_processor


def test_basic_conversion():
    """Test basic template and tag conversion"""
    processor = create_processor()
    
    # Sample MediaWiki content with various templates and tags
    sample_wikitext = """
{{verse|1|1|In the beginning God created the heaven and the earth.}}
{{sc|Genesis}} {{c|Chapter 1}}
{{larger|The Creation}}
{{rule}}
<ref name="gen1">This is a reference</ref>
<noinclude>This is not included</noinclude>
<i>Italic text</i>
<br>
"""
    
    print("=" * 60)
    print("BASIC CONVERSION TEST")
    print("=" * 60)
    print("Input MediaWiki:")
    print(sample_wikitext)
    print("\nOutput XML:")
    
    result = processor.process_wikitext(sample_wikitext)
    print(result.xml_content)
    
    if result.warnings:
        print(f"\nWarnings: {result.warnings}")
    if result.errors:
        print(f"\nErrors: {result.errors}")


def test_advanced_conversion():
    """Test more complex conversion scenarios"""
    processor = create_processor()
    
    # More complex MediaWiki content
    complex_wikitext = """
{{dropinitial|I}}n the beginning was the Word.
{{lang|he|בראשית}} {{lang|en|In the beginning}}
{{anchor|gen1-1}}
{{rh|Genesis 1:1}}
{{dhr}}
<table>
<tr><td>Chapter</td><td>Verse</td></tr>
<tr><td>1</td><td>1</td></tr>
</table>
{{smallrefs}}
<ref name="footnote1">This is a footnote</ref>
"""
    
    print("\n" + "=" * 60)
    print("ADVANCED CONVERSION TEST")
    print("=" * 60)
    print("Input MediaWiki:")
    print(complex_wikitext)
    print("\nOutput XML:")
    
    result = processor.process_wikitext(complex_wikitext)
    print(result.xml_content)
    
    if result.warnings:
        print(f"\nWarnings: {result.warnings}")
    if result.errors:
        print(f"\nErrors: {result.errors}")


def test_custom_handler():
    """Test adding custom handlers"""
    processor = create_processor()
    
    # Add a custom template handler
    def handle_custom_template(template):
        content = str(template.get(1, ''))
        return f'<custom rend="special">{content}</custom>'
    
    processor.add_template_handler('custom', handle_custom_template)
    
    # Add a custom tag handler
    def handle_custom_tag(tag):
        content = str(tag.contents) if tag.contents else ''
        return f'<custom-tag>{content}</custom-tag>'
    
    processor.add_tag_handler('custom', handle_custom_tag)
    
    # Test custom handlers
    custom_wikitext = """
{{custom|This is a custom template}}
<custom>This is a custom tag</custom>
"""
    
    print("\n" + "=" * 60)
    print("CUSTOM HANDLER TEST")
    print("=" * 60)
    print("Input MediaWiki:")
    print(custom_wikitext)
    print("\nOutput XML:")
    
    result = processor.process_wikitext(custom_wikitext)
    print(result.xml_content)
    
    if result.warnings:
        print(f"\nWarnings: {result.warnings}")
    if result.errors:
        print(f"\nErrors: {result.errors}")


def main():
    """Run all tests"""
    print("MediaWiki to XML Processor Test Suite")
    print("Based on 1917 JPS Wikisource Analysis")
    print("=" * 60)
    
    try:
        test_basic_conversion()
        test_advanced_conversion()
        test_custom_handler()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
