# ==============================================================================
# File: DESIGN_ARCHITECTURE.md
# Version: 0.3.5
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial architecture document creation.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Project name changed from "Personal Media Organizer and Deduplicator" to "File Organizer".
# 5. Updated version to 0.3.5, synchronized changelog, and set the status of deduplicator.py to 'Implemented' (v0.3.5).
# ------------------------------------------------------------------------------

# File Organizer Project: Design and Architecture Document

## 1. Architectural Overview 🏗️

The **File Organizer** project employs a **Modular, Data-Centric Architecture**.

* **Modular:** The core logic is isolated into nine distinct Python files (modules), each with a single, clear responsibility. This promotes testability and maintainability.
* **Data-Centric:** All state, analysis results, and file relationships are managed externally and persistently by a robust SQLite database. The modules act as processors that read from and write to the database.

## 2. File and Class Structure (10 Modules)

The project workflow is structured as a pipeline, where data flows through the modules sequentially:

| File Name | Class Name | Responsibility | Version Status |
| :--- | :--- | :--- | :--- |
| `config_manager.py`| `ConfigManager`| Loads, validates, and provides access to dynamic settings from `organizer_config.json`. | Ready (v0.1.2) |
| `config.py` | N/A | Global **static** settings and internal project constants (e.g., `DRY_RUN_MODE`, `BLOCK_SIZE`). | Ready (v0.1.5) |
| `database_manager.py`| `DatabaseManager`| Handles all SQLite connections, transactions, schema creation, and database teardown. | Ready (v0.1.6) |
| `file_scanner.py` | `FileScanner` | Traverses the file system, computes **SHA-256 content hash** (F02), and inserts basic path/hash data (F01). | Ready (v0.1.5) |
| `metadata_processor.py`| `MetadataProcessor`| Extracts complex, type-specific metadata (EXIF, video duration, document title) and updates `MediaContent` (F04). | Next |
| `deduplicator.py` | `Deduplicator` | Implements the logic to find duplicate groups (F03) and selects the "best" copy (F06), calculating the final path (F05). | **Implemented (v0.3.5)** |
| `migrator.py` | `Migrator` | Handles the actual file I/O: creating directories and copying primary files (F07) in live mode. | Planned |
| `html_generator.py` | `HTMLGenerator` | Queries final organized data and generates static HTML views (F09). | Planned |
| `report_generator.py` | `ReportGenerator` | Executes aggregate queries to generate the final statistical summary report (F08). | Planned |
| `main.py` | N/A | The project entry point and workflow orchestrator. | Planned |

---

## 3. Data Schema (SQLite) 💾

The database schema is normalized into two linked tables to support many-to-one mapping (many file paths point to one unique content hash).

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