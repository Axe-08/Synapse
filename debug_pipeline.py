# debug_pipeline.py
"""
A sequential, state-driven debugging script for the Project Synapse pipeline.
This script simulates the pipeline's state transitions and retry mechanisms
in a single thread. It is designed to be highly verbose, printing the
full state and data artifacts at each step to help diagnose issues.
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
    calibration_worker,
    analysis_worker,
    implementation_worker,
    vjs_worker,
    data_assembly_worker
)
from synapse.scraper import get_authenticated_driver
from create_database import (
    CREATE_PROBLEMS_TABLE_SQL, CREATE_WORKERS_TABLE_SQL,
    CREATE_PROCESS_HISTORY_TABLE_SQL, CREATE_WORKSPACE_TABLE_SQL,
    CREATE_METRICS_TABLE_SQL,
    CREATE_DYNAMIC_CONFIG_TABLE_SQL,
    CREATE_KEY_STATUS_TABLE_SQL
)
import config as default_config

# --- Configuration ---
DEBUG_PROBLEM_IDS: List[str] = ["2066B"] # Use a simple, well-known problem for debugging
MAX_ITERATIONS: int = 20 # Safety break to prevent infinite loops
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
load_dotenv()
GEMINI_API_KEYS: List[str] = [k.strip() for k in os.getenv('GEMINI_API_KEYS', '').split(',') if k.strip()]
GROQ_API_KEYS: List[str] = [k.strip() for k in os.getenv('GROQ_API_KEYS', '').split(',') if k.strip()]

def print_header(title: str) -> None:
    """Prints a formatted header to the console."""
    bar = "=" * 80
    print(f"\n{bar}\n--- {title.upper()} ---\n{bar}")

def print_workspace_details(problem_id: str, stage_name: str):
    """Prints specific fields from the workspace DB for a given problem."""
    print(f"\n--- ARTIFACTS AFTER {stage_name.upper()} for {problem_id} ---")
    try:
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
            row = cursor.fetchone()
            if not row:
                print(f"No workspace data found for {problem_id}")
                return

            fields_to_print = {
                'INGESTION': ['problem_statement_html', 'reference_solution_code', 'pretests_json'],
                'CALIBRATION': ['validated_pretests_json', 'slowness_factor', 'checker_mode', 'vjs_last_report'],
                'ANALYSIS': ['arl_pseudocode'],
                'IMPLEMENTATION': ['arl_reconstructed_code'],
                'VJS': ['vjs_last_report']
            }

            for field in fields_to_print.get(stage_name.upper(), []):
                print(f"\n>>> Field: {field}\n")
                content = row[field]
                if not content:
                    print("[EMPTY]")
                    continue
                # Try to pretty-print if it's JSON
                try:
                    parsed_json = json.loads(content)
                    print(json.dumps(parsed_json, indent=2))
                except (json.JSONDecodeError, TypeError):
                    print(content)
    except Exception as e:
        print(f"Could not print workspace details for {problem_id}: {e}")
    print("-" * 50)


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
    
    debug_progress_db = 'debug.db'
    debug_workspace_db = 'debug_workspace.db'
    
    if os.path.exists(debug_progress_db): os.remove(debug_progress_db)
    if os.path.exists(debug_workspace_db): os.remove(debug_workspace_db)
    
    db.PROGRESS_DB_PATH = debug_progress_db
    db.WORKSPACE_DB_PATH = debug_workspace_db
    db_writer.set_db_path(debug_progress_db)
    
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(CREATE_PROBLEMS_TABLE_SQL)
        conn.execute(CREATE_WORKERS_TABLE_SQL)
        conn.execute(CREATE_PROCESS_HISTORY_TABLE_SQL)
        conn.execute(CREATE_METRICS_TABLE_SQL)
        conn.execute(CREATE_DYNAMIC_CONFIG_TABLE_SQL)
        conn.execute(CREATE_KEY_STATUS_TABLE_SQL)

        for pid in DEBUG_PROBLEM_IDS:
            conn.execute("INSERT INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (pid, 'Debug', pid[:-1], pid[-1], time.time(), 'pending_ingestion'))
        for i in range(1, 6):
            conn.execute("INSERT INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)",
                         (f'DEBUG-{i}', 'DEBUG', 'idle', datetime.now().isoformat()))
        
        timestamp = datetime.now().isoformat()
        default_configs = [
            ('scraper_delay_seconds', str(default_config.DEFAULT_SCRAPER_DELAY_SECONDS), timestamp),
            ('ingestion_worker_count', str(1), timestamp),
            ('analysis_worker_count', str(1), timestamp),
            ('implementation_worker_count', str(1), timestamp),
            ('vjs_worker_count', str(1), timestamp),
            ('data_assembly_worker_count', str(1), timestamp),
            ('analysis_batch_size', str(1), timestamp),
        ]
        conn.executemany("INSERT OR REPLACE INTO dynamic_config (key, value, last_updated) VALUES (?, ?, ?)", default_configs)
                         
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(CREATE_WORKSPACE_TABLE_SQL)
        # conn.execute("ALTER TABLE problem_data_cache ADD COLUMN vjs_last_report TEXT;")


    db_writer.start()

    gemini_km = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_km = KeyManager(GROQ_API_KEYS, "GROQ")
    browser_queue: Queue = Queue(maxsize=1)
    driver = get_authenticated_driver()
    if not driver: return
    browser_queue.put(driver)
    iteration = 0
    try:
        # === MAIN STATE-DRIVEN LOOP ===
        while iteration < MAX_ITERATIONS:
            iteration += 1
            db_writer.wait_for_completion()
            time.sleep(1)
            statuses = get_all_problem_statuses()
            print_header(f"ITERATION {iteration} | CURRENT STATUSES")
            print(json.dumps(statuses, indent=2))
            
            terminal_states = {'completed', 'quarantined'} | {f'failed_{s}' for s in ['ingestion', 'calibration', 'analysis', 'implementation', 'vjs', 'data_assembly']}
            if all(s in terminal_states for s in statuses.values()):
                logging.info("All problems have reached a terminal state. Ending debug run.")
                break

            # --- Dispatch jobs based on current status ---
            for pid, status in statuses.items():
                job = {'id': pid, 'rating': 0}
                if status == 'pending_ingestion':
                    print_header(f"Dispatching '{pid}' to INGESTION worker")
                    ingestion_worker(job, 'INGESTION-1', browser_queue)
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'ingestion')

                elif status == 'pending_calibration':
                    print_header(f"Dispatching '{pid}' to CALIBRATION worker")
                    calibration_worker(job, 'CALIBRATION-1')
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'calibration')

                elif status == 'pending_analysis':
                    print_header(f"Dispatching '{pid}' to ANALYSIS worker")
                    analysis_worker([job], 'ANALYSIS-1', gemini_km)
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'analysis')

                elif status == 'pending_implementation':
                    print_header(f"Dispatching '{pid}' to IMPLEMENTATION worker")
                    implementation_worker(job, 'IMPLEMENTATION-1', groq_km)
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'implementation')
                
                elif status == 'pending_vjs':
                    print_header(f"Dispatching '{pid}' to VJS worker")
                    vjs_worker(job, 'VJS-1')
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'vjs')
                
                elif status == 'pending_data_assembly':
                    print_header(f"Dispatching '{pid}' to DATA ASSEMBLY worker")
                    data_assembly_worker(job, 'DATA_ASSEMBLY-1')
                
                elif status == 'pending_rescraping':
                    print_header(f"Dispatching '{pid}' to INGESTION worker for re-scraping")
                    ingestion_worker(job, 'INGESTION-1', browser_queue)
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'ingestion')

            time.sleep(2)

        if iteration >= MAX_ITERATIONS and not all(s in terminal_states for s in get_all_problem_statuses().values()):
            logging.warning("Max iterations reached. Ending debug run to prevent infinite loop.")

    except KeyboardInterrupt:
        logging.info("\nShutdown signal received.")
    except Exception as e:
        logging.critical("Debug pipeline failed unexpectedly.", exc_info=True)
    finally:
        # --- FINAL STATE & CLEANUP ---
        print_header("FINAL PROBLEM STATUSES")
        print(json.dumps(get_all_problem_statuses(), indent=2))
        print_header("CLEANUP")
        db_writer.stop()
        if not browser_queue.empty():
            driver_instance = browser_queue.get_nowait()
            if driver_instance: driver_instance.quit()
        if os.path.exists(debug_progress_db): os.remove(debug_progress_db)
        if os.path.exists(debug_workspace_db): os.remove(debug_workspace_db)
        logging.info("Cleaned up debug assets.")

if __name__ == "__main__":
    main()