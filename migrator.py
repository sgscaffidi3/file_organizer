# ==============================================================================
# File: migrator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation of Migrator class, handling file copy operations (F07) and adhering to DRY_RUN_MODE (N03).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "UX: Added TQDM progress bar for migration feedback."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.4
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import os
import shutil
import argparse
from tqdm import tqdm

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class Migrator:
    """
    Manages the physical file migration process (F07).
    Copies the primary copy of each unique file to its final calculated destination.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.dry_run = config.DRY_RUN_MODE
        self.files_copied = 0
        self.files_skipped = 0

    def _get_migration_jobs(self) -> List[Tuple[str, str, str]]:
        """Returns: [(content_hash, primary_full_path, new_path_id), ...]"""
        unique_content_query = """
        SELECT content_hash, new_path_id FROM MediaContent WHERE new_path_id IS NOT NULL;
        """
        unique_content = self.db.execute_query(unique_content_query)
        
        migration_jobs = []
        for content_hash, new_path_id in unique_content:
            instance_query = "SELECT original_full_path FROM FilePathInstances WHERE content_hash = ? AND is_primary = 1 LIMIT 1;"
            result = self.db.execute_query(instance_query, (content_hash,))
            
            # Fallback if is_primary wasn't set correctly (should be fixed by deduplicator)
            if not result:
                instance_query = "SELECT original_full_path FROM FilePathInstances WHERE content_hash = ? LIMIT 1;"
                result = self.db.execute_query(instance_query, (content_hash,))
            
            if result:
                migration_jobs.append((content_hash, result[0][0], new_path_id))
                
        return migration_jobs
    
    def _perform_copy(self, source_path: Path, dest_path: Path):
        """Creates destination directory and copies the file."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
        self.files_copied += 1

    def run_migration(self):
        """Main method to execute the copy operations."""
        jobs = self._get_migration_jobs()
        total_jobs = len(jobs)
        
        print("-" * 50)
        print(f"Migration Phase Start. Found {total_jobs} files to process.")
        print(f"DRY RUN MODE is: {'ON' if self.dry_run else 'OFF'} (N03)")
        print("-" * 50)

        with tqdm(total=total_jobs, desc="Migrating", unit="file") as pbar:
            for content_hash, primary_path_str, relative_dest_path_str in jobs:
                pbar.update(1)
                source_path = Path(primary_path_str)
                # new_path_id in DB is actually the full path string in current deduplicator logic
                # We handle both full absolute and relative just in case
                if os.path.isabs(relative_dest_path_str):
                    final_dest_path = Path(relative_dest_path_str)
                else:
                    final_dest_path = self.output_dir / Path(relative_dest_path_str)
                
                if not source_path.exists():
                    tqdm.write(f"Skipping hash {content_hash[:8]}...: Source file not found")
                    self.files_skipped += 1
                    continue
                    
                if final_dest_path.exists():
                    tqdm.write(f"Skipping hash {content_hash[:8]}...: Destination file already exists")
                    self.files_skipped += 1
                    continue

                if self.dry_run:
                    tqdm.write(f"[DRY RUN] Copy: {source_path.name} -> {final_dest_path.name}")
                    self.files_copied += 1
                else:
                    try:
                        self._perform_copy(source_path, final_dest_path)
                        # tqdm.write(f"[ LIVE ] Copied: {source_path.name}") # Optional: Reduce spam
                    except Exception as e:
                        tqdm.write(f"FATAL COPY ERROR for {source_path}: {e}")
                        self.files_skipped += 1
                    
        print("-" * 50)
        print(f"Migration finished. {'[DRY RUN]' if self.dry_run else '[LIVE RUN]'}")
        print(f"Files reported/copied: {self.files_copied}")
        print(f"Files skipped/errored: {self.files_skipped}")
        print("-" * 50)


if __name__ == "__main__":
    manager = ConfigManager()
    parser = argparse.ArgumentParser(description="Migrator Module for file_organizer.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--migrate', action='store_true', help=f"Run the file copy process.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "File Migration Handler")
    elif args.migrate:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database not found at {db_path}.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    migrator = Migrator(db, manager)
                    migrator.run_migration()
            except Exception as e:
                print(f"FATAL ERROR during migration: {e}")
    else:
        parser.print_help()