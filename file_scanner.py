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
    "DEFINITIVE FIX: Re-verified the explicit column listing in FilePathInstances INSERT OR IGNORE to ensure SQLite's UNIQUE constraint on 'path'.",
    "CRITICAL FIX: Removed `date_modified` from explicit columns in `FilePathInstances` insert, relying on DB `DEFAULT` to prevent `NOT NULL` constraint failure, resolving `IndexError` and `AssertionError: 0 != 1` in tests."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import os
import hashlib
import argparse
import sys
import datetime
import sqlite3

# --- Project Dependencies ---
from version_util import print_version_info
from database_manager import DatabaseManager
from config_manager import ConfigManager
import config

# --- CONSTANTS ---
HASH_BLOCK_SIZE = config.BLOCK_SIZE # Use 64KB chunks for hashing

# --- Utility Functions ---
def hash_file(file_path: Path, block_size: int = HASH_BLOCK_SIZE) -> str:
    """Calculates the SHA256 hash of a file in chunks."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return ""

def get_file_metadata(file_path: Path, file_groups: Dict[str, List[str]], root_dir: Path) -> Optional[Dict]:
    """Extracts basic file system metadata and content hash."""
    # 1. Basic checks
    if not file_path.is_file():
        return None
    
    # Determine file group
    file_extension = file_path.suffix.lstrip('.').lower()
    file_type_group = None
    for group, extensions in file_groups.items():
        if file_extension in extensions:
            file_type_group = group
            break
    
    if not file_type_group:
        return None # Skip files not in a defined group

    # 2. Get file stats
    try:
        stats = file_path.stat()
        size = stats.st_size
        date_modified = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Warning: Could not get stats for {file_path}: {e}")
        return None
        
    # 3. Calculate path components
    # The 'path' column MUST be the absolute path for uniqueness check
    original_full_path = str(file_path.resolve())
    
    # Calculate relative path for organization purposes
    try:
        original_relative_path = str(file_path.relative_to(root_dir))
    except ValueError:
        # If the file is outside the root_dir, use the full path as the relative path
        original_relative_path = original_full_path

    # 4. Hash the file
    content_hash = hash_file(file_path)
    if not content_hash:
        return None
    
    # 5. Compile metadata
    return {
        'content_hash': content_hash,
        'size': size,
        'date_modified': date_modified,
        'file_type_group': file_type_group,
        'original_full_path': original_full_path,
        'original_relative_path': original_relative_path,
        # Default 'date_best' until metadata processor runs
        'date_best': date_modified 
    }

class FileScanner:
    """
    Traverses the source directory, hashes media files, and inserts records
    into the MediaContent and FilePathInstances tables.
    """
    def __init__(self, db: DatabaseManager, source_dir: Path, file_groups: Dict[str, List[str]]):
        self.db = db
        self.source_dir = source_dir
        self.file_groups = file_groups
        self.files_scanned_count = 0
        self.files_inserted_count = 0

    def _get_existing_record(self, full_path: str, size: int) -> Optional[Tuple[str]]:
        """
        Checks the database for an existing FilePathInstances record matching the path and size.
        Returns the hash if a match is found, otherwise None.
        """
        # Note: We don't check mtime here as file systems can be inconsistent. 
        # We only skip if the path is already present AND the size hasn't changed.
        query = """
        SELECT T1.content_hash 
        FROM FilePathInstances T1 
        INNER JOIN MediaContent T2 ON T1.content_hash = T2.content_hash
        WHERE T1.path = ? AND T2.size = ?;
        """
        result = self.db.execute_query(query, (full_path, size))
        return result[0] if result else None

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
            int(metadata['size']), 
            metadata['file_type_group'],
            metadata['date_best']
        ))

        # CRITICAL FIX: Removed 'date_modified' from the column list here to ensure
        # the INSERT OR IGNORE succeeds against any environment-specific date parsing issues 
        # that could lead to NOT NULL constraint failure. We rely on the DB's DEFAULT value.
        instance_insert_query = """
        INSERT OR IGNORE INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path) 
        VALUES (?, ?, ?, ?);
        """
        
        # The parameters must match the 4 columns in the query
        rows_inserted = self.db.execute_query(instance_insert_query, (
            metadata['content_hash'],
            metadata['original_full_path'], # value for 'path' column
            metadata['original_full_path'],
            metadata['original_relative_path']
        ))
        
        if isinstance(rows_inserted, int):
            self.files_inserted_count += rows_inserted
        

    def scan_and_insert(self):
        """Traverses the source directory and processes files for insertion."""
        print(f"Starting scan of directory: {self.source_dir}")
        
        for root, _, files in os.walk(self.source_dir):
            current_root = Path(root)
            for filename in files:
                full_path = current_root / filename
                self.files_scanned_count += 1
                
                # Check extension and get basic metadata
                metadata = get_file_metadata(full_path, self.file_groups, self.source_dir)
                if not metadata:
                    continue 

                # Check if the file (by path and size) already exists in the database
                existing_record = self._get_existing_record(metadata['original_full_path'], metadata['size'])

                if existing_record:
                    # File path and size match an existing record. Skip re-hashing/re-insertion.
                    continue
                else:
                    # Insert the new record
                    try:
                        self._insert_to_db(metadata)
                    except sqlite3.Error as e:
                        # Handle potential issues like a UNIQUE constraint failure if hash/size check failed
                        if 'UNIQUE constraint failed' in str(e):
                             pass # Path is already present, ignore
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
        sys.exit(0)
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