# ==============================================================================
# File: migrator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [12]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.9.12
# ------------------------------------------------------------------------------
from pathlib import Path
import sys
from typing import List, Tuple, Dict
import os
import shutil
import argparse
import sqlite3
import json
import concurrent.futures
from collections import defaultdict
from tqdm import tqdm

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class Migrator:
    """
    Manages the physical file migration process using Multithreading.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.dry_run = config.DRY_RUN_MODE
        self.files_copied = 0
        self.files_skipped = 0
        self.clean_db_path = self.output_dir / "clean_index.sqlite"

    def _get_migration_jobs(self) -> List[Tuple]:
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
        Optimized path history builder.
        """
        print("Building path history map (indexing duplicates)...")
        # Optimization: Only select what we need
        query = "SELECT content_hash, original_full_path FROM FilePathInstances"
        rows = self.db.execute_query(query)
        
        history_map = defaultdict(list)
        # Using TQDM here because this can be slow in Python for 100k+ rows
        for h, p in tqdm(rows, desc="Indexing History", unit="row"):
            history_map[h].append(p)
        return history_map
    
    def _initialize_clean_db(self):
        if self.clean_db_path.exists():
            try:
                os.remove(self.clean_db_path)
            except PermissionError:
                print(f"WARNING: Could not overwrite {self.clean_db_path}. Is it open?")
                return None

        clean_db = DatabaseManager(str(self.clean_db_path))
        clean_db.create_schema()
        return clean_db

    def _copy_worker(self, job_data):
        """
        Worker function for ThreadPool. 
        Performs validation, copy, and prepares the Clean DB record.
        """
        # Unpack
        (c_hash, src_str, dest_rel_str, f_group, f_size, f_date, f_meta, f_w, f_h, f_dur, f_bit, path_history) = job_data
        
        source_path = Path(src_str)
        
        # Path Logic
        if os.path.isabs(dest_rel_str):
            final_dest_path = Path(dest_rel_str).resolve()
        else:
            final_dest_path = self.output_dir / Path(dest_rel_str)

        try:
            clean_rel_path = str(final_dest_path.relative_to(self.config.OUTPUT_DIR.resolve()))
        except ValueError:
            clean_rel_path = dest_rel_str

        # 1. Validation
        if not source_path.exists():
            return ('SKIP', f"Source missing: {source_path}")
        
        if final_dest_path.exists():
            # If destination exists, we skip copy but RETURN the DB record 
            # so the Clean DB knows about this file (assuming it was copied previously)
            pass
        else:
            # 2. Physical Copy
            if not self.dry_run:
                try:
                    final_dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, final_dest_path)
                except Exception as e:
                    return ('ERROR', f"Copy failed {source_path.name}: {e}")

        # 3. Prepare Clean DB Record
        if self.dry_run:
            return ('COPY_DRY', None)
        
        # Enrich Metadata
        try: meta_dict = json.loads(f_meta) if f_meta else {}
        except: meta_dict = {}
        
        meta_dict['Original_Filename'] = source_path.name
        meta_dict['Source_Copies'] = path_history
        enriched_meta = json.dumps(meta_dict)

        content_record = (c_hash, f_size, f_group, f_date, f_w, f_h, f_dur, f_bit, enriched_meta, str(final_dest_path))
        instance_record = (c_hash, str(final_dest_path), str(final_dest_path), clean_rel_path, 1)
        
        return ('SUCCESS', (content_record, instance_record))

    def run_migration(self):
        jobs = self._get_migration_jobs()
        total_jobs = len(jobs)
        
        print("-" * 60)
        print(f" MIGRATION PHASE START")
        print(f" Files to Process: {total_jobs}")
        print(f" Threads: {config.MIGRATION_THREADS}")
        print(f" Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        print("-" * 60)

        path_history_map = {}
        if not self.dry_run:
            path_history_map = self._build_path_history_map()

        clean_db_mgr = None
        if not self.dry_run:
            clean_db_mgr = self._initialize_clean_db()

        # Prepare Worker Args (Pre-package the history lookup to avoid sharing the huge dict across threads if possible, 
        # though read-only shared dict is thread-safe in Python)
        worker_args = []
        for job in jobs:
            # Append the specific history list for this hash
            c_hash = job[0]
            # Create a tuple of (job..., history_list)
            args = job + (path_history_map.get(c_hash, []),)
            worker_args.append(args)

        # Buffer for batch inserts
        new_content_records = []
        new_instance_records = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.MIGRATION_THREADS) as executor:
            # Map futures
            futures = [executor.submit(self._copy_worker, arg) for arg in worker_args]
            
            with tqdm(total=total_jobs, desc="Migrating", unit="file") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    pbar.update(1)
                    try:
                        status, data = future.result()
                        
                        if status == 'SUCCESS':
                            self.files_copied += 1
                            if data:
                                new_content_records.append(data[0])
                                new_instance_records.append(data[1])
                        elif status == 'COPY_DRY':
                            self.files_copied += 1
                        elif status == 'SKIP':
                            self.files_skipped += 1
                        elif status == 'ERROR':
                            self.files_skipped += 1
                            tqdm.write(str(data))
                            
                    except Exception as e:
                        tqdm.write(f"Thread Error: {e}")
                        self.files_skipped += 1

        # 4. Commit to Clean DB (Bulk)
        if not self.dry_run and clean_db_mgr:
            print("\nGenerating Clean Index Database...")
            clean_db_mgr.execute_many(
                "INSERT OR IGNORE INTO MediaContent (content_hash, size, file_type_group, date_best, width, height, duration, bitrate, extended_metadata, new_path_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                new_content_records
            )
            clean_db_mgr.execute_many(
                "INSERT OR IGNORE INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, is_primary) VALUES (?, ?, ?, ?, ?)",
                new_instance_records
            )
            clean_db_mgr.close()
            print(f"Clean Database Created: {self.clean_db_path}")

        print("-" * 60)
        print(f"Migration Finished. Copied: {self.files_copied}, Skipped: {self.files_skipped}")
        if not self.dry_run:
            print(f"python main.py --serve --db \"{self.clean_db_path}\"")
        print("-" * 60)


if __name__ == "__main__":
    manager = ConfigManager()
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--migrate', action='store_true')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        print_version_info(__file__, "File Migration Handler")
        sys.exit(0)
    elif args.migrate:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db:
            migrator = Migrator(db, manager)
            migrator.run_migration()