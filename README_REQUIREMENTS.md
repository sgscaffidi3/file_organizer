# ==============================================================================
# File: README_REQUIREMENTS.md
# Version: 0.3.6
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial document creation outlining Functional and Non-Functional requirements.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Project name changed from "Personal Media Organizer and Deduplicator" to "File Organizer".
# 5. Added N06 requirement to formalize CLI tool support for --version and --help.
# 6. Updated version to 0.3.6, synchronized changelog, and documented the default primary selection criteria for F06.
# ------------------------------------------------------------------------------

# File Organizer Project: Requirements Specification

This document outlines the core functional and non-functional requirements for the **file organization and deduplication utility**.

## 1. Functional Requirements (What it Must Do)

| ID | Requirement | Detail |
| :--- | :--- | :--- |
| **F01** | **Scanning** | Recursively traverse a source directory (defined in **JSON config**). |
| **F02** | **Hashing** | Calculate the **SHA-256 hash** for all files using incremental reading (`config.BLOCK_SIZE`) to support multi-terabyte scale. |
| **F03** | **Deduplication** | Identify all file paths that share the same SHA-256 hash. Store hash-to-path mappings in `FilePathInstances`. |
| **F04** | **Metadata Extraction** | Extract file-type-specific metadata (EXIF, video duration, document title) and store the aggregated, best-quality data in `MediaContent`. |
| **F05** | **Path Organization**| Calculate a deterministic, standardized output path for each unique file based on its **`date_best`** and **`file_type_group`**. |
| **F06** | **Primary Selection** | Implement logic to select the "primary" copy to keep from a group of duplicates based on user-defined criteria. **Default criteria is: Earliest DB `date_modified` > Shortest path > Smallest `file_id`.** |
| **F07** | **Migration** | (Live Mode Only) Copy the primary file instance (F06) to its calculated final path (F05) in the configured output directory. |
| **F08** | **Reporting** | Generate a detailed summary report of input analysis, duplicate counts, space savings, and final organizational structure. |
| **F09** | **Presentation** | Generate static HTML files to allow a user to browse the organized media structure easily. |

---

## 2. Non-Functional Requirements (Constraints)

| ID | Requirement | Detail |
| :--- | :--- | :--- |
| **N01** | **Scalability** | Must be designed to handle and process **multi-terabyte data sets**. |
| **N02** | **Safety** | Original source files must **never** be modified, moved, or deleted. |
| **N03** | **Dry-Run Mode** | Must execute fully, but **must not** perform any file-copying operations when `config.DRY_RUN_MODE` is `True`. |
| **N04** | **Persistence** | All analysis results and project state must be stored persistently in an **SQLite database**. |
| **N05** | **Future-Proofing**| The `MediaContent` schema must support adding future fields for AI analysis. |
| **N06** | **Tool Support** | Each core Python module must support standalone execution with the `--version` (`-v`) and `--help` (`-h`) command-line arguments. |