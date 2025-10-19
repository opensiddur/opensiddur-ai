import sys
import os
from pathlib import Path

# Import the XMLTransformer from its new location
from opensiddur.common.xslt import xslt_transform
from opensiddur.importer.util.validation import validate

# Define TEI namespace with 'tei' prefix
TEI_NS = "http://www.tei-c.org/ns/1.0"


def make_project_directory() -> Path:
    """ Make the project/wlc directory if it doesn't exist """
    default_directory = Path(__file__).parent.parent.parent.parent / "project/wlc"
    default_directory.mkdir(parents=True, exist_ok=True)
    return default_directory

def get_source_directory() -> Path:
    return Path(__file__).parent.parent.parent.parent / "sources/wlc"

def get_xslt_directory() -> Path:
    return Path(__file__).parent

def main():
    project_directory = make_project_directory()
    source_directory = get_source_directory()
    xslt_directory = get_xslt_directory()

    xslt_transform(xslt_directory / "transform_index.xslt", 
        source_directory / "TanachHeader.xml", 
        project_directory / "index.xml")
    for book in os.listdir(source_directory / "Books"):
        if book not in ["TanachHeader.xml", "TanachIndex.xml"] and not book.endswith(".DH.xml"):
            print(f"Transforming {book}")
            xslt_transform(xslt_directory / "transform_book.xslt", 
                source_directory / book, 
                project_directory / book.lower())

    for book in os.listdir(project_directory):
        if book.endswith(".xml"):
            print(f"Validating {book}")
            is_valid, errors = validate(project_directory / book)
            if not is_valid:
                print(f"Errors in {book}: {errors}")
    return 0

if __name__ == "__main__":
    sys.exit(main())