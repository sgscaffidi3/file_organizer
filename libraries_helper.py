# ==============================================================================
# File: libraries_helper.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_REL_CHANGES = [30]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# Version: 0.11.31
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
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False

try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False

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
    libs = ['tqdm', 'Pillow', 'pillow-heif', 'pymediainfo', 'rawpy', 'PyPDF2', 'python-docx', 'python-pptx', 'openpyxl', 'EbookLib', 'ImageHash']
    versions = {}
    for lib in libs:
        try:
            versions[lib] = importlib.metadata.version(lib)
        except importlib.metadata.PackageNotFoundError:
            versions[lib] = "Not Installed"
    return versions

# --- Helpers ---
def _convert_to_degrees(value):
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except:
        return 0.0

def _parse_fraction(val):
    try:
        if isinstance(val, tuple) and len(val) == 2:
            return val[0] / val[1] if val[1] != 0 else 0
        return float(val)
    except:
        return 0

def _parse_flash(val):
    try:
        v = int(val)
        return "Flash fired" if (v & 1) else "Flash did not fire"
    except:
        return str(val)

# --- Perceptual Hashing ---
def calculate_image_hash(file_path: Path) -> Optional[str]:
    """
    Calculates the dhash (difference hash) of an image for near-duplicate detection.
    Returns the hash as a hexadecimal string.
    """
    if not IMAGEHASH_AVAILABLE or not PIL_AVAILABLE:
        return None
    
    try:
        with Image.open(file_path) as img:
            # dhash is generally best for detecting resizes/modifications
            h = imagehash.dhash(img)
            return str(h)
    except Exception:
        # Fallback for RAW/HEIC if Pillow can't open directly (though register_heif_opener should handle HEIC)
        # For RAW, we might need rawpy, but imagehash expects a PIL Image.
        return None

# --- Specialized Extractors ---

def extract_raw_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extracts metadata from RAW images using rawpy.
    This guarantees full sensor dimensions vs embedded thumbnails.
    """
    if not RAWPY_AVAILABLE:
        # Fallback to MediaInfo if rawpy is missing, but warn
        return extract_video_metadata(file_path)

    metadata = {}
    try:
        with rawpy.imread(str(file_path)) as raw:
            # raw.sizes provides the full sensor size
            # .raw_width / .raw_height are the full uncropped dimensions
            metadata['Width'] = raw.sizes.width
            metadata['Height'] = raw.sizes.height
            metadata['Format'] = "RAW"
            metadata['Camera_Make'] = raw.camera_white_level_per_channel # Not directly available, rawpy focuses on pixel data
            
            # rawpy doesn't parse EXIF strings well (it focuses on image data).
            # We combine it with Pillow for tags if possible.
    except Exception as e:
        return {"Raw_Error": str(e)}

    # Secondary Pass: Use Pillow for EXIF Tags (Date, ISO, etc)
    # Pillow is good at tags, bad at RAW dimensions.
    if PIL_AVAILABLE:
        try:
            with Image.open(file_path) as img:
                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag == 'DateTime': metadata['Recorded_Date'] = str(value)
                        if tag == 'Make': metadata['Make'] = str(value).strip()
                        if tag == 'Model': metadata['Model'] = str(value).strip()
                        
                        # Deep EXIF (ISO/Aperture)
                        if tag_id == 0x8769: # ExifIFD
                            sub = exif.get_ifd(0x8769)
                            for k, v in sub.items():
                                t = ExifTags.TAGS.get(k, k)
                                if t == 'ISOSpeedRatings': metadata['ISO'] = str(v)
                                if t == 'FNumber': metadata['Aperture'] = f"f/{_parse_fraction(v):.1f}"
                                if t == 'ExposureTime': metadata['Shutter_Speed'] = f"{v} sec"
        except:
            pass
            
    return metadata

def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extracts Deep metadata from an image file using Pillow."""
    if not PIL_AVAILABLE:
        return {"Pillow_Error": "Pillow library not installed"}
    
    metadata = {}
    try:
        with Image.open(file_path) as img:
            metadata['Width'] = img.width
            metadata['Height'] = img.height
            metadata['Format'] = img.format
            
            exif = img.getexif()
            if not exif: return metadata

            metadata['Exif_Tags_Count'] = len(exif)
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                if tag == 'Make': metadata['Make'] = str(value).strip()
                if tag == 'Model': metadata['Model'] = str(value).strip()
                if tag == 'DateTime': metadata['Recorded_Date'] = str(value)
                if tag == 'Software': metadata['Software'] = str(value)

            if 0x8769 in exif:
                sub_exif = exif.get_ifd(0x8769)
                for tag_id, value in sub_exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag == 'ISOSpeedRatings': metadata['ISO'] = str(value)
                    if tag == 'FNumber': metadata['Aperture'] = f"f/{_parse_fraction(value):.1f}"
                    if tag == 'ExposureTime': metadata['Shutter_Speed'] = f"{value} sec"
                    if tag == 'FocalLength': metadata['Focal_Length'] = f"{_parse_fraction(value)} mm"
                    if tag == 'BrightnessValue': metadata['Brightness'] = f"{_parse_fraction(value):.2f} EV"
                    if tag == 'ExposureBiasValue': metadata['Exposure_Bias'] = f"{_parse_fraction(value):.2f} EV"
                    if tag == 'Flash': metadata['Flash'] = _parse_flash(value)
                    if tag == 'LensModel': metadata['Lens'] = str(value)

            if 0x8825 in exif:
                gps_info = exif.get_ifd(0x8825)
                gps_data = {}
                for key, val in gps_info.items():
                    name = ExifTags.GPSTAGS.get(key, key)
                    gps_data[name] = val

                if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                    lat = _convert_to_degrees(gps_data['GPSLatitude'])
                    lon = _convert_to_degrees(gps_data['GPSLongitude'])
                    if gps_data.get('GPSLatitudeRef') == 'S': lat = -lat
                    if gps_data.get('GPSLongitudeRef') == 'W': lon = -lon
                    metadata['GPS_Latitude'] = lat
                    metadata['GPS_Longitude'] = lon
                    metadata['GPS_Coordinates'] = f"{lat:.5f}, {lon:.5f}"

                if 'GPSAltitude' in gps_data:
                    alt = _parse_fraction(gps_data['GPSAltitude'])
                    ref = gps_data.get('GPSAltitudeRef', b'\x00')
                    is_below = (ord(ref) == 1) if isinstance(ref, bytes) else (int(ref) == 1)
                    if is_below: alt = -alt
                    metadata['Altitude'] = f"{alt:.1f} m"

    except Exception as e:
        return {"Pillow_Error": str(e)}
    return metadata

def extract_svg_metadata(file_path: Path) -> Dict[str, Any]:
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        meta = {}
        if 'width' in root.attrib: meta['Width'] = root.attrib['width']
        if 'height' in root.attrib: meta['Height'] = root.attrib['height']
        return meta
    except Exception as e:
        return {"SVG_Error": str(e)}

def extract_pdf_metadata(file_path: Path) -> Dict[str, Any]:
    if not PDF_AVAILABLE: return {"PDF_Error": "PyPDF2 library not installed"}
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            metadata['Page_Count'] = len(reader.pages)
            if reader.metadata:
                if reader.metadata.author: metadata['Author'] = reader.metadata.author
                if reader.metadata.title: metadata['Title'] = reader.metadata.title
    except Exception as e: return {"PDF_Error": str(e)}
    return metadata

def extract_docx_metadata(file_path: Path) -> Dict[str, Any]:
    if not DOCX_AVAILABLE: return {"Office_Error": "python-docx library not installed"}
    metadata = {}
    try:
        doc = docx.Document(file_path)
        props = doc.core_properties
        if props.author: metadata['Author'] = props.author
        if props.title: metadata['Title'] = props.title
        words = 0
        for para in doc.paragraphs: words += len(para.text.split())
        metadata['Word_Count'] = words
    except Exception as e: return {"Office_Error": str(e)}
    return metadata

def extract_pptx_metadata(file_path: Path) -> Dict[str, Any]:
    if not PPTX_AVAILABLE: return {"Office_Error": "python-pptx library not installed"}
    metadata = {}
    try:
        prs = pptx.Presentation(file_path)
        if prs.core_properties.author: metadata['Author'] = prs.core_properties.author
        if prs.core_properties.title: metadata['Title'] = prs.core_properties.title
        metadata['Slide_Count'] = len(prs.slides)
    except Exception as e: return {"Office_Error": str(e)}
    return metadata

def extract_xlsx_metadata(file_path: Path) -> Dict[str, Any]:
    if not XLSX_AVAILABLE: return {"Office_Error": "openpyxl library not installed"}
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        props = wb.properties
        meta = {}
        if props.creator: meta['Author'] = props.creator
        if props.title: meta['Title'] = props.title
        wb.close()
        return meta
    except Exception as e: return {"Office_Error": str(e)}

def extract_archive_metadata(file_path: Path) -> Dict[str, Any]:
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
        else: return {"Archive_Error": "Unsupported or Corrupt Archive"}
    except Exception as e: return {"Archive_Error": str(e)}
    return meta

def extract_ebook_metadata(file_path: Path) -> Dict[str, Any]:
    if not EBOOK_AVAILABLE: return {"Ebook_Error": "EbookLib not installed"}
    try:
        book = epub.read_epub(str(file_path)) 
        meta = {}
        if book.get_metadata('DC', 'title'): meta['Title'] = book.get_metadata('DC', 'title')[0][0]
        if book.get_metadata('DC', 'creator'): meta['Author'] = book.get_metadata('DC', 'creator')[0][0]
        return meta
    except Exception as e: return {"Ebook_Error": str(e)}


# --- Main Router ---

def get_video_metadata(file_path: Path, verbose: bool = False) -> Dict[str, Any]:
    results = {}
    try:
        stats = file_path.stat()
        results["File Size"] = stats.st_size
        results["Created"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        results["Modified"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e: results["OS_Error"] = str(e)

    ext = file_path.suffix.lower()
    specialized_meta = {}
    
    img_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']
    raw_exts = ['.cr2', '.nef', '.arw', '.dng', '.orf']

    if ext in ['.heic', '.heif']:
        specialized_meta = extract_image_metadata(file_path)
        if 'Pillow_Error' in specialized_meta:
            specialized_meta = extract_video_metadata(file_path)
            specialized_meta['_Source'] = 'MediaInfo (HEIC Fallback)'

    elif ext in img_exts:
        specialized_meta = extract_image_metadata(file_path)

    elif ext in raw_exts:
        # RAW FIX: Use rawpy for correct dimensions, Pillow for tags
        specialized_meta = extract_raw_metadata(file_path)
    
    elif ext == '.svg': specialized_meta = extract_svg_metadata(file_path)
    elif ext in ['.pdf']: specialized_meta = extract_pdf_metadata(file_path)
    elif ext in ['.docx', '.doc']: specialized_meta = extract_docx_metadata(file_path)
    elif ext in ['.pptx']: specialized_meta = extract_pptx_metadata(file_path)
    elif ext in ['.xlsx', '.xls']: specialized_meta = extract_xlsx_metadata(file_path)
    elif ext in ['.epub', '.mobi']: specialized_meta = extract_ebook_metadata(file_path)
    elif ext in ['.zip', '.tar', '.gz', '.7z', '.rar']: specialized_meta = extract_archive_metadata(file_path)
    else:
        if verbose: specialized_meta = extract_video_metadata_verbose(file_path)
        else: specialized_meta = extract_video_metadata(file_path)

    results.update(specialized_meta)
    return results


def extract_video_metadata_verbose(file_path: Path) -> Dict[str, Any]:
    results = {}
    if not MEDIINFO_AVAILABLE: return {"MediaInfo_Error": "pymediainfo not installed"}
    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            track_type = track.track_type
            if track_type in ["Audio", "Text"]: prefix = f"{track_type}_{track.track_id or '0'}"
            else: prefix = track_type
            track_dict = track.to_data()
            for key, value in track_dict.items():
                if value is None or key in ['track_type', 'track_id']: continue
                clean_key = f"{prefix}_{key.replace('_', ' ').title().replace(' ', '_')}"
                if clean_key not in results: results[clean_key] = value
    except Exception as e: results["MediaInfo_Error"] = str(e)
    return results

def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    results = {}
    if not MEDIINFO_AVAILABLE: return {"MediaInfo_Error": "pymediainfo not installed"}
    try:
        media_info = MediaInfo.parse(str(file_path))
        for track in media_info.tracks:
            if track.track_type == "General":
                results["Format"] = track.format
                if track.duration: results["Duration"] = int(track.duration) / 1000.0 
                results["Recorded_Date"] = track.recorded_date
            elif track.track_type == "Video":
                results["Video_Format"] = track.format
                if track.width: results["Width"] = int(track.width)
                if track.height: results["Height"] = int(track.height)
                results["Frame_Rate"] = track.frame_rate
                
                # FALLBACK: If Duration wasn't found in General, check Video track
                if "Duration" not in results and track.duration:
                    results["Duration"] = int(track.duration) / 1000.0
                    
            elif track.track_type == "Image":
                if track.width: results["Width"] = int(track.width)
                if track.height: results["Height"] = int(track.height)
                results["Format"] = track.format
            elif track.track_type == "Audio":
                t_id = f"Audio_{track.track_id or '1'}"
                results[f"{t_id}_Format"] = track.format
                if track.sampling_rate: results[f"{t_id}_Sampling_Rate"] = int(track.sampling_rate)
                if track.bit_rate: results["Bit_Rate"] = int(track.bit_rate)
    except Exception as e: results["MediaInfo_Error"] = str(e)
    return results

def demo_tqdm_progress(iterable: Any = 100, desc: str = "Testing Progress Bar"):
    if not TQDM_AVAILABLE: return
    items = range(iterable) if isinstance(iterable, int) else iterable
    for _ in tqdm(items, desc=desc, file=sys.stdout): time.sleep(0.01)
    print("TQDM Demo Complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    args = parser.parse_args()
    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Library Helper Utilities")
        sys.exit(0)