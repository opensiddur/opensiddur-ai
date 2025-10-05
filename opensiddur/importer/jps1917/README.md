# JPS1917 MediaWiki to TEI Converter

This directory contains a complete converter for transforming 1917 JPS Wikisource content from MediaWiki syntax to TEI XML.

## Overview

Based on comprehensive analysis of the 1917 JPS Wikisource project, this converter handles:

- **30+ MediaWiki Templates** (50,000+ instances)
- **11 HTML/XML Tags** (25,000+ instances)
- **Complete Workflow** from MediaWiki to TEI XML
- **Section-based Processing** for multi-book pages

## Workflow

The conversion process follows a three-stage pipeline:

1. **MediaWiki Processing** (`mediawiki_processor.py`) - Converts MediaWiki syntax to intermediate XML
2. **XSLT Transformation** (`mediawiki_to_tei.xslt`) - Transforms intermediate XML to TEI XML
3. **Batch Processing** (`convert_wikisource.py`) - Orchestrates the complete conversion workflow

## Files

- `convert_wikisource.py` - **Main entry point** for batch conversion
- `mediawiki_processor.py` - MediaWiki to XML processor with modular handlers
- `mediawiki_to_tei.xslt` - XSLT transformation to TEI XML
- `template_finder.py` - Analysis tools for identifying templates and tags


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

### Command Line (Recommended)

```bash
# Run the complete conversion workflow from command line
poetry run python -m opensiddur.importer.jps1917.convert_wikisource
```

### Complete Workflow (Programmatic)

```python
# Run the complete conversion workflow
from opensiddur.importer.jps1917.convert_wikisource import main

# Convert all books to TEI XML
main()
```

### Individual Book Conversion

```python
from opensiddur.importer.jps1917.convert_wikisource import book_file, Book

# Convert a specific book
book = Book(
    book_name_en="Genesis",
    book_name_he="בראשית", 
    file_name="genesis",
    start_page=25,  # Page 25 in the source
    end_page=86,    # Page 86 in the source
    is_section=False
)

# Generate TEI XML file
tei_content = book_file(book)
```

### Section-based Processing

For books that appear on the same page (like The Twelve prophets):

```python
book = Book(
    book_name_en="Obadiah",
    book_name_he="עובדיה",
    file_name="obadiah", 
    start_page=734,
    end_page=736,
    is_section=True  # Enable section filtering
)
```

### Direct MediaWiki Processing

```python
from opensiddur.importer.jps1917.mediawiki_processor import create_processor

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

| MediaWiki Template | Intermediate XML | Final TEI XML | Description |
|-------------------|------------------|---------------|-------------|
| `{{sc\|text}}` | `<sc>text</sc>` | `<tei:hi rend="small-caps">text</tei:hi>` | Small caps |
| `{{larger\|text}}` | `<larger>text</larger>` | `<tei:hi rend="large">text</tei:hi>` | Larger text |
| `{{c\|text}}` | `<c>text</c>` | `<tei:head>text</tei:head>` | Center alignment (when with larger) |
| `{{verse\|ch\|v\|text}}` | `<verse chapter="ch" verse="v">text</verse>` | `<tei:milestone unit="verse" n="v" corresp="urn:x-opensiddur:text:bible:book/ch/v"/>` | Biblical verse |
| `{{rule}}` | `<rule/>` | `<tei:lb type="double"/>` | Horizontal rule |
| `{{anchor\|name}}` | `<anchor name="name"/>` | `<tei:anchor xml:id="name"/>` | Page anchor |
| `{{lang\|code\|text}}` | `<lang code="code">text</lang>` | `<tei:foreign xml:lang="code">text</tei:foreign>` | Foreign language |
| `{{float right\|text}}` | `<float_right>text</float_right>` | `<tei:lb type="last"/>text` | Right-aligned text |

## Tag Conversions

| HTML Tag | Intermediate XML | Final TEI XML | Description |
|----------|------------------|---------------|-------------|
| `<i>text</i>` | `<i>text</i>` | `<tei:hi rend="italic">text</tei:hi>` | Italic text |
| `<br>` | `<br/>` | `<tei:lb/>` | Line break |
| `<ref name="id">text</ref>` | `<ref name="id">text</ref>` | `<tei:anchor xml:id="ref-1"/><tei:note target="#ref-1">text</tei:note>` | Reference |
| `<noinclude>text</noinclude>` | `<noinclude>text</noinclude>` | `<!-- excluded -->` | Excluded content |
| `<dd>text</dd>` | `<dd>text</dd>` | `<tei:lb/>` | Definition description (line break) |
| `<section begin="book">` | `<section begin="book"/>` | `<!-- section marker -->` | Section boundary |

## Processing Pipeline

### Stage 1: MediaWiki Processing (`mediawiki_processor.py`)

1. **Preprocessing**: Normalize whitespace, handle special characters, extract metadata
2. **Template Processing**: Convert MediaWiki templates to intermediate XML
3. **Tag Processing**: Convert HTML/XML tags to intermediate XML  
4. **Wikilink Processing**: Convert wikilinks to `__link__` elements
5. **Postprocessing**: Validate XML structure, finalize metadata

### Stage 2: XSLT Transformation (`mediawiki_to_tei.xslt`)

1. **Section Filtering**: For `is_section=True` books, filter content between section markers
2. **TEI Conversion**: Transform intermediate XML to TEI XML
3. **Reference Processing**: Move footnotes to standoff markup
4. **Structure Building**: Create proper TEI document structure

### Stage 3: Batch Processing (`convert_wikisource.py`)

1. **Page Retrieval**: Fetch MediaWiki pages from Wikisource
2. **Book Processing**: Process each book with appropriate parameters
3. **Index Generation**: Create index files with transclusion references
4. **File Output**: Write TEI XML files to project directory

## Architecture

### Three-Stage Pipeline

The converter uses a three-stage architecture:

1. **MediaWiki Processor** (`mediawiki_processor.py`)
   - Modular template and tag handlers
   - Preprocessing and postprocessing stages
   - Wikilink processing with nested template support
   - Error handling and validation

2. **XSLT Transformer** (`mediawiki_to_tei.xslt`)
   - Section-based content filtering
   - TEI XML structure generation
   - Reference processing and standoff markup
   - Template matching with priority system

3. **Batch Orchestrator** (`convert_wikisource.py`)
   - Page retrieval from Wikisource
   - Book and index file generation
   - TEI header creation
   - File output management

### Key Features

- **Section Processing**: Handle multi-book pages with section markers
- **Nested Templates**: Process templates within wikilinks and other contexts
- **Error Recovery**: Graceful handling of malformed content
- **Metadata Preservation**: Extract and maintain document information
- **Extensibility**: Easy addition of new handlers and processors

## Error Handling

The processor provides comprehensive error handling:

- **Warnings**: Unknown templates/tags, non-fatal issues
- **Errors**: Processing failures, malformed content
- **Metadata**: Processing statistics and information

## Current Status

✅ **Completed Features**:
- Complete MediaWiki to TEI conversion pipeline
- Section-based processing for multi-book pages
- Nested template processing within wikilinks
- Comprehensive template and tag handling
- Batch processing with book and index generation
- TEI XML output with proper structure

## Future Enhancements

- **Schema Validation**: Validate against TEI schema
- **Performance Optimization**: Optimize for large document processing
- **Custom Output Formats**: Support for different XML formats
- **Advanced Error Recovery**: Better handling of edge cases
- **Parallel Processing**: Multi-threaded batch processing