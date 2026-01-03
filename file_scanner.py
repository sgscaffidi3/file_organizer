# ==============================================================================
# File: file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation of high-performance file hashing and scanning logic (F01).",
    "Implemented incremental hashing using SHA256 (N01).",
    "Refactored scan logic to query file stats (size, modified date) before hashing, allowing fast skip of unchanged files (F02).",
    "Added support for configurable file groups (IMAGE, VIDEO, etc.) from ConfigManager.",
    "Implemented the insertion of MediaContent and FilePathInstances records.",
    "Refined path normalization to ensure absolute paths for database storage.",
    "Optimized file skipping for files already present in the database with matching size/mtime.",
    "FIX: The final path insertion uses the full path for the `path` column, explicitly ensuring correct behavior.",
    "CRITICAL FIX: Explicitly listed all column names in the FilePathInstances INSERT OR IGNORE statement to ensure SQLite correctly enforces the UNIQUE constraint on the 'path' column.",
    "DEFINITIVE FIX: Re-verified the explicit column listing in FilePathInstances INSERT OR IGNORE to ensure SQLite's UNIQUE constraint on 'path' is enforced.",
    "CRITICAL TEST FIX: Modified the insertion logic in `scan_and_insert` to ensure `self.files_inserted_count` is incremented accurately.",
    "UX: Added TQDM progress bar for real-time scanning feedback."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.12
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple
import os
import hashlib
import datetime
import argparse
import sys
import sqlite3
from tqdm import tqdm

from database_manager import DatabaseManager
from config_manager import ConfigManager
from version_util import print_version_info
import config 

# Define file type groups based on common extensions (ConfigManager manages this, but define a fallback)
DEFAULT_FILE_GROUPS: Dict[str, List[str]] = {
    'IMAGE': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
    'VIDEO': ['.mp4', '.mov', '.avi', '.mkv', '.wmv'],
    'DOCUMENT': ['.pdf', '.doc', '.docx', '.txt'],
    'OTHER': []
}

class FileScanner:
    """
    Traverses a source directory, generates SHA256 hashes for media content,
    and inserts records into the database while skipping duplicates.
    """
    def __init__(self, db: DatabaseManager, source_dir: Path, file_groups: Dict[str, List[str]]):
        self.db = db
        self.source_dir = source_dir
        self.file_groups = file_groups
        self.files_scanned_count = 0
        self.files_inserted_count = 0

    def _get_file_type_group(self, file_path: Path) -> str:
        """Determines the file group (e.g., IMAGE, VIDEO) based on the extension."""
        ext = file_path.suffix.lower()
        for group, extensions in self.file_groups.items():
            if ext in extensions:
                return group
        return 'OTHER'

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculates the SHA256 hash incrementally."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(config.BLOCK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ''
            
    def _check_if_known_and_unchanged(self, file_path: Path, file_stat: os.stat_result) -> bool:
        """
        Checks if a file with the same path, size, and modification time 
        already exists in FilePathInstances.
        """
        date_modified_str = datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        query = """
        SELECT COUNT(*) FROM FilePathInstances
        WHERE path = ? AND date_modified = ? AND file_id IN (
            SELECT file_id FROM FilePathInstances
            INNER JOIN MediaContent ON FilePathInstances.content_hash = MediaContent.content_hash
            WHERE MediaContent.size = ?
        );
        """
        result = self.db.execute_query(query, (str(file_path), date_modified_str, file_stat.st_size))
        
        if result and result[0][0] > 0:
            return True
        return False

    def scan_and_insert(self):
        """Traverses the source directory and inserts file data into the database."""
        
        print(f"\nStarting scan of directory: {self.source_dir}")
        self.files_scanned_count = 0
        self.files_inserted_count = 0
        
        if not self.source_dir.is_dir():
            print(f"Error: Source directory not found or is not a directory: {self.source_dir}")
            return

        # 1. Pre-count files for Progress Bar (UX)
        print("Analyzing directory structure (counting files)...")
        total_files = sum([len(files) for r, d, files in os.walk(self.source_dir)])
        
        # 2. Walk and Process
        with tqdm(total=total_files, unit="file", desc="Scanning") as pbar:
            for root, _, files in os.walk(self.source_dir):
                root_path = Path(root)
                for file_name in files:
                    pbar.update(1)
                    
                    full_path = root_path / file_name
                    
                    # Check file eligibility
                    file_type_group = self._get_file_type_group(full_path)
                    if file_type_group == 'OTHER' and not full_path.suffix == '':
                        continue 

                    self.files_scanned_count += 1
                    
                    try:
                        file_stat = full_path.stat()
                    except Exception as e:
                        # tqdm.write ensures the progress bar doesn't break visually
                        tqdm.write(f"Warning: Could not get stats for file {full_path}: {e}")
                        continue

                    # Quick skip check
                    if self._check_if_known_and_unchanged(full_path, file_stat):
                        continue

                    # --- HASHING ---
                    pbar.set_description(f"Hashing: {file_name[:20]}") # Update UI
                    content_hash = self._calculate_sha256(full_path)
                    if not content_hash:
                        continue 

                    # --- INSERTION PREP ---
                    full_path_str = str(full_path)
                    relative_path_str = str(full_path.relative_to(self.source_dir))
                    date_modified_str = datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    # 1. Insert/Ignore into MediaContent
                    media_content_query = """
                        INSERT OR IGNORE INTO MediaContent (content_hash, size, file_type_group, date_best)
                        VALUES (?, ?, ?, ?);
                    """
                    self.db.execute_query(media_content_query, (content_hash, file_stat.st_size, file_type_group, date_modified_str))

                    # 2. Insert/Ignore into FilePathInstances
                    instance_query = """
                        INSERT OR IGNORE INTO FilePathInstances 
                        (content_hash, path, original_full_path, original_relative_path, date_modified, is_primary) 
                        VALUES (?, ?, ?, ?, ?, ?);
                    """
                    try:
                        instance_rows_inserted = self.db.execute_query(instance_query, (
                            content_hash, full_path_str, full_path_str, relative_path_str, date_modified_str, 0
                        ))
                        if isinstance(instance_rows_inserted, int) and instance_rows_inserted > 0:
                            self.files_inserted_count += 1
                    except sqlite3.Error as e:
                        if 'UNIQUE constraint failed' not in str(e):
                             tqdm.write(f"Database insertion failed for {full_path}: {e}")
                
                # Reset description after loop
                pbar.set_description("Scanning")

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
            with DatabaseManager(db_path) as db: 
                scanner = FileScanner(db, manager.SOURCE_DIR, manager.FILE_GROUPS)
                scanner.scan_and_insert()
        except Exception as e:
            print(f"FATAL ERROR during scan process: {e}")
    else:
        parser.print_help()