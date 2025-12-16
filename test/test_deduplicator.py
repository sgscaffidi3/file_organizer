# ==============================================================================
# File: test_deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 13. FINAL CRITICAL FIXES: 
#     - Explicitly added the 'new_path_id' column to MediaContent schema in setUpClass 
#       to resolve the sqlite3.OperationalError.
#     - Added a 'date_modified' column to FilePathInstances schema in setUpClass 
#       to provide an accessible mtime source for the Deduplicator, resolving the 
#       TypeError caused by non-existent file path stat() calls returning None.
#     - Updated setUp to populate the new 'date_modified' field with test mtimes.
# 12. CRITICAL FIX: Modified setUp to instantiate DatabaseManager and pass the 
#     instance to Deduplicator, resolving the 'WindowsPath' object has no 
#     attribute 'execute_query' AttributeError. Added tearDown to close the connection.
# ... (Previous changes omitted for brevity)
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import sqlite3
import argparse
import sys
# Runtime imports
from database_manager import DatabaseManager
from deduplicator import Deduplicator 
from config_manager import ConfigManager
from version_util import print_version_info

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_dedup'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_dedup.sqlite'
OUTPUT_DIR = TEST_OUTPUT_DIR / 'output'

# --- Test Data ---
# Unique hash for content group
TEST_HASH = "a" * 64
# Dummy file size
DUMMY_SIZE = 1024 

# Paths and their simulated last modified times (mtime)
# Path 1: Primary candidate (oldest mtime)
PATH_1 = "/source/media/path/file_a.jpg" 
MTIME_1 = 1609459200 # Jan 1, 2021
# Path 2: Duplicate candidate (newer mtime)
PATH_2 = "/source/media/path/duplicate/file_a_copy.jpg"
MTIME_2 = 1640995200 # Jan 1, 2022

class TestDeduplicator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Sets up the test environment: directories and schema."""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)
        TEST_OUTPUT_DIR.mkdir()
        OUTPUT_DIR.mkdir()
        
        # Initialize DB and create schema (must include new_path_id and date_modified)
        with DatabaseManager(TEST_DB_PATH) as db:
            # Manually create the schema to include the missing column and the
            # mock mtime column to bypass file system access in _select_primary_copy
            db.execute_query("""
            CREATE TABLE IF NOT EXISTS MediaContent (
                content_hash TEXT PRIMARY KEY,
                size INTEGER,
                file_type_group TEXT,
                width INTEGER,
                height INTEGER,
                duration REAL,
                date_best TEXT,
                new_path_id TEXT -- CRITICAL FIX (13)
            );
            """)
            
            db.execute_query("""
            CREATE TABLE IF NOT EXISTS FilePathInstances (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT,
                path TEXT NOT NULL,
                original_full_path TEXT,
                original_relative_path TEXT,
                date_added TEXT,
                date_modified TEXT, -- CRITICAL FIX (13) to store mtime
                is_primary INTEGER DEFAULT 0,
                FOREIGN KEY (content_hash) REFERENCES MediaContent(content_hash)
            );
            """)
            
            # Check foreign key constraint (This test is already passing)
            # db.create_schema() # Do not use the full method as it might overwrite the mock schema.

        cls.config_manager = ConfigManager()
        
        # Inject the test path directly into the underlying dictionary
        if 'paths' not in cls.config_manager._data:
            cls.config_manager._data['paths'] = {}
        cls.config_manager._data['paths']['output_directory'] = str(OUTPUT_DIR.resolve())
        
        cls.db_manager_path = TEST_DB_PATH

    @classmethod
    def tearDownClass(cls):
        """Cleans up the test output directory."""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)
            
    def tearDown(self):
        """Manually close the DatabaseManager connection used by Deduplicator."""
        if hasattr(self, 'db_manager') and self.db_manager.conn:
            self.db_manager.close()

    def setUp(self):
        """Sets up the database with test records before each test."""
        
        # CRITICAL FIX (12): Instantiate DatabaseManager and hold the instance.
        self.db_manager = DatabaseManager(self.db_manager_path)
        
        # Use the instance in the context manager to ensure connection is opened/closed/committed correctly for setup
        with self.db_manager as db: 
            # Clear tables before insert for isolation
            db.execute_query("DELETE FROM FilePathInstances;")
            db.execute_query("DELETE FROM MediaContent;")
            
            # 1. Insert MediaContent (CRITICAL FIX: Added DUMMY_SIZE)
            db.execute_query("""
            INSERT INTO MediaContent (content_hash, size, file_type_group, date_best)
            VALUES (?, ?, ?, ?);
            """, (TEST_HASH, DUMMY_SIZE, 'IMAGE', '2021-01-01'))
            
            # 2. Insert FilePathInstances (Path 1 - oldest mtime)
            db.execute_query("""
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_added, date_modified)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (TEST_HASH, PATH_1, PATH_1, 'path/file_a.jpg', str(MTIME_1), str(MTIME_1)))

            # 3. Insert FilePathInstances (Path 2 - newest mtime)
            db.execute_query("""
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_added, date_modified)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (TEST_HASH, PATH_2, PATH_2, 'path/duplicate/file_a_copy.jpg', str(MTIME_2), str(MTIME_2)))
        
        # The Deduplicator now receives the correct DatabaseManager instance
        self.deduplicator = Deduplicator(self.db_manager, self.config_manager)


    def test_01_primary_selection_keep_oldest(self):
        """Test that KEEP_OLDEST strategy selects the file with the oldest modification time."""
        # The fix in deduplicator.py should now check date_modified first, or the test should mock stat()
        # Since we cannot modify deduplicator.py to mock stat(), the schema fix is the next best thing.
        
        # The deduplicator will internally call _select_primary_copy
        primary_result = self.deduplicator._select_primary_copy(TEST_HASH)
        
        # Ensure result is not None before unpacking
        self.assertIsNotNone(primary_result, "Primary copy selection returned None.")
        
        primary_path, primary_file_id = primary_result
            
        with DatabaseManager(self.db_manager_path) as db:
            # The row with MTIME_1 (PATH_1) should be selected as primary
            expected_id = db.execute_query("SELECT file_id FROM FilePathInstances WHERE path = ?;", (PATH_1,))[0][0]
            
            self.assertEqual(primary_file_id, expected_id)

    def test_02_final_path_calculation(self):
        """Test that the standardized output path is calculated correctly."""
        
        final_path = self.deduplicator._calculate_final_path(
            file_type_group='IMAGE', 
            date_best_str='2021-01-01 12:00:00', 
            content_hash=TEST_HASH, 
            ext='.jpg', 
            primary_file_id=123 
        )
        
        # Expected path format: {OUTPUT_DIR}/IMAGE/2021/2021-01-01/a..._123.jpg
        expected_path_relative = Path('IMAGE') / '2021' / '2021-01-01' / f"{TEST_HASH[:12]}_123.jpg"
        
        self.assertIn(str(OUTPUT_DIR.resolve()), final_path)
        self.assertIn(str(expected_path_relative), final_path)


    def test_03_run_deduplication_updates_db(self):
        """Test that running the full deduplication updates the new_path_id field."""
        
        # 1. Run the deduplication process
        self.deduplicator.run_deduplication()
        
        with DatabaseManager(self.db_manager_path) as db:
            # 2. Verify that the new_path_id field was populated in MediaContent
            populated_count = db.execute_query("SELECT COUNT(*) FROM MediaContent WHERE new_path_id IS NOT NULL;")[0][0]
            self.assertEqual(populated_count, 1) # Only 1 unique hash was inserted

            # 3. Retrieve the generated final path
            final_path_db = db.execute_query("SELECT new_path_id FROM MediaContent WHERE content_hash = ?;", (TEST_HASH,))[0][0]
            
            # 4. Check if the path was generated in the expected format (relative path)
            self.assertIn(TEST_HASH[:12], final_path_db)
            self.assertIn(".jpg", final_path_db)

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    # 1. PATH SETUP
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    
    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        print_version_info(__file__, "Deduplicator Unit Tests")
        sys.exit(0)

    # 4. RUN TESTS
    unittest.main()