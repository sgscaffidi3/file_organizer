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

class AssetManager:
    """
    Coordinates the scanning of files, extraction of metadata, 
    and storage in the hybrid database schema.
    """
    def __init__(self, db: DatabaseManager, verbose: bool = False):
        self.db = db
        self.verbose = verbose

    def process_file(self, file_path: Path, content_hash: str):
        """
        Extracts metadata and updates the MediaContent table 
        using the VideoAsset hybrid model.
        """
        # 1. Extract metadata from file
        raw_meta = get_video_metadata(file_path, verbose=self.verbose)
        
        # 2. Wrap in VideoAsset model (Hybrid logic happens here)
        asset = VideoAsset(file_path, raw_meta)
        
        # 3. Update the Database
        update_sql = """
        UPDATE MediaContent SET
            date_best = ?,
            width = ?,
            height = ?,
            duration = ?,
            bitrate = ?,
            video_codec = ?,
            extended_metadata = ?
        WHERE content_hash = ?;
        """
        params = (
            asset.recorded_date,
            asset.width,
            asset.height,
            asset.duration,
            asset.video_bitrate,
            asset.video_codec,
            asset.get_full_json(), # The JSON Backpack
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