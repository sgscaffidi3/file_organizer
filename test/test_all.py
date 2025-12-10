# ==============================================================================
# File: test_all.py
# Version: 0.2
# ------------------------------------------------------------------------------
# CHANGELOG:
# 3. Fixed File Not Found errors by correcting 'VERSION_CHECK_FILES' paths.
# 2. Added encoding='utf-8' to run_version_check to fix decoding issues.
# 1. Refactored to act as the primary test runner by default (no flag).
# ------------------------------------------------------------------------------
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional
import argparse
import sys
import unittest

# --- Configuration for the Test Runner ---
# List of test files (relative path) to be run by default
TEST_MODULES = [
    "test.test_database_manager",
    "test.test_file_scanner",
    "test.test_metadata_processor",
    "test.test_deduplicator",
]

# List of files to check for the --get_versions functionality (relative to project root)
VERSION_CHECK_FILES = [
    # Core Files (Stay in the root)
    "version_util.py",
    "config_manager.py",
    "config.py",
    "database_manager.py",
    "file_scanner.py",
    "metadata_processor.py",
    "deduplicator.py",
    "migrator.py",
    "html_generator.py",
    "report_generator.py",
    "main.py",
    
    # Test Files (Must use the 'test/' prefix)
    "test/test_database_manager.py",
    "test/test_file_scanner.py",
    "test/test_metadata_processor.py",
    "test/test_deduplicator.py",
    "test/test_all.py",
]

# ==============================================================================
# VERSION CHECK FUNCTIONS (Used when --get_versions is present)
# ==============================================================================

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
            encoding='utf-8', # FIX: Explicitly use UTF-8 encoding
            check=True,
            timeout=5 
        )
        
        # Check if the output contains a known encoding error message (just in case)
        if "charmap" in result.stdout.lower() or "codec can't decode" in result.stdout.lower():
            return None 

        # Look for the 'Version: X.Y.Z' line in the output
        for line in result.stdout.splitlines():
            if line.strip().startswith("Version:"):
                return line.split(':', 1)[1].strip()
        
        return None # Version line not found

    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Error executing {filepath.name}: {e}")
        return None

def compare_versions(version_a: str, version_b: str) -> bool:
    """Returns True if version_a is lower than version_b."""
    # Safety check added in case non-version strings slip through
    try:
        a = [int(x) for x in version_a.split('.')]
        b = [int(x) for x in version_b.split('.')]
        return a < b
    except ValueError:
        return False # Treat comparison failure as false

def get_version_extremes(versions: Dict[str, str]) -> Tuple[str, str]:
    """Determines the lowest and highest versions encountered."""
    version_items = list(versions.items())
    if not version_items:
        return ("N/A", "N/A")

    lowest_version = lowest_file = version_items[0][1]
    highest_version = highest_file = version_items[0][1]

    for filename, version in version_items:
        if compare_versions(version, lowest_version):
            lowest_version = version
            lowest_file = filename
        
        if compare_versions(highest_version, version):
            highest_version = version
            highest_file = filename
            
    return (f"{lowest_version} ({lowest_file})", f"{highest_version} ({highest_file})")


def execute_version_check():
    """Runs the version check and reports consistency."""
    print("\n" + "=" * 60)
    print("        FILE ORGANIZER SYSTEM HEALTH CHECK (Version Test)        ")
    print("=" * 60)

    # project_root is one level up from test/
    project_root = Path(__file__).parent.parent
    all_versions: Dict[str, str] = {}
    
    for file_name in VERSION_CHECK_FILES:
        # This correctly builds the path: project_root / 'test/test_file.py'
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
    
    print(f"Files Checked:   {len(all_versions)} / {len(VERSION_CHECK_FILES)}")
    print(f"Lowest Version:  {lowest_version_info}")
    print(f"Highest Version: {highest_version_info}")
    
    if lowest_version_info.split(' ')[0] != highest_version_info.split(' ')[0]:
        print("\n🚨 INCONSISTENCY DETECTED: Lowest and highest versions differ.")
        print("Please review the CHANGELOGs to bring all files up to the latest patch.")
    else:
        print("\n✨ SUCCESS: All files are at a consistent Major/Minor version level.")
        
    print("=" * 60 + "\n")


# ==============================================================================
# TEST RUNNER FUNCTIONS (Used by default)
# ==============================================================================

def run_all_tests():
    """Discovers and runs all tests in the configured modules."""
    
    print("\n" + "=" * 60)
    print("       FILE ORGANIZER UNIT TEST SUITE EXECUTION (v0.2.0)      ")
    print("=" * 60)

    # 1. Load the tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Discover tests from the specified module files
    for module_name in TEST_MODULES:
        try:
            # Import the module using the dot-notation path (e.g., test.test_database_manager)
            module = __import__(module_name, fromlist=[''])
            
            # Load all tests from the module
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
        except ImportError as e:
            print(f"❌ ERROR: Could not load test module {module_name}. Error: {e}")
            return

    # 2. Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("             TEST SUITE FINAL SUMMARY             ")
    print("=" * 60)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("🔴 TEST FAILURES DETECTED! Review errors above.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    # 1. Immediately check for the --version flag using a dedicated function
    parser = argparse.ArgumentParser(description="Test Runner for File Organizer. Runs unit tests by default or checks versions with a flag.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for the test runner script.')
    parser.add_argument('--get_versions', action='store_true', help='If present, only performs a version check across all files instead of running tests.')
    args, unknown = parser.parse_known_args()

    if args.version:
        print("\nFile Organizer Test Runner Version: 0.2.0\n")
        sys.exit(0)
        
    # 2. Path Modification for Test Execution (Only runs if we're not exiting for --version)
    # Add project root path to allow successful imports of test modules using dot notation
    project_root = Path(__file__).resolve().parent.parent
    sys.path.append(str(project_root)) 
        
    if args.get_versions:
        execute_version_check()
        
    else:
        # Default behavior: run all tests
        # We need an __init__.py in 'test/' for the dot-notation import to work correctly.
        # Ensure a dummy __init__.py exists in the test directory.
        init_file = project_root / 'test' / '__init__.py'
        if not init_file.exists():
             init_file.touch()
             
        run_all_tests()