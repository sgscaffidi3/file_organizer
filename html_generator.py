# ==============================================================================
# File: html_generator.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 8
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
    "FIX: Resolved SyntaxError by removing f-string escaping issues in HTML generation.",
    "FIX: Restored missing --generate CLI argument and generation logic.",
    "FIX: Resolved ValueError by separating CSS/JS from .format() template parsing.",
    "FIX: Switched to simple string concatenation for final HTML to prevent JS corruption.",
    "FIX: Replaced onclick data-passing with HTML5 data-attributes to fix Metadata Modal.",
    "FIX: Resolved f-string backslash SyntaxError and restored missing sidebar variables.",
    "PERFORMANCE: Switched from string concatenation to list buffering for row generation (O(n) vs O(n^2)).",
    "UX: Added TQDM progress bar for HTML generation feedback.",
    "ARCHITECTURE: Switched to Client-Side Rendering (JSON Island) for massive performance gain on 100k+ files.",
    "UX: Added Dashboard Summary Cards (Total Size, Wasted Space, etc).",
    "UX: Implemented Lazy Loading for media previews to prevent browser hangs.",
    "UX: Added Dedicated Duplicate Report tab.",
    "BUG FIX: Defined hidden DataTables columns for Folder, Extension, and Hash to enable Sidebar Filtering.",
    "FIX: Explicitly implemented CLI version print to support test runner audit."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.8.28
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import List, Tuple, Dict, Any
from collections import defaultdict
import argparse
import sys
import json
from tqdm import tqdm

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
            if dupe_count > 1:
                if c_hash not in dupe_groups:
                    dupe_groups[c_hash] = {"count": dupe_count, "name": Path(rel_path).name}
        
        return folder_tree, type_tree, dupe_groups, has_root_files

    def _render_folder_tree_html(self, tree: Dict, current_path: str = "") -> str:
        if not tree: return ""
        html_parts = ['<ul class="tree-list">']
        for folder, subtree in sorted(tree.items()):
            full_path = f"{current_path}/{folder}".strip("/")
            safe_path = full_path.replace("'", "\\'")
            if not subtree:
                html_parts.append(f'<li><span class="tree-item" onclick="filterByFolder(\'{safe_path}\')">📁 {folder}</span></li>')
            else:
                html_parts.append(f'<li><details><summary class="tree-summary" onclick="filterByFolder(\'{safe_path}\')">📂 {folder}</summary>')
                html_parts.append(self._render_folder_tree_html(subtree, full_path))
                html_parts.append('</details></li>')
        html_parts.append("</ul>")
        return "".join(html_parts)

    def _render_type_tree_html(self, tree: Dict) -> str:
        html_parts = ['<ul class="type-list">']
        icons = {'IMAGE': '🖼️', 'VIDEO': '🎬', 'AUDIO': '🎵', 'DOCUMENT': '📄'}
        for group, extensions in sorted(tree.items()):
            icon = icons.get(group, '📁')
            html_parts.append(f'<li><details open><summary class="type-summary">{icon} {group}</summary><ul>')
            for ext, count in sorted(extensions.items()):
                html_parts.append(f'<li class="tree-item" onclick="filterByType(\'{group}\', \'{ext}\')">{ext} <span class="badge-count">{count}</span></li>')
            html_parts.append('</ul></details></li>')
        html_parts.append("</ul>")
        return "".join(html_parts)

    def _format_size(self, size_bytes):
        if not size_bytes: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def generate_html_report(self):
        print("Fetching data for HTML generation...")
        data = self._get_organized_media_data()
        
        print(f"Building Directory Trees for {len(data)} files...")
        folder_tree, type_tree, dupe_groups, has_root = self._build_trees(data)
        
        # --- Stats Calculation ---
        total_files = len(data)
        total_size = sum(row[4] for row in data)
        
        unique_files = {}
        for row in data:
            if row[0] not in unique_files:
                unique_files[row[0]] = {'size': row[4], 'count': row[9]}
        
        wasted_size = 0
        for h, info in unique_files.items():
            if info['count'] > 1:
                wasted_size += info['size'] * (info['count'] - 1)

        # --- JSON Serialization ---
        js_data = []
        with tqdm(total=len(data), desc="Serializing Data", unit="row") as pbar:
            for row in data:
                pbar.update(1)
                c_hash, group, date, rel_path, size, w, h, full_path, meta_json, dupe_count = row
                
                filename = Path(rel_path).name
                folder_path = str(Path(rel_path).parent).replace('\\', '/')
                clean_full_path = str(full_path).replace('\\', '/')
                
                try:
                    if meta_json: json.loads(meta_json)
                except:
                    meta_json = "{}"

                # DATA STRUCTURE INDEX:
                # 0: Hash
                # 1: Group
                # 2: Name
                # 3: RelPath
                # 4: Size (int)
                # 5: Size (str)
                # 6: FullPath
                # 7: MetaJSON
                # 8: DupeCount
                # 9: FolderPath
                # 10: Extension
                js_data.append([
                    c_hash,
                    group,
                    filename,
                    rel_path,
                    size,
                    self._format_size(size),
                    clean_full_path,
                    meta_json,
                    dupe_count,
                    folder_path,
                    str(Path(rel_path).suffix.lower())
                ])

        json_payload = json.dumps(js_data)

        # --- HTML Components ---
        sidebar_f = self._render_folder_tree_html(folder_tree)
        sidebar_t = self._render_type_tree_html(type_tree)
        root_btn = '<div class="tree-item" onclick="filterByFolder(\'.\')" style="color:#03dac6; margin-bottom:5px;">📂 (Root Directory)</div>' if has_root else ""

        stats_html = f"""
        <div class="stats-container">
            <div class="stat-card"><h3>Total Files</h3><p>{total_files:,}</p></div>
            <div class="stat-card"><h3>Total Size</h3><p>{self._format_size(total_size)}</p></div>
            <div class="stat-card fail"><h3>Duplicates</h3><p>{len(dupe_groups):,}</p></div>
            <div class="stat-card fail"><h3>Wasted Space</h3><p>{self._format_size(wasted_size)}</p></div>
        </div>
        """

        css_content = """
        :root { --bg: #121212; --panel: #1e1e1e; --text: #e0e0e0; --accent: #bb86fc; --sec: #03dac6; --err: #cf6679; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        #sidebar { width: 320px; background: var(--panel); border-right: 1px solid #333; display: flex; flex-direction: column; flex-shrink: 0; }
        #main-area { flex-grow: 1; display: flex; flex-direction: column; overflow: hidden; padding: 20px; }
        
        .stats-container { display: flex; gap: 15px; margin-bottom: 20px; }
        .stat-card { background: var(--panel); padding: 15px; border-radius: 8px; flex: 1; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .stat-card h3 { margin: 0 0 5px 0; font-size: 0.9em; color: #888; }
        .stat-card p { margin: 0; font-size: 1.5em; font-weight: bold; color: var(--sec); }
        .stat-card.fail p { color: var(--err); }

        .tab-bar { display: flex; border-bottom: 1px solid #333; }
        .tab-btn { flex: 1; padding: 12px; background: #252525; color: #888; border: none; cursor: pointer; font-weight: bold; }
        .tab-btn.active { background: var(--panel); color: var(--accent); border-bottom: 2px solid var(--accent); }
        .sb-content { flex-grow: 1; overflow-y: auto; padding: 10px; display: none; }
        .sb-content.active { display: block; }

        ul.tree-list, ul.type-list { list-style: none; padding-left: 10px; margin: 0; font-size: 0.9em; }
        .tree-item { cursor: pointer; padding: 3px 6px; display: block; color: #bbb; border-radius: 3px; }
        .tree-item:hover { background: #333; color: #sec; }
        details > summary { cursor: pointer; color: #999; padding: 3px 0; }
        
        .view-tab { display: none; height: 100%; flex-direction: column; }
        .view-tab.active { display: flex; }
        .dataTables_wrapper { color: #ccc; font-size: 0.9em; flex-grow: 1; overflow-y: auto; }
        table.dataTable tbody tr { background-color: var(--panel) !important; }
        table.dataTable tbody td { border-color: #333; vertical-align: middle; }
        
        .media-thumb { width: 100px; height: 60px; object-fit: contain; background: #000; border: 1px solid #444; cursor: pointer; }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); }
        .modal-content { background: var(--panel); margin: 5% auto; padding: 20px; width: 80%; max-width: 800px; border-radius: 8px; position: relative; max-height: 85vh; overflow-y: auto; }
        .close-modal { position: absolute; right: 15px; top: 10px; color: #fff; font-size: 24px; cursor: pointer; }
        pre.meta-dump { background: #000; padding: 15px; color: #0f0; border-radius: 4px; overflow-x: auto; }
        
        .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .bg-IMAGE { background: #3f51b5; color: #fff; }
        .bg-VIDEO { background: #c2185b; color: #fff; }
        .bg-AUDIO { background: #00796b; color: #fff; }
        .bg-DOCUMENT { background: #e65100; color: #fff; }
        .dupe-alert { background: var(--err); color: #000; font-weight: bold; margin-left: 5px; padding: 1px 4px; border-radius: 3px; font-size: 0.7em; }
        """

        js_content = """
        let mainTable, dupeTable;
        const mediaData = """ + json_payload + """;

        $(document).ready(function() {
            // Main File Table
            mainTable = $('#fileTable').DataTable({
                data: mediaData,
                columns: [
                    { title: "Type", data: 1, render: (d) => `<span class="badge bg-${d}">${d}</span>` },
                    { title: "File Info", data: 2, render: (d, type, row) => {
                        let dup = row[8] > 1 ? '<span class="dupe-alert">DUPLICATE</span>' : '';
                        return `<strong>${d}</strong><br><span style="color:#888; font-size:0.85em">${row[3]}</span>${dup}`;
                    }},
                    { title: "Preview", data: 6, orderable: false, render: (d, type, row) => renderPreview(d, row[1]) },
                    { title: "Size", data: 4, render: (d, type, row) => row[5] },
                    { title: "Actions", data: null, orderable: false, render: (d, type, row) => `<button onclick='viewMeta(${JSON.stringify(row)})'>🔍 Info</button>` },
                    
                    // HIDDEN COLUMNS FOR FILTERING
                    { title: "Folder", data: 9, visible: false },
                    { title: "Ext", data: 10, visible: false },
                    { title: "Hash", data: 0, visible: false }
                ],
                pageLength: 25,
                deferRender: true, 
                dom: 'frtip'
            });

            // Duplicates Table
            const dupeData = mediaData.filter(row => row[8] > 1);
            dupeTable = $('#dupeTable').DataTable({
                data: dupeData,
                columns: [
                    { title: "Group", data: 1 },
                    { title: "Hash (Group ID)", data: 0, render: (d) => `<span style="font-family:monospace">${d.substring(0,12)}...</span>` },
                    { title: "File", data: 3 },
                    { title: "Size", data: 5 },
                    { title: "Copies", data: 8 }
                ],
                order: [[4, 'desc']], 
                pageLength: 25
            });
        });

        function renderPreview(path, group) {
            path = "file:///" + path; 
            if (group === 'IMAGE') return `<img data-src="${path}" class="media-thumb lazy" onclick="window.open('${path}')" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">`; 
            if (group === 'VIDEO') return `<div style="font-size:0.8em; color:#666">🎥 Video<br>(Click Info)</div>`;
            return `<div style="font-size:0.8em; color:#666">📄 File</div>`;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });

        $('#fileTable').on('draw.dt', function () {
            $('.media-thumb.lazy').each(function() { observer.observe(this); });
        });

        function switchTab(tabId) {
            $('.view-tab').removeClass('active');
            $('#view-' + tabId).addClass('active');
        }

        function switchSidebar(tabId) {
            $('.sb-content').removeClass('active');
            $('.tab-btn').removeClass('active');
            $('#sb-' + tabId).addClass('active');
            $(`button[onclick="switchSidebar('${tabId}')"]`).addClass('active');
        }

        // --- FILTERING LOGIC ---
        function filterByFolder(path) {
            switchTab('files');
            if (path === '.') { 
                mainTable.search('').columns().search('').draw(); 
                return; 
            }
            // Escape Regex chars for exact matching start
            let safePath = path.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\\\$&');
            // Filter Column 5 (Folder) using Regex (Start of string)
            mainTable.column(5).search('^' + safePath, true, false).draw();
        }

        function filterByType(group, ext) {
            switchTab('files');
            // Filter Col 0 (Type) and Col 6 (Ext)
            // Note: Column indexes refer to visible + hidden order defined in 'columns' array
            // Type is Index 0. Ext is Index 6.
            mainTable.column(0).search(group).column(6).search(ext).draw();
        }

        function viewMeta(row) {
            $('#metaJson').text(JSON.stringify(JSON.parse(row[7] || "{}"), null, 4));
            $('#metaModal').fadeIn();
            
            let content = '';
            let path = "file:///" + row[6];
            if (row[1] === 'VIDEO') content = `<video controls style="width:100%"><source src="${path}"></video>`;
            if (row[1] === 'AUDIO') content = `<audio controls style="width:100%"><source src="${path}"></audio>`;
            if (row[1] === 'IMAGE') content = `<img src="${path}" style="max-width:100%">`;
            $('#mediaContainer').html(content);
        }
        """

        # --- HTML Structure ---
        html_final = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Media Organizer Dashboard</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>{css_content}</style>
</head>
<body>
    <div id="sidebar">
        <div class="tab-bar">
            <button class="tab-btn active" onclick="switchSidebar('folders')">Folders</button>
            <button class="tab-btn" onclick="switchSidebar('types')">Types</button>
        </div>
        <div id="sb-folders" class="sb-content active">
            <div class="tree-item" onclick="filterByFolder('.')">🏠 All Files</div>
            {root_btn}
            {sidebar_f}
        </div>
        <div id="sb-types" class="sb-content">
            {sidebar_t}
        </div>
    </div>

    <div id="main-area">
        {stats_html}
        
        <div style="margin-bottom:10px;">
            <button onclick="switchTab('files')">📁 File Browser</button>
            <button onclick="switchTab('dupes')">⚠️ Duplicates Report</button>
        </div>

        <div id="view-files" class="view-tab active">
            <table id="fileTable" class="display" style="width:100%"></table>
        </div>

        <div id="view-dupes" class="view-tab">
            <table id="dupeTable" class="display" style="width:100%"></table>
        </div>
    </div>

    <div id="metaModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" onclick="$('#metaModal').fadeOut(); $('#mediaContainer').html('');">&times;</span>
            <h2>Metadata Inspector</h2>
            <div id="mediaContainer" style="text-align:center; margin-bottom:15px; background:#000; min-height:50px;"></div>
            <pre id="metaJson" class="meta-dump"></pre>
        </div>
    </div>

    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>{js_content}</script>
</body>
</html>"""

        print("Writing HTML file...")
        out_path = self.output_dir / "media_dashboard.html"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_final)
        print(f"\n[SUCCESS] Dashboard generated at: {out_path.resolve()}")

if __name__ == "__main__":
    c = ConfigManager(); p = argparse.ArgumentParser()
    p.add_argument('-v', '--version', action='store_true')
    p.add_argument('--generate', action='store_true')
    p.add_argument('--db', type=str)
    a = p.parse_args()
    
    # CRITICAL FIX: Print version and EXIT before doing logic
    if a.version:
        print(f"HTML Dashboard Generator v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}"); sys.exit(0)
    
    db_p = Path(a.db) if a.db else c.OUTPUT_DIR / 'metadata.sqlite'
    if a.generate or not a.version:
        if db_p.exists():
            with DatabaseManager(db_p) as db: HTMLGenerator(db, c).generate_html_report()
        else:
            print(f"Error: Database not found at {db_p}")