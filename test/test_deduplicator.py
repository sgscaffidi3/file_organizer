# ==============================================================================
# File: test_deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    # ... (Previous changes omitted for brevity)
    "CRITICAL FIX: Modified setUp to instantiate DatabaseManager and pass the instance to Deduplicator, resolving the 'WindowsPath' object has no attribute 'execute_query' AttributeError. Added tearDown to close the connection.",
    "FINAL CRITICAL FIXES: - Explicitly added the 'new_path_id' column to MediaContent schema in setUpClass to resolve the sqlite3.OperationalError. - Added a 'date_modified' column to FilePathInstances schema in setUpClass to provide an accessible mtime source for the Deduplicator, resolving the TypeError caused by non-existent file path stat() calls returning None. - Updated setUp to populate the new 'date_modified' field with test mtimes.",
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
import datetime
# Runtime imports
# 1. PATH SETUP
sys.path.append(str(Path(__file__).resolve().parent.parent))
from database_manager import DatabaseManager
from deduplicator import Deduplicator 
from config_manager import ConfigManager
from version_util import print_version_info

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_dedupe'
TEST_DB_FILENAME = 'test_dedupe.sqlite'
TEST_DB_PATH = TEST_OUTPUT_DIR / TEST_DB_FILENAME

# --- Constants for Test Data ---
TEST_HASH = "AABBCCDDEEFF00112233445566778899"
TEST_CONFIG_DATA = {
    "organization": {
        "deduplication_strategy": "oldest_modified_date",
        "date_format": "%Y/%m/%d"
    }
}
# Define the date modified strings for comparison (ISO format)
# The first one (A) should be the oldest and thus the primary
DATE_A = datetime.datetime(2020, 1, 1, 10, 0, 0).isoformat()
DATE_B = datetime.datetime(2020, 1, 1, 11, 0, 0).isoformat()
DATE_C = datetime.datetime(2020, 1, 1, 12, 0, 0).isoformat()


class TestDeduplicator(unittest.TestCase):
    db_manager_path: Path = TEST_DB_PATH
    
    @classmethod
    def setUpClass(cls):
        """Setup before any tests run."""
        # Ensure test directory exists
        cls.db_manager_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy config file
        config_path = cls.db_manager_path.parent / 'dummy_config.json'
        with open(config_path, 'w') as f:
            import json
            json.dump({"organization": TEST_CONFIG_DATA['organization'], 
                       "paths": {"output_directory": str(cls.db_manager_path.parent)}}, f)
        
        # Dynamically create a ConfigManager instance with the dummy config
        cls.config_manager = ConfigManager(config_path)

        # CRITICAL: Define a custom schema for tests that includes all fields used by the Deduplicator
        temp_db = DatabaseManager(cls.db_manager_path)
        
        content_table_sql = """
        CREATE TABLE IF NOT EXISTS MediaContent (
            content_hash TEXT PRIMARY KEY, 
            new_path_id TEXT, -- CRITICAL: Added for Deduplicator
            size INTEGER, 
            file_type_group TEXT
        );
        """
        instance_table_sql = """
        CREATE TABLE IF NOT EXISTS FilePathInstances (
            file_id INTEGER PRIMARY KEY, 
            content_hash TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL, 
            original_full_path TEXT NOT NULL,
            original_relative_path TEXT NOT NULL,
            date_modified TEXT, -- CRITICAL: Added for Deduplicator
            is_primary BOOLEAN DEFAULT 0
        );
        """
        try:
            temp_db.conn = sqlite3.connect(cls.db_manager_path)
            temp_db.conn.execute(content_table_sql)
            temp_db.conn.execute(instance_table_sql)
            temp_db.conn.commit()
        except Exception as e:
            print(f"Error setting up test schema: {e}")
        finally:
            temp_db.conn.close()

    @classmethod
    def tearDownClass(cls):
        """Cleanup after all tests run."""
        shutil.rmtree(cls.db_manager_path.parent, ignore_errors=True)

    def setUp(self):
        """Setup before each test: insert test data."""
        # 1. Use a fresh DB connection for each test
        self.db_manager = DatabaseManager(self.db_manager_path)
        self.db_manager.conn = sqlite3.connect(self.db_manager_path)
        self.db_manager.__enter__() # Manually enter context
        
        # 2. Clear existing data
        self.db_manager.execute_query("DELETE FROM MediaContent;")
        self.db_manager.execute_query("DELETE FROM FilePathInstances;")
        
        # 3. Insert one unique content record
        content_query = "INSERT INTO MediaContent (content_hash, size, file_type_group) VALUES (?, ?, ?);"
        self.db_manager.execute_query(content_query, (TEST_HASH, 100, 'IMAGE'))
        
        # 4. Insert three instances of that content (duplicates)
        instance_query = """
        INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_modified) 
        VALUES (?, ?, ?, ?, ?);
        """
        # Instance A (Oldest - should be primary)
        self.db_manager.execute_query(instance_query, (TEST_HASH, '/path/to/a.jpg', '/path/to/a.jpg', 'a.jpg', DATE_A))
        # Instance B (Middle)
        self.db_manager.execute_query(instance_query, (TEST_HASH, '/path/to/b.jpg', '/path/to/b.jpg', 'b.jpg', DATE_B))
        # Instance C (Newest)
        self.db_manager.execute_query(instance_query, (TEST_HASH, '/path/to/c.jpg', '/path/to/c.jpg', 'c.jpg', DATE_C))

        # 5. Commit the setup data
        self.db_manager.conn.commit()
        
        # 6. Instantiate the Deduplicator
        self.deduplicator = Deduplicator(self.db_manager, self.config_manager)

    def tearDown(self):
        """Cleanup after each test: close DB connection."""
        self.db_manager.__exit__(None, None, None)

    def test_01_oldest_modified_strategy(self):
        """Test that the oldest file is selected as the primary copy (F06)."""
        
        primary_path, _ = self.deduplicator._select_primary_copy(TEST_HASH)
        
        # Path A is the oldest and should be selected
        expected_path = Path('/path/to/a.jpg').resolve()
        
        self.assertEqual(primary_path.resolve(), expected_path, "The oldest file (a.jpg) was not selected as primary.")
        
    def test_02_calculate_final_path_format(self):
        """Test that the final path is generated in the correct format (F05)."""
        
        # Simulate the primary copy being selected
        primary_path = Path('/path/to/a.jpg').resolve()
        # file_id 1 is the primary copy's file_id (from setUp insertion order)
        file_id = 1 
        
        final_path = self.deduplicator._calculate_final_path(primary_path, file_id, TEST_HASH)
        
        # Expected format: {OUTPUT_DIR}/YYYY/MM/DD/HASH_ID.EXT
        # OUTPUT_DIR is test_output_dedupe (parent of the DB file)
        # Date is 2020/01/01
        # HASH is TEST_HASH[:12] + file_id 
        
        # Ensure it contains the output dir
        self.assertIn(str(TEST_OUTPUT_DIR), str(final_path))
        
        # Ensure it contains the date and ID
        expected_substring = f"2020/01/01/{TEST_HASH[:12]}_{file_id}.jpg"
        self.assertIn(expected_substring, str(final_path))
        
        # Final path must be an absolute Path object
        self.assertTrue(isinstance(final_path, Path))
        self.assertTrue(final_path.is_absolute())


    def test_03_run_deduplication_updates_db(self):
        """Test that running the full deduplication updates the new_path_id field."""
        
        # 1. Run the deduplication process
        self.deduplicator.run_deduplication()
        
        with DatabaseManager(self.db_manager_path) as db:
            # 2. Verify that the new_path_id field was populated in MediaContent
            populated_count = db.execute_query("SELECT COUNT(*) FROM MediaContent WHERE new_path_id IS NOT NULL;")[0][0]
            self.assertEqual(populated_count, 1, "The new_path_id was not populated for the unique content record.")

            # 3. Retrieve the generated final path (which is the new_path_id field)
            final_path_db = db.execute_query("SELECT new_path_id FROM MediaContent WHERE content_hash = ?;", (TEST_HASH,))[0][0]
            
            # 4. Check if the path was generated in the expected format (relative path)
            # The primary copy's file_id is 1
            self.assertIn(f"{TEST_HASH[:12]}_1.jpg", final_path_db)
            self.assertIn("2020/01/01", final_path_db)

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    
    # ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        print_version_info(__file__, "Deduplicator Unit Tests")
        sys.exit(0)
        
    unittest.main()