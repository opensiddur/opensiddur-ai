#!/usr/bin/env python3
"""
Extract title page information from the 1917 JPS Tanakh Wikisource.

This module contains functions to parse and extract metadata from the title pages
of the 1917 JPS Tanakh.
"""

import re
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

@dataclass
class TitlePageInfo:
    """Dataclass to hold title page information."""
    main_title: str
    hebrew_title: str
    english_subtitle: str
    publisher: str
    place: str
    year: int
    additional_info: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the TitlePageInfo to a dictionary."""
        return {
            'main_title': self.main_title,
            'hebrew_title': self.hebrew_title,
            'english_subtitle': self.english_subtitle,
            'publisher': self.publisher,
            'place': self.place,
            'year': self.year,
            'additional_info': self.additional_info
        }

def extract_title_page_info(page7_text: str, page8_text: str) -> TitlePageInfo:
    """
    Extract title page information from the raw text of pages 7 and 8.
    
    Args:
        page7_text: Raw text content of page 7
        page8_text: Raw text content of page 8
        
    Returns:
        TitlePageInfo object containing the extracted information
    """
    # Combine both pages for easier processing
    full_text = f"{page7_text}\n{page8_text}"
    
    # Initialize with default values
    info = {
        'main_title': 'THE HOLY SCRIPTURES',
        'hebrew_title': 'תנ״ך',
        'english_subtitle': 'ACCORDING TO THE MASORETIC TEXT',
        'publisher': 'The Jewish Publication Society of America',
        'place': 'Philadelphia',
        'year': 1917,
        'additional_info': {}
    }
    
    # Extract main title (usually in all caps)
    title_match = re.search(r'THE HOLY SCRIPTURES', full_text, re.IGNORECASE)
    if title_match:
        info['main_title'] = title_match.group(0).strip()
    
    # Extract Hebrew title (look for Hebrew characters)
    hebrew_match = re.search(r'[\u0590-\u05FF\uFB1D-\uFB4F]+', full_text)
    if hebrew_match:
        info['hebrew_title'] = hebrew_match.group(0).strip()
    
    # Extract subtitle (the long line after the main title)
    subtitle_match = re.search(r'ACCORDING TO THE MASORETIC TEXT[\s\S]*?(?=\n\s*\n)', full_text)
    if subtitle_match:
        info['english_subtitle'] = subtitle_match.group(0).strip()
    
    # Extract publisher and place (usually at the bottom of the page)
    publisher_match = re.search(r'(The Jewish Publication Society of America|JEWISH PUBLICATION SOCIETY)', 
                              full_text, re.IGNORECASE)
    if publisher_match:
        info['publisher'] = publisher_match.group(1).strip()
    
    place_match = re.search(r'PHILADELPHIA', full_text, re.IGNORECASE)
    if place_match:
        info['place'] = place_match.group(0).strip()
    
    # Extract year (look for a 4-digit number that's around 1917)
    year_match = re.search(r'\b(19\d{2})\b', full_text)
    if year_match:
        info['year'] = int(year_match.group(1))
    
    # Additional info that might be present
    additional_info = {}
    
    # Look for edition information
    edition_match = re.search(r'(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|\d+(?:st|nd|rd|th))\s+(Edition|Printing|Impression)', 
                            full_text, re.IGNORECASE)
    if edition_match:
        additional_info['edition'] = edition_match.group(0).strip()
    
    # Look for copyright information
    copyright_match = re.search(r'copyright.*?\d{4}', full_text, re.IGNORECASE | re.DOTALL)
    if copyright_match:
        additional_info['copyright'] = copyright_match.group(0).strip()
    
    info['additional_info'] = additional_info
    
    return TitlePageInfo(**info)

def load_page_text(file_path: Path) -> str:
    """Load the text content of a page file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def process_title_pages(text_dir: Path) -> Optional[TitlePageInfo]:
    """
    Process the title pages (pages 7-8) and extract metadata.
    
    Args:
        text_dir: Path to the directory containing the text files
        
    Returns:
        TitlePageInfo object if successful, None otherwise
    """
    # Find the first few text files (pages 7 and 8)
    text_files = sorted([f for f in text_dir.glob("*.txt") if f.name.isdigit()])
    
    if len(text_files) < 2:
        print(f"Error: Need at least 2 text files, found {len(text_files)}")
        return None
    
    # Use the first two files as title pages
    page7_text = load_page_text(text_files[0])
    page8_text = load_page_text(text_files[1])
    
    if not page7_text and not page8_text:
        print("Error: Could not read title page files")
        return None
    
    # Extract the title page information
    return extract_title_page_info(page7_text, page8_text)

def get_available_pages(text_dir: Path) -> List[Path]:
    """Get a list of available page files in the text directory."""
    return sorted([f for f in text_dir.glob("*.txt") if f.stem.isdigit()], 
                 key=lambda x: int(x.stem))

def get_page_range(text_dir: Path) -> Tuple[int, int]:
    """Get the range of available page numbers."""
    pages = get_available_pages(text_dir)
    if not pages:
        return (0, 0)
    return (int(pages[0].stem), int(pages[-1].stem))

if __name__ == "__main__":
    # Example usage
    base_dir = Path(__file__).parent.parent.parent.parent  # Move up to project root
    text_dir = base_dir / "sources" / "1917jps-wikisource" / "text"
    
    # Check if the directory exists
    if not text_dir.exists():
        print(f"Error: Directory not found: {text_dir}")
        exit(1)
    
    # Get available pages
    pages = get_available_pages(text_dir)
    if not pages:
        print(f"No text files found in {text_dir}")
        exit(1)
    
    first_page, last_page = get_page_range(text_dir)
    print(f"Found {len(pages)} pages (range: {first_page:04d}-{last_page:04d})")
    
    # Process title pages (first two files)
    print("\nProcessing title pages...")
    title_info = process_title_pages(text_dir)
    
    if title_info:
        print("\nTitle Page Information:")
        print(f"Main Title: {title_info.main_title}")
        print(f"Hebrew Title: {title_info.hebrew_title}")
        print(f"English Subtitle: {title_info.english_subtitle}")
        print(f"Publisher: {title_info.publisher}")
        print(f"Place: {title_info.place}")
        print(f"Year: {title_info.year}")
        
        if title_info.additional_info:
            print("\nAdditional Information:")
            for key, value in title_info.additional_info.items():
                print(f"{key}: {value}")
    else:
        print("Could not find or process title pages.")
