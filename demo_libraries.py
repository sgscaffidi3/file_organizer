# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial creation and evolution of demo suite.",
    "Integrated DatabaseManager for persistence in 'demo/metadata.sqlite'.",
    "Implemented Smart Update logic with field-level change detection.",
    "Added --debug option to restore exhaustive line-by-line metadata printing."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
import sys
import argparse
import json
import hashlib
from pathlib import Path
from PIL import Image

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from libraries_helper import get_library_versions, get_video_metadata
from database_manager import DatabaseManager
from base_assets import ImageAsset, GenericFileAsset
from video_asset import VideoAsset

# Constants
TEST_ASSETS_DIR = Path("test_assets")
DEMO_OUTPUT_DIR = Path("demo")
DEMO_DB_PATH = DEMO_OUTPUT_DIR / "metadata.sqlite"

def calculate_file_hash(file_path: Path) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_existing_metadata(db: DatabaseManager, content_hash: str) -> dict:
    res = db.execute_query("SELECT extended_metadata FROM MediaContent WHERE content_hash = ?", (content_hash,))
    return json.loads(res[0][0]) if res else None

def compare_metadata(old_meta: dict, new_meta: dict) -> list:
    diffs = []
    for k, v in new_meta.items():
        if k not in old_meta:
            diffs.append(f"Added {k}")
        elif str(old_meta[k]) != str(v):
            diffs.append(f"{k}: '{old_meta[k]}' -> '{v}'")
    return diffs

def run_demo():
    parser = argparse.ArgumentParser(description="Demonstrates external library usage and DB persistence.")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--verbose', action='store_true', help='Extract exhaustive MediaInfo streams.')
    parser.add_argument('--debug', action='store_true', help='Print full metadata to console for every file.')
    args = parser.parse_args()

    if args.version:
        print(f"Demo Libraries v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    print("=" * 60)
    print("EXTERNAL LIBRARY FEATURE DEMONSTRATION & DB PERSISTENCE")
    if args.debug: print("DEBUG MODE: ENABLED (Exhaustive Printing)")
    print("=" * 60)
    
    DEMO_OUTPUT_DIR.mkdir(exist_ok=True)
    db = DatabaseManager(str(DEMO_DB_PATH))
    db.create_schema()

    if not TEST_ASSETS_DIR.exists():
        print(f"\nERROR: '{TEST_ASSETS_DIR}' directory not found.")
        return

    asset_files = list(TEST_ASSETS_DIR.glob("*.*"))
    versions = get_library_versions()
    use_tqdm = versions.get('tqdm') != "Not Installed"
    
    if use_tqdm:
        from tqdm import tqdm
        iterator = tqdm(asset_files, desc="Processing Assets")
    else:
        iterator = asset_files
    
    stats = {"new": 0, "updated": 0, "skipped": 0}

    with db:
        for file_path in iterator:
            ext = file_path.suffix.lower()
            asset = None
            media_group = "UNKNOWN"
            
            try:
                content_hash = calculate_file_hash(file_path)
                file_stats = file_path.stat()
                raw_meta = {"OS_File_Size": file_stats.st_size}

                # Identification & Class Assignment
                if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    media_group = "IMAGE"
                    with Image.open(file_path) as img:
                        raw_meta.update({"Width": img.width, "Height": img.height, "Format": img.format})
                        asset = ImageAsset(file_path, raw_meta)
                elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                    media_group = "VIDEO"
                    extracted = get_video_metadata(file_path, verbose=args.verbose)
                    extracted.update(raw_meta)
                    asset = VideoAsset(file_path, extracted)
                else:
                    media_group = "GENERIC"
                    asset = GenericFileAsset(file_path, raw_meta)

                # Inject friendly size for DB storage
                asset.extended_metadata['Friendly_Size'] = asset.get_friendly_size()
                
                # --- DEBUG PRINTING ---
                if args.debug:
                    meta_to_show = json.loads(asset.get_full_json())
                    debug_header = f"\n[{media_group}] {file_path.name}"
                    if use_tqdm: tqdm.write(debug_header) 
                    else: print(debug_header)
                    
                    for key, value in meta_to_show.items():
                        # Truncate long values for terminal readability
                        val_str = str(value)[:70] + "..." if len(str(value)) > 73 else str(value)
                        line = f"    {key:<20}: {val_str}"
                        if use_tqdm: tqdm.write(line)
                        else: print(line)

                # --- DATABASE LOGIC ---
                old_meta = get_existing_metadata(db, content_hash)
                if old_meta is None:
                    stats['new'] += 1
                    status_msg = f"[NEW] {file_path.name}"
                    db.execute_query("""
                        INSERT INTO MediaContent (content_hash, size, file_type_group, width, height, duration, video_codec, extended_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (content_hash, asset.size_bytes, media_group, getattr(asset, 'width', 0), 
                          getattr(asset, 'height', 0), getattr(asset, 'duration', 0), 
                          getattr(asset, 'video_codec', "N/A"), asset.get_full_json()))
                else:
                    new_meta = json.loads(asset.get_full_json())
                    diffs = compare_metadata(old_meta, new_meta)
                    if diffs:
                        stats['updated'] += 1
                        status_msg = f"[UPDATE] {file_path.name}: {', '.join(diffs[:2])}..."
                        db.execute_query("""
                            UPDATE MediaContent SET extended_metadata = ?, width = ?, height = ? WHERE content_hash = ?
                        """, (asset.get_full_json(), getattr(asset, 'width', 0), getattr(asset, 'height', 0), content_hash))
                    else:
                        stats['skipped'] += 1
                        status_msg = None # Don't spam if nothing happened

                if status_msg and not args.debug: # Only show status msg if debug isn't already printing everything
                    if use_tqdm: tqdm.write(status_msg)
                    else: print(status_msg)

                # Ensure path instance
                db.execute_query("INSERT OR IGNORE INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path) VALUES (?, ?, ?, ?)",
                                (content_hash, str(file_path), str(file_path.resolve()), file_path.name))

            except Exception as e:
                err_msg = f"[ERROR] {file_path.name}: {e}"
                if use_tqdm: tqdm.write(err_msg)
                else: print(err_msg)

    print(f"\n--- Demo Complete ---")
    print(f"New: {stats['new']} | Updated: {stats['updated']} | Unchanged: {stats['skipped']}")
    print(f"Run Report: python report_generator.py --db {DEMO_DB_PATH}")

if __name__ == '__main__':
    run_demo()