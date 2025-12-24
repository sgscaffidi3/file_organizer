# ==============================================================================
# File: html_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 5
_CHANGELOG_ENTRIES = [
    "Initial implementation of HTMLGenerator class.",
    "Added DataTables integration and Metadata Inspector.",
    "FEATURE: Added Hierarchical Folder Browser sidebar.",
    "FEATURE: Added dynamic folder-based filtering logic.",
    "FIX: Robust path handling for Python versions < 3.12.",
    "FIX: Restored missing CLI arguments (--version, --db) in the main block."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.5.1
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple, Dict
import argparse
import datetime
import sys
import json
import urllib.parse

from database_manager import DatabaseManager
from config_manager import ConfigManager 

class HTMLGenerator:
    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.files_reported = 0

    def _get_organized_media_data(self) -> List[Tuple]:
        try:
            columns_res = self.db.execute_query("PRAGMA table_info(MediaContent)")
            col_names = [str(col[1]).lower() for col in columns_res] if columns_res else []
        except: col_names = []
        
        date_col = "mc.date_best" if "date_best" in col_names else \
                   "mc.recorded_date" if "recorded_date" in col_names else "'Unknown'"

        query = f"""
        SELECT 
            mc.content_hash, mc.file_type_group, {date_col}, 
            fpi.original_relative_path, mc.size, mc.width, mc.height,
            fpi.original_full_path, mc.extended_metadata
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        GROUP BY fpi.original_full_path
        ORDER BY fpi.original_relative_path ASC;
        """
        return self.db.execute_query(query)

    def _build_folder_tree(self, paths: List[str]) -> Dict:
        """Converts a list of relative paths into a nested dictionary tree."""
        tree = {}
        for path_str in paths:
            # We use the parent directory of the file to build the tree
            parts = Path(path_str).parent.parts
            current = tree
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        return tree

    def _render_tree_html(self, tree: Dict, current_path: str = "") -> str:
        """Recursively generates HTML for the folder sidebar."""
        if not tree: return ""
        html = "<ul>"
        for folder, subtree in sorted(tree.items()):
            # Build the path used for filtering in JS
            clean_folder = folder.replace("'", "\\'")
            full_path = f"{current_path}/{folder}".strip("/")
            html += f'<li><span class="folder-link" onclick="filterFolder(\'{full_path}\')">📂 {folder}</span>'
            if subtree:
                html += self._render_tree_html(subtree, full_path)
            html += "</li>"
        html += "</ul>"
        return html

    def _generate_html_body(self, data: List[Tuple]) -> str:
        html_rows = ""
        self.files_reported = len(data)

        for c_hash, group, date, rel_path, size, w, h, full_path, meta_json in data:
            size_str = f"{size / (1024*1024):.1f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            filename = Path(rel_path).name
            dir_path = str(Path(rel_path).parent).replace('\\', '/')
            
            # Sanitize paths for HTML/f-string compatibility
            safe_full_path = str(full_path).replace('\\', '/')
            file_link = f"file:///{safe_full_path}"
            
            media_html = ""
            if group == 'IMAGE':
                media_html = f'<img src="{file_link}" class="preview-img" onclick="window.open(this.src)">'
            elif group == 'VIDEO':
                media_html = f'<video class="preview-video" controls><source src="{file_link}"></video>'
            elif group == 'AUDIO':
                media_html = f'<audio class="preview-audio" controls><source src="{file_link}"></audio>'
            else:
                media_html = f'📄 <a href="{file_link}" target="_blank" style="color:#03dac6">Open File</a>'

            # Escape metadata for JavaScript modal
            js_meta = meta_json.replace('\\', '\\\\').replace("'", "&apos;")

            html_rows += f"""
            <tr data-folder="{dir_path}">
                <td><span class="badge">{group}</span></td>
                <td><strong>{filename}</strong><br><small style="color:#888">{rel_path}</small></td>
                <td>{media_html}</td>
                <td data-order="{size}">{size_str}</td>
                <td><button class="meta-btn" onclick='showMeta("{filename}", {js_meta})'>🔍</button></td>
            </tr>
            """
        return html_rows

    def generate_html_report(self):
        data = self._get_organized_media_data()
        all_rel_paths = [row[3] for row in data]
        folder_tree = self._build_folder_tree(all_rel_paths)
        
        sidebar_html = self._render_tree_html(folder_tree)
        body_content = self._generate_html_body(data)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Media Browser | Hierarchical Explorer</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; display: flex; height: 100vh; margin: 0; overflow: hidden; }}
        #sidebar {{ width: 320px; background: #1e1e1e; border-right: 1px solid #333; overflow-y: auto; padding: 20px; flex-shrink: 0; }}
        #main {{ flex-grow: 1; padding: 25px; overflow-y: auto; background: #121212; }}
        h1, h3 {{ color: #bb86fc; }}
        ul {{ list-style-type: none; padding-left: 18px; margin: 8px 0; }}
        .folder-link {{ cursor: pointer; color: #aaa; font-size: 0.95em; }}
        .folder-link:hover {{ color: #03dac6; }}
        .container {{ background: #1e1e1e; padding: 20px; border-radius: 12px; }}
        table.dataTable {{ background: #1e1e1e; color: #e0e0e0; font-size: 0.9em; }}
        .preview-img {{ max-width: 120px; border-radius: 4px; border: 1px solid #444; }}
        .preview-video {{ width: 220px; border-radius: 4px; }}
        .badge {{ background: #3700b3; padding: 3px 7px; border-radius: 4px; font-size: 0.75em; }}
        .meta-btn {{ background: #03dac6; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; }}
        .modal {{ display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); }}
        .modal-content {{ background: #242424; margin: 5% auto; padding: 25px; width: 65%; border-radius: 10px; position: relative; }}
        pre {{ background: #000; color: #00ff41; padding: 15px; border-radius: 6px; overflow-x: auto; font-family: monospace; }}
        .close {{ position: absolute; right: 20px; top: 15px; color: #aaa; font-size: 30px; cursor: pointer; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <h3>📂 Folder Browser</h3>
        <div class="folder-link" onclick="filterFolder('')" style="font-weight:bold; margin-bottom:10px;">🏠 All Files</div>
        {sidebar_html}
    </div>
    <div id="main">
        <div class="container">
            <h1>Media Explorer</h1>
            <table id="mediaTable" class="display" style="width:100%">
                <thead>
                    <tr><th>Type</th><th>File</th><th>Preview</th><th>Size</th><th>Meta</th></tr>
                </thead>
                <tbody>{body_content}</tbody>
            </table>
        </div>
    </div>
    <div id="metaModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle" style="color:#03dac6"></h2>
            <pre id="modalBody"></pre>
        </div>
    </div>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
        let table;
        $(document).ready(function() {{
            table = $('#mediaTable').DataTable({{ pageLength: 10, order: [[1, 'asc']] }});
        }});
        function filterFolder(folderPath) {{
            $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {{
                let rowFolder = $(table.row(dataIndex).node()).attr('data-folder');
                return folderPath === "" || rowFolder === folderPath || rowFolder.startsWith(folderPath + "/");
            }});
            table.draw();
            $.fn.dataTable.ext.search.pop();
        }}
        function showMeta(name, data) {{
            document.getElementById('modalTitle').innerText = name;
            document.getElementById('modalBody').innerText = JSON.stringify(data, null, 4);
            document.getElementById('metaModal').style.display = "block";
        }}
        function closeModal() {{ document.getElementById('metaModal').style.display = "none"; }}
        window.onclick = function(e) {{ if(e.target == document.getElementById('metaModal')) closeModal(); }}
    </script>
</body>
</html>
"""
        out_path = self.output_dir / "media_explorer.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[SUCCESS] Hierarchical Explorer generated at: {out_path.resolve()}")

if __name__ == "__main__":
    config_mgr = ConfigManager()
    parser = argparse.ArgumentParser(description="Media Explorer HTML Generator")
    parser.add_argument('-v', '--version', action='store_true', help="Show version")
    parser.add_argument('--generate', action='store_true', help="Generate the report")
    parser.add_argument('--db', type=str, help="Path to metadata.sqlite")
    args = parser.parse_args()

    if args.version:
        print(f"HTML Explorer Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
    
    db_path = Path(args.db) if args.db else config_mgr.OUTPUT_DIR / 'metadata.sqlite'
    if args.generate:
        if db_path.exists():
            with DatabaseManager(db_path) as db:
                HTMLGenerator(db, config_mgr).generate_html_report()
        else:
            print(f"Error: Database not found at {db_path}")
    else:
        parser.print_help()