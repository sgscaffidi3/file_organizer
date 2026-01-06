# ==============================================================================
# File: test/test_libraries.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 6
# Version: 0.3.6
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation of test_libraries.py to validate external library helpers.",
    "Implemented test for version reporting (get_library_versions).",
    "Implemented test for TQDM progress bar wrapper.",
    "Implemented test for Pillow metadata extraction with a non-existent file path.",
    "Implemented test for standalone CLI version check (N06).",
    "BUG FIX: Updated error key assertions to match granular error keys (Pillow_Error) introduced in libraries_helper v0.4.19."
]
# ------------------------------------------------------------------------------
import re
import unittest
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import argparse

# Ensure project root is in path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from libraries_helper import (
    get_library_versions, 
    demo_tqdm_progress, 
    extract_image_metadata,
    TQDM_AVAILABLE,
    PIL_AVAILABLE
)

# Define the path to the file being tested for standalone execution
LIBRARIES_HELPER_PATH = Path(__file__).resolve().parent.parent / 'libraries_helper.py'


class TestLibrariesHelper(unittest.TestCase):

    def test_01_library_version_reporting(self):
        """Test that get_library_versions returns expected keys and status."""
        versions = get_library_versions()
        self.assertIsInstance(versions, dict)
        self.assertIn('tqdm', versions)
        self.assertIn('Pillow', versions)

        if TQDM_AVAILABLE:
            self.assertNotEqual(versions['tqdm'], "Not Installed")
        else:
            self.assertEqual(versions['tqdm'], "Not Installed")

        if PIL_AVAILABLE:
            self.assertNotEqual(versions['Pillow'], "Not Installed")
        else:
            self.assertEqual(versions['Pillow'], "Not Installed")

    @unittest.skipUnless(TQDM_AVAILABLE, "tqdm library is not installed.")
    @patch('sys.stdout', new_callable=StringIO)
    def test_02_tqdm_progress_bar_execution(self, mock_stdout):
        """Test that the tqdm wrapper executes without error and prints output."""
        items = [1, 2, 3]
        demo_tqdm_progress(items, "Test TQDM")
        
        self.assertIn("Test TQDM", mock_stdout.getvalue())
        self.assertIn("TQDM Demo Complete", mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_03_tqdm_missing_library_handling(self, mock_stdout):
        """Test that the tqdm wrapper handles missing library gracefully."""
        if not TQDM_AVAILABLE:
            with patch('libraries_helper.TQDM_AVAILABLE', False):
                demo_tqdm_progress([1], "Test TQDM Fail")
                self.assertIn("tqdm is not installed.", mock_stdout.getvalue())


    def test_04_extract_metadata_file_not_found(self):
        """Test that metadata extraction returns an error for a non-existent path."""
        non_existent_path = Path("/this/path/does/not/exist_12345.jpg")
        
        result = extract_image_metadata(non_existent_path)
        
        # FIX: Check for the specific error key used in implementation
        self.assertTrue('error' in result or 'Pillow_Error' in result, "Expected error key in result")
        
        error_msg = result.get('error') or result.get('Pillow_Error')
        self.assertIn('No such file', str(error_msg)) # Loose string match for OS variance

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow library is not installed.")
    @patch('libraries_helper.Image.open')
    def test_05_extract_metadata_io_error_handling(self, mock_open):
        """Test that metadata extraction handles I/O errors from Pillow."""
        mock_open.side_effect = IOError("Simulated corrupted file error.")
        test_path = Path(__file__).resolve()
        
        result = extract_image_metadata(test_path)
        
        # FIX: Check for the specific error key used in implementation
        self.assertTrue('error' in result or 'Pillow_Error' in result, "Expected error key in result")
        
        error_msg = result.get('error') or result.get('Pillow_Error')
        self.assertIn('Simulated corrupted file error', str(error_msg))

    def test_06_standalone_version_check(self):
        """
        Test that running libraries_helper.py standalone with -v returns the version string.
        (Required by N06)
        """
        if not LIBRARIES_HELPER_PATH.exists():
             self.fail(f"Test setup failed: libraries_helper.py not found at {LIBRARIES_HELPER_PATH}")
             
        try:
            result = subprocess.run(
                [sys.executable, str(LIBRARIES_HELPER_PATH), '-v'],
                capture_output=True,
                text=True,
                check=True # Raise exception on non-zero exit code
            )
            
            # The expected version format is "Version: 0.3.5"
            # 1. Verify the 'Version:' label exists
            self.assertIn("Version:", result.stdout)

            # 2. Verify the format is 3 numbers separated by 2 dots (e.g., 0.3.16)
            # This regex looks for 'Version: ' followed by digits.digits.digits
            version_pattern = r"Version:\s+(\d+\.\d+\.\d+)"
            match = re.search(version_pattern, result.stdout)
            
            self.assertIsNotNone(
                match, 
                f"Output did not contain a valid version format. Output was: {result.stdout}"
            )
            
            # Optional: Log the detected version for debugging
            detected_version = match.group(1)
            print(f"Detected Version: {detected_version}")
            
        except subprocess.CalledProcessError as e:
            self.fail(f"Subprocess failed with error code {e.returncode}. Stderr: {e.stderr}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    args, unknown = parser.parse_known_args()
    
    if args.version:
        # Fallback if version_util not in path
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Libraries Tests")
        except:
            print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
        
    unittest.main(argv=[sys.argv[0]] + unknown)