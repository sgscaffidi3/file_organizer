# ==============================================================================
# File: DEVELOPMENT_ROADMAP.md
# Version: 0.1.0
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the project development roadmap and schedule.
# 2. Synchronized tasks with Functional Requirements F01-F10 and project version 0.3.26.
# ------------------------------------------------------------------------------

# File Organizer Project: Development Roadmap & Schedule

This document outlines the remaining tasks required to reach a v1.0.0 production-ready state. Estimates are based on focused development hours and include time for unit test creation.

## 📅 Project Completion Schedule

| Phase | Task ID | Task Description | Estimated Effort | Requirement Link |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | **T01** | **Metadata Processor Implementation**: Extract EXIF (Pillow), Video duration/bitrate (MoviePy), and Document titles. | 10-14 Hours | F04 |
| **Phase 1** | **T02** | **Metadata Unit Testing**: Create `test_metadata_processor.py` and verify extraction across different file types. | 4 Hours | N/A |
| **Phase 2** | **T03** | **Migrator Implementation**: Build directory creation logic and safe file-copying routines with Dry-Run support. | 6-8 Hours | F07, N03 |
| **Phase 2** | **T04** | **Safety & I/O Testing**: Verify that source files are never modified and that collision handling works. | 4 Hours | N02 |
| **Phase 3** | **T05** | **Report Generator**: Implement SQL aggregate queries to output final statistics (savings, file counts). | 4-6 Hours | F08 |
| **Phase 3** | **T06** | **HTML Generator**: Create a basic static site generator to browse the organized output. | 8-10 Hours | F09 |
| **Phase 4** | **T07** | **Main Orchestrator & CLI**: Tie all modules into `main.py` and implement the primary command-line interface. | 6 Hours | F01, N06 |
| **Phase 4** | **T08** | **Integration Testing**: Run the full pipeline (Scan -> Process -> Migrate) on a multi-GB test set. | 8 Hours | N01 |

**Total Estimated Remaining Effort: 50 - 64 Development Hours**

---

## 🏗️ Detailed Task Breakdown

### Phase 1: The "Intelligence" Layer (T01 - T02)
This is the most complex remaining coding task. The `MetadataProcessor` must gracefully handle corrupted files and missing library dependencies.
* **Key Challenge**: Mapping various metadata formats (EXIF, IPTC, XMP) into a single `date_best` field in the database.
* **Dependency**: Requires `Pillow` and potentially a video library like `MoviePy`.

### Phase 2: The "Action" Layer (T03 - T04)
The `Migrator` performs the physical file organization.
* **Key Challenge**: Implementing functional requirement **F07** while strictly adhering to non-functional requirement **N02** (original files must never be modified).
* **Dry-Run Logic**: Must provide detailed console output of what *would* happen without moving a single byte if `DRY_RUN_MODE` is enabled.

### Phase 3: The "Output" Layer (T05 - T06)
This phase transforms database records into human-readable results.
* **Report**: Calculates "Space Saved" by subtracting the total size of primary files from the total size of all instances.
* **HTML**: Provides the "Presentation" layer (F09).

### Phase 4: Integration & Orchestration (T07 - T08)
The final phase builds `main.py`, which acts as the conductor for the modules.
* **CLI Support**: Ensures the main tool supports `--version` and `--help` for consistency with core modules (N06).
* **Scalability Check**: A final stress test to ensure the database handles tens of thousands of records without significant slowdown (N01).

---

## 🚦 Current Project Status: 45% Complete
* **Infrastructure**: Database, Config, and Versioning logic are 100% complete.
* **Core Logic**: Scanning and Deduplication logic are 100% complete.
* **Testing**: Integrated Test Runner (`test_all.py`) is at v0.3.26 and provides detailed reporting.