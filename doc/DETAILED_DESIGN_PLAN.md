# ==============================================================================
# File: DETAILED_DESIGN_PLAN.md
# Version: 0.1.0
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the detailed TDD design and implementation plan.
# 2. Synchronized requirements with project version 0.3.26.
# 3. Defined test cases, implementation stubs, and updated effort estimates.
# ------------------------------------------------------------------------------

# File Organizer: Detailed Design & TDD Implementation Plan

This document serves as the technical blueprint for the remaining development phases. Following the **Test-Driven Development (TDD)** philosophy, each task begins with the creation of automated tests to define "success" before any functional logic is written.

---

## 🟢 Phase 1: Metadata Processor (`metadata_processor.py`)
**Objective**: Fulfill **F04** by extracting rich metadata (EXIF, video length, etc.) to determine the `date_best` for every unique file.

### 1. Test Suite: `test_metadata_processor.py`
We will create a suite that uses small, known sample files to verify extraction logic.
* **Test 01: Image EXIF Extraction**: Verify `Pillow` correctly reads `DateTimeOriginal`.
* **Test 02: Video Duration Stub**: Verify the processor identifies video extensions and attempts duration extraction.
* **Test 03: Date Best Selection Logic**: Verify the hierarchy: EXIF Date > Video Date > File System `mtime`.
* **Test 04: Graceful Dependency Handling**: Verify that if `Pillow` is missing, the system defaults to File System dates without crashing.
* **Test 05: DB Update Integrity**: Verify that `MediaContent` records are updated correctly based on their `content_hash`.

* **Test Implementation Estimate**: 5 Hours
* **Logic Implementation Estimate**: 10 Hours
* **Total Phase 1 Estimate**: 15 Hours

### 2. Functional Requirements / Stubs
The class `MetadataProcessor` must implement:
* `process_unprocessed_records(db_manager)`: Main loop to find records with `date_best IS NULL`.
* `_get_exif_data(file_path)`: Private method using `PIL.Image`.
* `_get_video_info(file_path)`: Private method using `getattr` to safely check for video libraries.
* `_calculate_date_best(metadata_results, stat_info)`: Logic to pick the "best" date.

---



---

## 🟡 Phase 2: Migrator (`migrator.py`)
**Objective**: Fulfill **F07** by safely copying files to the organized structure while respecting **N02** (Safety) and **N03** (Dry-Run).

### 1. Test Suite: `test_migrator.py`
* **Test 01: Dry-Run Enforcement**: Verify that `config.DRY_RUN_MODE = True` results in zero file system changes.
* **Test 02: Destination Path Generation**: Verify path format: `OUTPUT/YEAR/MONTH/HASH_ID.EXT`.
* **Test 03: Permission Preservation**: Verify that `shutil.copy2` correctly preserves file timestamps during migration.
* **Test 04: Existing File Collision**: Test behavior when the destination file already exists (e.g., skip vs. overwrite).

* **Test Implementation Estimate**: 4 Hours
* **Logic Implementation Estimate**: 8 Hours
* **Total Phase 2 Estimate**: 12 Hours

### 2. Functional Requirements / Stubs
The class `Migrator` must implement:
* `run_migration(db_manager)`: Entry point to process all "Primary" copies identified by the Deduplicator.
* `_prepare_directory(target_dir)`: Thread-safe directory creation logic.
* `_perform_copy(source, target)`: The actual I/O operation with error logging.

---

## 🔵 Phase 3: Reporting & Presentation (`report_generator.py` & `html_generator.py`)
**Objective**: Fulfill **F08** and **F09** by providing high-level summaries of space saved and a browsable file gallery.

### 1. Test Suite: `test_reporting.py`
* **Test 01: Space Savings Query**: Verify that (Total Size) - (Primary Size) correctly identifies "wasted" space.
* **Test 02: Grouping Logic**: Verify that file counts (IMAGE, VIDEO, etc.) match the database totals.
* **Test 03: HTML Template Rendering**: Verify that the generator outputs a valid HTML structure with the expected summary data.

* **Test Implementation Estimate**: 6 Hours
* **Logic Implementation Estimate**: 10 Hours
* **Total Phase 3 Estimate**: 16 Hours

### 2. Functional Requirements / Stubs
* `ReportGenerator.get_stats()`: SQL aggregate function for total size and counts.
* `HTMLGenerator.build_index()`: Generates a static index.html with a table/grid view.

---

## 🔴 Phase 4: Main Orchestrator (`main.py`)
**Objective**: Tie all components together into a functional CLI tool.

### 1. Test Suite: `test_integration.py`
* **Test 01: End-to-End Workflow**: A full run using a mock source directory with duplicates and mixed file types.
* **Test 02: CLI Flag Logic**: Verify `--init`, `--scan`, and `--get_versions` trigger the appropriate modules.

* **Test Implementation Estimate**: 4 Hours
* **Logic Implementation Estimate**: 5 Hours
* **Total Phase 4 Estimate**: 9 Hours

### 2. Functional Requirements / Stubs
* `main()`: Argparse configuration and high-level exception handling.
* `WorkflowManager`: A coordinator class that instantiates and executes modules in order: `Scanner -> Processor -> Deduplicator -> Migrator`.

---

## 📈 Consolidated Estimates (TDD Focused)

| Task | Test Implementation | Logic Development | Total Hours |
| :--- | :--- | :--- | :--- |
| **Phase 1: Metadata** | 5h | 10h | 15h |
| **Phase 2: Migrator** | 4h | 8h | 12h |
| **Phase 3: Reporting** | 6h | 10h | 16h |
| **Phase 4: Main/CLI** | 4h | 5h | 9h |
| **TOTAL** | **19 Hours** | **33 Hours** | **52 Hours** |

**Note on Estimates**: Logic development includes the time to refactor code until it passes the pre-written tests. This TDD approach requires more time upfront for tests but significantly reduces the time spent on manual debugging during integration.