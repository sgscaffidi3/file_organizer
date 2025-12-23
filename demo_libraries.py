# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial creation of the demo file to showcase external library features.",
    "Implemented TQDM progress bar demonstration.",
    "Implemented Pillow metadata extraction demonstration.",
    "FEATURE UPGRADE: Updated to dynamically process all files in 'test_assets'.",
    "UX FIX: Integrated tqdm.write() to display metadata without breaking the progress bar.",
    "SYNC: Added support for both image and video extraction using project classes.",
    "FIX: Added video metadata routing and improved printing with TQDM.",
    "Initial Hachoir implementation for basic headers.",
    "Added OpenCV fallback to resolve 0-width/height AVI issues.",
    "Added version checking and datetime import safety.",
    "Migrated to pymediainfo for professional stream-level analysis.",
    "Added specific mapping for DV/DVCPRO camera and tape metadata.",
    "Implemented Dynamic Mapping using to_data() to support 100% of MediaInfo fields automatically.",
    "Added --verbose option.",
    "FIX: Resolved ImportError by replacing legacy metadata_processor calls with AssetManager logic.",
    "FEATURE: Integrated GenericFileAsset.get_friendly_size() for dynamic unit scaling (B, KiB, MiB, GiB).",
    "RESTORED: Exhaustive metadata display to ensure no stream-level info is missed."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.18
# ------------------------------------------------------------------------------
import sys
import argparse
from pathlib import Path
from PIL import Image

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from libraries_helper import get_library_versions, get_video_metadata
from asset_manager import AssetManager
from base_assets import ImageAsset, GenericFileAsset
from video_asset import VideoAsset

# Constants
TEST_ASSETS_DIR = Path("test_assets")

def run_demo():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    args, unknown = parser.parse_known_args()
    
    print("=" * 60)
    print("EXTERNAL LIBRARY FEATURE DEMONSTRATION: ASSET SCAN")
    print("=" * 60)
    
    # 1. Library Version Check
    versions = get_library_versions()
    print("--- Library Versions ---")
    for lib in ['tqdm', 'Pillow', 'hachoir', 'opencv-python','pymediainfo']:
        version = versions.get(lib, "Not Installed")
        print(f"  {lib:<10}: {version}")

    # 2. Check for test_assets directory
    if not TEST_ASSETS_DIR.exists():
        print(f"\nERROR: '{TEST_ASSETS_DIR}' directory not found.")
        return

    # 3. Process all files in test_assets
    asset_files = list(TEST_ASSETS_DIR.glob("*.*"))
    if not asset_files:
        print(f"\nNo files found in {TEST_ASSETS_DIR.resolve()}")
        return

    print(f"\n--- Processing {len(asset_files)} assets found in {TEST_ASSETS_DIR} ---")
    
    use_tqdm = versions.get('tqdm') != "Not Installed"
    if use_tqdm:
        from tqdm import tqdm
        iterator = tqdm(asset_files, desc="Extracting Metadata")
    else:
        iterator = asset_files
    
    for file_path in iterator:
        ext = file_path.suffix.lower()
        asset = None
        media_type = "UNKNOWN"
        all_metadata = {}

        try:
            # Get OS file stats
            stats = file_path.stat()
            raw_meta = {
                "OS_File_Size": stats.st_size,
                "OS_Date_Created": stats.st_ctime,
                "OS_Date_Modified": stats.st_mtime
            }

            if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                media_type = "IMAGE"
                with Image.open(file_path) as img:
                    raw_meta.update({"Width": img.width, "Height": img.height, "Format": img.format})
                    asset = ImageAsset(file_path, raw_meta)
                    all_metadata = asset.extended_metadata
            elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                media_type = "VIDEO"
                # Use the exhaustive MediaInfo extractor
                all_metadata = get_video_metadata(file_path, verbose=args.verbose)
                all_metadata.update(raw_meta)
                asset = VideoAsset(file_path, all_metadata)
            else:
                asset = GenericFileAsset(file_path, raw_meta)
                all_metadata = raw_meta

        except Exception as e:
            all_metadata = {"Error": str(e)}

        # Output formatting
        output_lines = [f"\n[{media_type}] {file_path.name}"]
        
        # Display the Dynamic Friendly Size (Restores meaningful sizes like 3.89 GiB)
        if asset:
            output_lines.append(f"    File Size      : {asset.get_friendly_size()}")
        
        # Display EVERYTHING in the metadata dictionary
        for key, value in all_metadata.items():
            # Skip keys we've already displayed or internal keys
            if key == "OS_File_Size": continue
            
            val_str = str(value)[:70] + "..." if len(str(value)) > 73 else str(value)
            output_lines.append(f"    {key:<15}: {val_str}")
        
        final_output = "\n".join(output_lines)
        if use_tqdm:
            iterator.write(final_output)
        else:
            print(final_output)

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Demonstrates external library usage on test_assets.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--verbose', action='store_true', help='Use exhaustive metadata extraction.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Demo")
        sys.exit(0)

    run_demo()