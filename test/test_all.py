# ==============================================================================
# File: test_all.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Refactored to act as the primary test runner by default (no flag).",
    "Added encoding='utf-8' to run_version_check to fix decoding issues.",
    "Fixed File Not Found errors by correcting 'VERSION_CHECK_FILES' paths.",
    "Fixed import error for self-check by moving version_util import inside the __main__ block.",
    "Added IMMEIDATE PATH SETUP to prevent crash during self-check subprocess.",
    "CRITICAL FIX: Simplified TEST_MODULES names and import logic to fix \"No module named 'test.test_...'\" error.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Updated VERSION_CHECK_FILES list to include all 11 core and utility files for full version synchronization check."
]
# ------------------------------------------------------------------------------
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, List
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
    "config.py",
    "config_manager.py",
    "database_manager.py",
    "deduplicator.py",
    "file_scanner.py",
    "html_generator.py",
    "main.py",
    "metadata_processor.py",
    "migrator.py",
    "report_generator.py",
    "version_util.py",
    # Test files (FIX: paths must be relative to project root, which means adding 'test/')
    "test/test_all.py",
    "test/test_database_manager.py",
    "test/test_deduplicator.py",
    "test/test_file_scanner.py",
    "test/test_metadata_processor.py"
]

def run_version_check(file_path: str) -> Optional[str]:
    """Runs a subprocess to get the version string from a single file."""
    try:
        # Use python executable and the file path with the -v flag
        result = subprocess.run(
            [sys.executable, file_path, '-v'],
            capture_output=True,
            text=True,
            encoding='utf-8', # CRITICAL: Explicitly set encoding
            check=True
        )
        # The output format is standardized as "Version: X.Y.Z"
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.strip()
        return f"ERROR: Version tag not found in output for {file_path}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: Subprocess failed for {file_path}. Stderr: {e.stderr.strip()}"
    except Exception as e:
        return f"FATAL ERROR checking {file_path}: {e}"

def execute_version_check():
    """Checks and reports the version consistency across all project files."""
    print("=" * 60)
    print("🔄 PROJECT VERSION SYNCHRONIZATION CHECK")
    print("=" * 60)
    
    project_root = Path(__file__).resolve().parent.parent # Navigate up one level to project root
    versions: Dict[str, str] = {}
    
    # 1. Check all files defined in VERSION_CHECK_FILES
    for filename in VERSION_CHECK_FILES:
        filepath = project_root / filename
        if not filepath.exists():
            versions[filename] = f"FILE NOT FOUND at {filepath.name}"
            continue
            
        version_string = run_version_check(str(filepath.resolve()))
        versions[filename] = version_string
        
    # 2. Analyze results
    version_values = [v for v in versions.values() if v and not v.startswith(("ERROR", "FILE NOT FOUND"))]
    unique_versions = set(version_values)
    
    print("\n--- Individual File Versions ---")
    for filename, version in versions.items():
        if version.startswith("Version:"):
            print(f"✅ {filename:<25} {version}")
        else:
            print(f"❌ {filename:<25} {version}")
    
    print("\n--- Summary ---")
    if len(unique_versions) == 1:
        print(f"✅ SUCCESS: All {len(versions)} files are synchronized to {unique_versions.pop()}")
    elif not unique_versions:
        print("🔴 FAILURE: No valid version strings could be retrieved.")
    else:
        print("🔴 INCONSISTENCY DETECTED!")
        print("Found the following unique versions:")
        for v in sorted(list(unique_versions)):
            print(f"  - {v}")
    
    print("\n" + "=" * 60)


def run_tests():
    """Loads and runs all configured unit test modules."""
    print("=" * 60)
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 60)

    # Note: We do not need a TestLoader instance; unittest.defaultTestLoader is fine.
    # The modules are imported by name, assuming the path is set correctly.
    suite = unittest.TestSuite()
    
    for module_name in TEST_MODULES:
        try:
            # Dynamically import the test module
            module = __import__(module_name)
            # Find and add all test cases in the module
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                    suite.addTest(unittest.makeSuite(obj))
        except ImportError as e:
            print(f"ERROR: Could not import test module {module_name}: {e}")
            sys.exit(1)
            
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY:")
    print(f"Tests Run: {result.testsRun}")
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
    # Add project root to sys.path so modules (like version_util) can be imported
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root)) 

    # 2. ARGUMENT PARSING
    parser = argparse.ArgumentParser(description="Test Runner for File Organizer. Runs unit tests by default or checks versions with a flag.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for the test runner script.')
    parser.add_argument('--get_versions', action='store_true', help='If present, only performs a version check across all files instead of running tests.')
    args = parser.parse_args()

    # 3. VERSION EXIT (Must import here)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Test Runner")
        sys.exit(0)
        
    if args.get_versions:
        execute_version_check()
        
    else:
        # Default behavior: run all tests
        run_tests()