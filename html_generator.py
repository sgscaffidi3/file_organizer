# ==============================================================================
# File: html_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_CHANGELOG_ENTRIES = [
    "Initial implementation of HTMLGenerator class.",
    "Added DataTables integration and Metadata Inspector.",
    "FEATURE: Added Hierarchical Folder Browser sidebar.",
    "FEATURE: Added dynamic folder-based filtering logic.",
    "FIX: Robust path handling for Python versions < 3.12.",
    "FIX: Restored missing CLI arguments (--version, --db).",
    "FEATURE: implemented Collapsible Folder Tree using <details> tags.",
    "FEATURE: Added 'Type View' (Browse by Media/Extension).",
    "FEATURE: Added 'Duplicates View' (Browse by Hash Collision).",
    "FIX: Restored vertical scrolling (overflow-y) to Metadata Modal window.",
    "FIX: Added explicit 'Root Directory' item in sidebar for files at base level."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.6.2
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict
import argparse
import sys
import json

from database_manager import DatabaseManager
from config_manager import ConfigManager 

class HTMLGenerator:
    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db = db_manager
        self.config = config_manager
        self.output_dir = self.config.OUTPUT_DIR
        self.files_reported = 0

    def _get_organized_media_data(self) -> List[Tuple]:
        """Queries database for all file instances, including duplicate counts."""
        try:
            columns_res = self.db.execute_query("PRAGMA table_info(MediaContent)")
            col_names = [str(col[1]).lower() for col in columns_res] if columns_res else []
        except: col_names = []
        
        date_col = "mc.date_best" if "date_best" in col_names else \
                   "mc.recorded_date" if "recorded_date" in col_names else "'Unknown'"

        query = f"""
        SELECT 
            mc.content_hash, 
            mc.file_type_group, 
            {date_col}, 
            fpi.original_relative_path, 
            mc.size, 
            mc.width, 
            mc.height,
            fpi.original_full_path, 
            mc.extended_metadata,
            (SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = mc.content_hash) as dupe_count
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        ORDER BY fpi.original_relative_path ASC;
        """
        return self.db.execute_query(query)

    def _build_trees(self, data: List[Tuple]):
        """Builds data structures for Folders, Types, and Duplicates."""
        folder_tree = {}
        type_tree = defaultdict(lambda: defaultdict(int))
        dupe_groups = defaultdict(list)
        has_root_files = False

        for row in data:
            c_hash, group, _, rel_path, _, _, _, _, _, dupe_count = row
            ext = Path(rel_path).suffix.lower() or "no_ext"
            
            # 1. Folder Tree Logic
            # Check if file is at root (parent is '.' or empty)
            parent = Path(rel_path).parent
            if str(parent) == '.' or str(parent) == '':
                has_root_files = True
            else:
                parts = parent.parts
                current = folder_tree
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            # 2. Type Tree
            type_tree[group][ext] += 1

            # 3. Duplicates (Only if count > 1)
            if dupe_count > 1:
                if c_hash not in dupe_groups:
                     dupe_groups[c_hash] = {"count": dupe_count, "name": Path(rel_path).name}

        return folder_tree, type_tree, dupe_groups, has_root_files

    def _render_folder_tree_html(self, tree: Dict, current_path: str = "") -> str:
        """Recursive collapsible directory tree using <details>."""
        if not tree: return ""
        html = '<ul class="tree-list">'
        for folder, subtree in sorted(tree.items()):
            full_path = f"{current_path}/{folder}".strip("/")
            safe_path = full_path.replace("'", "\\'")
            
            if not subtree:
                html += f'<li><span class="tree-item" onclick="filterTable(\'folder\', \'{safe_path}\')">📁 {folder}</span></li>'
            else:
                html += f'''
                <li>
                    <details>
                        <summary class="tree-summary" onclick="filterTable('folder', '{safe_path}')">📂 {folder}</summary>
                        {self._render_folder_tree_html(subtree, full_path)}
                    </details>
                </li>
                '''
        html += "</ul>"
        return html

    def _render_type_tree_html(self, tree: Dict) -> str:
        """Grouped list by Media Type -> Extension."""
        html = '<ul class="type-list">'
        icons = {'IMAGE': '🖼️', 'VIDEO': '🎬', 'AUDIO': '🎵', 'DOCUMENT': '📄'}
        
        for group, extensions in sorted(tree.items()):
            icon = icons.get(group, '📁')
            html += f'''
            <li>
                <details open>
                    <summary class="type-summary">{icon} {group}</summary>
                    <ul>
            '''
            for ext, count in sorted(extensions.items()):
                filter_val = f"{group}|{ext}"
                html += f'<li class="tree-item" onclick="filterTable(\'type\', \'{filter_val}\')">{ext} <span class="badge-count">{count}</span></li>'
            
            html += '</ul></details></li>'
        html += "</ul>"
        return html

    def _render_dupe_tree_html(self, dupes: Dict) -> str:
        """List of duplicate groups."""
        if not dupes: return "<p style='padding:10px; color:#888'>No duplicates found! 🎉</p>"
        
        html = '<ul class="dupe-list">'
        sorted_dupes = sorted(dupes.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for c_hash, info in sorted_dupes:
            count = info['count']
            name = info['name']
            html += f'''
            <li class="tree-item dupe-item" onclick="filterTable('hash', '{c_hash}')">
                <span class="dupe-name">{name}</span>
                <span class="badge-fail">{count} copies</span>
            </li>
            '''
        html += "</ul>"
        return html

    def _generate_html_body(self, data: List[Tuple]) -> str:
        html_rows = ""
        self.files_reported = len(data)

        for c_hash, group, date, rel_path, size, w, h, full_path, meta_json, dupe_count in data:
            size_str = f"{size / (1024*1024):.1f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            filename = Path(rel_path).name
            ext = Path(rel_path).suffix.lower()
            dir_path = str(Path(rel_path).parent).replace('\\', '/')
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
                media_html = f'📄 <a href="{file_link}" target="_blank" style="color:#03dac6">Open</a>'

            js_meta = meta_json.replace('\\', '\\\\').replace("'", "&apos;")
            
            html_rows += f"""
            <tr data-folder="{dir_path}" data-hash="{c_hash}" data-group="{group}" data-ext="{ext}">
                <td><span class="badge">{group}</span></td>
                <td>
                    <strong>{filename}</strong><br>
                    <small style="color:#888">{rel_path}</small>
                    {f'<br><span class="badge-fail">DUPLICATE</span>' if dupe_count > 1 else ''}
                </td>
                <td>{media_html}</td>
                <td data-order="{size}">{size_str}</td>
                <td><button class="meta-btn" onclick='showMeta("{filename}", {js_meta})'>🔍</button></td>
            </tr>
            """
        return html_rows

    def generate_html_report(self):
        data = self._get_organized_media_data()
        
        folder_tree, type_tree, dupe_groups, has_root = self._build_trees(data)
        
        sidebar_folders = self._render_folder_tree_html(folder_tree)
        sidebar_types = self._render_type_tree_html(type_tree)
        sidebar_dupes = self._render_dupe_tree_html(dupe_groups)
        
        # Inject Root Directory item if needed
        root_html = ""
        if has_root:
            root_html = '<div class="tree-item" onclick="filterTable(\'folder\', \'.\')" style="color:#03dac6; margin-bottom:5px;">📂 (Root Directory)</div>'
        
        body_content = self._generate_html_body(data)
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Media Explorer v{_MAJOR_VERSION}.{_MINOR_VERSION}</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; display: flex; height: 100vh; margin: 0; overflow: hidden; }}
        
        #sidebar {{ width: 340px; background: #1e1e1e; border-right: 1px solid #333; display: flex; flex-direction: column; flex-shrink: 0; }}
        
        .tab-bar {{ display: flex; border-bottom: 1px solid #333; }}
        .tab-btn {{ flex: 1; padding: 15px 0; background: #252525; color: #888; border: none; cursor: pointer; font-weight: bold; transition: 0.2s; }}
        .tab-btn:hover {{ background: #2a2a2a; color: #fff; }}
        .tab-btn.active {{ background: #1e1e1e; color: #bb86fc; border-bottom: 2px solid #bb86fc; }}
        
        .tab-content {{ flex-grow: 1; overflow-y: auto; padding: 15px; display: none; }}
        .tab-content.active {{ display: block; }}
        
        ul.tree-list, ul.type-list, ul.dupe-list {{ list-style: none; padding-left: 10px; margin: 0; }}
        details > summary {{ cursor: pointer; padding: 5px; color: #ccc; list-style: none; }}
        details > summary::marker {{ display: none; }}
        details > summary:hover {{ color: #fff; }}
        .tree-item {{ display: block; padding: 4px 8px; cursor: pointer; color: #888; font-size: 0.9em; }}
        .tree-item:hover {{ color: #03dac6; background: #2a2a2a; border-radius: 4px; }}
        
        .dupe-item {{ display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding: 8px; }}
        .dupe-name {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }}
        
        #main {{ flex-grow: 1; padding: 20px; overflow-y: auto; background: #121212; }}
        .container {{ background: #1e1e1e; padding: 20px; border-radius: 12px; }}
        
        table.dataTable {{ background: #1e1e1e; color: #e0e0e0; font-size: 0.9em; }}
        .preview-img {{ max-width: 100px; max-height: 80px; border: 1px solid #444; border-radius: 4px; cursor: zoom-in; }}
        .preview-video, .preview-audio {{ width: 200px; }}
        
        .badge {{ background: #3700b3; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; }}
        .badge-count {{ background: #333; padding: 2px 6px; border-radius: 8px; font-size: 0.8em; float: right; }}
        .badge-fail {{ background: #cf6679; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; }}
        
        .meta-btn {{ background: #03dac6; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; }}
        
        /* Modal Scrolling Fix */
        .modal {{ display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); }}
        .modal-content {{ 
            background: #242424; 
            margin: 5% auto; 
            padding: 25px; 
            width: 70%; 
            max-height: 80vh; 
            overflow-y: auto; 
            border-radius: 10px; 
            position: relative; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        pre {{ background: #000; color: #00ff41; padding: 15px; overflow-x: auto; font-family: monospace; }}
        .close {{ position: absolute; right: 20px; top: 15px; color: #fff; font-size: 30px; cursor: pointer; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchTab('folders')">Folders</button>
            <button class="tab-btn" onclick="switchTab('types')">Types</button>
            <button class="tab-btn" onclick="switchTab('dupes')">Duplicates</button>
        </div>

        <div id="tab-folders" class="tab-content active">
            <div class="tree-item" onclick="filterTable('reset', '')" style="margin-bottom:10px; font-weight:bold;">🏠 Show All Files</div>
            {root_html}
            {sidebar_folders}
        </div>

        <div id="tab-types" class="tab-content">
            <div class="tree-item" onclick="filterTable('reset', '')" style="margin-bottom:10px; font-weight:bold;">🏠 Show All Files</div>
            {sidebar_types}
        </div>

        <div id="tab-dupes" class="tab-content">
            <p style="font-size:0.8em; color:#aaa; margin-top:0;">Click a group to isolate duplicates.</p>
            {sidebar_dupes}
        </div>
    </div>

    <div id="main">
        <div class="container">
            <h2 id="view-title" style="color:#bb86fc; margin-top:0;">All Files</h2>
            <table id="mediaTable" class="display" style="width:100%">
                <thead>
                    <tr><th>Type</th><th>File Info</th><th>Preview</th><th>Size</th><th>Meta</th></tr>
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
            table = $('#mediaTable').DataTable({{ 
                pageLength: 10,
                order: [[1, 'asc']],
                language: {{ searchPlaceholder: "Deep search..." }}
            }});
        }});

        function switchTab(tabName) {{
            $('.tab-content').removeClass('active');
            $('.tab-btn').removeClass('active');
            $('#tab-' + tabName).addClass('active');
            $('button[onclick="switchTab(\\'' + tabName + '\\')"]').addClass('active');
        }}

        function filterTable(mode, value) {{
            $.fn.dataTable.ext.search = [];
            let title = "Filtered Results";

            if (mode === 'reset') {{
                title = "All Files";
                table.search('').draw();
            }} else {{
                $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {{
                    let node = $(table.row(dataIndex).node());
                    if (mode === 'folder') {{
                        let rowFolder = node.attr('data-folder');
                        // Special handling for Root files
                        if (value === '.') return rowFolder === '.';
                        return rowFolder === value || rowFolder.startsWith(value + "/");
                    }}
                    else if (mode === 'type') {{
                        let parts = value.split('|');
                        return node.attr('data-group') === parts[0] && node.attr('data-ext') === parts[1];
                    }}
                    else if (mode === 'hash') {{
                        return node.attr('data-hash') === value;
                    }}
                    return true;
                }});
                title = (mode === 'hash') ? "Duplicate Group Inspector" : "Filtered: " + (value === '.' ? 'Root Directory' : value);
            }}
            $('#view-title').text(title);
            table.draw();
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
        out_path = self.output_dir / "media_dashboard.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[SUCCESS] Media Dashboard generated at: {out_path.resolve()}")

if __name__ == "__main__":
    config_mgr = ConfigManager()
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--db', type=str)
    args = parser.parse_args()

    if args.version:
        print(f"HTML Dashboard Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)
    
    db_path = Path(args.db) if args.db else config_mgr.OUTPUT_DIR / 'metadata.sqlite'
    if args.generate:
        if db_path.exists():
            with DatabaseManager(db_path) as db:
                HTMLGenerator(db, config_mgr).generate_html_report()
        else:
            print(f"Error: Database not found at {db_path}")
    else:
        if db_path.exists():
            with DatabaseManager(db_path) as db:
                HTMLGenerator(db, config_mgr).generate_html_report()
        else:
            parser.print_help()