# ==============================================================================
# File: html_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
_CHANGELOG_ENTRIES = [
    "Initial implementation of HTMLGenerator class.",
    "Added DataTables integration for search/sort.",
    "FEATURE: Added Inline Media Player and Gallery Mode.",
    "FEATURE: Added relative file linking for Video, Audio, and Images.",
    "FEATURE: Added Metadata Inspector (Modal View).",
    "FIX: Robust schema inspection for date and path columns.",
    "FIX: Resolved SyntaxError by moving backslash replacement out of f-string."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.6
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple
import argparse
import datetime
import sys
import json
import urllib.parse

from database_manager import DatabaseManager
from config_manager import ConfigManager 

class HTMLGenerator:
    """
    Generates a local web gallery with embedded media players and 
    a deep-dive metadata inspector for all scanned assets.
    """

    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.files_reported = 0

    def _get_organized_media_data(self) -> List[Tuple]:
        """Queries the database for assets and their full metadata."""
        try:
            columns_res = self.db.execute_query("PRAGMA table_info(MediaContent)")
            col_names = [str(col[1]).lower() for col in columns_res] if columns_res else []
        except:
            col_names = []
        
        date_col = "mc.date_best" if "date_best" in col_names else \
                   "mc.recorded_date" if "recorded_date" in col_names else "'Unknown'"

        query = f"""
        SELECT 
            mc.content_hash, mc.file_type_group, {date_col}, 
            fpi.original_relative_path, mc.size, mc.width, mc.height,
            fpi.original_full_path, mc.extended_metadata
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        GROUP BY mc.content_hash
        ORDER BY fpi.original_relative_path ASC;
        """
        return self.db.execute_query(query)

    def _generate_html_body(self, data: List[Tuple]) -> str:
        """Generates the HTML table rows and handles file path sanitization."""
        html_rows = ""
        self.files_reported = len(data)

        for c_hash, group, date, rel_path, size, w, h, full_path, meta_json in data:
            size_str = f"{size / (1024*1024):.1f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            filename = Path(rel_path).name
            
            # FIX: Sanitize paths outside of the f-string to avoid SyntaxError in Python < 3.12
            safe_full_path = str(full_path).replace('\\', '/')
            file_link = f"file:///{safe_full_path}"
            
            # Prepare Media Preview
            media_html = ""
            if group == 'IMAGE':
                media_html = f'<img src="{file_link}" class="preview-img" onclick="window.open(this.src)">'
            elif group == 'VIDEO':
                media_html = f'<video class="preview-video" controls><source src="{file_link}"></video>'
            elif group == 'AUDIO':
                media_html = f'<audio class="preview-audio" controls><source src="{file_link}"></audio>'
            else:
                media_html = f'📄 <a href="{file_link}" target="_blank" style="color:#03dac6">Open File</a>'

            # Escape metadata for JS transmission
            # Replace single quotes and backslashes for safe JSON handling in HTML attributes
            js_meta = meta_json.replace('\\', '\\\\').replace("'", "&apos;")

            html_rows += f"""
            <tr>
                <td><span class="badge">{group}</span></td>
                <td><strong>{filename}</strong><br><small style="color:#888">{rel_path}</small></td>
                <td>{media_html}</td>
                <td data-order="{size}">{size_str}</td>
                <td>
                    <button class="meta-btn" onclick='showMeta("{filename}", {js_meta})'>🔍 Inspect</button>
                </td>
            </tr>
            """
        return html_rows

    def generate_html_report(self):
        """Builds the final HTML file with the DataTables UI and Modal system."""
        try:
            data = self._get_organized_media_data()
        except Exception as e:
            print(f"Database Query Error: {e}")
            return

        body_content = self._generate_html_body(data)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Media Gallery & Metadata Inspector</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }}
        .container {{ background: #1e1e1e; padding: 25px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ color: #bb86fc; margin-top: 0; padding-bottom: 10px; border-bottom: 1px solid #333; }}
        
        /* Table overrides */
        table.dataTable {{ background: #1e1e1e; border: none !important; }}
        table.dataTable thead th {{ background: #2c2c2c; color: #bb86fc; border-bottom: 2px solid #333 !important; }}
        .dataTables_wrapper .dataTables_length, .dataTables_wrapper .dataTables_filter, 
        .dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate {{ color: #aaa; margin: 15px 0; }}
        
        /* Media Elements */
        .preview-img {{ max-width: 140px; max-height: 100px; border-radius: 6px; cursor: zoom-in; border: 1px solid #444; }}
        .preview-video {{ width: 220px; border-radius: 6px; }}
        .preview-audio {{ width: 220px; }}
        .badge {{ background: #3700b3; padding: 3px 8px; border-radius: 4px; font-size: 0.75em; text-transform: uppercase; }}
        
        /* Modal & Buttons */
        .meta-btn {{ background: #03dac6; color: #000; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: 600; }}
        .meta-btn:hover {{ background: #01bca9; }}
        
        .modal {{ display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); }}
        .modal-content {{ background: #242424; margin: 5% auto; padding: 25px; border-radius: 10px; width: 70%; max-height: 85vh; overflow-y: auto; position: relative; }}
        .close {{ position: absolute; right: 20px; top: 15px; color: #ff4081; font-size: 35px; cursor: pointer; }}
        pre {{ background: #000; color: #00ff41; padding: 20px; border-radius: 8px; border: 1px solid #333; font-family: 'Consolas', monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Media Explorer</h1>
        <p style="color:#999">Indexing <strong>{self.files_reported}</strong> files. Click 'Inspect' to see internal metadata tags.</p>
        
        <table id="mediaTable" class="display" style="width:100%">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>File</th>
                    <th>Preview</th>
                    <th>Size</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {body_content}
            </tbody>
        </table>
    </div>

    <div id="metaModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle" style="color:#03dac6; margin-top:0;"></h2>
            <pre id="modalBody"></pre>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
        $(document).ready(function() {{
            $('#mediaTable').DataTable({{
                pageLength: 10,
                order: [[1, 'asc']],
                language: {{ searchPlaceholder: "Search files..." }}
            }});
        }});

        function showMeta(name, data) {{
            document.getElementById('modalTitle').innerText = name;
            document.getElementById('modalBody').innerText = JSON.stringify(data, null, 4);
            document.getElementById('metaModal').style.display = "block";
        }}

        function closeModal() {{
            document.getElementById('metaModal').style.display = "none";
        }}

        window.onclick = function(event) {{
            if (event.target == document.getElementById('metaModal')) {{ closeModal(); }}
        }}
    </script>
</body>
</html>
"""
        out_path = self.output_dir / "media_explorer.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[SUCCESS] Media Explorer generated at: {out_path.resolve()}")

if __name__ == "__main__":
    config_mgr = ConfigManager()
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--db', type=str)
    args = parser.parse_args()

    if args.version:
        print(f"HTML Report Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
    
    db_path = Path(args.db) if args.db else config_mgr.OUTPUT_DIR / 'metadata.sqlite'
    if db_path.exists():
        with DatabaseManager(db_path) as db:
            HTMLGenerator(db, config_mgr).generate_html_report()
    else:
        print(f"Error: Database not found at {db_path}")