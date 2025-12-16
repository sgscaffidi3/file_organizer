# ==============================================================================
# File: test_database_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "Updated to use DatabaseManager's context manager functionality.",
    "Implemented a test for FOREIGN KEY constraint enforcement (test_03).",
    "Corrected test path definitions to use pathlib correctly relative to the project root.",
    "Added tearDown method to ensure the DB file is removed after every test method for strict isolation.",
    "CRITICAL FIX: Corrected tearDown method to access db_path using the class name (TestDatabaseManager.db_path) instead of self.db_path, resolving AttributeError errors.",
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
from version_util import print_version_info

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_db'
TEST_DB_FILENAME = 'test_db.sqlite'
TEST_DB_PATH = TEST_OUTPUT_DIR / TEST_DB_FILENAME

class TestDatabaseManager(unittest.TestCase):
    db_path: Path = TEST_DB_PATH

    @classmethod
    def setUpClass(cls):
        """Setup before any tests run."""
        # Ensure the test directory exists
        cls.db_path.parent.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        """Setup before each test: initialize the database."""
        if self.db_path.exists():
            os.remove(self.db_path)
            
        # Initialize with the schema
        with DatabaseManager(self.db_path) as db:
            db.create_schema()

    def tearDown(self):
        """Cleanup after each test: delete the database file."""
        if TestDatabaseManager.db_path.exists():
            os.remove(TestDatabaseManager.db_path)

    def test_01_connection_and_schema_creation(self):
        """Test that the DB file is created and schema exists."""
        # Setup in setUp() handles file creation and schema creation
        self.assertTrue(self.db_path.exists(), "Database file was not created.")
        
        with DatabaseManager(self.db_path) as db:
            # Check for MediaContent table
            table_check = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='MediaContent';")
            self.assertEqual(len(table_check), 1, "MediaContent table not found.")
            # Check for FilePathInstances table
            table_check = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='FilePathInstances';")
            self.assertEqual(len(table_check), 1, "FilePathInstances table not found.")

    def test_02_execute_query_insert_and_select(self):
        """Test basic INSERT and SELECT functionality."""
        content_hash = "TEST_HASH_12345"
        instance_path = "/a/b/c.jpg"
        
        with DatabaseManager(self.db_path) as db:
            # 1. Insert into MediaContent (parent record)
            insert_content_query = "INSERT INTO MediaContent (content_hash, size, file_type_group) VALUES (?, ?, ?);"
            db.execute_query(insert_content_query, (content_hash, 100, 'IMAGE'))
            
            # 2. Insert into FilePathInstances (child record)
            insert_instance_query = """
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path) 
            VALUES (?, ?, ?, ?);
            """
            db.execute_query(insert_instance_query, (content_hash, instance_path, instance_path, 'relative/c.jpg'))

            # 3. Select and verify
            select_query = "SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;"
            count = db.execute_query(select_query, (content_hash,))[0][0]
            self.assertEqual(count, 1, "Record count incorrect after insertion.")
            
    def test_03_foreign_key_constraint(self):
        """Test that insertion into FilePathInstances fails without MediaContent parent."""
        content_hash = "NON_EXISTENT_HASH"
        instance_path = "/d/e/f.mp4"
        
        with DatabaseManager(self.db_path) as db:
            insert_instance_query = """
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path) 
            VALUES (?, ?, ?, ?);
            """
            
            # Attempt to insert without parent content record
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute_query(insert_instance_query, (content_hash, instance_path, instance_path, 'relative/f.mp4'))

            # Manually insert into MediaContent (parent record)
            insert_content_query = """
            INSERT INTO MediaContent (content_hash, size, file_type_group) 
            VALUES (?, ?, ?);
            """
            db.execute_query(insert_content_query, (content_hash, 100, 'OTHER'))
            
            # Now, insertion into FilePathInstances should succeed
            db.execute_query(insert_instance_query, (content_hash, instance_path, instance_path, 'relative/f.mp4'))
            # If no exception is raised, it passes

    def test_04_teardown_functionality(self):
        """Test the explicit database deletion function."""
        # We rely on tearDown to clean up. This test ensures creation works.
        db_path = TestDatabaseManager.db_path
        
        # Ensure it exists before the test
        with DatabaseManager(db_path) as db:
            pass # Create the file
            
        self.assertTrue(db_path.exists(), "DB file was not created for test 04 setup.")


# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    #  ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for DatabaseManager.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        print_version_info(__file__, "DatabaseManager Unit Tests")
        sys.exit(0)
        
    unittest.main()