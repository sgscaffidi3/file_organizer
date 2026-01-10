# ==============================================================================
# File: doc/README.md
# Version: 0.1.3
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Updated documentation to reflect the new JSON-based configuration.
# 2. Added section for Web Dashboard and Transcoding features.
# 3. Documented NVIDIA Hardware Acceleration setup.
# ------------------------------------------------------------------------------

# 🗄️ File Organizer

This is a high-performance Python utility designed to catalog, deduplicate, and organize vast media collections (images, videos, documents). It features a modern **Web Dashboard** for browsing, inspecting, and managing your files.

## 🚀 Key Features

*   **Deduplication**: Identifies duplicates using SHA-256 hashing.
*   **Organization**: Sorts files into a `YEAR/MONTH` folder structure.
*   **Web Dashboard**: A responsive Flask-based UI to browse your library.
    *   **Map View**: Visualize GPS-tagged photos on an interactive world map.
    *   **Inspector**: View metadata, add **User Notes**, and check file history.
    *   **Transcoding**: Streams MKV, AVI, and HEVC videos to the browser on-the-fly.
*   **Hardware Acceleration**: Supports **NVIDIA NVENC** for fast video transcoding.
*   **RAW & HEIC Support**: Automatically converts professional formats for browser preview.

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
### 3. Configuration
Edit organizer_config.json to set your paths:
```bash
{
    "paths": {
        "source_directory": "C:/Your/Media/Source",
        "output_directory": "./organized_media_output"
    },
    "ffmpeg": {
        "binary_path": "C:/Path/To/ffmpeg/bin/ffmpeg.exe" 
    }
}
```
If binary_path is null, the system attempts to auto-detect FFmpeg from your system PATH.
🖥️ Usage
1. Build the Database (The Pipeline)
Run the full pipeline to scan, index, and organize your files:
```bash
python main.py --all
--scan: Indexes files.
--meta: Extracts metadata (Exif, Codecs, GPS).
--dedupe: Finds duplicates.
--migrate: Copies files to the Output Directory.
```
2. Launch the Dashboard
Start the web server to browse your organized library:
```bash
python main.py --serve
Access at: http://127.0.0.1:5000
Note: Also Accessible from other machines on your LAN, at http://your.ip.v4.address:5000
Map: Click the "Map" button in the top bar to see your geotagged photos.
Transcoding: Videos not natively supported by Chrome (AVI, MKV) are transcoded automatically.
Tip: If you have an NVIDIA GPU, ensure your drivers are installed. The server will auto-detect h264_nvenc.
```
🧩 Advanced Features
Clean Export:
If you want to view a "clean" version of the database (showing only the organized files, not the source files), run:
```bash
python main.py --serve --db "organized_media_output/clean_index.sqlite"
```
Dry-Run Summary
If you want to view a complete version of the database (showing all the source files), run:
```bash
python main.py --serve --db "organized_media_output/metadata.sqlite"
```
User Notes
You can add persistent notes to any file via the Inspector
```(Click the (i) button). Notes are saved to the SQLite database and exported with your library.
```
🧪 Testing:
Run the comprehensive test suite to verify your environment:
```bash
python test/test_all.py
```
