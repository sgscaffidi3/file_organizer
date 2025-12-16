# ==============================================================================
# File: version_util.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "Updated print_version_info to handle file reading for version detection.",
    "Implemented 'utf-8' encoding on file reads.",
    "Refactored versioning logic to use dynamic import of '_CHANGELOG_ENTRIES' list for patch determination (length of the list).",
    "Removed all comment-parsing logic, ensuring reliability of patch number calculation.",
    "Added 'import sys' and 'sys.exit(0)' to self-check for clean exit.",
    "Minor version bump to 0.3 to synchronize with highest version in the project.",
    "Added --get_all command to audit the version and format status of all files.",
]
# ------------------------------------------------------------------------------

# List of all files to check for project-wide version status.
# Copied from test_all.py to make this utility self-contained.
# This list defines the full scope of the project for the --get_all command.
VERSION_CHECK_FILES = [
    "version_util.py",
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
    "test_all.py",
    "test_database_manager.py",
    "test_deduplicator.py",
    "test_file_scanner.py",
    "test_metadata_processor.py",
]

from pathlib import Path
from typing import Optional, Tuple, List
import sys
import argparse
import importlib.util

# --- Helper Functions for Dynamic Import ---

def _load_module_by_path(filepath: Path):
    """Dynamically loads a module given its file path to access its variables."""
    module_name = filepath.stem
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None:
        # Fallback for complex paths or system configurations
        raise ImportError(f"Could not load spec for {filepath}")
        
    module = importlib.util.module_from_spec(spec)
    # CRITICAL: sys.modules must be updated for the imports *inside* the loaded module to work
    sys.modules[module_name] = module 
    
    # Execute the module code
    spec.loader.exec_module(module)
    return module

def get_all_file_versions(project_root: Path):
    """
    Checks the version status of all files in the project and reports the minor version
    and changelog format status in a table. Implements the --get_all command.
    """
    print("=" * 75)
    print("PROJECT VERSION AUDIT: Independent Versioning Status")
    print(f"Project Root: {project_root.resolve()}")
    print("=" * 75)
    print(f"{'FILE':<25}{'VERSION (M.m.P)':<18}{'MINOR (Expected 3)':<18}{'CHANGELOG FORMAT':<18}")
    print("-" * 75)

    for filename in VERSION_CHECK_FILES:
        # Assume all files are in the project_root directory alongside version_util.py
        filepath = project_root / filename
        
        # Check for file existence first
        if not filepath.exists():
             print(f"{filename:<25}{'---':<18}{'N/A':<18}{'FILE NOT FOUND':<18}")
             continue

        try:
            module = _load_module_by_path(filepath)
            
            # 1. Get Major and Minor version (always hardcoded)
            major = getattr(module, '_MAJOR_VERSION', 'ERR')
            minor = getattr(module, '_MINOR_VERSION', 'ERR')
            
            # 2. Check for the Changelog List
            if hasattr(module, '_CHANGELOG_ENTRIES'):
                changelog_list = getattr(module, '_CHANGELOG_ENTRIES')
                # A file using the list format has a Patch count derived from the list length
                patch = len(changelog_list)
                format_status = "✅ LIST-BASED"
            else:
                # If the list is not found, the file is NOT using the new format.
                patch = "???"
                format_status = "❌ COMMENTS/MISSING"

            full_version = f"{major}.{minor}.{patch}"
            minor_status = f"{minor}" if minor == 3 else f"**{minor}**"

            print(f"{filename:<25}{full_version:<18}{minor_status:<18}{format_status:<18}")

        except Exception:
            # Catching dynamic import errors (e.g., if a file has a syntax error)
            print(f"{filename:<25}{'---':<18}{'ERR':<18}{'IMPORT FAILED':<18}")

    print("=" * 75)
    print("\nSUMMARY:")
    print("Minor Version (0.3) needs synchronization in files marked with **.")
    print("Changelog needs conversion to Python list in files marked with ❌.")


def print_version_info(file_path: str, component_name: str, print_changelog: bool = True):
    """
    Prints the version information and changelog for a single file 
    by dynamically loading its variables.
    """
    file_path_obj = Path(file_path).resolve()
    
    try:
        module = _load_module_by_path(file_path_obj)
        
        major = getattr(module, '_MAJOR_VERSION', 'ERR')
        minor = getattr(module, '_MINOR_VERSION', 'ERR')
        # Get the changelog list, defaulting to an empty list if not found
        changelog_list = getattr(module, '_CHANGELOG_ENTRIES', [])
            
    except Exception as e:
        print(f"Component: {component_name}")
        print(f"Project: {file_path_obj.parent.name}")
        print(f"Version: Error printing version info (Import failed): {e}")
        print("\nCHANGELOG:")
        print("    Could not load changelog entries.")
        return

    full_version = f"{major}.{minor}.{len(changelog_list)}"
    
    print(f"Component: {component_name}")
    print(f"Project: {file_path_obj.parent.name}")
    print(f"Version: {full_version}")
    
    if print_changelog:
        print("\nCHANGELOG:")
        for i, entry in enumerate(changelog_list, 1):
            # Print the changelog entries clearly with index.
            print(f"    {i}. {entry}")


# Self-check logic for version_util.py itself
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for this utility and exit.')
    # NEW ARGUMENT: --get_all
    parser.add_argument('--get_all', action='store_true', help='Perform a version audit across all project files.')
    args = parser.parse_args()

    current_file_path = Path(__file__).resolve()
    # The parent directory is the project root, which is where all other files are located.
    project_root = current_file_path.parent 

    if args.version:
        # We manually use the global variables for the self-check (simplest path)
        major = _MAJOR_VERSION
        minor = _MINOR_VERSION
        patch = len(_CHANGELOG_ENTRIES)
        full_version = f"{major}.{minor}.{patch}"
        
        print(f"Component: Version Utility (self-check)")
        print(f"Project: {current_file_path.parent.name}")
        print(f"Version: {full_version}")
        print("\nCHANGELOG:")
        for i, entry in enumerate(_CHANGELOG_ENTRIES, 1):
            print(f"    {i}. {entry}")
            
        sys.exit(0)
    
    elif args.get_all:
        # NEW LOGIC: Audit all files in the project
        get_all_file_versions(project_root)
        sys.exit(0)
        
    else:
        # Default behavior (if no args are passed)
        parser.print_help()
        sys.exit(0)