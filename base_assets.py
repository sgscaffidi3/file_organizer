# ==============================================================================
# File: base_assets.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 2
_CHANGELOG_ENTRIES = [
    "Initial creation of base_assets module with class inheritance.",
    "Implemented GenericFileAsset, AudioAsset, DocumentAsset, and ImageAsset.",
    "Standardized JSON 'backpack' across all asset types.",
    "Added project-standard versioning and CLI --version support.",
    "Added _clean_numeric helper for ImageAsset dimension scrubbing.",
    "FEATURE: Added get_friendly_size() for dynamic unit scaling (B, KiB, MiB, GiB).",
    "FEATURE: Expanded AudioAsset to capture Artist, Album, Song, VBR, and technical specs.",
    "BUG FIX: Added 'camera' attribute to ImageAsset to capture Make/Model metadata (Fixes test_assets error)."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

class GenericFileAsset:
    """Base model for all files; handles file identity and the JSON backpack."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        self.path = file_path
        self.name = file_path.name
        # Store the raw bytes for calculations
        # Helper ensures we handle both raw ints and string representations cleanly if needed, 
        # though upstream should provide ints.
        raw_size = meta.get('OS_File_Size') or meta.get('File Size', 0)
        try:
            self.size_bytes = int(raw_size)
        except (ValueError, TypeError):
            self.size_bytes = 0
            
        self.recorded_date = meta.get('Recorded_Date') or meta.get('OS_Date_Created', "Unknown")
        self.extended_metadata = meta

    def get_friendly_size(self) -> str:
        """Returns the file size in the most appropriate unit (B, KiB, MiB, GiB, TiB)."""
        size = float(self.size_bytes)
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PiB"

    def get_full_json(self) -> str:
        """Returns the exhaustive metadata dictionary as a JSON string."""
        return json.dumps(self.extended_metadata, indent=4)

class AudioAsset(GenericFileAsset):
    """Asset model for audio files (MP3, WAV, FLAC, WMA, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        
        # Technical Metadata
        self.duration = meta.get('Duration') or meta.get('duration', "00:00:00")
        self.bitrate = meta.get('Bit_Rate') or meta.get('Audio_Bit_Rate') or meta.get('Bit Rate', "Unknown")
        self.sample_rate = meta.get('Sampling_Rate') or meta.get('Sample Rate', "Unknown")
        self.codec = meta.get('Format') or meta.get('Audio_Codec_List') or "Unknown"
        self.bitrate_mode = meta.get('Bit_Rate_Mode') or "CBR" # Default to CBR if not specified
        
        # Tag Metadata
        self.song = meta.get('Title') or meta.get('Track_Name') or self.name
        self.artist = meta.get('Artist') or meta.get('Performer') or "Unknown Artist"
        self.album = meta.get('Album') or "Unknown Album"
        self.track_num = meta.get('Track_Position') or meta.get('Track_Number') or "0"
        self.genre = meta.get('Genre', "Unknown")

class ImageAsset(GenericFileAsset):
    """Asset model for images (JPG, PNG, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        self.width = self._clean_numeric(meta.get('Width', 0))
        self.height = self._clean_numeric(meta.get('Height', 0))
        # Captures camera info for detailed reporting
        self.camera = meta.get('Make') or meta.get('Model') or "Unknown Camera"

    def _clean_numeric(self, value: Any) -> int:
        try:
            return int(''.join(filter(str.isdigit, str(value))))
        except (ValueError, TypeError):
            return 0

class DocumentAsset(GenericFileAsset):
    """Asset model for documents (PDF, DOCX, etc.)."""
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        super().__init__(file_path, meta)
        self.pages = meta.get('Page_Count', 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Base Asset Models")
    parser.add_argument('-v', '--version', action='store_true')
    args = parser.parse_args()

    if args.version:
        print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)