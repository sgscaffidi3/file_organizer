# ==============================================================================
# File: migrator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 8
_CHANGELOG_ENTRIES = [
    "Initial implementation of Migrator class, handling file copy operations (F07) and adhering to DRY_RUN_MODE (N03).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "UX: Added TQDM progress bar for migration feedback.",
    "PERFORMANCE: Replaced N+1 query loop with a single SQL JOIN to instantly load migration jobs.",
    "FEATURE: Implemented 'Clean Database Export'. Creates a new SQLite DB reflecting the organized structure.",
    "LOGIC: Added automatic 'clean_index.sqlite' generation during Live Run.",
    "FEATURE: Inject 'Original_Filename' and 'Source_Copies' list into extended_metadata for Clean DB export.",
    "BUG FIX: Fixed path concatenation logic to prevent double-nesting of output directory (e.g. output/output/2020).",
    "UX: Cleaned up relative paths in exported DB so Tree View starts at the Year."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.8.10
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple, Dict
import os
import shutil
import argparse
import sqlite3
import json
from collections import defaultdict
from tqdm import tqdm

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class Migrator:
    """
    Manages the physical file migration process (F07).
    Copies the primary copy of each unique file to its final calculated destination.
    Also generates a new 'Clean' database reflecting the organized structure.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.dry_run = config.DRY_RUN_MODE
        self.files_copied = 0
        self.files_skipped = 0
        
        # New DB Path
        self.clean_db_path = self.output_dir / "clean_index.sqlite"

    def _get_migration_jobs(self) -> List[Tuple]:
        """
        Retrieves all files ready for migration.
        Returns: [(content_hash, primary_full_path, new_path_id, ...), ...]
        """
        print("Fetching migration list from database...")
        query = """
        SELECT 
            mc.content_hash, 
            fpi.original_full_path, 
            mc.new_path_id,
            mc.file_type_group,
            mc.size,
            mc.date_best,
            mc.extended_metadata,
            mc.width,
            mc.height,
            mc.duration,
            mc.bitrate
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        WHERE mc.new_path_id IS NOT NULL 
          AND fpi.is_primary = 1;
        """
        return self.db.execute_query(query)

    def _build_path_history_map(self) -> Dict[str, List[str]]:
        """
        Creates a dictionary mapping content_hash -> [list of all original paths].
        Used to preserve the history of duplicates in the clean DB.
        """
        print("Building path history map...")
        query = "SELECT content_hash, original_full_path FROM FilePathInstances"
        rows = self.db.execute_query(query)
        
        history_map = defaultdict(list)
        for h, p in rows:
            history_map[h].append(p)
        return history_map
    
    def _initialize_clean_db(self):
        """Creates the schema for the new Clean Index database."""
        if self.clean_db_path.exists():
            try:
                os.remove(self.clean_db_path)
            except PermissionError:
                print(f"WARNING: Could not overwrite {self.clean_db_path}. Is it open?")
                return None

        clean_db = DatabaseManager(str(self.clean_db_path))
        clean_db.create_schema()
        return clean_db

    def _perform_copy(self, source_path: Path, dest_path: Path):
        """Creates destination directory and copies the file."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
        self.files_copied += 1

    def run_migration(self):
        """Main method to execute the copy operations and DB export."""
        jobs = self._get_migration_jobs()
        total_jobs = len(jobs)
        
        print("-" * 60)
        print(f" MIGRATION PHASE START")
        print(f" Files to Process: {total_jobs}")
        print(f" Mode: {'DRY RUN (Simulation)' if self.dry_run else 'LIVE RUN (Real Copy)'}")
        if not self.dry_run:
            print(f" Export DB: {self.clean_db_path}")
        print("-" * 60)

        # Pre-fetch duplicates history
        path_history = {}
        if not self.dry_run:
            path_history = self._build_path_history_map()

        new_content_records = []
        new_instance_records = []
        
        clean_db_mgr = None
        if not self.dry_run:
            clean_db_mgr = self._initialize_clean_db()

        with tqdm(total=total_jobs, desc="Migrating", unit="file") as pbar:
            for job in jobs:
                pbar.update(1)
                
                (c_hash, src_str, dest_rel_str, f_group, f_size, f_date, f_meta, f_w, f_h, f_dur, f_bit) = job
                
                source_path = Path(src_str)
                
                # --- PATH LOGIC FIX ---
                # dest_rel_str (from Deduplicator) typically looks like: "organized_output/2024/01/file.jpg"
                # We need to treat it as authoritative relative to CWD.
                
                # 1. Determine Physical Destination
                # We trust that dest_rel_str includes the output_dir prefix if the Deduplicator put it there.
                final_dest_path = Path(dest_rel_str).resolve()
                
                # 2. Determine "Clean" Relative Path (For the Tree View)
                # We want the tree to start at "2024", not "organized_output"
                try:
                    # Strip the output_dir prefix for the database
                    clean_rel_path = str(final_dest_path.relative_to(self.config.OUTPUT_DIR.resolve()))
                except ValueError:
                    # Fallback if path isn't inside output dir for some reason
                    clean_rel_path = dest_rel_str

                # 1. Validation
                if not source_path.exists():
                    tqdm.write(f"SKIP: Source missing: {source_path}")
                    self.files_skipped += 1
                    continue
                
                if final_dest_path.exists():
                    # Destination collision
                    self.files_skipped += 1
                else:
                    # 2. Physical Copy
                    if self.dry_run:
                        self.files_copied += 1
                    else:
                        try:
                            self._perform_copy(source_path, final_dest_path)
                        except Exception as e:
                            tqdm.write(f"ERROR Copying {source_path.name}: {e}")
                            self.files_skipped += 1
                            continue 

                # 3. Prepare Clean DB Records (Live Only)
                if not self.dry_run:
                    try:
                        meta_dict = json.loads(f_meta) if f_meta else {}
                    except:
                        meta_dict = {}
                    
                    # INJECT HISTORY
                    meta_dict['Original_Filename'] = source_path.name
                    meta_dict['Source_Copies'] = path_history.get(c_hash, [])
                    enriched_meta_json = json.dumps(meta_dict)

                    new_content_records.append((
                        c_hash, f_size, f_group, f_date, f_w, f_h, f_dur, f_bit, enriched_meta_json, str(final_dest_path)
                    ))
                    
                    new_instance_records.append((
                        c_hash, 
                        str(final_dest_path),       # path
                        str(final_dest_path),       # original_full_path
                        clean_rel_path,             # original_relative_path (Now clean: 2024/01/img.jpg)
                        1                           # is_primary
                    ))

        # 4. Commit to Clean DB
        if not self.dry_run and clean_db_mgr:
            print("\nGenerating Clean Index Database...")
            q_content = """
            INSERT OR IGNORE INTO MediaContent 
            (content_hash, size, file_type_group, date_best, width, height, duration, bitrate, extended_metadata, new_path_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            clean_db_mgr.execute_many(q_content, new_content_records)
            
            q_instance = """
            INSERT OR IGNORE INTO FilePathInstances
            (content_hash, path, original_full_path, original_relative_path, is_primary)
            VALUES (?, ?, ?, ?, ?)
            """
            clean_db_mgr.execute_many(q_instance, new_instance_records)
            
            clean_db_mgr.close()
            print(f"Clean Database Created: {self.clean_db_path}")

        print("-" * 60)
        print(f"Migration Finished.")
        print(f"  Copied/Verified: {self.files_copied}")
        print(f"  Skipped/Errors:  {self.files_skipped}")
        if not self.dry_run:
            print(f"\n✅ TO VIEW THE ORGANIZED COLLECTION:")
            print(f"python main.py --serve --db \"{self.clean_db_path}\"")
        print("-" * 60)


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
                import traceback
                traceback.print_exc()
    else:
        parser.print_help()