# create_database.py
"""
This script initializes the project's databases (progress.db and workspace.db).
It creates all necessary tables with the correct schemas and populates the
problems table from the Codeforces API and the dynamic_config table with
default values. This script is intended to be run once at the beginning
of a project deployment.
"""
import sqlite3
import requests
import logging
import time
import os
from datetime import datetime
from config import (
    DEFAULT_INGESTION_WORKER_COUNT,
    DEFAULT_ANALYSIS_WORKER_COUNT,
    DEFAULT_IMPLEMENTATION_WORKER_COUNT,
    DEFAULT_VJS_WORKER_COUNT,
    DEFAULT_DATA_ASSEMBLY_WORKER_COUNT,
    DEFAULT_ANALYSIS_BATCH_SIZE,
    DEFAULT_SCRAPER_DELAY_SECONDS, # BUGFIX: Added import
    PROGRESS_DB_NAME,
    WORKSPACE_DB_PATH,
    API_URL,
    # BUGFIX: Import MAX values for worker initialization
    MAX_INGESTION_WORKERS,
    MAX_ANALYSIS_WORKERS,
    MAX_IMPLEMENTATION_WORKERS,
    MAX_VJS_WORKERS,
    MAX_DATA_ASSEMBLY_WORKERS,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Schemas ---
# -- progress.db Schemas --
CREATE_PROBLEMS_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    contest_id INTEGER NOT NULL,
    problem_index TEXT NOT NULL,
    name TEXT NOT NULL,
    rating INTEGER,
    tags TEXT,
    status TEXT NOT NULL DEFAULT 'pending_ingestion',
    retry_count INTEGER DEFAULT 0,
    analysis_try_count INTEGER DEFAULT 0,
    implementation_try_count INTEGER DEFAULT 0,
    rescraping_attempts INTEGER DEFAULT 0,
    tried_submission_ids TEXT,
    reference_submissions_json TEXT,     -- ADD: Stores the JSON array of N submission objects.
    successful_oracles INTEGER DEFAULT 0,  -- ADD: Caches the count of compiled oracles.
    confidence_level INTEGER DEFAULT 0,    -- ADD: 0=pending, 1=calibrated, 2=differentially verified
    last_vjs_report TEXT,
    notes TEXT,
    last_updated TEXT NOT NULL
);
"""
CREATE_WORKERS_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS live_workers (
    worker_id TEXT PRIMARY KEY, -- BUGFIX: Changed to TEXT to support "POOL-ID" format
    pool TEXT NOT NULL,
    problem_id TEXT,
    stage TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TEXT NOT NULL
);
"""
CREATE_KEY_STATUS_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS key_status (
    key_fingerprint TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    status TEXT NOT NULL, -- AVAILABLE, RATE_LIMITED, EXHAUSTED, INVALID
    cooldown_until REAL
);
"""
CREATE_PROCESS_HISTORY_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS process_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    event_type TEXT NOT NULL, -- e.g., 'START', 'SUCCESS', 'FAILURE', 'RETRY_LOGIC'
    details TEXT
);
"""
CREATE_METRICS_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    worker_pool TEXT NOT NULL,
    event_type TEXT NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL,
    details_json TEXT
);
"""
CREATE_DYNAMIC_CONFIG_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS dynamic_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    last_updated TEXT NOT NULL
);
"""
# -- workspace.db Schema --
CREATE_WORKSPACE_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS problem_data_cache (
    problem_id TEXT PRIMARY KEY,
    problem_statement_html TEXT,
    reference_solution_json TEXT,          -- Metadata for the primary (highest-rated) oracle.
    reference_solution_code TEXT,          -- Source code for the primary oracle.
    secondary_reference_codes_json TEXT, -- ADD: JSON array of codes for oracles 2 through N.
    compiled_oracle_paths_json TEXT,     -- ADD: Stores paths to compiled binaries for the VJS worker.
    pretests_json TEXT,
    validated_pretests_json TEXT,        -- ADD: Stores pretests verified during calibration.
    slowness_factor REAL,                  -- ADD: Stores the calculated local vs. official judge speed ratio.
    checker_mode TEXT,                     -- ADD: Stores 'strict' or 'set_based' validation rule.
    arl_pseudocode TEXT,
    arl_reconstructed_code TEXT,
    arl_feedback TEXT,
    vjs_last_report TEXT,
    quality_analysis_json TEXT
);
"""

def populate_problems_table(cursor: sqlite3.Cursor) -> bool:
    """
    Fetches all problems from the Codeforces API and inserts them into progress.db.
    Args:
        cursor: The database cursor for progress.db.
    Returns:
        True if successful, False otherwise.
    """
    logging.info("Fetching problem list from Codeforces API...")
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.critical(f"Failed to fetch data from Codeforces API: {e}")
        return False

    if data.get('status') != 'OK':
        logging.critical(f"API returned non-OK status: {data.get('comment')}")
        return False

    problems = data['result']['problems']
    problems_to_insert = []
    for p in problems:
        if 'rating' not in p: continue
        problem_id = f"{p['contestId']}{p['index']}"
        tags = ", ".join(p.get('tags', []))
        timestamp = datetime.now().isoformat()
        problems_to_insert.append((problem_id, p['contestId'], p['index'], p['name'], p['rating'], tags, timestamp))

    try:
        cursor.executemany(
            "INSERT INTO problems (id, contest_id, problem_index, name, rating, tags, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
            problems_to_insert
        )
        logging.info(f"Successfully inserted {cursor.rowcount} new problems into progress.db.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to bulk insert problems: {e}")
        return False

def initialize_workers_table(cursor: sqlite3.Cursor) -> None:
    """
    (BUGFIX) Sets up the initial rows for the MAX number of possible workers
    across all pools. This ensures the dashboard has a row for every potential
    worker the optimizer might activate.
    Args:
        cursor: The database cursor for progress.db.
    """
    timestamp = datetime.now().isoformat()
    workers = []
    
    # BUGFIX: Use a dictionary of MAX worker counts to initialize the table
    pools = {
        'INGESTION': MAX_INGESTION_WORKERS,
        'ANALYSIS': MAX_ANALYSIS_WORKERS,
        'IMPLEMENTATION': MAX_IMPLEMENTATION_WORKERS,
        'VJS': MAX_VJS_WORKERS,
        'DATA_ASSEMBLY': MAX_DATA_ASSEMBLY_WORKERS
    }
    total_slots = sum(pools.values())
    logging.info(f"Initializing {total_slots} total worker slots in database...")

    for pool_name, max_count in pools.items():
        for i in range(1, max_count + 1):
            # Create a unique ID like "ANALYSIS-1", "ANALYSIS-2"
            worker_id = f"{pool_name}-{i}"
            workers.append((worker_id, pool_name, 'idle', timestamp))
            
    try:
        cursor.executemany("INSERT OR REPLACE INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)", workers)
        logging.info("Worker slots initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize worker slots: {e}")

def populate_initial_dynamic_config(cursor: sqlite3.Cursor) -> None:
    """
    Sets the default values for the dynamic_config table in progress.db.
    Args:
        cursor: The database cursor for progress.db.
    """
    logging.info("Populating dynamic_config with default values...")
    timestamp = datetime.now().isoformat()
    default_configs = [
        ('ingestion_worker_count', str(DEFAULT_INGESTION_WORKER_COUNT), timestamp),
        ('analysis_worker_count', str(DEFAULT_ANALYSIS_WORKER_COUNT), timestamp),
        ('implementation_worker_count', str(DEFAULT_IMPLEMENTATION_WORKER_COUNT), timestamp),
        ('vjs_worker_count', str(DEFAULT_VJS_WORKER_COUNT), timestamp),
        ('data_assembly_worker_count', str(DEFAULT_DATA_ASSEMBLY_WORKER_COUNT), timestamp),
        ('analysis_batch_size', str(DEFAULT_ANALYSIS_BATCH_SIZE), timestamp),
        ('scraper_delay_seconds', str(DEFAULT_SCRAPER_DELAY_SECONDS), timestamp), # BUGFIX: Correctly reference variable
    ]
    try:
        cursor.executemany(
            "INSERT OR REPLACE INTO dynamic_config (key, value, last_updated) VALUES (?, ?, ?)",
            default_configs
        )
        logging.info("Default dynamic configuration set successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to set default dynamic config: {e}")

def main() -> None:
    """Main function to set up and populate both databases."""
    for db_name in [PROGRESS_DB_NAME, WORKSPACE_DB_PATH]:
        if os.path.exists(db_name):
            logging.warning(f"Database '{db_name}' already exists.")
            response = input(f"This script will DELETE and re-create '{db_name}'. Continue? (y/n): ").lower()
            if response != 'y':
                logging.info("Operation cancelled by user.")
                return
            try:
                os.remove(db_name)
                logging.info(f"Removed existing database '{db_name}'.")
            except OSError as e:
                logging.critical(f"Error removing existing database: {e}")
                return

    # Setup progress.db
    try:
        logging.info(f"Setting up '{PROGRESS_DB_NAME}'...")
        with sqlite3.connect(PROGRESS_DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute(CREATE_PROBLEMS_TABLE_SQL)
            cursor.execute(CREATE_WORKERS_TABLE_SQL)
            cursor.execute(CREATE_KEY_STATUS_TABLE_SQL)
            cursor.execute(CREATE_PROCESS_HISTORY_TABLE_SQL)
            cursor.execute(CREATE_METRICS_TABLE_SQL)
            cursor.execute(CREATE_DYNAMIC_CONFIG_TABLE_SQL)
            if populate_problems_table(cursor):
                initialize_workers_table(cursor)
                populate_initial_dynamic_config(cursor)
                logging.info(f"'{PROGRESS_DB_NAME}' setup complete.")
            else:
                raise Exception("Failed to populate problems table.")
    except Exception as e:
        logging.critical(f"A critical error occurred with {PROGRESS_DB_NAME}: {e}")
        return

    # Setup workspace.db
    try:
        logging.info(f"Setting up '{WORKSPACE_DB_PATH}'...")
        with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute(CREATE_WORKSPACE_TABLE_SQL)
            logging.info(f"'{WORKSPACE_DB_PATH}' setup complete.")
    except Exception as e:
        logging.critical(f"A critical error occurred with {WORKSPACE_DB_PATH}: {e}")

if __name__ == "__main__":
    main()