# ==============================================================================
# File: server.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 4
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
    "LOGIC: Added explicit handling for 'Root Directory' vs 'All Files'.",
    "FEATURE: Added Server-Side Sorting implementation for DataTables.",
    "FEATURE: Restored Image Thumbnails in the main table.",
    "FEATURE: Added 'Report' Tab with aggregate statistics (Charts/Tables).",
    "FEATURE: Added 'Unique Files' filter mode.",
    "FEATURE: Added Advanced Filters (Size, Date Year).",
    "FIX: Resolved SyntaxError (f-string backslash) for Python < 3.12 compatibility.",
    "REPORTING: Implemented Comprehensive Analysis (Res/Quality/Bitrate) in /api/report.",
    "FIX: Corrected logic for Duplicate vs Redundant counts.",
    "FIX: Improved extension normalization in Sidebar counts.",
    "FIX: Resolved f-string backslash SyntaxError (again) by moving replacement logic out.",
    "REPORTING: Added Image Quality (Megapixel) breakdown.",
    "FIX: Improved Audio Bitrate parsing to handle 'kbps' strings and prevent 'Unknown' results.",
    "UX: Renamed 'Duplicates' stat to 'Redundant Copies' for clarity.",
    "CLI: Added --version and --help support."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.4.26
# ------------------------------------------------------------------------------
import os
import json
import sqlite3
import mimetypes
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from flask import Flask, render_template_string, request, jsonify, send_file, abort

from database_manager import DatabaseManager
from config_manager import ConfigManager

app = Flask(__name__)

# Global instances
DB_PATH = None
CONFIG = None

# --- DATABASE HELPERS ---
def norm_path_sql(path):
    if path is None: return ""
    return str(path).replace('\\', '/')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("NORM_PATH", 1, norm_path_sql)
    return conn

def format_size(size_bytes):
    if not size_bytes: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Organizer</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    
    <style>
        :root { --sidebar-width: 320px; --header-height: 55px; --bg-dark: #121212; --panel: #1e1e1e; --accent: #0d6efd; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; height: 100vh; overflow: hidden; background-color: var(--bg-dark); }
        
        .wrapper { display: flex; height: 100%; width: 100%; }
        
        /* Sidebar */
        #sidebar { width: var(--sidebar-width); background: var(--panel); border-right: 1px solid #333; display: flex; flex-direction: column; flex-shrink: 0; }
        .sidebar-header { height: var(--header-height); padding: 0 15px; display: flex; align-items: center; border-bottom: 1px solid #333; background: #252525; }
        .sidebar-brand { font-weight: 600; color: #fff; font-size: 1.1rem; }
        
        .nav-tabs-custom { border-bottom: 1px solid #333; display: flex; }
        .nav-item-custom { flex: 1; text-align: center; cursor: pointer; padding: 12px 5px; color: #888; border-bottom: 3px solid transparent; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
        .nav-item-custom:hover { background: #2a2a2a; color: #ccc; }
        .nav-item-custom.active { color: var(--accent); border-bottom-color: var(--accent); background: #252525; font-weight: bold; }
        
        .sidebar-content { flex: 1; overflow-y: auto; padding: 10px; display: none; }
        .sidebar-content.active { display: block; }
        
        /* Tree */
        .tree-node { margin-left: 12px; border-left: 1px solid #333; }
        .tree-row { display: flex; align-items: center; padding: 2px 0; }
        .tree-toggler { cursor: pointer; width: 18px; text-align: center; color: #666; font-size: 0.7rem; }
        .tree-label { cursor: pointer; padding: 4px 8px; border-radius: 4px; color: #bbb; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.9rem; }
        .tree-label:hover { background: #333; color: #fff; }
        .tree-label.selected { background: var(--accent); color: #fff; }
        .tree-label i { margin-right: 6px; color: #ffc107; }

        /* Main */
        #main { flex: 1; display: flex; flex-direction: column; background: var(--bg-dark); min-width: 0; }
        .top-bar { height: var(--header-height); border-bottom: 1px solid #333; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; background: var(--panel); }
        
        /* Dashboard Stats */
        .stats-row { display: flex; gap: 15px; padding: 15px 20px; background: #181818; border-bottom: 1px solid #333; }
        .stat-card { background: #252525; flex: 1; padding: 10px 15px; border-radius: 6px; border: 1px solid #333; display: flex; flex-direction: column; justify-content: center; }
        .stat-val { font-size: 1.2rem; font-weight: bold; color: #fff; }
        .stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; }

        /* Advanced Filters */
        .filters-bar { padding: 10px 20px; background: #1a1a1a; border-bottom: 1px solid #333; display: flex; gap: 10px; align-items: center; }
        .form-select-sm, .form-control-sm { background-color: #2b2b2b; border-color: #444; color: #eee; }
        
        /* Table */
        .table-container { flex: 1; padding: 0 20px 20px 20px; overflow: hidden; display: flex; flex-direction: column; }
        .dataTables_wrapper { height: 100%; display: flex; flex-direction: column; font-size: 0.9rem; }
        .dataTables_scroll { flex: 1; overflow: hidden; }
        .dataTables_scrollBody { flex: 1; overflow-y: auto; }
        
        table.dataTable thead th { background: #252525 !important; color: #aaa; font-weight: 600; border-bottom: 1px solid #444 !important; }
        table.dataTable tbody td { background: var(--panel) !important; border-color: #333 !important; color: #ccc; vertical-align: middle; }
        .badge-type { width: 55px; font-size: 0.7rem; }
        .thumb-img { width: 50px; height: 35px; object-fit: cover; border-radius: 3px; background: #000; border: 1px solid #444; cursor: zoom-in; }

        /* Views */
        .view-section { display: none; height: 100%; flex-direction: column; }
        .view-section.active { display: flex; }
        
        /* Report View */
        .report-container { padding: 20px; overflow-y: auto; }
        .report-card { background: var(--panel); border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .report-table th { color: #888; border-bottom: 1px solid #444; font-size: 0.9rem; }
        .report-table td { color: #ddd; vertical-align: middle; }
        h4.report-title { color: var(--accent); margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px; }

    </style>
</head>
<body>

<div class="wrapper">
    <!-- Sidebar -->
    <div id="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-brand"><i class="bi bi-hdd-network-fill text-primary"></i> Media Organizer</div>
        </div>
        <div class="nav-tabs-custom">
            <div class="nav-item-custom active" onclick="switchSidebar('browser')">Browser</div>
            <div class="nav-item-custom" onclick="switchSidebar('types')">Types</div>
            <div class="nav-item-custom" onclick="switchSidebar('dupes')">Dupes</div>
        </div>
        
        <!-- Browser Tab -->
        <div id="sb-browser" class="sidebar-content active">
            <div class="tree-row">
                <div class="tree-label" onclick="setFilter('all', '', this)"><i class="bi bi-collection"></i> All Files</div>
            </div>
            <div class="tree-row">
                <div class="tree-label" onclick="setFilter('unique', '', this)"><i class="bi bi-star-fill text-warning"></i> Unique Files</div>
            </div>
            <div class="tree-row">
                <div class="tree-label" onclick="setFilter('root', '', this)"><i class="bi bi-hdd"></i> Files in Root</div>
            </div>
            <hr style="border-color:#444; margin:10px 0;">
            <div id="tree-root"><div class="text-center text-muted mt-3">Loading...</div></div>
        </div>
        
        <!-- Types Tab -->
        <div id="sb-types" class="sidebar-content">
            <div id="types-list"></div>
        </div>
        
        <!-- Dupes Tab -->
        <div id="sb-dupes" class="sidebar-content">
            <div class="d-grid gap-2">
                <button class="btn btn-outline-danger btn-sm" onclick="setFilter('dupes', 'true', this)">Show All Duplicates</button>
            </div>
            <small class="text-muted d-block mt-2 p-2">Select a group below (Coming Soon)</small>
        </div>
    </div>

    <!-- Main -->
    <div id="main">
        <div class="top-bar">
            <div class="d-flex align-items-center gap-3">
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-secondary active" onclick="switchMainView('table', this)"><i class="bi bi-table"></i> Data</button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="switchMainView('report', this)"><i class="bi bi-bar-chart-line"></i> Report</button>
                </div>
                <span class="text-muted border-start ps-3" id="view-label">All Files</span>
            </div>
            <button class="btn btn-sm btn-dark" onclick="table.ajax.reload()"><i class="bi bi-arrow-clockwise"></i></button>
        </div>

        <!-- View: Table -->
        <div id="view-table" class="view-section active">
            <!-- Stats -->
            <div class="stats-row">
                <div class="stat-card"><div class="stat-label">Total Files</div><div class="stat-val" id="st-total">-</div></div>
                <div class="stat-card"><div class="stat-label">Size</div><div class="stat-val text-info" id="st-size">-</div></div>
                <div class="stat-card"><div class="stat-label">Redundant Copies</div><div class="stat-val text-warning" id="st-dupes">-</div></div>
                <div class="stat-card"><div class="stat-label">Wasted</div><div class="stat-val text-danger" id="st-waste">-</div></div>
            </div>
            
            <!-- Filters -->
            <div class="filters-bar">
                <span class="text-muted small">FILTERS:</span>
                <select class="form-select form-select-sm" style="width:150px;" id="filter-size">
                    <option value="">Any Size</option>
                    <option value="1048576">> 1 MB</option>
                    <option value="104857600">> 100 MB</option>
                    <option value="1073741824">> 1 GB</option>
                </select>
                <select class="form-select form-select-sm" style="width:150px;" id="filter-year">
                    <option value="">Any Year</option>
                    <!-- Populated by JS -->
                </select>
                <button class="btn btn-sm btn-outline-primary" onclick="table.ajax.reload()">Apply</button>
            </div>

            <!-- Table -->
            <div class="table-container">
                <table id="fileTable" class="table table-hover w-100">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Preview</th>
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

        <!-- View: Report -->
        <div id="view-report" class="view-section">
            <div class="report-container" id="report-content">
                <div class="text-center mt-5"><div class="spinner-border text-primary"></div></div>
            </div>
        </div>
    </div>
</div>

<!-- Modal -->
<div class="modal fade" id="metaModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content bg-dark border-secondary">
            <div class="modal-header border-secondary">
                <h5 class="modal-title text-light">File Inspector</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body row">
                <div class="col-md-7 d-flex align-items-center justify-content-center bg-black rounded" style="min-height:400px;" id="modal-preview"></div>
                <div class="col-md-5">
                    <h6 class="text-info">Metadata</h6>
                    <pre id="modal-json" class="p-3 rounded bg-black text-success" style="height:350px; overflow:auto; font-size:0.85rem;"></pre>
                    <a id="modal-download" href="#" target="_blank" class="btn btn-primary w-100 mt-3"><i class="bi bi-box-arrow-up-right"></i> Open Original</a>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>

<script>
    let table;
    let filterState = { type: 'all', val: '' };

    $(document).ready(function() {
        initStats();
        initTree();
        initTypes();
        initTable();
        initYears();
    });

    // --- INIT ---
    function initStats() {
        $.get('/api/stats', function(d) {
            $('#st-total').text(d.total_files.toLocaleString());
            $('#st-size').text(d.total_size);
            $('#st-dupes').text(d.duplicates.toLocaleString());
            $('#st-waste').text(d.wasted_size);
        });
    }

    function initYears() {
        let y = new Date().getFullYear();
        let html = '<option value="">Any Year</option>';
        for(let i=y; i>=1990; i--) html += `<option value="${i}">${i}</option>`;
        $('#filter-year').html(html);
    }

    function initTable() {
        table = $('#fileTable').DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/api/files',
                data: function(d) {
                    d.f_type = filterState.type;
                    d.f_val = filterState.val;
                    d.min_size = $('#filter-size').val();
                    d.year = $('#filter-year').val();
                }
            },
            columns: [
                { data: 'type', render: d => `<span class="badge bg-secondary badge-type">${d}</span>` },
                { data: 'id', orderable: false, render: (d, t, r) => renderThumb(d, r.type) },
                { data: 'name', render: d => `<strong>${d}</strong>` },
                { data: 'rel_path', render: d => `<div class="text-truncate text-muted" style="max-width:300px" title="${d}">${d}</div>` },
                { data: 'size_str' },
                { data: 'date', render: d => d ? d.split(' ')[0] : '-' },
                { data: 'id', orderable: false, render: d => `<button class="btn btn-sm btn-outline-info" onclick="openMeta(${d})"><i class="bi bi-info-circle"></i></button>` }
            ],
            order: [[2, 'asc']], // Default sort by Name
            pageLength: 25,
            lengthMenu: [25, 50, 100],
            language: { search: "", searchPlaceholder: "Search filenames..." },
            dom: 'frtip',
            scrollY: 'calc(100vh - 280px)',
            scrollCollapse: true,
            deferRender: true
        });
    }

    function renderThumb(id, type) {
        if (type === 'IMAGE') return `<img src="/api/media/${id}" class="thumb-img" loading="lazy" onclick="openMeta(${id})">`;
        if (type === 'VIDEO') return `<i class="bi bi-film fs-4 text-muted"></i>`;
        if (type === 'AUDIO') return `<i class="bi bi-music-note fs-4 text-muted"></i>`;
        return `<i class="bi bi-file-earmark fs-4 text-muted"></i>`;
    }

    // --- SIDEBAR LOGIC ---
    function initTree() {
        $.get('/api/tree', function(data) {
            $('#tree-root').html(buildTree(data));
        });
    }

    function buildTree(node, path='') {
        let html = '';
        Object.keys(node).sort().forEach(key => {
            let full = path ? `${path}/${key}` : key;
            let hasChild = Object.keys(node[key]).length > 0;
            html += `<div class="tree-node">
                <div class="tree-row">
                    <span class="tree-toggler" onclick="toggleTree(this)">${hasChild ? '▶' : '●'}</span>
                    <span class="tree-label" onclick="setFilter('folder', '${encodeURIComponent(full)}', this)">
                        <i class="bi bi-folder"></i> ${key}
                    </span>
                </div>`;
            if (hasChild) {
                html += `<div style="display:none">${buildTree(node[key], full)}</div>`;
            }
            html += `</div>`;
        });
        return html;
    }

    function toggleTree(el) {
        let sub = $(el).parent().next();
        if (sub.is(':visible')) { sub.slideUp('fast'); $(el).text('▶'); }
        else { sub.slideDown('fast'); $(el).text('▼'); }
    }

    function initTypes() {
        $.get('/api/types', function(data) {
            let html = '';
            for (let [g, exts] of Object.entries(data)) {
                html += `<div class="mb-2"><small class="fw-bold text-muted ps-2">${g}</small>`;
                Object.entries(exts).sort((a,b)=>b[1]-a[1]).forEach(([ext, cnt]) => {
                    html += `<div class="tree-row ps-3">
                        <span class="tree-label" onclick="setFilter('ext', '${ext}', this)">
                            ${ext} <span class="badge bg-dark float-end text-secondary">${cnt}</span>
                        </span>
                    </div>`;
                });
                html += `</div>`;
            }
            $('#types-list').html(html);
        });
    }

    function setFilter(type, val, el) {
        if (type === 'folder') val = decodeURIComponent(val);
        filterState = { type: type, val: val };
        
        $('.tree-label, .nav-item-custom, .btn').removeClass('selected active');
        if (el) $(el).addClass('selected');
        
        let label = val || (type === 'dupes' ? 'Duplicates' : type === 'unique' ? 'Unique Files' : 'All Files');
        $('#view-label').text(label);
        
        switchMainView('table');
        table.ajax.reload();
    }

    function switchSidebar(tab) {
        $('.sidebar-content').removeClass('active');
        $(`#sb-${tab}`).addClass('active');
        $('.nav-item-custom').removeClass('active');
        event.target.classList.add('active');
    }

    function switchMainView(view, btn) {
        $('.view-section').removeClass('active');
        $(`#view-${view}`).addClass('active');
        if(btn) {
            $('.btn-group .btn').removeClass('active');
            $(btn).addClass('active');
        }
        
        if (view === 'report') loadReport();
    }

    // --- MODAL ---
    function openMeta(id) {
        $.get(`/api/details/${id}`, function(d) {
            let meta = {};
            try { meta = JSON.parse(d.metadata); } catch(e) {}
            $('#modal-json').text(JSON.stringify(meta, null, 4));
            $('#modal-download').attr('href', `/api/media/${id}`);
            
            let preview = '<div class="text-muted">No Preview</div>';
            let src = `/api/media/${id}`;
            if (d.type === 'IMAGE') preview = `<img src="${src}" style="max-width:100%; max-height:100%; object-fit:contain">`;
            if (d.type === 'VIDEO') preview = `<video controls autoplay style="max-width:100%"><source src="${src}"></video>`;
            if (d.type === 'AUDIO') preview = `<audio controls src="${src}"></audio>`;
            
            $('#modal-preview').html(preview);
            new bootstrap.Modal('#metaModal').show();
        });
    }

    // --- REPORT ---
    function loadReport() {
        $('#report-content').html('<div class="text-center mt-5"><div class="spinner-border text-primary"></div></div>');
        $.get('/api/report', function(html) {
            $('#report-content').html(html);
        });
    }
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
    tree = {}
    for path in paths:
        clean = path.replace('\\', '/')
        parts = clean.split('/')
        curr = tree
        for part in parts:
            if not part: continue
            curr = curr.setdefault(part, {})
    return tree

# --- ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
    size = conn.execute("SELECT SUM(size) FROM MediaContent").fetchone()[0] or 0
    wasted = conn.execute("SELECT SUM(mc.size) FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash=mc.content_hash WHERE fpi.is_primary=0").fetchone()[0] or 0
    dupes = conn.execute("SELECT COUNT(*) FROM FilePathInstances WHERE is_primary=0").fetchone()[0]
    conn.close()
    return jsonify({'total_files': total, 'total_size': format_size(size), 'duplicates': dupes, 'wasted_size': format_size(wasted)})

@app.route('/api/tree')
def api_tree():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT NORM_PATH(original_relative_path) FROM FilePathInstances").fetchall()
    conn.close()
    paths = set()
    for r in rows:
        p = Path(r[0]).parent
        if str(p) != '.': paths.add(str(p))
    return jsonify(build_tree_dict(paths))

@app.route('/api/types')
def api_types():
    conn = get_db()
    rows = conn.execute("SELECT mc.file_type_group, NORM_PATH(fpi.original_relative_path) FROM MediaContent mc JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash").fetchall()
    conn.close()
    data = {}
    for g, p in rows:
        ext = Path(p).suffix.lower() or "no_ext"
        if g not in data: data[g] = {}
        data[g][ext] = data[g].get(ext, 0) + 1
    return jsonify(data)

@app.route('/api/files')
def api_files():
    conn = get_db()
    args = request.args
    draw = int(args.get('draw', 1))
    start = int(args.get('start', 0))
    length = int(args.get('length', 25))
    search = args.get('search[value]', '').lower()
    
    # Sort
    col_idx = args.get('order[0][column]')
    col_dir = args.get('order[0][dir]', 'asc')
    col_map = {0:'mc.file_type_group', 2:'fpi.original_relative_path', 4:'mc.size', 5:'mc.date_best'}
    order_clause = f"ORDER BY {col_map.get(int(col_idx), 'fpi.original_relative_path')} {col_dir}" if col_idx else ""

    # Filters
    f_type = args.get('f_type', 'all')
    f_val = args.get('f_val', '')
    min_size = args.get('min_size')
    year = args.get('year')

    base = """SELECT fpi.file_id, fpi.content_hash, fpi.original_relative_path, mc.file_type_group, mc.size, mc.date_best 
              FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash"""
    
    where = []
    params = []
    
    if search:
        where.append("(NORM_PATH(fpi.original_relative_path) LIKE ? OR mc.file_type_group LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    if f_type == 'folder' and f_val:
        clean_val = f_val.replace('\\', '/')
        # FIXED: Logic moved out of f-string
        param_val = f"{clean_val}/%" 
        where.append("NORM_PATH(fpi.original_relative_path) LIKE ?")
        params.append(param_val)
    elif f_type == 'root':
        where.append("instr(NORM_PATH(fpi.original_relative_path), '/') = 0")
    elif f_type == 'unique':
        where.append("fpi.is_primary = 1")
    elif f_type == 'dupes':
        where.append("fpi.content_hash IN (SELECT content_hash FROM FilePathInstances GROUP BY content_hash HAVING COUNT(*) > 1)")
    elif f_type == 'ext':
        where.append("NORM_PATH(fpi.original_relative_path) LIKE ?")
        params.append(f"%{f_val}")

    if min_size:
        where.append("mc.size >= ?")
        params.append(min_size)
    if year:
        where.append("mc.date_best LIKE ?")
        params.append(f"{year}%")

    if where: base += " WHERE " + " AND ".join(where)
    
    # Totals
    total = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
    filtered = conn.execute(f"SELECT COUNT(*) FROM ({base})", params).fetchone()[0]
    
    sql = f"{base} {order_clause} LIMIT ? OFFSET ?"
    params.extend([length, start])
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    data = []
    for r in rows:
        data.append({
            "id": r[0], "hash": r[1], "rel_path": r[2], "type": r[3], "size": r[4], 
            "size_str": format_size(r[4]), "date": r[5], "name": Path(r[2]).name
        })
        
    return jsonify({"draw": draw, "recordsTotal": total, "recordsFiltered": filtered, "data": data})

@app.route('/api/details/<int:id>')
def api_details(id):
    conn = get_db()
    row = conn.execute("SELECT fpi.file_id, fpi.original_relative_path, mc.file_type_group, mc.extended_metadata FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash WHERE fpi.file_id = ?", (id,)).fetchone()
    conn.close()
    return jsonify({"id": row[0], "name": Path(row[1]).name, "type": row[2], "metadata": row[3]}) if row else {}

@app.route('/api/media/<int:id>')
def serve(id):
    conn = get_db()
    row = conn.execute("SELECT original_full_path FROM FilePathInstances WHERE file_id=?", (id,)).fetchone()
    conn.close()
    if row and os.path.exists(row[0]):
        mime, _ = mimetypes.guess_type(row[0])
        return send_file(row[0], mimetype=mime)
    abort(404)

@app.route('/api/report')
def api_report():
    """Generates a comprehensive HTML report."""
    conn = get_db()
    
    # 1. Type Distribution
    type_data = conn.execute("""
        SELECT mc.file_type_group, COUNT(*), SUM(mc.size)
        FROM MediaContent mc
        JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
        GROUP BY mc.file_type_group
    """).fetchall()
    
    type_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Category</th><th>Total Files</th><th>Total Size</th></tr></thead><tbody>'
    for grp, count, size in type_data:
        type_html += f"<tr><td>{grp}</td><td>{count:,}</td><td>{format_size(size)}</td></tr>"
    type_html += '</tbody></table>'

    # 2. Extension Breakdown (Top 20)
    ext_data = conn.execute("""
        SELECT NORM_PATH(fpi.original_relative_path), mc.size 
        FROM FilePathInstances fpi 
        JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
    """).fetchall()
    
    ext_stats = defaultdict(lambda: {'count': 0, 'size': 0})
    for p, s in ext_data:
        ext = Path(p).suffix.lower() or "No Ext"
        ext_stats[ext]['count'] += 1
        ext_stats[ext]['size'] += s
    
    ext_html = '<table class="table table-dark table-sm table-striped report-table"><thead><tr><th>Extension</th><th>Count</th><th>Size</th></tr></thead><tbody>'
    for ext, stats in sorted(ext_stats.items(), key=lambda x: x[1]['size'], reverse=True)[:20]:
        ext_html += f"<tr><td>{ext}</td><td>{stats['count']:,}</td><td>{format_size(stats['size'])}</td></tr>"
    ext_html += '</tbody></table>'

    # 3. Video Quality (Resolution)
    res_data = conn.execute("SELECT height FROM MediaContent WHERE file_type_group='VIDEO'").fetchall()
    res_stats = {'4K+':0, '1080p':0, '720p':0, 'SD':0, 'Unknown':0}
    for r in res_data:
        h = r[0]
        if not h: res_stats['Unknown'] += 1
        elif h >= 2160: res_stats['4K+'] += 1
        elif h >= 1080: res_stats['1080p'] += 1
        elif h >= 720: res_stats['720p'] += 1
        else: res_stats['SD'] += 1
        
    res_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Resolution</th><th>Count</th></tr></thead><tbody>'
    for k, v in res_stats.items():
        if v > 0: res_html += f"<tr><td>{k}</td><td>{v:,}</td></tr>"
    res_html += '</tbody></table>'

    # 4. Image Quality (Megapixels)
    img_data = conn.execute("SELECT width, height FROM MediaContent WHERE file_type_group='IMAGE'").fetchall()
    img_stats = {'Pro (>20 MP)':0, 'High (12-20 MP)':0, 'Standard (2-12 MP)':0, 'Low (<2 MP)':0, 'Unknown':0}
    for w, h in img_data:
        if not w or not h:
            img_stats['Unknown'] += 1
            continue
        mp = (w * h) / 1_000_000
        if mp >= 20: img_stats['Pro (>20 MP)'] += 1
        elif mp >= 12: img_stats['High (12-20 MP)'] += 1
        elif mp >= 2: img_stats['Standard (2-12 MP)'] += 1
        else: img_stats['Low (<2 MP)'] += 1

    img_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Quality (Megapixels)</th><th>Count</th></tr></thead><tbody>'
    for k, v in img_stats.items():
        if v > 0: img_html += f"<tr><td>{k}</td><td>{v:,}</td></tr>"
    img_html += '</tbody></table>'

    # 5. Audio Quality (Bitrate)
    aud_data = conn.execute("SELECT bitrate FROM MediaContent WHERE file_type_group='AUDIO'").fetchall()
    aud_stats = {'High (>256k)':0, 'Standard (128k+)':0, 'Low (<128k)':0, 'Unknown':0}
    for r in aud_data:
        try:
            val = str(r[0]).lower()
            if not val or val == 'none':
                aud_stats['Unknown'] += 1
                continue
            # Remove units
            val = val.replace('bps','').replace('kb/s','000').replace('k','000').strip()
            # Handle float strings "320000.0"
            b = int(float(val))
            
            if b >= 256000: aud_stats['High (>256k)'] += 1
            elif b >= 128000: aud_stats['Standard (128k+)'] += 1
            else: aud_stats['Low (<128k)'] += 1
        except: aud_stats['Unknown'] += 1

    aud_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Quality</th><th>Count</th></tr></thead><tbody>'
    for k, v in aud_stats.items():
        if v > 0: aud_html += f"<tr><td>{k}</td><td>{v:,}</td></tr>"
    aud_html += '</tbody></table>'

    conn.close()
    
    full_html = f"""
    <div class="row g-4">
        <div class="col-md-6"><div class="report-card"><h4 class="report-title">Content Overview</h4>{type_html}</div></div>
        <div class="col-md-6"><div class="report-card"><h4 class="report-title">Top 20 Extensions (by Size)</h4>{ext_html}</div></div>
        <div class="col-md-4"><div class="report-card"><h4 class="report-title">Image Quality</h4>{img_html}</div></div>
        <div class="col-md-4"><div class="report-card"><h4 class="report-title">Video Resolution</h4>{res_html}</div></div>
        <div class="col-md-4"><div class="report-card"><h4 class="report-title">Audio Quality</h4>{aud_html}</div></div>
    </div>
    """
    return full_html

def run_server(config_manager):
    global DB_PATH, CONFIG
    CONFIG = config_manager
    DB_PATH = CONFIG.OUTPUT_DIR / 'metadata.sqlite'
    if not DB_PATH.exists(): return
    print("Starting Dashboard on http://127.0.0.1:5000")
    app.run(port=5000, debug=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Media Organizer Web Server")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Web Server")
        sys.exit(0)
    
    # Normal execution (usually called via main.py)
    # If run directly without main.py, it needs a config:
    run_server(ConfigManager())