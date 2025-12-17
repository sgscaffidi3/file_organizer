# ==============================================================================
# File: README.md
# Version: 0.3.5
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the README file with project description and setup instructions.
# 2. Updated documentation to reflect the new JSON-based configuration managed by `config_manager.py`.
# 3. Project name changed from \"Personal Media Organizer and Deduplicator\" to \"File Organizer\".
# 4. Updated version to 0.3.4, synchronized changelog, and clarified dependency and output path details.
# 5. Updated version to 0.3.5; changes are up-to-date with project version 0.3.26. Added tqdm to dependencies and included information about the test runner.
# ------------------------------------------------------------------------------

# 🗄️ File Organizer

This is a high-performance Python utility designed to catalog, deduplicate, and organize vast file collections (images, videos, documents) stored across multiple locations. It is built for **safety** and **scalability**, ensuring original files are never modified and utilizing database persistence to handle multi-terabyte data sets efficiently.

The project follows a modular, pipeline-based approach: Scan -> Process Metadata -> Deduplicate/Decide -> Migrate/Report.

## 🚀 Getting Started (Setup)

### 1. Prerequisites

* Python 3.8+
* Git (for cloning the repository)

### 2. Installation

1.  **Clone the Repository:**
    ```bash
    git clone [Your Repository URL Here]
    cd file_organizer
    ```

2.  **Set up the Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    .\venv\Scripts\activate   # On Windows
    ```

3.  **Install Dependencies:**
    Dependencies include libraries for metadata processing and UI feedback, such as **Pillow** (for images), **tqdm** (for progress bars), and potentially **MoviePy** (for video).
    ```bash
    pip install -r requirements.txt 
    ```

### 3. Configuration (Critical Step!)

The dynamic settings for the project are managed via a **JSON file**.

1.  **Locate the Configuration File:**
    * Find the file named `organizer_config.json` in the root directory.

2.  **Update Paths:**
    * Under the `"paths"` section, set **`"source_directory"`** to the root of your media collection.
    * Adjust **`"output_directory"`** for the final organized structure.

3.  **Review Preferences:**
    * Review the `"file_groups"` and `"organization"` settings to match your desired preferences.

### 4. Final Organized Path Format

The final path is deterministically calculated as:
`OUTPUT_DIR/YEAR/MONTH/HASH_FILEID.EXT`
*(Example: organized_media_output/2025/11/a4b2c3d4e5f6_12345.jpg)*

### 5. Initialization

Before running the full scan, you must initialize the database schema:

```bash
python database_manager.py --init
```
### 6. Running Tests
To verify the integrity of the project and your environment, run the integrated test suite:

Bash

python test/test_all.py
This will run all unit tests and generate a Detailed Test Report with a formatted summary table of PASS/FAIL/ERROR statuses for every component.