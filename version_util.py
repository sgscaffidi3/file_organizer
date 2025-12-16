# ==============================================================================
# File: version_util.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 7. CRITICAL FIX: Explicitly set encoding='utf-8' on all file opens to resolve 'charmap' codec errors.
# 6. Added logic to dynamically calculate patch version based on CHANGELOG count.
# 5. Updated version print logic to look for _MAJOR_VERSION and _MINOR_VERSION.
# 4. Refined version string format for consistent parsing by test runner.
# 3. Added __file__ parameter to print_version_info for accurate file reading.
# 2. Updated print_version_info to handle file reading for version detection.
# 1. Initial implementation.
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Optional
import sys
import argparse

def _calculate_version_parts(filepath: Path) -> tuple[int, int, int]:
    """
    Extracts major/minor versions from global variables and calculates
    the patch version from the CHANGELOG.
    """
    major_version = 0
    minor_version = 0
    patch_count = 0
    in_changelog = False
    
    try:
        # CRITICAL FIX: Ensure 'utf-8' encoding is used for reading the file contents
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                
                # 1. Extract Major and Minor from the file's header variables
                if line.startswith('_MAJOR_VERSION'):
                    major_version = int(line.split('=')[1].strip())
                    continue
                elif line.startswith('_MINOR_VERSION'):
                    minor_version = int(line.split('=')[1].strip())
                    continue
                
                # 2. Start counting changes
                if stripped_line == 'CHANGELOG:':
                    in_changelog = True
                    continue
                
                if in_changelog:
                    # Look for lines that start with a number followed by a period.
                    if stripped_line.startswith(tuple(str(i) + '.' for i in range(1, 10))):
                        patch_count += 1
                    
                    # Stop if we hit the end of the changelog section (a non-comment line)
                    if not stripped_line.startswith('#') and stripped_line != '':
                        break
                        
        return major_version, minor_version, patch_count

    except Exception as e:
        # Raise RuntimeError to be caught by print_version_info
        raise RuntimeError(f"Failed to read file parts: {e}")

def _print_changelog(filepath: Path):
    """Reads and prints the CHANGELOG section of a file."""
    in_changelog = False
    
    try:
        # CRITICAL FIX: Ensure 'utf-8' encoding is used for reading the file contents
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                
                if stripped_line == 'CHANGELOG:':
                    in_changelog = True
                    continue
                
                if in_changelog:
                    # Only print lines that look like changelog entries (start with number or #)
                    if stripped_line.startswith(tuple(str(i) + '.' for i in range(1, 20))) or stripped_line.startswith('#'):
                        print(f"{' '*4}{stripped_line}")
                    elif stripped_line == '-':
                        print(f"{' '*4}{stripped_line}")
                    else:
                        # Stop at the first non-changelog line
                        return 
                        
    except Exception:
        print("Could not load changelog.")


def print_version_info(filepath: str, component_name: str):
    """
    Assembles and prints the standardized version string.
    """
    file_path_obj = Path(filepath)
    try:
        major, minor, patch = _calculate_version_parts(file_path_obj)
        
        full_version = f"{major}.{minor}.{patch}"
        
        print(f"Component: {component_name}")
        print(f"Project: {file_path_obj.parent.name}")
        # CRITICAL: THIS OUTPUT MUST REMAIN EXACTLY "Version: X.Y.Z" for the test runner
        print(f"Version: {full_version}")
        print("\nCHANGELOG:")
        _print_changelog(file_path_obj)

    except RuntimeError as e:
        print(f"Component: {component_name}")
        print(f"Project: {file_path_obj.parent.name}")
        print(f"Version: Error reading version: {e}")
        print("\nCHANGELOG:")
        print("Could not load changelog.")
        
    except Exception as e:
        print(f"Component: {component_name}")
        print(f"Project: {file_path_obj.parent.name}")
        print(f"Version: Error printing version info: {e}")
        print("\nCHANGELOG:")
        print("Could not load changelog.")


# Self-check logic for version_util.py itself (simplest possible check)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Version Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        current_file = Path(__file__).resolve()
        
        # We must manually calculate here to avoid circular dependency
        major, minor, patch = _calculate_version_parts(current_file)
        
        print(f"Component: Version Utility")
        print(f"Project: {current_file.parent.name}")
        print(f"Version: {major}.{minor}.{patch}")
        sys.exit(0)