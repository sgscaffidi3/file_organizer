# ==============================================================================
# File: database_manager.py
# Version: 0.1
# ------------------------------------------------------------------------------
# CHANGELOG:
# 1. Added versioning and changelog structure to all files.
# 2. Implemented the versioning and patch derivation strategy.
# 3. Implemented --version/-v and --help/-h support for standalone execution.
# 4. Added --teardown functionality for easy database reset during development.
# 5. Updated to use paths from ConfigManager instead of config.py.
# 6. Project name changed to "file_organizer" in descriptions.
# ------------------------------------------------------------------------------
import sqlite3
from pathlib import Path
from typing import List, Tuple
import os
import argparse
from version_util import print_version_info
import config
from config_manager import ConfigManager 

class DatabaseManager:
    """
    Manages the connection, context, and schema for the SQLite database.
    Adheres to the two-table architecture (MediaContent and FilePathInstances).
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Ensure the output directory exists before attempting to create the DB file
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        """Context manager entry: opens the connection."""
        self.conn = sqlite3.connect(self.db_path)
        # Enable foreign key enforcement
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: closes the connection, committing changes or rolling back."""
        if self.conn:
            if exc_type is None:
                # Commit if no exceptions occurred
                self.conn.commit()
            else:
                # Rollback on error
                self.conn.rollback() 
            self.conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """A safe wrapper for executing read/write queries, returning results for SELECT queries."""
        try:
            self.cursor.execute(query, params)
            # Fetch all results only if the query implies a selection/read (common sqlite pattern)
            return self.cursor.fetchall()
        except sqlite3.Error:
            # Re-raise the exception to be handled by the context manager's __exit__
            raise 

    def create_schema(self):
        """Creates the two primary tables: MediaContent and FilePathInstances."""
        
        media_content_table = """
        CREATE TABLE IF NOT EXISTS MediaContent (
            content_hash TEXT PRIMARY KEY,
            new_path_id TEXT,               
            file_type_group TEXT,           
            size INTEGER,                   
            date_best TEXT,                 
            width INTEGER,
            height INTEGER,
            duration REAL,
            bitrate INTEGER,
            title TEXT,
            description_ai TEXT             
        );
        """
        
        # This table tracks every instance (path) that points to a unique content_hash
        file_path_instances_table = """
        CREATE TABLE IF NOT EXISTS FilePathInstances (
            instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_hash TEXT,
            original_full_path TEXT UNIQUE,  
            original_relative_path TEXT,     
            FOREIGN KEY (content_hash) REFERENCES MediaContent(content_hash) 
                ON DELETE CASCADE            
        );
        """
        
        self.cursor.execute(media_content_table)
        self.cursor.execute(file_path_instances_table)

    def teardown(self):
        """Deletes the database file completely."""
        if self.db_path.exists():
            os.remove(self.db_path)
            return True
        return False

if __name__ == "__main__":
    
    # Instantiate ConfigManager to correctly locate the database file
    manager = ConfigManager() 
    db_path = manager.OUTPUT_DIR / 'metadata.sqlite' 

    parser = argparse.ArgumentParser(description="Database Management for file_organizer: Used to initialize, verify, or teardown the schema.")
    parser.add_argument('-v', '--version', action='store_true', help='Show version information and exit.')
    parser.add_argument('--init', action='store_true', help='Initialize (or re-initialize) the database schema.')
    parser.add_argument('--teardown', action='store_true', help='Delete the database file completely (USE WITH CAUTION).')
    args = parser.parse_args()

    if args.version:
        print_version_info(__file__, "Database Manager")
    elif args.teardown:
        print(f"Attempting to delete database at: {db_path}")
        try:
            db_manager = DatabaseManager(db_path)
            if db_manager.teardown():
                print("Database file successfully deleted.")
            else:
                print("Database file did not exist.")
        except Exception as e:
            print(f"Error during database teardown: {e}")
    elif args.init:
        print(f"Attempting to initialize database at: {db_path}")
        try:
            with DatabaseManager(db_path) as db:
                db.create_schema()
                print("Database schema successfully created/verified.")
        except Exception as e:
            print(f"Error initializing database: {e}")
    else:
        parser.print_help()