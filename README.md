# ==============================================================================
# File: README.md
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation of the README file with project description and setup instructions.
# 2. Updated documentation to reflect the new JSON-based configuration managed by `config_manager.py`.
# 3. Project name changed from "Personal Media Organizer and Deduplicator" to "File Organizer".
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
    *(Currently, dependencies are minimal, but this will be updated in the next step to include libraries like Pillow for metadata.)*
    ```bash
    pip install -r requirements.txt 
    ```

### 3. Configuration (Critical Step!)

The dynamic settings for the project are managed via a **JSON file**.

1.  **Locate the Configuration File:**
    * Find the file named `organizer_config.json` in the root directory.

2.  **Update Paths:**
    * Under the `"paths"` section, set **`"source_directory"`** to the root of your media collection (e.g., `C:/family/dad/personal_media`).
    * Adjust **`"output_directory"`** if you want the final organized structure stored elsewhere.

3.  **Review Preferences:**
    * Review the `"file_groups"` and `"organization"` settings to match your desired organizational preferences.

### 4. Initialization

Before running the full scan, you must initialize the database schema. You can use the standalone execution command:

```bash
python database_manager.py --init