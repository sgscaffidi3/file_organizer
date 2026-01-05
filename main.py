# ==============================================================================
# File: main.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial implementation.",
    "Integrated all pipeline components (scanner, processor, deduplicator, migrator).",
    "Added graceful version check and orchestrator logic structure.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "COMPLETE REFACTOR: Implemented full PipelineOrchestrator class.",
    "FEATURE: Integrated FileScanner, MetadataProcessor, Deduplicator, Migrator, and Generators.",
    "CLI: Added flags for --scan, --meta, --dedupe, --migrate, --report, and --all.",
    "SAFETY: Added Database existence checks before running dependent stages.",
    "FEATURE: Added --serve flag to launch the Flask Web Dashboard.",
    "CLI: Added --db flag to override database path (useful for viewing clean_index.sqlite)."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.6.11
# ------------------------------------------------------------------------------
import sys
import argparse
import time
from pathlib import Path

# --- Project Dependencies ---
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    import config
    from config_manager import ConfigManager
    from database_manager import DatabaseManager
    from file_scanner import FileScanner
    from metadata_processor import MetadataProcessor
    from deduplicator import Deduplicator
    from migrator import Migrator
    from report_generator import ReportGenerator
    from html_generator import HTMLGenerator
    from server import run_server
    from version_util import print_version_info
except ImportError as e:
    print(f"CRITICAL: Failed to import project modules. {e}")
    sys.exit(1)

class PipelineOrchestrator:
    """
    Coordinates the execution of the File Organizer pipeline stages.
    """
    def __init__(self, db_override=None):
        self.config_mgr = ConfigManager()
        if db_override:
            self.db_path = Path(db_override)
        else:
            self.db_path = self.config_mgr.OUTPUT_DIR / 'metadata.sqlite'
        
    def _print_header(self, title: str):
        print("\n" + "="*60)
        print(f" {title.upper()}")
        print("="*60)

    def verify_db_exists(self) -> bool:
        if not self.db_path.exists():
            print(f"ERROR: Database not found at {self.db_path}")
            return False
        return True

    def run_scan(self):
        self._print_header("Stage 1: File Scanning")
        self.config_mgr.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        with DatabaseManager(self.db_path) as db:
            db.create_schema()
            scanner = FileScanner(db, self.config_mgr.SOURCE_DIR, self.config_mgr.FILE_GROUPS)
            scanner.scan_and_insert()

    def run_metadata(self):
        self._print_header("Stage 2: Metadata Extraction")
        if not self.verify_db_exists(): return
        
        with DatabaseManager(self.db_path) as db:
            processor = MetadataProcessor(db, self.config_mgr)
            processor.process_metadata()

    def run_dedupe(self):
        self._print_header("Stage 3: Deduplication & Path Calculation")
        if not self.verify_db_exists(): return

        with DatabaseManager(self.db_path) as db:
            deduper = Deduplicator(db, self.config_mgr)
            deduper.run_deduplication()

    def run_migrate(self):
        self._print_header("Stage 4: Migration (Copy & Export)")
        if not self.verify_db_exists(): return

        mode_str = "DRY RUN (Simulation)" if config.DRY_RUN_MODE else "LIVE RUN (Real Copy)"
        print(f"Mode: {mode_str}")
        
        with DatabaseManager(self.db_path) as db:
            migrator = Migrator(db, self.config_mgr)
            migrator.run_migration()

    def run_report(self):
        self._print_header("Stage 5: Reporting")
        if not self.verify_db_exists(): return

        with DatabaseManager(self.db_path) as db:
            reporter = ReportGenerator(db)
            reporter.print_full_report()
            
    def run_server(self):
        self._print_header("Web Interface")
        # Temporarily override config output dir if looking at a custom DB
        # This hack ensures the server looks at the right DB file
        
        # We actually need to pass the specific DB path to the server runner
        # But server.py currently assumes Config.OUTPUT_DIR / metadata.sqlite
        # So we must modify ConfigManager instance or Server logic.
        # EASIEST: Just monkey-patch the config manager instance for this run.
        
        # Point the config's output directory to the PARENT of the provided DB file
        # effectively making the provided DB the 'metadata.sqlite' of that context?
        # No, that's messy.
        
        # Better: Update server.py to accept an explicit DB path (Already done in previous steps? Let's check)
        # server.py's run_server accepts `config_manager`.
        # We need to tell server.py to use `self.db_path`.
        
        # UPDATE: I will modify server.py slightly to accept db_path override in run_server
        # For now, I will modify the global variable in server via the import.
        import server
        server.DB_PATH = self.db_path
        server.run_server(self.config_mgr)

    def run_all(self):
        start_time = time.time()
        print(f"Starting Full Pipeline Run on: {self.config_mgr.SOURCE_DIR}")
        
        self.run_scan()
        self.run_metadata()
        self.run_dedupe()
        self.run_migrate()
        self.run_report()
        
        elapsed = time.time() - start_time
        print(f"\nPipeline Completed in {elapsed:.2f} seconds.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="File Organizer Pipeline Orchestrator")
    
    # Mode Flags
    parser.add_argument('--scan', action='store_true', help="Step 1: Scan source directory and hash files.")
    parser.add_argument('--meta', action='store_true', help="Step 2: Extract rich metadata.")
    parser.add_argument('--dedupe', action='store_true', help="Step 3: Identify duplicates.")
    parser.add_argument('--migrate', action='store_true', help="Step 4: Copy files and Export Clean DB.")
    parser.add_argument('--report', action='store_true', help="Step 5: Generate Console report.")
    parser.add_argument('--serve', action='store_true', help="Step 6: Launch Web Dashboard.")
    parser.add_argument('--all', action='store_true', help="Run the FULL pipeline.")
    
    # Options
    parser.add_argument('--db', type=str, help="Override database path (e.g. for viewing export).")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Main Pipeline Orchestrator")
        sys.exit(0)

    # Initialize with DB Override if provided
    orchestrator = PipelineOrchestrator(db_override=args.db)
    
    if not any([args.scan, args.meta, args.dedupe, args.migrate, args.report, args.all, args.serve]):
        parser.print_help()
        sys.exit(0)

    if args.all:
        orchestrator.run_all()
    else:
        if args.scan: orchestrator.run_scan()
        if args.meta: orchestrator.run_metadata()
        if args.dedupe: orchestrator.run_dedupe()
        if args.migrate: orchestrator.run_migrate()
        if args.report: orchestrator.run_report()
        if args.serve: orchestrator.run_server()