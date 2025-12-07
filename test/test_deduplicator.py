# ==============================================================================
# File: test_deduplicator.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial implementation of Deduplicator unit tests.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import argparse
import hashlib
import time
import datetime

from database_manager import DatabaseManager
from deduplicator import Deduplicator 
from version_util import print_version_info
from config_manager import ConfigManager 

# --- Constants & Setup ---
TEST_OUTPUT_DIR = Path('./test_output_dedupe')
TEST_SOURCE_DIR = TEST_OUTPUT_DIR / 'source_media'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_dedupe_db.sqlite'

# Define hashes and the standardized date
KNOWN_HASH = hashlib.sha256(b"duplicate_content").hexdigest()
BEST_DATE_STR = "2020-11-15 10:30:00" 
BEST_DATE_OBJ = datetime.datetime(2020, 11, 15, 10, 30, 0)

class TestDeduplicator(unittest.TestCase):
    """Tests the functionality of the Deduplicator class."""

    @classmethod
    def setUpClass(cls):
        shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)
        TEST_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        
        cls.config_manager = ConfigManager()

        # 1. Create files with differing modification times for KEEP_OLDEST test
        
        # File 1: The OLDEST copy (10 seconds ago) - Should be selected as Primary
        cls.path_oldest = TEST_SOURCE_DIR / "archive" / "oldest_copy.jpg"
        cls.path_oldest.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.path_oldest, 'wb') as f:
            f.write(b"duplicate_content")
        os.utime(cls.path_oldest, (time.time() - 10, time.time() - 10)) # Set mtime 10s ago

        # File 2: The NEWEST copy (1 second ago)
        cls.path_newest = TEST_SOURCE_DIR / "phone_sync" / "newest_copy.jpg"
        cls.path_newest.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.path_newest, 'wb') as f:
            f.write(b"duplicate_content")
        os.utime(cls.path_newest, (time.time() - 1, time.time() - 1)) # Set mtime 1s ago

        # 2. Initialize DB and insert data simulating previous pipeline steps
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            
            # Insert the unique content hash with the final extracted date
            db.execute_query("""
            INSERT INTO MediaContent 
            (content_hash, file_type_group, date_best) 
            VALUES (?, ?, ?);
            """, (KNOWN_HASH, 'IMAGE', BEST_DATE_STR))
            
            # Insert both duplicate path instances
            db.execute_query("""
            INSERT INTO FilePathInstances 
            (content_hash, original_full_path, original_relative_path) 
            VALUES (?, ?, ?);
            """, (KNOWN_HASH, str(cls.path_oldest.resolve()), str(cls.path_oldest.relative_to(TEST_SOURCE_DIR))))
            
            db.execute_query("""
            INSERT INTO FilePathInstances 
            (content_hash, original_full_path, original_relative_path) 
            VALUES (?, ?, ?);
            """, (KNOWN_HASH, str(cls.path_newest.resolve()), str(cls.path_newest.relative_to(TEST_SOURCE_DIR))))

    def setUp(self):
        # Ensure new_path_id is cleared before each test
        with DatabaseManager(TEST_DB_PATH) as db:
            db.execute_query("UPDATE MediaContent SET new_path_id = NULL;")

    def test_01_primary_selection_keep_oldest(self):
        """Test that KEEP_OLDEST strategy selects the file with the oldest modification time."""
        # Note: The test uses the default strategy 'KEEP_OLDEST'
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            
            primary_path = dedupe._select_primary_copy(KNOWN_HASH)
            
            # Check that the oldest path was selected
            self.assertEqual(primary_path, str(self.path_oldest.resolve()))
            self.assertEqual(dedupe.duplicates_found, 1) # One duplicate instance found

    def test_02_final_path_calculation(self):
        """Test that the standardized output path is calculated correctly."""
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            
            # Simulate the path calculation for the unique file
            final_path = dedupe._calculate_final_path_with_ext(
                file_type_group='IMAGE', 
                date_best_str=BEST_DATE_STR, 
                content_hash=KNOWN_HASH, 
                ext='.jpg'
            )
            
            # Expected format: IMAGE / YEAR / YEAR-MONTH-DAY / hash_time.ext
            # Date part should be: 2020/2020-11-15
            expected_date_part = BEST_DATE_OBJ.strftime("%Y/%Y-%m-%d") 
            # Time part should be: 103000
            expected_filename = f"{KNOWN_HASH[:12]}_{BEST_DATE_OBJ.strftime('%H%M%S')}.jpg"
            
            expected_path = Path("IMAGE") / expected_date_part / expected_filename
            
            self.assertEqual(final_path, str(expected_path))

    def test_03_run_deduplication_updates_db(self):
        """Test that running the full deduplication updates the new_path_id field."""
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            dedupe.run_deduplication()
            
            # Check the database for the new_path_id
            query = "SELECT new_path_id FROM MediaContent WHERE content_hash = ?;"
            result = db.execute_query(query, (KNOWN_HASH,))[0][0]
            
            self.assertIsNotNone(result)
            self.assertIn("IMAGE/2020/2020-11-15", result)
            self.assertTrue(result.endswith(".jpg"))
            self.assertEqual(dedupe.processed_count, 1) # One unique hash was processed

    @classmethod
    def tearDownClass(cls):
        # Clean up the test environment
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Deduplicator Unit Tests")
    else:
        unittest.main()