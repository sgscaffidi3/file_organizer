# ==============================================================================
# File: main.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the main project orchestrator.
# ------------------------------------------------------------------------------
import argparse
import sys
from pathlib import Path

# Import all core modules
import config
from config_manager import ConfigManager 
from database_manager import DatabaseManager
from file_scanner import FileScanner
from metadata_processor import MetadataProcessor
from deduplicator import Deduplicator
from migrator import Migrator
from report_generator import ReportGenerator
from html_generator import HTMLGenerator
from version_util import print_version_info

class FileOrganizerPipeline:
    """Orchestrates the execution of the File Organizer project modules."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.db_path = self.config_manager.OUTPUT_DIR / 'metadata.sqlite'
        self.db_manager = DatabaseManager(self.db_path)

    def run_stage(self, stage_name: str, stage_function):
        """Standard wrapper to execute a pipeline stage with database context."""
        print(f"\n--- 🚀 Starting Stage: {stage_name} ---")
        try:
            # Re-establish connection/cursor for each stage to ensure isolation/visibility
            with DatabaseManager(self.db_path) as db: 
                # Re-instantiate the module with the active db manager
                if stage_name == "Scanning":
                    module = FileScanner(db, self.config_manager.SOURCE_DIR, self.config_manager.FILE_GROUPS)
                elif stage_name == "Metadata Extraction":
                    module = MetadataProcessor(db, self.config_manager)
                elif stage_name == "Deduplication & Path Calculation":
                    module = Deduplicator(db, self.config_manager)
                elif stage_name == "Migration":
                    module = Migrator(db, self.config_manager)
                else:
                    module = None # Should not happen

                # Execute the main function of the module
                if module:
                    stage_function(module)
                
            print(f"--- ✅ Stage {stage_name} Complete ---\n")
            return True
        except Exception as e:
            print(f"--- ❌ Stage {stage_name} Failed: {e} ---")
            return False

    def setup_database(self):
        """Initializes the database schema."""
        print("\n--- 💾 Setting up Database Schema ---")
        try:
            with DatabaseManager(self.db_path) as db:
                db.create_schema()
                print("Database schema created/verified.")
            print("--- ✅ Database Setup Complete ---\n")
            return True
        except Exception as e:
            print(f"--- ❌ Database Setup Failed: {e} ---")
            return False


    def run_full_pipeline(self):
        """Executes the entire workflow in sequence."""
        
        # 1. Setup
        if not self.setup_database():
            return
            
        # 2. Processing Stages
        stages = [
            ("Scanning", lambda m: m.scan_and_insert()),
            ("Metadata Extraction", lambda m: m.process_metadata()),
            ("Deduplication & Path Calculation", lambda m: m.run_deduplication()),
            ("Migration", lambda m: m.run_migration()),
        ]

        for name, func in stages:
            if not self.run_stage(name, func):
                print(f"Pipeline stopped due to error in {name} stage.")
                return

        # 3. Reporting Stages (Run outside the standard run_stage wrapper, 
        # as they handle their own printing/file writing)
        print("\n--- 📄 Starting Reporting and HTML Generation ---")
        with DatabaseManager(self.db_path) as db:
            
            # F08: Generate Statistical Report
            report = ReportGenerator(db, self.config_manager)
            report.generate_and_print_report()
            
            # F09: Generate HTML Report
            html = HTMLGenerator(db, self.config_manager)
            html.generate_html_report()
            
        print("--- 🏁 Pipeline Execution Finished Successfully ---")
        print(f"Output directory: {self.config_manager.OUTPUT_DIR.resolve()}")
        print(f"DRY RUN MODE: {'ON' if config.DRY_RUN_MODE else 'OFF'}")


def main():
    """Main command-line entry point."""
    
    parser = argparse.ArgumentParser(description="File Organizer: Automated media organization and deduplication utility.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information for the main script and exit.')
    parser.add_argument('--full-run', action='store_true', help='Execute the entire end-to-end pipeline (Setup -> Scan -> Process -> Dedupe -> Migrate -> Report).')
    
    # Subcommands for individual stage execution (for advanced users/debugging)
    subparsers = parser.add_subparsers(dest='command', help='Specific stage execution.')
    
    # Init subcommand
    subparsers.add_parser('init', help='Initialize the database schema only.')

    # Teardown subcommand
    subparsers.add_parser('teardown', help='Delete the database file and exit.')

    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Main Pipeline Orchestrator")
        return

    pipeline = FileOrganizerPipeline()

    if args.command == 'init':
        pipeline.setup_database()
    elif args.command == 'teardown':
        if pipeline.db_manager.teardown():
            print(f"Database file successfully deleted at {pipeline.db_path}.")
        else:
            print(f"Database file not found at {pipeline.db_path}.")
    elif args.full_run:
        pipeline.run_full_pipeline()
    else:
        # Default behavior is to show help
        parser.print_help()


if __name__ == "__main__":
    main()