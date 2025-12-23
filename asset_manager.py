# ==============================================================================
# File: asset_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Initial creation of AssetManager to coordinate asset processing.",
    "Integrated libraries_helper for metadata extraction.",
    "Implemented the Hybrid Metadata storage strategy into the database.",
    "Added support for --verbose flag to trigger exhaustive MediaInfo scans."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.1.4
# ------------------------------------------------------------------------------
from pathlib import Path
import sys
import argparse
import json
from video_asset import VideoAsset
from libraries_helper import get_video_metadata
from database_manager import DatabaseManager
from base_assets import GenericFileAsset, AudioAsset, ImageAsset, DocumentAsset

class AssetManager:
    """
    Coordinates the scanning of files, extraction of metadata, 
    and storage in the hybrid database schema.
    """
    def __init__(self, db: DatabaseManager, verbose: bool = False):
        self.db = db
        self.verbose = verbose

    def process_file(self, file_path: Path, content_hash: str, group: str = 'VIDEO'):
        raw_meta = get_video_metadata(file_path, verbose=self.verbose)
        
        # Simple Router logic
        if group == 'VIDEO':
            asset = VideoAsset(file_path, raw_meta)
        elif group == 'IMAGE':
            asset = ImageAsset(file_path, raw_meta)
        elif group == 'AUDIO':
            asset = AudioAsset(file_path, raw_meta)
        elif group == 'DOCUMENT':
            asset = DocumentAsset(file_path, raw_meta)
        else:
            asset = GenericFileAsset(file_path, raw_meta)

        # Standard SQL Update (Using the common interface)
        update_sql = """
        UPDATE MediaContent SET
            date_best = ?, width = ?, height = ?, duration = ?, 
            bitrate = ?, video_codec = ?, extended_metadata = ?
        WHERE content_hash = ?;
        """
        
        # Use getattr to safely handle missing attributes for non-video files
        params = (
            asset.recorded_date,
            getattr(asset, 'width', None),
            getattr(asset, 'height', None),
            getattr(asset, 'duration', None),
            getattr(asset, 'bitrate', None),
            getattr(asset, 'video_codec', None),
            asset.get_full_json(),
            content_hash
        )
        self.db.execute_query(update_sql, params)

if __name__ == "__main__":
    from version_util import print_version_info
    parser = argparse.ArgumentParser(description="Asset Manager Conductor")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--verbose', action='store_true', help='Store exhaustive metadata blobs.')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Asset Manager")
        sys.exit(0)