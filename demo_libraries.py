# ==============================================================================
# File: demo_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_CHANGELOG_ENTRIES = [
    "Initial creation and evolution of demo suite.",
    "Integrated DatabaseManager for persistence.",
    "Implemented Smart Update logic with field-level change detection.",
    "Added --debug option for exhaustive metadata printing.",
    "FEATURE: Implemented Nested Progress Bars (Overall + Per-File Hashing).",
    "RESTORED: --version support and fixed execution flow."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
import sys
import argparse
import json
import hashlib
from pathlib import Path
from PIL import Image
from tqdm import tqdm

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

def calculate_file_hash_with_progress(file_path: Path, pbar_inner: tqdm) -> str:
    """Calculates MD5 hash while updating the per-file progress bar."""
    hash_md5 = hashlib.md5()
    file_size = file_path.stat().st_size
    pbar_inner.reset(total=file_size)
    pbar_inner.set_description(f"  Hashing: {file_path.name[:20]}...")
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): # 1MB chunks
            hash_md5.update(chunk)
            pbar_inner.update(len(chunk))
    return hash_md5.hexdigest()

def get_existing_metadata(db: DatabaseManager, content_hash: str) -> dict:
    res = db.execute_query("SELECT extended_metadata FROM MediaContent WHERE content_hash = ?", (content_hash,))
    return json.loads(res[0][0]) if res else None

def compare_metadata(old_meta: dict, new_meta: dict) -> list:
    """Compares two metadata dicts and returns a list of differences."""
    diffs = []
    for k, v in new_meta.items():
        if k not in old_meta:
            diffs.append(f"Added {k}")
        elif str(old_meta[k]) != str(v):
            diffs.append(f"{k} changed")
    return diffs

def run_demo():
    parser = argparse.ArgumentParser(description="Demonstrates nested progress bars and DB persistence.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--debug', action='store_true', help='Print full metadata to console.')
    args = parser.parse_args()

    # --- RESTORED VERSION SUPPORT ---
    if args.version:
        print(f"Demo Libraries v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    DEMO_OUTPUT_DIR.mkdir(exist_ok=True)
    db = DatabaseManager(str(DEMO_DB_PATH))
    db.create_schema()

    if not TEST_ASSETS_DIR.exists():
        print(f"ERROR: '{TEST_ASSETS_DIR}' not found.")
        return

    asset_files = list(TEST_ASSETS_DIR.glob("*.*"))
    
    # Progress Bar Initialization
    pbar_outer = tqdm(total=len(asset_files), desc="OVERALL PROGRESS", position=0, leave=True)
    pbar_inner = tqdm(total=0, desc="  FILE PROGRESS   ", position=1, leave=False, unit='B', unit_scale=True)

    stats = {"new": 0, "updated": 0, "skipped": 0}

    with db:
        for file_path in asset_files:
            ext = file_path.suffix.lower()
            asset = None
            media_group = "UNKNOWN"
            
            try:
                content_hash = calculate_file_hash_with_progress(file_path, pbar_inner)
                file_stats = file_path.stat()
                raw_meta = {"OS_File_Size": file_stats.st_size}

                # Identification & Asset Class Creation
                if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    media_group = "IMAGE"
                    with Image.open(file_path) as img:
                        raw_meta.update({"Width": img.width, "Height": img.height, "Format": img.format})
                        asset = ImageAsset(file_path, raw_meta)
                elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                    media_group = "VIDEO"
                    extracted = get_video_metadata(file_path)
                    extracted.update(raw_meta)
                    asset = VideoAsset(file_path, extracted)
                else:
                    media_group = "GENERIC"
                    asset = GenericFileAsset(file_path, raw_meta)

                # Metadata Comparison & DB Persistence
                old_meta = get_existing_metadata(db, content_hash)
                new_meta_json = asset.get_full_json()
                
                if old_meta is None:
                    stats['new'] += 1
                    db.execute_query("""
                        INSERT INTO MediaContent (content_hash, size, file_type_group, width, height, duration, video_codec, extended_metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (content_hash, asset.size_bytes, media_group, getattr(asset, 'width', 0), 
                          getattr(asset, 'height', 0), getattr(asset, 'duration', 0), 
                          getattr(asset, 'video_codec', "N/A"), new_meta_json))
                else:
                    diffs = compare_metadata(old_meta, json.loads(new_meta_json))
                    if diffs:
                        stats['updated'] += 1
                        db.execute_query("UPDATE MediaContent SET extended_metadata = ? WHERE content_hash = ?", (new_meta_json, content_hash))
                    else:
                        stats['skipped'] += 1

                # Ensure path instance is recorded
                db.execute_query("INSERT OR IGNORE INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path) VALUES (?, ?, ?, ?)",
                                (content_hash, str(file_path), str(file_path.resolve()), file_path.name))

            except Exception as e:
                pbar_outer.write(f"[ERROR] {file_path.name}: {e}")

            pbar_outer.update(1)

    pbar_inner.close()
    pbar_outer.close()
    print(f"\n--- Scan Complete ---")
    print(f"New Assets: {stats['new']} | Updated: {stats['updated']} | Skipped: {stats['skipped']}")

if __name__ == '__main__':
    run_demo()