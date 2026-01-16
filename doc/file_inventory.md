<!--
File: doc/file_inventory.md
_MAJOR_VERSION: 0
_MINOR_VERSION: 1
Changelog:
- Initial creation of file inventory.
- Updated inventory to include release.py, server.py, and new utility scripts.
-->

Here is the file inventory for the **File Organizer** project, categorized by function:

### ⚙️ Configuration & Database
*   **`config.py`**: Contains static global constants.
*   **`config_manager.py`**: Loads and validates dynamic settings from `organizer_config.json`.
*   **`organizer_config.json`**: JSON file defining version, paths, file groups, and FFmpeg settings.
*   **`database_manager.py`**: Manages SQLite connections, schema creation (`MediaContent`, `FilePathInstances`), and query execution.

### 🧠 Core Logic Pipeline
*   **`main.py`**: The entry point and pipeline orchestrator.
*   **`file_scanner.py`**: Traverses directories, calculates SHA-256 hashes, and records file existence.
*   **`metadata_processor.py`**: Identifies records with missing metadata/hashes and delegates extraction.
*   **`deduplicator.py`**: Identifies duplicate hashes, selects the "primary" copy, and calculates final paths.
*   **`migrator.py`**: Handles physical copying of files and generation of `clean_index.sqlite`.

### 🏷️ Asset Modeling & Metadata
*   **`asset_manager.py`**: "Conductor" class that routes files to specific Asset models.
*   **`base_assets.py`**: Defines `GenericFileAsset`, `ImageAsset`, `AudioAsset`, and `DocumentAsset`.
*   **`video_asset.py`**: Specialized model for Video files.
*   **`libraries_helper.py`**: Wrapper for external libraries (`Pillow`, `MediaInfo`, `rawpy`, `ImageHash`) to handle dependencies safely.

### 📊 Reporting & Web UI
*   **`server.py`**: Flask Web Server handling API endpoints, streaming, and transcoding.
*   **`templates/dashboard.html`**: The frontend interface (HTML/JS/CSS) for the dashboard.
*   **`html_generator.py`**: (Legacy) Generates a static HTML Dashboard.
*   **`report_generator.py`**: Queries the database to generate text-based statistical reports.

### 🛠️ Release & Versioning
*   **`release.py`**: Automates version bumps, changelog cleanup, and code bundling.
*   **`version_util.py`**: Central Authority for auditing file versions and history.

### 🔧 Utilities (Maintenance)
*   **`reset_metadata.py`**: Forces re-extraction of metadata for specific file types.
*   **`reset_hashes.py`**: Forces re-calculation of Perceptual Hashes for visual deduplication.
*   **`debug_ffmpeg.py`**: Diagnostics tool to verify FFmpeg transcoding configuration.
*   **`debug_mkv.py`**: Diagnostics tool to verify MediaInfo DLL access.
*   **`fix_ui.py`**: Diagnostics tool to force-update the HTML template.
*   **`CodeStats.py`**: Legacy code analysis tool.
*   **`DebugPrint.py`**: Utility for granular debug logging control.

### 🧪 Testing
*   **`test/test_all.py`**: The master test runner (Console + Log file output).
*   **`test/test_*.py`**: Individual unit test suites for all major components.