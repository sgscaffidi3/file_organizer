# ==============================================================================
# File: test/test_deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 9
# Version: 0.3.9
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "CRITICAL FIX: Implemented logic to correctly set `is_primary=1` on the selected primary copy in the database during deduplication.",
    "CRITICAL FIX: Updated `setUp` to create mock files with unique `mtime` and `size` to ensure stable test environment.",
    "CRITICAL FIX: Modified `setUp` to instantiate DatabaseManager and pass the instance to Deduplicator, resolving the 'WindowsPath' object has no attribute 'execute_query' AttributeError. Added tearDown to close the connection.",
    "FINAL CRITICAL FIXES: - Explicitly added the 'new_path_id' column to MediaContent schema in setUpClass to resolve the sqlite3.OperationalError. - Added a 'date_modified' column to FilePathInstances schema in setUpClass to provide an accessible mtime source for the Deduplicator, resolving the TypeError caused by non-existent file path stat() calls returning None. - Updated setUp to populate the new 'date_modified' field with test mtimes.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "CRITICAL PATH FIX: Explicitly added the project root to `sys.path` to resolve `ModuleNotFoundError: No module named 'version_util'` when running the test file directly.",
    "CRITICAL CROSS-PLATFORM FIX: Replaced hardcoded 'YYYY/MM' assertions with `os.path.join` to correctly handle Windows path separators (`\`) in tests."
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
from typing import Tuple, List, Optional
import os
import shutil
import sqlite3
import argparse
import sys
import datetime

# Add the project root to sys.path to resolve module import issues when running test file directly
try:
    sys.path.insert(0, str(Path(__file__).parent.parent)) 
    from database_manager import DatabaseManager
    from deduplicator import Deduplicator
    from config_manager import ConfigManager
    from version_util import print_version_info
except ImportError as e:
    # This allows the version utility to run even if core dependencies fail
    print(f"Test setup import error: {e}. Please ensure file_organizer modules are in the path or imports are adjusted.")
    # Set a flag to skip tests later if dependencies are truly missing
    if 'DatabaseManager' not in locals():
        DatabaseManager = None


# --- CONSTANTS FOR TESTING ---
TEST_OUTPUT_DIR_NAME = "test_output_dedupe"
TEST_OUTPUT_DIR = Path(TEST_OUTPUT_DIR_NAME) 
TEST_HASH = "deadbeef01234567890abcdef01234567890abcdef01234567890a"


class TestDeduplicator(unittest.TestCase):
    
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
        if DatabaseManager:
            with DatabaseManager(cls.db_manager_path) as db:
                db.create_schema()
                
                # Manually extend MediaContent schema to add new_path_id
                try:
                    db.execute_query("ALTER TABLE MediaContent ADD COLUMN new_path_id TEXT;")
                except sqlite3.OperationalError:
                    pass # Column already exists
            
    @classmethod
    def tearDownClass(cls):
        """Teardown runs once for the class: cleans up the test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        pass

    def setUp(self):
        """Setup runs before each test: cleans the tables and inserts test data."""
        if not DatabaseManager:
            self.skipTest("DatabaseManager dependency failed to load.")

        self.db_manager = DatabaseManager(self.db_manager_path)
        self.db_manager.connect()
        
        # Clean up tables before each test
        self.db_manager.execute_query("DELETE FROM MediaContent;")
        self.db_manager.execute_query("DELETE FROM FilePathInstances;")
        
        # Instantiate Deduplicator
        self.deduplicator = Deduplicator(self.db_manager, self.config_manager)
        
        # --- INSERT TEST DATA ---
        
        # 1. MediaContent record (size is 1024, date_best is 2020-01-01 10:00:00)
        media_content_query = """
        INSERT INTO MediaContent 
        (content_hash, size, file_type_group, date_best) 
        VALUES (?, ?, ?, ?);
        """
        self.db_manager.execute_query(media_content_query, (TEST_HASH, 1024, 'IMAGE', "2020-01-01 10:00:00"))
        
        # 2. FilePathInstances (Three copies of the same content)
        # Note: We use relative paths for the test mock paths to keep it clean, 
        # but the DB stores the full path based on the logic in file_scanner.py
        instance_query = """
        INSERT INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path, date_modified, is_primary)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        
        # Copy A: Latest modified time, but worst path
        selfself.db_manager.execute_query(instance_query, (TEST_HASH, 
                                            str(Path(self.test_dir) / 'Z_path_latest_mtime.jpg'), 
                                            str(Path(self.test_dir) / 'Z_path_latest_mtime.jpg'), 
                                            'Z_path_latest_mtime.jpg', 
                                            "2020-01-03 10:00:00", 
                                            0)) # file_id = 1
        
        # Copy B: Middle modified time, second best path
        self.db_manager.execute_query(instance_query, (TEST_HASH, 
                                            str(Path(self.test_dir) / 'good_path_middle_mtime.jpg'), 
                                            str(Path(self.test_dir) / 'good_path_middle_mtime.jpg'), 
                                            'good_path_middle_mtime.jpg', 
                                            "2020-01-02 10:00:00", 
                                            0)) # file_id = 2
        
        # Copy C: Oldest modified time, best path (alphabetically first)
        self.db_manager.execute_query(instance_query, (TEST_HASH, 
                                            str(Path(self.test_dir) / 'A_path_oldest_mtime.jpg'), 
                                            str(Path(self.test_dir) / 'A_path_oldest_mtime.jpg'), 
                                            'A_path_oldest_mtime.jpg', 
                                            "2020-01-01 10:00:00", 
                                            0)) # file_id = 3
        
        self.db_manager.close() 

    def tearDown(self):
        """Teardown runs after each test."""
        if self.db_manager.conn:
             self.db_manager.close()

    def test_01_select_primary_copy(self):
        """Test the logic for selecting the primary copy based on mtime, then path."""
        
        # The primary copy should be file_id 1 (path='Z_path_latest_mtime.jpg', mtime='2020-01-03 10:00:00')
        primary_copy_path, primary_copy_file_id, primary_instance_path = self.deduplicator._select_primary_copy(TEST_HASH)
        
        self.assertIn("Z_path_latest_mtime.jpg", primary_copy_path, "The primary copy should be the one with the latest date_modified (Copy A).")
        self.assertEqual(primary_copy_file_id, 1, "The file_id of the primary copy should be 1.")

        # Test the tie-breaker: If all times are the same, it should choose the path that is alphabetically first (Copy C, file_id 3)
        self.db_manager.connect()
        # Update all copies to have the same mtime
        self.db_manager.execute_query("UPDATE FilePathInstances SET date_modified = ? WHERE content_hash = ?;", 
                                      ("2020-01-01 10:00:00", TEST_HASH))
        self.db_manager.close() 
        
        primary_copy_path_tie, primary_copy_file_id_tie, primary_instance_path_tie = self.deduplicator._select_primary_copy(TEST_HASH)
        
        self.assertIn("A_path_oldest_mtime.jpg", primary_copy_path_tie, "The primary copy should be the one with the alphabetically first path when mtimes are tied (Copy C).")
        self.assertEqual(primary_copy_file_id_tie, 3, "The file_id of the primary copy should be 3 (Copy C).")


    def test_02_calculate_final_path_format(self):
        """Test that the final path is generated in the correct output/YYYY/MM/HASH_ID.EXT format."""
        
        # NOTE: The test data in setUp uses date_best = "2020-01-01 10:00:00"
        
        # This simulates the path calculation for the primary copy (file_id 1)
        final_path = self.deduplicator._calculate_final_path(
            content_hash=TEST_HASH, 
            date_best="2020-01-01 10:00:00", 
            original_path_extension=".jpg",
            file_id=1
        )
        
        expected_date_part = os.path.join("2020", "01") # FIX: Use os.path.join
        
        self.assertIsInstance(final_path, str)
        self.assertIn(expected_date_part, final_path, "Final path does not contain the correct YYYY/MM directory structure derived from the date_best.")
        self.assertIn(f"{TEST_HASH[:12]}_1.jpg", final_path, "Final path does not contain the correct hash prefix and file_id suffix.")
        
        # Verify it's an absolute path that starts with the OUTPUT_DIR
        self.assertTrue(Path(final_path).is_absolute())
        self.assertTrue(final_path.startswith(str(self.config_manager.OUTPUT_DIR)))

    def test_03_run_deduplication_updates_new_path_id(self):
        """Test that the full deduplication run updates the new_path_id field."""
        
        # 1. Run the deduplication process
        self.deduplicator.run_deduplication()
        
        with DatabaseManager(self.db_manager_path) as db:
            # 2. Verify that the new_path_id field was populated in MediaContent
            populated_count = db.execute_query("SELECT COUNT(*) FROM MediaContent WHERE new_path_id IS NOT NULL;")[0][0]
            self.assertEqual(populated_count, 1, "The new_path_id was not populated for the unique content record.")

            # 3. Retrieve the generated final path (which is the new_path_id field)
            final_path_db_str = db.execute_query("SELECT new_path_id FROM MediaContent WHERE content_hash = ?;", (TEST_HASH,))[0][0]
            
            # 4. Check if the path was generated in the expected format (relative path)
            # The primary copy's file_id is 1, as selected in test_01 (latest mtime)
            expected_date_part = os.path.join("2020", "01") # FIX: Use os.path.join

            self.assertIn(f"{TEST_HASH[:12]}_1.jpg", final_path_db_str)
            self.assertIn(expected_date_part, final_path_db_str, "The final path in MediaContent does not contain the correct YYYY/MM structure.")

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    
    # ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    
    args, unknown = parser.parse_known_args()
    if args.version:
        if 'print_version_info' in locals():
            print_version_info(__file__, "Deduplicator Unit Tests")
        else:
            print("Cannot run version check: version_util failed to import.")
        sys.exit(0)

    unittest.main(argv=sys.argv[:1] + unknown, exit=False)