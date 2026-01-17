
# VERSIONING
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_REL_CHANGES = [1]
import os
import sys
import subprocess
from pathlib import Path
from config_manager import ConfigManager

# --- CONFIGURATION ---
# 1. REPLACE THIS WITH THE PATH TO THE AVI FILE THAT IS FAILING
TEST_FILE = r"organized_media_output\organized_media_output\2002\12\2002-12-23 14.15.28 Christmas Barn Bellport.avi"

def get_ffmpeg_binary(config):
    settings = config.FFMPEG_SETTINGS
    candidate = settings.get('binary_path')
    if not candidate: return "ffmpeg"
    
    path_obj = Path(candidate)
    
    # If it's a directory, look inside
    if path_obj.is_dir():
        if os.name == 'nt':
            potential = path_obj / 'ffmpeg.exe'
            potential_bin = path_obj / 'bin' / 'ffmpeg.exe'
        else:
            potential = path_obj / 'ffmpeg'
            potential_bin = path_obj / 'bin' / 'ffmpeg'
            
        if potential.exists(): return str(potential)
        if potential_bin.exists(): return str(potential_bin)
        
        print(f"❌ Error: Config points to directory '{candidate}' but ffmpeg executable not found inside.")
        return None
        
    return candidate

def test_transcode():
    config = ConfigManager()
    binary = get_ffmpeg_binary(config)
    
    if not binary:
        print("❌ Could not determine FFmpeg binary path.")
        return

    # 1. TEST BASIC EXECUTION (Version Check)
    print(f"1. Testing Binary Execution: {binary}")
    binary_dir = os.path.dirname(binary) if os.path.isabs(binary) else None
    
    try:
        # cwd=binary_dir helps Windows find DLLs next to the exe
        ver_proc = subprocess.run(
            [binary, "-version"], 
            capture_output=True, 
            text=True, 
            cwd=binary_dir
        )
        if ver_proc.returncode != 0:
            print("❌ FFmpeg failed to start (-version returned non-zero).")
            print(ver_proc.stderr)
            return
        else:
            print(f"✅ FFmpeg is executable. Version info:\n{ver_proc.stdout.splitlines()[0]}")
    except Exception as e:
        print(f"❌ Failed to run executable: {e}")
        return

    # 2. TEST TRANSCODING
    input_path = Path(TEST_FILE).resolve()
    # CRITICAL FIX: Make output path absolute so it doesn't get lost in binary_dir
    output_path = Path('debug_output.mp4').resolve()
    
    print(f"\n2. Testing Transcode of: {input_path}")
    
    if not input_path.exists():
        print("❌ Error: Input file not found on disk.")
        return

    cmd = [
        binary, '-y',
        '-i', str(input_path),
        '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-profile:v', 'baseline',
        '-c:a', 'aac', '-ac', '2', '-ar', '44100',
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+default_base_moof',
        '-reset_timestamps', '1',
        str(output_path) # Use absolute path here
    ]
    
    print("Running Command...")
    # print(" ".join(cmd)) # Uncomment to see full command
    
    try:
        process = subprocess.run(
            cmd, 
            check=True, 
            text=True, 
            capture_output=True, 
            cwd=binary_dir 
        )
        print("✅ Transcoding SUCCESS!")
        
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"Output saved to: {output_path} ({size/1024:.2f} KB)")
            print("Please try playing this file in VLC or Chrome to verify it works.")
        else:
            print(f"❌ Error: FFmpeg exited with 0, but file was not found at {output_path}")
        
    except subprocess.CalledProcessError as e:
        print("❌ Transcoding FAILED!")
        print("--- STDERR ---")
        print(e.stderr)
        print("--------------")

if __name__ == "__main__":
    test_transcode()