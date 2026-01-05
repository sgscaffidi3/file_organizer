import os
import sys
import subprocess
from pathlib import Path
from config_manager import ConfigManager

# --- CONFIGURATION ---
# 1. REPLACE THIS WITH THE PATH TO THE AVI FILE THAT IS FAILING
TEST_FILE = r"organized_media_output\organized_media_output\2002\12\2002-12-23 14.15.28 Christmas Barn Bellport.avi"

def test_transcode():
    config = ConfigManager()
    settings = config.FFMPEG_SETTINGS
    
    # Check Binary
    binary = settings.get('binary_path') or "ffmpeg"
    print(f"Testing Binary: {binary}")
    
    input_path = Path(TEST_FILE).resolve()
    print(f"Testing Input: {input_path}")
    
    if not input_path.exists():
        print("❌ Error: Input file not found!")
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
        print("Try playing 'debug_output.mp4' in VLC or Chrome to verify.")
        
    except subprocess.CalledProcessError as e:
        print("❌ Transcoding FAILED!")
        print("STDERR Output:")
        print(e.stderr)
    except FileNotFoundError:
        print(f"❌ Error: Could not find FFmpeg binary at '{binary}'")

if __name__ == "__main__":
    test_transcode()