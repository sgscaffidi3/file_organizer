# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 9
# Version: 0.3.9
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation of the demo file to showcase external library features.",
    "Implemented TQDM progress bar demonstration.",
    "Implemented Pillow metadata extraction demonstration.",
    "FEATURE UPGRADE: Updated to dynamically process all files in 'test_assets'.",
    "UX FIX: Integrated tqdm.write() to display metadata without breaking the progress bar.",
    "SYNC: Added support for both image and video extraction using project classes.",
    "FIX: Added video metadata routing and improved printing with TQDM."
]
# ------------------------------------------------------------------------------
import sys
import argparse
from pathlib import Path

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from libraries_helper import get_library_versions, extract_video_metadata
from metadata_processor import extract_image_metadata

# Constants
TEST_ASSETS_DIR = Path("test_assets")

def run_demo():
    """Runs a demonstration of library utilities against the test_assets directory."""
    
    print("=" * 60)
    print("EXTERNAL LIBRARY FEATURE DEMONSTRATION: ASSET SCAN")
    print("=" * 60)
    
    # 1. Library Version Check
    versions = get_library_versions()
    print("--- Library Versions ---")
    for lib in ['tqdm', 'Pillow', 'hachoir', 'opencv-python']:
        version = versions.get(lib, "Not Installed")
        print(f"  {lib:<10}: {version}")

    # 2. Check for test_assets directory
    if not TEST_ASSETS_DIR.exists():
        print(f"\nERROR: '{TEST_ASSETS_DIR}' directory not found.")
        print("Please run the test script with --gen_test_data first.")
        return

    # 3. Process all files in test_assets
    asset_files = list(TEST_ASSETS_DIR.glob("*.*"))
    if not asset_files:
        print(f"\nNo files found in {TEST_ASSETS_DIR.resolve()}")
        return

    print(f"\n--- Processing {len(asset_files)} assets found in {TEST_ASSETS_DIR} ---")
    
    # Use TQDM to wrap the file processing loop if available
    use_tqdm = versions.get('tqdm') != "Not Installed"
    if use_tqdm:
        from tqdm import tqdm
        iterator = tqdm(asset_files, desc="Extracting Metadata")
    else:
        iterator = asset_files
    
    for file_path in iterator:
        ext = file_path.suffix.lower()
        metadata = {}
        media_type = "UNKNOWN"

        # Determine extraction logic based on file type
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            media_type = "IMAGE"
            if versions.get('Pillow') != "Not Installed":
                metadata = extract_image_metadata(file_path)
        elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
            media_type = "VIDEO"
            if versions.get('hachoir') != "Not Installed":
                metadata = extract_video_metadata(file_path)

        # Prepare formatted output string
        output_lines = [f"\n[{media_type}] {file_path.name}"]
        if not metadata:
            output_lines.append("  Result: No metadata extracted or library missing.")
        else:
            for key, value in metadata.items():
                output_lines.append(f"    {key:<15}: {value}")
        
        final_output = "\n".join(output_lines)

        # Print using tqdm.write to preserve the progress bar, or standard print otherwise
        if use_tqdm:
            iterator.write(final_output)
        else:
            print(final_output)

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Demonstrates external library usage on test_assets.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Demo")
        sys.exit(0)

    run_demo()