# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 2. CRITICAL FIX: Removed manual database connection close/reopen logic, relying on the caller's DatabaseManager context.
# 1. Initial implementation of MetadataProcessor class and its update logic (F04).
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import argparse
import datetime
import sqlite3

# --- External Dependencies Placeholder ---
# NOTE: Libraries like PIL/Pillow for EXIF and moviepy/mutagen for video/audio 
# metadata would be imported here after defining them in requirements.txt.
# For now, we stub out the extraction functions.

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

# ==============================================================================
# STUB FUNCTIONS FOR METADATA EXTRACTION
# These will be replaced by actual library calls (e.g., from Pillow, moviepy, etc.)

def _extract_image_metadata(file_path: Path, group: str) -> Dict[str, Any]:
    """Stub: Extracts image dimensions and EXIF date."""
    # Placeholder date: 2010-01-01 if no EXIF found
    date_str = "2010-01-01 12:00:00"
    return {
        'width': 1920,
        'height': 1080,
        'date_extracted': date_str,
    }

def _extract_video_metadata(file_path: Path, group: str) -> Dict[str, Any]:
    """Stub: Extracts video duration, dimensions, and creation date."""
    # Placeholder date: 2015-06-15 
    date_str = "2015-06-15 15:30:00"
    return {
        'width': 1280,
        'height': 720,
        'duration': 15.5,
        'bitrate': 2500,
        'date_extracted': date_str,
    }

def _extract_document_metadata(file_path: Path, group: str) -> Dict[str, Any]:
    """Stub: Extracts document title and modification date."""
    # Placeholder date: 2020-03-20
    date_str = "2020-03-20 09:00:00"
    return {
        'title': f"Document Title {file_path.stem}",
        'date_extracted': date_str,
    }

# ==============================================================================

class MetadataProcessor:
    """
    Queries unique file content and extracts rich metadata (EXIF, duration, dimensions)
    to populate the MediaContent table (F04).
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0
        
        # Mapping file groups to the appropriate extraction function stub
        self.extractors = {
            'IMAGE': _extract_image_metadata,
            'VIDEO': _extract_video_metadata,
            'AUDIO': _extract_video_metadata, # Audio uses similar libs to video (e.g., mutagen)
            'DOCUMENT': _extract_document_metadata,
            'OTHER': lambda p, g: {}
        }


    def _find_best_instance_path(self, content_hash: str) -> Optional[Path]:
        """
        Finds the path of one instance of the file to read its metadata.
        We simply take the first path found.
        """
        query = "SELECT original_full_path FROM FilePathInstances WHERE content_hash = ? LIMIT 1;"
        result = self.db.execute_query(query, (content_hash,))
        
        if result and result[0]:
            return Path(result[0][0])
        return None

    def _update_media_content(self, content_hash: str, metadata: Dict[str, Any]):
        """Updates the MediaContent row with the extracted data."""

        # Combine size, group, and the best date from the original scan (date_best)
        # with the newly extracted metadata, preferring the extracted date.
        
        # NOTE: In a real implementation, 'date_extracted' would be rigorously 
        # compared against 'date_best' (which is currently just file mtime) 
        # to select the true chronological date. For the stub, we just use the extracted date.
        
        update_query = """
        UPDATE MediaContent SET
            date_best = ?,
            width = ?,
            height = ?,
            duration = ?,
            bitrate = ?,
            title = ?
        WHERE content_hash = ? AND (width IS NULL OR width = 0); 
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
        
        # We assume the content_hash already exists due to the FileScanner run
        self.db.execute_query(update_query, params)
        self.processed_count += 1


    def process_metadata(self):
        """Main method to iterate through all unique content and extract metadata."""
        
        # Query for all unique files (content_hash) that are missing metadata (width is NULL or 0)
        select_query = "SELECT content_hash, file_type_group FROM MediaContent WHERE width IS NULL OR width = 0;"
        
        # The DatabaseManager from the caller's context should be active here.
        
        try:
            items_to_process = self.db.execute_query(select_query)
        except sqlite3.OperationalError as e:
            print(f"Error querying database (Schema missing?): {e}")
            return

        print(f"Found {len(items_to_process)} unique files missing rich metadata.")
        
        for content_hash, file_type_group in items_to_process:
            file_path = self._find_best_instance_path(content_hash)
            
            if not file_path or not file_path.exists():
                self.skip_count += 1
                print(f"  Skipping hash {content_hash[:8]}...: Instance path not found.")
                continue

            extractor = self.extractors.get(file_type_group)
            
            if extractor:
                try:
                    metadata = extractor(file_path, file_type_group)
                    self._update_media_content(content_hash, metadata)
                except Exception as e:
                    print(f"  Error extracting metadata for {file_path}: {e}")
                    self.skip_count += 1
            else:
                self.skip_count += 1
                
        # Commit all updates after the loop finishes
        self.db.conn.commit()
        print(f"Metadata processing complete. Updated {self.processed_count} records, skipped {self.skip_count} records.")

if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Metadata Processor Module for file_organizer: Extracts EXIF/media details from files.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--process', action='store_true', help="Run metadata extraction on all records missing rich metadata.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Metadata Processor")
    elif args.process:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Please run database_manager.py --init and file_scanner.py --scan first.")
        else:
            try:
                # Use a dummy context manager just to ensure the DatabaseManager is instantiated
                with DatabaseManager(db_path) as db:
                    processor = MetadataProcessor(db, manager)
                    processor.process_metadata()
            except Exception as e:
                print(f"FATAL ERROR during metadata processing: {e}")
    else:
        parser.print_help()