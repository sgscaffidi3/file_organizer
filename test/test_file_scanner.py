# ==============================================================================
# File: test/test_file_scanner.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_PATCH_VERSION = 12
# Version: 0.3.12
# ------------------------------------------------------------------------------
# CHANGELOG:
_REL_CHANGES = [10]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
from typing import Tuple, List, Optional
import os
import shutil
import sqlite3
import hashlib
import datetime
import argparse
import sys

# Add the project root to sys.path to resolve module import issues when running test file directly
try:
    sys.path.insert(0, str(Path(__file__).parent.parent)) 
    # --- Project Dependencies ---
    from database_manager import DatabaseManager
    from file_scanner import FileScanner
    from config_manager import ConfigManager
    from version_util import print_version_info
    import config # For BLOCK_SIZE
except ImportError as e:
    print(f"Test setup import error: {e}. Please ensure file_organizer modules are in the path or imports are adjusted.")
    if 'DatabaseManager' not in locals():
        DatabaseManager = None
    if 'FileScanner' not in locals():
        FileScanner = None

# --- CONSTANTS FOR TESTING ---
TEST_OUTPUT_DIR_NAME = "test_output_scanner"
TEST_OUTPUT_DIR = Path(TEST_OUTPUT_DIR_NAME) 
INPUT_MEDIA_DIR = TEST_OUTPUT_DIR / 'input_media'
# Content for mock files
CONTENT_64KB_X = os.urandom(64 * 1024)
CONTENT_64KB_Y = os.urandom(64 * 1024)

# Pre-calculate hashes for assertions
HASH_64KB_X = hashlib.sha256(CONTENT_64KB_X).hexdigest()
HASH_64KB_Y = hashlib.sha256(CONTENT_64KB_Y).hexdigest()

# Mock file paths
FILE_A_PATH = INPUT_MEDIA_DIR / 'file_a.jpg'
FILE_B_PATH = INPUT_MEDIA_DIR / 'file_b.jpg' # Duplicate of C
FILE_C_PATH = INPUT_MEDIA_DIR / 'subdir' / 'file_c.jpg' # Duplicate of B
FILE_D_PATH = INPUT_MEDIA_DIR / 'file_d.png' # Unique


class TestFileScanner(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup runs once for the class: creates the test environment and database schema."""
        if not DatabaseManager or not FileScanner:
            return
            
        cls.test_dir = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
        cls.config_manager = ConfigManager(output_dir=cls.test_dir) # CRITICAL FIX: Removed unsupported source_dir
        cls.db_manager_path = str(cls.test_dir / 'metadata.sqlite')
        
        # 1. Clean up and create test environment
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        INPUT_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        (INPUT_MEDIA_DIR / 'subdir').mkdir(parents=True, exist_ok=True)
        
        # 2. Create Mock Files
        # File A: Unique content X
        with open(FILE_A_PATH, 'wb') as f:
            f.write(CONTENT_64KB_X)
        # File B: Duplicate content Y (first instance)
        with open(FILE_B_PATH, 'wb') as f:
            f.write(CONTENT_64KB_Y)
        # File C: Duplicate content Y (second instance)
        with open(FILE_C_PATH, 'wb') as f:
            f.write(CONTENT_64KB_Y)
        # File D: Unique content X (different extension, different hash)
        with open(FILE_D_PATH, 'wb') as f:
            f.write(CONTENT_64KB_X) 
        
        # 3. Initialize Database and Schema
        # Use a connection to ensure schema creation, and explicitly close it.
        try:
            db_setup = DatabaseManager(cls.db_manager_path)
            db_setup.connect()
            db_setup.create_schema()
        finally:
             if 'db_setup' in locals() and db_setup.conn:
                db_setup.close() # Ensure setup connection is closed

            
    @classmethod
    def tearDownClass(cls):
        """Teardown runs once for the class: cleans up the test environment."""
        if 'cls' in locals() and cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        pass

    def setUp(self):
        """Setup runs before each test: cleans the tables and sets up the scanner."""
        if not DatabaseManager or not FileScanner:
            self.skipTest("Core dependencies failed to load.")

        self.db_manager = DatabaseManager(self.db_manager_path)
        self.db_manager.connect()
        
        # Clean up tables before each test
        self.db_manager.execute_query("DELETE FROM MediaContent;")
        self.db_manager.execute_query("DELETE FROM FilePathInstances;")
        
        # Use the actual input directory (INPUT_MEDIA_DIR) for the scanner
        self.scanner = FileScanner(self.db_manager, INPUT_MEDIA_DIR, self.config_manager.FILE_GROUPS)

    def tearDown(self):
        """Teardown runs after each test."""
        if self.db_manager.conn:
             self.db_manager.close()

    def test_01_hashing_and_initial_insertion(self):
        """Test file hashing accuracy and initial insertion of all unique files."""
        
        # Run scan for the first time
        self.scanner.scan_and_insert()
        
        # Check scanner's internal counts
        self.assertEqual(self.scanner.files_scanned_count, 4, "Total files scanned count is incorrect.")
        # We expect 4 files inserted, as all 4 are unique paths
        self.assertEqual(self.scanner.files_inserted_count, 4, "Unique path instances recorded count is incorrect (expected 4).")
        
        # Check database content count 
        # Files A(X), B(Y), C(Y), D(X) result in 2 unique content hashes: X and Y.
        content_count = self.db_manager.execute_query("SELECT COUNT(*) FROM MediaContent;")[0][0]
        self.assertEqual(content_count, 2, "MediaContent count is incorrect (expected 2 unique content hashes: X and Y).")

        # Verify insertion and file type group for content X
        hash_x_group = self.db_manager.execute_query("SELECT file_type_group FROM MediaContent WHERE content_hash = ?;", (HASH_64KB_X,))
        self.assertGreater(len(hash_x_group), 0, "MediaContent record for HASH_64KB_X is missing.")
        self.assertEqual(hash_x_group[0][0], 'IMAGE', "File A/D content hash should be inserted as 'IMAGE'.")

        # Verify file path instances count (must be 4)
        instance_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count, 4, "FilePathInstances count is incorrect (expected 4).")


    def test_02_duplicate_content_deduplication(self):
        """Test that file B and C (same content) result in 1 content record and 2 path records."""
        
        # Run scan (This test is mainly about the counts)
        self.scanner.scan_and_insert()
        
        # The content hash for B and C is HASH_64KB_Y.
        
        # Check MediaContent count for the duplicate hash (should be 1)
        content_count = self.db_manager.execute_query("SELECT COUNT(*) FROM MediaContent WHERE content_hash = ?;", (HASH_64KB_Y,))[0][0]
        self.assertEqual(content_count, 1, "Duplicate content hash was inserted more than once in MediaContent.")
        
        # Check FilePathInstances count for the duplicate hash (should be 2)
        instance_count = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (HASH_64KB_Y,))[0][0]
        self.assertEqual(instance_count, 2, "File path instances count for duplicate content is incorrect (expected 2).")


    def test_03_duplicate_path_insertion_is_ignored(self):
        """Test that re-scanning the same file paths does not create new FilePathInstances records."""
        
        # 1. First scan (initial insert)
        self.scanner.scan_and_insert()
        
        # Verify initial path instance count
        instance_count_1 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count_1, 4, "Initial instance count must be 4 before second scan.")
        
        # 2. Re-scan the same files (should skip all based on path/size/mtime)
        # Note: The scanner's quick-skip logic should handle this.
        self.scanner.scan_and_insert()
        
        # Check final path instance count (should still be 4)
        instance_count_2 = self.db_manager.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
        self.assertEqual(instance_count_2, 4, "Final instance count should remain 4 after re-scanning the same paths.")
        
        # Check scanner's internal counts on re-scan
        self.assertEqual(self.scanner.files_scanned_count, 4, "Files scanned count on second run must be 4.")
        self.assertEqual(self.scanner.files_inserted_count, 0, "Unique instances recorded count on second run must be 0.")

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    
    # ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for File Scanner.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    
    args, unknown = parser.parse_known_args()
    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        if 'print_version_info' in locals():
            print_version_info(__file__, "File Scanner Unit Tests")
        else:
            print("Cannot run version check: version_util failed to import.")
        sys.exit(0)

    unittest.main(argv=sys.argv[:1] + unknown, exit=False)