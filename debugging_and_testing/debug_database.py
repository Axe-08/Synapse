# debugging_and_testing/debug_database.py
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from create_database import SQLITE_PROGRESS_TABLES_SQL, SQLITE_WORKSPACE_TABLES_SQL
import synapse.database as db

DEBUG_PROGRESS_DB = "debugging_and_testing/debug_progress.db"
DEBUG_WORKSPACE_DB = "debugging_and_testing/debug_workspace.db"

def setup_debug_dbs():
    """Drops existing debug databases and creates fresh ones with the standard schema."""
    print(f"Connecting to/Initializing {DEBUG_PROGRESS_DB}...")
    with db._get_db_connection(DEBUG_PROGRESS_DB) as conn:
        conn.executescript(SQLITE_PROGRESS_TABLES_SQL)

    print(f"Connecting to/Initializing {DEBUG_WORKSPACE_DB}...")
    with db._get_db_connection(DEBUG_WORKSPACE_DB) as conn:
        conn.executescript(SQLITE_WORKSPACE_TABLES_SQL)

    print("Debug databases created successfully.")

if __name__ == "__main__":
    setup_debug_dbs()
