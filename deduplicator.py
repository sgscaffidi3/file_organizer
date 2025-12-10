# ==============================================================================
# File: deduplicator.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
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

    def _select_primary_copy(self, content_hash: str) -> Optional[str]:
        """
        Applies the configured strategy to select the 'best' file path 
        to use as the source for the final copy operation.
        Returns the original_full_path of the primary copy.
        """
        # Query all instances for the given hash, including their file stats
        query = """
        SELECT original_full_path 
        FROM FilePathInstances 
        WHERE content_hash = ?;
        """
        instance_paths = self.db.execute_query(query, (content_hash,))
        
        if not instance_paths:
            return None

        paths = [Path(p[0]) for p in instance_paths]

        if len(paths) == 1:
            return str(paths[0])
            
        # --- Handle Duplicates (F06) ---
        self.duplicates_found += (len(paths) - 1)
        
        # Get stat metadata for all paths
        path_data = []
        for path in paths:
            try:
                stat = path.stat()
                # Use st_ctime for creation time (cross-platform), st_mtime for modification time
                path_data.append({
                    'path': path,
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime,
                    'size': stat.st_size
                })
            except (IOError, OSError):
                # Ignore inaccessible files when determining primary copy
                pass 

        if not path_data:
            return None # All instances were inaccessible
        
        # Simple strategy implementation (prioritizing stable metadata)
        if self.strategy == 'KEEP_OLDEST':
            # Select the file with the oldest modification time
            # Assumes oldest copy is the original
            primary_data = min(path_data, key=lambda x: x['modified'])
        elif self.strategy == 'KEEP_LARGEST':
            # Select the file with the largest size (useful if one copy is corrupted/truncated)
            primary_data = max(path_data, key=lambda x: x['size'])
        else: # Default: KEEP_OLDEST
            primary_data = min(path_data, key=lambda x: x['modified'])
            
        return str(primary_data['path'])

    def _calculate_final_path(self, file_type_group: str, date_best_str: str, content_hash: str) -> str:
        """
        Calculates the standardized output path based on configuration (F05).
        Format: OUTPUT_DIR / file_type_group / YEAR / YEAR-MONTH-DAY / hash.ext
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
        
        # 2. Determine the filename
        # We need the extension. We can't easily get it here without querying 
        # FilePathInstances again. For now, use a placeholder extension.
        # NOTE: A robust solution would pass the original primary copy path to get the extension.
        
        ext = '.dat' # Placeholder, must be fixed later or derived from primary copy path
        
        if self.config.ORGANIZATION_PREFS.get('rename_on_copy', True):
            filename = f"{content_hash[:12]}_{dt_object.strftime('%H%M%S')}{ext}"
        else:
            # Fallback to a simpler, content-based name
            filename = f"{content_hash[:12]}{ext}"
            
        # 3. Assemble the full relative path 
        final_relative_path = Path(file_type_group) / date_path_part / filename
        
        return str(final_relative_path)

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
            primary_path = self._select_primary_copy(content_hash)

            if not primary_path:
                print(f"  Warning: Skipping hash {content_hash[:8]}... as no accessible instance found.")
                continue

            # 3. Calculate the final path (F05)
            # NOTE: We need the extension of the primary path for _calculate_final_path
            
            # --- Robust Extension Handling ---
            primary_path_obj = Path(primary_path)
            ext = primary_path_obj.suffix.lower()
            
            # Recalculate the final path using a slightly modified helper
            new_path_id = self._calculate_final_path_with_ext(
                file_type_group, 
                date_best, 
                content_hash, 
                ext
            )
            
            update_data.append((new_path_id, primary_path, content_hash))
            self.processed_count += 1
            
        # 4. Perform a batch update
        update_query = """
        UPDATE MediaContent SET
            new_path_id = ?,
            primary_full_path = ? -- NOTE: primary_full_path field needs to be added to the schema! 
        WHERE content_hash = ?;
        """
        # Since we haven't updated the schema to include `primary_full_path`, 
        # we will only update `new_path_id` for now to keep the code running.
        
        final_update_query = """
        UPDATE MediaContent SET
            new_path_id = ?
        WHERE content_hash = ?;
        """

        # Perform individual updates for now until schema update is confirmed
        for new_path_id, _, content_hash in update_data:
             self.db.execute_query(final_update_query, (new_path_id, content_hash))


        print(f"Deduplication complete. Calculated final paths for {self.processed_count} unique files.")
        print(f"Duplicates identified and suppressed: {self.duplicates_found}")
        
    # Temporary helper to fix the extension issue in _calculate_final_path
    def _calculate_final_path_with_ext(self, file_type_group: str, date_best_str: str, content_hash: str, ext: str) -> str:
        """Correct helper that accepts the extension."""
        date_format = self.config.ORGANIZATION_PREFS.get('date_format', '%Y/%Y-%m-%d')
        
        try:
            dt_object = datetime.datetime.fromisoformat(date_best_str)
        except:
            try:
                dt_object = datetime.datetime.fromtimestamp(float(date_best_str))
            except:
                dt_object = datetime.datetime(1970, 1, 1)

        date_path_part = dt_object.strftime(date_format)
        
        if self.config.ORGANIZATION_PREFS.get('rename_on_copy', True):
            filename = f"{content_hash[:12]}_{dt_object.strftime('%H%M%S')}{ext}"
        else:
            filename = f"{content_hash[:12]}{ext}"
            
        final_relative_path = Path(file_type_group) / date_path_part / filename
        
        return str(final_relative_path)


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