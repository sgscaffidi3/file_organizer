# ==============================================================================
# File: video_asset.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [6]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.2.6
# ------------------------------------------------------------------------------
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

# Project Dependencies
from base_assets import GenericFileAsset

class VideoAsset(GenericFileAsset):
    """
    Specialized asset model for Video files.
    Inherits get_friendly_size() and the JSON backpack from GenericFileAsset.
    """
    def __init__(self, file_path: Path, meta: Dict[str, Any]):
        # Initialize the base class to set up size_bytes, recorded_date, and backpack
        super().__init__(file_path, meta)
        
        # --- File Identity & Dates (Restored) ---
        self.format = meta.get('Format', "Unknown")
        self.created = meta.get('OS_Date_Created') or meta.get('Created', "Unknown")
        self.modified = meta.get('OS_Date_Modified') or meta.get('Modified', "Unknown")

        # --- Core Video Specs (Restored) ---
        self.width = self._clean_numeric(meta.get('Width') or meta.get('Resolution', "0").split('x')[0])
        self.height = self._clean_numeric(meta.get('Height') or meta.get('Resolution', "0").split('x')[-1])
        self.duration = meta.get('Duration', "00:00:00")
        self.video_codec = meta.get('Video_Format') or meta.get('Video_Codec', "Unknown")
        self.video_bitrate = meta.get('Video_Bit_Rate', "Unknown")
        self.frame_rate = meta.get('Frame_Rate', "Unknown")
        self.standard = meta.get('Standard', "N/A")

        # --- Aspect Ratio Handling (Restored) ---
        self.aspect_decimal = meta.get('Display_Aspect_Ratio', "0.0")
        self.aspect_ratio = self._calculate_aspect_ratio()
        
        # --- Audio Specs (Restored) ---
        self.audio_codec = meta.get('Audio_0-0_Format') or meta.get('Audio_1_Format', "Unknown")
        self.audio_bitrate = meta.get('Audio_0-0_Bit_Rate') or meta.get('Audio_1_Bit_Rate', "Unknown")
        self.audio_channels = meta.get('Audio_0-0_Channels') or meta.get('Audio_1_Channels', "Unknown")

    def _clean_numeric(self, value: Any) -> int:
        """Helper to ensure dimensions are clean integers."""
        try:
            if isinstance(value, str):
                return int(''.join(filter(str.isdigit, value)))
            return int(value)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Asset Model")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        print(f"Version: {_MAJOR_VERSION}.{_MINOR_VERSION}.{_PATCH_VERSION}")
        sys.exit(0)

    if args.test:
        dummy_meta = {
            "OS_File_Size": 1024 * 1024 * 5, # 5 MiB
            "Format": "AVI",
            "Width": "720",
            "Height": "480",
            "Duration": "00:01:30"
        }
        asset = VideoAsset(Path("test.avi"), dummy_meta)
        print(f"Created: {asset}")
        print(f"Friendly Size: {asset.get_friendly_size()}")