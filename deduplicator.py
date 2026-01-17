# ==============================================================================
# File: deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [14]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.8.14
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import os
import argparse
import datetime
import re
import sys
from tqdm import tqdm

import config
from database_manager import DatabaseManager
from config_manager import ConfigManager 

class Deduplicator:
    """
    Identifies duplicate file content and selects a single 'primary' copy.
    Optimized for high-speed batch processing.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.processed_count = 0
        self.duplicates_found = 0
        self.assigned_paths: Set[str] = set()

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    def _parse_date(self, date_str: str) -> Optional[datetime.datetime]:
        """Attempts to parse a date string into a datetime object."""
        if not date_str or date_str == "Unknown":
            return None
        try:
            # Handle YYYY-MM-DD HH:MM:SS
            return datetime.datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
        except:
            try:
                # Handle YYYY-MM-DD
                return datetime.datetime.strptime(date_str.split()[0], '%Y-%m-%d')
            except:
                return None

    def _calculate_final_path(self, primary_path: str, content_hash: str, ext: str, primary_file_id: int, date_best_str: str, date_fs_str: str) -> str:
        """
        Calculates the final, organized path.
        Priority: date_best (Metadata) -> date_fs (FileSystem) -> Today
        """
        date_obj = None
        
        # 1. Try Metadata Date
        if date_best_str:
            try:
                date_obj = datetime.datetime.strptime(date_best_str.split()[0], '%Y-%m-%d')
            except: pass
            
        # 2. Try File System Date (Fallback)
        if not date_obj and date_fs_str:
            try:
                date_obj = datetime.datetime.strptime(date_fs_str.split()[0], '%Y-%m-%d')
            except: pass
            
        # 3. Ultimate Fallback (Today) - Should rarely happen if scanned correctly
        if not date_obj:
            date_obj = datetime.datetime.now()
            
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%m')
        
        # Check Configuration
        rename_enabled = self.config.ORGANIZATION_PREFS.get('rename_on_copy', True)
        
        if rename_enabled:
            hash_prefix = content_hash[:12]
            filename = f"{hash_prefix}_{primary_file_id}{ext}"
        else:
            original_name = Path(primary_path).stem
            safe_name = self._sanitize_filename(original_name)
            filename = f"{safe_name}{ext}"
            
            rel_check = f"{year}/{month}/{filename}"
            if rel_check in self.assigned_paths:
                filename = f"{safe_name}_{primary_file_id}{ext}"

        relative_path = Path(year) / month / filename
        final_path = self.config.OUTPUT_DIR / relative_path
        
        self.assigned_paths.add(f"{year}/{month}/{filename}")
        
        return str(final_path)

    def run_deduplication(self):
        print("Resetting previous deduplication state...")
        self.db.execute_query("UPDATE FilePathInstances SET is_primary = 0;")
        
        print("Fetching all file instances (this may take a moment)...")
        # Added fpi.date_modified to query for fallback
        query = """
        SELECT 
            fpi.content_hash, 
            fpi.file_id, 
            fpi.path, 
            mc.date_best,
            fpi.date_modified
        FROM FilePathInstances fpi
        JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
        ORDER BY 
            fpi.content_hash ASC, 
            fpi.date_modified ASC, 
            LENGTH(fpi.path) ASC, 
            fpi.file_id ASC;
        """
        all_rows = self.db.execute_query(query)
        
        print(f"Processing {len(all_rows)} instances...")
        
        seen_hashes: Set[str] = set()
        self.assigned_paths.clear()
        
        primary_id_updates: List[Tuple[int]] = []
        media_content_updates: List[Tuple[str, str]] = []
        
        self.duplicates_found = 0
        self.processed_count = 0

        with tqdm(total=len(all_rows), desc="Deduplicating", unit="file") as pbar:
            for content_hash, file_id, path_str, date_best, date_fs in all_rows:
                pbar.update(1)
                
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    
                    primary_id_updates.append((file_id,))
                    
                    ext = Path(path_str).suffix
                    # Pass both dates to calculation
                    final_path = self._calculate_final_path(path_str, content_hash, ext, file_id, date_best, date_fs)
                    
                    media_content_updates.append((final_path, content_hash))
                    self.processed_count += 1
                else:
                    self.duplicates_found += 1

        print("Committing updates to database...")
        
        if primary_id_updates:
            self.db.execute_many(
                "UPDATE FilePathInstances SET is_primary = 1 WHERE file_id = ?;", 
                primary_id_updates
            )
            
        if media_content_updates:
            self.db.execute_many(
                "UPDATE MediaContent SET new_path_id = ? WHERE content_hash = ?;",
                media_content_updates
            )

        print(f"Deduplication complete.")
        print(f"  Unique Files Processed: {self.processed_count}")
        print(f"  Duplicates Suppressed:  {self.duplicates_found}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--dedupe', action='store_true')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Deduplicator and Path Calculator")
        sys.exit(0)
    elif args.dedupe:
        manager = ConfigManager()
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db:
            processor = Deduplicator(db, manager)
            processor.run_deduplication()