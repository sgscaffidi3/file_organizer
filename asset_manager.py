# ==============================================================================
# File: asset_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [5]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.2.5
# ------------------------------------------------------------------------------
from pathlib import Path
import sys
import argparse
import json
from video_asset import VideoAsset
from libraries_helper import get_video_metadata, calculate_image_hash
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
        
        # Router logic: Choose the correct model
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

        # Calculate Perceptual Hash for Images
        p_hash = None
        if group == 'IMAGE':
            p_hash = calculate_image_hash(file_path)

        update_sql = """
        UPDATE MediaContent SET
            date_best = ?, width = ?, height = ?, duration = ?,
            bitrate = ?, video_codec = ?, perceptual_hash = ?, extended_metadata = ?
        WHERE content_hash = ?;
        """
        # Safely handle attributes that might not exist on all models
        params = (
            asset.recorded_date,
            getattr(asset, 'width', None),
            getattr(asset, 'height', None),
            getattr(asset, 'duration', None),
            getattr(asset, 'bitrate', None if group != 'AUDIO' else asset.bitrate),
            getattr(asset, 'video_codec', None),
            p_hash,
            asset.get_full_json(),
            content_hash
        )
        self.db.execute_query(update_sql, params)

if __name__ == "__main__":
    from version_util import print_version_info
    parser = argparse.ArgumentParser(description="Asset Manager Conductor")
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--verbose', action='store_true', help='Store exhaustive metadata blobs.')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        print_version_info(__file__, "Asset Manager")
        sys.exit(0)