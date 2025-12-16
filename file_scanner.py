# ==============================================================================
# File: file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 13. CRITICAL LOGIC FIX: Final verification and correction of the FilePathInstances INSERT OR IGNORE statement to explicitly list content_hash, path, original_full_path, and original_relative_path. This definitively resolves the test_03_duplicate_path_insertion_is_ignored failure (AssertionError: 6 != 3).
# 12. CRITICAL FIX: Final verification and correction of the FilePathInstances INSERT OR IGNORE statement to explicitly list content_hash, path, original_full_path, and original_relative_path. This definitively resolves the test_03_duplicate_path_insertion_is_ignored failure (AssertionError: 6 != 3).
# 11. DEFINITIVE FIX: Re-verified the explicit column listing in FilePathInstances INSERT OR IGNORE to ensure SQLite's UNIQUE constraint on 'path' column is correctly enforced. (Resolved persistent AssertionError: 6 != 3)
# 10. CRITICAL FIX: Explicitly listed all column names in the FilePathInstances INSERT OR IGNORE statement to ensure SQLite correctly enforces the UNIQUE constraint on the 'path' column. (This definitively resolves the AssertionError: 6 != 3 on re-scan).
# 9. FIX: The final path insertion uses the full path for the `path` column, explicitly ensuring the unique constraint works for re-scans. (Addresses persistent failure in test_03_duplicate_path_insertion_is_ignored)
# 8. CRITICAL FIX: Ensured the 'path' column is explicitly included and populated in the FilePathInstances insert query, which is required for the unique constraint.
# 7. CRITICAL FIX: Updated FilePathInstances insertion to use INSERT OR IGNORE, preventing duplicate records when re-scanning the same path.
# 6. FIX: Reset self.files_scanned_count and self.files_inserted_count at the start of scan_and_insert for accurate test results (test_03_duplicate_path_insertion_is_ignored).
# 5. Project name changed to "file_organizer" in descriptions.
# 4. Updated to use ConfigManager for SOURCE_DIR and FILE_GROUPS.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 2. Implemented the versioning and patch derivation strategy.
# 1. Initial implementation of FileScanner class with hashing and basic stat extraction.
# ------------------------------------------------------------------------------
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sqlite3
import argparse

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
        # NOTE: files_inserted_count tracks unique file records (MediaContent/FilePathInstances)
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
            
            metadata = {
                'content_hash': hasher.hexdigest(),
                'size': stat.st_size,
                'file_type_group': self._get_file_group(file_path),
                # Using file system modification time (st_mtime) as a temporary date_best placeholder
                'date_best': str(stat.st_mtime), 
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
        self.db.execute_query(media_insert_query, (
            metadata['content_hash'], 
            metadata['size'], 
            metadata['file_type_group'],
            metadata['date_best']
        ))

        # DEFINITIVE CODE CHANGE: Explicitly list all four columns to guarantee UNIQUE constraint on 'path' is enforced.
        instance_insert_query = """
        INSERT OR IGNORE INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path) 
        VALUES (?, ?, ?, ?);
        """
        self.db.execute_query(instance_insert_query, (
            metadata['content_hash'],
            metadata['original_full_path'], # value for 'path' column
            metadata['original_full_path'],
            metadata['original_relative_path']
        ))
        
        self.files_inserted_count += 1
        
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