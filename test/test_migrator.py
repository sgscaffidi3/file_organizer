# ==============================================================================
# File: test/test_migrator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of TestMigrator suite.",
    "Implemented Dry-Run safety verification (T04).",
    "Implemented Live Execution verification (F07).",
    "Implemented Destination Collision verification.",
    "Integrated standard CLI versioning support."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.5
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import shutil
import os
import sys
import argparse
import time

# --- BOOTSTRAP PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database_manager import DatabaseManager
from migrator import Migrator
from config_manager import ConfigManager

TEST_OUTPUT_DIR_NAME = "test_output_migrator"
TEST_WORK_DIR = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
TEST_DB_PATH = TEST_WORK_DIR / "metadata.sqlite"
SOURCE_DIR = TEST_WORK_DIR / "source"
OUTPUT_DIR = TEST_WORK_DIR / "output"

class TestMigrator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Setup runs once for the class: creates the test environment."""
        # 1. Clean Environment
        if TEST_WORK_DIR.exists():
            shutil.rmtree(TEST_WORK_DIR)
        TEST_WORK_DIR.mkdir(parents=True, exist_ok=True)
        SOURCE_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)

        # 2. Initialize ConfigManager (Pointing to our test output)
        cls.config_manager = ConfigManager(output_dir=OUTPUT_DIR)

        # 3. Create Schema
        db = DatabaseManager(str(TEST_DB_PATH))
        with db:
            db.create_schema()
            # Manually ensure new_path_id column exists (if not in create_schema yet)
            try:
                db.execute_query("ALTER TABLE MediaContent ADD COLUMN new_path_id TEXT;")
            except: 
                pass

    def setUp(self):
        """Runs before every test."""
        # Reset DB Data
        self.db = DatabaseManager(str(TEST_DB_PATH))
        self.db.connect()
        self.db.execute_query("DELETE FROM MediaContent;")
        self.db.execute_query("DELETE FROM FilePathInstances;")

        # Create Dummy File
        self.test_file_name = "test_image.jpg"
        self.source_file_path = SOURCE_DIR / self.test_file_name
        with open(self.source_file_path, "wb") as f:
            f.write(b"DATA_MIGRATION_TEST")

        # Insert Mock DB Record (Post-Deduplication State)
        # Content Hash: AAAA...
        # New Path ID: 2025/01/AAAA_1.jpg
        self.content_hash = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        self.relative_dest_path = "2025/01/AAAA_1.jpg"
        self.full_dest_path = OUTPUT_DIR / self.relative_dest_path

        # Insert Parent
        self.db.execute_query("""
            INSERT INTO MediaContent (content_hash, size, file_type_group, new_path_id)
            VALUES (?, 10, 'IMAGE', ?)
        """, (self.content_hash, self.relative_dest_path))

        # Insert Instance
        self.db.execute_query("""
            INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path)
            VALUES (?, ?, ?, ?)
        """, (self.content_hash, str(self.source_file_path), str(self.source_file_path), self.test_file_name))

        # Init Migrator
        self.migrator = Migrator(self.db, self.config_manager)

    def tearDown(self):
        self.db.close()
        # Clean up output dir for next test
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir()

    def test_01_dry_run_safety(self):
        """Verify DRY_RUN_MODE=True copies NOTHING."""
        # Force Dry Run
        self.migrator.dry_run = True
        
        self.migrator.run_migration()

        self.assertTrue(self.source_file_path.exists(), "Source file should still exist.")
        self.assertFalse(self.full_dest_path.exists(), "Destination file SHOULD NOT exist in Dry Run.")
        self.assertEqual(self.migrator.files_copied, 1, "Dry run should report 'copied' (simulated) count.")

    def test_02_live_migration(self):
        """Verify DRY_RUN_MODE=False copies the file."""
        # Force Live Run
        self.migrator.dry_run = False
        
        self.migrator.run_migration()

        self.assertTrue(self.source_file_path.exists(), "Source file should be preserved (Copy, not Move).")
        self.assertTrue(self.full_dest_path.exists(), "Destination file should exist.")
        
        # Verify Content
        with open(self.full_dest_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"DATA_MIGRATION_TEST")

    def test_03_collision_handling(self):
        """Verify existing destination file is NOT overwritten."""
        self.migrator.dry_run = False
        
        # Pre-create the destination with DIFFERENT content
        self.full_dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.full_dest_path, "wb") as f:
            f.write(b"EXISTING_DATA_DO_NOT_TOUCH")
            
        self.migrator.run_migration()
        
        # Verify content was NOT changed
        with open(self.full_dest_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"EXISTING_DATA_DO_NOT_TOUCH")
        self.assertEqual(self.migrator.files_skipped, 1)

    def test_04_missing_source_handling(self):
        """Verify missing source file does not crash the system."""
        self.migrator.dry_run = False
        
        # Delete the source file physically
        os.remove(self.source_file_path)
        
        try:
            self.migrator.run_migration()
        except Exception as e:
            self.fail(f"Migrator crashed on missing source file: {e}")
            
        self.assertEqual(self.migrator.files_skipped, 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrator Unit Tests")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    
    args, unknown = parser.parse_known_args()

    if args.version:
        # Try to use standard printer, fallback to manual if not found
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Migrator Unit Tests")
        except ImportError:
            print(f"Migrator Unit Tests v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    unittest.main(argv=[sys.argv[0]] + unknown)