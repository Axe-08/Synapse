# create_database.py (Dual-Database Setup Version)
import sqlite3
import requests
import logging
import time
import os
from datetime import datetime

# --- Configuration ---
PROGRESS_DB_NAME = 'progress.db'
WORKSPACE_DB_NAME = 'workspace.db'
API_URL = "https://codeforces.com/api/problemset.problems"

# Worker pool configuration remains the single source of truth for concurrency
INGESTION_WORKER_COUNT = 1
ARL_WORKER_COUNT = 4
VJS_WORKER_COUNT = 2
TOTAL_WORKER_COUNT = INGESTION_WORKER_COUNT + ARL_WORKER_COUNT + VJS_WORKER_COUNT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Schemas ---
CREATE_PROBLEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY, contest_id INTEGER NOT NULL, problem_index TEXT NOT NULL,
    name TEXT NOT NULL, rating INTEGER, tags TEXT,
    status TEXT NOT NULL DEFAULT 'pending_ingestion',
    retry_count INTEGER DEFAULT 0, notes TEXT, last_updated TEXT NOT NULL
);
"""
CREATE_WORKERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS live_workers (
    worker_id INTEGER PRIMARY KEY, pool TEXT NOT NULL, problem_id TEXT,
    stage TEXT, status TEXT NOT NULL DEFAULT 'idle', last_heartbeat TEXT NOT NULL
);
"""
CREATE_WORKSPACE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS problem_data_cache (
    problem_id TEXT PRIMARY KEY,
    problem_statement_html TEXT,
    reference_solution_json TEXT,
    pretests_json TEXT,
    arl_pseudocode TEXT,
    arl_reconstructed_code TEXT
);
"""

CREATE_KEY_STATUS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS key_status (
    key_fingerprint TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    status TEXT NOT NULL,
    cooldown_until REAL
);
"""

def populate_problems_table(cursor):
    """Fetches all problems from the Codeforces API and inserts them into progress.db."""
    logging.info("Fetching problem list from Codeforces API...")
    # ... (This function's logic is unchanged)
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
        cursor.executemany("INSERT INTO problems (id, contest_id, problem_index, name, rating, tags, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)", problems_to_insert)
        logging.info(f"Successfully inserted {cursor.rowcount} new problems into progress.db.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to bulk insert problems: {e}")
        return False

def initialize_workers_table(cursor):
    """Sets up the initial rows for all workers across all pools in progress.db."""
    logging.info(f"Initializing {TOTAL_WORKER_COUNT} total worker slots...")
    # ... (This function's logic is unchanged)
    timestamp = datetime.now().isoformat()
    workers = []
    worker_id_counter = 1
    for _ in range(INGESTION_WORKER_COUNT):
        workers.append((worker_id_counter, 'INGESTION', 'idle', timestamp)); worker_id_counter += 1
    for _ in range(ARL_WORKER_COUNT):
        workers.append((worker_id_counter, 'ARL', 'idle', timestamp)); worker_id_counter += 1
    for _ in range(VJS_WORKER_COUNT):
        workers.append((worker_id_counter, 'VJS', 'idle', timestamp)); worker_id_counter += 1
    try:
        cursor.executemany("INSERT OR REPLACE INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)", workers)
        logging.info("Worker slots initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize worker slots: {e}")

def main():
    """Main function to set up and populate both databases."""
    for db_name in [PROGRESS_DB_NAME, WORKSPACE_DB_NAME]:
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
            cursor.execute(CREATE_PROBLEMS_TABLE_SQL)
            cursor.execute(CREATE_WORKERS_TABLE_SQL)
            cursor.execute(CREATE_KEY_STATUS_TABLE_SQL)
            if populate_problems_table(cursor):
                initialize_workers_table(cursor)
                logging.info(f"'{PROGRESS_DB_NAME}' setup complete.")
            else:
                raise Exception("Failed to populate problems table.")
    except Exception as e:
        logging.critical(f"A critical error occurred with {PROGRESS_DB_NAME}: {e}")
        return

    # Setup workspace.db
    try:
        logging.info(f"Setting up '{WORKSPACE_DB_NAME}'...")
        with sqlite3.connect(WORKSPACE_DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_WORKSPACE_TABLE_SQL)
            logging.info(f"'{WORKSPACE_DB_NAME}' setup complete.")
    except Exception as e:
        logging.critical(f"A critical error occurred with {WORKSPACE_DB_NAME}: {e}")

if __name__ == "__main__":
    main()