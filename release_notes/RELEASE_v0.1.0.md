# Release v0.1.0
Date: 2026-01-16 18:06

## asset_manager.py
- Initial creation of AssetManager to coordinate asset processing.
- Integrated libraries_helper for metadata extraction.
- Implemented the Hybrid Metadata storage strategy into the database.
- Added support for --verbose flag to trigger exhaustive MediaInfo scans.
- FEATURE: Added calculation of Perceptual Hash (dhash) for IMAGE type assets.

## base_assets.py
- Initial creation of base_assets module with class inheritance.
- Implemented GenericFileAsset, AudioAsset, DocumentAsset, and ImageAsset.
- Standardized JSON 'backpack' across all asset types.
- Added project-standard versioning and CLI --version support.
- Added _clean_numeric helper for ImageAsset dimension scrubbing.
- FEATURE: Added get_friendly_size() for dynamic unit scaling (B, KiB, MiB, GiB).
- FEATURE: Expanded AudioAsset to capture Artist, Album, Song, VBR, and technical specs.
- BUG FIX: Added 'camera' attribute to ImageAsset to capture Make/Model metadata (Fixes test_assets error).

## bundle_project.py
- Automatically initialized by release script.

## CodeStats.py
- Automatically initialized by release script.

## config.py
- Added versioning and changelog structure to all files.
- Implemented the versioning and patch derivation strategy.
- Implemented --version/-v and --help/-h support for standalone execution.
- Refactored to remove dynamic settings (paths, file groups), which are now managed by ConfigManager.
- Project name changed to "file_organizer" in descriptions.
- Added CLI argument parsing for --version to allow clean exit during health checks.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- PERFORMANCE: Increased BLOCK_SIZE to 1MB to speed up hashing of large video files.
- REVERT: Rolled back BLOCK_SIZE to 64KB (from 1MB) as per user request.
- PERFORMANCE: Re-enabled 1MB BLOCK_SIZE for production speed.
- PERFORMANCE: Added HASHING_THREADS setting to control concurrency.
- PERFORMANCE: Added specific thread counts for Metadata Extraction and Migration.

## config_manager.py
- Initial creation to manage dynamic settings loaded from a JSON file.
- Project name changed to "file_organizer" in descriptions.
- Added CLI argument parsing for --version to allow clean exit during health checks.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- CRITICAL FIX: Added optional `output_dir` to `__init__` to enable test environment isolation, resolving `AttributeError` in test suite setup.
- CRITICAL IMPORT FIX: Moved `argparse` and `sys` imports to the `if __name__ == '__main__':` block to prevent dynamic import crashes.
- FEATURE: Added FFMPEG_SETTINGS property to expose video transcoding configuration.
- FEATURE: Added PROJECT_VERSION property to access the master version tuple.

## database_manager.py
- Initial implementation with basic connection management.
- Implemented the versioning and patch derivation strategy.
- Added basic schema creation for MediaContent and FilePathInstances tables.
- Added execute_query method to simplify database operations.
- Implemented context manager methods (__enter__, __exit__) for reliable connection handling.
- Improved execute_query to handle SELECT COUNT(*) returning empty results gracefully.
- CRITICAL SCHEMA FIX: Added the UNIQUE constraint to the 'path' column in the FilePathInstances table definition.
- CRITICAL SCHEMA FIX: Renamed the primary key of FilePathInstances from 'id' to 'file_id' to maintain consistency.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.
- CRITICAL SCHEMA FIX: Added the `date_modified` column to the `FilePathInstances` table.
- CRITICAL API FIX: Updated `execute_query` to return the `rowcount` for non-SELECT queries.
- CRITICAL SCHEMA FIX: Added `DEFAULT (DATETIME('now'))` to `FilePathInstances.date_modified`.
- FEATURE: Added dump_database() method and --dump_db CLI option for quick debugging inspection.
- SCHEMA MIGRATION: Added auto-detection and creation of 'new_path_id' column if missing (Fixes Deduplicator crash on legacy DBs).
- PERFORMANCE: Added Indices for content_hash and is_primary to eliminate full-table scans during deduplication.
- PERFORMANCE: Added execute_many() method to support high-speed batch updates.
- SCHEMA MIGRATION: Added 'perceptual_hash' column to MediaContent to support near-duplicate detection.

## DebugPrint.py
- Automatically initialized by release script.

## debug_ffmpeg.py
- Automatically initialized by release script.

## debug_mkv.py
- Automatically initialized by release script.

## deduplicator.py
- Initial implementation of Deduplicator class, handling primary copy selection (F06) and path calculation (F05).
- Updated _select_primary_copy to return a tuple (path, file_id) to support final path naming.
- Refactored final path calculation to include the primary copy's file_id in the filename (HASH_FILE_ID.EXT).
- Added CLI argument parsing for --version to allow clean exit during health checks.
- CRITICAL FIX: Modified _calculate_final_path to prepend OUTPUT_DIR, returning the full absolute path.
- CRITICAL FIX: Updated _select_primary_copy to read 'date_modified' from FilePathInstances, prioritizing DB time over file stat() to support tests.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.
- CRITICAL FIX: Updated `_calculate_final_path` signature to match the requirements of `test_deduplicator.py` (`ext` and `primary_file_id`).
- UX: Added TQDM progress bar for deduplication feedback.
- PERFORMANCE: Rewrote Deduplicator to use Batch Processing (Vectorization) instead of iterative DB calls. Speed improvement ~100x.
- FEATURE: Added support for 'rename_on_copy' config. If False, preserves original filename unless collision occurs.
- BUG FIX: Changed date fallback logic. If date_best is missing, use file_system_date (date_modified) instead of Today/2026.
- FIX: Added missing 'import sys' to support clean exit for version check.

## demo_libraries.py
- Initial creation and evolution of demo suite.
- Integrated DatabaseManager for persistence.
- Implemented Smart Update logic with field-level change detection.
- Added --debug option for exhaustive metadata printing.
- FEATURE: Implemented Nested Progress Bars (Overall + Per-File Hashing).
- RESTORED: --version support and fixed execution flow.
- FEATURE: Added recursive scanning and relative path preservation for subdirs.
- REFACTOR: Switched to using internal AudioAsset from base_assets.py.
- FEATURE: Implemented per-file database commits to allow resume-on-cancel.
- OPTIMIZATION: Added Fast-Skip logic (Path+Size check) to avoid redundant hashing.
- FEATURE: Added double-hash verification for mismatched files.

## file_scanner.py
- Initial implementation of high-performance file hashing and scanning logic (F01).
- Implemented incremental hashing using SHA256 (N01).
- Refactored scan logic to query file stats (size, modified date) before hashing, allowing fast skip of unchanged files (F02).
- Added support for configurable file groups (IMAGE, VIDEO, etc.) from ConfigManager.
- Implemented the insertion of MediaContent and FilePathInstances records.
- Refined path normalization to ensure absolute paths for database storage.
- Optimized file skipping for files already present in the database with matching size/mtime.
- FIX: The final path insertion uses the full path for the `path` column, explicitly ensuring correct behavior.
- CRITICAL FIX: Explicitly listed all column names in the FilePathInstances INSERT OR IGNORE statement to ensure SQLite correctly enforces the UNIQUE constraint on the 'path' column.
- DEFINITIVE FIX: Re-verified the explicit column listing in FilePathInstances INSERT OR IGNORE to ensure SQLite's UNIQUE constraint on 'path' is enforced.
- CRITICAL TEST FIX: Modified the insertion logic in `scan_and_insert` to ensure `self.files_inserted_count` is incremented accurately.
- UX: Added TQDM progress bar for real-time scanning feedback.
- REVERT: Removed nested byte-level progress bar as per user request.
- PERFORMANCE: Implemented RAM Cache for _check_if_known_and_unchanged to enable Fast Resume.
- UX: Re-implemented Nested Byte-Level Progress Bar for large file visibility.
- PERFORMANCE: Implemented Multithreaded Hashing using ThreadPoolExecutor (producer-consumer model).
- UX: Implemented Position Pool to allow multiple progress bars (one per thread) simultaneously.
- PERFORMANCE: Added 'Smart UI Threshold'. Only files > 50MB get a dedicated progress bar to prevent UI lag on small files.
- PERFORMANCE: Implemented Batch Database Commits (1000 records/batch) to eliminate disk IO latency.

## find_corrupt.py
- Automatically initialized by release script.

## html_generator.py
- Initial implementation of HTMLGenerator class.
- Added DataTables integration and Metadata Inspector.
- FEATURE: Added Hierarchical Folder Browser sidebar.
- FEATURE: Added dynamic folder-based filtering logic.
- FIX: Robust path handling for Python versions < 3.12.
- FIX: Restored missing CLI arguments (--version, --db).
- FEATURE: implemented Collapsible Folder Tree using <details> tags.
- FEATURE: Added 'Type View' (Browse by Media/Extension).
- FEATURE: Added 'Duplicates View' (Browse by Hash Collision).
- FIX: Restored vertical scrolling (overflow-y) to Metadata Modal window.
- FIX: Added explicit 'Root Directory' item in sidebar for files at base level.
- FIX: Added JS safety checks to metadata modal to prevent 'silent' failures.
- FIX: Added 'formatSize' utility to metadata inspector for human-readable sizes.
- FIX: Added video playback fallback message for browser/CORS compatibility issues.
- FIX: Resolved SyntaxError by removing f-string escaping issues in HTML generation.
- FIX: Restored missing --generate CLI argument and generation logic.
- FIX: Resolved ValueError by separating CSS/JS from .format() template parsing.
- FIX: Switched to simple string concatenation for final HTML to prevent JS corruption.
- FIX: Replaced onclick data-passing with HTML5 data-attributes to fix Metadata Modal.
- FIX: Resolved f-string backslash SyntaxError and restored missing sidebar variables.
- PERFORMANCE: Switched from string concatenation to list buffering for row generation (O(n) vs O(n^2)).
- UX: Added TQDM progress bar for HTML generation feedback.
- ARCHITECTURE: Switched to Client-Side Rendering (JSON Island) for massive performance gain on 100k+ files.
- UX: Added Dashboard Summary Cards (Total Size, Wasted Space, etc).
- UX: Implemented Lazy Loading for media previews to prevent browser hangs.
- UX: Added Dedicated Duplicate Report tab.
- BUG FIX: Defined hidden DataTables columns for Folder, Extension, and Hash to enable Sidebar Filtering.
- FIX: Explicitly implemented CLI version print to support test runner audit.
- FIX: Updated version print format to 'Version: X.Y.Z' to satisfy test auditor regex.

## libraries_helper.py
- Initial creation of libraries_helper to encapsulate external library interactions.
- Added utility for reporting installed library versions.
- Added demo function for tqdm progress bar use.
- Added function for extracting EXIF metadata using Pillow (F04 implementation detail).
- Implemented CLI argument parsing for --version to allow clean exit during health checks (N06).
- FEATURE UPGRADE: Added hachoir detection to get_library_versions to support video metadata.
- FEATURE UPGRADE: Implemented extract_video_metadata using Hachoir (F04).
- BUG FIX: Added safety checks for Hachoir tag retrieval to prevent 'Metadata has no value' errors.
- RELIABILITY: Improved tag discovery to capture width, height, and bitrate more reliably.
- RELIABILITY: Added recursive metadata discovery to find nested stream tags (F04).
- BUG FIX: Fixed 'is_list' attribute error by using 'is_group' for recursion.
- BUG FIX: Fixed 'Data' object attribute error by using flat iteration for video metadata.
- BUG FIX: Fixed 'Data' object attribute error by using direct item access and exportPlaintext.
- EVOLUTION: Integrated MediaInfo for professional-grade and dynamic metadata extraction.
- CLI: Added --verbose argument to toggle between standard and exhaustive MediaInfo extraction.
- SYNC: Refined internal logic to support external calls for verbose vs standard metadata.
- BUG FIX: Changed file size extraction to return raw integers instead of formatted strings to prevent processing errors in Asset models.
- FEATURE UPGRADE: Added specialized extractors for PDF, Office, Ebooks, and Archives.
- FEATURE UPGRADE: Added router logic to dispatch to specific extractors based on extension.
- FEATURE UPGRADE: Added support for RAW images, SVG, and PPTX metadata extraction.
- FEATURE UPGRADE: Added 'pillow-heif' registration for .HEIC support.
- DATA INTEGRITY: Updated MediaInfo extractor to return RAW INTEGERS for BitRate, Duration, Width, Height (Fixes sorting/reporting).
- ROBUSTNESS: Added automatic fallback to MediaInfo for HEIC files if Pillow/pillow-heif fails.
- FIX: Routed RAW images (.NEF, .CR2) to MediaInfo for Metadata. Pillow only reads thumbnails (160x120), MediaInfo reads true dimensions.
- FEATURE: Enhanced EXIF extraction to parse ISO, F-Stop, Shutter Speed, and GPS Coordinates.
- FEATURE: Implemented Deep EXIF Parsing (ExifIFD and GPSIFD) to capture Altitude, Brightness, Bias, and detailed Flash status.
- CRITICAL FIX: Switched RAW Metadata extraction to 'rawpy'. MediaInfo/Pillow often read the embedded thumbnail (160x120). rawpy ensures full sensor dimensions.
- BUG FIX: Added Duration extraction fallback to 'Video' track. Some containers (MKV/MPEG) only report duration on the stream, not the general container.
- FIX: Added .tif extension to image routing list to ensure Pillow extraction.
- FEATURE: Added 'calculate_image_hash' using ImageHash (dhash) for near-duplicate detection.

## main.py
- Initial implementation.
- Integrated all pipeline components (scanner, processor, deduplicator, migrator).
- Added graceful version check and orchestrator logic structure.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.
- COMPLETE REFACTOR: Implemented full PipelineOrchestrator class.
- FEATURE: Integrated FileScanner, MetadataProcessor, Deduplicator, Migrator, and Generators.
- CLI: Added flags for --scan, --meta, --dedupe, --migrate, --report, and --all.
- SAFETY: Added Database existence checks before running dependent stages.
- FEATURE: Added --serve flag to launch the Flask Web Dashboard.
- CLI: Added --db flag to override database path (useful for viewing clean_index.sqlite).
- FIX: Added db.create_schema() to run_metadata, run_dedupe, and run_migrate to ensure DB schema is up-to-date when skipping the scan phase.

## metadata_processor.py
- Initial implementation of MetadataProcessor class (F04).
- PRODUCTION UPGRADE: Integrated Pillow and Hachoir for extraction.
- RELIABILITY: Added safety handling for missing physical files.
- ARCHITECTURE REFACTOR: Migrated to Hybrid Metadata model via AssetManager.
- CLEANUP: Removed redundant local extractors; delegated all routing to AssetManager.
- FEATURE: Enabled full support for VIDEO, IMAGE, AUDIO, and DOCUMENT groups.
- UX: Added TQDM progress bar for real-time extraction feedback.
- BUG FIX: Updated _get_files_to_process query to prevent infinite re-processing of Audio/Docs.
- PERFORMANCE: Implemented Multithreaded Metadata Extraction using ThreadPoolExecutor.
- PERFORMANCE: Implemented Batch Database Writes (1000/batch) to fix SQLite locking issues.
- DATA SAFETY: Modified SQL UPDATE to use COALESCE, preventing NULL dates from overwriting valid file system dates.
- FIX: Added missing 'import argparse' to support clean exit for version check.
- FEATURE: Added Perceptual Hash (dhash) calculation to the processing loop for Images.
- RELIABILITY: Reduced DB_BATCH_SIZE to 50 and added KeyboardInterrupt handler for better resumability.
- CRITICAL FIX: Explicitly handle failed hash calculations by setting perceptual_hash to 'UNKNOWN' instead of NULL, preventing infinite processing loops.
- UX: Added startup stats to show Total vs Remaining files.
- UX: Added 'flush=True' to print statements to ensure immediate visibility.

## migrator.py
- Initial implementation of Migrator class, handling file copy operations (F07) and adhering to DRY_RUN_MODE (N03).
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.
- UX: Added TQDM progress bar for migration feedback.
- PERFORMANCE: Replaced N+1 query loop with a single SQL JOIN to instantly load migration jobs.
- FEATURE: Implemented 'Clean Database Export'. Creates a new SQLite DB reflecting the organized structure.
- LOGIC: Added automatic 'clean_index.sqlite' generation during Live Run.
- FEATURE: Inject 'Original_Filename' and 'Source_Copies' list into extended_metadata for Clean DB export.
- BUG FIX: Fixed path concatenation logic to prevent double-nesting of output directory.
- UX: Cleaned up relative paths in exported DB so Tree View starts at the Year.
- PERFORMANCE: Implemented Multithreaded Copying using ThreadPoolExecutor.
- PERFORMANCE: Optimized Path History Map building with TQDM feedback.

## report_generator.py
- Initial implementation of ReportGenerator class.
- Refactored for database-agnostic reporting using DatabaseManager.
- Added Video Codec and Resolution (SD/HD/4K) breakdown reports.
- Added Space-savings and Duplicate Audit path reporting.
- Added Image Megapixel (MP) quality breakdown.
- Added Extremes (Largest/Smallest, Longest/Shortest) and Averages.
- Added Yearly Timeline distribution.
- FIX: Handle 'N/A' or non-integer strings in duration and bitrate.
- FEATURE: Added Audio Codec and Bitrate quality tiers.
- CONSOLIDATION: Merged all previous features into a single comprehensive report.
- UPDATE: Refactored Duplicate Audit to show top 10 largest (with --verbose toggle).
- FEATURE: Added Extraction Spot-Check for largest file of each type.
- FIX: Corrected get_top_duplicates query to use COUNT(*) instead of non-existent fpi.id.
- FIX: Added null-checks for extended_metadata in get_audio_summary to prevent TypeError.
- FIX: CLI Version check now exits before attempting to connect to the database (resolves OperationalError).
- FIX: Reordered __main__ block to ensure clean version exit without DB errors.
- FEATURE: Added 'Visual Duplicates' report using Perceptual Hash matches.
- UX: Added TQDM progress bars to Visual Duplicate and Extraction Sample queries to prevent 'stuck' appearance.
- PERFORMANCE: Replaced N+1 query loop in 'Visual Duplicates' with a single optimized JOIN for instant results.

## reset_hashes.py
- Automatically initialized by release script.

## reset_metadata.py
- Automatically initialized by release script.

## reset_raw.py
- Automatically initialized by release script.

## server.py
- Initial implementation of Flask Server.
- Added API endpoints for Statistics, Folder Tree, and File Data.
- Implemented Server-Side Processing for DataTables (Pagination/Sorting/Filtering).
- Implemented secure media serving route to bypass local file security restrictions.
- Created modern Bootstrap 5 Dashboard template with dark mode.
- REFACTOR: Implemented full hierarchical Folder Tree (recursive) instead of flat list.
- REFACTOR: Added Type/Extension browser to Sidebar.
- FIX: Added SQLite custom function 'NORM_PATH' to handle Windows/Linux path separator mismatches.
- UX: Restored 3-Tab Sidebar (Browser, Types, Duplicates).
- FIX: Switched JS event handling to ID-based lookup to fix broken buttons.
- UX: Improved Tree rendering and CSS to ensure folder labels are visible.
- LOGIC: Added explicit handling for 'Root Directory' vs 'All Files'.
- FEATURE: Added Server-Side Sorting implementation for DataTables.
- FEATURE: Restored Image Thumbnails in the main table.
- FEATURE: Added 'Report' Tab with aggregate statistics (Charts/Tables).
- FEATURE: Added 'Unique Files' filter mode.
- FEATURE: Added Advanced Filters (Size, Date Year).
- FIX: Resolved SyntaxError (f-string backslash) for Python < 3.12 compatibility.
- REPORTING: Implemented Comprehensive Analysis (Res/Quality/Bitrate) in /api/report.
- FIX: Corrected logic for Duplicate vs Redundant counts.
- FIX: Improved extension normalization in Sidebar counts.
- FIX: Resolved f-string backslash SyntaxError (again) by moving replacement logic out.
- REPORTING: Added Image Quality (Megapixel) breakdown.
- FIX: Improved Audio Bitrate parsing to handle 'kbps' strings and prevent 'Unknown' results.
- UX: Renamed 'Duplicates' stat to 'Redundant Copies' for clarity.
- CLI: Added --version and --help support.
- FIX: Implemented special SQL logic for browsing files with no extension ('no_ext').
- UX: Clarified Duplicate Table vs Stats distinction.
- FEATURE: Added 'History' tab to File Inspector for viewing Original Name and Source Copies.
- UX: Added Database Name indicator in Navbar to distinguish Source Scan vs Clean Export.
- FEATURE: Added 'Quality' Tab to Sidebar for browsing by Resolution/Bitrate/Megapixels.
- FEATURE: Added Text File Preview (.txt, .md, .csv, etc) in File Inspector.
- SEARCH: Enhanced search to index 'extended_metadata', enabling search by Original Filename, Camera Model, etc.
- FIX: Enforced file_type_group constraints in Quality Filters (prevents Images appearing in Video lists).
- FEATURE: Added PDF Preview support via Embed.
- UX: Added browser compatibility warning for non-web video formats (MKV, AVI).
- PERFORMANCE: Replaced slow Python NORM_PATH function with native SQLite REPLACE() for massive speedup.
- FIX: Ensured metadata API returns valid JSON string '{}' even if DB is NULL to prevent JS display errors.
- REFACTOR: Separated HTML template into 'templates/dashboard.html' (Standard Flask MVC).
- FEATURE: Added On-the-Fly RAW Image Conversion (NEF/CR2 -> JPEG) via rawpy.
- FEATURE: Added .DOCX Text Extraction for browser preview.
- FEATURE: Added On-the-Fly HEIC Image Conversion (HEIC -> JPEG) via Pillow-HEIF.
- NETWORKING: Changed host to '0.0.0.0' to allow access from other computers on the LAN.
- FIX: Added Cache-Busting (?t=timestamp) to image previews to force browser to load High-Res RAW conversions.
- DEBUG: Added console logging for RAW conversion attempts.
- FEATURE: Added On-the-Fly Video Transcoding (MKV/AVI/WMV -> MP4) using FFmpeg streaming.
- FEATURE: Configurable FFmpeg binary path and arguments via organizer_config.json.
- FIX: Enforced '-pix_fmt yuv420p' and '-ac 2' in FFmpeg to ensure browser compatibility.
- FIX: Added robust path detection for FFmpeg to handle Folder paths vs Binary paths (fixes WinError 5).
- PERFORMANCE: Added '-tune zerolatency' and '-g 60' to FFmpeg to fix browser playback timeouts.
- DEBUG: Added stderr capture to FFmpeg stream to diagnose transcoding failures.
- COMPATIBILITY: Forced '-profile:v baseline' and '-reset_timestamps 1' to fix Gray Screen/0:00 duration issues.
- CRITICAL FIX: Set subprocess `bufsize=0` to prevent Python from holding video headers, fixing the Gray Screen hanging issue.
- DEBUG: Implemented threaded stderr reader to print FFmpeg logs to console in real-time.
- FIX: Resolved absolute path for FFmpeg input to prevent 'No such file' errors on nested directories.
- DEBUG: Simplified stderr handling to write directly to sys.stderr for immediate feedback.
- PERFORMANCE: Removed -analyzeduration/-probesize flags which were causing startup hangs on large files.
- CRITICAL FIX: Set `cwd` in subprocess to FFmpeg binary directory to ensure DLLs are found.
- FEATURE: Added `ffprobe` detection and HEVC/H.265 detection to force transcoding for 'Audio Only' MP4s.
- COMPATIBILITY: Added .mpg, .mpeg, and .mpe to mandatory transcoding list.
- FEATURE: Added /api/map endpoint to serve GPS coordinates from metadata.
- FEATURE: Added /api/update_notes endpoint to write User Notes into JSON metadata.
- FEATURE: Added /api/export_db endpoint to download the SQLite database.
- PERFORMANCE: Implemented Auto-Detection for NVIDIA GPU (h264_nvenc).
- PERFORMANCE: Added adaptive transcoding logic to swap 'libx264' with 'h264_nvenc' and adjust flags (crf->cq, preset->p1) automatically.
- UX: Added automatic LAN IP detection to print the actual network URL on startup.
- FEATURE: Added On-the-Fly TIFF to JPEG conversion to allow .tif/.tiff previews in browser.
- FEATURE: Added /api/visual_dupes endpoint to serve grouped Perceptual Hash matches.
- FIX: Added .tif and .tiff to conversion list (handled by Pillow) to fix broken previews in browser.
- CONFIG: Enabled TEMPLATES_AUTO_RELOAD to prevent caching of dashboard UI updates.

## version_util.py
- Initial implementation.
- Updated print_version_info to handle file reading for version detection.
- Implemented 'utf-8' encoding on file reads.
- Refactored versioning logic to use dynamic import of '_CHANGELOG_ENTRIES' list for patch determination (length of the list).
- Removed all comment-parsing logic, ensuring reliability of patch number calculation.
- Added 'import sys' and 'sys.exit(0)' to self-check for clean exit.
- Minor version bump to 0.3 to synchronize with highest version in the project.
- Added --get_all command to audit the version and format status of all files.
- CRITICAL FIX: Updated VERSION_CHECK_FILES to correctly locate test files within the 'test' subdirectory.
- Formatting fix: Increased the width of the 'FILE' column in the --get_all audit output.
- REFACTOR: Removed hardcoded file list. Implemented dynamic recursive scanning for .py files.
- FEATURE: Added --get_change_counts command to report historical changes using _REL_CHANGES list.
- LOGIC: Update audit to check if MINOR_VERSION matches the Master Config.
- FEATURE: Added print_change_history() to support the new --changes CLI flag across the project.

## video_asset.py
- Initial implementation of VideoAsset model.
- Integrated MediaInfo for professional stream-level parsing.
- Added support for DV/DVCPRO camera and tape metadata mapping.
- ARCHITECTURE REFACTOR: Now inherits from GenericFileAsset for shared behavior.
- FEATURE: Support for get_friendly_size() via base class inheritance.
- RESTORED: Re-integrated audio codecs, bitrates, and aspect ratio logic lost in refactor.

## test_all.py
- Refactored to act as the primary test runner by default (no flag).
- Added encoding='utf-8' to run_version_check to fix decoding issues.
- Fixed File Not Found errors by correcting 'VERSION_CHECK_FILES' paths.
- Fixed import error for self-check by moving version_util import inside the __main__ block.
- Added IMMEIDATE PATH SETUP to prevent crash during self-check subprocess.
- CRITICAL FIX: Simplified TEST_MODULES names and import logic to fix "No module named 'test.test_...'" error.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Updated VERSION_CHECK_FILES list to include all 11 core and utility files for full version synchronization check.
- FEATURE: Implemented CustomTestResult and CustomTestRunner to generate a detailed, structured summary table of all test results (PASS/FAIL/ERROR) at the end of the run. Refactored test loading to use TestLoader.loadTestsFromTestCase to remove DeprecationWarning.
- CRITICAL FIX: Implemented safe parsing in CustomTestResult._get_test_info to prevent IndexError when processing non-standard unittest IDs (like setup/teardown steps).
- CRITICAL FIX & READABILITY IMPROVEMENT: Modified CustomTestResult._get_test_info to use robust test object attributes (__module__, _testMethodName) instead of unreliable string parsing. Corrected test run metrics calculation and improved detailed table readability by formatting module and method names.
- READABILITY IMPROVEMENT: Modified format_results_table to dynamically calculate column widths and use string padding for consistent, aligned output in the detailed report table.
- VISUAL FIX: Refined column width calculation and separator line generation in format_results_table to ensure perfect alignment of all pipe characters (|) in the console output.
- VISUAL FIX: Corrected f-string padding logic to ensure the separator line uses the exact same calculated total width as the header and data rows, fixing final pipe alignment.
- VISUAL FIX: Applied dynamic column width calculation and padding to the Summary Table for improved console alignment and readability.
- FEATURE: Added 'test_libraries' to the test suite and updated version audit list.
- FEATURE: Added 'test_migrator' to the test suite and updated version audit list.
- FEATURE: Added 'test_type_coverage' to the test suite (TDD Red Phase).
- FEATURE: Implemented Log File Output. Tests now write to 'test_run.log' in addition to console.
- UX: Changed log file extension to .txt for easier sharing.
- FIX: Moved version check argument parsing before logging setup to prevent sys.unraisablehook error.

## test_assets.py
- Initial creation of TestAssetArchitecture suite.
- Added data cleaning validation for VideoAsset attributes.
- Implemented aspect ratio and JSON backpack verification.
- Integrated project-standard versioning and --version CLI support.
- CRITICAL: Added sys.path bootstrapping to resolve ModuleNotFoundError in subdirectories.
- Added Integration Test for AssetManager using Mock Database patterns.
- FEATURE: Added Test #04 for missing data resilience (Corrupt File handling).
- FIX: Updated db integration test to account for new 'perceptual_hash' column index.

## test_database_manager.py
- Initial implementation.
- Updated to use DatabaseManager's context manager functionality.
- Implemented a test for FOREIGN KEY constraint enforcement (test_03).
- Corrected test path definitions to use pathlib correctly relative to the project root.
- Added tearDown method to ensure the DB file is removed after every test method for strict isolation.
- CRITICAL FIX: Corrected tearDown method to access db_path using the class name (TestDatabaseManager.db_path) instead of self.db_path, resolving AttributeError errors.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.

## test_deduplicator.py
- Initial implementation.
- CRITICAL FIX: Implemented logic to correctly set `is_primary=1`.
- CRITICAL FIX: Updated `setUp` to create mock files with unique `mtime`.
- CRITICAL TEST FIX: Refined test data arguments.
- TEST REFACTOR: Removed obsolete test for `_select_primary_copy` (logic is now in batch query).
- TEST REFACTOR: Updated `_calculate_final_path` test to match new signature (6 arguments).
- TEST REFACTOR: Verified database state for `run_deduplication` test.
- TEST FIX: Forced 'rename_on_copy' preference to True in test_02 to ensure deterministic path generation.

## test_file_scanner.py
- Initial implementation of test suite for FileScanner.
- CRITICAL FIX: Implemented logic to correctly create mock files (A, B, C, D) and their directories in `setUpClass`.
- CRITICAL FIX: Used a real ConfigManager instance for tests to properly handle output paths.
- CRITICAL FIX: Extended `setUpClass` to ensure the correct hashes (HASH_64KB_X, HASH_64KB_Y) are generated and set as class attributes to be used in assertions.
- Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.
- Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.
- CRITICAL PATH FIX: Explicitly added the project root to `sys.path` to resolve `ModuleNotFoundError: No module named 'version_util'` when running the test file directly.
- CRITICAL TEST FIX: Explicitly check for successful insertion into MediaContent in `test_01` and `test_02`. This was implicitly broken by the prior fix to the scanner's counter logic.
- DEFINITIVE TEST FIX: Added constants for HASH_64KB_X and HASH_64KB_Y based on the file contents created, and ensured `setUpClass` closes the setup DB connection to prevent `PermissionError`. Added explicit definition of mock file paths and a check for inserted content to resolve `IndexError` and `AssertionError: 0 != 1`.
- CRITICAL CONFIG FIX: Removed unsupported `source_dir` argument from ConfigManager initialization in `setUpClass`.

## test_libraries.py
- Initial creation of test_libraries.py to validate external library helpers.
- Implemented test for version reporting (get_library_versions).
- Implemented test for TQDM progress bar wrapper.
- Implemented test for Pillow metadata extraction with a non-existent file path.
- Implemented test for standalone CLI version check (N06).
- BUG FIX: Updated error key assertions to match granular error keys (Pillow_Error) introduced in libraries_helper v0.4.19.
- FIX: Added missing 'import argparse' to support clean exit for version check.

## test_metadata_processor.py
- FIX: Updated Test 02 to provide both width and height to mock skipped record.
- RELIABILITY: Maintained Deep Asset Check for required test files.
- SYNC: Matched all logic with MetadataProcessor v0.3.23.
- FIX: Updated DB inserts to include 'perceptual_hash' so skipped records are correctly ignored.

## test_migrator.py
- Automatically initialized by release script.

## test_type_coverage.py
- Initial creation of Type Coverage suite (TDD Step 1: Red Phase).
- Added tests for Document (PDF, DOCX) metadata expectations.
- REFACTOR: Implemented Mocking for MediaInfo, Pillow, and Rawpy to test logic without real binary assets.
- FIX: Updated MediaInfo mock to correctly simulate track data structure (Fixes Duration failures).
- RESTORED: Added back individual test methods for all file types (3GP, AAC, FLAC, etc.) to ensure full coverage report.

