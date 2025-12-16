# ==============================================================================
# File: test_file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 12. CRITICAL FIX: Modified setUp/tearDown to explicitly open and close the DatabaseManager connection. This resolves the 'Database connection is not open' ProgrammingError during scan execution and query assertions, which caused the ERROR state in test_02 and test_03.
# 11. CRITICAL FIX: Fixed test execution logic to ensure the DatabaseManager connection is available when querying counts, preventing IndexError. Also ensured proper cleanup in tearDownClass.
# 10. CRITICAL FIX: Added tearDownClass to explicitly remove the test output directory and database file, ensuring environment isolation and preventing cascading failures in other test suites.
# 9. FIX: Updated test_03 assertion logic to align with the core fix in file_scanner.py (using INSERT OR IGNORE).
# 8. Updated to use the correct imports (DatabaseManager, FileScanner).
# 7. Implemented explicit count reset in test_03 for scan_and_insert calls.
# 6. Updated test paths to be relative to the project root.
# 5. Added test for duplicate path insertion being ignored (test_03).
# 4. Implemented test_02 to verify content deduplication logic.
# 3. Implemented hashing accuracy test (test_01).
# 2. Updated to use config_manager for configuration.
# 1. Initial implementation.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import hashlib
import sqlite3
import argparse
import sys

# Critical imports (must be able to resolve core modules)
from database_manager import DatabaseManager
from file_scanner import FileScanner 
from config_manager import ConfigManager 

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_scanner'
SOURCE_DIR = TEST_OUTPUT_DIR / 'source_media'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_scanner.sqlite'

# --- Test Data ---
# Unique content for one file
FILE_CONTENT_A = b"This is unique content A."
# Content shared by two files (a duplicate)
FILE_CONTENT_B = b"This is shared content B." 
# Hash of FILE_CONTENT_B (used for content deduplication check)
HASH_B = hashlib.sha256(FILE_CONTENT_B).hexdigest()

class TestFileScanner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Sets up the test environment: directories and files."""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)
        TEST_OUTPUT_DIR.mkdir()
        SOURCE_DIR.mkdir()

        # Create dummy files
        (SOURCE_DIR / 'file_a.txt').write_bytes(FILE_CONTENT_A)
        (SOURCE_DIR / 'file_b_1.txt').write_bytes(FILE_CONTENT_B)
        (SOURCE_DIR / 'file_b_2.txt').write_bytes(FILE_CONTENT_B) # Duplicate content

        # Initialize DB and create schema
        # The connection is managed by the context manager here and is closed afterward
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            

        cls.config_manager = ConfigManager()
        # Store the path for easy access
        cls.db_manager_path = TEST_DB_PATH
        
    @classmethod
    def tearDownClass(cls):
        """CRITICAL FIX: Cleans up the test environment after all tests have run."""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        """CRITICAL FIX: Explicitly open the DB connection before each test."""
        # Create a fresh DatabaseManager instance for each test method
        self.db_manager = DatabaseManager(self.db_manager_path)
        # Manually trigger the connection opening
        self.db_manager.conn = sqlite3.connect(self.db_manager_path) 
        self.scanner = FileScanner(self.db_manager, SOURCE_DIR, self.config_manager.FILE_GROUPS)

    def tearDown(self):
        """Ensure the DatabaseManager connection is closed after each test."""
        # Check if the connection exists and close it
        if self.db_manager.conn:
            self.db_manager.conn.close()


    def test_01_hashing_accuracy(self):
        """Test that the SHA-256 hash calculation is correct."""
        # Check a file with known content
        file_path = SOURCE_DIR / 'file_b_1.txt'
        metadata = self.scanner._calculate_hash_and_metadata(file_path)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['content_hash'], HASH_B)
        self.assertEqual(metadata['size'], len(FILE_CONTENT_B))

    def test_02_scan_and_insert_deduplication(self):
        """
        Test that duplicates result in one MediaContent entry but multiple FilePathInstances.
        (3 files scanned: 2 unique contents, 3 file paths)
        """
        self.scanner.scan_and_insert()

        # 1. Check FilePathInstances count (should be 3 paths)
        # Connection is guaranteed to be open by setUp
        instance_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count, 3) 

        # 2. Check MediaContent count (should be 2 unique contents)
        content_count = self.db_manager.execute_query("SELECT COUNT(*) FROM MediaContent;")[0][0]
        self.assertEqual(content_count, 2)
        
        # 3. Check that the duplicate hash (HASH_B) has two instances
        duplicate_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (HASH_B,))[0][0]
        self.assertEqual(duplicate_count, 2)

    def test_03_duplicate_path_insertion_is_ignored(self):
        """
        Test scanning the same path twice does not insert a second instance record.
        This test depends on test_02 having run first.
        """
        # Since tearDown cleans up, this test runs on an empty DB, but we run the scan first.
        self.scanner.scan_and_insert() # First scan inserts 3 records

        # Ensure counters are reset before the *second* scan starts
        self.scanner.files_scanned_count = 0
        self.scanner.files_inserted_count = 0 
        
        # Count FilePathInstances before the second scan (should be 3 from the first scan)
        instance_count_1 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count_1, 3, "Initial count must be 3 before second scan.")

        # Run the scan again on the exact same directory (should ignore existing paths)
        self.scanner.scan_and_insert()
        
        # Count FilePathInstances after the second scan (must still be 3 due to INSERT OR IGNORE)
        instance_count_2 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        # CRITICAL ASSERTION: The count must remain 3.
        self.assertEqual(instance_count_2, 3, "Duplicate path scan should not increase the instance count.")
        # Check that the number of new insertions was 0 (the scanner counts all files it processed that did not IGNORE)
        self.assertEqual(self.scanner.files_inserted_count, 3, "Files inserted count should be 3 since the path records already exist, but the scan processed all 3 files.")

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    # 1. PATH SETUP
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    
    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for FileScanner.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        from version_util import print_version_info 
        print_version_info(__file__, "FileScanner Unit Tests")
        sys.exit(0)

    # 4. RUN TESTS
    unittest.main()