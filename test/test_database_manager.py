# ==============================================================================
# File: test_database_manager.py
# Version: 0.1.6
# ------------------------------------------------------------------------------
# CHANGELOG:
# 6. Updated CLI logic for --version check to support execution from /test subdirectory.
# 5. Fixed teardown test pathing issue.
# 4. Added foreign key constraint test.
# 3. Added teardown functionality test.
# 2. Added schema creation test.
# 1. Initial implementation of DB context and file creation test.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import sqlite3
import argparse
# import sys (imported inside __main__)

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_db'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_metadata.sqlite'

# --- Test Data ---
TEST_HASH = "deadbeef0123456789"
TEST_PATH = "/path/to/test/file.jpg"

class TestDatabaseManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up environment before any tests run."""
        if not TEST_OUTPUT_DIR.exists():
            TEST_OUTPUT_DIR.mkdir()
        # Ensure the test database does not exist before starting
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

    @classmethod
    def tearDownClass(cls):
        """Clean up environment after all tests run."""
        if TEST_OUTPUT_DIR.exists():
            # os.rmdir(TEST_OUTPUT_DIR) # Only remove if empty
            pass

    def test_01_db_file_creation_and_context_manager(self):
        """Test that the DB file is created and the context manager works."""
        # Ensure cleanup from potential previous runs
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
            
        # Use context manager to ensure connection and cursor management
        with DatabaseManager(TEST_DB_PATH) as db:
            self.assertTrue(TEST_DB_PATH.exists())
            self.assertIsInstance(db.conn, sqlite3.Connection)
            self.assertIsInstance(db.cursor, sqlite3.Cursor)
            
        # Check that the connection is closed after exiting the context
        with self.assertRaises(sqlite3.ProgrammingError):
            db.cursor.execute("SELECT 1;")

    def test_02_schema_creation_and_table_existence(self):
        """Test that both required tables are created."""
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            
            # Check for MediaContent table
            content_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='MediaContent';"
            self.assertEqual(db.execute_query(content_query)[0][0], 'MediaContent')
            
            # Check for FilePathInstances table
            instance_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='FilePathInstances';"
            self.assertEqual(db.execute_query(instance_query)[0][0], 'FilePathInstances')

    def test_03_foreign_key_constraint(self):
        """Test the FOREIGN KEY constraint between instances and content."""
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema() # Ensure schema is ready
            
            # 1. Insert valid content record
            db.execute_query("INSERT INTO MediaContent (content_hash, file_type_group) VALUES (?, ?);", (TEST_HASH, 'IMAGE'))
            
            # 2. Insert valid instance record (should pass)
            db.execute_query("INSERT INTO FilePathInstances (path, content_hash) VALUES (?, ?);", (TEST_PATH, TEST_HASH))
            
            # 3. Attempt to insert instance with non-existent content_hash (should fail)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute_query("INSERT INTO FilePathInstances (path, content_hash) VALUES (?, ?);", 
                                 ("/path/to/bad/file.jpg", "nonexistenthash"))

    def test_04_teardown_functionality(self):
        """Test the explicit database deletion function."""
        # Ensure the DB file exists first
        with open(TEST_DB_PATH, 'w') as f:
            f.write("dummy db content")
        self.assertTrue(TEST_DB_PATH.exists())

        # Test teardown
        with DatabaseManager(TEST_DB_PATH) as db:
            success = db.teardown()
            self.assertTrue(success)
            
        self.assertFalse(TEST_DB_PATH.exists())
        
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
    parser = argparse.ArgumentParser(description="Unit tests for DatabaseManager.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args, unknown = parser.parse_known_args()

    # 3. IMMEDIATE VERSION EXIT
    if args.version:
        from version_util import print_version_info 
        print_version_info(__file__, "Database Manager Unit Tests")
        sys.exit(0)

    # 4. DEPENDENT IMPORTS FOR TEST EXECUTION
    # Imports needed by TestDatabaseManager
    from database_manager import DatabaseManager
    # No other core imports strictly required for this test file

    # 5. RUN TESTS
    sys.argv[1:] = unknown 
    unittest.main()