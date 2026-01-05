# ==============================================================================
# File: test/test_metadata_processor.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 21
# Version: 0.3.21
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "FIX: Updated Test 02 to provide both width and height to mock skipped record.",
    "RELIABILITY: Maintained Deep Asset Check for required test files.",
    "SYNC: Matched all logic with MetadataProcessor v0.3.23."
]
# ------------------------------------------------------------------------------
import unittest, os, shutil, sqlite3, sys, argparse
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).parent.parent)) 
    from database_manager import DatabaseManager
    from metadata_processor import MetadataProcessor
    from config_manager import ConfigManager
except ImportError: pass

TEST_OUTPUT_DIR_NAME = "test_output_meta"
TEST_ASSETS_DIR = Path("test_assets")
REQUIRED_ASSETS = ["sample_valid.jpg", "sample_corrupt.jpg", "sample_video.mp4"]

def generate_test_data():
    """Bootstraps the test_assets directory with real media bytes."""
    print(f"Generating test data in {TEST_ASSETS_DIR}...")
    TEST_ASSETS_DIR.mkdir(exist_ok=True)
    jpeg_data = (
        b'\xff\xd8\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07'
        b'\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f'
        b'\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14'
        b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xdf'
        b'\xff\xd9'
    )
    (TEST_ASSETS_DIR / "sample_valid.jpg").write_bytes(jpeg_data)
    (TEST_ASSETS_DIR / "sample_corrupt.jpg").write_text("Not a real image file.")
    (TEST_ASSETS_DIR / "sample_video.mp4").touch() 
    print("Generation complete.")

class TestMetadataProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TEST_ASSETS_DIR.exists():
            print(f"\nERROR: Assets folder not found. Run: python {__file__} --gen_test_data\n")
            sys.exit(1)
        missing = [f for f in REQUIRED_ASSETS if not (TEST_ASSETS_DIR / f).exists()]
        if missing:
            print(f"\nERROR: Missing assets: {missing}. Run: python {__file__} --gen_test_data\n")
            sys.exit(1)

        cls.test_dir = Path(os.getcwd()) / TEST_OUTPUT_DIR_NAME
        cls.config_manager = ConfigManager(output_dir=cls.test_dir) 
        cls.db_path = str(cls.test_dir / 'metadata.sqlite')
        if cls.test_dir.exists(): shutil.rmtree(cls.test_dir)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager(cls.db_path); db.connect(); db.create_schema()
        for col in ["width INTEGER", "height INTEGER", "duration REAL", "bitrate INTEGER", "title TEXT"]:
            try: db.execute_query(f"ALTER TABLE MediaContent ADD COLUMN {col};")
            except: pass
        db.close()

    def setUp(self):
        self.db = DatabaseManager(self.db_path); self.db.connect()
        self.db.execute_query("DELETE FROM MediaContent;"); self.db.execute_query("DELETE FROM FilePathInstances;")
        self.processor = MetadataProcessor(self.db, self.config_manager)
        
        # 1. Valid
        p_valid = self.test_dir / "valid.jpg"
        shutil.copy(TEST_ASSETS_DIR / "sample_valid.jpg", p_valid)
        self._insert_record("h_valid", p_valid, 'IMAGE')

        # 2. Already processed (Must have width AND height to be skipped by query)
        p_skip = self.test_dir / "skipped.jpg"
        shutil.copy(TEST_ASSETS_DIR / "sample_valid.jpg", p_skip)
        self._insert_record("h_skip", p_skip, 'IMAGE', width=1, height=1)

        # 3. Missing
        p_miss = self.test_dir / "missing.jpg" 
        self._insert_record("h_miss", p_miss, 'IMAGE')

        # 4. Corrupt
        p_bad = self.test_dir / "bad.jpg"
        shutil.copy(TEST_ASSETS_DIR / "sample_corrupt.jpg", p_bad)
        self._insert_record("h_bad", p_bad, 'IMAGE')

    def _insert_record(self, c_hash, path, group, width=None, height=None):
        mq = "INSERT INTO MediaContent (content_hash, size, file_type_group, date_best, width, height) VALUES (?, 1, ?, '2023', ?, ?)"
        self.db.execute_query(mq, (c_hash, group, width, height))
        pq = "INSERT INTO FilePathInstances (content_hash, path, original_full_path, original_relative_path, is_primary) VALUES (?, ?, ?, ?, 1)"
        self.db.execute_query(pq, (c_hash, str(path), str(path), path.name))

    def tearDown(self):
        self.db.close()

    def test_01_standard_extraction(self):
        self.processor.process_metadata()
        self.assertGreaterEqual(self.processor.processed_count, 1)

    def test_02_skips_processed_via_query(self):
        records = self.processor._get_files_to_process()
        record_hashes = [r[0] for r in records]
        self.assertNotIn("h_skip", record_hashes)

    def test_03_missing_file_handling(self):
        self.processor.process_metadata()
        self.assertGreaterEqual(self.processor.skip_count, 1)

    def test_04_corruption_handling(self):
        self.processor.process_metadata()
        self.assertGreaterEqual(self.processor.skip_count, 1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_test_data', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    args, unknown = parser.parse_known_args()
    
    if args.version:
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Metadata Processor Tests")
        except:
            print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    if args.gen_test_data:
        generate_test_data(); sys.exit(0)
    unittest.main(argv=[sys.argv[0]] + unknown)