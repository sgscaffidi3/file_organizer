# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 20
# Version: 0.3.20
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class (F04).",
    "PRODUCTION UPGRADE: Integrated Pillow for real EXIF 'DateTimeOriginal' extraction.",
    "PRODUCTION UPGRADE: Integrated Hachoir for real video stream parsing.",
    "CRITICAL FIX: Restored sys/argparse imports to __main__ block for import stability.",
    "CRITICAL FIX: Restored accurate processed_count tracking via database rowcount.",
    "RELIABILITY: Added safety handling for missing physical files and corrupt streams."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import os
import datetime
import sqlite3

# --- Extraction Libraries ---
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    from hachoir.core import config as hachoir_config
    hachoir_config.quiet = True
except ImportError:
    pass

# --- Project Dependencies ---
from database_manager import DatabaseManager
from config_manager import ConfigManager
from asset_manager import AssetManager

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts real EXIF and dimension data using Pillow."""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            exif_data = img._getexif()
            date_extracted = None
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "DateTimeOriginal":
                        # Standardize EXIF '2023:10:01' to ISO '2023-10-01'
                        date_extracted = value.replace(':', '-', 2)
                        break
            return {
                'date_extracted': date_extracted,
                'width': width,
                'height': height,
                'duration': None,
                'bitrate': None,
                'title': file_path.name
            }
    except Exception:
        return {}

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts stream metadata using Hachoir."""
    try:
        parser = createParser(str(file_path))
        if not parser: return {}
        with parser:
            metadata = extractMetadata(parser)
            if not metadata: return {}
            return {
                'date_extracted': str(metadata.get('creation_date')) if metadata.has('creation_date') else None,
                'width': metadata.get('width') if metadata.has('width') else None,
                'height': metadata.get('height') if metadata.has('height') else None,
                'duration': metadata.get('duration').total_seconds() if metadata.has('duration') else None,
                'bitrate': metadata.get('bitrate') if metadata.has('bitrate') else None,
                'title': metadata.get('title') if metadata.has('title') else file_path.name
            }
    except Exception:
        return {}

class MetadataProcessor:
    """Processes MediaContent records missing metadata by reading physical files."""
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0
        self.extractors = {'IMAGE': extract_image_metadata, 'VIDEO': extract_video_metadata}

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.original_full_path
        FROM MediaContent T1
        INNER JOIN FilePathInstances T2 ON T1.content_hash = T2.content_hash AND T2.is_primary = 1
        WHERE (T1.width IS NULL OR T1.height IS NULL)
        """
        results = self.db.execute_query(query)
        return results if results else []

    def _update_media_content(self, content_hash: str, metadata: Dict[str, Any]):
        update_query = """
        UPDATE MediaContent SET
            date_best = COALESCE(?, date_best),
            width = ?, height = ?, duration = ?, bitrate = ?, title = ?
        WHERE content_hash = ?;
        """
        params = (
            metadata.get('date_extracted'),
            metadata.get('width'),
            metadata.get('height'),
            metadata.get('duration'),
            metadata.get('bitrate'),
            metadata.get('title'),
            content_hash
        )
        rows_updated = self.db.execute_query(update_query, params) 
        if isinstance(rows_updated, int):
            self.processed_count += rows_updated

    def process_metadata(self):
        """Processes MediaContent records using the new AssetManager conductor."""
        self.processed_count = 0
        self.skip_count = 0
        records = self._get_files_to_process()
        
        # Instantiate the new Conductor
        asset_mgr = AssetManager(self.db)

        for content_hash, group, path_str in records:
            file_path = Path(path_str)
            
            if not file_path.exists():
                self.skip_count += 1
                continue

            # We now delegate EVERYTHING to the AssetManager for VIDEO group
            if group == 'VIDEO':
                try:
                    # This one line replaces extraction, cleaning, and DB updating
                    asset_mgr.process_file(file_path, content_hash)
                    self.processed_count += 1
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    self.skip_count += 1
            else:
                # Fallback for IMAGE or other groups until they get Asset models
                extractor = self.extractors.get(group)
                if extractor:
                    metadata = extractor(file_path)
                    if metadata: self._update_media_content(content_hash, metadata)
                    else: self.skip_count += 1
                else: self.skip_count += 1
                
        print(f"Metadata processing complete. Updated {self.processed_count} records.")

# --- CLI EXECUTION LOGIC ---
if __name__ == "__main__":
    import argparse
    import sys
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
        with DatabaseManager(db_path) as db:
            MetadataProcessor(db, manager).process_metadata()
    else:
        parser.print_help()