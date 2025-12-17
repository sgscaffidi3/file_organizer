# ==============================================================================
# File: README_REQUIREMENTS.md
# Version: 0.3.7
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial document creation outlining Functional and Non-Functional requirements.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Project name changed from \"Personal Media Organizer and Deduplicator\" to \"File Organizer\".
# 5. Added N06 requirement to formalize CLI tool support for --version and --help.
# 6. Updated version to 0.3.6, synchronized changelog, and documented the default primary selection criteria for F06.
# 7. Updated version to 0.3.7; changes are up-to-date with project version 0.3.26. Added F10 (Dependency Audit) to functional requirements.
# ------------------------------------------------------------------------------

# File Organizer Project: Requirements Specification

This document outlines the core functional and non-functional requirements for the **file organization and deduplication utility**.

## 1. Functional Requirements (What it Must Do)

| ID | Requirement | Detail |
| :--- | :--- | :--- |
| **F01** | **Scanning** | Recursively traverse a source directory (defined in **JSON config**). |
| **F02** | **Hashing** | Calculate the **SHA-256 hash** using incremental reading to support multi-terabyte scale. |
| **F03** | **Deduplication** | Identify all file paths sharing the same SHA-256 hash. |
| **F04** | **Metadata Extraction** | Extract type-specific metadata (EXIF, duration, etc.) for `MediaContent`. |
| **F05** | **Path Organization**| Calculate standardized output paths based on **`date_best`** and **`file_type_group`**. |
| **F06** | **Primary Selection** | Select the "primary" copy to keep based on earliest DB `date_modified` > Shortest path > Smallest `file_id`. |
| **F07** | **Migration** | (Live Mode Only) Copy the primary file instance to its calculated final path. |
| **F08** | **Reporting** | Generate a detailed summary of analysis, library versions, duplicate counts, and space savings. |
| **F09** | **Presentation** | Generate static HTML files to browse the organized media structure. |
| **F10** | **Dependency Audit** | Verify the presence and versions of required third-party libraries (tqdm, Pillow) before execution. |

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