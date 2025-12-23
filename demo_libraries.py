# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 5
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
    "FEATURE: Integrated GenericFileAsset.get_friendly_size() for dynamic unit scaling.",
    "DISPLAY FIX: Restored Dimensions, Aspect, Audio, and Date fields to demo output.",
    "PERSISTENCE: Added DatabaseManager integration to save results to 'demo/metadata.sqlite'.",
    "LOGIC: Added file hashing and 'Smart Update' logic to detect and report changed metadata fields.",
    "DB FIX: Explicitly inject 'Friendly_Size' into the JSON backpack so the database stores the readable format."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.5.20
# ------------------------------------------------------------------------------
import sys
import argparse
import json
import hashlib
import sqlite3
from pathlib import Path
from PIL import Image

# Ensure project root is in path for imports
sys.path.insert(0, str(Path(__file__).parent))

from libraries_helper import get_library_versions, get_video_metadata
from asset_manager import AssetManager
from database_manager import DatabaseManager
from base_assets import ImageAsset, GenericFileAsset
from video_asset import VideoAsset

# Constants
TEST_ASSETS_DIR = Path("test_assets")
DEMO_OUTPUT_DIR = Path("demo")
DEMO_DB_PATH = DEMO_OUTPUT_DIR / "metadata.sqlite"

def calculate_file_hash(file_path: Path) -> str:
    """Generates an MD5 hash of the file content for database identification."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_existing_record(db: DatabaseManager, content_hash: str):
    """Fetches the existing extended_metadata for a given hash."""
    query = "SELECT extended_metadata FROM MediaContent WHERE content_hash = ?"
    results = db.execute_query(query, (content_hash,))
    if results:
        return json.loads(results[0][0]) if results[0][0] else {}
    return None

def compare_metadata(old_meta: dict, new_meta: dict) -> list:
    """Returns a list of keys that differ between old and new metadata."""
    diffs = []
    all_keys = set(old_meta.keys()) | set(new_meta.keys())
    for key in all_keys:
        val_old = old_meta.get(key)
        val_new = new_meta.get(key)
        # Convert to string to avoid type mismatches (e.g. 1 vs "1")
        if str(val_old) != str(val_new):
            diffs.append(f"{key}: '{val_old}' -> '{val_new}'")
    return diffs

def run_demo():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    args, unknown = parser.parse_known_args()
    
    print("=" * 60)
    print("EXTERNAL LIBRARY FEATURE DEMONSTRATION & DB PERSISTENCE")
    print("=" * 60)
    
    # 1. Setup Demo Environment
    if not TEST_ASSETS_DIR.exists():
        print(f"\nERROR: '{TEST_ASSETS_DIR}' directory not found.")
        return

    # Ensure demo directory exists
    DEMO_OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Target Database: {DEMO_DB_PATH}")

    # Initialize Database
    db = DatabaseManager(str(DEMO_DB_PATH))
    db.create_schema()

    # 2. Scan Files
    asset_files = list(TEST_ASSETS_DIR.glob("*.*"))
    print(f"--- Processing {len(asset_files)} assets in {TEST_ASSETS_DIR} ---")
    
    versions = get_library_versions()
    use_tqdm = versions.get('tqdm') != "Not Installed"
    
    if use_tqdm:
        from tqdm import tqdm
        iterator = tqdm(asset_files, desc="Processing Assets")
    else:
        iterator = asset_files
    
    files_updated = 0
    files_new = 0
    files_unchanged = 0

    with db: # Use context manager for connection safety
        for file_path in iterator:
            ext = file_path.suffix.lower()
            asset = None
            media_type = "UNKNOWN"
            status_msg = ""
            
            try:
                # 1. Identification (Hash & Stat)
                content_hash = calculate_file_hash(file_path)
                stats = file_path.stat()
                raw_meta = {
                    "OS_File_Size": stats.st_size,
                    "OS_Date_Created": stats.st_ctime,
                    "OS_Date_Modified": stats.st_mtime
                }

                # 2. Metadata Extraction
                if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    media_type = "IMAGE"
                    with Image.open(file_path) as img:
                        raw_meta.update({"Width": img.width, "Height": img.height, "Format": img.format})
                        asset = ImageAsset(file_path, raw_meta)
                elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                    media_type = "VIDEO"
                    all_meta = get_video_metadata(file_path, verbose=args.verbose)
                    all_meta.update(raw_meta)
                    asset = VideoAsset(file_path, all_meta)
                else:
                    asset = GenericFileAsset(file_path, raw_meta)
                    media_type = "GENERIC"

                # CRITICAL UPDATE: Inject Friendly Size into the Backpack for DB Storage
                if asset:
                    asset.extended_metadata['Friendly_Size'] = asset.get_friendly_size()

                # 3. Database Logic (Smart Upsert)
                existing_meta = get_existing_record(db, content_hash)
                
                if existing_meta is None:
                    # INSERT NEW
                    files_new += 1
                    status_msg = "[NEW] Inserted into DB"
                    
                    # Insert into MediaContent
                    db.execute_query("""
                        INSERT INTO MediaContent (content_hash, size, file_type_group, width, height, duration, video_codec, extended_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        content_hash,
                        asset.size_bytes, # Still store raw bytes in 'size' column for sorting
                        media_type,
                        getattr(asset, 'width', None),
                        getattr(asset, 'height', None),
                        getattr(asset, 'duration', None),
                        getattr(asset, 'video_codec', None),
                        asset.get_full_json() # 'Friendly_Size' is now inside this JSON
                    ))
                else:
                    # CHECK FOR CHANGES
                    current_json_dict = json.loads(asset.get_full_json())
                    diffs = compare_metadata(existing_meta, current_json_dict)
                    
                    if diffs:
                        files_updated += 1
                        diff_str = "; ".join(diffs[:3]) 
                        if len(diffs) > 3: diff_str += "..."
                        status_msg = f"[UPDATED] Changed: {diff_str}"
                        
                        db.execute_query("""
                            UPDATE MediaContent 
                            SET extended_metadata = ?, width = ?, height = ?
                            WHERE content_hash = ?
                        """, (asset.get_full_json(), getattr(asset, 'width', None), getattr(asset, 'height', None), content_hash))
                    else:
                        files_unchanged += 1
                        status_msg = "[UNCHANGED] Skipped"

                # Ensure FilePathInstances link exists
                db.execute_query("""
                    INSERT OR IGNORE INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, is_primary)
                    VALUES (?, ?, ?, ?, 1)
                """, (content_hash, str(file_path), str(file_path.resolve()), file_path.name))

            except Exception as e:
                status_msg = f"[ERROR] {str(e)}"

            # 4. Display
            if use_tqdm:
                if "UNCHANGED" not in status_msg:
                    tqdm.write(f"{file_path.name:<30} | {asset.get_friendly_size() if asset else 'N/A'} | {status_msg}")

    print("-" * 60)
    print(f"Summary: New: {files_new} | Updated: {files_updated} | Unchanged: {files_unchanged}")
    print("Run the following command to verify the database contents:")
    print(f"python database_manager.py --dump_db --db {DEMO_DB_PATH}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Demonstrates external library usage and DB persistence.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--verbose', action='store_true', help='Use exhaustive metadata extraction.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Demo")
        sys.exit(0)

    run_demo()