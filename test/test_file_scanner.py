# ==============================================================================
# File: test_file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "Implemented hashing accuracy test (test_01).",
    "Implemented test_02 to verify content deduplication logic.",
    "Added test for duplicate path insertion being ignored (test_03).",
    "Updated test paths to be relative to the project root.",
    "Implemented explicit count reset in test_03 for scan_and_insert calls.",
    "Updated to use the correct imports (DatabaseManager, FileScanner).",
    "FIX: Updated test_03 assertion logic to align with the core fix in file_scanner.py (using INSERT OR IGNORE).",
    "CRITICAL FIX: Added tearDownClass to explicitly remove the test output directory and database file, ensuring environment isolation and preventing cascading failures in other test suites.",
    "CRITICAL FIX: Fixed test execution logic to ensure the DatabaseManager connection is available when querying counts, preventing IndexError. Also ensured proper cleanup in tearDownClass.",
    "CRITICAL FIX: Modified setUp/tearDown to explicitly open and close the DatabaseManager connection. This resolves the 'Database connection is not open' ProgrammingError during scan execution and query assertions, which caused the ERROR state in test_02 and test_03.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check."
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import sqlite3
import argparse
import sys
# Runtime imports
# PATH SETUP
sys.path.append(str(Path(__file__).resolve().parent.parent))
from database_manager import DatabaseManager
from file_scanner import FileScanner
from config_manager import ConfigManager
from version_util import print_version_info
import config

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_scanner'
TEST_INPUT_DIR = TEST_OUTPUT_DIR / 'input_media'
TEST_DB_FILENAME = 'test_scanner.sqlite'
TEST_DB_PATH = TEST_OUTPUT_DIR / TEST_DB_FILENAME

# --- Constants for Test Data ---
# Standard HASH of a 64KB block of 'X's
HASH_64KB_X = 'e37748464303d8d697841c7b2756d11f977d4c20f78564e9a0c1157173b28b7a'
# HASH of a 128KB block of 'Y's
HASH_128KB_Y = '891395b058c42a59a927a44f9ec33f1165c71932402127914838036d7af6f658'
# HASH of a 128KB block of 'Z's (Same size as Y but different content)
HASH_128KB_Z = '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069'


class TestFileScanner(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup before any tests run."""
        # 1. Setup directories
        TEST_INPUT_DIR.mkdir(parents=True, exist_ok=True)
        # Create a dummy config file (required for ConfigManager)
        config_path = TEST_OUTPUT_DIR / 'dummy_config.json'
        with open(config_path, 'w') as f:
            import json
            json.dump({
                "paths": {"source_directory": str(TEST_INPUT_DIR), "output_directory": str(TEST_OUTPUT_DIR)}, 
                "file_groups": {"IMAGE": [".jpg", ".jpeg"], "VIDEO": [".mp4"]}
            }, f)
        
        # 2. Setup ConfigManager
        cls.config_manager = ConfigManager(config_path)

        # 3. Create dummy files
        with open(TEST_INPUT_DIR / 'file_a.jpg', 'wb') as f:
            f.write(b'X' * config.BLOCK_SIZE * 1) # 64KB -> HASH_64KB_X
        with open(TEST_INPUT_DIR / 'file_b.jpg', 'wb') as f:
            f.write(b'Y' * config.BLOCK_SIZE * 2) # 128KB -> HASH_128KB_Y
        with open(TEST_INPUT_DIR / 'file_c.jpg', 'wb') as f:
            f.write(b'Y' * config.BLOCK_SIZE * 2) # 128KB -> HASH_128KB_Y (Duplicate of B)
        with open(TEST_INPUT_DIR / 'file_d.mp4', 'wb') as f:
            f.write(b'Z' * config.BLOCK_SIZE * 2) # 128KB -> HASH_128KB_Z (Unique type)

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests run."""
        # Remove the entire test output directory
        shutil.rmtree(TEST_OUTPUT_DIR, ignore_errors=True)

    def setUp(self):
        """Setup before each test: initialize DB and scanner."""
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
            
        # 1. Initialize DB and create schema
        self.db_manager = DatabaseManager(TEST_DB_PATH)
        self.db_manager.__enter__() # Manually enter context
        self.db_manager.create_schema()
        
        # 2. Initialize Scanner
        self.scanner = FileScanner(
            self.db_manager, 
            self.config_manager.SOURCE_DIR, 
            self.config_manager.FILE_GROUPS
        )

    def tearDown(self):
        """Cleanup after each test: close DB connection."""
        self.db_manager.__exit__(None, None, None)

    def test_01_hashing_and_initial_insertion(self):
        """Test file hashing accuracy and initial insertion of all unique files."""
        
        self.scanner.scan_and_insert()
        
        # Check MediaContent count (should be 3 unique hashes)
        content_count = self.db_manager.execute_query("SELECT COUNT(*) FROM MediaContent;")[0][0]
        self.assertEqual(content_count, 3, "MediaContent count is incorrect (expected 3 unique files).")
        
        # Check FilePathInstances count (should be 4 total files scanned)
        instance_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count, 4, "FilePathInstances count is incorrect (expected 4 path records).")
        
        # Check specific hashes and file groups
        hash_a_group = self.db_manager.execute_query("SELECT file_type_group FROM MediaContent WHERE content_hash = ?;", (HASH_64KB_X,))[0][0]
        self.assertEqual(hash_a_group, 'IMAGE', "Incorrect file group for file A.")
        
        hash_d_group = self.db_manager.execute_query("SELECT file_type_group FROM MediaContent WHERE content_hash = ?;", (HASH_128KB_Z,))[0][0]
        self.assertEqual(hash_d_group, 'VIDEO', "Incorrect file group for file D.")
        
    def test_02_duplicate_content_deduplication(self):
        """Test that file B and C (same content) result in 1 content record and 2 path records."""
        
        self.scanner.scan_and_insert()
        
        # Check MediaContent count for the duplicate content hash (HASH_128KB_Y)
        content_count = self.db_manager.execute_query("SELECT COUNT(*) FROM MediaContent WHERE content_hash = ?;", (HASH_128KB_Y,))[0][0]
        self.assertEqual(content_count, 1, "Duplicate content hash was inserted more than once in MediaContent.")
        
        # Check FilePathInstances count for the duplicate content hash (HASH_128KB_Y)
        instance_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (HASH_128KB_Y,))[0][0]
        self.assertEqual(instance_count, 2, "Duplicate content should have two path records in FilePathInstances.")
        
    def test_03_duplicate_path_insertion_is_ignored(self):
        """Test that re-scanning the same file paths does not create new FilePathInstances records."""
        
        # 1. Initial scan (scans 4 files, inserts 3 unique content, 4 path instances)
        self.scanner.scan_and_insert()
        
        # Check initial instance count
        instance_count_1 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count_1, 4, "Initial instance count must be 4 before second scan.")
        
        # Run the scan again on the exact same directory (should ignore existing paths)
        # Note: The scanner's internal 'files_inserted_count' tracks how many new rows were inserted.
        self.scanner.files_inserted_count = 0 # Reset the counter for the second run
        self.scanner.scan_and_insert()
        
        # Count FilePathInstances after the second scan (must still be 4 due to INSERT OR IGNORE)
        instance_count_2 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        # CRITICAL ASSERTION: The count must remain 4.
        self.assertEqual(instance_count_2, 4, "Duplicate path scan should not increase the instance count.")
        # Check that the scanner inserted 0 *new* files (it may scan, but shouldn't insert)
        # NOTE: The scanner's insert count tracks files that were *attempted* to be inserted,
        # but the test runner *must* assert that the actual DB count did not increase.
        # Since the FileScanner implementation only counts successfully new inserts,
        # the internal `files_inserted_count` should be 0, or at least no more than the initial scan.
        # Since the initial scan inserted 4 new file paths, the second scan should result in 0 new inserts.
        self.assertEqual(self.scanner.files_inserted_count, 0, "No new file paths should have been inserted on the second scan.")


# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    #  ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for FileScanner.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        from version_util import print_version_info 
        print_version_info(__file__, "FileScanner Unit Tests")
        sys.exit(0)
        
    unittest.main()