# ==============================================================================
# File: file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 7
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
    "UX: Added TQDM progress bar for real-time scanning feedback.",
    "REVERT: Removed nested byte-level progress bar as per user request.",
    "PERFORMANCE: Implemented RAM Cache for _check_if_known_and_unchanged to enable Fast Resume.",
    "UX: Re-implemented Nested Byte-Level Progress Bar for large file visibility.",
    "PERFORMANCE: Implemented Multithreaded Hashing using ThreadPoolExecutor (producer-consumer model).",
    "UX: Implemented Position Pool to allow multiple progress bars (one per thread) simultaneously."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.7.17
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, List, Tuple, Set
import os
import hashlib
import datetime
import argparse
import sys
import sqlite3
import concurrent.futures
import queue
import threading
from tqdm import tqdm

from database_manager import DatabaseManager
from config_manager import ConfigManager
from version_util import print_version_info
import config 

DEFAULT_FILE_GROUPS: Dict[str, List[str]] = {
    'IMAGE': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
    'VIDEO': ['.mp4', '.mov', '.avi', '.mkv', '.wmv'],
    'DOCUMENT': ['.pdf', '.doc', '.docx', '.txt'],
    'OTHER': []
}

class FileScanner:
    """
    Traverses a source directory, generates SHA256 hashes for media content,
    and inserts records into the database.
    Uses Multithreading with visual feedback for each thread.
    """
    def __init__(self, db: DatabaseManager, source_dir: Path, file_groups: Dict[str, List[str]]):
        self.db = db
        self.source_dir = source_dir
        self.file_groups = file_groups
        self.files_scanned_count = 0
        self.files_inserted_count = 0
        self.known_files_cache: Dict[str, Tuple[str, int]] = {} 
        
        # Position Management for Multithreaded UI
        self.max_workers = config.HASHING_THREADS
        self.position_pool = queue.Queue()
        # Fill pool with positions 1..max_workers (0 is reserved for main bar)
        for i in range(1, self.max_workers + 1):
            self.position_pool.put(i)

    def _get_file_type_group(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        for group, extensions in self.file_groups.items():
            if ext in extensions:
                return group
        return 'OTHER'

    def _load_cache(self):
        """Pre-loads existing file paths from DB into memory."""
        print("Loading existing file index for fast resume...")
        query = "SELECT fpi.path, fpi.date_modified, mc.size FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash"
        try:
            rows = self.db.execute_query(query)
            for path, date_mod, size in rows:
                self.known_files_cache[path] = (date_mod, size)
            print(f"Index loaded: {len(self.known_files_cache)} files known.")
        except sqlite3.Error:
            print("Cache load failed (likely empty DB).")

    def _calculate_sha256_worker(self, args):
        """
        Worker function to hash a file.
        Acquires a UI slot (position) to draw its own progress bar.
        """
        file_path, file_size = args
        hasher = hashlib.sha256()
        
        # Acquire a visual slot (Block until one is available, though thread pool limits active count anyway)
        position = self.position_pool.get()
        
        try:
            with tqdm(
                total=file_size, 
                unit='B', 
                unit_scale=True, 
                unit_divisor=1024, 
                desc=f"T{position}: {file_path.name[:15]}", 
                position=position, 
                leave=False # Clear bar when done to reuse slot cleanly
            ) as pbar:
                with open(file_path, 'rb') as f:
                    while chunk := f.read(config.BLOCK_SIZE):
                        hasher.update(chunk)
                        pbar.update(len(chunk))
            return hasher.hexdigest()
            
        except Exception as e:
            # Move cursor to bottom to print error safely
            # tqdm.write(f"Error reading file {file_path}: {e}") 
            return None
        finally:
            # Return the slot to the pool
            self.position_pool.put(position)

    def _check_if_known_and_unchanged(self, file_path: Path, file_stat: os.stat_result) -> bool:
        path_str = str(file_path)
        if path_str not in self.known_files_cache:
            return False
        cached_date, cached_size = self.known_files_cache[path_str]
        current_date = datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return cached_size == file_stat.st_size and cached_date == current_date

    def scan_and_insert(self):
        print(f"\nStarting scan of directory: {self.source_dir}")
        self._load_cache()
        self.files_scanned_count = 0
        self.files_inserted_count = 0
        
        if not self.source_dir.is_dir():
            print(f"Error: Source directory not found: {self.source_dir}")
            return

        print("Analyzing directory structure...")
        files_to_process = []
        
        # 1. Walk and Filter (Main Thread)
        for root, _, files in os.walk(self.source_dir):
            root_path = Path(root)
            for file_name in files:
                full_path = root_path / file_name
                
                # Check eligibility
                file_type_group = self._get_file_type_group(full_path)
                if file_type_group == 'OTHER' and not full_path.suffix == '':
                    continue 
                
                try:
                    file_stat = full_path.stat()
                except Exception:
                    continue

                self.files_scanned_count += 1
                
                # Fast Skip
                if self._check_if_known_and_unchanged(full_path, file_stat):
                    continue
                
                # Tuple: (Path, Stat, Group)
                files_to_process.append((full_path, file_stat, file_type_group))

        print(f"Files requiring hashing: {len(files_to_process)}")
        
        if not files_to_process:
            print("No new files to process.")
            return

        # 2. Multithreaded Hashing
        print(f"Spinning up {self.max_workers} threads for hashing...")
        print("NOTE: If system becomes sluggish, reduce HASHING_THREADS in config.py")
        print("\n" * (self.max_workers + 1)) # Clear space for the bars

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            # We map future -> original data so we know what file it was
            future_to_file = {
                executor.submit(self._calculate_sha256_worker, (f_path, f_stat.st_size)): (f_path, f_stat, f_group) 
                for f_path, f_stat, f_group in files_to_process
            }
            
            # Position 0 is for the Overall Progress
            with tqdm(total=len(files_to_process), desc="Total Progress", position=0) as pbar_main:
                for future in concurrent.futures.as_completed(future_to_file):
                    f_path, f_stat, f_group = future_to_file[future]
                    pbar_main.update(1)
                    
                    try:
                        content_hash = future.result()
                    except Exception as e:
                        continue
                        
                    if not content_hash:
                        continue

                    # 3. Database Write (Sequential, Main Thread)
                    # We do this here to avoid DB locking issues with threads
                    full_path_str = str(f_path)
                    relative_path_str = str(f_path.relative_to(self.source_dir))
                    date_modified_str = datetime.datetime.fromtimestamp(f_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    self.db.execute_query(
                        "INSERT OR IGNORE INTO MediaContent (content_hash, size, file_type_group, date_best) VALUES (?, ?, ?, ?)", 
                        (content_hash, f_stat.st_size, f_group, date_modified_str)
                    )

                    try:
                        res = self.db.execute_query(
                            "INSERT OR IGNORE INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_modified, is_primary) VALUES (?, ?, ?, ?, ?, ?)",
                            (content_hash, full_path_str, full_path_str, relative_path_str, date_modified_str, 0)
                        )
                        if isinstance(res, int) and res > 0:
                            self.files_inserted_count += 1
                            # Update RAM cache immediately
                            self.known_files_cache[full_path_str] = (date_modified_str, f_stat.st_size)
                    except sqlite3.Error:
                        pass

        print(f"\nScan complete. Total files scanned: {self.files_scanned_count}, new recorded: {self.files_inserted_count}")

if __name__ == "__main__":
    manager = ConfigManager()
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--scan', action='store_true')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "File Scanner")
        sys.exit(0)
    elif args.scan:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db: 
            scanner = FileScanner(db, manager.SOURCE_DIR, manager.FILE_GROUPS)
            scanner.scan_and_insert()