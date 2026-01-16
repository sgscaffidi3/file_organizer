# ==============================================================================
# File: README_REQUIREMENTS.md
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial document creation outlining Functional and Non-Functional requirements.",
    "Updated versioning and patch derivation strategy.",
    "Added requirements for Visual Duplicates, Mapping, Transcoding, and Release Automation.",
    "Added **F11-F14** to cover Visual Matching, Mapping, Transcoding, and User Notes.",
    "Added **N07** for Release Automation."
]
# ------------------------------------------------------------------------------

# File Organizer Project: Requirements Specification

This document outlines the core functional and non-functional requirements for the **file organization and deduplication utility**.

## 1. Functional Requirements (What it Must Do)

| ID | Requirement | Detail |
| :--- | :--- | :--- |
| **F01** | **Scanning** | Recursively traverse a source directory (defined in **JSON config**). |
| **F02** | **Hashing** | Calculate the **SHA-256 hash** using incremental reading to support multi-terabyte scale. |
| **F03** | **Deduplication** | Identify all file paths sharing the same SHA-256 hash. |
| **F04** | **Metadata Extraction** | Extract type-specific metadata (EXIF, duration, GPS) for `MediaContent`. |
| **F05** | **Path Organization**| Calculate standardized output paths based on **`date_best`** and **`file_type_group`**. |
| **F06** | **Primary Selection** | Select the "primary" copy to keep based on earliest DB `date_modified` > Shortest path > Smallest `file_id`. |
| **F07** | **Migration** | (Live Mode Only) Copy the primary file instance to its calculated final path. |
| **F08** | **Reporting** | Generate a detailed summary of analysis, library versions, duplicate counts, and space savings. |
| **F09** | **Presentation** | Generate a dynamic Web Dashboard (Flask) to browse the organized media structure. |
| **F10** | **Dependency Audit** | Verify the presence and versions of required third-party libraries (tqdm, Pillow, FFmpeg) before execution. |
| **F11** | **Visual Duplicates** | Identify images that look similar (resized/edited) using **Perceptual Hashing (dHash)**. |
| **F12** | **Geospatial Mapping** | Display GPS-tagged images on an interactive world map within the dashboard. |
| **F13** | **Live Transcoding** | Transcode incompatible video formats (MKV, AVI, HEVC) to browser-safe MP4 on-the-fly. |
| **F14** | **User Annotation** | Allow users to add persistent notes to files via the Web UI, saved to the database. |

---

## 2. Non-Functional Requirements (Constraints)

| ID | Requirement | Detail |
| :--- | :--- | :--- |
| **N01** | **Scalability** | Must be designed to handle and process **multi-terabyte data sets**. |
| **N02** | **Safety** | Original source files must **never** be modified, moved, or deleted. |
| **N03** | **Dry-Run Mode** | Must execute fully without performing file-copying operations when `DRY_RUN_MODE` is `True`. |
| **N04** | **Persistence** | All analysis results and project state must be stored in an **SQLite database**. |
| **N05** | **Future-Proofing**| The `MediaContent` schema must support adding future fields for AI analysis. |
| **N06** | **Tool Support** | Each core module must support standalone execution with `--version` (`-v`) and `--help` (`-h`). |
| **N07** | **Release Automation** | The project must support a `release.py` workflow to clean changelogs and bundle code for LLM context optimization. |