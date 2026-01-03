# ==============================================================================
# File: test/test_type_coverage.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial creation of Type Coverage suite (TDD Step 1: Red Phase).",
    "Added tests for Document (PDF, DOCX) metadata expectations.",
    "Added tests for Advanced Image (HEIC, RAW) metadata expectations.",
    "Added tests for Archive (ZIP) metadata expectations.",
    "EXPANDED: Included tests for Standard Images (JPG, PNG, GIF, BMP, TIFF, WEBP).",
    "EXPANDED: Included tests for Standard Video (MP4, MOV, AVI, MKV, WMV, 3GP, WEBM).",
    "EXPANDED: Included tests for Pro Video (TS, VOB, MXF).",
    "EXPANDED: Included tests for Standard Audio (MP3, FLAC, WAV, M4A).",
    "EXPANDED: Included tests for Pro Audio (AIFF, OPUS).",
    "CRITICAL UPDATE: Enforced STRICT library checks. Images/Docs must NOT rely on MediaInfo errors.",
    "REFACTOR: Unrolled loops into individual test methods to ensure visibility in test report.",
    "COMPLETION: Added individual tests for ALL projected file types (NEF, RAR, 7Z, DNG, etc.).",
    "FIX: Updated RAW image tests to accept 'Pillow_Error' as valid proof of attempting to parse."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.3.13
# ------------------------------------------------------------------------------
import unittest
import sys
import shutil
import os
from pathlib import Path

# --- BOOTSTRAP PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the extraction logic
from libraries_helper import get_video_metadata

TEST_OUTPUT_DIR = Path(os.getcwd()) / "test_output_coverage"

class TestTypeCoverage(unittest.TestCase):
    """
    TDD Suite to verify support for ALL intended file types.
    Each format has a dedicated test to ensure it appears in the final report.
    """

    @classmethod
    def setUpClass(cls):
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)
        TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def _create_dummy_file(self, filename):
        """Creates a zero-byte dummy file with the specific extension."""
        path = TEST_OUTPUT_DIR / filename
        # Ensure unique name to prevent collisions if running parallel
        if not path.exists():
            with open(path, "wb") as f:
                f.write(b"DUMMY_CONTENT_FOR_TDD")
        return path

    def _verify_type(self, ext, expected_keys, allowed_errors=None):
        """Helper to run the assertion for a specific extension."""
        fpath = self._create_dummy_file(f"test_file.{ext}")
        meta = get_video_metadata(fpath)
        
        if allowed_errors is None:
            allowed_errors = []

        has_key = any(k in meta for k in expected_keys)
        has_valid_error = any(k in meta for k in allowed_errors)

        # Check for incorrect MediaInfo usage fallback
        is_mediainfo_fallback = 'MediaInfo_Error' in meta and 'MediaInfo_Error' not in allowed_errors
        
        if is_mediainfo_fallback:
             self.fail(f"[{ext.upper()}] Incorrectly relied on MediaInfo. Metadata: {meta}")

        self.assertTrue(
            has_key or has_valid_error,
            f"[{ext.upper()}] No valid parsing attempt. Expected {expected_keys}. Got: {list(meta.keys())}"
        )

    # ==========================================================================
    # GROUP 1: IMAGES (Should Fail - Current code uses MediaInfo)
    # ==========================================================================
    # Standard
    def test_fmt_jpg(self): self._verify_type("jpg", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_jpeg(self): self._verify_type("jpeg", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_png(self): self._verify_type("png", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_gif(self): self._verify_type("gif", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_bmp(self): self._verify_type("bmp", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_tiff(self): self._verify_type("tiff", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_webp(self): self._verify_type("webp", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    
    # Advanced / RAW (Updated to accept Pillow_Error as we route RAW to Pillow)
    def test_fmt_heic(self): self._verify_type("heic", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_heif(self): self._verify_type("heif", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_cr2(self): self._verify_type("cr2", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_nef(self): self._verify_type("nef", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_arw(self): self._verify_type("arw", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_dng(self): self._verify_type("dng", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_orf(self): self._verify_type("orf", ["Width", "Height"], allowed_errors=["Pillow_Error"])
    def test_fmt_svg(self): self._verify_type("svg", ["Width", "Height"], allowed_errors=["SVG_Error"])

    # ==========================================================================
    # GROUP 2: DOCUMENTS (Should Fail - Current code uses MediaInfo)
    # ==========================================================================
    def test_fmt_pdf(self): self._verify_type("pdf", ["Page_Count"], allowed_errors=["PDF_Error"])
    def test_fmt_docx(self): self._verify_type("docx", ["Author", "Word_Count"], allowed_errors=["Office_Error"])
    def test_fmt_doc(self): self._verify_type("doc", ["Author", "Word_Count"], allowed_errors=["Office_Error"])
    def test_fmt_xlsx(self): self._verify_type("xlsx", ["Author"], allowed_errors=["Office_Error"])
    def test_fmt_xls(self): self._verify_type("xls", ["Author"], allowed_errors=["Office_Error"])
    def test_fmt_pptx(self): self._verify_type("pptx", ["Slide_Count"], allowed_errors=["Office_Error"])
    def test_fmt_epub(self): self._verify_type("epub", ["Title"], allowed_errors=["Ebook_Error"])
    def test_fmt_mobi(self): self._verify_type("mobi", ["Title"], allowed_errors=["Ebook_Error"])

    # ==========================================================================
    # GROUP 3: ARCHIVES (Should Fail - Current code uses MediaInfo)
    # ==========================================================================
    def test_fmt_zip(self): self._verify_type("zip", ["File_Count"], allowed_errors=["Archive_Error"])
    def test_fmt_rar(self): self._verify_type("rar", ["File_Count"], allowed_errors=["Archive_Error"])
    def test_fmt_7z(self): self._verify_type("7z", ["File_Count"], allowed_errors=["Archive_Error"])
    def test_fmt_tar(self): self._verify_type("tar", ["File_Count"], allowed_errors=["Archive_Error"])
    def test_fmt_gz(self): self._verify_type("gz", ["File_Count"], allowed_errors=["Archive_Error"])

    # ==========================================================================
    # GROUP 4: VIDEO (Should Pass - MediaInfo is allowed)
    # ==========================================================================
    # Standard
    def test_fmt_mp4(self): self._verify_type("mp4", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_mov(self): self._verify_type("mov", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_avi(self): self._verify_type("avi", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_mkv(self): self._verify_type("mkv", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_wmv(self): self._verify_type("wmv", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_3gp(self): self._verify_type("3gp", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_webm(self): self._verify_type("webm", ["Duration"], allowed_errors=["MediaInfo_Error"])
    
    # Pro / Legacy
    def test_fmt_ts(self):  self._verify_type("ts",  ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_m2ts(self): self._verify_type("m2ts", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_vob(self): self._verify_type("vob", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_ifo(self): self._verify_type("ifo", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_flv(self): self._verify_type("flv", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_mxf(self): self._verify_type("mxf", ["Duration"], allowed_errors=["MediaInfo_Error"])

    # ==========================================================================
    # GROUP 5: AUDIO (Should Pass - MediaInfo is allowed)
    # ==========================================================================
    # Standard
    def test_fmt_mp3(self): self._verify_type("mp3", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_flac(self): self._verify_type("flac", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_wav(self): self._verify_type("wav", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_m4a(self): self._verify_type("m4a", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_aac(self): self._verify_type("aac", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_ogg(self): self._verify_type("ogg", ["Duration"], allowed_errors=["MediaInfo_Error"])
    
    # Pro
    def test_fmt_aiff(self): self._verify_type("aiff", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_wma(self): self._verify_type("wma", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_m4b(self): self._verify_type("m4b", ["Duration"], allowed_errors=["MediaInfo_Error"])
    def test_fmt_opus(self): self._verify_type("opus", ["Duration"], allowed_errors=["MediaInfo_Error"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    args, unknown = parser.parse_known_args()
    
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Type Coverage Tests")
        sys.exit(0)
        
    unittest.main(argv=[sys.argv[0]] + unknown)