import unittest
import sys
import argparse
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- BOOTSTRAP PATHS ---
# Add the parent directory (project root) to sys.path so we can import source classes
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Attempt imports from project root
try:
    from base_assets import AudioAsset, ImageAsset
    from video_asset import VideoAsset
    from asset_manager import AssetManager
except ImportError as e:
    print(f"Error: Could not import project modules. Ensure this file is in the 'test' folder. Details: {e}")
    sys.exit(1)

# --- PROJECT METADATA ---
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of TestAssetArchitecture suite.",
    "Added data cleaning validation for VideoAsset attributes.",
    "Implemented aspect ratio and JSON backpack verification.",
    "Integrated project-standard versioning and --version CLI support.",
    "CRITICAL: Added sys.path bootstrapping to resolve ModuleNotFoundError in subdirectories.",
    "Added Integration Test for AssetManager using Mock Database patterns.",
    "FEATURE: Added Test #04 for missing data resilience (Corrupt File handling)."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.7

class TestAssetArchitecture(unittest.TestCase):

    def test_01_video_asset_data_cleaning(self):
        """Verify that '1920 pixels' (string) correctly becomes 1920 (int)."""
        dummy_meta = {
            "Width": "1920 pixels",
            "Height": "1080",
            "Duration": "00:01:30.500",
            "Video_Format": "AVC"
        }
        asset = VideoAsset(Path("test.mp4"), dummy_meta)
        
        self.assertEqual(asset.width, 1920)
        self.assertEqual(asset.height, 1080)
        self.assertEqual(asset.video_codec, "AVC")

    def test_02_aspect_ratio_logic(self):
        """Verify the asset correctly identifies standard aspect ratios."""
        asset_16_9 = VideoAsset(Path("hd.mp4"), {"Width": "1920", "Height": "1080"})
        asset_4_3 = VideoAsset(Path("old.avi"), {"Width": "640", "Height": "480"})
        
        # Checking ratio values (Floating point comparison)
        self.assertAlmostEqual(asset_16_9.width / asset_16_9.height, 1.778, places=3)
        self.assertAlmostEqual(asset_4_3.width / asset_4_3.height, 1.333, places=3)

    def test_03_json_backpack_preservation(self):
        """Ensure all raw metadata is preserved in the extended JSON blob."""
        dummy_meta = {
            "Camera_Model": "Vintage Cam",
            "Width": "1280",
            "Custom_Tag": "SpecialValue"
        }
        asset = VideoAsset(Path("video.mp4"), dummy_meta)
        
        full_json = asset.get_full_json()
        decoded = json.loads(full_json)
        
        self.assertEqual(decoded["Camera_Model"], "Vintage Cam")
        self.assertEqual(decoded["Custom_Tag"], "SpecialValue")

    def test_04_missing_data_resilience(self):
        """Verify that the asset model handles empty dictionaries without crashing."""
        asset = VideoAsset(Path("corrupt_file.mp4"), {})
        
        self.assertEqual(asset.width, 0)
        self.assertEqual(asset.height, 0)
        self.assertEqual(asset.video_codec, "Unknown")
        self.assertEqual(asset.get_full_json(), "{}")

    @patch('asset_manager.get_video_metadata')
    def test_05_asset_manager_db_integration(self, mock_get_meta):
        """Verify AssetManager correctly updates the database via Mock objects."""
        # Setup Mock DB and Mock Metadata
        mock_db = MagicMock()
        mock_get_meta.return_value = {"Width": "1280", "Height": "720"}
        
        manager = AssetManager(mock_db)
        test_path = Path("my_video.mp4")
        test_hash = "abc123hash"

        # Execute
        manager.process_file(test_path, test_hash)

        # Assert: Verify the SQL UPDATE was called
        self.assertTrue(mock_db.execute_query.called)
        
        # Verify the arguments (params) passed to execute_query
        args, _ = mock_db.execute_query.call_args
        sql_query = args[0]
        params = args[1]
        
        self.assertIn("UPDATE MediaContent SET", sql_query)
        self.assertEqual(params[1], 1280)   # Width promoted to column
        self.assertIn('"Width": "1280"', params[6]) # Width also in JSON backpack
        self.assertEqual(params[7], test_hash) # WHERE clause hash match
        
    def test_06_audio_asset_parsing(self):
        """Verify AudioAsset handles duration and bitrates."""
        meta = {"Duration": "00:03:45", "Bit Rate": "320kbps"}
        asset = AudioAsset(Path("song.mp3"), meta)
        self.assertEqual(asset.duration, "00:03:45")
        self.assertEqual(asset.name, "song.mp3")

    def test_07_image_asset_cleaning(self):
        """Verify ImageAsset cleans dimensions and captures camera make."""
        meta = {"Width": "4000 px", "Height": "3000", "Make": "Sony"}
        asset = ImageAsset(Path("photo.jpg"), meta)
        self.assertEqual(asset.width, 4000)
        self.assertEqual(asset.camera, "Sony")
        self.assertIn('"Make": "Sony"', asset.get_full_json())
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asset Architecture Unit Tests")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    
    args, unknown = parser.parse_known_args()

    if args.version:
        # Try to use standard printer, fallback to manual if not found
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Asset Architecture Unit Tests")
        except ImportError:
            print(f"Asset Architecture Unit Tests v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    # Pass remaining args to unittest (e.g. -v for verbose test output)
    unittest.main(argv=[sys.argv[0]] + unknown)