# ==============================================================================
# File: test_database_manager.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial implementation of database manager unit tests.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Updated tests to account for the new --teardown functionality.
# 5. Updated to use paths from ConfigManager instead of config.py.
# 6. Project name changed to "file_organizer" in descriptions.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import sqlite3
import argparse

from database_manager import DatabaseManager 
from version_util import print_version_info 

# Define a temporary test database path within a test-specific directory
TEST_DB_PATH = Path('./test_output/test_metadata.sqlite')

class TestDatabaseManager(unittest.TestCase):
    """Tests the functionality of the DatabaseManager class and the schema."""

    @classmethod
    def setUpClass(cls):
        # Create the parent directory for the test database if it doesn't exist
        TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        # Ensure the test database is clean before each test method runs
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

    def test_01_db_file_creation_and_context_manager(self):
        """Test that the DB file is created and the context manager works."""
        self.assertFalse(TEST_DB_PATH.exists())
        
        # Using the context manager to open and close connection
        with DatabaseManager(TEST_DB_PATH) as db:
            self.assertIsInstance(db.conn, sqlite3.Connection)
            self.assertTrue(TEST_DB_PATH.exists())
        
        # After exit, the file should still exist
        self.assertTrue(TEST_DB_PATH.exists())
        
    def test_02_schema_creation_and_table_existence(self):
        """Test that both required tables are created."""
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            # Query the master table to check for existence of our tables
            tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('MediaContent', 'FilePathInstances');")
            self.assertEqual(len(tables), 2)

    def test_03_foreign_key_constraint(self):
        """Test the FOREIGN KEY constraint between instances and content."""
        hash_val = 'a'*64
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            insert_instance_query = """
            INSERT INTO FilePathInstances (content_hash, original_full_path, original_relative_path) 
            VALUES (?, ?, ?);
            """
            # 1. Attempt insert before MediaContent exists (should fail)
            with self.assertRaises(sqlite3.IntegrityError): 
                 db.execute_query(insert_instance_query, (hash_val, 'path1', 'relpath1'))
                 
            # 2. Insert the required MediaContent entry
            db.execute_query("INSERT INTO MediaContent (content_hash, size) VALUES (?, 100);", (hash_val,))
            
            # 3. Attempt insert again (should succeed)
            db.execute_query(insert_instance_query, (hash_val, 'path2', 'relpath2'))
            
            count = db.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (hash_val,))[0][0]
            self.assertEqual(count, 1)

    def test_04_teardown_functionality(self):
        """Test the explicit database deletion function."""
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
        self.assertTrue(TEST_DB_PATH.exists())

        db_manager = DatabaseManager(TEST_DB_PATH)
        self.assertTrue(db_manager.teardown())
        self.assertFalse(TEST_DB_PATH.exists())
        self.assertFalse(db_manager.teardown()) # Should return False if the file is already gone

    def tearDown(self):
        # Clean up the database file after each test
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

    @classmethod
    def tearDownClass(cls):
        # Clean up the test output directory if empty
        if TEST_DB_PATH.parent.exists():
            try:
                os.rmdir(TEST_DB_PATH.parent)
            except OSError:
                # Ignore if directory is not empty (e.g., from other test remnants)
                pass 

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unit tests for DatabaseManager.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Database Manager Unit Tests")
    else:
        # Run tests if no specific arguments are given
        unittest.main()