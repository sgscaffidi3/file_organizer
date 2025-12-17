# ==============================================================================
# File: DESIGN_ARCHITECTURE.md
# Version: 0.3.6
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial architecture document creation.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Project name changed from "Personal Media Organizer and Deduplicator" to "File Organizer".
# 5. Updated version to 0.3.5, synchronized changelog, and set the status of deduplicator.py to 'Implemented' (v0.3.5).
# 6. Updated version to 0.3.6; changes are up-to-date with project version 0.3.26. Added libraries_helper.py and version_util.py to the module list.
# ------------------------------------------------------------------------------

# File Organizer Project: Design and Architecture Document

## 1. Architectural Overview 🏗️

The **File Organizer** project employs a **Modular, Data-Centric Architecture**.

* **Modular:** The core logic is isolated into twelve distinct Python files (modules), each with a single, clear responsibility. This promotes testability and maintainability.
* **Data-Centric:** All state, analysis results, and file relationships are managed externally and persistently by a robust SQLite database. The modules act as processors that read from and write to the database.

## 2. File and Class Structure (12 Modules)

The project workflow is structured as a pipeline, where data flows through the modules sequentially:

| File Name | Class Name | Responsibility | Version Status |
| :--- | :--- | :--- | :--- |
| `config_manager.py`| `ConfigManager`| Loads, validates, and provides access to dynamic settings from `organizer_config.json`. | Ready (v0.1.2) |
| `config.py` | N/A | Global **static** settings and internal project constants (e.g., `DRY_RUN_MODE`, `BLOCK_SIZE`). | Ready (v0.1.5) |
| `database_manager.py`| `DatabaseManager`| Handles all SQLite connections, transactions, schema creation, and database teardown. | Ready (v0.1.6) |
| `file_scanner.py` | `FileScanner` | Traverses the file system, computes **SHA-256 content hash**, and inserts basic path/hash data. | Ready (v0.1.5) |
| `metadata_processor.py`| `MetadataProcessor`| Extracts complex, type-specific metadata (EXIF, video duration, document title) and updates `MediaContent`. | Next |
| `deduplicator.py` | `Deduplicator` | Implements logic to find duplicate groups and selects the "best" copy, calculating the final path. | Implemented (v0.3.5) |
| `libraries_helper.py`| N/A | Utility to manage library version checks and provide progress bar abstractions (tqdm). | Ready (v0.1.0) |
| `version_util.py` | N/A | Core utility for project-wide version auditing and multi-file consistency checks. | Ready (v0.3.0) |
| `migrator.py` | `Migrator` | Handles file I/O: creating directories and copying primary files in live mode. | Planned |
| `html_generator.py` | `HTMLGenerator` | Queries final organized data and generates static HTML views. | Planned |
| `report_generator.py` | `ReportGenerator` | Executes aggregate queries to generate the final statistical summary report. | Planned |
| `main.py` | N/A | The project entry point and workflow orchestrator. | Planned |

---

## 3. Data Schema (SQLite) 💾

The database schema is normalized into two linked tables to support many-to-one mapping.

### MediaContent Table (Unique Files)

| Field | Type | Description |
| :--- | :--- | :--- |
| `content_hash` | TEXT | **PRIMARY KEY**. The unique SHA-256 hash of the file content. |
| `new_path_id` | TEXT | The calculated final storage path/filename (set by `Deduplicator`). |
| `file_type_group`| TEXT | IMAGE, VIDEO, AUDIO, DOCUMENT, or OTHER. |
| `size` | INTEGER | File size in bytes (initial stat). |
| `date_best` | TEXT | The best determined date (EXIF > Video > File System). |
| `width` | INTEGER | Image/video width (set by `MetadataProcessor`). |
| `height` | INTEGER | Image/video height (set by `MetadataProcessor`). |
| `duration` | REAL | Video/audio duration in seconds. |
| `bitrate` | INTEGER | Video/audio bitrate. |
| `title` | TEXT | Document title or similar rich metadata. |
| `description_ai` | TEXT | Reserved for future AI analysis (N05). |

### FilePathInstances Table (All Copies)

| Field | Type | Description |
| :--- | :--- | :--- |
| `instance_id` | INTEGER | **PRIMARY KEY** AUTOINCREMENT. |
| `content_hash` | TEXT | **FOREIGN KEY** referencing `MediaContent.content_hash`. |
| `original_full_path`| TEXT | The absolute path on the source file system (UNIQUE). |
| `original_relative_path`| TEXT | Path relative to the configured source directory. |