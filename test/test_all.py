# ==============================================================================
# File: test/test_all.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
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
    "VISUAL FIX: Applied dynamic column width calculation and padding to the Summary Table for improved console alignment and readability.",
    "FEATURE: Added 'test_libraries' to the test suite and updated version audit list.",
    "FEATURE: Added 'test_migrator' to the test suite and updated version audit list.",
    "FEATURE: Added 'test_type_coverage' to the test suite (TDD Red Phase).",
    "FEATURE: Implemented Log File Output. Tests now write to 'test_run.log' in addition to console.",
    "UX: Changed log file extension to .txt for easier sharing.",
    "FIX: Moved version check argument parsing before logging setup to prevent sys.unraisablehook error."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.21
# ------------------------------------------------------------------------------
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import argparse
import sys
import unittest
import io 
import textwrap
import datetime

# --- Configuration for the Test Runner ---
TEST_MODULES = [
    "test_database_manager",
    "test_file_scanner",
    "test_metadata_processor",
    "test_deduplicator",
    "test_libraries",
    "test_assets",
    "test_migrator",
    "test_type_coverage"
]

# List of files to check for the --get_versions functionality
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
    "libraries_helper.py",  
    "demo_libraries.py",    
    "asset_manager.py",
    "video_asset.py",
    "base_assets.py",
    "server.py",
    # Test files
    "test/test_all.py",
    "test/test_database_manager.py",
    "test/test_deduplicator.py",
    "test/test_file_scanner.py",
    "test/test_metadata_processor.py",
    "test/test_libraries.py",
    "test/test_assets.py",
    "test/test_migrator.py",
    "test/test_type_coverage.py"
]

# --- Helper for Dual Output (Console + File) ---
class Tee(io.TextIOWrapper):
    """Writes to both stdout/stderr and a file."""
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, data):
        self.original_stream.write(data)
        self.log_file.write(data)
        self.flush()

    def flush(self):
        self.original_stream.flush()
        self.log_file.flush()

# ==============================================================================
# 1. Custom Test Result Class
# ==============================================================================
class CustomTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_results = []
        self.test_method_names = set()

    def _get_test_info(self, test, status, err=None):
        if hasattr(test, '__module__') and hasattr(test, '_testMethodName'):
            module_name = test.__module__
            method_name = test._testMethodName
            self.test_method_names.add(method_name)
        else:
            module_name = "Internal"
            method_name = "Setup/Teardown"

        details = ""
        if err:
            traceback_str = self._exc_info_to_string(err, test)
            lines = [line.strip() for line in traceback_str.split('\n')]
            for line in reversed(lines):
                 if line and not (line.startswith('File "') and line.endswith('.py"')):
                     details = line
                     break
        return module_name, method_name, status, details

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
    test_entries = [r for r in all_results if r[0] != "Internal"]
    
    total_run = total_tests_run
    passed_count = sum(1 for _, _, status, _ in test_entries if status == '✅ PASS')
    failed_count = sum(1 for _, _, status, _ in test_entries if status in ('❌ FAIL', '🔴 ERROR'))
    passing_percentage = (passed_count / total_run) * 100 if total_run > 0 else 0

    # --- SUMMARY TABLE ---
    summary_data_raw = [
        ["**Tests Run**", str(total_run)],
        ["**Passed**", str(passed_count)],
        ["**Failed / Errored**", str(failed_count)],
        ["**Passing Percentage**", f"**{passing_percentage:.2f}%**"],
    ]

    summary_header = ["Metric", "Value"]
    max_metric_content_width = len(summary_header[0])
    max_value_content_width = len(summary_header[1])
    
    for metric, value in summary_data_raw:
        max_metric_content_width = max(max_metric_content_width, len(metric))
        max_value_content_width = max(max_value_content_width, len(value))

    total_metric_width = max_metric_content_width + 2 
    total_value_width = max_value_content_width + 2
    
    summary_table = "\n"
    summary_table += f"|{summary_header[0].center(total_metric_width)}"
    summary_table += f"|{summary_header[1].center(total_value_width)}|\n"
    summary_table += f"|{'-' * total_metric_width}"
    summary_table += f"|{'-' * total_value_width}|\n"
    
    for metric, value in summary_data_raw:
        summary_table += f"|{metric.ljust(total_metric_width)}"
        summary_table += f"|{value.rjust(total_value_width)}|\n"
    
    summary = summary_table

    # --- DETAILED TEST REPORT ---
    detailed_data = []
    header_row = ["Test Suite", "Test Name", "Status", "Error/Failure Details"]
    MAX_DETAILS_WIDTH = 50 

    max_widths = [len(header_row[0]), len(header_row[1]), len(header_row[2]), MAX_DETAILS_WIDTH]

    for module_name, test_name, status, details in test_entries:
        suite_readable = module_name.replace('test_', '').title().replace('_', ' ')
        max_widths[0] = max(max_widths[0], len(suite_readable))

        if test_name.startswith('test_'):
            parts = test_name.split('_', 2)
            if len(parts) >= 3 and parts[1].isdigit():
                name_readable = f"{parts[1].zfill(2)}: {parts[2].replace('_', ' ').title()}"
            else:
                name_readable = test_name.replace('_', ' ').title()
        else:
            name_readable = test_name
        max_widths[1] = max(max_widths[1], len(name_readable))
        
        detailed_data.append([suite_readable, name_readable, status, details.replace('|', '/')])

    total_col_widths = [w + 2 for w in max_widths] 

    detail_table = "\n### Detailed Test Report\n\n"
    sep = "".join(f"|{'-' * w}" for w in total_col_widths) + "|\n"
    header = "".join(f"|{header_row[i].center(total_col_widths[i])}" for i in range(4)) + "|\n"

    detail_table += sep + header + sep

    for row in detailed_data:
        wrapped_details = textwrap.wrap(row[3], width=MAX_DETAILS_WIDTH)
        if not wrapped_details:
            wrapped_details = [""]

        line_1 = (f"|{row[0].ljust(total_col_widths[0])}"
                f"|{row[1].ljust(total_col_widths[1])}"
                f"|{row[2].center(total_col_widths[2])}"
                f"| {wrapped_details[0].ljust(MAX_DETAILS_WIDTH)} |\n")
        detail_table += line_1
        
        for extra_line in wrapped_details[1:]:
            detail_table += (f"|{' ' * total_col_widths[0]}"
                            f"|{' ' * total_col_widths[1]}"
                            f"|{' ' * total_col_widths[2]}"
                            f"| {extra_line.ljust(MAX_DETAILS_WIDTH)} |\n")
        
    detail_table += sep
    return summary + detail_table


# ==============================================================================
# 3. Custom Test Runner Class
# ==============================================================================
class CustomTestRunner(unittest.TextTestRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(stream=sys.stderr, *args, **kwargs)
        self.resultclass = CustomTestResult 
        self.verbosity = 2

    def run(self, test):
        result = super().run(test)
        print("\n" + "="*80)
        print("FINAL TEST EXECUTION SUMMARY")
        print("="*80)
        print(format_results_table(result.all_results, result.testsRun))
        print("="*80 + "\n")
        return result


def run_version_check(file_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            [sys.executable, file_path, '-v'],
            capture_output=True, text=True, encoding='utf-8', check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.strip()
        return f"ERROR: Version tag not found in output for {file_path}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: Subprocess failed for {file_path}. Stderr: {e.stderr.strip()}"
    except Exception as e:
        return f"FATAL ERROR checking {file_path}: {e}"

def execute_version_check():
    print("=" * 60)
    print("🔄 PROJECT VERSION SYNCHRONIZATION CHECK")
    print("=" * 60)
    
    project_root = Path(__file__).resolve().parent.parent
    versions: Dict[str, str] = {}
    
    for filename in VERSION_CHECK_FILES:
        filepath = project_root / filename
        if not filepath.exists():
            versions[filename] = f"FILE NOT FOUND at {filepath.name}"
            continue
        version_string = run_version_check(str(filepath.resolve()))
        versions[filename] = version_string
        
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
        for v in sorted(list(unique_versions)):
            print(f"  - {v}")
    print("\n" + "=" * 60)


def run_tests():
    print("=" * 60)
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module_name in TEST_MODULES:
        try:
            module = __import__(module_name)
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                    suite.addTest(loader.loadTestsFromTestCase(obj))
        except ImportError as e:
            print(f"ERROR: Could not import test module {module_name}: {e}")
            continue 
            
    runner = CustomTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root)) 

    # SETUP ARGS FIRST - Critical for clean version check
    parser = argparse.ArgumentParser(description="Test Runner")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--get_versions', action='store_true')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Test Runner")
        sys.exit(0)
    
    if args.get_versions:
        # Run check immediately without logging overhead
        execute_version_check()
    else:
        # SETUP LOGGING only when running actual tests
        log_file_path = project_root / "test_run.log.txt"
        log_file = open(log_file_path, "w", encoding="utf-8")
        
        # Redirect streams to Tee (writes to console AND file)
        sys.stdout = Tee(sys.stdout, log_file)
        sys.stderr = Tee(sys.stderr, log_file)

        try:
            print(f"Logging test results to: {log_file_path}")
            print(f"Timestamp: {datetime.datetime.now()}")
            run_tests()
        finally:
            log_file.close()