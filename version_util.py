# ==============================================================================
# File: version_util.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 5
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "Updated print_version_info to handle file reading for version detection.",
    "Implemented 'utf-8' encoding on file reads.",
    "Refactored versioning logic to use dynamic import of '_CHANGELOG_ENTRIES' list for patch determination (length of the list).",
    "Removed all comment-parsing logic, ensuring reliability of patch number calculation.",
    "Added 'import sys' and 'sys.exit(0)' to self-check for clean exit.",
    "Minor version bump to 0.3 to synchronize with highest version in the project.",
    "Added --get_all command to audit the version and format status of all files.",
    "CRITICAL FIX: Updated VERSION_CHECK_FILES to correctly locate test files within the 'test' subdirectory.",
    "Formatting fix: Increased the width of the 'FILE' column in the --get_all audit output.",
    "REFACTOR: Removed hardcoded file list. Implemented dynamic recursive scanning for .py files.",
    "FEATURE: Added --get_change_counts command to report historical changes using _REL_CHANGES list.",
    "LOGIC: Update audit to check if MINOR_VERSION matches the Master Config.",
    "FEATURE: Added print_change_history() to support the new --changes CLI flag across the project."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Optional, Tuple, List, Generator
import sys
import argparse
import importlib.util

# Config dependency for Master Version check
try:
    from config_manager import ConfigManager
except ImportError:
    ConfigManager = None

def get_python_files(root: Path) -> Generator[Path, None, None]:
    """Recursively finds all .py files, ignoring venv and pycache."""
    for path in root.rglob("*.py"):
        # Filter out unwanted directories
        parts = path.parts
        if 'venv' in parts or '.venv' in parts or '__pycache__' in parts or '.git' in parts:
            continue
        yield path

def _load_module_by_path(filepath: Path):
    """Dynamically loads a module given its file path."""
    module_name = filepath.stem
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None:
        raise ImportError(f"Could not load spec for {filepath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module 
    spec.loader.exec_module(module)
    return module

def get_all_file_versions(project_root: Path):
    """Audits version status of all files against Master Config."""
    
    # Get Master Version
    master_minor = -1
    if ConfigManager:
        try:
            _, master_minor = ConfigManager(project_root / 'organizer_config.json').PROJECT_VERSION
        except: pass

    SEPARATOR_WIDTH = 110
    FILE_WIDTH = 45
    VERSION_WIDTH = 15
    STATUS_WIDTH = 45

    print("=" * SEPARATOR_WIDTH)
    print("PROJECT VERSION AUDIT")
    print(f"Root: {project_root.resolve()}")
    if master_minor != -1:
        print(f"Master Config Target Minor Version: {master_minor}")
    print("=" * SEPARATOR_WIDTH)
    
    print(f"{'FILE':<{FILE_WIDTH}}{'VER (M.m.P)':<{VERSION_WIDTH}}{'STATUS':<{STATUS_WIDTH}}")
    print("-" * SEPARATOR_WIDTH)

    for filepath in get_python_files(project_root):
        rel_path = str(filepath.relative_to(project_root))
        
        try:
            module = _load_module_by_path(filepath)
            major = getattr(module, '_MAJOR_VERSION', '?')
            minor = getattr(module, '_MINOR_VERSION', '?')
            
            patch = "?"
            if hasattr(module, '_CHANGELOG_ENTRIES'):
                patch = len(getattr(module, '_CHANGELOG_ENTRIES'))
            
            full_ver = f"{major}.{minor}.{patch}"
            
            status = []
            if minor != master_minor and master_minor != -1:
                status.append(f"MINOR MISMATCH (Exp {master_minor})")
            
            if not hasattr(module, '_REL_CHANGES'):
                status.append("NO HISTORY TRACKING")
                
            status_str = ", ".join(status) if status else "✅ OK"
            
            print(f"{rel_path:<{FILE_WIDTH}}{full_ver:<{VERSION_WIDTH}}{status_str:<{STATUS_WIDTH}}")

        except Exception as e:
            print(f"{rel_path:<{FILE_WIDTH}}{'ERR':<{VERSION_WIDTH}}{str(e):<{STATUS_WIDTH}}")
            
    print("=" * SEPARATOR_WIDTH)

def print_change_history(file_path: str, arg_value: str):
    """
    Handles the --changes command.
    arg_value: 'all' (const) or an integer string.
    """
    file_path_obj = Path(file_path).resolve()
    try:
        module = _load_module_by_path(file_path_obj)
        rel_changes = getattr(module, '_REL_CHANGES', [])
        current_log = getattr(module, '_CHANGELOG_ENTRIES', [])
        major = getattr(module, '_MAJOR_VERSION', 0)
        
        # Mode 1: Grand Total
        if arg_value == 'all' or arg_value is None:
            total = sum(rel_changes) + len(current_log)
            print(f"Total Changes: {total}")
            print(f"  - Historical Releases: {sum(rel_changes)}")
            print(f"  - Current Pending:     {len(current_log)}")
            return

        # Mode 2: Specific Release Index
        try:
            idx = int(arg_value)
            if 0 <= idx < len(rel_changes):
                count = rel_changes[idx]
                # Format: Major.ListPosition.Count
                print(f"Release v{major}.{idx}.{count} Changes: {count}")
            else:
                print(f"Error: Release index {idx} out of range. History length: {len(rel_changes)}")
        except ValueError:
            print(f"Error: Invalid argument for --changes: {arg_value}")

    except Exception as e:
        print(f"Error reading change history for {file_path}: {e}")

def print_version_info(file_path: str, component_name: str, print_changelog: bool = True):
    """Prints version info for a single file."""
    file_path_obj = Path(file_path).resolve()
    
    try:
        module = _load_module_by_path(file_path_obj)
        major = getattr(module, '_MAJOR_VERSION', 'ERR')
        minor = getattr(module, '_MINOR_VERSION', 'ERR')
        changelog_list = getattr(module, '_CHANGELOG_ENTRIES', [])
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    full_version = f"{major}.{minor}.{len(changelog_list)}"
    print(f"Component: {component_name}")
    print(f"Version: {full_version}")
    
    if print_changelog:
        print("\nCHANGELOG:")
        for i, entry in enumerate(changelog_list, 1):
            print(f"    {i}. {entry}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information.')
    parser.add_argument('--get_all', action='store_true', help='Audit all project files.')
    # This script itself supports the new standard
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent 

    if args.version:
        print_version_info(__file__, "Version Utility")
        sys.exit(0)
    
    if args.changes:
        print_change_history(__file__, args.changes)
        sys.exit(0)

    if args.get_all:
        get_all_file_versions(project_root)
        sys.exit(0)