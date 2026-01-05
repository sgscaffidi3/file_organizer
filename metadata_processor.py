# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 8
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class (F04).",
    "PRODUCTION UPGRADE: Integrated Pillow and Hachoir for extraction.",
    "RELIABILITY: Added safety handling for missing physical files.",
    "ARCHITECTURE REFACTOR: Migrated to Hybrid Metadata model via AssetManager.",
    "CLEANUP: Removed redundant local extractors; delegated all routing to AssetManager.",
    "FEATURE: Enabled full support for VIDEO, IMAGE, AUDIO, and DOCUMENT groups.",
    "UX: Added TQDM progress bar for real-time extraction feedback.",
    "BUG FIX: Updated _get_files_to_process query to prevent infinite re-processing of Audio/Docs.",
    "PERFORMANCE: Implemented Multithreaded Metadata Extraction using ThreadPoolExecutor.",
    "PERFORMANCE: Implemented Batch Database Writes (1000/batch) to fix SQLite locking issues."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.8.10
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import sys
import concurrent.futures
import os
from tqdm import tqdm

from database_manager import DatabaseManager
from config_manager import ConfigManager
from asset_manager import AssetManager
import config

DB_BATCH_SIZE = 1000

class MetadataProcessor:
    """Processes MediaContent records missing metadata using multithreading and batch commits."""
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
            
        try:
            # Local import to avoid circular dependency/pickling issues in threads
            from libraries_helper import get_video_metadata
            from video_asset import VideoAsset
            from base_assets import GenericFileAsset, AudioAsset, ImageAsset, DocumentAsset
            
            raw_meta = get_video_metadata(path, verbose=False)
            
            if group == 'VIDEO': asset = VideoAsset(path, raw_meta)
            elif group == 'IMAGE': asset = ImageAsset(path, raw_meta)
            elif group == 'AUDIO': asset = AudioAsset(path, raw_meta)
            elif group == 'DOCUMENT': asset = DocumentAsset(path, raw_meta)
            else: asset = GenericFileAsset(path, raw_meta)
            
            # Extract data needed for DB update
            return (
                asset.recorded_date,
                getattr(asset, 'width', None),
                getattr(asset, 'height', None),
                getattr(asset, 'duration', None),
                getattr(asset, 'bitrate', None if group != 'AUDIO' else asset.bitrate),
                getattr(asset, 'video_codec', None),
                asset.get_full_json(),
                content_hash # WHERE clause
            )
        except Exception:
            return None

    def process_metadata(self):
        records = self._get_files_to_process()
        if not records:
            print("No records require metadata processing.")
            return

        print(f"Processing metadata for {len(records)} files...")
        print(f"Threads: {config.METADATA_THREADS}")
        
        # Buffer for batch updates
        batch_updates = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.METADATA_THREADS) as executor:
            future_to_hash = {executor.submit(self._process_single_file, r): r[0] for r in records}
            
            with tqdm(total=len(records), desc="Extracting", unit="file") as pbar:
                for future in concurrent.futures.as_completed(future_to_hash):
                    pbar.update(1)
                    try:
                        result = future.result()
                        if result:
                            batch_updates.append(result)
                            self.processed_count += 1
                        else:
                            self.skip_count += 1
                            
                        # Batch Commit
                        if len(batch_updates) >= DB_BATCH_SIZE:
                            self._flush_batch(batch_updates)
                            batch_updates.clear()
                            
                    except Exception as e:
                        tqdm.write(f"Error in thread: {e}")
                        self.skip_count += 1
            
            # Final Flush
            if batch_updates:
                self._flush_batch(batch_updates)
                
        print(f"Metadata processing complete. Updated {self.processed_count} records.")

    def _flush_batch(self, data):
        """Executes a batch update."""
        update_sql = """
        UPDATE MediaContent SET
            date_best = ?, width = ?, height = ?, duration = ?,
            bitrate = ?, video_codec = ?, extended_metadata = ?
        WHERE content_hash = ?;
        """
        try:
            self.db.execute_many(update_sql, data)
        except Exception as e:
            print(f"Batch Write Failed: {e}")

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
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with DatabaseManager(db_path) as db:
            db.create_schema()
            MetadataProcessor(db, manager).process_metadata()