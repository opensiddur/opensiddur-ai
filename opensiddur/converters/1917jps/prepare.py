#!/usr/bin/env python3
"""
Prepare 1917 JPS XML files by standardizing filenames and page breaks.

This script processes XML files from the 1917 JPS source, renames them to match
the WLC naming convention, and replaces sequences of four newlines with
<page-break/> elements.
"""
import os
from pathlib import Path
import re
from typing import Dict, Optional

# Mapping from 1917jps filenames to wlc filenames
FILENAME_MAPPING = {
    'GENESIS': 'genesis',
    'EXODUS': 'exodus',
    'LEVITICUS': 'leviticus',
    'NUMBERS': 'numbers',
    'DEUTERONOMY': 'deuteronomy',
    'JOSHUA': 'joshua',
    'JUDGES': 'judges',
    'RUTH': 'ruth',
    'FIRST SAMUEL': 'samuel_1',
    'SECOND SAMUEL': 'samuel_2',
    'FIRST KINGS': 'kings_1',
    'SECOND KINGS': 'kings_2',
    'FIRST CHRONICLES': 'chronicles_1',
    'SECOND CHRONICLES': 'chronicles_2',
    'EZRA': 'ezra',
    'NEHEMIAH': 'nehemiah',
    'ESTHER': 'esther',
    'JOB': 'job',
    'PSALMS': 'psalms',
    'PROVERBS': 'proverbs',
    'ECCLESIASTES': 'ecclesiastes',
    'SONG OF SONGS': 'song_of_songs',
    'ISAIAH': 'isaiah',
    'JEREMIAH': 'jeremiah',
    'LAMENTATIONS': 'lamentations',
    'EZEKIEL': 'ezekiel',
    'DANIEL': 'daniel',
    'HOSEA': 'hosea',
    'JOEL': 'joel',
    'AMOS': 'amos',
    'OBADIAH': 'obadiah',
    'JONAH': 'jonah',
    'MICAH': 'micah',
    'NAHUM': 'nahum',
    'HABAKKUK': 'habakkuk',
    'ZEPHANIAH': 'zephaniah',
    'HAGGAI': 'haggai',
    'ZECHARIAH': 'zechariah',
    'MALACHI': 'malachi',
    # Special cases for THE TWELVE (minor prophets)
    'THE TWELVE': 'the_twelve',  # We'll handle this specially
    # Other files that might not have direct mappings
    'PREFACE': 'preface',
    'TABLE OF READINGS': 'table_of_readings',
    'THE LAW': 'the_law',
    'THE ORDER OF THE BOOKS': 'order_of_the_books',
    'THE PROPHETS': 'the_prophets',
    'THE WRITINGS': 'the_writings',
    'TITLE PAGE': "title_page",
}


def map_filename(jps_filename: str) -> Optional[str]:
    """Map a 1917jps filename to Open Siddur standard filename format.
    
    Args:
        jps_filename: The base filename from 1917jps (without .xml extension)
        
    Returns:
        The corresponding OS filename (without .xml extension) or None if no mapping exists
    """    
    # Look up the mapping
    base_name = jps_filename.upper()
    mapped = FILENAME_MAPPING.get(base_name)
    
    if mapped is not None:
        return mapped
    else:
        raise Exception(f"Invalid filename: {jps_filename}")


def process_file(input_path: Path, output_path: Path) -> None:
    """Process a single XML file, replacing sequences of four newlines with <page-break/>.
    
    Args:
        input_path: Path to the input XML file
        output_path: Path where the processed file should be saved
    """
    try:
        # Read the input file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace sequences of four newlines with <page-break/>
        processed_content = re.sub(r'(\n\s+){4,}', '<page-break/>\n', content)
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the processed content to the output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
            
        print(f"Processed: {input_path} -> {output_path}")
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")


def prepare() -> None:
    """Main function to prepare 1917jps XML files.
    
    This function:
    1. Iterates through XML files in sources/1917jps
    2. Maps filenames to match wlc/Books naming convention
    3. Processes each file to replace 4+ newlines with <page-break/>
    4. Saves processed files to sources/1917jps/processed/
    """
    # Define paths
    base_dir = Path(__file__).parent.parent.parent.parent  # repo root
    print(f'{base_dir=}')
    source_dir = base_dir / 'sources' / '1917jps'
    output_dir = base_dir / 'prepared_sources' / '1917jps'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each XML file in the source directory
    for input_file in source_dir.glob('*.xml'):
        print(f'{input_file=}')
        # Skip the XSD file
        if input_file.suffix.lower() != '.xml' or input_file.name.lower() == '1917jps.xsd':
            continue
        
        # Get the base filename without extension
        base_name = input_file.stem
        
        # Map the filename to wlc format
        mapped_name = map_filename(base_name)
        if mapped_name is None:
            print(f"Skipping {input_file.name} - no mapping defined")
            continue
        
        # Create output path
        output_file = output_dir / f"{mapped_name}.xml"
        
        # Process the file
        process_file(input_file, output_file)
    
    print("Processing complete.")


if __name__ == '__main__':
    prepare()
