# ==============================================================================
# File: config_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation to manage dynamic settings loaded from a JSON file.",
    "Project name changed to \"file_organizer\" in descriptions.",
    "Added CLI argument parsing for --version to allow clean exit during health checks.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "CRITICAL FIX: Added optional `output_dir` to `__init__` to enable test environment isolation, resolving `AttributeError` in test suite setup.",
    "CRITICAL IMPORT FIX: Moved `argparse` and `sys` imports to the `if __name__ == '__main__':` block to prevent dynamic import crashes.",
    "FEATURE: Added FFMPEG_SETTINGS property to expose video transcoding configuration."
]
# ------------------------------------------------------------------------------
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# --- Project Dependencies ---
from version_util import print_version_info

class ConfigManager:
    """
    Loads and validates configuration from a JSON file.
    Provides structured access to paths, file groups, and organizational preferences.
    """
    DEFAULT_CONFIG_FILE = Path('./organizer_config.json')

    def __init__(self, config_path: Path = DEFAULT_CONFIG_FILE, output_dir: Optional[Path] = None):
        self.config_path = config_path
        self._data: Dict[str, Any] = self._load_config()
        
        # Store the output_dir internally, prioritizing the passed argument (for testing)
        if output_dir is not None:
            self._output_dir_override = output_dir
        else:
            self._output_dir_override = None

    def _load_config(self) -> Dict[str, Any]:
        """Loads and attempts to parse the JSON configuration file."""
        if not self.config_path.exists():
            print(f"Warning: Configuration file not found at {self.config_path}. Using default settings.")
            return {}
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding config file {self.config_path}: {e}. Using default settings.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred loading config: {e}. Using default settings.")
            return {}

    @property
    def SOURCE_DIR(self) -> Path:
        """Returns the source directory path, ensuring it's a Path object."""
        return Path(self._data.get('paths', {}).get('source_directory', './'))

    @property
    def OUTPUT_DIR(self) -> Path:
        """Returns the output directory path, ensuring it's a Path object."""
        # CRITICAL FIX: Return the override path if provided (for testing)
        if self._output_dir_override is not None:
            return self._output_dir_override
            
        return Path(self._data.get('paths', {}).get('output_directory', './organized_media_output'))

    @property
    def FILE_GROUPS(self) -> Dict[str, List[str]]:
        """Returns the file group definitions (e.g., 'IMAGE', 'VIDEO')."""
        return self._data.get('file_groups', {})

    @property
    def ORGANIZATION_PREFS(self) -> Dict[str, Any]:
        """Returns organizational preferences (e.g., date format, strategy)."""
        return self._data.get('organization', {})

    @property
    def FFMPEG_SETTINGS(self) -> Dict[str, Any]:
        """Returns FFmpeg configuration settings."""
        defaults = {
            "binary_path": None,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "preset": "ultrafast",
            "crf": "23",
            "extra_args": []
        }
        return self._data.get('ffmpeg', defaults)

if __name__ == "__main__":
    
    # CRITICAL IMPORT FIX: Move system/cli imports to the execution block
    import argparse 
    import sys

    parser = argparse.ArgumentParser(description="Config Manager for file_organizer: Loads and validates project settings from JSON.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Configuration Manager")
        sys.exit(0)
    else:
        # Example usage of the ConfigManager when run independently
        manager = ConfigManager()
        print(f"Loaded config from: {manager.config_path.resolve()}")
        print(f"Source Directory: {manager.SOURCE_DIR}")
        print(f"Output Directory: {manager.OUTPUT_DIR}")
        print("File Groups:", manager.FILE_GROUPS)
        print("FFmpeg Settings:", manager.FFMPEG_SETTINGS)