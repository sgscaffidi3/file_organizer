import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# --- PROJECT METADATA ---
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of base_assets module with class inheritance.",
    "Implemented GenericFileAsset, AudioAsset, DocumentAsset, and ImageAsset.",
    "Standardized JSON 'backpack' across all asset types.",
    "Added project-standard versioning and CLI --version support.",
    "Added _clean_numeric helper for ImageAsset dimension scrubbing."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.5

class GenericFileAsset:
    """Base model for all files; handles file identity and the JSON backpack."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        self.path = file_path
        self.name = file_path.name
        self.size = meta.get('OS_File_Size') or meta.get('File Size', 0)
        self.recorded_date = meta.get('Recorded_Date') or meta.get('OS_Date_Created', "Unknown")
        self.extended_metadata = meta

    def get_full_json(self) -> str:
        """Returns the exhaustive metadata dictionary as a JSON string."""
        return json.dumps(self.extended_metadata, indent=4)

class AudioAsset(GenericFileAsset):
    """Asset model for audio files (MP3, WAV, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        self.duration = meta.get('Duration', "00:00:00")
        self.bitrate = meta.get('Audio_Bit_Rate') or meta.get('Bit Rate', "Unknown")
        self.channels = meta.get('Audio_Channels', "Unknown")

class ImageAsset(GenericFileAsset):
    """Asset model for images (JPG, PNG, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        self.width = self._clean_numeric(meta.get('Width', 0))
        self.height = self._clean_numeric(meta.get('Height', 0))
        self.camera = meta.get('Camera_Model') or meta.get('Make', "Unknown")

    def _clean_numeric(self, value: Any) -> int:
        """Strip units (like 'pixels') and return a clean integer."""
        try:
            return int(''.join(filter(str.isdigit, str(value))))
        except (ValueError, TypeError):
            return 0

class DocumentAsset(GenericFileAsset):
    """Asset model for documents (PDF, DOCX, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        self.pages = meta.get('Page_Count', 1)
        self.author = meta.get('Author', "Unknown")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Base Asset Models")
    parser.add_argument('-v', '--version', action='store_true')
    args = parser.parse_args()

    if args.version:
        print(f"Base Assets v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)