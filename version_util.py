# ==============================================================================
# File: version_util.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation to handle version extraction from file headers.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Project name changed to "file_organizer" in descriptions.
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Tuple

def get_version_info(filepath: Path) -> Tuple[str, str]:
    """
    Reads the file to determine the Major/Minor version and calculates the 
    Patch version by counting CHANGELOG entries.
    Returns: (Full Version String, Changelog History)
    """
    version_major_minor = "0.0"
    changelog = []
    in_changelog = False
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                
                if line.startswith("# Version:"):
                    parts = line.split(':')
                    if len(parts) > 1:
                        version_major_minor = parts[1].strip()
                        
                elif line.startswith("# CHANGELOG:"):
                    in_changelog = True
                
                elif in_changelog and line.startswith("#") and len(line) > 1:
                    # Capture actual changelog entries
                    # Example entry: "# 1. Initial creation..."
                    if line.split(' ')[1].isdigit() and line.split(' ')[2].startswith('.'):
                        changelog.append(line.replace('# ', '', 1).strip())
                    
        patch = len(changelog)
        full_version = f"{version_major_minor}.{patch}"
        
        # Prepare the changelog for display (removing entry numbers)
        changelog_display = []
        for entry in changelog:
            parts = entry.split('.', 1)
            if len(parts) > 1:
                changelog_display.append(parts[1].strip())
            else:
                changelog_display.append(entry)
                
        changelog_text = "\n".join(changelog_display)
        
        return full_version, changelog_text
        
    except Exception as e:
        return f"Error reading version: {e}", "Could not load changelog."


def print_version_info(filepath: str, description: str):
    """Prints the formatted version and changelog information."""
    version, changelog = get_version_info(Path(filepath))
    
    print("-" * 50)
    print(f"{Path(filepath).name} ({description})")
    print(f"Project: file_organizer")
    print(f"Version: {version}")
    print("\nCHANGELOG:")
    print(changelog)
    print("-" * 50)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Version Utility: Reads and displays version information from file headers.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Version Management Utility")
    else:
        parser.print_help()