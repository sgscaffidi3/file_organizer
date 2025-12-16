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
    "Minor version bump to 0.3 to synchronize with highest version in the project."
]
# ------------------------------------------------------------------------------
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
        raise ImportError(f"Could not find module spec for {filepath}")
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    # Execute the module's code to populate its variables
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # Ignore common errors that halt execution but still allow version reading
        if 'unittest.main' in str(e) or 'NameError' in str(e) or 'sqlite3.OperationalError' in str(e):
             pass
        else:
             print(f"Warning: Failed to fully execute module {module_name} for version check: {e}")
             
    return module

def _get_version_parts_by_import(filepath: Path) -> Tuple[int, int, int]:
    """
    Dynamically imports the module and extracts _MAJOR_VERSION, _MINOR_VERSION,
    and calculates PATCH as the length of _CHANGELOG_ENTRIES.
    """
    module = _load_module_by_path(filepath)
    
    major = getattr(module, '_MAJOR_VERSION', 0)
    minor = getattr(module, '_MINOR_VERSION', 0)
    
    # CRITICAL: Patch is now the length of the list.
    changelog_list: List[str] = getattr(module, '_CHANGELOG_ENTRIES', [])
    patch = len(changelog_list)
    
    return major, minor, patch

# --- Main Public Function ---

def print_version_info(filepath: str, component_name: str):
    """
    Assembles and prints the standardized version string using dynamic import.
    """
    file_path_obj = Path(filepath)
    
    # Check if this is the version utility itself, which is a special case
    if file_path_obj.name == 'version_util.py':
        major = _MAJOR_VERSION
        minor = _MINOR_VERSION
        changelog_list = _CHANGELOG_ENTRIES
    else:
        try:
            major, minor, patch = _get_version_parts_by_import(file_path_obj)
            
            # Reload the module to get the changelog list for printing
            module = _load_module_by_path(file_path_obj)
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
    print("\nCHANGELOG:")
    for i, entry in enumerate(changelog_list, 1):
        # Print the changelog entries clearly with index.
        print(f"    {i}. {entry}")


# Self-check logic for version_util.py itself
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        current_file = Path(__file__).resolve()
        
        # We manually use the global variables for the self-check (simplest path)
        major = _MAJOR_VERSION
        minor = _MINOR_VERSION
        patch = len(_CHANGELOG_ENTRIES)
        
        print(f"Component: Version Utility")
        print(f"Project: {current_file.parent.name}")
        print(f"Version: {major}.{minor}.{patch}")
        sys.exit(0)