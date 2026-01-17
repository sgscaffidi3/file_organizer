# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [17]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.13.17
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import sys
import concurrent.futures
import os
import argparse
from tqdm import tqdm

from database_manager import DatabaseManager
from config_manager import ConfigManager
from asset_manager import AssetManager
import config

# LOWERED BATCH SIZE: Saves progress more frequently (every ~50 files)
DB_BATCH_SIZE = 50

class MetadataProcessor:
    """Processes MediaContent records missing metadata using multithreading and batch commits."""
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        # Updated Query: Also check for missing perceptual_hash in Images
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.original_full_path
        FROM MediaContent T1
        INNER JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash AND T2.is_primary = 1
        WHERE 
           (T1.file_type_group IN ('IMAGE', 'VIDEO') AND (T1.width IS NULL OR T1.height IS NULL))
           OR
           (T1.file_type_group = 'IMAGE' AND T1.perceptual_hash IS NULL)
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
            from libraries_helper import get_video_metadata, calculate_image_hash
            from video_asset import VideoAsset
            from base_assets import GenericFileAsset, AudioAsset, ImageAsset, DocumentAsset
            
            # Note: We re-extract metadata here. Ideally in future we only extract what is missing.
            raw_meta = get_video_metadata(path, verbose=False)
            
            p_hash = None
            
            if group == 'VIDEO': 
                asset = VideoAsset(path, raw_meta)
            elif group == 'IMAGE': 
                asset = ImageAsset(path, raw_meta)
                p_hash = calculate_image_hash(path)
                # CRITICAL FIX: If hashing fails (missing lib or corrupt file), set a sentinel
                if p_hash is None:
                    p_hash = "UNKNOWN"
            elif group == 'AUDIO': 
                asset = AudioAsset(path, raw_meta)
            elif group == 'DOCUMENT': 
                asset = DocumentAsset(path, raw_meta)
            else: 
                asset = GenericFileAsset(path, raw_meta)
            
            return (
                asset.recorded_date, # May be None
                getattr(asset, 'width', None),
                getattr(asset, 'height', None),
                getattr(asset, 'duration', None),
                getattr(asset, 'bitrate', None if group != 'AUDIO' else asset.bitrate),
                getattr(asset, 'video_codec', None),
                p_hash,
                asset.get_full_json(),
                content_hash
            )
        except Exception:
            return None

    def process_metadata(self):
        print("Scanning database for unprocessed files...", flush=True)
        records = self._get_files_to_process()
        
        # Get total count for context
        total_assets = self.db.execute_query("SELECT COUNT(*) FROM MediaContent")[0][0]
        completed = total_assets - len(records)
        
        print("-" * 60, flush=True)
        print(f" Total Assets:     {total_assets}", flush=True)
        print(f" Already Done:     {completed}", flush=True)
        print(f" Left to Process:  {len(records)}", flush=True)
        print("-" * 60, flush=True)
        
        if not records:
            print("✅ Metadata is up to date.", flush=True)
            return

        print(f"Spinning up {config.METADATA_THREADS} threads (Batch Size: {DB_BATCH_SIZE})...", flush=True)
        
        batch_updates = []
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=config.METADATA_THREADS) as executor:
                future_to_hash = {executor.submit(self._process_single_file, r): r[0] for r in records}
                
                with tqdm(total=len(records), desc="Processing", unit="file") as pbar:
                    for future in concurrent.futures.as_completed(future_to_hash):
                        pbar.update(1)
                        try:
                            result = future.result()
                            if result:
                                batch_updates.append(result)
                                self.processed_count += 1
                            else:
                                self.skip_count += 1
                                
                            if len(batch_updates) >= DB_BATCH_SIZE:
                                self._flush_batch(batch_updates)
                                batch_updates.clear()
                                
                        except Exception as e:
                            tqdm.write(f"Error in thread: {e}")
                            self.skip_count += 1
                
                # Final flush
                if batch_updates:
                    self._flush_batch(batch_updates)

        except KeyboardInterrupt:
            print("\n\n🛑 User Interrupted! Saving pending batch...", flush=True)
            if batch_updates:
                self._flush_batch(batch_updates)
                print(f"✅ Saved {len(batch_updates)} records. You can resume later.", flush=True)
            else:
                print("No pending records to save.", flush=True)
            sys.exit(0)
                
        print(f"Metadata processing complete. Updated {self.processed_count} records.", flush=True)

    def _flush_batch(self, data):
        """Executes a batch update. Uses COALESCE to protect existing dates."""
        if not data: return
        
        # SQLite COALESCE(?, date_best) checks if the new value (?) is NULL.
        update_sql = """
        UPDATE MediaContent SET
            date_best = COALESCE(?, date_best), 
            width = ?, 
            height = ?, 
            duration = ?,
            bitrate = ?, 
            video_codec = ?, 
            perceptual_hash = ?,
            extended_metadata = ?
        WHERE content_hash = ?;
        """
        try:
            self.db.execute_many(update_sql, data)
        except Exception as e:
            print(f"Batch Write Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--process', action='store_true')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Metadata Processor")
        sys.exit(0)
    elif args.process:
        manager = ConfigManager()
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db:
            MetadataProcessor(db, manager).process_metadata()