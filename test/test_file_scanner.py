# ==============================================================================
# File: test_file_scanner.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial implementation of FileScanner unit tests.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Updated to use ConfigManager for SOURCE_DIR and FILE_GROUPS (Test setup remains the same, but the tested class uses ConfigManager).
# 5. Project name changed to "file_organizer" in descriptions.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import hashlib
import shutil
import argparse

from database_manager import DatabaseManager
from file_scanner import FileScanner 
from version_util import print_version_info
from config_manager import ConfigManager 

# Define constants for testing
TEST_OUTPUT_DIR = Path('./test_output_scanner')
TEST_SOURCE_DIR = TEST_OUTPUT_DIR / 'source_media'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_scanner_metadata.sqlite'
KNOWN_CONTENT = b"This is a test file for calculating SHA-256."
KNOWN_HASH = hashlib.sha256(KNOWN_CONTENT).hexdigest() 

class TestFileScanner(unittest.TestCase):
    """Tests the functionality of the FileScanner class."""

    @classmethod
    def setUpClass(cls):
        # 0. Setup directories
        shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)
        TEST_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 1. Create duplicate files (same hash)
        cls.file_a_path = TEST_SOURCE_DIR / "file_a.txt"
        with open(cls.file_a_path, 'wb') as f:
            f.write(KNOWN_CONTENT)
            
        cls.file_b_path = TEST_SOURCE_DIR / "subdir" / "file_b_copy.txt"
        cls.file_b_path.parent.mkdir(exist_ok=True)
        with open(cls.file_b_path, 'wb') as f:
            f.write(KNOWN_CONTENT)
            
        # 2. Create a unique file (different hash)
        cls.file_c_path = TEST_SOURCE_DIR / "file_c_unique.log"
        with open(cls.file_c_path, 'w') as f:
            f.write("This is different content.")

        # 3. Initialize the database and schema
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()

        # 4. Initialize ConfigManager to get file groups for the scanner
        cls.config_manager = ConfigManager()
            
    def setUp(self):
        # Ensure tables are empty before each test run
        with DatabaseManager(TEST_DB_PATH) as db:
            db.execute_query("DELETE FROM MediaContent;")
            db.execute_query("DELETE FROM FilePathInstances;")

    def test_01_hashing_accuracy(self):
        """Test that the SHA-256 hash calculation is correct."""
        with DatabaseManager(TEST_DB_PATH) as db:
            # Pass dummy paths/groups, as this test is about hashing logic
            scanner = FileScanner(db, TEST_SOURCE_DIR, self.config_manager.FILE_GROUPS) 
            metadata = scanner._calculate_hash_and_metadata(self.file_a_path)
            self.assertEqual(metadata['content_hash'], KNOWN_HASH)

    def test_02_scan_and_insert_deduplication(self):
        """Test that duplicates result in one MediaContent entry but multiple FilePathInstances."""
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, TEST_SOURCE_DIR, self.config_manager.FILE_GROUPS)
            scanner.scan_and_insert()
            
            # Should be 2 unique files: file_a/file_b (same hash) and file_c (unique hash)
            media_count = db.execute_query("SELECT COUNT(*) FROM MediaContent;")[0][0]
            self.assertEqual(media_count, 2) 
            
            # Should be 3 file paths (instances) recorded
            instance_count = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
            self.assertEqual(instance_count, 3) 
            
            # Check the count for the KNOWN_HASH
            duplicate_path_count = db.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (KNOWN_HASH,))[0][0]
            self.assertEqual(duplicate_path_count, 2)

    def test_03_duplicate_path_insertion_is_ignored(self):
        """Test scanning the same path twice does not insert a second instance record."""
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, TEST_SOURCE_DIR, self.config_manager.FILE_GROUPS)
            
            # First scan inserts 3 instances
            scanner.scan_and_insert()
            instance_count_1 = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
            self.assertEqual(instance_count_1, 3)
            
            scanner.files_scanned_count = 0
            scanner.files_inserted_count = 0
            
            # Second scan should scan 3 files but insert 0 new instances due to UNIQUE constraint
            scanner.scan_and_insert()
            instance_count_2 = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]

            self.assertEqual(instance_count_2, 3)
            self.assertEqual(scanner.files_inserted_count, 0) # Key test: no new rows inserted
            

    @classmethod
    def tearDownClass(cls):
        # Clean up the test environment
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unit tests for FileScanner.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "File Scanner Unit Tests")
    else:
        unittest.main()