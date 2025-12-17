# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class and its update logic (F04).",
    "CRITICAL FIX: Removed manual database connection close/reopen logic, relying on the caller's DatabaseManager context.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "CRITICAL LOGIC FIX: Updated `_update_media_content` to increment `self.processed_count` using the `rowcount` from the database manager, ensuring accurate counting (Resolves `test_03_processor_skips_already_processed_records`).",
    "CRITICAL IMPORT FIX: Moved `argparse` and `sys` imports to the `if __name__ == '__main__':` block for dynamic import stability.",
    "DEFINITIVE IMPORT FIX: Moved `version_util` import to the `if __name__ == '__main__':` block to prevent circular dependency/partial import failure during version audit.",
    "CRITICAL TYPING FIX: Added `Tuple` to the `from typing` import list to resolve `NameError`."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple # <-- FIXED: Added Tuple
import os
import datetime
import sqlite3

# --- Project Dependencies ---
from database_manager import DatabaseManager
from config_manager import ConfigManager


# --- Stub/Mock Extraction Logic ---

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Stub function for image metadata extraction (e.g., EXIF)."""
    # Simulate extraction for testing
    return {
        'date_extracted': '2020-01-01 10:00:00',
        'width': 1920,
        'height': 1080,
        'duration': None,
        'bitrate': None,
        'title': 'Test Image Title'
    }

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Stub function for video metadata extraction (e.g., duration, bitrate)."""
    # Simulate extraction for testing
    return {
        'date_extracted': '2021-06-15 15:30:00',
        'width': 1280,
        'height': 720,
        'duration': 120.5,
        'bitrate': 5000000,
        'title': 'Test Video Title'
    }


class MetadataProcessor:
    """
    Scans MediaContent records that are missing rich metadata and runs extraction
    on the file system copy of the file. Updates the MediaContent record with the results.
    """
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0
        
        # Map file type groups to their respective extraction function stubs
        self.extractors = {
            'IMAGE': extract_image_metadata,
            'VIDEO': extract_video_metadata,
            # Add other groups here (e.g., 'AUDIO')
        }

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        """
        Queries the database for unique content items that are missing rich metadata.
        Rich metadata is considered missing if width OR height are NULL.
        Returns: [(content_hash, file_type_group, original_full_path)]
        """
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.path
        FROM MediaContent T1
        INNER JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash AND T2.is_primary = 1
        WHERE T1.width IS NULL OR T1.height IS NULL
        """
        # We only need the primary copy path for metadata extraction
        results = self.db.execute_query(query)
        return results if results else []

    def _update_media_content(self, content_hash: str, metadata: Dict[str, Any]):
        """Updates the MediaContent row with the extracted data."""
        
        update_query = """
        UPDATE MediaContent SET
            date_best = ?,
            width = ?,
            height = ?,
            duration = ?,
            bitrate = ?,
            title = ?
        WHERE content_hash = ?;
        """
        
        params = (
            metadata.get('date_extracted'),
            metadata.get('width', None),
            metadata.get('height', None),
            metadata.get('duration', None),
            metadata.get('bitrate', None),
            metadata.get('title', None),
            content_hash
        )
        
        # CRITICAL LOGIC FIX: Use rowcount returned from execute_query to track actual updates
        rows_updated = self.db.execute_query(update_query, params) 
        if isinstance(rows_updated, int):
            self.processed_count += rows_updated


    def process_metadata(self):
        """Main method to run the metadata extraction and update process."""
        self.processed_count = 0
        self.skip_count = 0
        
        records_to_process = self._get_files_to_process()
        print(f"Found {len(records_to_process)} unique files missing rich metadata.")
        
        for content_hash, file_type_group, path_to_file in records_to_process:
            
            file_path = Path(path_to_file)
            
            # Check if the file still exists on the file system
            if not file_path or not file_path.exists():
                self.skip_count += 1
                continue

            extractor = self.extractors.get(file_type_group)
            
            if extractor:
                try:
                    metadata = extractor(file_path)
                    if metadata:
                        self._update_media_content(content_hash, metadata)
                except Exception as e:
                    print(f"Error extracting metadata for {path_to_file}: {e}")
                    self.skip_count += 1
            else:
                # No extractor for this file group
                self.skip_count += 1
                
        # The commit happens inside DatabaseManager.execute_query for each update.
        print(f"Metadata processing complete. Updated {self.processed_count} records, skipped {self.skip_count} records.")

# --- CLI EXECUTION LOGIC ---
if __name__ == "__main__":
    # CRITICAL IMPORT FIX: Move system/cli imports to the execution block
    import sys
    import argparse
    from version_util import print_version_info # <-- MOVED HERE TO PREVENT CRASH
    
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Metadata Processor Module for file_organizer: Extracts EXIF/media details from files.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--process', action='store_true', help="Run metadata extraction on all records missing rich metadata.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Metadata Processor")
        sys.exit(0)
    elif args.process:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Please run database_manager.py --init and file_scanner.py --scan first.")
        else:
            try:
                # Use a context manager to ensure the DatabaseManager is properly handled
                with DatabaseManager(db_path) as db:
                    processor = MetadataProcessor(db, manager)
                    processor.process_metadata()
            except Exception as e:
                print(f"FATAL ERROR during metadata processing: {e}")
    else:
        parser.print_help()