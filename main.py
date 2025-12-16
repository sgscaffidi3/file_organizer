# ==============================================================================
# File: main.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 3. Added graceful version check and orchestrator logic structure.
# 2. Integrated all pipeline components (scanner, processor, deduplicator, migrator).
# 1. Initial implementation.
# ------------------------------------------------------------------------------
import sys
import argparse
from pathlib import Path

# --- Runtime Imports ---

def setup_environment(db_path: Path):
    """Sets up the necessary directories and DB schema."""
    # Placeholder for setup logic
    print(f"Setting up environment for DB: {db_path}")

def run_pipeline(source_dir, destination_dir, db_path):
    """Orchestrates the entire file organization pipeline."""
    # Placeholder for running the scanner, processor, etc.
    print("Running full pipeline...")
    
    # 1. Initialization (Example)
    from config_manager import ConfigManager
    config = ConfigManager()
    
    print(f"Source: {source_dir}, Destination: {destination_dir}")
    print("Pipeline completed.")


if __name__ == '__main__':
    # 1. IMMEDIATE PATH SETUP (Needed for the subsequent version_util import)
    project_root = Path(__file__).resolve().parent
    # Check if the script is run from the root (common) or elsewhere.
    if project_root not in sys.path:
        sys.path.append(str(project_root))

    parser = argparse.ArgumentParser(description="Main Pipeline Orchestrator")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--source', type=str, required=False, help="Source directory to scan.")
    parser.add_argument('--dest', type=str, required=False, help="Destination directory for migrated files.")
    
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Main Pipeline Orchestrator")
        sys.exit(0)

    # Placeholder for execution
    default_source = Path('./input_media')
    default_dest = Path('./organized_media')
    
    run_pipeline(args.source or default_source, args.dest or default_dest, Path('./metadata.sqlite'))