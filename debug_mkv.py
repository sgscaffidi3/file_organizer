
# VERSIONING
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_REL_CHANGES = [1]
import os
import sys
from pathlib import Path
import ctypes.util

# Try to import the library
try:
    import pymediainfo
    from pymediainfo import MediaInfo
    print(f"✅ pymediainfo library found (Module Version: {pymediainfo.__version__})")
except ImportError:
    print("❌ pymediainfo NOT installed. Run: pip install pymediainfo")
    sys.exit(1)

# --- CONFIGURATION ---
TEST_FILE = r"C:\Path\To\Your\Video.mkv" 

def test_mkv():
    # 1. Check for the DLL explicitly (Common Windows Issue)
    print("\n[Dependency Check]")
    dll_path = ctypes.util.find_library("MediaInfo")
    if dll_path:
        print(f"✅ System MediaInfo DLL found at: {dll_path}")
    else:
        # Check local folder
        local_dll = Path("MediaInfo.dll")
        if local_dll.exists():
             print(f"✅ Local MediaInfo.dll found in project folder.")
        else:
             print("⚠️  WARNING: MediaInfo DLL not found in PATH or project folder.")
             print("    Metadata extraction will likely FAIL or return empty.")

    # 2. Find a File
    file_path = Path(TEST_FILE)
    if str(TEST_FILE) == r"C:\Path\To\Your\Video.mkv":
        print("\n[File Search]")
        print("Searching for an .mkv file in the output directory...")
        found = list(Path('.').rglob('*.mkv'))
        if found:
            file_path = found[0]
            print(f"Found auto-detected file: {file_path}")
        else:
            print("❌ No MKV files found to test. Please edit TEST_FILE in the script.")
            return

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    # 3. Parse
    print(f"\n[Parsing Analysis]")
    print(f"Target: {file_path.name}")
    print("-" * 60)

    try:
        media_info = MediaInfo.parse(str(file_path))
        
        if len(media_info.tracks) == 0:
            print("❌ FAILURE: MediaInfo returned 0 tracks.")
            print("   This confirms pymediainfo is installed, but the underlying 'MediaInfo.dll' is missing or blocked.")
            return

        found_video = False
        for track in media_info.tracks:
            if track.track_type == "Video":
                found_video = True
                print(f"✅ Video Track Found!")
                print(f"   - Resolution: {track.width}x{track.height}")
                print(f"   - Duration:   {track.duration} ms")
                print(f"   - Codec:      {track.format}")
                print(f"   - Frame Rate: {track.frame_rate}")
        
        if not found_video:
            print("⚠️  Parsed successfully, but NO Video track found. (Is this an audio file?)")
            if hasattr(media_info, 'tracks'):
                print("   Tracks found: " + ", ".join([str(t.track_type) for t in media_info.tracks]))
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("\nPossible Causes:")
        print("1. 'MediaInfo.dll' is missing from your system.")
        print("2. The MKV file header is corrupted.")

if __name__ == "__main__":
    test_mkv()