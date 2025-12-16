# ==============================================================================
# File: database_manager.py
_MAJOR_VERSION = 0
_MINOR_VERSION = 3
# Version: <Automatically calculated via dynamic import of target module>
# ------------------------------------------------------------------------------
# CHANGELOG:
_CHANGELOG_ENTRIES = [
    "Initial implementation with basic connection management.",
    "Implemented the versioning and patch derivation strategy.",
    "Added basic schema creation for MediaContent and FilePathInstances tables.",
    "Added execute_query method to simplify database operations.",
    "Implemented context manager methods (__enter__, __exit__) for reliable connection handling.",
    "Improved execute_query to handle SELECT COUNT(*) returning empty results gracefully.",
    "CRITICAL SCHEMA FIX: Added the UNIQUE constraint to the 'path' column in the FilePathInstances table definition. (Resolves test_03_duplicate_path_insertion_is_ignored).",
    "CRITICAL SCHEMA FIX: Renamed the primary key of FilePathInstances from 'id' to 'file_id' to maintain consistency with the field name used in deduplicator.py's SQL queries.",
    "Minor version bump to 0.3 and refactored changelog to Python list for reliable versioning.",
    "Added logic to enforce a clean exit (sys.exit(0)) when running the --version check.",
    "CRITICAL SCHEMA FIX: Added the `date_modified` column to the `FilePathInstances` table to support deduplication logic based on file modification time (Resolves all `test_deduplicator` errors).",
    "CRITICAL API FIX: Updated `execute_query` to return the `rowcount` (number of affected/inserted rows) for non-SELECT queries. (Required for `FileScanner` to track insertions).",
    "CRITICAL SCHEMA FIX: Added `DEFAULT (DATETIME('now'))` to `FilePathInstances.date_modified`. This resolves the `IntegrityError: NOT NULL constraint failed` in `test_database_manager` and should fix all cascading test failures."
]
# ------------------------------------------------------------------------------
import sqlite3
from typing import Optional, Tuple, List
import os
from contextlib import contextmanager

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
            # Note: Isolation level is set to None for autocommit mode, 
            # as per standard practice unless explicit transactions are needed.
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
        Executes a query. Commits changes for non-SELECT queries.
        Returns results for SELECT queries, or rowcount for others.
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
                # Ensure a list is always returned
                return result if result is not None else []
            else:
                # For INSERT/UPDATE/DELETE, commit and return the number of rows affected/inserted
                self.conn.commit()
                return cursor.rowcount
                
        except sqlite3.Error as e:
            if self.conn and not query.strip().upper().startswith('SELECT'):
                self.conn.rollback()
            raise e
            
    def create_schema(self):
        """Creates the necessary tables if they don't exist."""
        if not self.conn:
            self.connect() # Ensure connection is open to create schema

        # MediaContent: Unique file content (hashes) and associated rich metadata
        content_table_sql = """
        CREATE TABLE IF NOT EXISTS MediaContent (
            content_hash TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            file_type_group TEXT NOT NULL,
            
            -- Rich Metadata (extracted by MetadataProcessor)
            date_best TEXT, -- Best estimated date (EXIF, file system, etc.)
            width INTEGER,
            height INTEGER,
            duration REAL,
            bitrate INTEGER,
            title TEXT
        );
        """
        
        # FilePathInstances: List of all file locations. 
        # The 'path' column MUST be UNIQUE to prevent re-insertion on re-scan.
        instance_table_sql = """
        CREATE TABLE IF NOT EXISTS FilePathInstances (
            file_id INTEGER PRIMARY KEY, -- CRITICAL FIX (8): Renamed from 'id' to 'file_id'
            content_hash TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL, 
            original_full_path TEXT NOT NULL,
            original_relative_path TEXT NOT NULL,
            
            -- Metadata derived from file system:
            date_added TEXT DEFAULT (DATETIME('now')), -- Date/time file was first scanned
            date_modified TEXT NOT NULL DEFAULT (DATETIME('now')), -- CRITICAL FIX: Added default value for NOT NULL constraint
            
            -- Deduplication/Organization fields:
            is_primary BOOLEAN DEFAULT 0, -- Set to 1 if this is the chosen primary instance
            new_path_id INTEGER, -- FK to itself (id of the instance that holds the new path)

            FOREIGN KEY (content_hash) REFERENCES MediaContent(content_hash) ON DELETE CASCADE
        );
        """
        
        try:
            self.conn.execute(content_table_sql)
            self.conn.execute(instance_table_sql)
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error creating schema: {e}")
            raise e

# --- CLI EXECUTION LOGIC ---
if __name__ == '__main__':
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Database Manager Utility")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    args = parser.parse_args()

    if args.version:
        from version_util import print_version_info
        print_version_info(__file__, "Database Manager")
        sys.exit(0)