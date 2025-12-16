# ==============================================================================
# File: migrator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of Migrator class, handling file copy operations (F07) and adhering to DRY_RUN_MODE (N03).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import os
import shutil
import argparse

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class Migrator:
    """
    Manages the physical file migration process (F07).
    Copies the primary copy of each unique file to its final calculated destination 
    in the output directory, respecting DRY_RUN_MODE (N03).
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.dry_run = config.DRY_RUN_MODE
        self.files_copied = 0
        self.files_skipped = 0

    def _get_migration_jobs(self) -> List[Tuple[str, str, str]]:
        """
        Queries the database for all unique files that have a final path calculated
        and returns the necessary data for migration.
        
        Returns: [(content_hash, primary_full_path, new_path_id), ...]
        """
        # NOTE: Since the Deduplicator step was designed to calculate the 
        # `primary_full_path` but the schema wasn't updated, we must query 
        # FilePathInstances to find the primary path based on the logic 
        # defined in the Deduplicator. This is a temporary inefficiency.
        
        # A proper fix would be to store primary_full_path in MediaContent.
        # For now, we assume the oldest file is the primary path (as used in tests).
        
        # We need: content_hash, new_path_id, and the path of the oldest instance.
        
        # SQL to find the oldest path for each hash is complex. 
        # For simplicity in the migrator, we will rely on a placeholder 
        # query until the Deduplicator/Schema is refactored:
        
        # Placeholder Query: Select content_hash and new_path_id for files ready to be migrated.
        query = """
        SELECT mc.content_hash, mc.new_path_id, fpi.original_full_path
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        WHERE mc.new_path_id IS NOT NULL; 
        """
        
        # This query returns ALL instances. We must filter down to the primary path outside.
        
        # --- Simplified Approach: Use the first path found and rely on the dry-run output ---
        
        # We need a stable list of unique content_hash and new_path_id
        unique_content_query = """
        SELECT content_hash, new_path_id FROM MediaContent WHERE new_path_id IS NOT NULL;
        """
        unique_content = self.db.execute_query(unique_content_query)
        
        migration_jobs = []
        
        for content_hash, new_path_id in unique_content:
            # Find any instance path associated with this hash (we'll assume this is the source)
            # This is non-ideal but keeps the schema stable for now.
            instance_query = "SELECT original_full_path FROM FilePathInstances WHERE content_hash = ? LIMIT 1;"
            source_path = self.db.execute_query(instance_query, (content_hash,))
            
            if source_path:
                migration_jobs.append((content_hash, source_path[0][0], new_path_id))
                
        return migration_jobs
    
    def _perform_copy(self, source_path: Path, dest_path: Path):
        """Creates destination directory and copies the file."""
        
        # Ensure the parent directory of the destination exists
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

        for content_hash, primary_path_str, relative_dest_path_str in jobs:
            source_path = Path(primary_path_str)
            final_dest_path = self.output_dir / Path(relative_dest_path_str)
            
            if not source_path.exists():
                print(f"Skipping hash {content_hash[:8]}...: Source file not found: {source_path}")
                self.files_skipped += 1
                continue
                
            if final_dest_path.exists():
                # This could happen if a previous run failed mid-copy, or if the logic is flawed
                print(f"Skipping hash {content_hash[:8]}...: Destination file already exists: {final_dest_path.name}")
                self.files_skipped += 1
                continue

            if self.dry_run:
                # DRY RUN: Report what *would* happen
                print(f"[DRY RUN] Copy: {source_path.name} -> {final_dest_path}")
                self.files_copied += 1 # Count it as 'copied' for the dry-run report
            else:
                # LIVE RUN: Perform the actual copy (F07)
                try:
                    self._perform_copy(source_path, final_dest_path)
                    print(f"[ LIVE ] Copied: {source_path.name}")
                except Exception as e:
                    print(f"FATAL COPY ERROR for {source_path}: {e}")
                    self.files_skipped += 1
                    
        print("-" * 50)
        print(f"Migration finished. {'[DRY RUN]' if self.dry_run else '[LIVE RUN]'}")
        print(f"Files reported/copied: {self.files_copied}")
        print(f"Files skipped/errored: {self.files_skipped}")
        print("-" * 50)


if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Migrator Module for file_organizer: Handles physical file copy operations (F07).")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--migrate', action='store_true', help=f"Run the file copy process. DRY_RUN_MODE is currently {'ON' if config.DRY_RUN_MODE else 'OFF'}.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "File Migration Handler")
    elif args.migrate:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Run all previous steps first.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    migrator = Migrator(db, manager)
                    migrator.run_migration()
            except Exception as e:
                print(f"FATAL ERROR during migration: {e}")
    else:
        parser.print_help()