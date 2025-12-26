# ==============================================================================
# File: html_generator.py
# ------------------------------------------------------------------------------
_MAJOR_VERSION = 0
_MINOR_VERSION = 6
_REMOVED_CHANGELOG_COUNT = 0 
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
    "FIX: Added explicit 'Root Directory' item in sidebar for files at base level.",
    "FIX: Added JS safety checks to metadata modal to prevent 'silent' failures.",
    "FIX: Added 'formatSize' utility to metadata inspector for human-readable sizes.",
    "FIX: Added video playback fallback message for browser/CORS compatibility issues.",
    "VERSIONING: Added _REMOVED_CHANGELOG_COUNT to prevent version regression.",
    "FIX: Resolved SyntaxError by removing f-string escaping issues in HTML generation.",
    "FIX: Restored missing --generate CLI argument and generation logic.",
    "FIX: Resolved ValueError by separating CSS/JS from .format() template parsing.",
    "FIX: Switched to simple string concatenation for final HTML to prevent JS corruption.",
    "FIX: Replaced onclick data-passing with HTML5 data-attributes to fix Metadata Modal.",
    "FIX: Resolved f-string backslash SyntaxError and restored missing sidebar variables."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES) + _REMOVED_CHANGELOG_COUNT
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
            fpi.original_full_path, mc.extended_metadata,
            (SELECT COUNT(*) FROM FilePathInstances WHERE content_hash = mc.content_hash) as dupe_count
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        ORDER BY fpi.original_relative_path ASC;
        """
        return self.db.execute_query(query)

    def _build_trees(self, data: List[Tuple]):
        folder_tree = {}
        type_tree = defaultdict(lambda: defaultdict(int))
        dupe_groups = defaultdict(list)
        has_root_files = False

        for row in data:
            c_hash, group, _, rel_path, _, _, _, _, _, dupe_count = row
            ext = Path(rel_path).suffix.lower() or "no_ext"
            parent = Path(rel_path).parent
            
            if str(parent) in ('.', ''):
                has_root_files = True
            else:
                current = folder_tree
                for part in parent.parts:
                    if part not in current: current[part] = {}
                    current = current[part]
            
            type_tree[group][ext] += 1
            if dupe_count > 1 and c_hash not in dupe_groups:
                dupe_groups[c_hash] = {"count": dupe_count, "name": Path(rel_path).name}
        
        return folder_tree, type_tree, dupe_groups, has_root_files

    def _render_folder_tree_html(self, tree: Dict, current_path: str = "") -> str:
        if not tree: return ""
        html = '<ul class="tree-list">'
        for folder, subtree in sorted(tree.items()):
            full_path = f"{current_path}/{folder}".strip("/")
            safe_path = full_path.replace("'", "\\'")
            if not subtree:
                html += f'<li><span class="tree-item" onclick="filterTable(\'folder\', \'{safe_path}\')">📁 {folder}</span></li>'
            else:
                html += f'<li><details><summary class="tree-summary" onclick="filterTable(\'folder\', \'{safe_path}\')">📂 {folder}</summary>'
                html += self._render_folder_tree_html(subtree, full_path)
                html += '</details></li>'
        html += "</ul>"
        return html

    def _render_type_tree_html(self, tree: Dict) -> str:
        html = '<ul class="type-list">'
        icons = {'IMAGE': '🖼️', 'VIDEO': '🎬', 'AUDIO': '🎵', 'DOCUMENT': '📄'}
        for group, extensions in sorted(tree.items()):
            icon = icons.get(group, '📁')
            html += f'<li><details open><summary class="type-summary">{icon} {group}</summary><ul>'
            for ext, count in sorted(extensions.items()):
                html += f'<li class="tree-item" onclick="filterTable(\'type\', \'{group}|{ext}\')">{ext} <span class="badge-count">{count}</span></li>'
            html += '</ul></details></li>'
        html += "</ul>"
        return html

    def _render_dupe_tree_html(self, dupes: Dict) -> str:
        if not dupes: return "<p style='padding:10px; color:#888'>No duplicates found! 🎉</p>"
        html = '<ul class="dupe-list">'
        for c_hash, info in sorted(dupes.items(), key=lambda x: x[1]['count'], reverse=True):
            html += f'<li class="tree-item dupe-item" onclick="filterTable(\'hash\', \'{c_hash}\')">'
            html += f'<span class="dupe-name">{info["name"]}</span><span class="badge-fail">{info["count"]} copies</span></li>'
        html += "</ul>"
        return html

    def generate_html_report(self):
        data = self._get_organized_media_data()
        folder_tree, type_tree, dupe_groups, has_root = self._build_trees(data)
        
        body_rows = ""
        for row in data:
            c_hash, group, date, rel_path, size, w, h, full_path, meta_json, dupe_count = row
            size_kb = size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
            filename = Path(rel_path).name
            dir_path = str(Path(rel_path).parent).replace('\\', '/')
            
            # FIX: Resolve backslash SyntaxError by manipulating path outside f-string
            clean_full_path = str(full_path).replace('\\', '/')
            file_link = f"file:///{clean_full_path}"
            
            media_html = ""
            if group == 'IMAGE':
                media_html = f'<img src="{file_link}" class="preview-img" onclick="window.open(this.src)">'
            elif group == 'VIDEO':
                media_html = f'<video class="preview-video" controls><source src="{file_link}">Video Not Supported</video>'
            elif group == 'AUDIO':
                media_html = f'<audio class="preview-audio" controls><source src="{file_link}"></audio>'
            else:
                media_html = f'📄 <a href="{file_link}" target="_blank">Open</a>'

            try:
                meta_dict = json.loads(meta_json) if meta_json else {}
            except:
                meta_dict = {"error": "Invalid metadata JSON"}
            
            meta_attr = json.dumps(meta_dict).replace("'", "&apos;")
            
            body_rows += f"""
            <tr data-folder="{dir_path}" data-hash="{c_hash}" data-group="{group}" data-ext="{Path(rel_path).suffix.lower()}">
                <td><span class="badge">{group}</span></td>
                <td><strong>{filename}</strong><br><small>{rel_path}</small>
                    {f'<br><span class="badge-fail">DUPLICATE</span>' if dupe_count > 1 else ''}</td>
                <td>{media_html}</td>
                <td data-order="{size}">{size_str}</td>
                <td><button class="meta-btn" data-name="{filename}" data-meta='{meta_attr}' onclick="showMeta(this)">🔍</button></td>
            </tr>"""

        sidebar_f = self._render_folder_tree_html(folder_tree)
        sidebar_t = self._render_type_tree_html(type_tree)
        sidebar_d = self._render_dupe_tree_html(dupe_groups)
        root_btn = '<div class="tree-item" onclick="filterTable(\'folder\', \'.\')" style="color:#03dac6; margin-bottom:5px;">📂 (Root Directory)</div>' if has_root else ""

        css_content = """
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; display: flex; height: 100vh; margin: 0; overflow: hidden; }
        #sidebar { width: 340px; background: #1e1e1e; border-right: 1px solid #333; display: flex; flex-direction: column; flex-shrink: 0; }
        .tab-bar { display: flex; border-bottom: 1px solid #333; }
        .tab-btn { flex: 1; padding: 15px 0; background: #252525; color: #888; border: none; cursor: pointer; font-weight: bold; }
        .tab-btn.active { background: #1e1e1e; color: #bb86fc; border-bottom: 2px solid #bb86fc; }
        .tab-content { flex-grow: 1; overflow-y: auto; padding: 15px; display: none; }
        .tab-content.active { display: block; }
        ul.tree-list, ul.type-list { list-style: none; padding-left: 10px; margin: 0; }
        .tree-item { display: block; padding: 4px 8px; cursor: pointer; color: #888; font-size: 0.9em; }
        .tree-item:hover { color: #03dac6; background: #2a2a2a; border-radius: 4px; }
        #main { flex-grow: 1; padding: 20px; overflow-y: auto; background: #121212; }
        .container { background: #1e1e1e; padding: 20px; border-radius: 12px; }
        table.dataTable { background: #1e1e1e; color: #e0e0e0; font-size: 0.9em; }
        .preview-img { max-width: 100px; max-height: 80px; border: 1px solid #444; border-radius: 4px; cursor: zoom-in; }
        .preview-video { width: 220px; background: #000; }
        .badge { background: #3700b3; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; }
        .badge-fail { background: #cf6679; color: #000; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; }
        .meta-btn { background: #03dac6; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
        .modal { display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); }
        .modal-content { background: #242424; margin: 5% auto; padding: 25px; width: 70%; max-height: 80vh; overflow-y: auto; border-radius: 10px; position: relative; }
        pre { background: #000; color: #00ff41; padding: 15px; overflow-x: auto; font-family: monospace; }
        .close { position: absolute; right: 20px; top: 15px; color: #fff; font-size: 30px; cursor: pointer; }
        """

        js_content = """
        let table;
        $(document).ready(function() {
            table = $('#mediaTable').DataTable({ pageLength: 10, order: [[1, 'asc']] });
        });
        function switchTab(t) {
            $('.tab-content').removeClass('active'); $('.tab-btn').removeClass('active');
            $('#tab-' + t).addClass('active');
            $('button[onclick="switchTab(\'' + t + '\')"]').addClass('active');
        }
        function filterTable(m, v) {
            $.fn.dataTable.ext.search = [];
            if (m === 'reset') { table.search('').draw(); } 
            else {
                $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
                    let node = $(table.row(dataIndex).node());
                    if (m === 'folder') return v === '.' ? node.attr('data-folder') === '.' : node.attr('data-folder') === v || node.attr('data-folder').startsWith(v + "/");
                    if (m === 'type') { let p = v.split('|'); return node.attr('data-group') === p[0] && node.attr('data-ext') === p[1]; }
                    return node.attr('data-hash') === v;
                });
            }
            table.draw();
        }
        function formatSize(b) {
            if (!b || isNaN(b)) return b;
            const u = ['B', 'KB', 'MB', 'GB']; let l = 0, n = parseInt(b, 10) || 0;
            while(n >= 1024 && ++l) { n = n/1024; }
            return n.toFixed(n < 10 && l > 0 ? 1 : 0) + ' ' + u[l];
        }
        function showMeta(btn) {
            const name = btn.getAttribute('data-name');
            const metaRaw = btn.getAttribute('data-meta');
            try {
                const data = JSON.parse(metaRaw);
                if (data.FileSize) data.FriendlySize = formatSize(data.FileSize);
                document.getElementById('modalTitle').innerText = name;
                document.getElementById('modalBody').innerText = JSON.stringify(data, null, 4);
                document.getElementById('metaModal').style.display = "block";
            } catch (e) { alert("Metadata error: " + e.message); }
        }
        function closeModal() { document.getElementById('metaModal').style.display = "none"; }
        """

        # ASSEMBLE HTML PARTS
        html_top = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Media Explorer v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}</title>'
        html_top += f'<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css"><style>{css_content}</style></head><body>'
        
        sidebar_html = f"""<div id="sidebar">
            <div class="tab-bar">
                <button class="tab-btn active" onclick="switchTab('folders')">Folders</button>
                <button class="tab-btn" onclick="switchTab('types')">Types</button>
                <button class="tab-btn" onclick="switchTab('dupes')">Duplicates</button>
            </div>
            <div id="tab-folders" class="tab-content active">
                <div class="tree-item" onclick="filterTable('reset', '')" style="font-weight:bold;">🏠 Show All Files</div>
                {root_btn} {sidebar_f}
            </div>
            <div id="tab-types" class="tab-content">{sidebar_t}</div>
            <div id="tab-dupes" class="tab-content">{sidebar_d}</div>
        </div>"""

        main_html = f"""<div id="main"><div class="container">
            <h2 id="view-title" style="color:#bb86fc; margin-top:0;">All Files</h2>
            <table id="mediaTable" class="display" style="width:100%">
                <thead><tr><th>Type</th><th>File Info</th><th>Preview</th><th>Size</th><th>Meta</th></tr></thead>
                <tbody>{body_rows}</tbody>
            </table>
        </div></div>"""

        modal_html = """<div id="metaModal" class="modal"><div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle" style="color:#03dac6"></h2>
            <pre id="modalBody"></pre>
        </div></div>"""

        scripts_html = f'<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>'
        scripts_html += '<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>'
        scripts_html += f'<script>{js_content}</script></body></html>'

        out_path = self.output_dir / "media_dashboard.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_top + sidebar_html + main_html + modal_html + scripts_html)
        print(f"\n[SUCCESS] Media Dashboard generated at: {out_path.resolve()}")

if __name__ == "__main__":
    c = ConfigManager(); p = argparse.ArgumentParser()
    p.add_argument('-v', '--version', action='store_true')
    p.add_argument('--generate', action='store_true')
    p.add_argument('--db', type=str)
    a = p.parse_args()
    if a.version:
        print(f"HTML Dashboard Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}"); sys.exit(0)
    db_p = Path(a.db) if a.db else c.OUTPUT_DIR / 'metadata.sqlite'
    if a.generate or not a.version:
        if db_p.exists():
            with DatabaseManager(db_p) as db: HTMLGenerator(db, c).generate_html_report()
        else:
            print(f"Error: Database not found at {db_p}")