import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Import the XMLTransformer from its new location
from opensiddur.converters.util.validation import validate

def make_project_directory():
    """ Make the project/1917jps directory if it doesn't exist """
    default_directory = Path(__file__).parent.parent.parent.parent / "project/1917jps"
    default_directory.mkdir(parents=True, exist_ok=True)
    return default_directory

def get_source_directory() -> Path:
    return Path(__file__).parent.parent.parent.parent / "prepared_sources/1917jps"

def xslt_transform(project_directory: Path, source_directory: Path, 
source_file: str, output_file: str, xslt_file: str):
    """ 
    Create the index.xml file with TEI header from TanachHeader.xml
    
    Args:
        project_directory: Path to the project directory
        source_directory: Path to the source directory containing Books/TanachHeader.xml
    """
    try:
        # Define input and output paths
        input_file = source_directory / source_file
        output_file = project_directory / output_file
        
        # Get the directory containing the XSLT file
        xslt_file = Path(__file__).parent / xslt_file
        
        # Read the input XML
        with open(input_file, 'r', encoding='utf-8') as f:
            input_xml = f.read()
        
        # Perform the transformation
        from saxonche import PySaxonProcessor
        
        with PySaxonProcessor(license=False) as proc:
            # Create XSLT processor
            xslt_proc = proc.new_xslt30_processor()
            
            # Compile the stylesheet
            executable = xslt_proc.compile_stylesheet(stylesheet_file=str(xslt_file))
            if executable is None:
                raise ValueError(f"Failed to compile XSLT: {xslt_proc.error_message}")
            
            # Parse the input XML

            document = proc.parse_xml(xml_text=input_xml)
            
            # Transform the document
            result = executable.transform_to_string(xdm_node=document)
            
            # Write the result to the output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            
            print(f"Successfully created {output_file}")
            
    except Exception as e:
        print(f"Error in index function: {e}", file=sys.stderr)
        raise

book_files = [
    "chronicles_1.xml", 
    "chronicles_2.xml", 
    "daniel.xml", 
    "deuteronomy.xml", 
    "ecclesiastes.xml", 
    "esther.xml", 
    "exodus.xml", 
    "ezekiel.xml", 
    "ezra.xml", 
    "genesis.xml", 
    "isaiah.xml", 
    "jeremiah.xml", 
    "job.xml", 
    "joshua.xml", 
    "judges.xml", 
    "kings_1.xml", 
    "kings_2.xml",
    "lamentations.xml", 
    "leviticus.xml", 
    "nehemiah.xml", 
    "numbers.xml", 
    "proverbs.xml", 
    "psalms.xml", 
    "ruth.xml", 
    "samuel_1.xml", 
    "samuel_2.xml", 
    "song_of_songs.xml",  
    "the_twelve.xml", 
    
]

index_files = [
    "ktuvim.xml", 
    "title_page.xml", 
    "torah.xml",
    "neviim.xml", 
    "table_of_readings.xml",
    "order_of_the_books.xml", 
    "preface.xml", 
]

def main():
    project_directory = make_project_directory()
    source_directory = get_source_directory()
    
    # TODO: produce the index file
    #xslt_transform(project_directory, source_directory, "TanachHeader.xml", "index.xml", "transform_index.xslt")
    for book_file in book_files:
        print(f"Transforming {book_file}")
        xslt_transform(project_directory, source_directory, book_file, 
                book_file.lower(), "book.xslt")

    for tei_file in os.listdir(project_directory):
        if tei_file.endswith(".xml"):
            print(f"Validating {tei_file}")
            is_valid, errors = validate(project_directory / tei_file)
            if not is_valid:
                print(f"Errors in {tei_file}: {errors}")
    return 0

if __name__ == "__main__":
    sys.exit(main())