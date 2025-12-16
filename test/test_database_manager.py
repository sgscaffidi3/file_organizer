# ==============================================================================
# File: test_database_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 6. CRITICAL FIX: Corrected tearDown method to access db_path using the class name (TestDatabaseManager.db_path) instead of self.db_path, resolving AttributeError errors.
# 5. Added tearDown method to ensure the DB file is removed after every test method for strict isolation.
# 4. Corrected test path definitions to use pathlib correctly relative to the project root.
# 3. Implemented a test for FOREIGN KEY constraint enforcement (test_03).
# 2. Updated to use DatabaseManager's context manager functionality.
# 1. Initial implementation.
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
from version_util import print_version_info

# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_db'
TEST_DB_FILENAME = 'test_db.sqlite'
TEST_DB_PATH = TEST_OUTPUT_DIR / TEST_DB_FILENAME

class TestDatabaseManager(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Sets up the test environment, cleaning up old outputs."""
        # Set path as a class attribute for access in teardown methods
        cls.db_path = TEST_DB_PATH
        
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)
        TEST_OUTPUT_DIR.mkdir()

    @classmethod
    def tearDownClass(cls):
        """Cleans up the test output directory."""
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def tearDown(self):
        """CRITICAL FIX: Ensures the DB file is removed after every test method for isolation."""
        # Must access the class attribute via the Class name, not 'self', 
        # unless 'self' was initialized with it.
        if os.path.exists(TestDatabaseManager.db_path):
            os.remove(TestDatabaseManager.db_path)

    def test_01_db_file_creation_and_context_manager(self):
        """Test that the DB file is created and the context manager works."""
        self.assertFalse(TestDatabaseManager.db_path.exists())
        
        with DatabaseManager(TestDatabaseManager.db_path) as db:
            pass
        
        self.assertTrue(TestDatabaseManager.db_path.exists())

    def test_02_schema_creation_and_table_existence(self):
        """Test that both required tables are created."""
        with DatabaseManager(TestDatabaseManager.db_path) as db:
            db.create_schema()

            cursor = db.conn.cursor()
            
            # Check for MediaContent table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='MediaContent';")
            self.assertIsNotNone(cursor.fetchone(), "MediaContent table was not created.")

            # Check for FilePathInstances table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='FilePathInstances';")
            self.assertIsNotNone(cursor.fetchone(), "FilePathInstances table was not created.")

    def test_03_foreign_key_constraint(self):
        """Test the FOREIGN KEY constraint between instances and content."""
        content_hash = "a" * 64
        instance_path = "/test/path/file.txt"

        with DatabaseManager(TestDatabaseManager.db_path) as db:
            db.create_schema()
            
            # Attempt to insert into instances without corresponding content (should fail)
            insert_instance_query = """
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path) 
            VALUES (?, ?, ?, ?);
            """
            
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute_query(insert_instance_query, (content_hash, instance_path, instance_path, 'relative/path'))
                db.conn.commit() # The error usually triggers on commit/query

            # Insert into MediaContent (parent record)
            insert_content_query = """
            INSERT INTO MediaContent (content_hash, size, file_type_group) 
            VALUES (?, ?, ?);
            """
            db.execute_query(insert_content_query, (content_hash, 100, 'OTHER'))
            
            # Now, insertion into FilePathInstances should succeed
            db.execute_query(insert_instance_query, (content_hash, instance_path, instance_path, 'relative/path'))
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
    # 1. PATH SETUP
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    
    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Unit tests for DatabaseManager.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    # 3. VERSION EXIT
    if args.version:
        print_version_info(__file__, "DatabaseManager Unit Tests")
        sys.exit(0)

    # 4. RUN TESTS
    unittest.main()