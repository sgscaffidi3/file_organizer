# ==============================================================================
# File: reset_metadata.py
# Utility to force re-processing of metadata for specific file types
# without re-hashing the files.
# ------------------------------------------------------------------------------
import argparse
from database_manager import DatabaseManager
from config_manager import ConfigManager

def reset_metadata(extensions):
    mgr = ConfigManager()
    db_path = mgr.OUTPUT_DIR / 'metadata.sqlite'
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print(f"Connecting to {db_path}...")
    
    with DatabaseManager(db_path) as db:
        total_reset = 0
        
        # SQL to reset metadata fields to NULL
        # This flags the files as "Unprocessed" for the MetadataProcessor
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
            # Handle case sensitivity logic in SQL query params
            # We look for .ext and .EXT
            ext_lower = f"%{ext.lower()}"
            ext_upper = f"%{ext.upper()}"
            
            # 1. Count targets
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
            print("🚀 NOW RUN: python main.py --meta")
        else:
            print("No records were updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset metadata for specific file extensions.")
    parser.add_argument('extensions', nargs='+', help="List of extensions to reset (e.g. .heic .jpg .mov)")
    args = parser.parse_args()
    
    # Ensure dots
    exts = [e if e.startswith('.') else f".{e}" for e in args.extensions]
    
    reset_metadata(exts)