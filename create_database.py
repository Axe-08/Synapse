# create_database.py (Stage-Centric Pipeline Version)
import sqlite3
import requests
import logging
import time
import os
from datetime import datetime

# --- Configuration ---
DB_NAME = 'progress.db'
API_URL = "https://codeforces.com/api/problemset.problems"

# --- NEW: Worker Pool Configuration ---
# This defines the concurrency for each stage of our pipeline.
INGESTION_WORKER_COUNT = 1
ARL_WORKER_COUNT = 4 # Tuned for network-bound tasks
VJS_WORKER_COUNT = 2 # Tuned for CPU-bound tasks
TOTAL_WORKER_COUNT = INGESTION_WORKER_COUNT + ARL_WORKER_COUNT + VJS_WORKER_COUNT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Problems Table Schema ---
CREATE_PROBLEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    contest_id INTEGER NOT NULL,
    problem_index TEXT NOT NULL,
    name TEXT NOT NULL,
    rating INTEGER,
    tags TEXT,
    -- KEY CHANGE: The default status is now the first stage of our pipeline.
    status TEXT NOT NULL DEFAULT 'pending_ingestion',
    pretest_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    notes TEXT,
    last_updated TEXT NOT NULL
);
"""

# --- Live Workers Table Schema ---
CREATE_WORKERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS live_workers (
    worker_id INTEGER PRIMARY KEY,
    -- KEY CHANGE: Tracks which pool the worker belongs to.
    pool TEXT NOT NULL, 
    problem_id TEXT,
    stage TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TEXT NOT NULL
);
"""

def populate_problems_table(cursor):
    """Fetches all problems from the Codeforces API and inserts them."""
    logging.info(f"Fetching problem list from Codeforces API...")
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
    logging.info(f"Found {len(problems)} total problems. Inserting rated problems...")
    
    problems_to_insert = []
    for p in problems:
        if 'rating' not in p: continue
        problem_id = f"{p['contestId']}{p['index']}"
        tags = ", ".join(p.get('tags', []))
        timestamp = datetime.now().isoformat()
        problems_to_insert.append(
            (problem_id, p['contestId'], p['index'], p['name'], p['rating'], tags, timestamp)
        )

    try:
        cursor.executemany("INSERT INTO problems (id, contest_id, problem_index, name, rating, tags, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)", problems_to_insert)
        logging.info(f"Successfully inserted {cursor.rowcount} new problems.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to bulk insert problems: {e}")
        return False

def initialize_workers_table(cursor):
    """Sets up the initial rows for all workers across all pools."""
    logging.info(f"Initializing {TOTAL_WORKER_COUNT} total worker slots in 'live_workers' table...")
    timestamp = datetime.now().isoformat()
    workers = []
    worker_id_counter = 1
    
    for _ in range(INGESTION_WORKER_COUNT):
        workers.append((worker_id_counter, 'INGESTION', 'idle', timestamp))
        worker_id_counter += 1
    for _ in range(ARL_WORKER_COUNT):
        workers.append((worker_id_counter, 'ARL', 'idle', timestamp))
        worker_id_counter += 1
    for _ in range(VJS_WORKER_COUNT):
        workers.append((worker_id_counter, 'VJS', 'idle', timestamp))
        worker_id_counter += 1
        
    try:
        cursor.executemany("INSERT OR REPLACE INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)", workers)
        logging.info("Worker slots initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to initialize worker slots: {e}")


def main():
    """Main function to set up and populate the database."""
    if os.path.exists(DB_NAME):
        logging.warning(f"Database '{DB_NAME}' already exists.")
        response = input("This script will DELETE and re-create the database. Continue? (y/n): ").lower()
        if response != 'y':
            logging.info("Operation cancelled.")
            return
        try:
            os.remove(DB_NAME)
            logging.info(f"Removed existing database.")
        except OSError as e:
            logging.critical(f"Error removing existing database: {e}")
            return
            
    logging.info(f"Setting up new database '{DB_NAME}'...")
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        logging.info("Creating 'problems' table...")
        cursor.execute(CREATE_PROBLEMS_TABLE_SQL)
        
        logging.info("Creating 'live_workers' table...")
        cursor.execute(CREATE_WORKERS_TABLE_SQL)
        
        if populate_problems_table(cursor):
            initialize_workers_table(cursor)
            conn.commit()
            logging.info("Database setup and population complete.")
        else:
            logging.error("Database population failed. Rolling back changes.")
            conn.rollback()
    
    except sqlite3.Error as e:
        logging.critical(f"A database error occurred: {e}")
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()