import sys
import os
from pathlib import Path
from typing import Optional

# Import the XMLTransformer from its new location
from opensiddur.converters.util.transformer import XMLTransformer


def make_project_directory():
    """ Make the project/wlc directory if it doesn't exist """
    default_directory = Path(__file__).parent.parent.parent / "project/wlc"
    default_directory.mkdir(parents=True, exist_ok=True)
    return default_directory

def get_source_directory() -> Path:
    return Path(__file__).parent.parent.parent / "sources/wlc"

def index(project_directory: Path, source_directory: Path):
    """ 
    Create the index.xml file with TEI header from TanachHeader.xml
    
    Args:
        project_directory: Path to the project directory
        source_directory: Path to the source directory containing Books/TanachHeader.xml
    """
    try:
        # Initialize the transformer
        transformer = XMLTransformer()
        
        # Define input and output paths
        input_file = source_directory / "Books" / "TanachHeader.xml"
        output_file = project_directory / "index.xml"
        
        # Perform the transformation
        if transformer.transform_file(input_file, output_file):
            print(f"Successfully created {output_file}")
        else:
            print(f"Failed to create {output_file}", file=sys.stderr)
            
    except Exception as e:
        print(f"Error in index function: {e}", file=sys.stderr)
        raise

def main():
    project_directory = make_project_directory()
    source_directory = get_source_directory()
    index(project_directory, source_directory)
    return 0

if __name__ == "__main__":
    sys.exit(main())