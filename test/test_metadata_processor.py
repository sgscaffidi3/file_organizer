# ==============================================================================
# File: test_file_scanner.py
# Version: 0.1.5
# ------------------------------------------------------------------------------
# CHANGELOG:
# 5. Updated CLI logic for --version check to support execution from /test subdirectory.
# 4. Added test for preventing duplicate path insertion.
# 3. Updated setUpClass to create dummy files for testing.
# 2. Added test for deduplication logic during scanning.
# 1. Initial implementation of hashing accuracy test.
# ------------------------------------------------------------------------------
import unittest
from pathlib import Path
import os
import argparse
import sys
# from version_util import print_version_info (Imported later)
# from database_manager import DatabaseManager (Imported later)
# from file_scanner import FileScanner (Imported later)
# from config_manager import ConfigManager (Imported later)


# Define test paths relative to the project root
TEST_OUTPUT_DIR = Path(__file__).parent.parent / 'test_output_scanner'
SOURCE_DIR = TEST_OUTPUT_DIR / 'source_media'
TEST_DB_PATH = TEST_OUTPUT_DIR / 'test_scanner_metadata.sqlite'

# --- Test Data ---
# Test file contents and known SHA256 hashes
FILE_A_CONTENT = b"This is file A."
FILE_A_HASH = "8ac38d8f078a632e8312017366d1f03f56d787754f49491753384226f30a9e99"

FILE_B_CONTENT = b"This is file B, a duplicate of A."
FILE_B_HASH = "6e5223c6f8744032d1f67f80470211910d54024b4570085a6a5789b5c32801e0"

class TestFileScanner(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Creates the test directory structure and dummy files once."""
        if not TEST_OUTPUT_DIR.exists():
            TEST_OUTPUT_DIR.mkdir()
        if not SOURCE_DIR.exists():
            SOURCE_DIR.mkdir()

        # Cleanup DB if it exists
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

        # Create dummy files for testing
        (SOURCE_DIR / 'file_a.txt').write_bytes(FILE_A_CONTENT)
        (SOURCE_DIR / 'file_b.txt').write_bytes(FILE_B_CONTENT)
        (SOURCE_DIR / 'file_a_duplicate.txt').write_bytes(FILE_A_CONTENT) # Duplicate of A

    @classmethod
    def tearDownClass(cls):
        """Cleans up the environment."""
        # We generally leave test output dirs for inspection unless cleanup is essential.
        pass

    def setUp(self):
        """Runs before every test: ensures a fresh DB state."""
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
        
        # We need a fresh DB and schema for every test to ensure isolation
        with DatabaseManager(TEST_DB_PATH) as db:
            db.create_schema()
            
        # Re-initialize ConfigManager for the scanner
        self.config_manager = ConfigManager()

    def test_01_hashing_accuracy(self):
        """Test that the SHA-256 hash calculation is correct."""
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, SOURCE_DIR, self.config_manager.FILE_GROUPS)
            
            # Test known content against known hash
            calculated_hash_a = scanner._calculate_hash(SOURCE_DIR / 'file_a.txt')
            self.assertEqual(calculated_hash_a, FILE_A_HASH)
            
            # Test different content
            calculated_hash_b = scanner._calculate_hash(SOURCE_DIR / 'file_b.txt')
            self.assertEqual(calculated_hash_b, FILE_B_HASH)

    def test_02_scan_and_insert_deduplication(self):
        """Test that duplicates result in one MediaContent entry but multiple FilePathInstances."""
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, SOURCE_DIR, self.config_manager.FILE_GROUPS)
            scanner.scan_and_insert()
            
            # Check MediaContent table (should have 2 unique files: A and B)
            content_count = db.execute_query("SELECT COUNT(*) FROM MediaContent;")[0][0]
            self.assertEqual(content_count, 2)
            
            # Check FilePathInstances table (should have 3 file paths: A, B, A_dup)
            instance_count = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
            self.assertEqual(instance_count, 3)
            
            # Check content_hash count for the duplicate file (should be 2 instances for FILE_A_HASH)
            instance_for_a = db.execute_query("SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = ?;", (FILE_A_HASH,))[0][0]
            self.assertEqual(instance_for_a, 2)

    def test_03_duplicate_path_insertion_is_ignored(self):
        """Test scanning the same path twice does not insert a second instance record."""
        with DatabaseManager(TEST_DB_PATH) as db:
            scanner = FileScanner(db, SOURCE_DIR, self.config_manager.FILE_GROUPS)
            
            # First scan (should insert 3 instances)
            scanner.scan_and_insert()
            instance_count_1 = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
            self.assertEqual(instance_count_1, 3)

            # Second scan (should find 3 files, but insert 0 new instances)
            scanner.scan_and_insert()
            instance_count_2 = db.execute_query("SELECT COUNT(*) FROM FilePathInstances;")[0][0]
            self.assertEqual(instance_count_2, 3)
            # The scanner's 'unique_instances_recorded' should be 0 on the second run
            self.assertEqual(scanner.unique_instances_recorded, 0)


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
    parser = argparse.ArgumentParser(description="Unit tests for MetadataProcessor.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args, unknown = parser.parse_known_args()

    # 3. IMMEDIATE VERSION EXIT
    if args.version:
        from version_util import print_version_info 
        print_version_info(__file__, "Metadata Processor Unit Tests")
        sys.exit(0) 

    # 4. DEPENDENT IMPORTS FOR TEST EXECUTION
    # Imports needed by TestMetadataProcessor
    from database_manager import DatabaseManager
    from file_scanner import FileScanner 
    from metadata_processor import MetadataProcessor 
    from config_manager import ConfigManager 

    # 5. RUN TESTS
    sys.argv[1:] = unknown 
    unittest.main()