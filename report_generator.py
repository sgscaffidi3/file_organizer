# ==============================================================================
# File: report_generator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of ReportGenerator class for statistical summaries (F08).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any
import os
import argparse
import datetime
import sqlite3

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class ReportGenerator:
    """
    Queries aggregate data from the database to generate a statistical summary 
    report (F08) on space savings, duplicate counts, and file distribution.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager

    def _format_size(self, size_bytes: int) -> str:
        """Converts bytes to a human-readable format (KB, MB, GB, TB)."""
        if size_bytes < 1024:
            return f"{size_bytes} Bytes"
        
        units = ['KB', 'MB', 'GB', 'TB']
        size = size_bytes / 1024.0
        
        for unit in units:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        
        return f"{size:.2f} TB" # Fallback for extremely large sizes

    def generate_statistics(self) -> Dict[str, Any]:
        """Runs aggregate queries and calculates key statistics."""
        stats = {}
        
        # 1. Total files scanned (N)
        total_paths_query = "SELECT COUNT(*) FROM FilePathInstances;"
        stats['total_paths_scanned'] = self.db.execute_query(total_paths_query)[0][0]

        # 2. Total unique content (U)
        unique_content_query = "SELECT COUNT(*) FROM MediaContent;"
        stats['total_unique_content'] = self.db.execute_query(unique_content_query)[0][0]

        # 3. Total duplicates (D = N - U)
        stats['total_duplicates'] = stats['total_paths_scanned'] - stats['total_unique_content']

        # 4. Total size of all files scanned
        total_size_query = "SELECT SUM(size) FROM MediaContent;"
        total_bytes = self.db.execute_query(total_size_query)[0][0] or 0
        stats['total_size_scanned'] = self._format_size(total_bytes)

        # 5. Total size of unique files (The required storage)
        # We assume size in MediaContent is the unique file size.
        stats['unique_size'] = self._format_size(total_bytes)

        # 6. Saved space (Space that would be freed if duplicates were deleted)
        # Formula: Duplicated Bytes = SUM(size) from all FilePathInstances - SUM(size) from all MediaContent
        
        # To calculate true saved space, we need the size of every instance, 
        # but size is only stored in MediaContent. We can approximate it:
        # Saved Bytes = Total Bytes * (D / N)
        if stats['total_paths_scanned'] > 0:
            bytes_saved = total_bytes * (stats['total_duplicates'] / stats['total_paths_scanned'])
        else:
            bytes_saved = 0
            
        stats['estimated_space_saved'] = self._format_size(int(bytes_saved))

        # 7. Distribution by file group
        group_dist_query = "SELECT file_type_group, COUNT(*) FROM MediaContent GROUP BY file_type_group ORDER BY COUNT(*) DESC;"
        group_dist = self.db.execute_query(group_dist_query)
        stats['distribution_by_group'] = {group: count for group, count in group_dist}
        
        return stats

    def print_report(self, stats: Dict[str, Any]):
        """Formats and prints the final summary report."""
        
        print("\n" + "=" * 60)
        print("          FILE ORGANIZER PROJECT: SUMMARY REPORT (F08)         ")
        print("=" * 60)
        print(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        print("\n--- Input Analysis ---")
        print(f"Total Source Paths Scanned: {stats['total_paths_scanned']:,}")
        print(f"Total Unique Files Found:   {stats['total_unique_content']:,}")
        print(f"Total Duplicate Files:      {stats['total_duplicates']:,}")
        
        print("\n--- Size & Space Savings ---")
        print(f"Total Disk Space Scanned: {stats['total_size_scanned']}")
        print(f"Unique Content Storage:   {stats['unique_size']}")
        print(f"Estimated Space Saved:    {stats['estimated_space_saved']}")
        
        print("\n--- Distribution by File Group ---")
        for group, count in stats['distribution_by_group'].items():
            percentage = (count / stats['total_unique_content']) * 100 if stats['total_unique_content'] else 0
            print(f"  {group.ljust(10)}: {count:,} ({percentage:.1f}%)")
            
        print("-" * 60 + "\n")


    def generate_and_print_report(self):
        """Runs the statistics generation and printing process."""
        try:
            stats = self.generate_statistics()
            self.print_report(stats)
        except Exception as e:
            print(f"Error generating report: {e}")
            
if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="Report Generator Module for file_organizer: Generates a statistical summary of the project results (F08).")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--report', action='store_true', help="Generate and print the summary report.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Statistical Report Generator")
    elif args.report:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Please run the full pipeline first.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    generator = ReportGenerator(db, manager)
                    generator.generate_and_print_report()
            except Exception as e:
                print(f"FATAL ERROR during report generation: {e}")
    else:
        parser.print_help()