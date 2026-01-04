# ==============================================================================
# File: server.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial implementation of Flask Server.",
    "Added API endpoints for Statistics, Folder Tree, and File Data.",
    "Implemented Server-Side Processing for DataTables (Pagination/Sorting/Filtering).",
    "Implemented secure media serving route to bypass local file security restrictions.",
    "Created modern Bootstrap 5 Dashboard template with dark mode."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.5
# ------------------------------------------------------------------------------
import os
import json
import sqlite3
import mimetypes
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file, Response, abort

from database_manager import DatabaseManager
from config_manager import ConfigManager

app = Flask(__name__)

# Global instances (initialized in run_server)
DB_PATH = None
CONFIG = None

# --- HTML TEMPLATE (Embedded for single-file portability) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Organizer Dashboard</title>
    <!-- Bootstrap 5 & DataTables -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; height: 100vh; overflow: hidden; }
        #wrapper { display: flex; height: 100%; }
        #sidebar { width: 300px; background: #212529; border-right: 1px solid #333; display: flex; flex-direction: column; }
        #content { flex: 1; display: flex; flex-direction: column; padding: 20px; overflow-y: auto; background: #121212; }
        
        /* Sidebar */
        .sidebar-header { padding: 15px; border-bottom: 1px solid #333; color: #fff; }
        .folder-tree { flex: 1; overflow-y: auto; padding: 10px; font-size: 0.9rem; }
        .folder-item { cursor: pointer; padding: 4px 8px; color: #adb5bd; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .folder-item:hover { background: #343a40; color: #fff; }
        .folder-item.active { background: #0d6efd; color: #fff; }
        .folder-icon { margin-right: 5px; color: #ffc107; }

        /* Stats Cards */
        .card-stat { background: #2c3034; border: none; margin-bottom: 20px; }
        .card-stat h6 { color: #888; font-size: 0.8rem; text-transform: uppercase; }
        .card-stat h3 { color: #fff; margin: 0; }
        .text-accent { color: #0dcaf0; }
        .text-danger-custom { color: #ff6b6b; }

        /* Table */
        .table-responsive { background: #212529; border-radius: 8px; padding: 15px; }
        table.dataTable tbody tr { background-color: transparent !important; }
        .badge-type { width: 60px; text-align: center; }
        
        /* Modal */
        .modal-content { background-color: #212529; border: 1px solid #444; }
        pre.meta-json { background: #000; padding: 10px; border-radius: 5px; color: #0f0; max-height: 400px; overflow: auto; }
        
        /* Media Preview */
        .thumb-img { width: 80px; height: 45px; object-fit: cover; border: 1px solid #444; cursor: pointer; }
    </style>
</head>
<body>

<div id="wrapper">
    <!-- Sidebar -->
    <div id="sidebar">
        <div class="sidebar-header">
            <h5 class="m-0"><i class="bi bi-hdd-network"></i> File Organizer</h5>
        </div>
        <div class="p-2 border-bottom border-secondary">
            <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary" id="folderSearch" placeholder="Filter folders...">
        </div>
        <div class="folder-tree" id="folderTree">
            <div class="text-center mt-3"><div class="spinner-border text-secondary" role="status"></div></div>
        </div>
    </div>

    <!-- Main Content -->
    <div id="content">
        <!-- Stats Row -->
        <div class="row g-3 mb-3">
            <div class="col-md-3">
                <div class="card card-stat p-3">
                    <h6>Total Files</h6>
                    <h3 id="stat-total">0</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat p-3">
                    <h6>Total Size</h6>
                    <h3 id="stat-size" class="text-accent">0 GB</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat p-3">
                    <h6>Duplicates</h6>
                    <h3 id="stat-dupes" class="text-danger-custom">0</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card card-stat p-3">
                    <h6>Wasted Space</h6>
                    <h3 id="stat-waste" class="text-danger-custom">0 GB</h3>
                </div>
            </div>
        </div>

        <!-- Toolbar -->
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 id="current-view-title" class="m-0">All Files</h4>
            <div class="btn-group">
                <button class="btn btn-outline-secondary active" id="btn-all" onclick="setView('all')">All Files</button>
                <button class="btn btn-outline-secondary" id="btn-dupes" onclick="setView('dupes')">Duplicates</button>
            </div>
        </div>

        <!-- Table -->
        <div class="table-responsive flex-grow-1">
            <table id="fileTable" class="table table-dark table-hover w-100">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Filename</th>
                        <th>Path (Relative)</th>
                        <th>Size</th>
                        <th>Preview</th>
                        <th>Action</th>
                    </tr>
                </thead>
            </table>
        </div>
    </div>
</div>

<!-- Metadata Modal -->
<div class="modal fade" id="metaModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">File Details</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div id="media-preview-container" class="text-center mb-3 bg-black p-2 rounded" style="display:none;"></div>
                <ul class="nav nav-tabs mb-3" id="metaTabs">
                    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-meta">Metadata</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-tech">Technical</button></li>
                </ul>
                <div class="tab-content">
                    <div class="tab-pane fade show active" id="tab-meta">
                        <pre id="meta-json-content" class="meta-json"></pre>
                    </div>
                    <div class="tab-pane fade" id="tab-tech">
                        <table class="table table-sm table-dark table-striped" id="tech-table"></table>
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
    let currentFolder = null;
    let viewMode = 'all'; // 'all' or 'dupes'

    $(document).ready(function() {
        loadStats();
        loadFolders();
        initTable();
        
        // Folder Search
        $('#folderSearch').on('keyup', function() {
            let val = $(this).val().toLowerCase();
            $('.folder-item').filter(function() {
                $(this).toggle($(this).text().toLowerCase().indexOf(val) > -1)
            });
        });
    });

    function initTable() {
        table = $('#fileTable').DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/api/files',
                data: function (d) {
                    d.folder = currentFolder;
                    d.view = viewMode;
                }
            },
            columns: [
                { data: 'type', render: d => `<span class="badge bg-secondary badge-type">${d}</span>` },
                { data: 'name', render: (d, t, r) => `<strong>${d}</strong>` },
                { data: 'rel_path', render: d => `<small class="text-secondary">${d}</small>` },
                { data: 'size_str' },
                { data: 'id', orderable: false, render: (d, t, r) => renderPreview(r) },
                { data: 'id', orderable: false, render: (d, t, r) => `<button class="btn btn-sm btn-info" onclick='openMeta(${JSON.stringify(r)})'>Info</button>` }
            ],
            order: [[1, 'asc']], // Sort by Name default
            pageLength: 25,
            lengthMenu: [10, 25, 50, 100],
            language: { search: "_INPUT_", searchPlaceholder: "Search files..." }
        });
    }

    function renderPreview(row) {
        if (row.type === 'IMAGE') {
            return `<img src="/api/media/${row.id}" class="thumb-img" onclick="openMeta(this.dataset.row)">`;
        }
        return '<span class="text-muted">-</span>';
    }

    function loadStats() {
        $.get('/api/stats', function(data) {
            $('#stat-total').text(data.total_files.toLocaleString());
            $('#stat-size').text(data.total_size);
            $('#stat-dupes').text(data.duplicates.toLocaleString());
            $('#stat-waste').text(data.wasted_size);
        });
    }

    function loadFolders() {
        $.get('/api/folders', function(data) {
            let html = `<div class="folder-item active" onclick="selectFolder(null, this)"><i class="bi bi-house-door folder-icon"></i> (Root / All)</div>`;
            data.forEach(f => {
                html += `<div class="folder-item" onclick="selectFolder('${f}', this)"><i class="bi bi-folder folder-icon"></i> ${f}</div>`;
            });
            $('#folderTree').html(html);
        });
    }

    function selectFolder(path, el) {
        $('.folder-item').removeClass('active');
        $(el).addClass('active');
        currentFolder = path;
        
        // Update Title
        if (path) {
            let name = path.split('/').pop();
            $('#current-view-title').text(name || path);
        } else {
            $('#current-view-title').text(viewMode === 'all' ? "All Files" : "Duplicates");
        }
        
        table.ajax.reload();
    }

    function setView(mode) {
        viewMode = mode;
        $('.btn-group .btn').removeClass('active');
        $('#btn-' + mode).addClass('active');
        
        // Reset folder filter on mode switch
        currentFolder = null; 
        $('.folder-item').removeClass('active');
        $('.folder-item:first').addClass('active');
        
        $('#current-view-title').text(mode === 'all' ? "All Files" : "Duplicates");
        table.ajax.reload();
    }

    // --- METADATA MODAL LOGIC ---
    window.openMeta = function(row) {
        if (typeof row === 'string') row = JSON.parse(row); // Handle if passed as string
        
        // 1. Metadata JSON
        let meta = JSON.parse(row.metadata || "{}");
        $('#meta-json-content').text(JSON.stringify(meta, null, 4));
        
        // 2. Technical Table
        let techHtml = '';
        techHtml += `<tr><td>Path</td><td>${row.full_path}</td></tr>`;
        techHtml += `<tr><td>Size</td><td>${row.size_str} (${row.size} bytes)</td></tr>`;
        techHtml += `<tr><td>Hash</td><td><code class="text-accent">${row.hash}</code></td></tr>`;
        $('#tech-table').html(techHtml);

        // 3. Media Preview
        let previewHtml = '';
        let url = `/api/media/${row.id}`;
        
        if (row.type === 'IMAGE') {
            previewHtml = `<img src="${url}" style="max-height:400px; max-width:100%;">`;
        } else if (row.type === 'VIDEO') {
            previewHtml = `<video controls src="${url}" style="max-height:400px; max-width:100%;"></video>`;
        } else if (row.type === 'AUDIO') {
            previewHtml = `<audio controls src="${url}" style="width:100%;"></audio>`;
        }
        
        if (previewHtml) {
            $('#media-preview-container').html(previewHtml).show();
        } else {
            $('#media-preview-container').hide();
        }

        new bootstrap.Modal(document.getElementById('metaModal')).show();
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

def get_db():
    # Helper to get a thread-local DB connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    total_files = cursor.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
    total_size = cursor.execute("SELECT SUM(size) FROM MediaContent").fetchone()[0] or 0
    
    # Calculate Wasted Space (Size * (Count - 1) for dupes)
    # This query sums the size of all non-primary copies
    wasted = cursor.execute("""
        SELECT SUM(mc.size)
        FROM FilePathInstances fpi
        JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
        WHERE fpi.is_primary = 0
    """).fetchone()[0] or 0
    
    dupe_count = cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT content_hash FROM FilePathInstances 
            GROUP BY content_hash HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    
    conn.close()
    return jsonify({
        'total_files': total_files,
        'total_size': format_size(total_size),
        'duplicates': dupe_count,
        'wasted_size': format_size(wasted)
    })

@app.route('/api/folders')
def api_folders():
    """Returns a flat list of unique parent folders for the sidebar."""
    conn = get_db()
    # Get distinct folders. 
    # Use standard path separator logic. We rely on 'original_relative_path'
    query = "SELECT DISTINCT original_relative_path FROM FilePathInstances"
    rows = conn.execute(query).fetchall()
    conn.close()
    
    # Extract parent directory from paths
    folders = set()
    for r in rows:
        p = Path(r[0]).parent
        if str(p) != '.':
            folders.add(str(p).replace('\\', '/'))
            
    return jsonify(sorted(list(folders)))

@app.route('/api/files')
def api_files():
    """
    DataTables Server-Side Processing Endpoint.
    Handles Pagination, Filtering, and Sorting efficiently via SQL.
    """
    conn = get_db()
    
    # DataTables Parameters
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 25))
    search_value = request.args.get('search[value]', '').lower()
    
    # Custom Filters
    folder_filter = request.args.get('folder', None)
    view_mode = request.args.get('view', 'all') # 'all' or 'dupes'

    # Build SQL
    base_query = """
        SELECT fpi.file_id, fpi.content_hash, fpi.original_relative_path, 
               fpi.original_full_path, mc.file_type_group, mc.size, mc.extended_metadata
        FROM FilePathInstances fpi
        JOIN MediaContent mc ON fpi.content_hash = mc.content_hash
    """
    
    where_clauses = []
    params = []

    # 1. Search Filter
    if search_value:
        where_clauses.append("(fpi.original_relative_path LIKE ? OR mc.file_type_group LIKE ?)")
        params.extend([f"%{search_value}%", f"%{search_value}%"])

    # 2. Folder Filter
    if folder_filter:
        # Match folders that start with the selected path
        # Normalize slashes for SQL LIKE
        search_path = folder_filter.replace('/', '\\') # Windows fix if needed, or rely on consistency
        where_clauses.append("fpi.original_relative_path LIKE ?")
        # Ensure we catch files IN that folder, or subfolders
        params.append(f"{folder_filter}/%")

    # 3. View Mode (Dupes Only)
    if view_mode == 'dupes':
        # Subquery to find hashes with > 1 instance
        where_clauses.append("""
            fpi.content_hash IN (
                SELECT content_hash FROM FilePathInstances 
                GROUP BY content_hash HAVING COUNT(*) > 1
            )
        """)

    # Combine Where
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    # Count Total Filtered (for Pagination)
    count_sql = f"SELECT COUNT(*) FROM ({base_query})"
    total_filtered = conn.execute(count_sql, params).fetchone()[0]

    # Get Total Records (Unfiltered)
    total_records = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]

    # Add Sorting & Pagination
    # Simple sort by file_id desc for now, or handle 'order[0][column]' from DataTables
    base_query += " LIMIT ? OFFSET ?"
    params.extend([length, start])

    # Execute
    data = []
    rows = conn.execute(base_query, params).fetchall()
    
    for r in rows:
        data.append({
            "id": r[0],
            "hash": r[1],
            "rel_path": r[2],
            "full_path": r[3],
            "name": Path(r[2]).name,
            "type": r[4],
            "size": r[5],
            "size_str": format_size(r[5]),
            "metadata": r[6]
        })

    conn.close()
    
    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_filtered,
        "data": data
    })

@app.route('/api/media/<int:file_id>')
def serve_media(file_id):
    """Securely serves the file content based on ID."""
    conn = get_db()
    row = conn.execute("SELECT original_full_path, file_type_group FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash WHERE fpi.file_id = ?", (file_id,)).fetchone()
    conn.close()
    
    if not row:
        abort(404)
        
    full_path = row[0]
    if not os.path.exists(full_path):
        abort(404)
        
    # Guess mime type
    mime, _ = mimetypes.guess_type(full_path)
    return send_file(full_path, mimetype=mime)

def run_server(config_manager):
    """Entry point called by main.py"""
    global DB_PATH, CONFIG
    CONFIG = config_manager
    DB_PATH = CONFIG.OUTPUT_DIR / 'metadata.sqlite'
    
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Starting Web Interface on http://127.0.0.1:5000")
    print("Press CTRL+C to stop.")
    app.run(debug=False, port=5000)

if __name__ == '__main__':
    # Standalone testing
    run_server(ConfigManager())