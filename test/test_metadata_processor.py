# ==============================================================================
# File: test/test_metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of test suite for MetadataProcessor.",
    "CRITICAL FIX: Updated setUp to populate all necessary columns (file_type_group, is_primary) to allow MetadataProcessor to query files correctly.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "DEFINITIVE FIX: Used real ConfigManager with temporary output directory, matching deduplicator tests. Modified setUpClass to extend MediaContent schema for metadata fields (width, height, etc.).",
    "CRITICAL IMPORT FIX: Moved `argparse` and `sys` imports to the `if __name__ == '__main__':` block to prevent dynamic import crashes during version audit.",
    "DEFINITIVE CLI FIX: Moved `version_util` import into the `if __name__ == '__main__':` block to ensure `--version` works even if core dependencies fail to import.",
    "CRITICAL PATH FIX: Explicitly added the project root to `sys.path` to resolve `ModuleNotFoundError: No module named 'version_util'` when running the test file directly."
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import sqlite3
import datetime
import time 

# --- Project Dependencies ---
try:
    # We keep the core project imports here. If they fail, the tests won't run, but 
    # the CLI version check should still work below due to the path fix.
    from database_manager import DatabaseManager
    from metadata_processor import MetadataProcessor, extract_image_metadata, extract_video_metadata
    from config_manager import ConfigManager
except ImportError as e:
    print(f"Test setup import error: {e}. Please ensure file_organizer modules are in the path or imports are adjusted.")
    # Note: We avoid sys.exit(1) here to allow version_util to continue auditing.


# --- CONSTANTS FOR TESTING ---
TEST_OUTPUT_DIR_NAME = "test_output_meta"
# Path to the test environment root (relative to where the test is run)
TEST_OUTPUT_DIR = Path(TEST_OUTPUT_DIR_NAME) 
TEST_HASH_IMAGE = "deadbeef01234567890abcdef01234567890abcdef01234567890a"
TEST_HASH_VIDEO = "video1234567890abcdef01234567890abcdef01234567890abcdef"


class TestMetadataProcessor(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup runs once for the class: creates the test environment and database schema."""
        cls.test_dir = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
        # ConfigManager now accepts output_dir override for isolation
        cls.config_manager = ConfigManager(output_dir=cls.test_dir) 
        cls.db_manager_path = str(cls.test_dir / 'metadata.sqlite')
        
        # 1. Clean up and create test environment
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Initialize Database and Schema
        with DatabaseManager(cls.db_manager_path) as db:
            db.create_schema()
            
            # Manually extend MediaContent schema to add metadata fields (if not already present)
            try:
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN width INTEGER;")
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN height INTEGER;")
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN duration REAL;")
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN bitrate INTEGER;")
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN title TEXT;")
            except sqlite3.OperationalError:
                pass # Columns already exist
            
    @classmethod
    def tearDownClass(cls):
        """Teardown runs once for the class: cleans up the test environment."""
        pass

    def setUp(self):
        """Setup runs before each test: cleans the tables and inserts test data."""
        self.db_manager = DatabaseManager(self.db_manager_path)
        self.db_manager.connect()
        
        # Clean up tables before each test
        self.db_manager.execute_query("DELETE FROM MediaContent;")
        self.db_manager.execute_query("DELETE FROM FilePathInstances;")
        
        # Instantiate Processor
        self.processor = MetadataProcessor(self.db_manager, self.config_manager)
        
        # --- INSERT TEST DATA ---
        
        # 1. Image file to be processed (width/height NULL)
        media_content_query = """
        INSERT INTO MediaContent 
        (content_hash, size, file_type_group, date_best) 
        VALUES (?, ?, ?, ?);
        """
        self.db_manager.execute_query(media_content_query, (TEST_HASH_IMAGE, 1024, 'IMAGE', "2020-01-01 10:00:00"))
        
        # 2. Video file to be processed (width/height NULL)
        self.db_manager.execute_query(media_content_query, (TEST_HASH_VIDEO, 2048, 'VIDEO', "2021-06-15 15:30:00"))

        # 3. Already processed file (to be skipped)
        TEST_HASH_SKIPPED = "skip1234567890abcdef01234567890abcdef01234567890a"
        processed_query = """
        INSERT INTO MediaContent 
        (content_hash, size, file_type_group, date_best, width, height) 
        VALUES (?, ?, ?, ?, 100, 100);
        """
        self.db_manager.execute_query(processed_query, (TEST_HASH_SKIPPED, 512, 'IMAGE', "2019-01-01 09:00:00"))

        # --- INSERT FILEPATH INSTANCES (Requires is_primary=1 for processor to find path) ---
        instance_query = """
        INSERT INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path, is_primary)
        VALUES (?, ?, ?, ?, ?);
        """
        # We use Path('/dev/null') or similar stub path as the extractor doesn't actually read the file.
        self.db_manager.execute_query(instance_query, (TEST_HASH_IMAGE, str(self.test_dir / 'image.jpg'), str(self.test_dir / 'image.jpg'), 'image.jpg', 1))
        self.db_manager.execute_query(instance_query, (TEST_HASH_VIDEO, str(self.test_dir / 'video.mp4'), str(self.test_dir / 'video.mp4'), 'video.mp4', 1))
        self.db_manager.execute_query(instance_query, (TEST_HASH_SKIPPED, str(self.test_dir / 'skip.jpg'), str(self.test_dir / 'skip.jpg'), 'skip.jpg', 1))
        
        self.db_manager.close() 

    def tearDown(self):
        """Teardown runs after each test."""
        if self.db_manager.conn:
             self.db_manager.close()

    def test_01_processor_updates_all_new_records(self):
        """Test that MetadataProcessor successfully updates records missing metadata."""
        
        # We need a new connection for the processor run
        with DatabaseManager(self.db_manager_path) as db:
            self.processor.db = db # Use the new connection
            self.processor.process_metadata()

        # Check processor's internal count
        self.assertEqual(self.processor.processed_count, 2, "Should have processed 2 files (Image and Video).")
        self.assertEqual(self.processor.skip_count, 0, "Should have skipped 0 files.")
        
        # Verify Image content was updated
        image_data = self.db_manager.execute_query("SELECT width, height, title FROM MediaContent WHERE content_hash = ?;", (TEST_HASH_IMAGE,))[0]
        self.assertEqual(image_data[0], 1920)
        self.assertEqual(image_data[1], 1080)
        self.assertEqual(image_data[2], 'Test Image Title')

        # Verify Video content was updated
        video_data = self.db_manager.execute_query("SELECT width, height, duration, title FROM MediaContent WHERE content_hash = ?;", (TEST_HASH_VIDEO,))[0]
        self.assertEqual(video_data[0], 1280)
        self.assertEqual(video_data[1], 720)
        self.assertAlmostEqual(video_data[2], 120.5)
        self.assertEqual(video_data[3], 'Test Video Title')
        
    def test_02_processor_skips_already_processed_records(self):
        """Test that MetadataProcessor skips files that already have rich metadata."""
        
        # Record TEST_HASH_SKIPPED already has width/height set in setUp.
        
        with DatabaseManager(self.db_manager_path) as db:
            self.processor.db = db
            self.processor.process_metadata()

        # Check processor's internal count
        self.assertEqual(self.processor.processed_count, 2, "Should have processed 2 files (Image and Video).")
        
        # The skipped count should be 0 because the skipping is done at the query level.
        self.assertEqual(self.processor.skip_count, 0, "Should have skipped 0 files at runtime (query handles skipping).")
        
        # Verify the skipped file was NOT touched (width/height remain 100)
        skipped_data = self.db_manager.execute_query("SELECT width, height FROM MediaContent WHERE content_hash = ?;", (TEST_HASH_SKIPPED,))[0]
        self.assertEqual(skipped_data[0], 100)
        self.assertEqual(skipped_data[1], 100)


# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    
    # CRITICAL IMPORT FIX: Move system/cli imports to the execution block
    import sys
    import argparse
    
    # CRITICAL PATH FIX: Add the project root (parent directory) to sys.path
    try:
        # Path(__file__).parent is 'test', .parent is 'file_organizer'
        # Insert at the beginning of sys.path to prioritize local imports
        sys.path.insert(0, str(Path(__file__).parent.parent)) 
    except Exception as e:
        print(f"Warning: Failed to modify sys.path for version check: {e}")
        
    from version_util import print_version_info # <-- This should now succeed.
    
    # ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Metadata Processor.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    
    args, unknown = parser.parse_known_args()
    if args.version:
        print_version_info(__file__, "Metadata Processor Unit Tests")
        sys.exit(0)

    unittest.main(argv=sys.argv[:1] + unknown, exit=False)