import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# --- PROJECT METADATA ---
_MAJOR_VERSION = 0
_MINOR_VERSION = 1

_CHANGELOG_ENTRIES = [
    "Initial creation of VideoAsset class with Hybrid Metadata Support.",
    "Implemented explicit attribute mapping for core video/audio metrics.",
    "Added JSON 'backpack' for exhaustive metadata storage (Verbose Strategy).",
    "Added aspect ratio calculation logic for 4:3 and 16:9 detection.",
    "Standardized CLI support for --version, --help, and independent testing.",
    "Synchronized versioning logic with version_util and automated patch numbering."
]

_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.6

class VideoAsset:
    """
    Represents a video file with a hybrid metadata model.
    Core fields are promoted to attributes; exhaustive data is stored in a JSON blob.
    """
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        # --- OS & File Identity ---
        self.path = file_path
        self.name = file_path.name
        self.size = meta.get('OS_File_Size') or meta.get('File Size', "Unknown")
        self.created = meta.get('OS_Date_Created') or meta.get('Created', "Unknown")
        self.modified = meta.get('OS_Date_Modified') or meta.get('Modified', "Unknown")
        
        # --- Core Video Specs ---
        self.format = meta.get('Format', "Unknown")
        self.duration = meta.get('Duration', "00:00:00")
        self.recorded_date = meta.get('Recorded_Date', "Unknown")
        self.video_codec = meta.get('Video_Format') or meta.get('Video_Codec', "Unknown")
        self.video_bitrate = meta.get('Video_Bit_Rate', "Unknown")
        
        # Extract numeric values for width/height to support math
        self.width = self._clean_numeric(meta.get('Width') or meta.get('Resolution', "0").split('x')[0])
        self.height = self._clean_numeric(meta.get('Height') or meta.get('Resolution', "0").split('x')[-1])
        self.standard = meta.get('Standard', "N/A")
        
        # --- Aspect Ratio Handling ---
        self.aspect_decimal = meta.get('Display_Aspect_Ratio', "0.0")
        self.aspect_ratio = self._calculate_aspect_ratio()
        
        # --- Audio Specs ---
        self.audio_codec = meta.get('Audio_0-0_Format') or meta.get('Audio_1_Format', "Unknown")
        self.audio_bitrate = meta.get('Audio_0-0_Bit_Rate') or meta.get('Audio_1_Bit_Rate', "Unknown")
        self.audio_channels = meta.get('Audio_0-0_Channels') or meta.get('Audio_1_Channels', "Unknown")

        # --- The JSON "Backpack" ---
        self.extended_metadata = meta 

    def _clean_numeric(self, value: Any) -> int:
        """Strip units (like 'pixels') and return a clean integer."""
        try:
            return int(''.join(filter(str.isdigit, str(value))))
        except (ValueError, TypeError):
            return 0

    def _calculate_aspect_ratio(self) -> str:
        """Determines if the video is 4:3, 16:9, or other based on dimensions."""
        if self.width == 0 or self.height == 0: 
            return "Unknown"
        
        ratio = self.width / self.height
        if abs(ratio - 1.333) < 0.01: return "4:3"
        if abs(ratio - 1.777) < 0.01: return "16:9"
        return f"{self.width}:{self.height}"

    def __repr__(self):
        return f"<VideoAsset: {self.name} | {self.format} | {self.aspect_ratio}>"

    def get_full_json(self) -> str:
        """Returns the complete metadata dictionary as a JSON string for DB storage."""
        return json.dumps(self.extended_metadata, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VideoAsset Model: Represents a media file with metadata.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version info.')
    parser.add_argument('--test', action='store_true', help='Run a self-test with dummy data.')
    args = parser.parse_args()

    if args.version:
        # Add project root to path to ensure version_util is found
        project_root = Path(__file__).resolve().parent
        if str(project_root) not in sys.path: sys.path.append(str(project_root))
        
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Video Asset Data Model")
            sys.exit(0)
        except ImportError:
            # Fallback if version_util isn't in this directory
            print(f"VideoAsset Model v{_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
            sys.exit(0)

    if args.test:
        print("--- Running VideoAsset Self-Test ---")
        dummy_meta = {
            "Format": "AVI",
            "Width": "720 pixels",
            "Height": "480 pixels",
            "Video_Format": "DV",
            "Recorded_Date": "2003-06-15",
            "Audio_0-0_Format": "PCM"
        }
        asset = VideoAsset(Path("test_video.avi"), dummy_meta)
        print(f"Asset Created: {asset}")
        print(f"Detected Ratio: {asset.aspect_ratio}")
        print(f"Numeric Width: {asset.width}")
        print("\nJSON Backpack Preview (First 50 chars):")
        print(asset.get_full_json()[:1500] + "...")