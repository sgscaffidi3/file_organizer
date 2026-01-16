<!--
File: doc/DESIGN_ARCHITECTURE.md
_MAJOR_VERSION: 0
_MINOR_VERSION: 1
Changelog:
- Initial architecture document creation.
- Implemented the versioning and patch derivation strategy.
- Updated versioning logic details.
- Added libraries_helper.py and version_util.py to the module list.
- Updated to reflect Phase 6 architecture (Web Server, Release, Transcoding).
-->

# File Organizer Project: Design and Architecture Document

## 1. Architectural Overview 🏗️

The **File Organizer** project employs a **Modular, Data-Centric Architecture**.

*   **Modular:** The core logic is isolated into distinct Python files (modules), each with a single, clear responsibility.
*   **Data-Centric:** All state, analysis results, and file relationships are managed externally and persistently by a robust SQLite database.
*   **Hybrid Interface:** Supports both a robust CLI for batch operations and a modern Web Dashboard (Flask) for interactive management.

## 2. File and Class Structure (Key Modules)

The project workflow is structured as a pipeline, where data flows through the modules sequentially:

| File Name | Responsibility |
| :--- | :--- |
| `config_manager.py`| Loads, validates, and provides access to dynamic settings from `organizer_config.json`. |
| `database_manager.py`| Handles all SQLite connections, transactions, schema creation, and database teardown. |
| `file_scanner.py` | Traverses the file system, computes **SHA-256 content hash**, and inserts basic path/hash data. |
| `metadata_processor.py`| Extracts complex, type-specific metadata (EXIF, dHash, GPS) and updates `MediaContent`. |
| `deduplicator.py` | Implements logic to find duplicate groups and selects the "best" copy. |
| `migrator.py` | Handles file I/O: creating directories and copying primary files (supports Dry-Run). |
| `server.py` | Hosts the Web Dashboard, REST API, and Video Transcoding stream. |
| `release.py` | Manages project lifecycle, version history, and context window optimization. |

---

## 3. Data Schema (SQLite) 💾

The database schema is normalized into two linked tables.

### MediaContent Table (Unique Files)

| Field | Type | Description |
| :--- | :--- | :--- |
| `content_hash` | TEXT | **PRIMARY KEY**. The unique SHA-256 hash of the file content. |
| `new_path_id` | TEXT | The calculated final storage path/filename. |
| `file_type_group`| TEXT | IMAGE, VIDEO, AUDIO, DOCUMENT, or OTHER. |
| `size` | INTEGER | File size in bytes. |
| `date_best` | TEXT | The best determined date (EXIF > Video > File System). |
| `width` | INTEGER | Image/video width. |
| `height` | INTEGER | Image/video height. |
| `duration` | REAL | Video/audio duration in seconds. |
| `perceptual_hash`| TEXT | Difference Hash (dHash) for visual duplicate detection. |
| `extended_metadata`| TEXT | JSON blob containing all extracted tags (Exif, Notes, etc). |

### FilePathInstances Table (All Copies)

| Field | Type | Description |
| :--- | :--- | :--- |
| `file_id` | INTEGER | **PRIMARY KEY** AUTOINCREMENT. |
| `content_hash` | TEXT | **FOREIGN KEY** referencing `MediaContent.content_hash`. |
| `original_full_path`| TEXT | The absolute path on the source file system (UNIQUE). |
| `is_primary` | BOOLEAN | Flag indicating if this is the copy chosen for migration. |