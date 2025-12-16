# ==============================================================================
# File: test_all.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 6. CRITICAL FIX: Simplified TEST_MODULES names and import logic to fix "No module named 'test.test_...'" error.
# 5. Added IMMEIDATE PATH SETUP to prevent crash during self-check subprocess.
# 4. Fixed import error for self-check by moving version_util import inside the __main__ block.
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
# CRITICAL FIX: List modules using only their filename (no 'test.' prefix)
TEST_MODULES = [
    "test_database_manager",
    "test_file_scanner",
    "test_metadata_processor",
    "test_deduplicator",
]

# List of files to check for the --get_versions functionality (relative to project root)
VERSION_CHECK_FILES = [
    "version_util.py", "config_manager.py", "config.py", "database_manager.py",
    "file_scanner.py", "metadata_processor.py", "deduplicator.py",
    "migrator.py", "html_generator.py", "report_generator.py",
    "main.py", 
    "test/test_database_manager.py", "test/test_file_scanner.py", 
    "test/test_metadata_processor.py", "test/test_deduplicator.py",
    "test/test_all.py",
]

# ==============================================================================
# VERSION CHECK FUNCTIONS (Used when --get_versions is present)
# ==============================================================================
# (These functions remain unchanged, but rely on the sys.path setup below)

def run_version_check(filepath: Path) -> Optional[str]:
    """
    Executes a Python file with the --version argument and captures the output.
    """
    try:
        # Execute the file as a subprocess
        result = subprocess.run(
            [sys.executable, str(filepath), '--version'],
            capture_output=True,
            text=True,
            encoding='utf-8', 
            check=False,
            timeout=5 
        )
        
        # Check for non-zero exit status (a crash or clean exit 1)
        if result.returncode != 0 and not result.stdout:
            print(f"Error executing {filepath.name}: Command returned non-zero exit status {result.returncode}.")
            return None
            
        # Look for the 'Version: X.Y.Z' line in the output
        for line in result.stdout.splitlines():
            if line.strip().startswith("Version:"):
                return line.split(':', 1)[1].strip()
        
        return None

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"Error executing {filepath.name}: {e}")
        return None

def compare_versions(version_a: str, version_b: str) -> bool:
    """Returns True if version_a is lower than version_b."""
    try:
        a = [int(x) for x in version_a.split('.')]
        b = [int(x) for x in version_b.split('.')]
        return a < b
    except ValueError:
        return False

def get_version_extremes(versions: Dict[str, str]) -> Tuple[str, str]:
    version_items = list(versions.items())
    if not version_items:
        return ("N/A", "N/A")

    lowest_version = version_items[0][1]
    lowest_file = version_items[0][0]
    highest_version = version_items[0][1]
    highest_file = version_items[0][0]

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

    project_root = Path(__file__).parent.parent
    all_versions: Dict[str, str] = {}
    
    for file_name in VERSION_CHECK_FILES:
        file_path = project_root / file_name 
        
        if not file_path.exists():
            print(f"❌ ERROR: File not found: {file_name}")
            continue

        version = run_version_check(file_path)
        
        if version and version != "Error":
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
    
    low_major_minor = ".".join(lowest_version_info.split(' ')[0].split('.')[:2])
    high_major_minor = ".".join(highest_version_info.split(' ')[0].split('.')[:2])
    
    if low_major_minor != high_major_minor:
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
    
    # Discover tests from the simplified module names
    for module_name in TEST_MODULES:
        try:
            # We import the module directly; Python looks in the test/ subdirectory 
            # because we added the project root to sys.path in the __main__ block.
            module = __import__(module_name)
            
            # Load all tests from the module object
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
        except ImportError as e:
            print(f"❌ ERROR: Could not load test module {module_name}. Ensure it exists in the 'test/' folder and imports are correct. Error: {e}")
            return
        except Exception as e:
             print(f"❌ ERROR: Failed to process module {module_name}. Error: {e}")
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
    # 1. CRITICAL: IMMEDIATE PATH SETUP (MUST be first)
    project_root = Path(__file__).resolve().parent.parent
    sys.path.append(str(project_root)) 

    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Test Runner for File Organizer. Runs unit tests by default or checks versions with a flag.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for the test runner script.')
    parser.add_argument('--get_versions', action='store_true', help='If present, only performs a version check across all files instead of running tests.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Test Runner")
        sys.exit(0)
        
    if args.get_versions:
        execute_version_check()
        
    else:
        # Default behavior: run all tests
        # Ensure a dummy __init__.py exists (for import stability)
        init_file = project_root / 'test' / '__init__.py'
        if not init_file.exists():
             init_file.touch()
             
        run_all_tests()