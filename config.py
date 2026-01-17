# ==============================================================================
# File: config.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_REL_CHANGES = [12]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
# ------------------------------------------------------------------------------
from pathlib import Path
import argparse
import sys
import os
from version_util import print_version_info
from config_manager import ConfigManager 

# --- Execution Settings ---
DRY_RUN_MODE = False           # If True, no files are copied/moved/deleted (N03).
BLOCK_SIZE = 1048576          # Chunk size (1MB).

# --- Threading Configuration ---
# Auto-detect CPU cores, cap at 32 to prevent system instability.
CPU_CORES = os.cpu_count() or 4

# Hashing: IO intensive (Read)
HASHING_THREADS = min(CPU_CORES, 32)

# Metadata: CPU + IO intensive (Read + Parse)
METADATA_THREADS = min(CPU_CORES * 2, 32) # Can usually handle more than cores due to IO wait

# Migration: Pure IO (Read/Write)
# CAUTION: High thread counts on mechanical HDDs will cause thrashing.
MIGRATION_THREADS = min(CPU_CORES, 16)

# --- Path Definitions ---
CONFIG_MANAGER = ConfigManager()
DATABASE_FILE = CONFIG_MANAGER.OUTPUT_DIR / 'metadata.sqlite' 


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configuration file for the file_organizer Project. Holds static execution settings.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        print_version_info(__file__, "Static Configuration and Global Settings")
        sys.exit(0)
    else:
        parser.print_help()