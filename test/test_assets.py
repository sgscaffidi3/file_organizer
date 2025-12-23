import unittest
import sys
import argparse
import os
from pathlib import Path

# --- BOOTSTRAP PATHS ---
# Add the parent directory (project root) to sys.path so we can import our classes
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Now these imports will work
from video_asset import VideoAsset
from asset_manager import AssetManager

# --- PROJECT METADATA ---
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of TestAssetArchitecture suite.",
    "Added data cleaning validation for VideoAsset attributes.",
    "Implemented aspect ratio and JSON backpack verification.",
    "Integrated project-standard versioning and --version CLI support.",
    "CRITICAL FIX: Added sys.path manipulation to allow imports from parent directory."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.5

class TestAssetArchitecture(unittest.TestCase):
    # ... (Your test methods remain here) ...
    def test_01_video_asset_cleaning(self):
        dummy_meta = {"Width": "1920 pixels", "Height": "1080"}
        asset = VideoAsset(Path("test.mp4"), dummy_meta)
        self.assertEqual(asset.width, 1920)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unit Tests for Asset Architecture")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    
    # Check for version flag before letting unittest take over
    args, unknown = parser.parse_known_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Asset Architecture Unit Tests")
        sys.exit(0)

    # If not checking version, run the tests
    unittest.main(argv=[sys.argv[0]] + unknown)