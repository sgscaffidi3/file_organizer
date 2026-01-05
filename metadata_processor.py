# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 7
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class (F04).",
    "PRODUCTION UPGRADE: Integrated Pillow and Hachoir for extraction.",
    "RELIABILITY: Added safety handling for missing physical files.",
    "ARCHITECTURE REFACTOR: Migrated to Hybrid Metadata model via AssetManager.",
    "CLEANUP: Removed redundant local extractors; delegated all routing to AssetManager.",
    "FEATURE: Enabled full support for VIDEO, IMAGE, AUDIO, and DOCUMENT groups.",
    "UX: Added TQDM progress bar for real-time extraction feedback.",
    "BUG FIX: Updated _get_files_to_process query to prevent infinite re-processing of Audio/Docs (which inherently have NULL width/height).",
    "PERFORMANCE: Implemented Multithreaded Metadata Extraction using ThreadPoolExecutor."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.7.9
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import sys
import concurrent.futures
import os
import json
from tqdm import tqdm

from database_manager import DatabaseManager
from config_manager import ConfigManager
from asset_manager import AssetManager

class MetadataProcessor:
    """Processes MediaContent records missing metadata using multithreading."""
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.original_full_path
        FROM MediaContent T1
        INNER JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash AND T2.is_primary = 1
        WHERE 
           (T1.file_type_group IN ('IMAGE', 'VIDEO') AND (T1.width IS NULL OR T1.height IS NULL))
           OR
           (T1.file_type_group = 'AUDIO' AND T1.duration IS NULL)
           OR
           (T1.file_type_group NOT IN ('IMAGE', 'VIDEO', 'AUDIO') AND T1.extended_metadata IS NULL);
        """
        results = self.db.execute_query(query)
        return results if results else []

    def _process_single_file(self, args):
        """Worker function. Returns (content_hash, asset_data_dict) or None."""
        content_hash, group, path_str = args
        path = Path(path_str)
        
        if not path.exists():
            return None
            
        # We instantiate a temporary AssetManager just for the logic, 
        # or better, just use the Asset classes directly?
        # Re-using AssetManager is safer to keep logic centralized, 
        # BUT AssetManager writes to DB. We need to prevent that in threads.
        
        # We will use AssetManager BUT we need to modify it to return data instead of writing?
        # Actually, AssetManager.process_file currently calls self.db.execute_query.
        # This is bad for threading (SQLite lock).
        
        # SOLUTION: We will replicate the router logic here briefly or Refactor AssetManager.
        # For stability now, I will use AssetManager but Mock the DB to capture the output.
        # OR: Just instantiate the assets directly.
        
        try:
            from libraries_helper import get_video_metadata
            from video_asset import VideoAsset
            from base_assets import GenericFileAsset, AudioAsset, ImageAsset, DocumentAsset
            
            raw_meta = get_video_metadata(path, verbose=False)
            
            if group == 'VIDEO': asset = VideoAsset(path, raw_meta)
            elif group == 'IMAGE': asset = ImageAsset(path, raw_meta)
            elif group == 'AUDIO': asset = AudioAsset(path, raw_meta)
            elif group == 'DOCUMENT': asset = DocumentAsset(path, raw_meta)
            else: asset = GenericFileAsset(path, raw_meta)
            
            # Return data for main thread to write
            return (
                content_hash,
                asset.recorded_date,
                getattr(asset, 'width', None),
                getattr(asset, 'height', None),
                getattr(asset, 'duration', None),
                getattr(asset, 'bitrate', None if group != 'AUDIO' else asset.bitrate),
                getattr(asset, 'video_codec', None),
                asset.get_full_json()
            )
        except Exception:
            return None

    def process_metadata(self):
        records = self._get_files_to_process()
        if not records:
            print("No records require metadata processing.")
            return

        print(f"Processing metadata for {len(records)} files...")
        
        max_workers = os.cpu_count() or 4
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all
            future_to_hash = {executor.submit(self._process_single_file, r): r[0] for r in records}
            
            with tqdm(total=len(records), desc="Extracting", unit="file") as pbar:
                for future in concurrent.futures.as_completed(future_to_hash):
                    pbar.update(1)
                    try:
                        result = future.result()
                        if result:
                            # Unpack and Write to DB (Main Thread)
                            (c_hash, r_date, w, h, dur, bit, codec, json_meta) = result
                            
                            update_sql = """
                            UPDATE MediaContent SET
                                date_best = ?, width = ?, height = ?, duration = ?,
                                bitrate = ?, video_codec = ?, extended_metadata = ?
                            WHERE content_hash = ?;
                            """
                            self.db.execute_query(update_sql, (r_date, w, h, dur, bit, codec, json_meta, c_hash))
                            self.processed_count += 1
                        else:
                            self.skip_count += 1
                    except Exception as e:
                        tqdm.write(f"Error in thread: {e}")
                        self.skip_count += 1
                
        print(f"Metadata processing complete. Updated {self.processed_count} records.")

if __name__ == "__main__":
    manager = ConfigManager()
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--process', action='store_true')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Metadata Processor")
        sys.exit(0)
    elif args.process:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db:
            db.create_schema()
            MetadataProcessor(db, manager).process_metadata()