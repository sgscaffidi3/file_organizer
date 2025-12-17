# ==============================================================================
# File: metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 23
# Version: 0.3.23
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of MetadataProcessor class (F04).",
    "PRODUCTION UPGRADE: Integrated Pillow and Hachoir for real media extraction.",
    "CRITICAL FIX: Tightened SQL query WHERE clause to properly filter out processed records (Fixes Test 02).",
    "RELIABILITY: Restored explicit skip_count logic for missing and corrupt files."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import os
import sqlite3

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    from hachoir.core import config as hachoir_config
    hachoir_config.quiet = True
except ImportError:
    pass

from database_manager import DatabaseManager
from config_manager import ConfigManager

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            exif_data = img._getexif()
            date_extracted = None
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "DateTimeOriginal":
                        date_extracted = value.replace(':', '-', 2)
                        break
            return {'date_extracted': date_extracted, 'width': width, 'height': height, 'title': file_path.name}
    except Exception: return {}

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
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
    except Exception: return {}

class MetadataProcessor:
    def __init__(self, db: DatabaseManager, config_manager: ConfigManager):
        self.db = db
        self.config = config_manager
        self.processed_count = 0
        self.skip_count = 0
        self.extractors = {'IMAGE': extract_image_metadata, 'VIDEO': extract_video_metadata}

    def _get_files_to_process(self) -> List[Tuple[str, str, str]]:
        # FIXED: Added strict IS NULL checks to ensure efficiency
        query = """
        SELECT T1.content_hash, T1.file_type_group, T2.path
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
        params = (metadata.get('date_extracted'), metadata.get('width'), metadata.get('height'), 
                  metadata.get('duration'), metadata.get('bitrate'), metadata.get('title'), content_hash)
        rows_updated = self.db.execute_query(update_query, params) 
        if isinstance(rows_updated, int): self.processed_count += rows_updated

    def process_metadata(self):
        self.processed_count = 0
        self.skip_count = 0
        records = self._get_files_to_process()
        for c_hash, group, path_str in records:
            file_path = Path(path_str)
            if not file_path.exists():
                self.skip_count += 1
                continue
            extractor = self.extractors.get(group)
            if extractor:
                metadata = extractor(file_path)
                if metadata: self._update_media_content(c_hash, metadata)
                else: self.skip_count += 1
            else: self.skip_count += 1
        print(f"Updated: {self.processed_count} | Skipped: {self.skip_count}")

if __name__ == "__main__":
    import argparse, sys
    from version_util import print_version_info
    manager = ConfigManager()
    parser = argparse.ArgumentParser(description="Metadata Processor")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--process', action='store_true')
    args = parser.parse_args()
    if args.version:
        print_version_info(__file__, "Metadata Processor"); sys.exit(0)
    elif args.process:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        with DatabaseManager(db_path) as db:
            MetadataProcessor(db, manager).process_metadata()
    else: parser.print_help()