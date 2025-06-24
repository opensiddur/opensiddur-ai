import os
import requests
from pathlib import Path
from zipfile import ZipFile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_and_unzip_tanach():
    """Download and unzip the latest Tanach XML file from tanach.us."""
    # URL of the Tanach XML zip file
    url = "https://tanach.us/Books/Tanach.xml.zip"
    
    # Create target directory if it doesn't exist
    target_dir = Path(__file__).parent.parent / "sources/wlc"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Download the zip file
    logger.info(f"Downloading {url}...")
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    # Save the zip file
    zip_path = target_dir / "Tanach.xml.zip"
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    
    logger.info(f"Downloaded file saved to {zip_path}")
    
    # Unzip the file
    logger.info(f"Unzipping {zip_path}...")
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    
    logger.info(f"Successfully extracted files to {target_dir}")
    
    # Clean up the zip file
    zip_path.unlink()
    logger.info(f"Removed temporary zip file")

if __name__ == "__main__":
    try:
        download_and_unzip_tanach()
    except Exception as e:
        logger.error(f"Error downloading/unzipping Tanach: {str(e)}")
        raise
