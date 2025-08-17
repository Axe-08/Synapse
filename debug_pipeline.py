# debug_pipeline.py
"""
A sequential, state-driven debugging script for the Project Synapse pipeline.

This script simulates the pipeline's state transitions and retry mechanisms
in a single thread. It runs a main loop that dispatches problems to the correct
worker based on their current status in the database.

This version operates "naturally," meaning it relies on the actual performance
of the LLMs. Retries and self-correction will only be triggered if an LLM
genuinely produces code that fails the Verification & Judging Subsystem (VJS).
"""
import logging
import json
import os
import time
import sqlite3
from queue import Queue
from datetime import datetime
from typing import Dict, Any, List
from synapse.database_writer import db_writer
from dotenv import load_dotenv

# --- Project Imports ---
import synapse.database as db
from synapse.key_manager import KeyManager
from synapse.workers import (
    ingestion_worker,
    analysis_worker,
    implementation_worker,
    vjs_worker,
    data_assembly_worker
)
from synapse.scraper import get_authenticated_driver
from create_database import (
    CREATE_PROBLEMS_TABLE_SQL, CREATE_WORKERS_TABLE_SQL,
    CREATE_PROCESS_HISTORY_TABLE_SQL, CREATE_WORKSPACE_TABLE_SQL
)

# --- Configuration ---
DEBUG_PROBLEM_IDS: List[str] = ["1003A", "1003C", "1003D"]
MAX_ITERATIONS: int = 15 # Safety break to prevent infinite loops

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
load_dotenv()
GEMINI_API_KEYS: List[str] = [k.strip() for k in os.getenv('GEMINI_API_KEYS', '').split(',') if k.strip()]
GROQ_API_KEYS: List[str] = [k.strip() for k in os.getenv('GROQ_API_KEYS', '').split(',') if k.strip()]

def print_header(title: str) -> None:
    """Prints a formatted header to the console."""
    print("\n" + "="*80)
    print(f"--- {title.upper()} ---")
    print("="*80)

def get_all_problem_statuses() -> Dict[str, str]:
    """Fetches the current status of all debug problems."""
    statuses = {}
    with db._get_db_connection('debug.db') as conn:
        placeholders = ','.join('?' for _ in DEBUG_PROBLEM_IDS)
        cursor = conn.execute(f"SELECT id, status FROM problems WHERE id IN ({placeholders})", DEBUG_PROBLEM_IDS)
        for row in cursor.fetchall():
            statuses[row[0]] = row[1]
    return statuses

def main() -> None:
    """Main execution function for the debug script."""
    if not all([GEMINI_API_KEYS, GROQ_API_KEYS]):
        logging.error("API keys not found in .env file. Exiting.")
        return

    # --- SETUP ---
    print_header(f"SETUP: PREPARING DEBUG RUN FOR {len(DEBUG_PROBLEM_IDS)} PROBLEMS")
    db_writer.start()
    if os.path.exists('debug.db'): os.remove('debug.db')
    if os.path.exists('debug_workspace.db'): os.remove('debug_workspace.db')
    db.PROGRESS_DB_PATH = 'debug.db'; db.WORKSPACE_DB_PATH = 'debug_workspace.db'

    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(CREATE_PROBLEMS_TABLE_SQL); conn.execute(CREATE_WORKERS_TABLE_SQL); conn.execute(CREATE_PROCESS_HISTORY_TABLE_SQL)
        for pid in DEBUG_PROBLEM_IDS:
            conn.execute("INSERT INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (pid, 'Debug', pid[:-1], pid[-1], time.time(), 'pending_ingestion'))
        for i in range(1, 6):
            conn.execute("INSERT INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)",
                         (i, f'DEBUG-{i}', 'idle', datetime.now().isoformat()))
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(CREATE_WORKSPACE_TABLE_SQL)

    gemini_km = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_km = KeyManager(GROQ_API_KEYS, "GROQ")
    browser_queue: Queue = Queue(maxsize=1)
    driver = get_authenticated_driver()
    if not driver: return
    browser_queue.put(driver)

    iteration = 0
    try:
        # === INITIAL INGESTION PASS ===
        print_header("STAGE 1: INITIAL INGESTION")
        for i, pid in enumerate(DEBUG_PROBLEM_IDS):
            ingestion_worker({'id': pid, 'rating': 0}, i + 1, browser_queue)
        db_writer.wait_for_completion()
        # === MAIN STATE-DRIVEN LOOP ===
        while iteration < MAX_ITERATIONS:
            iteration += 1
            statuses = get_all_problem_statuses()
            print_header(f"ITERATION {iteration} | CURRENT STATUSES")
            print(json.dumps(statuses, indent=2))

            # Check for completion
            terminal_states = {'completed', 'quarantined'} | {f'failed_{s}' for s in ['ingestion', 'analysis', 'implementation', 'vjs', 'data_assembly']}
            if all(s in terminal_states for s in statuses.values()):
                logging.info("All problems have reached a terminal state. Ending debug run.")
                break

            # --- Dispatch jobs based on current status ---
            analysis_jobs = [{'id': pid} for pid, s in statuses.items() if s == 'pending_analysis']
            if analysis_jobs:
                print_header(f"Dispatching {len(analysis_jobs)} jobs to ANALYSIS worker")
                analysis_worker(analysis_jobs, 2, gemini_km)

            for pid, status in statuses.items():
                job = {'id': pid, 'rating': 0}
                if status == 'pending_implementation':
                    print_header(f"Dispatching '{pid}' to IMPLEMENTATION worker")
                    implementation_worker(job, 3, groq_km)
                elif status == 'pending_vjs':
                    print_header(f"Dispatching '{pid}' to VJS worker")
                    vjs_worker(job, 4)
                elif status == 'pending_data_assembly':
                    print_header(f"Dispatching '{pid}' to DATA ASSEMBLY worker")
                    data_assembly_worker(job, 5)
                elif status == 'pending_rescraping':
                    print_header(f"Dispatching '{pid}' to INGESTION worker for re-scraping")
                    ingestion_worker(job, 1, browser_queue)
            db_writer.wait_for_completion()
            time.sleep(2) # Pause to allow observing state changes

        if iteration >= MAX_ITERATIONS:
            logging.warning("Max iterations reached. Ending debug run to prevent infinite loop.")

    except Exception as e:
        logging.critical("Debug pipeline failed unexpectedly.", exc_info=True)
    finally:
        # --- FINAL STATE & CLEANUP ---
        print_header("FINAL PROBLEM STATUSES")
        print(json.dumps(get_all_problem_statuses(), indent=2))
        print_header("CLEANUP")
        db_writer.stop()
        driver_instance = browser_queue.get_nowait()
        if driver_instance: driver_instance.quit()
        if os.path.exists('debug.db'): os.remove('debug.db')
        if os.path.exists('debug_workspace.db'): os.remove('debug_workspace.db')
        logging.info("Cleaned up debug assets.")

if __name__ == "__main__":
    main()