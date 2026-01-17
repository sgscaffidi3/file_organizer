
# VERSIONING
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_REL_CHANGES = [1]
# ==============================================================================
# File: reset_raw.py
# Utility to force re-processing of RAW files
# ------------------------------------------------------------------------------
from database_manager import DatabaseManager
from config_manager import ConfigManager

def reset_raw_metadata():
    mgr = ConfigManager()
    db_path = mgr.OUTPUT_DIR / 'metadata.sqlite'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    # Extensions to reset (Case insensitive in SQLite LIKE usually, but we be explicit)
    raw_exts = ['.NEF', '.CR2', '.ARW', '.DNG', '.ORF']
    
    print(f"Connecting to {db_path}...")
    
    with DatabaseManager(db_path) as db:
        total_reset = 0
        for ext in raw_exts:
            # 1. Count how many we are about to nuke
            # We use LIKE with % to match the end of the string
            query_count = f"SELECT COUNT(*) FROM FilePathInstances WHERE path LIKE '%{ext}'"
            count = db.execute_query(query_count)[0][0]
            
            if count > 0:
                print(f"Found {count} records for {ext}...")
                
                # 2. Reset the Metadata columns to NULL
                # This makes the MetadataProcessor think they are "New/Unprocessed"
                query_reset = f"""
                UPDATE MediaContent 
                SET width=NULL, height=NULL, extended_metadata=NULL, video_codec=NULL, date_best=NULL
                WHERE content_hash IN (
                    SELECT content_hash FROM FilePathInstances WHERE path LIKE '%{ext}'
                )
                """
                db.execute_query(query_reset)
                total_reset += count
        
        print("-" * 40)
        print(f"Success! Metadata cleared for {total_reset} RAW files.")
        print("Now run: python main.py --meta")

if __name__ == "__main__":
    reset_raw_metadata()