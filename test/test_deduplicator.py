# ==============================================================================
# File: test_deduplicator.py
# Version: 0.1.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial implementation of primary selection and path calculation tests.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
from typing import Dict
import argparse
import sys
import datetime

# --- Test Data ---
KNOWN_HASH = "b700b80e9cde78a230758410d32c918360d00f606775f0a282f6412c98d7f724" # Dummy JPG hash
DATE_BEST = "2020-11-15"
FILE_TYPE_GROUP = "IMAGE"

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_dedupe'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_dedupe.sqlite'

# Instance path creation times (for KEEP_OLDEST test)
MOCK_TIME_OLDEST = 1577836800.0  # 2020-01-01
MOCK_TIME_NEWEST = 1609459200.0  # 2021-01-01


class TestDeduplicator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Creates the test directory and cleans up DB."""
        if not TEST_OUTPUT_DIR.exists():
            TEST_OUTPUT_DIR.mkdir()

    def setUp(self):
        """Runs before every test: ensures a fresh DB state with test data."""
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
        
        # Re-initialize ConfigManager
        self.config_manager = ConfigManager()

        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            
            # Insert content record
            db.execute_query("""
                INSERT INTO MediaContent (content_hash, file_type_group, date_best)
                VALUES (?, ?, ?);
            """, (KNOWN_HASH, FILE_TYPE_GROUP, DATE_BEST))

            # Insert two instance records (duplicates) with different C-times
            # 1. OLDEST copy (should be the primary)
            db.execute_query("""
                INSERT INTO FilePathInstances (path, content_hash, creation_time, file_id) 
                VALUES (?, ?, ?, ?);
            """, ("/source/old_copy.jpg", KNOWN_HASH, MOCK_TIME_OLDEST, 1000))
            
            # 2. NEWEST copy
            db.execute_query("""
                INSERT INTO FilePathInstances (path, content_hash, creation_time, file_id) 
                VALUES (?, ?, ?, ?);
            """, ("/source/new_copy.jpg", KNOWN_HASH, MOCK_TIME_NEWEST, 1001))

    def test_01_primary_selection_keep_oldest(self):
        """Test that KEEP_OLDEST strategy selects the file with the oldest modification time."""
        # ConfigManager default is KEEP_OLDEST
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            
            primary_path = dedupe._select_primary_copy(KNOWN_HASH)
            
            self.assertEqual(primary_path, "/source/old_copy.jpg")

    def test_02_final_path_calculation(self):
        """Test that the standardized output path is calculated correctly."""
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            
            # Mock required metadata
            metadata = {
                'content_hash': KNOWN_HASH,
                'date_best': DATE_BEST,
                'file_type_group': FILE_TYPE_GROUP,
                'primary_path_id': 1000, # Oldest copy
                'primary_path': "/source/old_copy.jpg"
            }
            
            final_path = dedupe._calculate_final_path(metadata)
            
            # Expected format: GROUP/YEAR/DATE/HASH_FILE_ID.EXT
            # Expected: IMAGE/2020/2020-11-15/b700b80e9cde_1000.jpg
            expected_prefix = f"{FILE_TYPE_GROUP}/{DATE_BEST[:4]}/{DATE_BEST}"
            
            self.assertTrue(final_path.startswith(expected_prefix))
            self.assertTrue(final_path.endswith(f"_{metadata['primary_path_id']}.jpg"))

    def test_03_run_deduplication_updates_db(self):
        """Test that running the full deduplication updates the new_path_id field."""
        with DatabaseManager(TEST_DB_PATH) as db:
            dedupe = Deduplicator(db, self.config_manager)
            
            dedupe.run_deduplication()
            
            # Query the database for the new_path_id
            query = "SELECT new_path_id FROM MediaContent WHERE content_hash = ?;"
            result = db.execute_query(query, (KNOWN_HASH,))[0][0]
            
            self.assertIsNotNone(result)
            
            # Check the path components for OS-agnostic testing
            result_path = Path(result)
            
            # 1. Check if the date components are correct (IMAGE/2020/2020-11-15)
            expected_date_part = Path("IMAGE/2020/2020-11-15")
            
            # Check if the result path contains the expected parts
            # We check the first 3 parts of the result path against the expected parts
            self.assertTrue(result_path.parts[:3] == expected_date_part.parts, 
                            f"Expected path prefix {expected_date_part.parts} not found in {result_path.parts}")
            
            # 2. Check the extension
            self.assertTrue(result.endswith(".jpg"))
            
            self.assertEqual(dedupe.processed_count, 1) # One unique hash was processed


# --- CLI EXECUTION LOGIC ---
# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    import argparse
    import sys
    from pathlib import Path
    
    # 1. TEMPORARILY ADD PATH FOR VERSION_UTIL IMPORT
    project_root = str(Path(__file__).resolve().parent.parent)
    sys.path.append(project_root)

    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for Deduplicator.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args, unknown = parser.parse_known_args()

    # 3. IMMEDIATE VERSION EXIT
    if args.version:
        from version_util import print_version_info 
        print_version_info(__file__, "Deduplicator Unit Tests")
        sys.exit(0) 

    # 4. DEPENDENT IMPORTS FOR TEST EXECUTION
    # Imports needed by TestDeduplicator
    from database_manager import DatabaseManager
    from deduplicator import Deduplicator 
    from config_manager import ConfigManager 

    # 5. RUN TESTS
    sys.argv[1:] = unknown 
    unittest.main()