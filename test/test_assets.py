# ==============================================================================
# File: test/test_assets.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [8]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.8
# ------------------------------------------------------------------------------
import unittest
import sys
import argparse
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- BOOTSTRAP PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from base_assets import AudioAsset, ImageAsset
    from video_asset import VideoAsset
    from asset_manager import AssetManager
except ImportError as e:
    print(f"Error: Could not import project modules. Details: {e}")
    sys.exit(1)

class TestAssetArchitecture(unittest.TestCase):

    def test_01_video_asset_data_cleaning(self):
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
        asset_16_9 = VideoAsset(Path("hd.mp4"), {"Width": "1920", "Height": "1080"})
        asset_4_3 = VideoAsset(Path("old.avi"), {"Width": "640", "Height": "480"})
        self.assertAlmostEqual(asset_16_9.width / asset_16_9.height, 1.778, places=3)
        self.assertAlmostEqual(asset_4_3.width / asset_4_3.height, 1.333, places=3)

    def test_03_json_backpack_preservation(self):
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
        asset = VideoAsset(Path("corrupt_file.mp4"), {})
        self.assertEqual(asset.width, 0)
        self.assertEqual(asset.height, 0)
        self.assertEqual(asset.video_codec, "Unknown")
        self.assertEqual(asset.get_full_json(), "{}")

    @patch('asset_manager.get_video_metadata')
    def test_05_asset_manager_db_integration(self, mock_get_meta):
        mock_db = MagicMock()
        mock_get_meta.return_value = {"Width": "1280", "Height": "720"}
        
        manager = AssetManager(mock_db)
        test_path = Path("my_video.mp4")
        test_hash = "abc123hash"

        manager.process_file(test_path, test_hash)

        self.assertTrue(mock_db.execute_query.called)
        args, _ = mock_db.execute_query.call_args
        params = args[1]
        
        # Current Schema order: date_best, width, height, duration, bitrate, video_codec, p_hash, extended_meta
        self.assertEqual(params[1], 1280)   # Width
        
        # FIX: The JSON backpack is now at index 7 (was 6) due to perceptual_hash
        self.assertIn('"Width": "1280"', params[7]) 
        self.assertEqual(params[8], test_hash) # Content Hash is last
        
    def test_06_audio_asset_parsing(self):
        meta = {"Duration": "00:03:45", "Bit Rate": "320kbps"}
        asset = AudioAsset(Path("song.mp3"), meta)
        self.assertEqual(asset.duration, "00:03:45")
        self.assertEqual(asset.name, "song.mp3")

    def test_07_image_asset_cleaning(self):
        meta = {"Width": "4000 px", "Height": "3000", "Make": "Sony"}
        asset = ImageAsset(Path("photo.jpg"), meta)
        self.assertEqual(asset.width, 4000)
        self.assertEqual(asset.camera, "Sony")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    args, unknown = parser.parse_known_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Asset Tests")
        except:
            print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    unittest.main(argv=[sys.argv[0]] + unknown)