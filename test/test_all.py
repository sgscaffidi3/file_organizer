# ==============================================================================
# File: test_all.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the system health check and version verification utility.
# ------------------------------------------------------------------------------
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional
import argparse
import sys

# List of files we want to test for version information
TEST_FILES = [
    "version_util.py",
    "config_manager.py",
    "config.py",
    "database_manager.py",
    "test_database_manager.py",
    "file_scanner.py",
    "test_file_scanner.py",
    "metadata_processor.py",
    "test_metadata_processor.py",
    "deduplicator.py",
    "test_deduplicator.py",
    "migrator.py",
    "html_generator.py",
    "report_generator.py",
    "main.py"
]

def run_version_check(filepath: Path) -> Optional[str]:
    """
    Executes a Python file with the --version argument and captures the output.
    Returns the version string (e.g., '0.1.5').
    """
    try:
        # Execute the file as a subprocess
        result = subprocess.run(
            [sys.executable, str(filepath), '--version'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5 # Prevent hangs
        )
        
        # Look for the 'Version: X.Y.Z' line in the output
        for line in result.stdout.splitlines():
            if line.strip().startswith("Version:"):
                # Clean up the version string
                return line.split(':', 1)[1].strip()
        
        return None # Version line not found
        
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Error executing {filepath.name}: {e}")
        return None

def compare_versions(version_a: str, version_b: str) -> bool:
    """Returns True if version_a is lower than version_b."""
    # Split version strings (e.g., '0.1.5' -> [0, 1, 5])
    a = [int(x) for x in version_a.split('.')]
    b = [int(x) for x in version_b.split('.')]
    return a < b

def get_version_extremes(versions: Dict[str, str]) -> Tuple[str, str]:
    """Determines the lowest and highest versions encountered."""
    
    version_items = list(versions.items())
    if not version_items:
        return ("N/A", "N/A")

    lowest_file, lowest_version = version_items[0]
    highest_file, highest_version = version_items[0]

    for filename, version in version_items:
        if compare_versions(version, lowest_version):
            lowest_version = version
            lowest_file = filename
        
        if compare_versions(highest_version, version):
            highest_version = version
            highest_file = filename
            
    return (f"{lowest_version} ({lowest_file})", f"{highest_version} ({highest_file})")


def main():
    """Main execution point for the version test utility."""
    parser = argparse.ArgumentParser(description="System Health Check: Invokes --version on all core Python files to verify version consistency.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for the main script and exit.')
    args = parser.parse_args()

    if args.version:
        # Since this script runs the version utility itself, it doesn't need to 
        # import print_version_info, but for consistency we'll use a local output.
        print("\n" + "=" * 50)
        print("test_all.py (System Health Check Utility)")
        print("Version: 0.1.1")
        print("=" * 50 + "\n")
        return

    print("\n" + "=" * 60)
    print("        FILE ORGANIZER SYSTEM HEALTH CHECK (Version Test)        ")
    print("=" * 60)

    project_root = Path(__file__).parent
    all_versions: Dict[str, str] = {}
    
    for file_name in TEST_FILES:
        file_path = project_root / file_name
        
        if not file_path.exists():
            print(f"❌ ERROR: File not found: {file_name}")
            continue

        version = run_version_check(file_path)
        
        if version:
            all_versions[file_name] = version
            print(f"✅ Found version for {file_name.ljust(25)}: {version}")
        else:
            print(f"⚠️  WARNING: Could not extract version from {file_name}")

    # --- Summary ---
    print("\n" + "-" * 60)
    print("              VERSION CONSISTENCY SUMMARY               ")
    print("-" * 60)

    lowest_version_info, highest_version_info = get_version_extremes(all_versions)
    
    print(f"Files Checked:   {len(all_versions)} / {len(TEST_FILES)}")
    print(f"Lowest Version:  {lowest_version_info}")
    print(f"Highest Version: {highest_version_info}")
    
    if lowest_version_info.split(' ')[0] != highest_version_info.split(' ')[0]:
        print("\n🚨 INCONSISTENCY DETECTED: Lowest and highest versions differ.")
        print("Please review the CHANGELOGs to bring all files up to the latest patch.")
    else:
        print("\n✨ SUCCESS: All files are at a consistent Major/Minor version level.")
        
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()