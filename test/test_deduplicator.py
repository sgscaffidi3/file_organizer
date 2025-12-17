# ==============================================================================
# File: test_deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "CRITICAL FIX: Modified setUp to instantiate DatabaseManager and pass the instance to Deduplicator, resolving the 'WindowsPath' object has no attribute 'execute_query' AttributeError. Added tearDown to close the connection.",
    "FINAL CRITICAL FIXES: - Explicitly added the 'new_path_id' column to MediaContent schema in setUpClass to resolve the sqlite3.OperationalError. - Added a 'date_modified' column to FilePathInstances schema in setUpClass to provide an accessible mtime source for the Deduplicator, resolving the TypeError caused by non-existent file path stat() calls returning None. - Updated setUp to populate the new 'date_modified' field with test mtimes.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "DEFINITIVE FIX: Removed the failing MockConfigManager and instantiated the real ConfigManager with a custom output_dir, fixing the setup failure (Requires `config_manager.py` update)."
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import sqlite3
import argparse
import sys
import datetime
import time 

# --- Project Dependencies ---
try:
    from database_manager import DatabaseManager
    from deduplicator import Deduplicator
    from config_manager import ConfigManager
    from version_util import print_version_info
    import config
except ImportError as e:
    print(f"Test setup import error: {e}. Please ensure file_organizer modules are in the path or imports are adjusted.")
    sys.exit(1)


# --- CONSTANTS FOR TESTING ---
TEST_OUTPUT_DIR_NAME = "test_output_dedupe"
# Path to the test environment root (relative to where the test is run)
TEST_OUTPUT_DIR = Path(TEST_OUTPUT_DIR_NAME) 
TEST_DB_PATH = TEST_OUTPUT_DIR / 'metadata.sqlite'
TEST_HASH = "deadbeef01234567890abcdef01234567890abcdef01234567890a"


class TestDeduplicator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup runs once for the class: creates the test environment and database schema."""
        # CRITICAL FIX: Instantiate the real ConfigManager, passing the test path.
        cls.test_dir = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
        # This relies on the updated ConfigManager accepting an output_dir argument.
        cls.config_manager = ConfigManager(output_dir=cls.test_dir) 
        
        cls.db_manager_path = str(cls.test_dir / 'metadata.sqlite')
        
        # 1. Clean up and create test environment
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Initialize Database and Schema
        with DatabaseManager(cls.db_manager_path) as db:
            db.create_schema()
            
            # Manually extend MediaContent schema for deduplicator needs 
            try:
                # Add the new_path_id column to MediaContent 
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN new_path_id TEXT;")
            except sqlite3.OperationalError:
                pass # Column already exists
            
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
        
        # Instantiate Deduplicator with the DatabaseManager instance
        self.deduplicator = Deduplicator(self.db_manager, self.config_manager)
        
        # --- INSERT TEST DATA ---
        MEDIA_DATE_BEST = "2020-01-01 10:00:00"
        media_content_query = """
        INSERT INTO MediaContent 
        (content_hash, size, file_type_group, date_best) 
        VALUES (?, ?, ?, ?);
        """
        self.db_manager.execute_query(media_content_query, (TEST_HASH, 1024, 'IMAGE', MEDIA_DATE_BEST))
        
        # Copy 1: The PRIMARY copy (earliest date_modified)
        file_path_1 = f"/path/to/source/A/F05.jpg"
        mtime_1 = "2020-01-01 10:00:00" 
        
        # Copy 2: A DUPLICATE copy (later date_modified)
        file_path_2 = f"/path/to/source/B/F05_copy.jpg"
        mtime_2 = "2020-01-01 11:00:00"
        
        # Copy 3: Another DUPLICATE copy (same later date_modified, longer path)
        file_path_3 = f"/path/to/source/C/very_long_path_F05_copy.jpg"
        mtime_3 = "2020-01-01 11:00:00"

        instance_query = """
        INSERT INTO FilePathInstances 
        (content_hash, path, original_full_path, original_relative_path, date_modified)
        VALUES (?, ?, ?, ?, ?);
        """
        # File IDs should be 1, 2, 3
        self.db_manager.execute_query(instance_query, (TEST_HASH, file_path_1, file_path_1, 'A/F05.jpg', mtime_1))
        self.db_manager.execute_query(instance_query, (TEST_HASH, file_path_2, file_path_2, 'B/F05_copy.jpg', mtime_2))
        self.db_manager.execute_query(instance_query, (TEST_HASH, file_path_3, file_path_3, 'C/very_long_path_F05_copy.jpg', mtime_3))
        
        self.db_manager.close() # Close connection after setup

    def tearDown(self):
        """Teardown runs after each test."""
        if self.db_manager.conn:
             self.db_manager.close()

    def test_01_select_primary_copy(self):
        """Test the logic for selecting the primary copy based on mtime, then path."""
        with DatabaseManager(self.db_manager_path) as db:
            self.deduplicator.db = db
            primary_path, primary_file_id = self.deduplicator._select_primary_copy(TEST_HASH)
            expected_primary_path = "/path/to/source/A/F05.jpg" 
            self.assertEqual(primary_path, expected_primary_path, "The earliest date_modified file was not selected as primary.")
            self.assertEqual(primary_file_id, 1, "The primary file_id should be 1.")
            is_primary_flag = db.execute_query("SELECT is_primary FROM FilePathInstances WHERE file_id = ?;", (primary_file_id,))[0][0]
            self.assertEqual(is_primary_flag, 1, "The 'is_primary' flag was not set to 1 on the primary record.")
            duplicate_flags = db.execute_query("SELECT is_primary FROM FilePathInstances WHERE file_id IN (2, 3);")
            for flag in duplicate_flags:
                self.assertEqual(flag[0], 0, "Duplicate file instance was incorrectly marked as primary.")


    def test_02_calculate_final_path_format(self):
        """Test that the final path is generated in the correct output/YYYY/MM/HASH_ID.EXT format."""
        primary_path = "/path/to/source/A/F05.jpg"
        with DatabaseManager(self.db_manager_path) as db:
            query_primary_id = "SELECT file_id FROM FilePathInstances WHERE path = ?;"
            primary_file_id = db.execute_query(query_primary_id, (primary_path,))[0][0]
        
        ext = '.jpg'
        
        # The arguments must be correct to test the function
        final_path = self.deduplicator._calculate_final_path(
            primary_path, 
            TEST_HASH,           
            ext,                 
            primary_file_id      
        )
        
        expected_hash_id_part = f"{TEST_HASH[:12]}_{primary_file_id}{ext}"
        self.assertTrue(final_path.startswith(str(self.config_manager.OUTPUT_DIR)), "Final path does not start with the correct output directory.")
        self.assertIn("2020/01", final_path, "Final path does not contain the correct YYYY/MM directory structure derived from the date_best.")
        self.assertTrue(final_path.endswith(expected_hash_id_part), f"Final path does not end with the required HASH_FILEID.EXT format. Found: {final_path}. Expected ending: {expected_hash_id_part}")

    def test_03_run_deduplication_updates_new_path_id(self):
        """Test that the full deduplication run updates the new_path_id field."""
        # 1. Run the deduplication process
        self.deduplicator.run_deduplication()
        primary_file_id = 1
        
        with DatabaseManager(self.db_manager_path) as db:
            # 2. Verify that the new_path_id field was populated in MediaContent
            populated_count = db.execute_query("SELECT COUNT(*) FROM MediaContent WHERE new_path_id IS NOT NULL;")[0][0]
            self.assertEqual(populated_count, 1, "The new_path_id was not populated for the unique content record.")

            # 3. Retrieve the generated final path (which is the new_path_id field)
            final_path_db = db.execute_query("SELECT new_path_id FROM MediaContent WHERE content_hash = ?; ", (TEST_HASH,))[0][0]
            
            # 4. Check if the path was generated in the expected format (relative path)
            self.assertIn(f"{TEST_HASH[:12]}_{primary_file_id}.jpg", final_path_db, "The final path in MediaContent does not match the expected HASH_FILEID.EXT format.")
            self.assertIn("2020/01", final_path_db, "The final path in MediaContent does not contain the correct YYYY/MM structure.")
            
            # 5. Check the duplicate count
            self.assertEqual(self.deduplicator.duplicates_found, 2, "The duplicate counter did not correctly identify 2 duplicates.")


# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    
    # ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    
    args, unknown = parser.parse_known_args()
    if args.version:
        print_version_info(__file__, "Deduplicator Unit Tests")
        sys.exit(0)

    unittest.main(argv=sys.argv[:1] + unknown, exit=False)