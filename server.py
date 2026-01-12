# ==============================================================================
# File: server.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 16
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
    "CLI: Added --version and --help support.",
    "FIX: Implemented special SQL logic for browsing files with no extension ('no_ext').",
    "UX: Clarified Duplicate Table vs Stats distinction.",
    "FEATURE: Added 'History' tab to File Inspector for viewing Original Name and Source Copies.",
    "UX: Added Database Name indicator in Navbar to distinguish Source Scan vs Clean Export.",
    "FEATURE: Added 'Quality' Tab to Sidebar for browsing by Resolution/Bitrate/Megapixels.",
    "FEATURE: Added Text File Preview (.txt, .md, .csv, etc) in File Inspector.",
    "SEARCH: Enhanced search to index 'extended_metadata', enabling search by Original Filename, Camera Model, etc.",
    "FIX: Enforced file_type_group constraints in Quality Filters (prevents Images appearing in Video lists).",
    "FEATURE: Added PDF Preview support via Embed.",
    "UX: Added browser compatibility warning for non-web video formats (MKV, AVI).",
    "PERFORMANCE: Replaced slow Python NORM_PATH function with native SQLite REPLACE() for massive speedup.",
    "FIX: Ensured metadata API returns valid JSON string '{}' even if DB is NULL to prevent JS display errors.",
    "REFACTOR: Separated HTML template into 'templates/dashboard.html' (Standard Flask MVC).",
    "FEATURE: Added On-the-Fly RAW Image Conversion (NEF/CR2 -> JPEG) via rawpy.",
    "FEATURE: Added .DOCX Text Extraction for browser preview.",
    "FEATURE: Added On-the-Fly HEIC Image Conversion (HEIC -> JPEG) via Pillow-HEIF.",
    "NETWORKING: Changed host to '0.0.0.0' to allow access from other computers on the LAN.",
    "FIX: Added Cache-Busting (?t=timestamp) to image previews to force browser to load High-Res RAW conversions.",
    "DEBUG: Added console logging for RAW conversion attempts.",
    "FEATURE: Added On-the-Fly Video Transcoding (MKV/AVI/WMV -> MP4) using FFmpeg streaming.",
    "FEATURE: Configurable FFmpeg binary path and arguments via organizer_config.json.",
    "FIX: Enforced '-pix_fmt yuv420p' and '-ac 2' in FFmpeg to ensure browser compatibility.",
    "FIX: Added robust path detection for FFmpeg to handle Folder paths vs Binary paths (fixes WinError 5).",
    "PERFORMANCE: Added '-tune zerolatency' and '-g 60' to FFmpeg to fix browser playback timeouts.",
    "DEBUG: Added stderr capture to FFmpeg stream to diagnose transcoding failures.",
    "COMPATIBILITY: Forced '-profile:v baseline' and '-reset_timestamps 1' to fix Gray Screen/0:00 duration issues.",
    "CRITICAL FIX: Set subprocess `bufsize=0` to prevent Python from holding video headers, fixing the Gray Screen hanging issue.",
    "DEBUG: Implemented threaded stderr reader to print FFmpeg logs to console in real-time.",
    "FIX: Resolved absolute path for FFmpeg input to prevent 'No such file' errors on nested directories.",
    "DEBUG: Simplified stderr handling to write directly to sys.stderr for immediate feedback.",
    "PERFORMANCE: Removed -analyzeduration/-probesize flags which were causing startup hangs on large files.",
    "CRITICAL FIX: Set `cwd` in subprocess to FFmpeg binary directory to ensure DLLs are found.",
    "FEATURE: Added `ffprobe` detection and HEVC/H.265 detection to force transcoding for 'Audio Only' MP4s.",
    "COMPATIBILITY: Added .mpg, .mpeg, and .mpe to mandatory transcoding list.",
    "FEATURE: Added /api/map endpoint to serve GPS coordinates from metadata.",
    "FEATURE: Added /api/update_notes endpoint to write User Notes into JSON metadata.",
    "FEATURE: Added /api/export_db endpoint to download the SQLite database.",
    "PERFORMANCE: Implemented Auto-Detection for NVIDIA GPU (h264_nvenc).",
    "PERFORMANCE: Added adaptive transcoding logic to swap 'libx264' with 'h264_nvenc' and adjust flags (crf->cq, preset->p1) automatically.",
    "UX: Added automatic LAN IP detection to print the actual network URL on startup.",
    "FEATURE: Added On-the-Fly TIFF to JPEG conversion to allow .tif/.tiff previews in browser.",
    "FEATURE: Added /api/visual_dupes endpoint to serve grouped Perceptual Hash matches.",
    "FIX: Added .tif and .tiff to conversion list (handled by Pillow) to fix broken previews in browser.",
    "CONFIG: Enabled TEMPLATES_AUTO_RELOAD to prevent caching of dashboard UI updates."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.16.70
# ------------------------------------------------------------------------------
import os
import json
import sqlite3
import mimetypes
import argparse
import sys
import io
import subprocess
import shutil
import threading
import socket
from pathlib import Path
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, abort, Response, stream_with_context

# Import Pillow for Image Conversion
try:
    from PIL import Image
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError: pass
except ImportError:
    Image = None

# Import rawpy for high-quality RAW conversion
try:
    import rawpy
except ImportError:
    rawpy = None

# Import Docx for Word Preview
try:
    import docx
except ImportError:
    docx = None

from database_manager import DatabaseManager
from config_manager import ConfigManager

template_dir = Path(__file__).parent / 'templates'
if not template_dir.exists():
    print(f"WARNING: 'templates' directory not found at {template_dir}")

app = Flask(__name__, template_folder=str(template_dir))

# CRITICAL FIX: Ensure UI updates are reflected immediately
app.config['TEMPLATES_AUTO_RELOAD'] = True

DB_PATH = None
CONFIG = None
FFMPEG_BINARY = None
FFPROBE_BINARY = None
HW_ACCEL_TYPE = "none" # 'none' or 'nvidia'

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

def get_local_ip():
    """Attempts to determine the primary LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_hardware_acceleration(binary, cwd):
    """Checks if NVENC is available in the FFmpeg build."""
    try:
        # Run ffmpeg -encoders and grep for nvenc
        cmd = [binary, '-hide_banner', '-encoders']
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if 'h264_nvenc' in result.stdout:
            return 'nvidia'
    except Exception as e:
        print(f"HW Check Failed: {e}")
    return 'none'

def transcode_video_stream(path_str):
    """
    Generates a stream of bytes from FFmpeg, transcoding the input 
    to fragmented MP4 (H.264/AAC) for browser playback.
    Automatically adapts to NVIDIA GPU if available.
    """
    if not FFMPEG_BINARY:
        return 
    
    # 1. Resolve Path
    abs_path = Path(path_str).resolve()
    if not abs_path.exists():
        print(f"[FFmpeg] ERROR: Input file not found: {abs_path}")
        return

    settings = CONFIG.FFMPEG_SETTINGS
    
    # 2. Build Command
    cmd = [FFMPEG_BINARY, '-y']
    cmd.extend(['-i', str(abs_path)])
    
    # --- VIDEO CODEC LOGIC ---
    if HW_ACCEL_TYPE == 'nvidia':
        # NVIDIA NVENC SETTINGS
        # Use h264_nvenc
        cmd.extend(['-c:v', 'h264_nvenc'])
        
        # Preset: p1 (fastest) to p7 (slowest). Default to p1 for streaming speed.
        cmd.extend(['-preset', 'p1'])
        
        # Quality: NVENC uses -cq (0-51) instead of -crf.
        # Map user's CRF pref (default 23) to CQ.
        crf = settings.get('crf', '23')
        cmd.extend(['-rc', 'vbr', '-cq', crf])
        
        # Zero Latency is often implicit with p1/low-latency tuning, 
        # but we add specific flags if needed. NVENC usually streams well by default.
        # -tune zerolatency is NOT a standard nvenc flag, we skip it.
    else:
        # CPU SOFTWARE SETTINGS (libx264)
        cmd.extend(['-c:v', settings.get('video_codec', 'libx264')])
        
        if settings.get('preset'):
            cmd.extend(['-preset', settings.get('preset')])
        
        if settings.get('crf'):
            cmd.extend(['-crf', settings.get('crf')])
            
        cmd.extend(['-tune', 'zerolatency'])

    # --- COMMON SETTINGS ---
    
    # WEB COMPATIBILITY: Force standard pixel format and baseline profile
    cmd.extend(['-pix_fmt', 'yuv420p'])
    # NVENC supports -profile:v, but typically 'main' or 'high'. 'baseline' is often safe.
    cmd.extend(['-profile:v', 'baseline'])

    # Audio
    cmd.extend(['-c:a', settings.get('audio_codec', 'aac'), '-ac', '2', '-ar', '44100'])
    
    # User Extras
    if settings.get('extra_args'):
        cmd.extend(settings.get('extra_args'))

    # Container (Fragmented MP4)
    cmd.extend([
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+default_base_moof', 
        '-reset_timestamps', '1',
        '-g', '30', 
        'pipe:1'
    ])
    
    print(f"[FFmpeg] Command: {' '.join(cmd)}")
    
    # 3. Execution
    cwd = os.path.dirname(FFMPEG_BINARY)
    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=sys.stderr, 
        bufsize=0,
        cwd=cwd 
    )
    
    try:
        while True:
            data = proc.stdout.read(32768)
            if not data:
                break
            yield data
            
            if proc.poll() is not None and proc.returncode != 0:
                print(f"[FFmpeg] Process exited with error: {proc.returncode}")
                break
                
    except GeneratorExit:
        proc.terminate()
    except Exception as e:
        print(f"[FFmpeg] Exception: {e}")
        proc.kill()
    finally:
        if proc.poll() is None:
            proc.terminate()

def needs_transcoding(path_obj):
    """
    Determines if a video needs transcoding based on extension and codec.
    """
    ext = path_obj.suffix.lower()
    
    # 1. Always transcode unsupported containers
    if ext in ['.mkv', '.avi', '.wmv', '.flv', '.vob', '.mts', '.m2ts', '.ts', '.3gp', '.mpg', '.mpeg', '.mpe']:
        return True
    
    # 2. For MP4/MOV, check if it's HEVC (H.265)
    if ext in ['.mp4', '.mov'] and FFPROBE_BINARY:
        try:
            cmd = [
                FFPROBE_BINARY, 
                '-v', 'error', 
                '-select_streams', 'v:0', 
                '-show_entries', 'stream=codec_name', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                str(path_obj.resolve())
            ]
            cwd = os.path.dirname(FFPROBE_BINARY)
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
            codec = result.stdout.strip().lower()
            
            if codec and codec not in ['h264', 'av1', 'vp8', 'vp9']:
                print(f"[Media] Detected non-web codec '{codec}' in {path_obj.name}. Transcoding enabled.")
                return True
        except Exception as e:
            print(f"[Media] FFprobe check failed: {e}")
            
    return False

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
    size = conn.execute("SELECT SUM(size) FROM MediaContent").fetchone()[0] or 0
    wasted = conn.execute("SELECT SUM(mc.size) FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash=mc.content_hash WHERE fpi.is_primary=0").fetchone()[0] or 0
    dupes = conn.execute("SELECT COUNT(*) FROM FilePathInstances WHERE is_primary=0").fetchone()[0]
    conn.close()
    
    db_name = Path(DB_PATH).name
    label = "Source Index"
    if "clean" in db_name.lower(): label = "Clean Export"
    
    return jsonify({
        'total_files': total, 'total_size': format_size(size), 
        'duplicates': dupes, 'wasted_size': format_size(wasted),
        'db_label': label
    })

@app.route('/api/tree')
def api_tree():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT REPLACE(original_relative_path, '\\', '/') FROM FilePathInstances").fetchall()
    conn.close()
    paths = set()
    for r in rows:
        p = Path(r[0]).parent
        if str(p) != '.': paths.add(str(p))
    
    tree = {}
    for path in paths:
        clean = str(path).replace('\\', '/')
        parts = clean.split('/')
        curr = tree
        for part in parts:
            if not part: continue
            curr = curr.setdefault(part, {})
            
    return jsonify(tree)

@app.route('/api/types')
def api_types():
    conn = get_db()
    rows = conn.execute("SELECT mc.file_type_group, REPLACE(fpi.original_relative_path, '\\', '/') FROM MediaContent mc JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash").fetchall()
    conn.close()
    data = {}
    for g, p in rows:
        ext = Path(p).suffix.lower() or "no_ext"
        if g not in data: data[g] = {}
        data[g][ext] = data[g].get(ext, 0) + 1
    return jsonify(data)

@app.route('/api/quality')
def api_quality():
    conn = get_db()
    # Video
    res_data = conn.execute("SELECT height FROM MediaContent WHERE file_type_group='VIDEO'").fetchall()
    res_stats = {'4K+':0, '1080p':0, '720p':0, 'SD':0}
    for r in res_data:
        h = r[0]
        if not h: continue
        if h >= 2160: res_stats['4K+'] += 1
        elif h >= 1080: res_stats['1080p'] += 1
        elif h >= 720: res_stats['720p'] += 1
        else: res_stats['SD'] += 1
    # Image
    img_data = conn.execute("SELECT width, height FROM MediaContent WHERE file_type_group='IMAGE'").fetchall()
    img_stats = {'Pro (>20 MP)':0, 'High (12-20 MP)':0, 'Standard (2-12 MP)':0, 'Low (<2 MP)':0}
    for w, h in img_data:
        if not w or not h: continue
        mp = (w * h) / 1_000_000
        if mp >= 20: img_stats['Pro (>20 MP)'] += 1
        elif mp >= 12: img_stats['High (12-20 MP)'] += 1
        elif mp >= 2: img_stats['Standard (2-12 MP)'] += 1
        else: img_stats['Low (<2 MP)'] += 1
    # Audio
    aud_data = conn.execute("SELECT bitrate FROM MediaContent WHERE file_type_group='AUDIO'").fetchall()
    aud_stats = {'High (>256k)':0, 'Standard (128k+)':0, 'Low (<128k)':0}
    for r in aud_data:
        try:
            val = str(r[0]).lower()
            if not val or val == 'none': continue
            val = val.replace('bps','').replace('kb/s','000').replace('k','000').strip()
            b = int(float(val))
            if b >= 256000: aud_stats['High (>256k)'] += 1
            elif b >= 128000: aud_stats['Standard (128k+)'] += 1
            else: aud_stats['Low (<128k)'] += 1
        except: pass
    conn.close()
    return jsonify({'video': res_stats, 'image': img_stats, 'audio': aud_stats})

@app.route('/api/map')
def api_map():
    """Returns JSON of files containing GPS metadata."""
    conn = get_db()
    query = """
    SELECT fpi.file_id, mc.extended_metadata, fpi.original_relative_path 
    FROM MediaContent mc 
    JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash 
    WHERE fpi.is_primary = 1 
      AND mc.file_type_group = 'IMAGE'
      AND mc.extended_metadata LIKE '%GPS%'
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    
    markers = []
    for r in rows:
        fid, meta_json, path = r
        try:
            if not meta_json: continue
            meta = json.loads(meta_json)
            lat = meta.get('GPS_Latitude')
            lng = meta.get('GPS_Longitude')
            if lat and lng:
                markers.append({
                    "id": fid,
                    "lat": float(lat),
                    "lng": float(lng),
                    "name": Path(path).name
                })
        except: continue
    return jsonify(markers)

@app.route('/api/visual_dupes')
def api_visual_dupes():
    """Returns grouped visual duplicates (Same Phash)."""
    conn = get_db()
    # 1. Get Hash Groups
    query = """
    SELECT mc.perceptual_hash, mc.content_hash, mc.size, fpi.file_id, fpi.original_relative_path, mc.file_type_group 
    FROM MediaContent mc
    JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash
    WHERE mc.perceptual_hash IN (
        SELECT perceptual_hash FROM MediaContent 
        WHERE perceptual_hash IS NOT NULL AND perceptual_hash != 'UNKNOWN'
        GROUP BY perceptual_hash 
        HAVING COUNT(*) > 1
    ) AND fpi.is_primary = 1
    ORDER BY mc.perceptual_hash
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    
    # 2. Group by Phash
    groups = defaultdict(list)
    for r in rows:
        phash = r[0]
        groups[phash].append({
            "hash": r[1],
            "size": format_size(r[2]),
            "id": r[3],
            "name": Path(r[4]).name,
            "path": r[4],
            "type": r[5]
        })
        
    return jsonify([{"phash": k, "items": v} for k, v in groups.items()])

@app.route('/api/update_notes', methods=['POST'])
def api_update_notes():
    """Updates the 'User_Notes' field in the extended_metadata JSON blob."""
    data = request.json
    file_id = data.get('id')
    notes = data.get('notes', '')
    
    conn = get_db()
    try:
        row = conn.execute("SELECT mc.content_hash, mc.extended_metadata FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash WHERE fpi.file_id = ?", (file_id,)).fetchone()
        
        if not row:
            return jsonify({"success": False, "error": "File ID not found"}), 404
            
        c_hash, meta_str = row
        try:
            meta = json.loads(meta_str) if meta_str else {}
        except:
            meta = {}
            
        meta['User_Notes'] = notes
        new_meta_str = json.dumps(meta, indent=4)
        
        conn.execute("UPDATE MediaContent SET extended_metadata = ? WHERE content_hash = ?", (new_meta_str, c_hash))
        conn.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/export_db')
def api_export_db():
    """Downloads the current database file."""
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True)
    abort(404)

@app.route('/api/files')
def api_files():
    conn = get_db()
    args = request.args
    draw = int(args.get('draw', 1))
    start = int(args.get('start', 0))
    length = int(args.get('length', 25))
    search = args.get('search[value]', '').lower()
    col_idx = args.get('order[0][column]')
    col_dir = args.get('order[0][dir]', 'asc')
    col_map = {0:'mc.file_type_group', 2:'fpi.original_relative_path', 4:'mc.size', 5:'mc.date_best'}
    order_clause = f"ORDER BY {col_map.get(int(col_idx), 'fpi.original_relative_path')} {col_dir}" if col_idx else ""
    f_type = args.get('f_type', 'all')
    f_val = args.get('f_val', '')
    min_size = args.get('min_size')
    year = args.get('year')

    base = """SELECT fpi.file_id, fpi.content_hash, fpi.original_relative_path, mc.file_type_group, mc.size, mc.date_best 
              FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash"""
    where = []
    params = []
    if search:
        where.append("(REPLACE(fpi.original_relative_path, '\\', '/') LIKE ? OR mc.file_type_group LIKE ? OR mc.extended_metadata LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if f_type == 'folder' and f_val:
        clean_val = f_val.replace('\\', '/')
        param_val = f"{clean_val}/%" 
        where.append("REPLACE(fpi.original_relative_path, '\\', '/') LIKE ?")
        params.append(param_val)
    elif f_type == 'root':
        where.append("instr(REPLACE(fpi.original_relative_path, '\\', '/'), '/') = 0")
    elif f_type == 'unique':
        where.append("fpi.is_primary = 1")
    elif f_type == 'dupes':
        where.append("fpi.content_hash IN (SELECT content_hash FROM FilePathInstances GROUP BY content_hash HAVING COUNT(*) > 1)")
    elif f_type == 'ext':
        if f_val == 'no_ext':
            where.append("REPLACE(fpi.original_relative_path, '\\', '/') NOT LIKE '%.%'")
        else:
            where.append("REPLACE(fpi.original_relative_path, '\\', '/') LIKE ?")
            params.append(f"%{f_val}")
    elif f_type == 'qual':
        cat, criteria = f_val.split(':', 1)
        if cat == 'vid':
            where.append("mc.file_type_group = 'VIDEO'")
            if '4K' in criteria: where.append("mc.height >= 2160")
            elif '1080' in criteria: where.append("mc.height >= 1080 AND mc.height < 2160")
            elif '720' in criteria: where.append("mc.height >= 720 AND mc.height < 1080")
            elif 'SD' in criteria: where.append("mc.height < 720")
        elif cat == 'img':
            where.append("mc.file_type_group = 'IMAGE'")
            if 'Pro' in criteria: where.append("(mc.width * mc.height) >= 20000000")
            elif 'High' in criteria: where.append("(mc.width * mc.height) >= 12000000 AND (mc.width * mc.height) < 20000000")
            elif 'Standard' in criteria: where.append("(mc.width * mc.height) >= 2000000 AND (mc.width * mc.height) < 12000000")
            elif 'Low' in criteria: where.append("(mc.width * mc.height) < 2000000")
        elif cat == 'aud':
            where.append("mc.file_type_group = 'AUDIO'")
            if 'High' in criteria: where.append("mc.bitrate >= 256000")
            elif 'Standard' in criteria: where.append("mc.bitrate >= 128000 AND mc.bitrate < 256000")
            elif 'Low' in criteria: where.append("mc.bitrate < 128000")

    if min_size:
        where.append("mc.size >= ?")
        params.append(min_size)
    if year:
        where.append("mc.date_best LIKE ?")
        params.append(f"{year}%")

    if where: base += " WHERE " + " AND ".join(where)
    
    try:
        total = conn.execute("SELECT COUNT(*) FROM FilePathInstances").fetchone()[0]
        filtered = conn.execute(f"SELECT COUNT(*) FROM ({base})", params).fetchone()[0]
        sql = f"{base} {order_clause} LIMIT ? OFFSET ?"
        params.extend([length, start])
        rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        print(f"SQL Error: {e}")
        rows = []
        filtered = 0
        total = 0
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
    meta_val = row[3] if row and row[3] else "{}"
    if row:
        return jsonify({"id": row[0], "name": Path(row[1]).name, "type": row[2], "metadata": meta_val})
    else:
        return jsonify({})

@app.route('/api/content/<int:id>')
def api_content(id):
    conn = get_db()
    row = conn.execute("SELECT original_full_path FROM FilePathInstances WHERE file_id = ?", (id,)).fetchone()
    conn.close()
    if not row or not os.path.exists(row[0]): return "File not found.", 404
    path = Path(row[0])
    ext = path.suffix.lower()
    try:
        if ext in ['.txt', '.md', '.csv', '.json', '.xml', '.log', '.py', '.js', '.html', '.css', '.sh', '.bat', '.ini', '.rtf']:
            with open(path, 'r', encoding='utf-8', errors='replace') as f: return f.read()
        elif ext == '.docx':
            if docx is None: return "python-docx library not installed."
            doc = docx.Document(path)
            return '\n'.join([p.text for p in doc.paragraphs])
        return "Preview not supported."
    except Exception as e: return f"Error: {e}", 500

@app.route('/api/media/<int:id>')
def serve(id):
    conn = get_db()
    row = conn.execute("SELECT original_full_path FROM FilePathInstances WHERE file_id=?", (id,)).fetchone()
    conn.close()
    if row and os.path.exists(row[0]):
        path = Path(row[0])
        ext = path.suffix.lower()
        
        # RAW Conversion
        if ext in ['.cr2', '.nef', '.arw', '.dng', '.orf', '.heic', '.heif', '.tif', '.tiff']:
            print(f"[Media] Processing {ext} file: {path.name}")
            
            # 1. Try Rawpy (High Quality) for RAWs
            if rawpy and ext not in ['.heic', '.heif', '.tif', '.tiff']:
                try:
                    with rawpy.imread(str(path)) as raw:
                        rgb = raw.postprocess(use_camera_wb=True)
                    if Image:
                        img = Image.fromarray(rgb)
                        img_io = io.BytesIO()
                        img.save(img_io, 'JPEG', quality=85)
                        img_io.seek(0)
                        print(f"[Rawpy] Success.")
                        return send_file(img_io, mimetype='image/jpeg')
                except Exception as e:
                    print(f"[Rawpy] Failed: {e}")

            # 2. Try Pillow (Thumbnail or HEIC or TIFF)
            if Image:
                try:
                    img = Image.open(path)
                    if img.mode not in ('RGB', 'L'): img = img.convert('RGB')
                    img_io = io.BytesIO()
                    img.save(img_io, 'JPEG', quality=85)
                    img_io.seek(0)
                    print(f"[Pillow] Success.")
                    return send_file(img_io, mimetype='image/jpeg')
                except Exception as e:
                     print(f"[Pillow] Failed: {e}")
        
        # On-the-Fly Video Transcoding Check
        if FFMPEG_BINARY and needs_transcoding(path):
            print(f"[Media] Transcoding {ext} video: {path.name}")
            return Response(stream_with_context(transcode_video_stream(path)), mimetype='video/mp4')

        mime, _ = mimetypes.guess_type(row[0])
        return send_file(row[0], mimetype=mime)
    abort(404)

@app.route('/api/report')
def api_report():
    conn = get_db()
    type_data = conn.execute("SELECT mc.file_type_group, COUNT(*), SUM(mc.size) FROM MediaContent mc JOIN FilePathInstances fpi ON mc.content_hash = fpi.content_hash GROUP BY mc.file_type_group").fetchall()
    type_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Category</th><th>Total Files</th><th>Total Size</th></tr></thead><tbody>'
    for grp, count, size in type_data:
        type_html += f"<tr><td>{grp}</td><td>{count:,}</td><td>{format_size(size)}</td></tr>"
    type_html += '</tbody></table>'

    ext_data = conn.execute("SELECT REPLACE(fpi.original_relative_path, '\\', '/'), mc.size FROM FilePathInstances fpi JOIN MediaContent mc ON fpi.content_hash = mc.content_hash").fetchall()
    ext_stats = defaultdict(lambda: {'count': 0, 'size': 0})
    for p, s in ext_data:
        ext = Path(p).suffix.lower() or "No Ext"
        ext_stats[ext]['count'] += 1
        ext_stats[ext]['size'] += s
    ext_html = '<table class="table table-dark table-sm table-striped report-table"><thead><tr><th>Extension</th><th>Count</th><th>Size</th></tr></thead><tbody>'
    for ext, stats in sorted(ext_stats.items(), key=lambda x: x[1]['size'], reverse=True)[:20]:
        ext_html += f"<tr><td>{ext}</td><td>{stats['count']:,}</td><td>{format_size(stats['size'])}</td></tr>"
    ext_html += '</tbody></table>'

    res_data = conn.execute("SELECT height FROM MediaContent WHERE file_type_group='VIDEO'").fetchall()
    res_stats = {'4K+':0, '1080p':0, '720p':0, 'SD':0}
    for r in res_data:
        h = r[0]
        if not h: continue
        if h >= 2160: res_stats['4K+'] += 1
        elif h >= 1080: res_stats['1080p'] += 1
        elif h >= 720: res_stats['720p'] += 1
        else: res_stats['SD'] += 1
    res_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Resolution</th><th>Count</th></tr></thead><tbody>'
    for k, v in res_stats.items():
        if v > 0: res_html += f"<tr><td>{k}</td><td>{v:,}</td></tr>"
    res_html += '</tbody></table>'

    img_data = conn.execute("SELECT width, height FROM MediaContent WHERE file_type_group='IMAGE'").fetchall()
    img_stats = {'Pro (>20 MP)':0, 'High (12-20 MP)':0, 'Standard (2-12 MP)':0, 'Low (<2 MP)':0}
    for w, h in img_data:
        if not w or not h: continue
        mp = (w * h) / 1_000_000
        if mp >= 20: img_stats['Pro (>20 MP)'] += 1
        elif mp >= 12: img_stats['High (12-20 MP)'] += 1
        elif mp >= 2: img_stats['Standard (2-12 MP)'] += 1
        else: img_stats['Low (<2 MP)'] += 1
    img_html = '<table class="table table-dark table-striped report-table"><thead><tr><th>Quality (Megapixels)</th><th>Count</th></tr></thead><tbody>'
    for k, v in img_stats.items():
        if v > 0: img_html += f"<tr><td>{k}</td><td>{v:,}</td></tr>"
    img_html += '</tbody></table>'

    aud_data = conn.execute("SELECT bitrate FROM MediaContent WHERE file_type_group='AUDIO'").fetchall()
    aud_stats = {'High (>256k)':0, 'Standard (128k+)':0, 'Low (<128k)':0}
    for r in aud_data:
        try:
            val = str(r[0]).lower()
            if not val or val == 'none': continue
            val = val.replace('bps','').replace('kb/s','000').replace('k','000').strip()
            b = int(float(val))
            if b >= 256000: aud_stats['High (>256k)'] += 1
            elif b >= 128000: aud_stats['Standard (128k+)'] += 1
            else: aud_stats['Low (<128k)'] += 1
        except: pass
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
    global DB_PATH, CONFIG, FFMPEG_BINARY, FFPROBE_BINARY, HW_ACCEL_TYPE
    CONFIG = config_manager
    if DB_PATH is None:
        DB_PATH = CONFIG.OUTPUT_DIR / 'metadata.sqlite'
    if not Path(DB_PATH).exists(): 
        print(f"Error: Database not found at {DB_PATH}")
        return
    
    # DETERMINE FFMPEG PATH
    cfg = CONFIG.FFMPEG_SETTINGS
    candidate_path = cfg.get('binary_path')
    
    if candidate_path:
        path_obj = Path(candidate_path)
        if path_obj.is_dir():
            # Try to find ffmpeg inside
            if os.name == 'nt':
                potential = path_obj / 'ffmpeg.exe'
            else:
                potential = path_obj / 'ffmpeg'
                
            if potential.exists() and potential.is_file():
                FFMPEG_BINARY = str(potential)
            else:
                # Maybe it's in a bin subfolder?
                potential_bin = path_obj / 'bin' / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
                if potential_bin.exists():
                    FFMPEG_BINARY = str(potential_bin)
                else:
                    print(f"⚠️ Configured FFmpeg path is a directory and executable not found: {candidate_path}")
                    FFMPEG_BINARY = None
        elif path_obj.exists() and path_obj.is_file():
             FFMPEG_BINARY = str(path_obj)
        else:
             print(f"⚠️ Configured FFmpeg path does not exist: {candidate_path}")
             FFMPEG_BINARY = None
    else:
        FFMPEG_BINARY = shutil.which('ffmpeg')
        
    # DETERMINE FFPROBE PATH
    if FFMPEG_BINARY:
        # Check Hardware Acceleration Support
        cwd = os.path.dirname(FFMPEG_BINARY)
        HW_ACCEL_TYPE = check_hardware_acceleration(FFMPEG_BINARY, cwd)
        
        # Assume ffprobe is next to ffmpeg
        ffmpeg_path = Path(FFMPEG_BINARY)
        probe_candidate = ffmpeg_path.parent / ('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
        if probe_candidate.exists():
            FFPROBE_BINARY = str(probe_candidate)
        else:
            print("⚠️ FFmpeg found but FFprobe not found. Codec detection disabled.")

    print(f"Starting Dashboard on http://127.0.0.1:5000")
    local_ip = get_local_ip()
    print(f"LAN Access: http://{local_ip}:5000")
    print(f"Database: {DB_PATH}")
    
    if FFMPEG_BINARY:
        print(f"✅ FFmpeg detected at: {FFMPEG_BINARY}")
        if HW_ACCEL_TYPE == 'nvidia':
            print(f"🚀 NVIDIA Hardware Acceleration Detected (h264_nvenc) - ACTIVE")
        else:
            print(f"ℹ️  Software Encoding Active (libx264)")
    else:
        print("⚠️ FFmpeg not found. MKV/AVI/WMV playback disabled.")
        
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Media Organizer Web Server")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    args = parser.parse_args()
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Web Server")
        sys.exit(0)
    run_server(ConfigManager())