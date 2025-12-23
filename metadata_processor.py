# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class (F04).",
    "PRODUCTION UPGRADE: Integrated Pillow and Hachoir for extraction.",
    "RELIABILITY: Added safety handling for missing physical files.",
    "ARCHITECTURE REFACTOR: Migrated to Hybrid Metadata model via AssetManager.",
    "CLEANUP: Removed redundant local extractors; delegated all routing to AssetManager.",
    "FEATURE: Enabled full support for VIDEO, IMAGE, AUDIO, and DOCUMENT groups."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.6
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import sys

# --- Project Dependencies ---
from database_manager import DatabaseManager
from config_manager import ConfigManager
from asset_manager import AssetManager

class MetadataProcessor:
    """Processes MediaContent records missing metadata by delegating to AssetManager."""
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        """Finds records where core metadata (width/height) is missing."""
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.original_full_path
        FROM MediaContent T1
        INNER JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash AND T2.is_primary = 1
        WHERE (T1.width IS NULL OR T1.height IS NULL)
        """
        results = self.db.execute_query(query)
        return results if results else []

    def process_metadata(self):
        """Processes MediaContent records using the new AssetManager conductor."""
        self.processed_count = 0
        self.skip_count = 0
        records = self._get_files_to_process()
        
        # The AssetManager handles the specialized classes (Video, Image, etc.)
        asset_mgr = AssetManager(self.db)

        for content_hash, group, path_str in records:
            file_path = Path(path_str)
            
            if not file_path.exists():
                self.skip_count += 1
                continue

            try:
                # Delegate extraction, cleaning, and DB updating to the manager.
                # Passing group=group ensures the manager uses the correct Asset class.
                asset_mgr.process_file(file_path, content_hash, group=group)
                self.processed_count += 1
            except Exception as e:
                print(f"Error processing {file_path} ({group}): {e}")
                self.skip_count += 1
                
        print(f"Metadata processing complete. Updated {self.processed_count} records.")

# --- CLI EXECUTION LOGIC ---
if __name__ == "__main__":
    import argparse
    from version_util import print_version_info
    
    manager = ConfigManager()
    parser = argparse.ArgumentParser(description="Metadata Processor Module")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--process', action='store_true', help="Run metadata extraction.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Metadata Processor")
        sys.exit(0)
    elif args.process:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        # Ensure the directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with DatabaseManager(db_path) as db:
            db.create_schema()
            MetadataProcessor(db, manager).process_metadata()
    else:
        parser.print_help()