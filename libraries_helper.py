# ==============================================================================
# File: libraries_helper.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 5
# Version: 0.3.5
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation of libraries_helper to encapsulate external library interactions.",
    "Added utility for reporting installed library versions.",
    "Added demo function for tqdm progress bar use.",
    "Added function for extracting EXIF metadata using Pillow (F04 implementation detail).",
    "Implemented CLI argument parsing for --version to allow clean exit during health checks (N06)."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, Optional
import time
import sys
import argparse

# Attempt to import external dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


import importlib.metadata

def get_library_versions():
    versions = {}
    try:
        versions['tqdm'] = importlib.metadata.version('tqdm')
    except importlib.metadata.PackageNotFoundError:
        versions['tqdm'] = "Not Installed"
        
    # Do the same for Pillow (PIL)
    try:
        versions['Pillow'] = importlib.metadata.version('Pillow')
    except importlib.metadata.PackageNotFoundError:
        versions['Pillow'] = "Not Installed"
        
    return versions

def demo_tqdm_progress(items: list, description: str = "Processing") -> None:
    """
    Demonstrates the use of a progress bar with a list of items.
    """
    if not TQDM_AVAILABLE:
        print("tqdm is not installed. Cannot run progress bar demo.")
        return

    print(f"\n--- TQDM Demo: {description} ---")
    
    # The 'tqdm' function wraps an iterable, adding a progress bar
    for item in tqdm(items, desc=description, unit="item"):
        # Simulate work being done
        time.sleep(0.01)

    print("--- TQDM Demo Complete ---\n")


def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extracts essential metadata (EXIF data, dimensions) from an image file
    using the Pillow library, fulfilling a component of F04.
    """
    if not PIL_AVAILABLE:
        return {"error": "Pillow is not installed or available."}

    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}
        
    metadata = {}
    try:
        with Image.open(file_path) as img:
            # 1. Dimensions
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['format'] = img.format
            
            # 2. Basic EXIF data (as a simple dictionary)
            if img.getexif():
                # Note: EXIF tags are integer keys, map them to readable strings if needed
                # Here we just keep the raw data for simplicity.
                exif_data = dict(img.getexif())
                metadata['exif_tags_count'] = len(exif_data)
            else:
                metadata['exif_tags_count'] = 0

    except IOError as e:
        return {"error": f"Could not open or process image: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}
        
    return metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Library Helper Module for File Organizer.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    
    # Note: We only need to check for --version here. No other action is defined for standalone execution.
    args = parser.parse_args()

    if args.version:
        # Need to ensure version_util is available if called standalone
        project_root = Path(__file__).resolve().parent
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))
            
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Library Helper Utilities")
            sys.exit(0)
        except ImportError:
            print("Error: Could not import version_util.")
            sys.exit(1)
            
    # Default action if no argument is provided: Print status
    print("This module provides utility functions and is typically imported.")
    print("Current Library Status:", get_library_versions())