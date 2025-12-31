# ==============================================================================
# File: libraries_helper.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial creation of libraries_helper to encapsulate external library interactions.",
    "Added utility for reporting installed library versions.",
    "Added demo function for tqdm progress bar use.",
    "Added function for extracting EXIF metadata using Pillow (F04 implementation detail).",
    "Implemented CLI argument parsing for --version to allow clean exit during health checks (N06).",
    "FEATURE UPGRADE: Added hachoir detection to get_library_versions to support video metadata.",
    "FEATURE UPGRADE: Implemented extract_video_metadata using Hachoir (F04).",
    "BUG FIX: Added safety checks for Hachoir tag retrieval to prevent 'Metadata has no value' errors.",
    "RELIABILITY: Improved tag discovery to capture width, height, and bitrate more reliably.",
    "RELIABILITY: Added recursive metadata discovery to find nested stream tags (F04).",
    "BUG FIX: Fixed 'is_list' attribute error by using 'is_group' for recursion.",
    "BUG FIX: Fixed 'Data' object attribute error by using flat iteration for video metadata.",
    "BUG FIX: Fixed 'Data' object attribute error by using direct item access and exportPlaintext.",
    "EVOLUTION: Integrated MediaInfo for professional-grade and dynamic metadata extraction.",
    "CLI: Added --verbose argument to toggle between standard and exhaustive MediaInfo extraction.",
    "SYNC: Refined internal logic to support external calls for verbose vs standard metadata.",
    "BUG FIX: Changed file size extraction to return raw integers instead of formatted strings to prevent processing errors in Asset models."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.3.17
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, Optional
import time, datetime
import sys
import argparse
import importlib.metadata

# Attempt to import external dependencies
try:
    from pymediainfo import MediaInfo
    MEDIINFO_AVAILABLE = True
except ImportError:
    MEDIINFO_AVAILABLE = False
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    from hachoir.core import config as hachoir_config
    # Suppress internal Hachoir warnings to keep the console clean
    hachoir_config.quiet = True
    HACHOIR_AVAILABLE = True
except ImportError:
    HACHOIR_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
    OPENCV_VERSION = cv2.__version__
except ImportError:
    OPENCV_AVAILABLE = False
    OPENCV_VERSION = "Not Installed"

def get_library_versions():
    """Returns a dictionary of relevant library versions for the project."""
    versions = {}
    for lib in ['tqdm', 'Pillow', 'hachoir', 'opencv-python', 'pymediainfo']:
        try:
            versions[lib] = importlib.metadata.version(lib)
        except importlib.metadata.PackageNotFoundError:
            versions[lib] = "Not Installed"
    return versions

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from an image file using Pillow (F04)."""
    if not PIL_AVAILABLE:
        return {"error": "Pillow is not installed or available."}
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}
        
    metadata = {}
    try:
        with Image.open(file_path) as img:
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['format'] = img.format
            if img.getexif():
                metadata['exif_tags_count'] = len(dict(img.getexif()))
    # In libraries_helper.py -> extract_image_metadata
    except Exception as e:
        # Adding the specific phrase the test suite expects
        return {'error': f"Could not open or process image. Pillow error: {e}"}
    return metadata

def extract_video_metadata_verbose(file_path: Path) -> Dict[str, Any]:
    """
    Dynamic Metadata Scraper.
    Automatically captures 100% of available MediaInfo attributes.
    """
    results = {}
    
    # 1. OS-Level Stats
    try:
        stats = file_path.stat()
        # FIX: Return raw integer bytes for calculation logic
        results["OS_File_Size"] = stats.st_size
        # Readable string moved to separate key if needed for display later
        results["OS_File_Size_Readable"] = f"{stats.st_size / (1024**3):.2f} GiB"
        
        results["OS_Date_Created"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        results["OS_Date_Modified"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        results["OS_Error"] = str(e)

    try:
        media_info = MediaInfo.parse(str(file_path))
        
        for track in media_info.tracks:
            # Create a clean prefix for the track type
            track_type = track.track_type
            if track_type in ["Audio", "Text"]:
                prefix = f"{track_type}_{track.track_id or '0'}"
            else:
                prefix = track_type
            
            # Convert track object to a dictionary of all available data
            track_dict = track.to_data()
            
            for key, value in track_dict.items():
                if value is None or key in ['track_type', 'track_id']:
                    continue
                
                other_key = f"other_{key}"
                if other_key in track_dict and track_dict[other_key]:
                    display_value = track_dict[other_key][0]
                else:
                    display_value = value

                clean_key = f"{prefix}_{key.replace('_', ' ').title().replace(' ', '_')}"
                
                if clean_key not in results:
                    results[clean_key] = display_value

    except Exception as e:
        results["MediaInfo_Error"] = str(e)

    return results

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Standard MediaInfo extraction with hardcoded keys for consistent UI."""
    results = {}
    
    # OS Level Stats
    try:
        stats = file_path.stat()
        # FIX: Return raw integer bytes
        results["File Size"] = stats.st_size
        results["Created"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        results["Modified"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        results["OS_Error"] = str(e)

    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            if track.track_type == "General":
                results["Format"] = track.format
                results["Format_Info"] = track.format_info
                results["Commercial_Name"] = track.commercial_name
                results["Format_Profile"] = track.format_profile
                results["Duration"] = track.other_duration[0] if track.other_duration else "N/A"
                results["Overall_Bit_Rate_Mode"] = track.overall_bit_rate_mode
                results["Overall_Bit_Rate"] = f"{float(track.overall_bit_rate)/1000000:.1f} Mb/s" if track.overall_bit_rate else "N/A"
                results["Frame_Rate"] = f"{track.frame_rate} FPS"
                results["Recorded_Date"] = track.recorded_date

            elif track.track_type == "Video":
                results["Video_ID"] = track.track_id
                results["Video_Format"] = track.format
                results["Video_Commercial_Name"] = track.commercial_name
                results["Video_Bit_Rate_Mode"] = track.bit_rate_mode
                results["Video_Bit_Rate"] = f"{float(track.bit_rate)/1000000:.1f} Mb/s" if track.bit_rate else "N/A"
                results["Width"] = f"{track.width} pixels"
                results["Height"] = f"{track.height} pixels"
                results["Display_Aspect_Ratio"] = track.display_aspect_ratio
                results["Video_Frame_Rate_Mode"] = track.frame_rate_mode
                results["Video_Frame_Rate"] = f"{track.frame_rate} ({track.frame_rate_num}/{track.frame_rate_den}) FPS"
                results["Standard"] = track.standard
                results["Color_Space"] = track.color_space
                results["Chroma_Subsampling"] = track.chroma_subsampling
                results["Bit_Depth"] = f"{track.bit_depth} bits"
                results["Scan_Type"] = track.scan_type
                results["Scan_Order"] = track.scan_order
                results["Compression_Mode"] = track.compression_mode
                results["Bits_Pixel_Frame"] = track.bits__pixel_frame
                results["Time_Code_First_Frame"] = track.other_time_code_first_frame[0] if track.other_time_code_first_frame else "N/A"
                results["Time_Code_Source"] = track.time_code_source
                results["Stream_Size"] = track.other_stream_size[0] if track.other_stream_size else "N/A"
                results["Encoding_Settings"] = track.encoding_settings

            elif track.track_type == "Audio":
                t_id = f"Audio_{track.track_id or '1'}"
                results[f"{t_id}_Format"] = track.format
                results[f"{t_id}_Format_Settings"] = track.format_settings
                results[f"{t_id}_Muxing_Mode"] = track.muxing_mode
                results[f"{t_id}_Muxing_More"] = track.muxing_mode_more_info
                results[f"{t_id}_Bit_Rate_Mode"] = track.bit_rate_mode
                results[f"{t_id}_Bit_Rate"] = f"{int(track.bit_rate)/1000:,.0f} kb/s" if track.bit_rate else "N/A"
                results[f"{t_id}_Channels"] = f"{track.channel_s} channels"
                results[f"{t_id}_Sampling_Rate"] = f"{float(track.sampling_rate)/1000} kHz"
                results[f"{t_id}_Bit_Depth"] = f"{track.bit_depth} bits"
                results[f"{t_id}_Stream_Size"] = track.other_stream_size[0] if track.other_stream_size else "N/A"

    except Exception as e:
        results["MediaInfo_Error"] = str(e)

    return results

def get_video_metadata(file_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """
    Unified entry point for metadata extraction.
    Toggles between standard (clean) and verbose (exhaustive) output.
    """
    if verbose:
        return extract_video_metadata_verbose(file_path)
    return extract_video_metadata(file_path)

def demo_tqdm_progress(iterable: Any = 100, desc: str = "Testing Progress Bar"):
    """
    A demo function to verify tqdm is working. 
    Updated to match test suite expectations for output and signature.
    """
    if not TQDM_AVAILABLE:
        print("tqdm is not available.")
        return
    
    # If passed an integer, create a range; otherwise use the iterable directly
    items = range(iterable) if isinstance(iterable, int) else iterable
    
    # Ensure tqdm outputs to sys.stdout so the test mock can capture it
    for _ in tqdm(items, desc=desc, file=sys.stdout):
        time.sleep(0.01)
    
    # CRITICAL: This print statement is required by Test 02
    print("TQDM Demo Complete")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Library Helper Module for File Organizer.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--verbose', action='store_true', help='Use exhaustive metadata extraction.')
    parser.add_argument('file', nargs='?', help='Path to a video file for metadata extraction demo.')
    args = parser.parse_args()

    if args.version:
        project_root = Path(__file__).resolve().parent
        if str(project_root) not in sys.path: sys.path.append(str(project_root))
        try:
            from version_util import print_version_info
            print_version_info(__file__, "Library Helper Utilities")
            sys.exit(0)
        except ImportError: sys.exit(1)
            
    print("Library Helper Status:", get_library_versions())

    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            print(f"\n--- Metadata Demo for: {file_path.name} ---")
            metadata = get_video_metadata(file_path, verbose=args.verbose)
            
            for key, value in sorted(metadata.items()):
                print(f"{key:25}: {value}")
        else:
            print(f"\nError: File not found: {args.file}")