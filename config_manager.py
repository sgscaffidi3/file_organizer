# ==============================================================================
# File: config_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
# Version: <Automatically calculated via _MAJOR_VERSION._MINOR_VERSION.PATCH>
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Initial creation to manage dynamic settings loaded from a JSON file.
# 2. Project name changed to "file_organizer" in descriptions.
# ------------------------------------------------------------------------------
import json
from pathlib import Path
from typing import Dict, Any, List
import argparse
from version_util import print_version_info

class ConfigManager:
    """
    Loads and validates configuration from a JSON file.
    Provides structured access to paths, file groups, and organizational preferences.
    """
    DEFAULT_CONFIG_FILE = Path('./organizer_config.json')

    def __init__(self, config_path: Path = DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        self._data: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads and attempts to parse the JSON configuration file."""
        if not self.config_path.exists():
            print(f"Error: Configuration file not found at {self.config_path}. Using default empty settings.")
            return {
                "paths": {}, 
                "organization": {}, 
                "file_groups": {}
            }
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format in {self.config_path}: {e}")
            return {
                "paths": {}, 
                "organization": {}, 
                "file_groups": {}
            }

    @property
    def SOURCE_DIR(self) -> Path:
        """Returns the source directory path, ensuring it's a Path object."""
        # Defaults to the current directory if not found in JSON
        return Path(self._data.get('paths', {}).get('source_directory', './'))

    @property
    def OUTPUT_DIR(self) -> Path:
        """Returns the output directory path, ensuring it's a Path object."""
        return Path(self._data.get('paths', {}).get('output_directory', './organized_media_output'))

    @property
    def FILE_GROUPS(self) -> Dict[str, List[str]]:
        """Returns the file group definitions (e.g., 'IMAGE', 'VIDEO')."""
        return self._data.get('file_groups', {})

    @property
    def ORGANIZATION_PREFS(self) -> Dict[str, Any]:
        """Returns organizational preferences (e.g., date format, strategy)."""
        return self._data.get('organization', {})

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Config Manager for file_organizer: Loads and validates project settings from JSON.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Configuration Manager")
    else:
        # Example usage of the ConfigManager when run independently
        manager = ConfigManager()
        print(f"Loaded config from: {manager.config_path.resolve()}")
        print(f"Source Directory: {manager.SOURCE_DIR}")
        print(f"Output Directory: {manager.OUTPUT_DIR}")
        print(f"Organization Strategy: {manager.ORGANIZATION_PREFS.get('deduplication_strategy', 'N/A')}")