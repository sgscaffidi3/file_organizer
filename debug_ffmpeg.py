import os
import sys
import subprocess
from pathlib import Path
from config_manager import ConfigManager

# --- CONFIGURATION ---
# Replace with the file that failed
TEST_FILE = r"organized_media_output\organized_media_output\2002\12\2002-12-23 14.15.28 Christmas Barn Bellport.avi"

def get_ffmpeg_binary(config):
    settings = config.FFMPEG_SETTINGS
    candidate = settings.get('binary_path')
    if not candidate: return "ffmpeg"
    
    path_obj = Path(candidate)
    if path_obj.is_dir():
        if os.name == 'nt':
            potential = path_obj / 'ffmpeg.exe'
        else:
            potential = path_obj / 'ffmpeg'
        if potential.exists(): return str(potential)
    elif path_obj.exists():
        return str(path_obj)
    return candidate

def test_transcode():
    config = ConfigManager()
    binary = get_ffmpeg_binary(config)
    
    # 1. TEST BASIC EXECUTION (Version Check)
    print(f"1. Testing Binary Execution: {binary}")
    binary_dir = os.path.dirname(binary) if os.path.isabs(binary) else None
    
    try:
        # CRITICAL FIX: cwd=binary_dir helps Windows find DLLs next to the exe
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
        'debug_output.mp4'
    ]
    
    print("Running Command...")
    
    try:
        # CRITICAL FIX: cwd=binary_dir
        process = subprocess.run(
            cmd, 
            check=True, 
            text=True, 
            capture_output=True, 
            cwd=binary_dir 
        )
        print("✅ Transcoding SUCCESS!")
        size = os.path.getsize('debug_output.mp4')
        print(f"Output: debug_output.mp4 ({size/1024:.2f} KB)")
        
    except subprocess.CalledProcessError as e:
        print("❌ Transcoding FAILED!")
        print("--- STDERR ---")
        print(e.stderr)
        print("--------------")

if __name__ == "__main__":
    test_transcode()