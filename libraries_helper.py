# ==============================================================================
# File: libraries_helper.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
_PATCH_VERSION = 13
# Version: 0.3.13
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
    "BUG FIX: Fixed 'Data' object attribute error by using direct item access and exportPlaintext."
]
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
    except Exception as e:
        return {"error": f"Pillow error: {e}"}
    return metadata
def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    results = {}
    
    # OS Level Stats
    stats = file_path.stat()
    results["File Size"] = f"{stats.st_size / (1024**3):.2f} GiB"
    results["Created"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
    results["Modified"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            # --- GENERAL ---
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

            # --- VIDEO ---
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

            # --- AUDIO ---
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
'''
def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Combines Hachoir and OpenCV to ensure resolution is never missing."""
    results = {}
    
    # 1. Use OpenCV for the 'Physical' data (Width, Height, FPS)
    if OPENCV_AVAILABLE:
        try:
            cap = cv2.VideoCapture(str(file_path))
            if cap.isOpened():
                results["Width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                results["Height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    results["FPS"] = round(fps, 2)
                
                # --- NEW: Codec Extraction ---
                fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
                # Convert the integer to a 4-character string (e.g., 'XVID')
                fourcc_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
                results["Codec"] = fourcc_str.strip()
                
                # Get total frame count (useful for deep analysis)
                results["Frame Count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                cap.release()
        except Exception as e:
            results["OpenCV_Error"] = str(e)

    # 2. Use Hachoir for the 'Header' data (Duration, Bitrate, MIME)
    try:
        parser = createParser(str(file_path))
        if parser:
            with parser:
                meta = extractMetadata(parser)
                if meta:
                    for line in meta.exportPlaintext():
                        if ":" in line:
                            k, v = line.lstrip("- ").split(":", 1)
                            key, val = k.strip(), v.strip()
                            # Avoid overwriting the accurate CV2 data
                            if key not in ["Image width", "Image height", "Frame rate"]:
                                results[key] = val
    except Exception as e:
        results["Hachoir_Status"] = f"Header read failed: {e}"

    return results
    '''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Library Helper Module for File Organizer.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
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