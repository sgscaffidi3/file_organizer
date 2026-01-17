
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
from tqdm import tqdm

# Import our helper to test the files
try:
    from libraries_helper import extract_raw_metadata, extract_image_metadata
except ImportError:
    # Quick hack to allow running if not in python path
    sys.path.append(os.getcwd())
    from libraries_helper import extract_raw_metadata, extract_image_metadata

def scan_for_corruption(directory):
    print(f"Scanning {directory} for corrupt RAW/HEIC files...")
    
    # Extensions to check
    targets = ['.nef', '.cr2', '.arw', '.dng', '.orf', '.heic']
    
    files_to_check = []
    for root, _, files in os.walk(directory):
        for f in files:
            if Path(f).suffix.lower() in targets:
                files_to_check.append(Path(root) / f)
                
    print(f"Found {len(files_to_check)} candidate files.")
    
    bad_files = []
    
    for fpath in tqdm(files_to_check, unit="file"):
        try:
            ext = fpath.suffix.lower()
            if ext in ['.heic']:
                # Test HEIC
                res = extract_image_metadata(fpath)
                if 'Pillow_Error' in res:
                    # Double check if it's a real error or just a library missing error
                    if "not installed" not in res['Pillow_Error']:
                        print(f"\n[CORRUPT HEIC] {fpath}")
                        print(f"  Error: {res['Pillow_Error']}")
                        bad_files.append(fpath)
            else:
                # Test RAW
                # We simply call the function. The C-library might print "data corrupted" to stderr
                # But we want to associate it with the filename.
                res = extract_raw_metadata(fpath)
                if 'Raw_Error' in res:
                    print(f"\n[CORRUPT RAW] {fpath}")
                    print(f"  Error: {res['Raw_Error']}")
                    bad_files.append(fpath)
                    
        except Exception as e:
            print(f"\n[CRASH] {fpath}: {e}")
            bad_files.append(fpath)

    print("-" * 40)
    print(f"Scan Complete. Found {len(bad_files)} corrupt files.")
    if bad_files:
        with open("corrupt_files_report.txt", "w") as f:
            for bf in bad_files:
                f.write(str(bf) + "\n")
        print("List saved to 'corrupt_files_report.txt'")

if __name__ == "__main__":
    # Change this to your source directory
    source = "D:/personal_media" 
    scan_for_corruption(source)