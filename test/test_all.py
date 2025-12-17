# ==============================================================================
# File: test_all.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 25
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
    "Updated VERSION_CHECK_FILES list to include all 11 core and utility files for full version synchronization check.",
    "FEATURE: Implemented CustomTestResult and CustomTestRunner to generate a detailed, structured summary table of all test results (PASS/FAIL/ERROR) at the end of the run. Refactored test loading to use TestLoader.loadTestsFromTestCase to remove DeprecationWarning.",
    "CRITICAL FIX: Implemented safe parsing in CustomTestResult._get_test_info to prevent IndexError when processing non-standard unittest IDs (like setup/teardown steps).",
    "CRITICAL FIX & READABILITY IMPROVEMENT: Modified CustomTestResult._get_test_info to use robust test object attributes (__module__, _testMethodName) instead of unreliable string parsing. Corrected test run metrics calculation and improved detailed table readability by formatting module and method names.",
    "READABILITY IMPROVEMENT: Modified format_results_table to dynamically calculate column widths and use string padding for consistent, aligned output in the detailed report table.",
    "VISUAL FIX: Refined column width calculation and separator line generation in format_results_table to ensure perfect alignment of all pipe characters (|) in the console output.",
    "VISUAL FIX: Corrected f-string padding logic to ensure the separator line uses the exact same calculated total width as the header and data rows, fixing final pipe alignment.",
    "VISUAL FIX: Applied dynamic column width calculation and padding to the Summary Table for improved console alignment and readability."
]
# ------------------------------------------------------------------------------
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import argparse
import sys
import unittest
import io # Added for CustomTestRunner stream handling

# --- Configuration for the Test Runner ---
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
    # Test files
    "test/test_all.py",
    "test/test_database_manager.py",
    "test/test_deduplicator.py",
    "test/test_file_scanner.py",
    "test/test_metadata_processor.py"
]

# ==============================================================================
# 1. Custom Test Result Class
#    Captures the status and details of every single test run.
# ==============================================================================
class CustomTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        # We need to set up the stream before calling super() for correct verbosity output
        super().__init__(*args, **kwargs)
        self.all_results = []
        # Store the class method names for reliable lookup
        self.test_method_names = set()

    def _get_test_info(self, test, status, err=None):
        """
        Extracts necessary information from the test object using attributes for robustness.
        """
        
        # Check if the test object is a standard TestCase instance
        if hasattr(test, '__module__') and hasattr(test, '_testMethodName'):
            module_name = test.__module__
            method_name = test._testMethodName
            # Add the method name to our set to correctly calculate the total run tests
            self.test_method_names.add(method_name)
        else:
            # Internal unittest object (e.g. setup/teardown steps)
            module_name = "Internal"
            method_name = "Setup/Teardown"

        # If it's a failure or error, extract a single line summary of the issue
        details = ""
        if err:
            # Format the exception info into a string
            traceback_str = self._exc_info_to_string(err, test)
            
            # Use the last non-empty line of the traceback as a summary (usually the error message)
            lines = [line.strip() for line in traceback_str.split('\n')]
            for line in reversed(lines):
                 # Ignore lines that just contain file/line info
                 if line and not (line.startswith('File "') and line.endswith('.py"')):
                     details = line
                     break

        return module_name, method_name, status, details

    # Override standard methods to capture results and print minimal output
    def addSuccess(self, test):
        super().addSuccess(test)
        self.all_results.append(self._get_test_info(test, '✅ PASS'))
        self.stream.write("ok\n")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.all_results.append(self._get_test_info(test, '❌ FAIL', err))
        self.stream.write("FAIL\n")
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.all_results.append(self._get_test_info(test, '🔴 ERROR', err))
        self.stream.write("ERROR\n")
        self.stream.flush()


# ==============================================================================
# 2. Helper function to format the table
# ==============================================================================
def format_results_table(all_results, total_tests_run):
    """Formats the test results into a dynamically padded string table."""
    
    # Filter out internal entries for accurate statistics and detailed report
    test_entries = [r for r in all_results if r[0] != "Internal"]
    
    # Data collection
    total_run = total_tests_run
    passed_count = sum(1 for _, _, status, _ in test_entries if status == '✅ PASS')
    failed_count = sum(1 for _, _, status, _ in test_entries if status in ('❌ FAIL', '🔴 ERROR'))
    passing_percentage = (passed_count / total_run) * 100 if total_run > 0 else 0

    # ==========================================================================
    # --- SUMMARY TABLE ---
    # ==========================================================================
    
    # 1. Prepare Summary Data
    summary_data_raw = [
        ["**Tests Run**", str(total_run)],
        ["**Passed**", str(passed_count)],
        ["**Failed / Errored**", str(failed_count)],
        ["**Passing Percentage**", f"**{passing_percentage:.2f}%**"],
    ]

    # 2. Calculate Column Widths for Summary (Content length only)
    summary_header = ["Metric", "Value"]
    
    max_metric_content_width = len(summary_header[0])
    max_value_content_width = len(summary_header[1])
    
    for metric, value in summary_data_raw:
        max_metric_content_width = max(max_metric_content_width, len(metric))
        max_value_content_width = max(max_value_content_width, len(value))

    # Total width (W_T): max_content_width + 2 spaces for padding
    total_metric_width = max_metric_content_width + 2 
    total_value_width = max_value_content_width + 2
    
    # 3. Format Summary Table String
    summary_table = "\n"
    
    # Header
    summary_table += f"|{summary_header[0].center(total_metric_width)}"
    summary_table += f"|{summary_header[1].center(total_value_width)}|\n"
    
    # Separator
    summary_table += f"|{'-' * total_metric_width}"
    summary_table += f"|{'-' * total_value_width}|\n"
    
    # Data Rows
    for metric, value in summary_data_raw:
        # Metric is left-justified
        summary_table += f"|{metric.ljust(total_metric_width)}"
        # Value is right-justified (standard for numbers)
        summary_table += f"|{value.rjust(total_value_width)}|\n"
    
    summary = summary_table

    # ==========================================================================
    # --- DETAILED TEST REPORT ---
    # ==========================================================================

    # Detailed Table Header and Data Preparation
    detailed_data = []
    header_row = ["Test Suite", "Test Name", "Status", "Error/Failure Details"]
    
    # 1. Prepare raw data and calculate readable names, while finding max content length
    # Note: We use max_widths to store the maximum *content* length (excluding surrounding spaces/pipes)
    max_widths = [len(h) for h in header_row]
    
    for module_name, test_name, status, details in test_entries:
        # 1. Clean up Suite Name (e.g., test_database_manager -> Database Manager)
        suite_name_readable = module_name.replace('test_', '').title().replace('_', ' ')
        max_widths[0] = max(max_widths[0], len(suite_name_readable))

        # 2. Clean up Test Name (e.g., test_01_... -> 01: Test Name)
        if test_name.startswith('test_'):
            parts = test_name.split('_', 2)
            if len(parts) >= 3 and parts[1].isdigit():
                # Formats test_01_hashing_and_initial_insertion to 01: Hashing And Initial Insertion
                test_number_padded = parts[1].zfill(2)
                test_name_body = parts[2].replace('_', ' ').title()
                test_name_readable = f"{test_number_padded}: {test_name_body}"
            else:
                test_name_readable = test_name.replace('_', ' ').title()
        else:
             test_name_readable = test_name
        max_widths[1] = max(max_widths[1], len(test_name_readable))

        details_summary = details.replace('|', '/') if details else ""
        max_widths[2] = max(max_widths[2], len(status))
        max_widths[3] = max(max_widths[3], len(details_summary))
        
        detailed_data.append([suite_name_readable, test_name_readable, status, details_summary])

    # 2. Calculate final column widths (Total width between pipes: max_content_length + 2 spaces)
    total_col_width = [w + 2 for w in max_widths] 
    
    
    # 3. Format the detailed table string
    detail_table = "\n### Detailed Test Report\n\n"
    
    header_line = ""
    separator_line = ""
    
    for i, title in enumerate(header_row):
        W_T = total_col_width[i] 
        
        # Header: Content centered within the total width W_T space.
        header_line += f"|{title.center(W_T)}" 
        
        # Separator: W_T hyphens to match the width of the content cell.
        separator_line += f"|{'-' * W_T}" 

    header_line += "|"
    separator_line += "|" # Final pipe

    detail_table += header_line + "\n"
    detail_table += separator_line + "\n"

    # Format Data Rows
    for row_data in detailed_data:
        row_line = ""
        
        # Data rows are padded to the full width W_T.
        # Col 0 (Suite) and Col 1 (Name) are left-justified.
        row_line += f"|{row_data[0].ljust(total_col_width[0])}" 
        row_line += f"|{row_data[1].ljust(total_col_width[1])}"
        # Col 2 (Status) is center-justified.
        row_line += f"|{row_data[2].center(total_col_width[2])}"
        # Col 3 (Details) is left-justified.
        row_line += f"|{row_data[3].ljust(total_col_width[3])}"
        row_line += "|"
        detail_table += row_line + "\n"

    return summary + detail_table


# ==============================================================================
# 3. Custom Test Runner Class
#    Uses the custom result and prints the final table.
# ==============================================================================
class CustomTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        # Use sys.stderr for stream to ensure test prints (like scan output) show up correctly
        super().__init__(stream=sys.stderr, *args, **kwargs)
        self.resultclass = CustomTestResult 
        self.verbosity = 2 # Ensures descriptions are printed

    def run(self, test):
        # The result object will collect all data in self.all_results
        result = super().run(test)
        
        # Print the final summary section
        print("\n" + "="*80)
        print("FINAL TEST EXECUTION SUMMARY")
        print("="*80)
        
        # The result.testsRun is the definitive total count from unittest
        print(format_results_table(result.all_results, result.testsRun))
        print("="*80 + "\n")
        
        return result


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
    """Loads and runs all configured unit test modules using the CustomTestRunner."""
    print("=" * 60)
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Dynamically load the test case classes and add them to the suite
    for module_name in TEST_MODULES:
        try:
            # Dynamically import the test module
            module = __import__(module_name)
            # Find and add all test cases in the module
            for name in dir(module):
                obj = getattr(module, name)
                # Check if it's a class, is a TestCase subclass, and is not the base TestCase itself
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                    # Replacing deprecated unittest.makeSuite with modern TestLoader.
                    suite.addTest(loader.loadTestsFromTestCase(obj))
        except ImportError as e:
            print(f"ERROR: Could not import test module {module_name}: {e}")
            # Do not exit immediately, continue trying other modules if possible
            continue 
            
    # Use the CustomTestRunner to run tests and print the detailed summary
    runner = CustomTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Use the result to set the final exit code
    if not result.wasSuccessful():
        sys.exit(1)
    # Note: If successful, the program will exit cleanly (sys.exit(0) is implicit)


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
        # Import inside the block to avoid dependency issues if version_util is missing/broken
        from version_util import print_version_info
        print_version_info(__file__, "Test Runner")
        sys.exit(0)
        
    if args.get_versions:
        execute_version_check()
        
    else:
        # Default behavior: run all tests
        run_tests()