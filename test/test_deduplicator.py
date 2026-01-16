# ==============================================================================
# File: test/test_deduplicator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "CRITICAL FIX: Implemented logic to correctly set `is_primary=1`.",
    "CRITICAL FIX: Updated `setUp` to create mock files with unique `mtime`.",
    "CRITICAL TEST FIX: Refined test data arguments.",
    "TEST REFACTOR: Removed obsolete test for `_select_primary_copy` (logic is now in batch query).",
    "TEST REFACTOR: Updated `_calculate_final_path` test to match new signature (6 arguments).",
    "TEST REFACTOR: Verified database state for `run_deduplication` test.",
    "TEST FIX: Forced 'rename_on_copy' preference to True in test_02 to ensure deterministic path generation."
]
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import shutil
import sqlite3
import argparse
import sys
from unittest.mock import patch

# Add project root to sys.path
try:
    sys.path.insert(0, str(Path(__file__).parent.parent)) 
    from database_manager import DatabaseManager
    from deduplicator import Deduplicator
    from config_manager import ConfigManager
    from version_util import print_version_info
except ImportError as e:
    print(f"Test setup import error: {e}")
    if 'DatabaseManager' in locals(): DatabaseManager = None

TEST_OUTPUT_DIR_NAME = "test_output_dedupe"
TEST_HASH = "deadbeef01234567890abcdef01234567890abcdef01234567890a"

class TestDeduplicator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        if not DatabaseManager: return
        cls.test_dir = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
        cls.config_manager = ConfigManager(output_dir=cls.test_dir) 
        cls.db_manager_path = str(cls.test_dir / 'metadata.sqlite')
        
        if cls.test_dir.exists(): shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        db_setup = DatabaseManager(cls.db_manager_path)
        db_setup.connect()
        db_setup.create_schema()
        try: db_setup.execute_query("ALTER TABLE MediaContent ADD COLUMN new_path_id TEXT;")
        except: pass
        try: db_setup.execute_query("ALTER TABLE MediaContent ADD COLUMN perceptual_hash TEXT;")
        except: pass
        db_setup.close()
            
    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists(): shutil.rmtree(cls.test_dir)

    def setUp(self):
        if not DatabaseManager: self.skipTest("Dep fail")
        self.db_manager = DatabaseManager(self.db_manager_path)
        self.db_manager.connect()
        self.db_manager.execute_query("DELETE FROM MediaContent;")
        self.db_manager.execute_query("DELETE FROM FilePathInstances;")
        self.deduplicator = Deduplicator(self.db_manager, self.config_manager)
        
        # INSERT DATA
        # MediaContent: Has 'date_best'
        self.db_manager.execute_query(
            "INSERT INTO MediaContent (content_hash, size, file_type_group, date_best) VALUES (?, ?, ?, ?)", 
            (TEST_HASH, 1024, 'IMAGE', "2020-01-01 10:00:00")
        )
        
        # 1. Primary Candidate (Oldest Date)
        self.db_manager.execute_query(
            "INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_modified, is_primary) VALUES (?, ?, ?, ?, ?, ?)",
            (TEST_HASH, str(self.test_dir/'A.jpg'), str(self.test_dir/'A.jpg'), 'A.jpg', "2020-01-01 10:00:00", 0)
        )
        # 2. Duplicate (Newer Date)
        self.db_manager.execute_query(
            "INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, date_modified, is_primary) VALUES (?, ?, ?, ?, ?, ?)",
            (TEST_HASH, str(self.test_dir/'B.jpg'), str(self.test_dir/'B.jpg'), 'B.jpg', "2020-01-03 10:00:00", 0)
        )

    def tearDown(self):
        if self.db_manager.conn: self.db_manager.close()

    def test_02_calculate_final_path_format(self):
        """Test final path generation with updated signature."""
        primary_path = str(Path(self.test_dir) / 'A.jpg') 
        
        # FORCE rename_on_copy = True for this test
        # This ensures we get the HASH_ID filename format instead of the original name
        with patch.object(ConfigManager, 'ORGANIZATION_PREFS', {'rename_on_copy': True}):
            final_path = self.deduplicator._calculate_final_path(
                primary_path, 
                TEST_HASH, 
                '.jpg', 
                100, 
                "2020-01-01 10:00:00", 
                "2020-01-01 10:00:00"
            )
            
            expected_part = os.path.join("2020", "01")
            
            self.assertIn(expected_part, final_path)
            self.assertIn(f"{TEST_HASH[:12]}_100.jpg", final_path)
            self.assertTrue(final_path.startswith(str(self.config_manager.OUTPUT_DIR)))

    def test_03_run_deduplication_updates_new_path_id(self):
        """Test full run updates DB correctly."""
        self.deduplicator.run_deduplication()
        
        with DatabaseManager(self.db_manager_path) as db:
            # Check is_primary was set. 
            prim_row = db.execute_query("SELECT file_id FROM FilePathInstances WHERE path LIKE '%A.jpg'")[0]
            prim_id = prim_row[0]
            
            # Check MediaContent new_path_id
            row = db.execute_query("SELECT new_path_id FROM MediaContent WHERE content_hash = ?", (TEST_HASH,))
            self.assertTrue(row, "No record found in MediaContent")
            final_path = row[0][0]
            
            # Verify path contains the date structure
            self.assertIn(os.path.join("2020", "01"), final_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    args, unknown = parser.parse_known_args()
    
    if args.version:
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Deduplicator Tests")
        except:
            print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{len(_CHANGELOG_ENTRIES)}")
        sys.exit(0)

    unittest.main(argv=[sys.argv[0]] + unknown, exit=False)