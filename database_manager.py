# ==============================================================================
# File: database_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 1
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_REL_CHANGES = [18]
_CHANGELOG_ENTRIES = [
    "Released as v0.1.0"
]
_PATCH_VERSION = len(_CHANGELOG_ENTRIES)
# ------------------------------------------------------------------------------
import sqlite3
from typing import Optional, Tuple, List, Any
import os
import sys
import argparse
from contextlib import contextmanager
from pathlib import Path

class DatabaseManager:
    """
    Manages the SQLite connection and provides core database operations.
    Implements the context manager protocol for reliable connection handling.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
    
    def __enter__(self):
        """Opens the database connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the database connection."""
        self.close()

    def connect(self):
        """Establishes a connection to the SQLite database."""
        if self.conn is None:
            # Ensure the directory exists if we are creating a new DB
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign key constraint enforcement
            self.conn.execute('PRAGMA foreign_keys = ON;')

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Tuple] | int:
        """
        Executes a single query.
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                # Return results for SELECT
                result = cursor.fetchall()
                return result if result is not None else []
            else:
                # For INSERT/UPDATE/DELETE, commit
                self.conn.commit()
                return cursor.rowcount
                
        except sqlite3.Error as e:
            if self.conn and not query.strip().upper().startswith('SELECT'):
                self.conn.rollback()
            raise e

    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        Executes the same query for many sets of parameters.
        Highly optimized for bulk updates/inserts.
        """
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        try:
            cursor.executemany(query, params_list)
            self.conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def create_schema(self):
        """Creates the necessary tables if they don't exist and handles basic migrations."""
        if not self.conn:
            self.connect()

        # MediaContent: Updated with hybrid metadata support
        content_table_sql = """
        CREATE TABLE IF NOT EXISTS MediaContent (
            content_hash TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            file_type_group TEXT NOT NULL,
            
            -- Core Metadata Columns
            date_best TEXT, 
            width INTEGER,
            height INTEGER,
            duration REAL,
            bitrate INTEGER,
            title TEXT,
            video_codec TEXT, 
            
            -- Deduplication / Organization
            new_path_id TEXT,
            
            -- Visual Analysis
            perceptual_hash TEXT,
            
            -- Hybrid "Backpack" Column
            extended_metadata TEXT 
        );
        """
        # FilePathInstances: List of all file locations. 
        instance_table_sql = """
        CREATE TABLE IF NOT EXISTS FilePathInstances (
            file_id INTEGER PRIMARY KEY,
            content_hash TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL, 
            original_full_path TEXT NOT NULL,
            original_relative_path TEXT NOT NULL,
            
            -- Metadata derived from file system:
            date_added TEXT DEFAULT (DATETIME('now')), -- Date/time file was first scanned
            date_modified TEXT NOT NULL DEFAULT (DATETIME('now')), 
            
            -- Deduplication/Organization fields:
            is_primary BOOLEAN DEFAULT 0,
            
            FOREIGN KEY (content_hash) REFERENCES MediaContent(content_hash) ON DELETE CASCADE
        );
        """
        
        # Indices for Performance
        index_hash_sql = "CREATE INDEX IF NOT EXISTS idx_fpi_content_hash ON FilePathInstances(content_hash);"
        index_primary_sql = "CREATE INDEX IF NOT EXISTS idx_fpi_is_primary ON FilePathInstances(is_primary);"
        index_phash_sql = "CREATE INDEX IF NOT EXISTS idx_mc_phash ON MediaContent(perceptual_hash);"
        
        try:
            self.conn.execute(content_table_sql)
            self.conn.execute(instance_table_sql)
            
            # --- MIGRATIONS ---
            # 1. new_path_id
            try:
                self.conn.execute("ALTER TABLE MediaContent ADD COLUMN new_path_id TEXT;")
            except sqlite3.OperationalError: pass
            
            # 2. perceptual_hash (New for v0.11)
            try:
                self.conn.execute("ALTER TABLE MediaContent ADD COLUMN perceptual_hash TEXT;")
            except sqlite3.OperationalError: pass
                
            # Create Indices
            self.conn.execute(index_hash_sql)
            self.conn.execute(index_primary_sql)
            self.conn.execute(index_phash_sql)
                
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error creating schema: {e}")
            raise e

    def dump_database(self):
        """Prints the contents of all tables in a friendly format."""
        if not self.conn:
            self.connect()
        
        print(f"\n{'='*60}")
        print(f"DATABASE DUMP: {self.db_path}")
        print(f"{'='*60}")

        # Helper to print a table
        def print_table(table_name):
            print(f"\n--- Table: {table_name} ---")
            try:
                # Get columns
                cursor = self.conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Get rows
                rows = self.execute_query(f"SELECT * FROM {table_name}")
                
                if not rows:
                    print("  [Empty Table]")
                    return

                # Calculate column widths
                col_widths = [len(c) for c in columns]
                for row in rows:
                    for i, val in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(str(val)))
                
                # Print Header
                header = " | ".join(f"{col:<{col_widths[i]}}" for i, col in enumerate(columns))
                print(header)
                print("-" * len(header))
                
                # Print Rows
                for row in rows:
                    print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))
                
                print(f"  ({len(rows)} records found)")
                
            except sqlite3.Error as e:
                print(f"  Error reading table: {e}")

        print_table("MediaContent")
        print_table("FilePathInstances")
        print(f"\n{'='*60}\n")

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Database Manager Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--changes', nargs='?', const='all', help='Show changelog history.')
    parser.add_argument('--dump_db', action='store_true', help='Dump the contents of the database to stdout.')
    parser.add_argument('--db', type=str, default=r"organized_media_output/metadata.sqlite", help='Path to the database file (default: organized_media_output/metadata.sqlite)')
    args = parser.parse_args()

    
    if hasattr(args, 'changes') and args.changes:
        from version_util import print_change_history
        print_change_history(__file__, args.changes)
        sys.exit(0)
    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Database Manager")
        sys.exit(0)

    if args.dump_db:
        if not os.path.exists(args.db):
            print(f"Error: Database file not found at '{args.db}'")
            sys.exit(1)
            
        db = DatabaseManager(args.db)
        with db:
            db.dump_database()
        sys.exit(0)