# ==============================================================================
# File: html_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_CHANGELOG_ENTRIES = [
    "Initial implementation of HTMLGenerator class for static output visualization (F09).",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "FEATURE: Added DataTables integration for instant search, sorting, and pagination.",
    "FEATURE: Added 'Quick Filter' buttons for Media Groups (Images, Video, etc.).",
    "REFACTOR: Full end-to-end implementation with integrated ConfigManager and DatabaseManager.",
    "FIX: Updated SQL query to handle varying date column names (recorded_date vs date_best).",
    "FIX: Robust schema inspection to prevent 'int object is not iterable' errors during PRAGMA check."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.3.8
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import argparse
import datetime
import sqlite3
import sys
import json

# Standard project imports
from database_manager import DatabaseManager
from config_manager import ConfigManager 

class HTMLGenerator:
    """
    Queries the database and generates an interactive 'Media Explorer' HTML file
    using DataTables for advanced searching and filtering (F09).
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.files_reported = 0

    def _get_organized_media_data(self) -> List[Tuple]:
        """
        Queries the database for unique assets. Uses a robust check for the date column.
        """
        # Get table info to see which columns actually exist
        # PRAGMA table_info returns rows like (id, name, type, notnull, dflt_value, pk)
        try:
            columns_res = self.db.execute_query("PRAGMA table_info(MediaContent)")
            # Ensure we are iterating over a list of tuples/rows
            col_names = []
            if isinstance(columns_res, list):
                col_names = [str(col[1]).lower() for col in columns_res if len(col) > 1]
        except Exception:
            col_names = []
        
        # Determine the best available date column
        if "date_best" in col_names:
            date_col = "mc.date_best"
        elif "recorded_date" in col_names:
            date_col = "mc.recorded_date"
        else:
            date_col = "'Unknown'"

        query = f"""
        SELECT 
            mc.content_hash, 
            mc.file_type_group, 
            {date_col}, 
            fpi.original_relative_path, 
            mc.size, 
            mc.width, 
            mc.height 
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        GROUP BY mc.content_hash
        ORDER BY fpi.original_relative_path ASC;
        """
        return self.db.execute_query(query)

    def _generate_html_body(self, data: List[Tuple]) -> str:
        """Generates the HTML table rows containing file data."""
        html_rows = ""
        self.files_reported = len(data)

        for content_hash, group, date, path, size, width, height in data:
            # Format size to human-readable string
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size/1024:.1f} KB"
            
            filename = Path(path).name
            icon = '🖼️' if group == 'IMAGE' else \
                   '🎬' if group == 'VIDEO' else \
                   '🎵' if group == 'AUDIO' else \
                   '📄' if group == 'DOCUMENT' else '📁'

            dim_str = f"{width}x{height}" if width and height else "-"
            display_date = str(date)[:10] if date else "Unknown"

            html_rows += f"""
            <tr>
                <td>{icon} {group}</td>
                <td title="{path}"><code>{filename}</code></td>
                <td>{display_date}</td>
                <td data-order="{size}">{size_str}</td>
                <td>{dim_str}</td>
                <td><small>{content_hash[:8]}</small></td>
            </tr>
            """
        return html_rows

    def generate_html_report(self):
        """Main method to generate the interactive HTML explorer."""
        try:
            data = self._get_organized_media_data()
            if not data:
                print("No data found in database to report.")
                return
        except Exception as e:
            print(f"Error: Could not query database. {e}")
            return

        html_body_rows = self._generate_html_body(data)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Explorer | File Organizer</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f7f6; }}
        .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        .stats {{ color: #7f8c8d; margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px; }}
        table.dataTable thead th {{ background-color: #34495e; color: white; border: none; padding: 15px; }}
        tr:hover {{ background-color: #f1f1f1 !important; transition: 0.2s; }}
        code {{ background: #f8f9fa; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9em; }}
        .footer {{ margin-top: 30px; text-align: center; color: #bdc3c7; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Media Explorer</h1>
        <p class="stats">
            Found <strong>{self.files_reported}</strong> unique assets. 
            Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </p>
        
        <table id="mediaTable" class="display" style="width:100%">
            <thead>
                <tr>
                    <th>Group</th>
                    <th>Filename</th>
                    <th>Date</th>
                    <th>Size</th>
                    <th>Resolution</th>
                    <th>Hash</th>
                </tr>
            </thead>
            <tbody>
                {html_body_rows}
            </tbody>
        </table>
        
        <div class="footer">
            Generated by File Organizer v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
        $(document).ready(function() {{
            $('#mediaTable').DataTable({{
                pageLength: 25,
                order: [[1, 'asc']],
                language: {{
                    search: "_INPUT_",
                    searchPlaceholder: "Quick search files..."
                }}
            }});
        }});
    </script>
</body>
</html>
"""

        report_file = self.output_dir / "media_explorer.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML Report generated successfully: {report_file.resolve()}")
        except IOError as e:
            print(f"Error writing HTML report: {e}")

if __name__ == "__main__":
    config_mgr = ConfigManager()
    
    parser = argparse.ArgumentParser(description="HTML Generator Module")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info')
    parser.add_argument('--generate', action='store_true', help="Generate the HTML report")
    parser.add_argument('--db', type=str, help="Override default database path")
    args = parser.parse_args()

    if args.version:
        print(f"HTML Report Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
    
    db_path = Path(args.db) if args.db else config_mgr.OUTPUT_DIR / 'metadata.sqlite'
    
    if args.generate:
        if not db_path.exists():
            print(f"Error: Database not found at {db_path}.")
        else:
            try:
                with DatabaseManager(db_path) as db:
                    generator = HTMLGenerator(db, config_mgr)
                    generator.generate_html_report()
            except Exception as e:
                print(f"FATAL ERROR: {e}")
    else:
        parser.print_help()