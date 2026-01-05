# ==============================================================================
# File: libraries_helper.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 5
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
    "BUG FIX: Changed file size extraction to return raw integers instead of formatted strings to prevent processing errors in Asset models.",
    "FEATURE UPGRADE: Added specialized extractors for PDF, Office, Ebooks, and Archives.",
    "FEATURE UPGRADE: Added router logic to dispatch to specific extractors based on extension.",
    "FEATURE UPGRADE: Added support for RAW images, SVG, and PPTX metadata extraction.",
    "FEATURE UPGRADE: Added 'pillow-heif' registration for .HEIC support.",
    "DATA INTEGRITY: Updated MediaInfo extractor to return RAW INTEGERS for BitRate, Duration, Width, Height (Fixes sorting/reporting).",
    "ROBUSTNESS: Added automatic fallback to MediaInfo for HEIC files if Pillow/pillow-heif fails."
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.5.23
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Dict, Any, Optional
import time, datetime
import sys
import argparse
import importlib.metadata
import zipfile
import tarfile
import xml.etree.ElementTree as ET

# --- Dependency Checks ---
try:
    from pymediainfo import MediaInfo
    MEDIINFO_AVAILABLE = True
except ImportError:
    MEDIINFO_AVAILABLE = False

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
    # Try HEIC support
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        HEIC_AVAILABLE = True
    except ImportError:
        HEIC_AVAILABLE = False
except ImportError:
    PIL_AVAILABLE = False
    HEIC_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pptx
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from ebooklib import epub
    EBOOK_AVAILABLE = True
except ImportError:
    EBOOK_AVAILABLE = False

# --- Version Reporting ---
def get_library_versions():
    """Returns a dictionary of relevant library versions for the project."""
    libs = ['tqdm', 'Pillow', 'pillow-heif', 'pymediainfo', 'PyPDF2', 'python-docx', 'python-pptx', 'openpyxl', 'EbookLib']
    versions = {}
    for lib in libs:
        try:
            versions[lib] = importlib.metadata.version(lib)
        except importlib.metadata.PackageNotFoundError:
            versions[lib] = "Not Installed"
    return versions

# --- Specialized Extractors ---

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from an image file using Pillow."""
    if not PIL_AVAILABLE:
        return {"Pillow_Error": "Pillow library not installed"}
    
    metadata = {}
    try:
        with Image.open(file_path) as img:
            metadata['Width'] = img.width
            metadata['Height'] = img.height
            metadata['Format'] = img.format
            
            # Basic EXIF
            exif_raw = img.getexif()
            if exif_raw:
                metadata['Exif_Tags_Count'] = len(exif_raw)
                for tag_id, value in exif_raw.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'Make': metadata['Make'] = str(value)
                    if tag == 'Model': metadata['Model'] = str(value)
                    if tag == 'DateTime': metadata['Recorded_Date'] = str(value)

    except Exception as e:
        return {"Pillow_Error": str(e)}
    return metadata

def extract_svg_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts dimensions from SVG XML."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        meta = {}
        # Simple extraction, SVG units can be complex (cm, mm, px, %)
        if 'width' in root.attrib: meta['Width'] = root.attrib['width']
        if 'height' in root.attrib: meta['Height'] = root.attrib['height']
        return meta
    except Exception as e:
        return {"SVG_Error": str(e)}

def extract_pdf_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts page count and info from PDFs."""
    if not PDF_AVAILABLE:
        return {"PDF_Error": "PyPDF2 library not installed"}
    
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            metadata['Page_Count'] = len(reader.pages)
            if reader.metadata:
                if reader.metadata.author: metadata['Author'] = reader.metadata.author
                if reader.metadata.title: metadata['Title'] = reader.metadata.title
    except Exception as e:
        return {"PDF_Error": str(e)}
    return metadata

def extract_docx_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from Word documents."""
    if not DOCX_AVAILABLE:
        return {"Office_Error": "python-docx library not installed"}
    
    metadata = {}
    try:
        doc = docx.Document(file_path)
        props = doc.core_properties
        if props.author: metadata['Author'] = props.author
        if props.title: metadata['Title'] = props.title
        
        words = 0
        for para in doc.paragraphs:
            words += len(para.text.split())
        metadata['Word_Count'] = words
    except Exception as e:
        return {"Office_Error": str(e)}
    return metadata

def extract_pptx_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from PowerPoint presentations."""
    if not PPTX_AVAILABLE:
        return {"Office_Error": "python-pptx library not installed"}
    
    metadata = {}
    try:
        prs = pptx.Presentation(file_path)
        if prs.core_properties.author: metadata['Author'] = prs.core_properties.author
        if prs.core_properties.title: metadata['Title'] = prs.core_properties.title
        metadata['Slide_Count'] = len(prs.slides)
    except Exception as e:
        return {"Office_Error": str(e)}
    return metadata

def extract_xlsx_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from Excel spreadsheets."""
    if not XLSX_AVAILABLE:
        return {"Office_Error": "openpyxl library not installed"}
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        props = wb.properties
        meta = {}
        if props.creator: meta['Author'] = props.creator
        if props.title: meta['Title'] = props.title
        wb.close()
        return meta
    except Exception as e:
        return {"Office_Error": str(e)}

def extract_archive_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts file counts from ZIP/TAR archives."""
    meta = {}
    try:
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as z:
                meta['File_Count'] = len(z.namelist())
                meta['Archive_Type'] = "ZIP"
        elif tarfile.is_tarfile(file_path):
            with tarfile.open(file_path, 'r') as t:
                meta['File_Count'] = len(t.getnames())
                meta['Archive_Type'] = "TAR"
        else:
            return {"Archive_Error": "Unsupported or Corrupt Archive"}
    except Exception as e:
        return {"Archive_Error": str(e)}
    return meta

def extract_ebook_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts metadata from EPUBs."""
    if not EBOOK_AVAILABLE:
        return {"Ebook_Error": "EbookLib not installed"}
    try:
        book = epub.read_epub(str(file_path)) 
        meta = {}
        if book.get_metadata('DC', 'title'):
            meta['Title'] = book.get_metadata('DC', 'title')[0][0]
        if book.get_metadata('DC', 'creator'):
            meta['Author'] = book.get_metadata('DC', 'creator')[0][0]
        return meta
    except Exception as e:
        return {"Ebook_Error": str(e)}


# --- Main Router ---

def get_video_metadata(file_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """
    Unified entry point. Dispatches to specialized extractors based on extension,
    falling back to MediaInfo for AV/Unknown types.
    """
    results = {}
    
    # 1. Basic OS Stats
    try:
        stats = file_path.stat()
        results["File Size"] = stats.st_size
        results["Created"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        results["Modified"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        results["OS_Error"] = str(e)

    ext = file_path.suffix.lower()

    # 2. Dispatch Logic
    specialized_meta = {}
    
    # HEIC Specific Handling (Attempt Pillow/HEIF first, Fallback to MediaInfo)
    if ext in ['.heic', '.heif']:
        specialized_meta = extract_image_metadata(file_path)
        # If Pillow failed (e.g. library missing or header issue), use MediaInfo
        if 'Pillow_Error' in specialized_meta:
            # Drop the pillow error and try MediaInfo
            specialized_meta = extract_video_metadata(file_path)
            # Add a flag to indicate source
            specialized_meta['_Source'] = 'MediaInfo (HEIC Fallback)'

    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.cr2', '.nef', '.arw', '.dng', '.orf']:
        specialized_meta = extract_image_metadata(file_path)
    
    elif ext == '.svg':
        specialized_meta = extract_svg_metadata(file_path)
    
    elif ext in ['.pdf']:
        specialized_meta = extract_pdf_metadata(file_path)
        
    elif ext in ['.docx', '.doc']:
        specialized_meta = extract_docx_metadata(file_path)
    
    elif ext in ['.pptx']:
        specialized_meta = extract_pptx_metadata(file_path)
        
    elif ext in ['.xlsx', '.xls']:
        specialized_meta = extract_xlsx_metadata(file_path)
        
    elif ext in ['.epub', '.mobi']:
        specialized_meta = extract_ebook_metadata(file_path)
        
    elif ext in ['.zip', '.tar', '.gz', '.7z', '.rar']:
        specialized_meta = extract_archive_metadata(file_path)
        
    else:
        # Fallback to MediaInfo for Audio/Video/Unknown
        if verbose:
            specialized_meta = extract_video_metadata_verbose(file_path)
        else:
            specialized_meta = extract_video_metadata(file_path)

    # Merge results
    results.update(specialized_meta)
    return results


def extract_video_metadata_verbose(file_path: Path) -> Dict[str, Any]:
    """(Internal) Exhaustive MediaInfo extraction."""
    results = {}
    if not MEDIINFO_AVAILABLE:
        return {"MediaInfo_Error": "pymediainfo not installed"}
        
    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            track_type = track.track_type
            if track_type in ["Audio", "Text"]:
                prefix = f"{track_type}_{track.track_id or '0'}"
            else:
                prefix = track_type
            
            track_dict = track.to_data()
            for key, value in track_dict.items():
                if value is None or key in ['track_type', 'track_id']: continue
                
                clean_key = f"{prefix}_{key.replace('_', ' ').title().replace(' ', '_')}"
                if clean_key not in results:
                    results[clean_key] = value
    except Exception as e:
        results["MediaInfo_Error"] = str(e)
    return results

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """
    (Internal) Standard MediaInfo extraction.
    UPDATED: Returns INTs for calculations, not strings.
    """
    results = {}
    if not MEDIINFO_AVAILABLE:
        return {"MediaInfo_Error": "pymediainfo not installed"}

    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            if track.track_type == "General":
                results["Format"] = track.format
                # Duration is ms, return float seconds or ms int? 
                # MediaInfo 'duration' is usually Int (ms). 
                if track.duration:
                    results["Duration"] = int(track.duration) / 1000.0 # Seconds
                results["Recorded_Date"] = track.recorded_date

            elif track.track_type == "Video":
                results["Video_Format"] = track.format
                if track.width: results["Width"] = int(track.width)
                if track.height: results["Height"] = int(track.height)
                results["Frame_Rate"] = track.frame_rate

            elif track.track_type == "Audio":
                t_id = f"Audio_{track.track_id or '1'}"
                results[f"{t_id}_Format"] = track.format
                if track.sampling_rate:
                    results[f"{t_id}_Sampling_Rate"] = int(track.sampling_rate)
                
                # Bitrate extraction
                br = track.bit_rate or track.other_bit_rate
                if track.bit_rate:
                    results["Bit_Rate"] = int(track.bit_rate) # Raw bits/sec
                elif isinstance(track.other_bit_rate, list) and track.other_bit_rate:
                     results["Bit_Rate_String"] = track.other_bit_rate[0]

    except Exception as e:
        results["MediaInfo_Error"] = str(e)
    return results

# --- Demo/Test Support ---
def demo_tqdm_progress(iterable: Any = 100, desc: str = "Testing Progress Bar"):
    if not TQDM_AVAILABLE:
        print("tqdm is not available.")
        return
    items = range(iterable) if isinstance(iterable, int) else iterable
    for _ in tqdm(items, desc=desc, file=sys.stdout):
        time.sleep(0.01)
    print("TQDM Demo Complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Helper Utilities")
        sys.exit(0)