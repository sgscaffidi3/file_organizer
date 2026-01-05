# ==============================================================================
# File: reset_metadata.py
# Utility to force re-processing of metadata for specific file types.
# v0.2 - Added --auto flag to chain re-scan and migration.
# ------------------------------------------------------------------------------
import argparse
import subprocess
import sys
from database_manager import DatabaseManager
from config_manager import ConfigManager

def reset_metadata(extensions, auto_process=False):
    mgr = ConfigManager()
    db_path = mgr.OUTPUT_DIR / 'metadata.sqlite'
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print(f"Connecting to {db_path}...")
    
    with DatabaseManager(db_path) as db:
        total_reset = 0
        
        query_reset = """
        UPDATE MediaContent 
        SET width=NULL, 
            height=NULL, 
            duration=NULL,
            bitrate=NULL,
            extended_metadata=NULL, 
            video_codec=NULL, 
            date_best=NULL
        WHERE content_hash IN (
            SELECT content_hash FROM FilePathInstances 
            WHERE path LIKE ? OR path LIKE ?
        )
        """
        
        for ext in extensions:
            ext_lower = f"%{ext.lower()}"
            ext_upper = f"%{ext.upper()}"
            
            count_query = "SELECT COUNT(*) FROM FilePathInstances WHERE path LIKE ? OR path LIKE ?"
            count = db.execute_query(count_query, (ext_lower, ext_upper))[0][0]
            
            if count > 0:
                print(f"Resetting metadata for {count} files with extension '{ext}'...")
                db.execute_query(query_reset, (ext_lower, ext_upper))
                total_reset += count
            else:
                print(f"No files found for extension '{ext}'")
        
        print("-" * 40)
        if total_reset > 0:
            print(f"✅ Success! Metadata cleared for {total_reset} records.")
            
            if auto_process:
                print("\n🚀 --auto flag detected. Starting Metadata Extraction...")
                # Run Metadata Processor
                subprocess.run([sys.executable, "main.py", "--meta"], check=True)
                
                print("\n📦 Updating Clean Database (Migration)...")
                # Run Migrator (Refresh Clean DB)
                subprocess.run([sys.executable, "main.py", "--migrate"], check=True)
                
                print("\n✨ Done! You can now restart the server.")
            else:
                print("To apply changes, run:")
                print("1. python main.py --meta")
                print("2. python main.py --migrate")
        else:
            print("No records were updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset metadata for specific file extensions.")
    parser.add_argument('extensions', nargs='+', help="List of extensions to reset (e.g. .heic .jpg)")
    parser.add_argument('--auto', action='store_true', help="Automatically run --meta and --migrate after reset.")
    args = parser.parse_args()
    
    exts = [e if e.startswith('.') else f".{e}" for e in args.extensions]
    
    reset_metadata(exts, args.auto)