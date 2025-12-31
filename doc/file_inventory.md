Here is the file inventory for the **File Organizer (v0.3.x)** project, categorized by function:

### ⚙️ Configuration & Database
*   **`config.py`**: Contains static global constants (e.g., `DRY_RUN_MODE`, `BLOCK_SIZE`).
*   **`config_manager.py`**: Loads and validates dynamic settings (paths, file groups) from `organizer_config.json`.
*   **`organizer_config.json`**: JSON file defining source/output directories and file extension groupings.
*   **`database_manager.py`**: Manages SQLite connections, schema creation (`MediaContent`, `FilePathInstances`), and query execution.

### 🧠 Core Logic Pipeline
*   **`main.py`**: The entry point and pipeline orchestrator (currently structured as a shell for integration).
*   **`file_scanner.py`**: Traverses directories, calculates SHA-256 hashes, and records file existence in the database.
*   **`metadata_processor.py`**: Identifies records with missing metadata and delegates extraction to `asset_manager.py`.
*   **`deduplicator.py`**: Identifies duplicate hashes, selects the "primary" copy (best date/path), and calculates the final organized path.
*   **`migrator.py`**: Handles the physical copying of files to the output directory (respects Dry-Run mode).

### 🏷️ Asset Modeling & Metadata
*   **`asset_manager.py`**: "Conductor" class that routes files to the specific Asset model based on file type.
*   **`base_assets.py`**: Defines `GenericFileAsset`, `ImageAsset`, `AudioAsset`, and `DocumentAsset` classes.
*   **`video_asset.py`**: Specialized model for Video files (handling resolution, codecs, aspect ratio).
*   **`libraries_helper.py`**: Wrapper for external libraries (`Pillow`, `MediaInfo`, `tqdm`, `Hachoir`) to handle dependencies safely.

### 📊 Reporting & UI
*   **`html_generator.py`**: Generates the static HTML Dashboard (`media_dashboard.html`) with the 3-tab sidebar and metadata modal.
*   **`report_generator.py`**: Queries the database to generate text-based statistical reports (space savings, duplicates, timeline).

### 🛠️ Utilities
*   **`version_util.py`**: **Central Authority** for project versioning. Audits all files to ensure version synchronization.
*   **`CodeStats.py`**: Legacy utility for counting lines of code and function definitions.
*   **`DebugPrint.py`**: Utility for granular debug logging control.
*   **`demo_libraries.py`**: Standalone script to demonstrate/test library capabilities (hashing, metadata extraction) with progress bars.

### 🧪 Testing
*   **`test/test_all.py`**: The master test runner. Executes all sub-tests and generates a formatted results table.
*   **`test/test_assets.py`**: Unit tests for asset class hierarchy and parsing logic.
*   **`test/test_database_manager.py`**: Unit tests for DB connectivity and schema integrity.
*   **`test/test_deduplicator.py`**: Unit tests for primary copy selection and path calculation.
*   **`test/test_file_scanner.py`**: Unit tests for hashing accuracy and directory traversal.
*   **`test/test_libraries.py`**: Unit tests for external library wrappers and version reporting.
*   **`test/test_metadata_processor.py`**: Unit tests for metadata extraction flows and corruption handling.

### 📄 Documentation
*   **`DESIGN_ARCHITECTURE.md`**: High-level architectural overview and module responsibilities.
*   **`DETAILED_DESIGN_PLAN.md`**: TDD specs and implementation estimates.
*   **`DEVELOPMENT_ROADMAP.md`**: Phase-based project schedule.
*   **`README.md`**: User setup guide and installation instructions.
*   **`README_REQUIREMENTS.md`**: Functional (F-xx) and Non-Functional (N-xx) requirements.
*   **`file_inventory.md`**: This document.