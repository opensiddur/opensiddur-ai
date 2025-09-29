# JPS1917 MediaWiki to XML Converter

This directory contains a modular converter for transforming 1917 JPS Wikisource content from MediaWiki syntax to XML.

## Overview

Based on comprehensive analysis of the 1917 JPS Wikisource project, this converter handles:

- **30+ MediaWiki Templates** (50,000+ instances)
- **11 HTML/XML Tags** (25,000+ instances)
- **Modular Architecture** for easy customization

## Files

- `template_finder.py` - Analysis tools for identifying templates and tags
- `mediawiki_processor.py` - Main converter with modular handlers
- `convert_wikisource.py` - Entry point for conversion (to be implemented)
- `book.xslt` - XSLT transformations for final XML processing

## Template Analysis Results

### Most Common Templates (by usage count):
1. **`verse`** (22,295 uses) - Biblical verse formatting
2. **`sc`** (6,986 uses) - Small caps text
3. **`c`** (1,280 uses) - Center alignment
4. **`larger`** (1,352 uses) - Larger text
5. **`rule`** (1,113 uses) - Horizontal rules
6. **`rh`** (1,101 uses) - Right-aligned headers
7. **`anchor`** (910 uses) - Page anchors
8. **`dropinitial`** (927 uses) - Drop caps
9. **`dhr`** (1,586 uses) - Double horizontal rules
10. **`smallrefs`** (745 uses) - Small references

### Template Categories:
- **Text Formatting**: `sc`, `larger`, `x-larger`, `xx-larger`, `xxx-larger`, `smaller`
- **Layout**: `c`, `right`, `rule`, `dhr`, `nop`
- **Biblical Content**: `verse`, `rh`, `dropinitial`
- **Navigation**: `anchor`, `anchor+`
- **Language**: `lang`
- **References**: `smallrefs`
- **Special**: `hws`, `hwe`, `***`, `reconstruct`, `SIC`, `sup`, `bar`

## Tag Analysis Results

### Most Common Tags (by usage count):
1. **`dd`** (21,100 uses) - Definition descriptions
2. **`noinclude`** (2,303 uses) - Content not included in transclusions
3. **`pagequality`** (1,152 uses) - Page quality metadata
4. **`ref`** (224 uses) - References/footnotes
5. **`td`** (222 uses) - Table data cells
6. **`i`** (193 uses) - Italic text
7. **`tr`** (96 uses) - Table rows
8. **`br`** (36 uses) - Line breaks
9. **`section`** (32 uses) - Section divisions
10. **`table`** (5 uses) - Table containers
11. **`span`** (1 use) - Inline styling

## Usage

### Basic Usage

```python
from opensiddur.converters.jps1917.mediawiki_processor import create_processor

# Create processor
processor = create_processor()

# Process MediaWiki content
result = processor.process_wikitext(wikitext_content)

print(result.xml_content)
print("Warnings:", result.warnings)
print("Errors:", result.errors)
```

### Custom Handlers

```python
# Add custom template handler
def handle_custom_template(template):
    return f"<custom>{template.get(1, '')}</custom>"

processor.add_template_handler('custom', handle_custom_template)

# Add custom tag handler
def handle_custom_tag(tag):
    return f"<custom-tag>{tag.contents}</custom-tag>"

processor.add_tag_handler('custom', handle_custom_tag)
```

## Template Conversions

| MediaWiki Template | XML Output | Description |
|-------------------|------------|-------------|
| `{{sc\|text}}` | `<hi rend="small-caps">text</hi>` | Small caps |
| `{{larger\|text}}` | `<hi rend="larger">text</hi>` | Larger text |
| `{{c\|text}}` | `<p rend="center">text</p>` | Center alignment |
| `{{verse\|ch\|v\|text}}` | `<l n="ch.v">text</l>` | Biblical verse |
| `{{rule}}` | `<milestone unit="hr"/>` | Horizontal rule |
| `{{anchor\|name}}` | `<anchor xml:id="name"/>` | Page anchor |
| `{{lang\|code\|text}}` | `<foreign xml:lang="code">text</foreign>` | Foreign language |

## Tag Conversions

| HTML Tag | XML Output | Description |
|----------|------------|-------------|
| `<i>text</i>` | `<hi rend="italic">text</hi>` | Italic text |
| `<br>` | `<lb/>` | Line break |
| `<ref name="id">text</ref>` | `<note xml:id="id">text</note>` | Reference |
| `<noinclude>text</noinclude>` | `<!-- noinclude: text -->` | Excluded content |
| `<table>...</table>` | `<table>...</table>` | Table structure |
| `<td>text</td>` | `<cell>text</cell>` | Table cell |

## Architecture

### Modular Design

The processor uses a modular architecture with separate handlers for:

1. **Template Handlers** - Convert MediaWiki templates to XML
2. **Tag Handlers** - Convert HTML/XML tags to TEI XML
3. **Preprocessors** - Clean and normalize input
4. **Postprocessors** - Validate and finalize output

### Processing Pipeline

1. **Preprocessing** - Normalize whitespace, handle special characters
2. **Template Processing** - Convert MediaWiki templates
3. **Tag Processing** - Convert HTML/XML tags
4. **Postprocessing** - Validate XML structure, cleanup

### Extensibility

- **Custom Handlers**: Add new template/tag handlers easily
- **Custom Processors**: Add preprocessing/postprocessing steps
- **Validation**: Built-in error handling and warnings
- **Metadata**: Extract and preserve document metadata

## Error Handling

The processor provides comprehensive error handling:

- **Warnings**: Unknown templates/tags, non-fatal issues
- **Errors**: Processing failures, malformed content
- **Metadata**: Processing statistics and information

## Future Enhancements

- **Schema Validation**: Validate against TEI schema
- **Batch Processing**: Process multiple pages efficiently
- **Custom Output**: Support for different XML formats
- **Performance**: Optimize for large document processing