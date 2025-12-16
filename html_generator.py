# ==============================================================================
# File: html_generator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation of HTMLGenerator class for static output visualization (F09).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check."
]
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import os
import argparse
import datetime
import sqlite3

import config
from database_manager import DatabaseManager
from version_util import print_version_info
from config_manager import ConfigManager 

class HTMLGenerator:
    """
    Queries the final organized data from the database and generates a static 
    HTML file to allow browsing of the new media structure (F09).
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.files_reported = 0

    def _get_organized_media_data(self) -> List[Tuple]:
        """
        Queries the database for all successfully migrated and named files, 
        ordered by their final path.
        """
        # Note: This query assumes new_path_id contains the final relative path
        query = """
        SELECT content_hash, file_type_group, date_best, new_path_id, size, width, height 
        FROM MediaContent 
        WHERE new_path_id IS NOT NULL 
        ORDER BY new_path_id ASC;
        """
        return self.db.execute_query(query)

    def _generate_html_body(self, data: List[Tuple]) -> str:
        """Generates the HTML table rows containing file data."""
        html_rows = ""
        self.files_reported = len(data)

        for content_hash, file_type_group, date_best, new_path_id, size, width, height in data:
            # Format size to human-readable string (e.g., 1.5 MB)
            size_kb = size / 1024
            size_str = f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"
            
            # Use only the relative file path for display
            relative_path = Path(new_path_id).name
            
            # Simple icon based on file type
            icon = '🖼️' if file_type_group == 'IMAGE' else \
                   '🎬' if file_type_group == 'VIDEO' else \
                   '📄' if file_type_group == 'DOCUMENT' else '📁'

            html_rows += f"""
            <tr>
                <td>{icon}</td>
                <td><a href="{new_path_id}">{relative_path}</a></td>
                <td>{file_type_group}</td>
                <td>{date_best[:10]}</td>
                <td>{size_str}</td>
                <td>{width if width else '-'}x{height if height else '-'}</td>
                <td>{content_hash[:8]}...</td>
            </tr>
            """
        return html_rows

    def generate_html_report(self):
        """Main method to generate the static HTML file."""
        
        # 1. Get the data
        try:
            data = self._get_organized_media_data()
        except sqlite3.OperationalError:
            print("Error: Could not query database. Ensure schema is initialized and data exists.")
            return

        html_body_rows = self._generate_html_body(data)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Organizer - Organized Media Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>File Organizer: Organized Media (Total Files: {self.files_reported})</h2>
        <p>Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <p>This report lists all unique files copied to the output directory and their calculated destination paths. Click the file name to view the file in the new location.</p>
    
    <table>
        <thead>
            <tr>
                <th>Type</th>
                <th>Final Filename (Relative Path)</th>
                <th>Group</th>
                <th>Date Best</th>
                <th>Size</th>
                <th>Dimensions</th>
                <th>Hash ID</th>
            </tr>
        </thead>
        <tbody>
            {html_body_rows}
        </tbody>
    </table>
</body>
</html>
"""

        # 2. Write the file to the output directory
        report_file = self.output_dir / "organized_media_report.html"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML Report generated successfully: {report_file.resolve()}")
        except IOError as e:
            print(f"Error writing HTML report: {e}")

if __name__ == "__main__":
    manager = ConfigManager()
    
    parser = argparse.ArgumentParser(description="HTML Generator Module for file_organizer: Creates static HTML output of organized files (F09).")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--generate', action='store_true', help="Generate the static HTML report.")
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "HTML Report Generator")
    elif args.generate:
        db_path = manager.OUTPUT_DIR / 'metadata.sqlite'
        if not db_path.exists():
            print(f"Error: Database file not found at {db_path}. Please run the full pipeline first.")
        else:
            try:
                # Use a dummy context manager to ensure the DatabaseManager is properly closed
                with DatabaseManager(db_path) as db:
                    generator = HTMLGenerator(db, manager)
                    generator.generate_html_report()
            except Exception as e:
                print(f"FATAL ERROR during HTML generation: {e}")
    else:
        parser.print_help()