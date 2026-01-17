# ==============================================================================
# File: test/test_type_coverage.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_PATCH_VERSION = 2
# Version: 0.7.2
# ------------------------------------------------------------------------------
# CHANGELOG:
_REL_CHANGES = [5]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
# ------------------------------------------------------------------------------
import unittest
import sys
import shutil
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# --- BOOTSTRAP PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from libraries_helper import get_video_metadata

TEST_OUTPUT_DIR = Path(os.getcwd()) / "test_output_coverage"

class TestTypeCoverage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if TEST_OUTPUT_DIR.exists(): shutil.rmtree(TEST_OUTPUT_DIR)
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _create_dummy_file(self, filename):
        path = TEST_OUTPUT_DIR / filename
        if not path.exists():
            with open(path, "wb") as f: f.write(b"DUMMY")
        return path

    def _test_with_mock(self, ext, expected_key, mock_data):
        """Helper to run test with mocked library calls."""
        fpath = self._create_dummy_file(f"test.{ext}")
        
        # We patch the specific classes used in libraries_helper
        with patch('libraries_helper.MediaInfo.parse') as mock_mi, \
             patch('libraries_helper.Image.open') as mock_img, \
             patch('libraries_helper.rawpy.imread') as mock_raw:
            
            # --- Setup MediaInfo Mock (CRITICAL FIX) ---
            # libraries_helper iterates over tracks.
            # It checks track.track_type and then calls track.to_data().
            
            # Mock General Track
            track_general = MagicMock()
            track_general.track_type = "General"
            track_general.to_data.return_value = {"Format": "TestFormat", "Duration": 5000}
            track_general.duration = 5000 # accessed as attribute in helper
            
            # Mock Video Track
            track_video = MagicMock()
            track_video.track_type = "Video"
            track_video.to_data.return_value = {"Width": 1920, "Height": 1080}
            track_video.width = 1920
            track_video.height = 1080
            
            # Mock Audio Track
            track_audio = MagicMock()
            track_audio.track_type = "Audio"
            track_audio.to_data.return_value = {"Bit_Rate": 320000}
            track_audio.bit_rate = 320000

            mock_mi_obj = MagicMock()
            # Return list of tracks
            mock_mi_obj.tracks = [track_general, track_video, track_audio]
            mock_mi.return_value = mock_mi_obj
            
            # --- Setup Pillow Mock ---
            mock_img_obj = MagicMock()
            mock_img_obj.width = 800
            mock_img_obj.height = 600
            mock_img_obj.format = "JPEG"
            mock_img_obj.getexif.return_value = {}
            mock_img.return_value.__enter__.return_value = mock_img_obj
            
            # Execute
            meta = get_video_metadata(fpath)
            
            # Assert
            self.assertTrue(expected_key in meta, f"[{ext}] Missing {expected_key}. Got: {list(meta.keys())}")

    # ==========================================================================
    # GROUP 1: IMAGES (Pillow / Rawpy)
    # ==========================================================================
    def test_fmt_jpg(self): self._test_with_mock("jpg", "Width", {})
    def test_fmt_jpeg(self): self._test_with_mock("jpeg", "Width", {})
    def test_fmt_png(self): self._test_with_mock("png", "Width", {})
    def test_fmt_gif(self): self._test_with_mock("gif", "Width", {})
    def test_fmt_bmp(self): self._test_with_mock("bmp", "Width", {})
    def test_fmt_tiff(self): self._test_with_mock("tiff", "Width", {})
    def test_fmt_webp(self): self._test_with_mock("webp", "Width", {})
    def test_fmt_heic(self): self._test_with_mock("heic", "Width", {})
    def test_fmt_heif(self): self._test_with_mock("heif", "Width", {})
    # RAW
    def test_fmt_cr2(self): self._test_with_mock("cr2", "Width", {})
    def test_fmt_nef(self): self._test_with_mock("nef", "Width", {})
    def test_fmt_arw(self): self._test_with_mock("arw", "Width", {})
    def test_fmt_dng(self): self._test_with_mock("dng", "Width", {})
    def test_fmt_orf(self): self._test_with_mock("orf", "Width", {})

    # ==========================================================================
    # GROUP 2: VIDEO (MediaInfo - Expect Duration)
    # ==========================================================================
    def test_fmt_mp4(self): self._test_with_mock("mp4", "Duration", {})
    def test_fmt_mov(self): self._test_with_mock("mov", "Duration", {})
    def test_fmt_avi(self): self._test_with_mock("avi", "Duration", {})
    def test_fmt_mkv(self): self._test_with_mock("mkv", "Duration", {})
    def test_fmt_wmv(self): self._test_with_mock("wmv", "Duration", {})
    def test_fmt_3gp(self): self._test_with_mock("3gp", "Duration", {})
    def test_fmt_webm(self): self._test_with_mock("webm", "Duration", {})
    def test_fmt_ts(self):  self._test_with_mock("ts",  "Duration", {})
    def test_fmt_m2ts(self): self._test_with_mock("m2ts", "Duration", {})
    def test_fmt_vob(self): self._test_with_mock("vob", "Duration", {})
    def test_fmt_flv(self): self._test_with_mock("flv", "Duration", {})
    def test_fmt_mxf(self): self._test_with_mock("mxf", "Duration", {})
    def test_fmt_mpg(self): self._test_with_mock("mpg", "Duration", {})
    def test_fmt_mpeg(self): self._test_with_mock("mpeg", "Duration", {})

    # ==========================================================================
    # GROUP 3: AUDIO (MediaInfo - Expect Duration or Bit_Rate)
    # ==========================================================================
    def test_fmt_mp3(self): self._test_with_mock("mp3", "Duration", {}) 
    def test_fmt_flac(self): self._test_with_mock("flac", "Duration", {})
    def test_fmt_wav(self): self._test_with_mock("wav", "Duration", {})
    def test_fmt_m4a(self): self._test_with_mock("m4a", "Duration", {})
    def test_fmt_aac(self): self._test_with_mock("aac", "Duration", {})
    def test_fmt_ogg(self): self._test_with_mock("ogg", "Duration", {})
    def test_fmt_aiff(self): self._test_with_mock("aiff", "Duration", {})
    def test_fmt_wma(self): self._test_with_mock("wma", "Duration", {})
    def test_fmt_m4b(self): self._test_with_mock("m4b", "Duration", {})
    def test_fmt_opus(self): self._test_with_mock("opus", "Duration", {})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    args, unknown = parser.parse_known_args()
    
    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Type Coverage Tests")
        sys.exit(0)
        
    unittest.main(argv=[sys.argv[0]] + unknown)