# ==============================================================================
# File: test_metadata_processor.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial implementation of MetadataProcessor unit tests.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import argparse
import hashlib

from database_manager import DatabaseManager
from file_scanner import FileScanner 
from metadata_processor import MetadataProcessor 
from version_util import print_version_info
from config_manager import ConfigManager 

# --- Constants & Setup ---
TEST_OUTPUT_DIR = Path('./test_output_metadata')
TEST_SOURCE_DIR = TEST_OUTPUT_DIR / 'source_media'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_metadata_db.sqlite'
# Content hashes for predictable testing
IMAGE_HASH = hashlib.sha256(b"image_content_1").hexdigest()
VIDEO_HASH = hashlib.sha256(b"video_content_2").hexdigest()

class TestMetadataProcessor(unittest.TestCase):
    """Tests the functionality of the MetadataProcessor class."""

    @classmethod
    def setUpClass(cls):
        shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)
        TEST_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create dummy files for FileScanner to insert, simulating different types
        cls.image_path = TEST_SOURCE_DIR / "photo.jpg"
        with open(cls.image_path, 'wb') as f:
            f.write(b"image_content_1") # Should yield IMAGE_HASH
            
        cls.video_path = TEST_SOURCE_DIR / "movie.mp4"
        with open(cls.video_path, 'wb') as f:
            f.write(b"video_content_2") # Should yield VIDEO_HASH

        # 1. Initialize the database and run the scanner to populate initial data
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
        
        cls.config_manager = ConfigManager()
        
        # NOTE: We need to use the actual file groups from the config manager 
        # for the scanner to correctly categorize the files as IMAGE/VIDEO
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, TEST_SOURCE_DIR, cls.config_manager.FILE_GROUPS)
            scanner.scan_and_insert()
        
    def setUp(self):
        # We don't clear the tables here; we need the data inserted by setUpClass.
        # We only need to reset the metadata fields for testing updates.
        update_query = """
        UPDATE MediaContent SET width = NULL, height = NULL, date_best = NULL, duration = NULL, bitrate = NULL, title = NULL;
        """
        with DatabaseManager(TEST_DB_PATH) as db:
            db.execute_query(update_query)

    def test_01_image_metadata_extraction_and_update(self):
        """Tests that image records are updated with dimensions and date stub."""
        with DatabaseManager(TEST_DB_PATH) as db:
            processor = MetadataProcessor(db, self.config_manager)
            processor.process_metadata()
            
            # Query the updated record
            query = "SELECT width, height, date_best FROM MediaContent WHERE content_hash = ?;"
            result = db.execute_query(query, (IMAGE_HASH,))[0]
            
            # Check results based on the IMAGE stub function in metadata_processor.py
            self.assertEqual(result[0], 1920) # width
            self.assertEqual(result[1], 1080) # height
            self.assertIn("2010-01-01", result[2]) # date_best

    def test_02_video_metadata_extraction_and_update(self):
        """Tests that video records are updated with dimensions, duration, and date stub."""
        with DatabaseManager(TEST_DB_PATH) as db:
            processor = MetadataProcessor(db, self.config_manager)
            processor.process_metadata()
            
            # Query the updated record
            query = "SELECT width, height, duration, bitrate, date_best FROM MediaContent WHERE content_hash = ?;"
            result = db.execute_query(query, (VIDEO_HASH,))[0]
            
            # Check results based on the VIDEO stub function in metadata_processor.py
            self.assertEqual(result[0], 1280) # width
            self.assertEqual(result[1], 720)  # height
            self.assertEqual(result[2], 15.5) # duration (REAL type check)
            self.assertEqual(result[3], 2500) # bitrate
            self.assertIn("2015-06-15", result[4]) # date_best

    def test_03_already_processed_files_are_skipped(self):
        """Tests that the processor skips files where rich metadata is already set."""
        with DatabaseManager(TEST_DB_PATH) as db:
            # Manually set a file as 'processed'
            db.execute_query("UPDATE MediaContent SET width = 100 WHERE content_hash = ?;", (IMAGE_HASH,))
            
            processor = MetadataProcessor(db, self.config_manager)
            processor.process_metadata()
            
            # Only the video hash should have been processed and updated, but the image was skipped.
            # Total records processed should be 1 (the video)
            self.assertEqual(processor.processed_count, 1)
            # Total records skipped that were found initially (the image, skipped by WHERE clause)
            self.assertEqual(processor.skip_count, 0) # Skipped count should be 0 because the SQL query excludes it

            # Query the width of the skipped image file (should remain 100, not 1920)
            skipped_width = db.execute_query("SELECT width FROM MediaContent WHERE content_hash = ?;", (IMAGE_HASH,))[0][0]
            self.assertEqual(skipped_width, 100) # Confirms it was not processed/overwritten

    @classmethod
    def tearDownClass(cls):
        # Clean up the test environment
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unit tests for MetadataProcessor.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Metadata Processor Unit Tests")
    else:
        unittest.main()