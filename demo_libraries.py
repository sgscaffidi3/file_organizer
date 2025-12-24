# ==============================================================================
# File: demo_libraries.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_CHANGELOG_ENTRIES = [
    "Initial creation and evolution of demo suite.",
    "Integrated DatabaseManager for persistence.",
    "Implemented Smart Update logic with field-level change detection.",
    "Added --debug option for exhaustive metadata printing.",
    "FEATURE: Implemented Nested Progress Bars (Overall + Per-File Hashing).",
    "RESTORED: --version support and fixed execution flow.",
    "FEATURE: Added recursive scanning and relative path preservation for subdirs.",
    "REFACTOR: Switched to using internal AudioAsset from base_assets.py.",
    "FEATURE: Implemented per-file database commits to allow resume-on-cancel.",
    "OPTIMIZATION: Added Fast-Skip logic (Path+Size check) to avoid redundant hashing.",
    "FEATURE: Added double-hash verification for mismatched files."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.3.22
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
from base_assets import ImageAsset, GenericFileAsset, AudioAsset
from video_asset import VideoAsset

# Constants
TEST_ASSETS_DIR = Path("test_assets")
DEMO_OUTPUT_DIR = Path("demo")
DEMO_DB_PATH = DEMO_OUTPUT_DIR / "metadata.sqlite"

def calculate_file_hash_with_progress(file_path: Path, pbar_inner: tqdm) -> str:
    """Calculates MD5 hash while updating the per-file progress bar."""
    hash_md5 = hashlib.md5()
    try:
        file_size = file_path.stat().st_size
        pbar_inner.reset(total=file_size)
        pbar_inner.set_description(f"  Hashing: {file_path.name[:20]}...")
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""): 
                hash_md5.update(chunk)
                pbar_inner.update(len(chunk))
    except PermissionError:
        return "PERMISSION_DENIED"
    return hash_md5.hexdigest()

def get_hash_by_path_and_size(db, rel_path, size):
    """Checks if we already have a hash for this specific file path and size."""
    query = """
        SELECT mc.content_hash 
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        WHERE fpi.original_relative_path = ? AND mc.size = ?
    """
    res = db.execute_query(query, (rel_path, size))
    return res[0][0] if res else None

def get_existing_metadata(db: DatabaseManager, content_hash: str) -> dict:
    res = db.execute_query("SELECT extended_metadata FROM MediaContent WHERE content_hash = ?", (content_hash,))
    return json.loads(res[0][0]) if res else None

def compare_metadata(old_meta: dict, new_meta: dict) -> list:
    """Compares metadata and returns list of changed keys."""
    diffs = []
    for k, v in new_meta.items():
        if k not in old_meta or str(old_meta[k]) != str(v):
            diffs.append(k)
    return diffs

def run_demo():
    parser = argparse.ArgumentParser(description="High-Performance Resumable Media Scanner")
    parser.add_argument('-v', '--version', action='store_true', help="Show version and exit")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")
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

    asset_files = [f for f in TEST_ASSETS_DIR.rglob("*.*") if f.is_file()]
    
    pbar_outer = tqdm(total=len(asset_files), desc="OVERALL PROGRESS", position=0, leave=True)
    pbar_inner = tqdm(total=0, desc="  FILE PROGRESS   ", position=1, leave=False, unit='B', unit_scale=True)

    stats = {"new": 0, "updated": 0, "skipped": 0}

    for file_path in asset_files:
        ext = file_path.suffix.lower()
        rel_path = str(file_path.relative_to(TEST_ASSETS_DIR))
        file_size = file_path.stat().st_size
        
        try:
            # --- STEP 1: FAST SKIP (Check Path + Size) ---
            existing_hash = get_hash_by_path_and_size(db, rel_path, file_size)
            if existing_hash:
                stats['skipped'] += 1
                pbar_outer.update(1)
                continue 

            # --- STEP 2: HASHING WITH VERIFICATION ---
            content_hash = calculate_file_hash_with_progress(file_path, pbar_inner)
            if content_hash == "PERMISSION_DENIED":
                continue
            
            # User requirement: re-hash to confirm consistency
            verify_hash = calculate_file_hash_with_progress(file_path, pbar_inner)
            if content_hash != verify_hash:
                pbar_outer.write(f"[WARN] Hash mismatch on {rel_path}. Retrying final verification...")
                content_hash = calculate_file_hash_with_progress(file_path, pbar_inner)

            # --- STEP 3: METADATA EXTRACTION ---
            old_meta = get_existing_metadata(db, content_hash)
            raw_meta = {"OS_File_Size": file_size}
            asset, media_group = None, "UNKNOWN"

            if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                media_group = "IMAGE"
                with Image.open(file_path) as img:
                    raw_meta.update({"Width": img.width, "Height": img.height, "Format": img.format})
                    asset = ImageAsset(file_path, raw_meta)
            elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.mpg', '.ts']:
                media_group = "VIDEO"
                raw_meta.update(get_video_metadata(file_path))
                asset = VideoAsset(file_path, raw_meta)
            elif ext in ['.mp3', '.wav', '.flac', '.m4a', '.wma', '.ogg']:
                media_group = "AUDIO"
                raw_meta.update(get_video_metadata(file_path)) 
                asset = AudioAsset(file_path, raw_meta)
            else:
                media_group = "GENERIC"
                asset = GenericFileAsset(file_path, raw_meta)

            # --- STEP 4: DB PERSISTENCE (PER-FILE COMMIT) ---
            with db:
                new_meta_json = asset.get_full_json()
                if old_meta is None:
                    stats['new'] += 1
                    db.execute_query("""
                        INSERT INTO MediaContent (
                            content_hash, size, file_type_group, width, height, 
                            duration, bitrate, video_codec, extended_metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        content_hash, asset.size_bytes, media_group, 
                        getattr(asset, 'width', 0), getattr(asset, 'height', 0), 
                        getattr(asset, 'duration', 0), getattr(asset, 'bitrate', "N/A"),
                        getattr(asset, 'video_codec', "N/A"), new_meta_json
                    ))
                else:
                    if compare_metadata(old_meta, json.loads(new_meta_json)):
                        stats['updated'] += 1
                        db.execute_query("UPDATE MediaContent SET extended_metadata = ? WHERE content_hash = ?", (new_meta_json, content_hash))
                    else:
                        stats['skipped'] += 1

                db.execute_query("""
                    INSERT OR IGNORE INTO FilePathInstances 
                    (content_hash, path, original_full_path, original_relative_path) 
                    VALUES (?, ?, ?, ?)
                """, (content_hash, str(file_path), str(file_path.resolve()), rel_path))

        except Exception as e:
            pbar_outer.write(f"[ERROR] {rel_path}: {e}")

        pbar_outer.update(1)

    pbar_inner.close()
    pbar_outer.close()
    print(f"\n--- Recursive Scan Complete ---")
    print(f"Total: {len(asset_files)} | New: {stats['new']} | Updated: {stats['updated']} | Skipped: {stats['skipped']}")

if __name__ == '__main__':
    run_demo()