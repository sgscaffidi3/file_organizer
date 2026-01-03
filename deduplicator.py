# ==============================================================================
# File: deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation of Deduplicator class, handling primary copy selection (F06) and path calculation (F05).",
    "Updated _select_primary_copy to return a tuple (path, file_id) to support final path naming.",
    "Refactored final path calculation to include the primary copy's file_id in the filename (HASH_FILE_ID.EXT).",
    "Added CLI argument parsing for --version to allow clean exit during health checks.",
    "CRITICAL FIX: Modified _calculate_final_path to prepend OUTPUT_DIR, returning the full absolute path.",
    "CRITICAL FIX: Updated _select_primary_copy to read 'date_modified' from FilePathInstances, prioritizing DB time over file stat() to support tests.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "CRITICAL FIX: Updated `_calculate_final_path` signature to match the requirements of `test_deduplicator.py` (`ext` and `primary_file_id`).",
    "UX: Added TQDM progress bar for deduplication feedback."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.10
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import os
import argparse
import datetime
import sqlite3
import sys
from tqdm import tqdm

import config
from database_manager import DatabaseManager
from config_manager import ConfigManager 

class Deduplicator:
    """
    Identifies duplicate file content and selects a single 'primary' copy.
    It then calculates the final, organized path for that content.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.processed_count = 0
        self.duplicates_found = 0

    def _select_primary_copy(self, content_hash: str) -> Optional[Tuple[str, int]]:
        """
        Selects the primary file instance for a given content hash.
        Criteria: Earliest date > Shortest path > Smallest file_id
        """
        query = """
        SELECT path, file_id
        FROM FilePathInstances
        WHERE content_hash = ?
        ORDER BY 
            date_modified ASC, 
            LENGTH(path) ASC,
            file_id ASC
        LIMIT 1;
        """
        result = self.db.execute_query(query, (content_hash,))
        
        if result and result[0]:
            primary_path, primary_file_id = result[0]
            update_query = "UPDATE FilePathInstances SET is_primary = 1 WHERE file_id = ?;"
            self.db.execute_query(update_query, (primary_file_id,))
            return primary_path, primary_file_id
            
        return None

    def _calculate_final_path(self, primary_path: str, content_hash: str, ext: str, primary_file_id: int) -> str:
        """
        Calculates the final, organized path based on the primary copy's date and hash.
        Format: OUTPUT_DIR/YEAR/MONTH/HASH_FILEID.EXT
        """
        try:
            # Try to get date_best from MediaContent
            query = "SELECT T1.date_best FROM MediaContent T1 JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash WHERE T2.file_id = ?;"
            date_best_result = self.db.execute_query(query, (primary_file_id,))
            
            if date_best_result and date_best_result[0][0]:
                date_best_str = date_best_result[0][0]
                # date_best format usually YYYY-MM-DD HH:MM:SS or similar
                # Simple parser for YYYY-MM-DD
                date_obj = datetime.datetime.strptime(date_best_str.split()[0], '%Y-%m-%d')
            else:
                date_obj = datetime.datetime.now()
        except Exception:
            date_obj = datetime.datetime.now()
            
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%m')
        hash_prefix = content_hash[:12]
        filename = f"{hash_prefix}_{primary_file_id}{ext}"
        
        relative_path = Path(year) / month / filename
        final_path = self.config.OUTPUT_DIR / relative_path
        return str(final_path)

    def run_deduplication(self):
        """Main method to iterate through all unique content and calculate final paths."""
        select_hashes_query = "SELECT content_hash, file_type_group FROM MediaContent;"
        hashes_to_process = self.db.execute_query(select_hashes_query)
        
        print(f"Starting deduplication for {len(hashes_to_process)} unique content hashes.")

        self.processed_count = 0
        self.duplicates_found = 0

        with tqdm(total=len(hashes_to_process), desc="Deduplicating", unit="hash") as pbar:
            for content_hash, file_type_group in hashes_to_process:
                pbar.update(1)
                
                # 1. Select the primary copy
                primary_result = self._select_primary_copy(content_hash)
                
                if not primary_result:
                    continue

                primary_path, primary_file_id = primary_result
                ext = Path(primary_path).suffix
                
                # 2. Calculate the final path 
                final_path = self._calculate_final_path(
                    primary_path, 
                    content_hash, 
                    ext, 
                    primary_file_id
                )
                
                self.processed_count += 1
                
                # 3. Mark the primary instance with its final path
                update_primary_query = "UPDATE MediaContent SET new_path_id = ? WHERE content_hash = ?;"
                self.db.execute_query(update_primary_query, (final_path, content_hash))
                
                # 4. Count the number of duplicates for this hash
                count_query = "SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ? AND is_primary = 0;"
                duplicate_count = self.db.execute_query(count_query, (content_hash,))
                self.duplicates_found += duplicate_count[0][0]

        print(f"Deduplication complete. Calculated final paths for {self.processed_count} unique files.")
        print(f"Duplicates identified and suppressed: {self.duplicates_found}")


if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Deduplicator Module for file_organizer.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--dedupe', action='store_true', help="Run deduplication.")
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Deduplicator and Path Calculator")
        sys.exit(0)
    elif args.dedupe:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    processor = Deduplicator(db, manager)
                    processor.run_deduplication()
            except Exception as e:
                print(f"FATAL ERROR during deduplication process: {e}")
    else:
        parser.print_help()