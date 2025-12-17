# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 3
# Version: 0.3.3
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation of the demo file to showcase external library features.",
    "Implemented TQDM progress bar demonstration.",
    "Implemented Pillow metadata extraction demonstration (requires a dummy image file)."
]
# ------------------------------------------------------------------------------
import sys
import argparse
from pathlib import Path
from libraries_helper import (
    get_library_versions, 
    demo_tqdm_progress, 
    extract_image_metadata
)

def run_demo():
    """Runs a complete demonstration of the external library utilities."""
    
    print("=" * 60)
    print("EXTERNAL LIBRARY FEATURE DEMONSTRATION")
    print("=" * 60)
    
    # 1. Library Version Check
    versions = get_library_versions()
    print("--- Library Versions ---")
    for lib, version in versions.items():
        print(f"  {lib:<10}: {version}")
    
    # 2. TQDM Progress Bar Demo
    if versions.get('tqdm') != "Not Installed":
        data_to_process = list(range(200))
        demo_tqdm_progress(data_to_process, "Hashing simulation")
    else:
        print("\nSkipping TQDM demo: Library not available.")


    # 3. Pillow Metadata Extraction Demo
    if versions.get('Pillow') != "Not Installed":
        # NOTE: This requires a placeholder file to run fully.
        # We will use a non-existent path and demonstrate the error handling path.
        dummy_file_path = Path("test_data/sample_image.jpg")
        
        print(f"\n--- Pillow Metadata Extraction Demo ---")
        print(f"Attempting to process: {dummy_file_path.resolve()}")
        
        metadata = extract_image_metadata(dummy_file_path)
        
        if 'error' in metadata:
            print(f"Result: {metadata['error']}")
            print("Note: Create a dummy image file at the specified path to see successful output.")
        else:
            print("Metadata Extracted Successfully:")
            for key, value in metadata.items():
                print(f"  {key:<15}: {value}")
    else:
        print("\nSkipping Pillow demo: Library not available.")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Demonstrates external library usage (tqdm, Pillow).")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Demo")
        sys.exit(0)

    run_demo()