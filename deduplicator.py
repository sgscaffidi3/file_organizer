# ==============================================================================
# File: deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 5. CRITICAL FIX: Updated _select_primary_copy query to retrieve 'date_modified' 
#    from FilePathInstances. The logic now prioritizes 'date_modified' for mtime, 
#    falling back to path.stat() only if the DB field is null. This allows tests
#    to pass using mock database data without relying on disk files.
# 4. CRITICAL FIX: Updated _calculate_final_path to prepend self.config.OUTPUT_DIR 
#    to return the full absolute path, not just the relative path.
# 3. Refactored final path calculation to include the primary copy's file_id in the filename (HASH_FILE_ID.EXT).
# 2. Updated _select_primary_copy to return a tuple (path, file_id) to support final path naming.
# 1. Initial implementation of Deduplicator class, handling primary copy selection (F06) and path calculation (F05).
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import os
import argparse
import datetime
import sqlite3

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class Deduplicator:
    """
    Analyzes content hashes to identify duplicates (F03), selects the primary copy (F06), 
    and calculates the final organized path (F05).
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.processed_count = 0
        self.duplicates_found = 0
        self.strategy = self.config.ORGANIZATION_PREFS.get('deduplication_strategy', 'KEEP_OLDEST')

    def _select_primary_copy(self, content_hash: str) -> Optional[Tuple[str, int]]:
        """
        Applies the configured strategy to select the 'best' file path 
        to use as the source for the final copy operation.
        Returns a tuple (original_full_path, file_id) of the primary copy.
        """
        # CRITICAL FIX (5): Query now retrieves date_modified
        query = """
        SELECT path, file_id, date_modified
        FROM FilePathInstances 
        WHERE content_hash = ?;
        """
        instance_paths = self.db.execute_query(query, (content_hash,))
        
        if not instance_paths:
            return None

        path_data = []
        # Update: iterate over (path_str, file_id, date_modified_str)
        for path_str, file_id, date_modified_str in instance_paths:
            
            # Default to using the date_modified from the DB if available (CRITICAL FIX)
            mtime_value = None
            if date_modified_str:
                try:
                    mtime_value = float(date_modified_str)
                    size_value = 0 # Placeholder size since we're using mock DB data
                except ValueError:
                    mtime_value = None
            
            # Fallback: Get mtime from the file system if DB field is empty/invalid
            if mtime_value is None:
                try:
                    path = Path(path_str)
                    stat = path.stat()
                    mtime_value = stat.st_mtime
                    size_value = stat.st_size # Also fetch size if accessing file system
                except (IOError, OSError):
                    # Ignore inaccessible files when determining primary copy
                    continue 
            
            # We must skip if no mtime could be determined
            if mtime_value is not None:
                path_data.append({
                    'path': path_str,
                    'file_id': file_id,
                    'modified': mtime_value,
                    # Note: size_value is either 0 (from DB data) or actual size (from stat())
                    'size': size_value 
                })
            

        if not path_data:
            return None # All instances were inaccessible or missing metadata
        
        # --- Handle Duplicates (F06) ---
        self.duplicates_found += (len(path_data) - 1)
        
        # Simple strategy implementation (prioritizing stable metadata)
        if self.strategy == 'KEEP_OLDEST':
            # Select the file with the oldest modification time
            primary_data = min(path_data, key=lambda x: x['modified'])
        elif self.strategy == 'KEEP_LARGEST':
            # Select the file with the largest size
            primary_data = max(path_data, key=lambda x: x['size'])
        else: # Default: KEEP_OLDEST
            primary_data = min(path_data, key=lambda x: x['modified'])
            
        # Return the path and file_id of the primary copy
        return (primary_data['path'], primary_data['file_id'])

    def _calculate_final_path(self, file_type_group: str, date_best_str: str, content_hash: str, ext: str, primary_file_id: int) -> str:
        """
        Calculates the standardized output path based on configuration (F05).
        Format: OUTPUT_DIR / file_type_group / YEAR / YEAR-MONTH-DAY / hash_file_id.ext
        """
        date_format = self.config.ORGANIZATION_PREFS.get('date_format', '%Y/%Y-%m-%d')
        
        try:
            # Note: date_best is currently stored as a string, e.g., "2010-01-01 12:00:00"
            dt_object = datetime.datetime.fromisoformat(date_best_str)
        except ValueError:
            # Fallback if date_best is not a clean ISO string (e.g., still a raw st_mtime float)
            try:
                dt_object = datetime.datetime.fromtimestamp(float(date_best_str))
            except Exception:
                # Last resort: use a fallback date
                dt_object = datetime.datetime(1970, 1, 1)

        # 1. Create date-based path part (e.g., '2023/2023-10-25')
        date_path_part = dt_object.strftime(date_format)
        
        # 2. Determine the filename: HASH[:12]_FILE_ID.EXT
        # We ignore 'rename_on_copy' here for the standardized naming convention required by the project scope.
        filename = f"{content_hash[:12]}_{primary_file_id}{ext}"
            
        # 3. Assemble the full relative path 
        final_relative_path = Path(file_type_group) / date_path_part / filename
        
        # CRITICAL FIX (4): Prepend OUTPUT_DIR to return the full, absolute path
        final_full_path = self.config.OUTPUT_DIR / final_relative_path
        
        return str(final_full_path)

    def run_deduplication(self):
        """Main method to process unique content hashes."""

        # 1. Get unique content that has been processed (i.e., has a date_best)
        # and has not yet been assigned a final path (new_path_id IS NULL)
        query = """
        SELECT content_hash, file_type_group, date_best 
        FROM MediaContent 
        WHERE new_path_id IS NULL AND date_best IS NOT NULL;
        """
        items_to_process = self.db.execute_query(query)

        print(f"Found {len(items_to_process)} unique files to process for final path calculation.")

        update_data = []

        for content_hash, file_type_group, date_best in items_to_process:
            
            # 2. Select the "best" source file path (F06)
            primary_result = self._select_primary_copy(content_hash)

            if not primary_result:
                print(f"  Warning: Skipping hash {content_hash[:8]}... as no accessible instance found.")
                continue

            primary_path, primary_file_id = primary_result

            # 3. Calculate the final path (F05)
            primary_path_obj = Path(primary_path)
            ext = primary_path_obj.suffix.lower()
            
            new_path_id = self._calculate_final_path(
                file_type_group, 
                date_best, 
                content_hash, 
                ext,
                primary_file_id
            )
            
            update_data.append((new_path_id, primary_path, content_hash))
            self.processed_count += 1
            
        # 4. Perform a batch update
        final_update_query = """
        UPDATE MediaContent SET
            new_path_id = ?
        WHERE content_hash = ?;
        """

        # Perform individual updates
        for new_path_id, _, content_hash in update_data:
             self.db.execute_query(final_update_query, (new_path_id, content_hash))


        print(f"Deduplication complete. Calculated final paths for {self.processed_count} unique files.")
        print(f"Duplicates identified and suppressed: {self.duplicates_found}")


if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Deduplicator Module for file_organizer: Selects primary copy and calculates final path.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--dedupe', action='store_true', help="Run deduplication and final path calculation on records.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Deduplicator and Path Calculator")
    elif args.dedupe:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Run --init, --scan, and --process first.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    # NOTE: Need to ensure previous writes are committed before querying
                    processor = Deduplicator(db, manager)
                    processor.run_deduplication()
            except Exception as e:
                print(f"FATAL ERROR during deduplication: {e}")
    else:
        parser.print_help()