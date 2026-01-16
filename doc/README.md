# ==============================================================================
# File: README.md
_MAJOR_VERSION = 0
_MINOR_VERSION = 5
_CHANGELOG_ENTRIES = [
    "Initial creation of the README file.",
    "Updated for v0.3.x pipeline features.",
    "Updated for v0.9.x Web Dashboard, Transcoding, and Visual Analysis features.",
    "Added Release Automation workflow details."
]
# ------------------------------------------------------------------------------

# 🗄️ File Organizer

This is a high-performance Python utility designed to catalog, deduplicate, and organize vast media collections (images, videos, documents). It features a modern **Web Dashboard** for browsing, inspecting, and managing your files locally.

## 🚀 Key Features

### Core Organization
*   **Deduplication**: Identifies exact duplicates using SHA-256 hashing.
*   **Visual Match**: Identifies resized or edited duplicates using **Perceptual Hashing (dHash)**.
*   **Organization**: Sorts files into a `YEAR/MONTH` folder structure.
*   **Safety**: Non-destructive "Copy" migration by default (Dry-Run supported).

### Web Dashboard
A responsive Flask-based UI running locally (`http://127.0.0.1:5000`):
*   **Map View**: Visualize GPS-tagged photos on an interactive world map (Leaflet.js).
*   **Inspector**: View metadata, add **User Notes** (saved to DB), and check file history.
*   **Live Transcoding**: Streams MKV, AVI, and HEVC videos to the browser on-the-fly using FFmpeg.
*   **Hardware Acceleration**: Supports **NVIDIA NVENC** for high-speed video transcoding.
*   **RAW & HEIC Support**: Automatically converts professional formats (`.CR2`, `.NEF`, `.HEIC`, `.TIF`) for browser preview.

## 🛠️ Setup & Installation

### 1. Prerequisites
*   Python 3.8+
*   **FFmpeg** (Required for video transcoding)

### 2. Installation
```bash
git clone [Repo URL]
cd file_organizer
pip install -r requirements.txt
```
### 3. Usage
🖥️ Usage
1. Build the Database (The Pipeline)
Run the full pipeline to scan, index, hash, and organize your files:
```bash
python main.py --all
--scan: Indexes files and calculates SHA256.
--meta: Extracts metadata (Exif, Codecs, GPS, Perceptual Hashes).
--dedupe: Finds exact duplicates.
--migrate: Copies files to the Output Directory and builds clean_index.sqlite.
--report: Generates a statistical report (including Visual Duplicates).
```
2. Launch the Dashboard
Start the web server to browse your organized library:
```bash
python main.py --serve
```
Access at: http://127.0.0.1:5000
Map: Click the "Map" button in the top bar.
Visual Duplicates: Go to Sidebar -> Dupes -> Show Visual Match.
Transcoding: Videos not natively supported by Chrome (AVI, MKV) are transcoded automatically.
Export: Click "Export DB" to download the SQLite catalog.

🧩 Maintenance & Troubleshooting
Utility Scripts
reset_metadata.py: Force re-extraction of metadata for specific file types.
Usage: python reset_metadata.py .mkv .avi --auto
reset_hashes.py: Force recalculation of Perceptual Hashes (for Visual Match).
Usage: python reset_hashes.py
debug_ffmpeg.py: Diagnostics to test transcoding configuration.
debug_mkv.py: Diagnostics to test MediaInfo library access.
release.py: Automated release engineering tool (cleans changelogs, updates version history).

🧪 Testing
Run the comprehensive test suite to verify your environment:
code
Bash
python test/test_all.py

📦 Release Management
To prepare the project for a new release (cleaning changelogs and compressing context):
code
Bash
python release.py --dry-run
python release.py
