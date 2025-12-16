# ==============================================================================
# File: config.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Added versioning and changelog structure to all files.",
    "Implemented the versioning and patch derivation strategy.",
    "Implemented --version/-v and --help/-h support for standalone execution.",
    "Refactored to remove dynamic settings (paths, file groups), which are now managed by ConfigManager.",
    "Project name changed to \"file_organizer\" in descriptions.",
    "Added CLI argument parsing for --version to allow clean exit during health checks.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning."
]
# ------------------------------------------------------------------------------
from pathlib import Path
import argparse
import sys
from version_util import print_version_info
from config_manager import ConfigManager 

# --- Execution Settings ---
DRY_RUN_MODE = True           # If True, no files are copied/moved/deleted (N03).
BLOCK_SIZE = 65536            # Chunk size for incremental hashing (64KB).

# --- Path Definitions ---
# The location of the SQLite database file. This is derived from the OUTPUT_DIR
# set in the JSON configuration via the ConfigManager.
CONFIG_MANAGER = ConfigManager()
DATABASE_FILE = CONFIG_MANAGER.OUTPUT_DIR / 'metadata.sqlite' 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configuration file for the file_organizer Project. Holds static execution settings.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Static Configuration and Global Settings")
        sys.exit(0)
    else:
        parser.print_help()