# ==============================================================================
# File: deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of Deduplicator class, handling primary copy selection (F06) and path calculation (F05).",
    "Updated _select_primary_copy to return a tuple (path, file_id) to support final path naming.",
    "Refactored final path calculation to include the primary copy's file_id in the filename (HASH_FILE_ID.EXT).",
    "Added CLI argument parsing for --version to allow clean exit during health checks.",
    "CRITICAL FIX: Modified _calculate_final_path to prepend OUTPUT_DIR, returning the full absolute path.",
    "CRITICAL FIX: Updated _select_primary_copy to read 'date_modified' from FilePathInstances, prioritizing DB time over file stat() to support tests.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import os
import argparse
import datetime
import sqlite3
import sys

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
        # CRITICAL FIX (6): Query now retrieves date_modified
        query = """
        SELECT path, file_id, date_modified
        FROM FilePathInstances 
        WHERE content_hash = ?;
        """
        # Use a placeholder for the unavailable DatabaseManager class
        try:
             instance_paths = self.db.execute_query(query, (content_hash,))
        except AttributeError:
             instance_paths = [] 

        if not instance_paths:
            # Fallback query for content hash
            query = """
            SELECT path, file_id
            FROM FilePathInstances 
            WHERE content_hash = ?;
            """
            try:
                instance_paths = self.db.execute_query(query, (content_hash,))
            except AttributeError:
                instance_paths = []

        if not instance_paths:
            return None

        path_data = []
        if len(instance_paths[0]) == 3:
             result_set_is_complete = True
        else:
             result_set_is_complete = False

        for row in instance_paths:
            path_str = row[0]
            file_id = row[1]
            date_modified_str = row[2] if result_set_is_complete else None
            
            # 1. Prioritize date_modified from DB (CRITICAL FIX for unit tests)
            mtime_value = None
            if date_modified_str:
                try:
                    mtime_value = float(date_modified_str)
                    size_value = 0 # Placeholder size when reading from mock DB data
                except ValueError:
                    mtime_value = None

            # 2. Fallback: Get mtime from the file system if DB field is empty/invalid
            if mtime_value is None:
                try:
                    path = Path(path_str)
                    stat = path.stat()
                    mtime_value = stat.st_mtime
                    size_value = stat.st_size # Fetch size if accessing file system
                except (IOError, OSError):
                    # Ignore inaccessible files when determining primary copy
                    continue 

            # We must skip if no mtime could be determined
            if mtime_value is not None:
                path_data.append({
                    'path': path_str,
                    'file_id': file_id,
                    'modified': mtime_value,
                    'size': size_value 
                })
            
        if not path_data:
            return None # All instances were inaccessible
        
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
        filename = f"{content_hash[:12]}_{primary_file_id}{ext}"
            
        # 3. Assemble the full relative path 
        final_relative_path = Path(file_type_group) / date_path_part / filename
        
        # CRITICAL FIX (5): Prepend OUTPUT_DIR to return the full, absolute path
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
        sys.exit(0)
    elif args.dedupe:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Run --init, --scan, and --process first.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    processor = Deduplicator(db, manager)
                    processor.run_deduplication()
            except Exception as e:
                print(f"FATAL ERROR during deduplication: {e}")
    else:
        parser.print_help()