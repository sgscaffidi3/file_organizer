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
    
    if not candidate:
        return "ffmpeg"
        
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
        return

    print(f"Testing Binary: {binary}")
    
    input_path = Path(TEST_FILE).resolve()
    print(f"Testing Input: {input_path}")
    
    if not input_path.exists():
        print("❌ Error: Input file not found!")
        # Try to find *any* avi file to help the user
        print("Searching for any AVI file...")
        found = list(Path('.').rglob('*.avi'))
        if found:
            print(f"Found: {found[0]}")
            input_path = found[0]
        else:
            return

    # Build the exact command used by the server
    cmd = [
        binary, 
        '-y',
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
        'debug_output.mp4' # Write to file instead of pipe to verify validity
    ]
    
    print("\nRunning Command:")
    print(" ".join(cmd))
    print("-" * 60)
    
    try:
        # Run and capture output
        process = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print("✅ Transcoding SUCCESS!")
        print(f"Output saved to: {os.path.abspath('debug_output.mp4')}")
        print("Please try playing 'debug_output.mp4' in VLC or Chrome to verify it works.")
        
    except subprocess.CalledProcessError as e:
        print("❌ Transcoding FAILED!")
        print("STDERR Output (The actual error from FFmpeg):")
        print("="*60)
        print(e.stderr)
        print("="*60)
    except FileNotFoundError:
        print(f"❌ Error: Could not execute binary at '{binary}'")
    except Exception as e:
        print(f"❌ Python Error: {e}")

if __name__ == "__main__":
    test_transcode()