
# VERSIONING
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_REL_CHANGES = [1]
import sqlite3
from pathlib import Path
from config_manager import ConfigManager
from database_manager import DatabaseManager

def reset_hashes():
    mgr = ConfigManager()
    db_path = mgr.OUTPUT_DIR / 'metadata.sqlite'
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    print(f"🔌 Connecting to {db_path}...")
    
    with DatabaseManager(db_path) as db:
        # Check if column exists first (it should if you ran the server at least once)
        try:
            db.execute_query("SELECT perceptual_hash FROM MediaContent LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️ Column 'perceptual_hash' does not exist yet.")
            print("   Run 'python main.py --scan' first to update the schema.")
            return

        print("🔄 Resetting Perceptual Hashes for all images...")
        
        # Set to NULL to trigger re-processing
        # We only target IMAGE types
        sql = "UPDATE MediaContent SET perceptual_hash = NULL WHERE file_type_group = 'IMAGE'"
        db.execute_query(sql)
        
        # Verify
        count = db.execute_query("SELECT COUNT(*) FROM MediaContent WHERE file_type_group = 'IMAGE' AND perceptual_hash IS NULL")[0][0]
        
        print(f"✅ Success! {count} images marked for visual hashing.")
        print("-" * 40)
        print("NEXT STEP: Run 'python main.py --meta' to generate the hashes.")

if __name__ == "__main__":
    reset_hashes()