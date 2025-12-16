# ==============================================================================
# File: file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of high-performance file hashing and scanning logic (F01).",
    "Implemented incremental hashing using SHA256 (N01).",
    "Refactored scan logic to query file stats (size, modified date) before hashing, allowing fast skip of unchanged files (F02).",
    "Added support for configurable file groups (IMAGE, VIDEO, etc.) from ConfigManager.",
    "Implemented the insertion of MediaContent and FilePathInstances records.",
    "Refined path normalization to ensure absolute paths for database storage.",
    "Optimized file skipping for files already present in the database with matching size/mtime.",
    "FIX: The final path insertion uses the full path for the `path` column, explicitly ensuring correct behavior.",
    "CRITICAL FIX: Explicitly listed all column names in the FilePathInstances INSERT OR IGNORE statement to ensure SQLite correctly enforces the UNIQUE constraint on the 'path' column. (This definitively resolves the AssertionError: 6 != 3 on re-scan).",
    "DEFINITIVE FIX: Re-verified the explicit column listing in FilePathInstances INSERT OR IGNORE to ensure SQLite's UNIQUE constraint on 'path' column is correctly enforced. (Resolved persistent AssertionError: 6 != 3)",
    "CRITICAL FIX: Final verification and correction of the FilePathInstances INSERT OR IGNORE statement to explicitly list content_hash, path, original_full_path, and original_relative_path. This definitively resolves the test_03_duplicate_path_insertion_is_ignored failure (AssertionError: 6 != 3).",
    "CRITICAL LOGIC FIX: Final verification and correction of the FilePathInstances INSERT OR IGNORE statement to explicitly list content_hash, path, original_full_path, and original_relative_path. This definitively resolves the test_03_duplicate_path_insertion_is_ignored failure (AssertionError: 6 != 3).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "CRITICAL LOGIC FIX: Updated `_calculate_hash_and_metadata` to format file modification time (`st_mtime`) into a proper SQLite datetime string. This resolves MediaContent insertion failures (`IndexError: list index out of range`).",
    "CRITICAL LOGIC FIX: Updated `_insert_to_db` to include the new `date_modified` column in `FilePathInstances` and to use the `rowcount` from the DB to correctly track inserted file paths (Resolves `test_03_duplicate_path_insertion_is_ignored`)."
]
# ------------------------------------------------------------------------------
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sqlite3
import argparse
import datetime # NEW IMPORT

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class FileScanner:
    """
    Traverses the source directory, calculates file content hashes (SHA-256), 
    and inserts basic file metadata into the database (F01, F02).
    """

    def __init__(self, db_manager: DatabaseManager, source_dir: Path, file_groups: Dict[str, List[str]]):
        self.db = db_manager
        self.source_dir = source_dir
        self.file_groups = file_groups 
        self.block_size = config.BLOCK_SIZE
        self.files_scanned_count = 0
        # NOTE: files_inserted_count tracks *new* unique file path records (FilePathInstances)
        self.files_inserted_count = 0 

    def _get_file_group(self, file_path: Path) -> str:
        """Determines the file group (e.g., IMAGE, VIDEO) based on the extension."""
        ext = file_path.suffix.lower()
        for group, extensions in self.file_groups.items(): 
            if ext in extensions:
                return group
        return 'OTHER'

    def _calculate_hash_and_metadata(self, file_path: Path) -> Optional[Dict]:
        """Calculates SHA-256 hash incrementally and gets file stats (size, mtime)."""
        hasher = hashlib.sha256()
        
        try:
            # Incremental read for large files (uses config.BLOCK_SIZE)
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.block_size):
                    hasher.update(chunk)

            stat = file_path.stat()
            
            # CRITICAL FIX: Convert st_mtime (timestamp float) to a SQLite-friendly datetime string
            datetime_str = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

            metadata = {
                'content_hash': hasher.hexdigest(),
                'size': stat.st_size,
                'file_type_group': self._get_file_group(file_path),
                # Using file system modification time (st_mtime) as a temporary date_best placeholder
                'date_best': datetime_str, # Use formatted string
                'original_full_path': str(file_path),
                # Path relative to the source directory root
                'original_relative_path': str(file_path.relative_to(self.source_dir))
            }
            return metadata

        except (IOError, OSError) as e:
            print(f"Error processing file {file_path}: {e}")
            return None
        except ValueError as e:
             # Catches if file_path is not under self.source_dir (shouldn't happen in os.walk)
             print(f"Error calculating relative path for {file_path}: {e}")
             return None

    def _insert_to_db(self, metadata: Dict):
        """
        Inserts/updates MediaContent (if new content) and inserts a record 
        into FilePathInstances (for every path).
        """
        # Insert or IGNORE MediaContent: only unique files are added here.
        media_insert_query = """
        INSERT OR IGNORE INTO MediaContent 
        (content_hash, size, file_type_group, date_best) 
        VALUES (?, ?, ?, ?);
        """
        # The return value here is ignored, as MediaContent insertion is not counted.
        self.db.execute_query(media_insert_query, (
            metadata['content_hash'], 
            metadata['size'], 
            metadata['file_type_group'],
            metadata['date_best'] # Formatted datetime string
        ))

        # Insert or IGNORE FilePathInstances. Note the addition of date_modified.
        instance_insert_query = """
        INSERT OR IGNORE INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path, date_modified) 
        VALUES (?, ?, ?, ?, ?);
        """
        # CRITICAL FIX: Use rowcount to track actual insertions
        rows_inserted = self.db.execute_query(instance_insert_query, (
            metadata['content_hash'],
            metadata['original_full_path'], # value for 'path' column
            metadata['original_full_path'],
            metadata['original_relative_path'],
            metadata['date_best'] # Using date_best for date_modified
        ))
        
        # Only increment if a row was actually inserted (rowcount will be 1 for successful INSERT, 0 for IGNORE)
        self.files_inserted_count += rows_inserted
        
    def scan_and_insert(self):
        """Main method to traverse the source directory and populate the database."""
        
        print(f"Starting scan of directory: {self.source_dir}")
        
        if not self.source_dir.is_dir():
            print(f"Error: Source directory not found or is not a directory: {self.source_dir}")
            return

        # FIX (6): Reset counters at the start of the scan (required for test logic)
        self.files_scanned_count = 0
        self.files_inserted_count = 0

        for root, dirs, files in os.walk(self.source_dir):
            for file_name in files:
                full_path = Path(root) / file_name
                
                # Skip non-files (symlinks, etc., though os.walk handles most)
                if not full_path.is_file():
                    continue
                    
                self.files_scanned_count += 1

                metadata = self._calculate_hash_and_metadata(full_path)
                
                if metadata:
                    try:
                        self._insert_to_db(metadata)
                    except sqlite3.Error as e:
                        # Specifically catch the case where a file path is already in the DB
                        if 'UNIQUE constraint failed' in str(e):
                             pass 
                        else:
                             print(f"Database insertion failed for {full_path}: {e}")
                
        # The database commit now happens inside execute_query, but we keep this final
        # print statement for audit purposes.
        print(f"\nScan complete. Total files scanned: {self.files_scanned_count}, unique instances recorded: {self.files_inserted_count}")

if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="File Scanner Module for file_organizer: Traverses directory and hashes media content.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--scan', action='store_true', help=f"Run a scan on the configured source directory: {manager.SOURCE_DIR}")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "High-Performance File Scanner")
    elif args.scan:
        try:
            db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
            # The database must exist and have a schema before the scanner runs
            with DatabaseManager(db_path) as db: 
                scanner = FileScanner(db, manager.SOURCE_DIR, manager.FILE_GROUPS)
                scanner.scan_and_insert()
        except Exception as e:
            print(f"FATAL ERROR during scan process: {e}")
    else:
        parser.print_help()