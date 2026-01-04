# ==============================================================================
# File: server.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
_CHANGELOG_ENTRIES = [
    "Initial implementation of Flask Server.",
    "Added API endpoints for Statistics, Folder Tree, and File Data.",
    "Implemented Server-Side Processing for DataTables (Pagination/Sorting/Filtering).",
    "Implemented secure media serving route to bypass local file security restrictions.",
    "Created modern Bootstrap 5 Dashboard template with dark mode.",
    "REFACTOR: Implemented full hierarchical Folder Tree (recursive) instead of flat list.",
    "REFACTOR: Added Type/Extension browser to Sidebar.",
    "FIX: Added SQLite custom function 'NORM_PATH' to handle Windows/Linux path separator mismatches.",
    "UX: Restored 3-Tab Sidebar (Browser, Types, Duplicates).",
    "FIX: Switched JS event handling to ID-based lookup to fix broken buttons.",
    "UX: Improved Tree rendering and CSS to ensure folder labels are visible.",
    "LOGIC: Added explicit handling for 'Root Directory' vs 'All Files'."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.2.12
# ------------------------------------------------------------------------------
import os
import json
import sqlite3
import mimetypes
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file, abort

from database_manager import DatabaseManager
from config_manager import ConfigManager

app = Flask(__name__)

# Global instances
DB_PATH = None
CONFIG = None

# --- DATABASE HELPERS ---
def norm_path_sql(path):
    """SQLite Custom Function: Normalize paths to forward slashes for comparison."""
    if path is None: return ""
    return str(path).replace('\\', '/')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Register the normalization function so we can use NORM_PATH() in queries
    conn.create_function("NORM_PATH", 1, norm_path_sql)
    return conn

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Organizer Dashboard</title>
    
    <!-- CSS Dependencies -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    
    <style>
        :root { --sidebar-width: 350px; --header-height: 60px; --bg-dark: #121212; --panel: #1e1e1e; }
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; height: 100vh; overflow: hidden; background-color: var(--bg-dark); }
        
        /* Layout Grid */
        .wrapper { display: flex; height: 100%; width: 100%; }
        
        /* Sidebar Styling */
        #sidebar { 
            width: var(--sidebar-width); 
            background: var(--panel); 
            border-right: 1px solid #333; 
            display: flex; 
            flex-direction: column; 
            flex-shrink: 0;
        }
        .sidebar-header { height: var(--header-height); padding: 0 15px; display: flex; align-items: center; border-bottom: 1px solid #333; background: #252525; }
        .sidebar-brand { font-weight: 600; color: #fff; font-size: 1.1rem; }
        
        /* Sidebar Tabs */
        .nav-tabs-custom { border-bottom: 1px solid #333; display: flex; }
        .nav-item-custom { flex: 1; text-align: center; cursor: pointer; padding: 12px 5px; color: #888; border-bottom: 3px solid transparent; font-size: 0.9rem; transition: all 0.2s; }
        .nav-item-custom:hover { color: #ccc; background: #2a2a2a; }
        .nav-item-custom.active { color: #0dcaf0; border-bottom-color: #0dcaf0; background: #252525; font-weight: bold; }
        
        /* Sidebar Content Areas */
        .sidebar-content { flex: 1; overflow-y: auto; padding: 10px; display: none; }
        .sidebar-content.active { display: block; }
        
        /* Tree View */
        .tree-node { margin-left: 10px; border-left: 1px solid #333; }
        .tree-row { display: flex; align-items: center; padding: 2px 0; }
        .tree-toggler { cursor: pointer; width: 20px; text-align: center; color: #666; font-size: 0.8rem; user-select: none; }
        .tree-toggler:hover { color: #fff; }
        .tree-label { cursor: pointer; padding: 4px 8px; border-radius: 4px; color: #bbb; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; user-select: none; }
        .tree-label:hover { background: #333; color: #fff; }
        .tree-label.selected { background: #0d6efd; color: #fff; }
        .tree-label i { margin-right: 6px; color: #ffc107; }
        
        /* Type List */
        .type-group { margin-bottom: 15px; }
        .type-header { font-weight: bold; color: #888; text-transform: uppercase; font-size: 0.75rem; padding: 5px; border-bottom: 1px solid #333; margin-bottom: 5px; }
        .type-item { display: flex; justify-content: space-between; padding: 4px 10px; cursor: pointer; border-radius: 4px; color: #ccc; font-size: 0.9rem; }
        .type-item:hover { background: #333; color: #fff; }
        .type-item.selected { background: #0d6efd; color: #fff; }
        .count-badge { background: #333; padding: 1px 6px; border-radius: 10px; font-size: 0.75rem; color: #999; }

        /* Main Content */
        #main { flex: 1; display: flex; flex-direction: column; background: var(--bg-dark); min-width: 0; }
        
        /* Top Bar */
        .top-bar { height: var(--header-height); border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; background: var(--panel); }
        .current-path { font-family: monospace; color: #0dcaf0; background: #252525; padding: 4px 10px; border-radius: 4px; }
        
        /* Stats Dashboard */
        .dashboard-stats { display: flex; gap: 15px; padding: 20px; background: #181818; border-bottom: 1px solid #333; }
        .stat-card { background: #252525; flex: 1; padding: 15px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        .stat-val { font-size: 1.4rem; font-weight: bold; color: #fff; }
        .stat-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        
        /* Data Table */
        .table-container { flex: 1; padding: 20px; overflow: hidden; display: flex; flex-direction: column; }
        .dataTables_wrapper { height: 100%; display: flex; flex-direction: column; }
        .dataTables_scroll { flex: 1; overflow: hidden; }
        .dataTables_scrollBody { flex: 1; overflow-y: auto; }
        
        table.dataTable { border-collapse: separate; border-spacing: 0; width: 100% !important; }
        table.dataTable thead th { background: #252525 !important; border-bottom: 1px solid #444 !important; color: #ccc; padding: 12px 10px; position: sticky; top: 0; z-index: 10; }
        table.dataTable tbody td { background: var(--panel) !important; border-bottom: 1px solid #333 !important; color: #ccc; padding: 8px 10px; vertical-align: middle; }
        table.dataTable tbody tr:hover td { background: #2a2a2a !important; color: #fff; }
        
        .badge-type { min-width: 60px; }
        
        /* Modal */
        .modal-content { background: #252525; border: 1px solid #444; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .modal-header { border-bottom: 1px solid #444; }
        .modal-footer { border-top: 1px solid #444; }
        pre.json-view { background: #111; color: #76ff03; padding: 15px; border-radius: 4px; max-height: 400px; overflow: auto; font-size: 0.85rem; }
        
    </style>
</head>
<body>

<div class="wrapper">
    <!-- SIDEBAR -->
    <div id="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-brand"><i class="bi bi-grid-3x3-gap-fill text-info"></i> Media Organizer</div>
        </div>
        
        <!-- Sidebar Tabs -->
        <div class="nav-tabs-custom">
            <div class="nav-item-custom active" onclick="switchTab('browser')"><i class="bi bi-folder2-open"></i> Browser</div>
            <div class="nav-item-custom" onclick="switchTab('types')"><i class="bi bi-tags"></i> Types</div>
            <div class="nav-item-custom" onclick="switchTab('dupes')"><i class="bi bi-files"></i> Duplicates</div>
        </div>
        
        <!-- Tab 1: Folder Browser -->
        <div id="tab-browser" class="sidebar-content active">
            <div class="tree-row">
                <div class="tree-label" onclick="setFilter('all', '', this)">
                    <i class="bi bi-globe"></i> All Files
                </div>
            </div>
            <div class="tree-row">
                <div class="tree-label" onclick="setFilter('root', '', this)">
                    <i class="bi bi-hdd"></i> Files in Root
                </div>
            </div>
            <hr style="border-color:#444; margin: 10px 0;">
            <div id="folder-tree-root">
                <div class="text-center mt-4"><div class="spinner-border text-info" role="status"></div></div>
            </div>
        </div>
        
        <!-- Tab 2: Types -->
        <div id="tab-types" class="sidebar-content">
            <div id="types-list"></div>
        </div>
        
        <!-- Tab 3: Duplicates -->
        <div id="tab-dupes" class="sidebar-content">
            <div class="alert alert-dark border-secondary">
                <small><i class="bi bi-info-circle"></i> This view shows duplicate groups. Click a group to see all copies.</small>
            </div>
            <button class="btn btn-outline-danger w-100 mb-3" onclick="filterByDupes(this)">
                <i class="bi bi-exclamation-triangle"></i> Show All Duplicates
            </button>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div id="main">
        <!-- Top Bar -->
        <div class="top-bar">
            <div>
                <span class="text-secondary me-2">Current View:</span>
                <span id="active-filter-display" class="current-path">All Files</span>
            </div>
            <div>
                <button class="btn btn-sm btn-outline-secondary" onclick="table.ajax.reload()"><i class="bi bi-arrow-clockwise"></i> Refresh</button>
            </div>
        </div>
        
        <!-- Stats -->
        <div class="dashboard-stats">
            <div class="stat-card">
                <div class="stat-label">Total Files</div>
                <div class="stat-val" id="stat-total">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Size</div>
                <div class="stat-val text-info" id="stat-size">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duplicates</div>
                <div class="stat-val text-warning" id="stat-dupes">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Wasted Space</div>
                <div class="stat-val text-danger" id="stat-waste">-</div>
            </div>
        </div>
        
        <!-- Table -->
        <div class="table-container">
            <table id="fileTable" class="table table-sm w-100">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Filename</th>
                        <th>Path</th>
                        <th>Size</th>
                        <th>Date</th>
                        <th>Action</th>
                    </tr>
                </thead>
            </table>
        </div>
    </div>
</div>

<!-- Modal -->
<div class="modal fade" id="detailModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Asset Details</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body row">
                <div class="col-md-7">
                    <div id="preview-container" class="bg-black d-flex align-items-center justify-content-center" style="min-height:400px; border-radius:4px; height: 100%;">
                        <!-- Media injected here -->
                    </div>
                </div>
                <div class="col-md-5">
                    <h6 class="text-info">Metadata</h6>
                    <pre id="modal-meta" class="json-view"></pre>
                    <div class="mt-3">
                        <a id="download-link" href="#" class="btn btn-primary w-100" target="_blank"><i class="bi bi-download"></i> Open Original File</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Scripts -->
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>

<script>
    let table;
    let currentFilter = { type: 'all', value: '' };

    $(document).ready(function() {
        initStats();
        initTree();
        initTypes();
        initTable();
    });

    // --- INITIALIZATION ---
    function initStats() {
        $.get('/api/stats', function(data) {
            $('#stat-total').text(data.total_files.toLocaleString());
            $('#stat-size').text(data.total_size);
            $('#stat-dupes').text(data.duplicates.toLocaleString());
            $('#stat-waste').text(data.wasted_size);
        });
    }

    function initTable() {
        table = $('#fileTable').DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/api/files',
                data: function(d) {
                    d.filter_type = currentFilter.type;
                    d.filter_value = currentFilter.value;
                }
            },
            columns: [
                { data: 'type', render: (d) => `<span class="badge bg-secondary badge-type">${d}</span>` },
                { data: 'name', render: (d) => `<strong>${d}</strong>` },
                { data: 'rel_path', render: (d) => `<div class="text-truncate" style="max-width:350px; color:#888;" title="${d}">${d}</div>` },
                { data: 'size_str' },
                { data: 'date', render: (d) => `<small class="text-muted">${d.split(' ')[0]}</small>` },
                { data: 'id', orderable: false, render: (d) => 
                    `<button class="btn btn-sm btn-outline-info" onclick="fetchAndOpenModal(${d})"><i class="bi bi-eye"></i> View</button>` 
                }
            ],
            pageLength: 25,
            scrollY: '50vh',
            scrollCollapse: true,
            deferRender: true,
            order: [[1, 'asc']]
        });
    }

    // --- TREE VIEW LOGIC ---
    function initTree() {
        $.get('/api/tree', function(data) {
            // data is nested dict
            let html = buildTreeHtml(data);
            $('#folder-tree-root').html(html);
        });
    }

    function buildTreeHtml(node, path='') {
        let html = '';
        let keys = Object.keys(node).sort();

        keys.forEach(key => {
            let currentPath = path ? `${path}/${key}` : key;
            let children = node[key];
            let hasChildren = Object.keys(children).length > 0;
            
            // Container for this node
            html += `<div>`;
            
            // Row
            html += `<div class="tree-row">`;
            
            // Toggler
            if (hasChildren) {
                // Generate unique ID for collapse
                let uid = Math.random().toString(36).substr(2, 9);
                html += `<span class="tree-toggler" onclick="toggleNode(this)">▶</span>`;
            } else {
                html += `<span class="tree-toggler" style="opacity:0">●</span>`;
            }
            
            // Label
            // We use encodeURIComponent to ensure special chars in path don't break JS
            html += `<span class="tree-label" onclick="setFilter('folder', '${encodeURIComponent(currentPath)}', this)">
                        <i class="bi bi-folder"></i> ${key}
                     </span>`;
            html += `</div>`;
            
            // Children Container (Hidden by default)
            if (hasChildren) {
                html += `<div class="tree-node" style="display:none;">${buildTreeHtml(children, currentPath)}</div>`;
            }
            
            html += `</div>`;
        });
        return html;
    }

    function toggleNode(el) {
        let container = $(el).parent().next('.tree-node');
        if (container.is(':visible')) {
            container.slideUp('fast');
            $(el).text('▶');
        } else {
            container.slideDown('fast');
            $(el).text('▼');
        }
    }

    // --- TYPES LOGIC ---
    function initTypes() {
        $.get('/api/types', function(data) {
            let html = '';
            for (const [group, exts] of Object.entries(data)) {
                html += `<div class="type-group">`;
                html += `<div class="type-header">${group}</div>`;
                let sortedExts = Object.entries(exts).sort((a,b) => b[1] - a[1]);
                
                sortedExts.forEach(([ext, count]) => {
                    html += `<div class="type-item" onclick="setFilter('ext', '${ext}', this)">
                                <span>${ext}</span>
                                <span class="count-badge">${count}</span>
                             </div>`;
                });
                html += `</div>`;
            }
            $('#types-list').html(html);
        });
    }

    // --- FILTERING ---
    function setFilter(type, value, el) {
        // Decode value if it came from the tree
        if (type === 'folder') value = decodeURIComponent(value);
        
        currentFilter = { type: type, value: value };
        
        // UI Updates
        $('.tree-label, .type-item, .nav-item-custom').removeClass('selected');
        if (el) $(el).addClass('selected');
        
        // Title Update
        let title = value || "All Files";
        if (type === 'dupes') title = "Duplicate Files";
        if (type === 'root') title = "Files in Root Directory";
        if (type === 'all') title = "All Files";
        
        $('#active-filter-display').text(title);
        table.ajax.reload();
    }
    
    function filterByDupes(el) {
        setFilter('dupes', 'true', el);
    }

    function switchTab(tab) {
        $('.sidebar-content').removeClass('active');
        $('.nav-item-custom').removeClass('active');
        $(`#tab-${tab}`).addClass('active');
        $(`.nav-item-custom[onclick="switchTab('${tab}')"]`).addClass('active');
    }

    // --- MODAL ---
    window.fetchAndOpenModal = function(fileId) {
        // Fetch full details from server
        $.get(`/api/details/${fileId}`, function(data) {
            openModal(data);
        });
    }

    function openModal(data) {
        // Meta
        let metaObj = {};
        try { metaObj = JSON.parse(data.metadata); } catch(e) {}
        $('#modal-meta').text(JSON.stringify(metaObj, null, 4));
        
        // Download Link
        let url = `/api/media/${data.id}`;
        $('#download-link').attr('href', url);
        
        // Preview
        let html = '<div class="text-secondary">No Preview Available</div>';
        if (data.type === 'IMAGE') {
            html = `<img src="${url}" style="max-width:100%; max-height:100%; object-fit:contain;">`;
        } else if (data.type === 'VIDEO') {
            html = `<video controls autoplay style="max-width:100%; max-height:100%"><source src="${url}"></video>`;
        } else if (data.type === 'AUDIO') {
            html = `<div style="text-align:center"><i class="bi bi-music-note-beamed" style="font-size:4rem; color:#666;"></i><br><br><audio controls src="${url}"></audio></div>`;
        }
        
        $('#preview-container').html(html);
        new bootstrap.Modal(document.getElementById('detailModal')).show();
    };

</script>
</body>
</html>
"""

# --- HELPERS ---
def format_size(size_bytes):
    if not size_bytes: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def build_tree_dict(paths):
    """Converts a list of paths into a nested dictionary tree."""
    tree = {}
    for path in paths:
        # Normalize to forward slash
        clean_path = path.replace('\\', '/')
        parts = clean_path.split('/')
        current = tree
        for part in parts:
            if not part: continue
            current = current.setdefault(part, {})
    return tree

# --- ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
    size = conn.execute("SELECT SUM(size) FROM MediaContent").fetchone()[0] or 0
    wasted = conn.execute("SELECT SUM(mc.size) FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash=mc.content_hash WHERE fpi.is_primary=0").fetchone()[0] or 0
    dupes = conn.execute("SELECT COUNT(*) FROM (SELECT content_hash FROM FilePathInstances GROUP BY content_hash HAVING COUNT(*) > 1)").fetchone()[0]
    conn.close()
    return jsonify({'total_files': total, 'total_size': format_size(size), 'duplicates': dupes, 'wasted_size': format_size(wasted)})

@app.route('/api/tree')
def api_tree():
    """Returns a recursive dictionary of folders."""
    conn = get_db()
    query = "SELECT DISTINCT NORM_PATH(original_relative_path) FROM FilePathInstances"
    rows = conn.execute(query).fetchall()
    conn.close()
    
    folder_paths = set()
    for r in rows:
        p = Path(r[0]).parent
        if str(p) != '.':
            folder_paths.add(str(p))
            
    tree = build_tree_dict(folder_paths)
    return jsonify(tree)

@app.route('/api/types')
def api_types():
    conn = get_db()
    query = "SELECT mc.file_type_group, NORM_PATH(fpi.original_relative_path) FROM MediaContent mc JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash"
    rows = conn.execute(query).fetchall()
    conn.close()
    
    data = {}
    for group, path in rows:
        ext = Path(path).suffix.lower() or "no_ext"
        if group not in data: data[group] = {}
        if ext not in data[group]: data[group][ext] = 0
        data[group][ext] += 1
    return jsonify(data)

@app.route('/api/details/<int:file_id>')
def api_details(file_id):
    """Fetch single file details for Modal."""
    conn = get_db()
    query = """
    SELECT fpi.file_id, fpi.original_relative_path, mc.file_type_group, mc.extended_metadata
    FROM FilePathInstances fpi
    JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
    WHERE fpi.file_id = ?
    """
    row = conn.execute(query, (file_id,)).fetchone()
    conn.close()
    
    if not row: return jsonify({})
    return jsonify({
        "id": row[0],
        "name": Path(row[1]).name,
        "type": row[2],
        "metadata": row[3]
    })

@app.route('/api/files')
def api_files():
    conn = get_db()
    
    # DataTable Params
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 25))
    search = request.args.get('search[value]', '').lower()
    
    # Custom Filters
    f_type = request.args.get('filter_type', 'all')
    f_val = request.args.get('filter_value', '')

    base_query = """
    SELECT fpi.file_id, fpi.content_hash, fpi.original_relative_path, 
           mc.file_type_group, mc.size, mc.date_best
    FROM FilePathInstances fpi
    JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
    """
    
    where = []
    params = []
    
    # Global Search
    if search:
        where.append("(NORM_PATH(fpi.original_relative_path) LIKE ? OR mc.file_type_group LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
        
    # Filters
    if f_type == 'folder':
        if f_val:
            clean_val = f_val.replace('\\', '/')
            # Ensure filtering matches only inside this folder (and subfolders)
            where.append("NORM_PATH(fpi.original_relative_path) LIKE ?")
            params.append(f"{clean_val}/%")
            
    elif f_type == 'root':
        # Files where the relative path has no slashes (top level)
        where.append("instr(NORM_PATH(fpi.original_relative_path), '/') = 0")
        
    elif f_type == 'ext':
        where.append("NORM_PATH(fpi.original_relative_path) LIKE ?")
        params.append(f"%{f_val}")
        
    elif f_type == 'dupes':
        where.append("fpi.content_hash IN (SELECT content_hash FROM FilePathInstances GROUP BY content_hash HAVING COUNT(*) > 1)")

    if where:
        base_query += " WHERE " + " AND ".join(where)
        
    # Totals
    try:
        total_records = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
        count_sql = f"SELECT COUNT(*) FROM ({base_query})"
        filtered_records = conn.execute(count_sql, params).fetchone()[0]
        
        # Sort & Paginate
        base_query += " LIMIT ? OFFSET ?"
        params.extend([length, start])
        
        rows = conn.execute(base_query, params).fetchall()
    except Exception as e:
        print(f"Query Error: {e}")
        rows = []
        filtered_records = 0
        total_records = 0

    conn.close()
    
    data = []
    for r in rows:
        data.append({
            "id": r[0],
            "hash": r[1],
            "rel_path": r[2],
            "name": Path(r[2]).name,
            "type": r[3],
            "size": r[4],
            "size_str": format_size(r[4]),
            "date": r[5] or "Unknown"
        })
        
    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": filtered_records,
        "data": data
    })

@app.route('/api/media/<int:file_id>')
def serve_media(file_id):
    conn = get_db()
    row = conn.execute("SELECT original_full_path FROM FilePathInstances WHERE file_id = ?", (file_id,)).fetchone()
    conn.close()
    if not row or not os.path.exists(row[0]): abort(404)
    
    mime, _ = mimetypes.guess_type(row[0])
    return send_file(row[0], mimetype=mime)

def run_server(config_manager):
    global DB_PATH, CONFIG
    CONFIG = config_manager
    DB_PATH = CONFIG.OUTPUT_DIR / 'metadata.sqlite'
    if not DB_PATH.exists():
        print("Database not found.")
        return
    print("Starting Dashboard on http://127.0.0.1:5000")
    app.run(port=5000, debug=False)

if __name__ == '__main__':
    pass