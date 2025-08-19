# debug_pipeline.py
"""
A sequential, state-driven debugging script for the Project Synapse v2.0 pipeline.
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
from config import N_REFERENCE_SOLUTIONS, MIN_VIABLE_ORACLES # Import new v2.0 config

# --- Configuration ---
DEBUG_PROBLEM_IDS: List[str] = ["2066B"] # Target question for this debug run
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
    """Prints specific fields from both workspace and progress DBs for a given problem."""
    print(f"\n--- ARTIFACTS AFTER {stage_name.upper()} for {problem_id} ---")
    try:
        # Print from workspace.db
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
            row = cursor.fetchone()
            if not row:
                print(f"No workspace data found for {problem_id}")
            else:
                fields_to_print = {
                    'INGESTION': ['reference_solution_code', 'secondary_reference_codes_json', 'pretests_json'],
                    'CALIBRATION': ['compiled_oracle_paths_json', 'validated_pretests_json', 'slowness_factor', 'checker_mode'],
                    'ANALYSIS': ['arl_pseudocode'],
                    'IMPLEMENTATION': ['arl_reconstructed_code'],
                    'VJS': ['vjs_last_report']
                }
                for field in fields_to_print.get(stage_name.upper(), []):
                    print(f"\n>>> WORKSPACE Field: {field}\n")
                    content = row[field]
                    if not content: print("[EMPTY]")
                    else:
                        try: print(json.dumps(json.loads(content), indent=2))
                        except (json.JSONDecodeError, TypeError): print(content)
        
        # Print from progress.db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
            row = cursor.fetchone()
            if row:
                fields_to_print_progress = {
                    'INGESTION': ['reference_submissions_json'],
                    'CALIBRATION': ['successful_oracles', 'confidence_level'],
                    'VJS': ['confidence_level']
                }
                for field in fields_to_print_progress.get(stage_name.upper(), []):
                    print(f"\n>>> PROGRESS Field: {field}\n")
                    content = row[field]
                    if not content: print("[EMPTY]")
                    else:
                        try: print(json.dumps(json.loads(content), indent=2))
                        except (json.JSONDecodeError, TypeError): print(content)

    except Exception as e:
        print(f"Could not print workspace details for {problem_id}: {e}")
    print("-" * 50)

def get_all_problem_statuses() -> Dict[str, Dict]:
    """Fetches a rich status object for all debug problems."""
    statuses = {}
    with db._get_db_connection('debug.db') as conn:
        placeholders = ','.join('?' for _ in DEBUG_PROBLEM_IDS)
        cursor = conn.execute(f"SELECT id, status, successful_oracles, confidence_level FROM problems WHERE id IN ({placeholders})", DEBUG_PROBLEM_IDS)
        for row in cursor.fetchall():
            statuses[row[0]] = {
                "status": row[1],
                "successful_oracles": row[2],
                "confidence_level": row[3]
            }
    return statuses

def main() -> None:
    """Main execution function for the debug script."""
    if not all([GEMINI_API_KEYS, GROQ_API_KEYS]):
        logging.error("API keys not found in .env file. Exiting.")
        return

    print_header(f"SETUP: PREPARING DEBUG RUN FOR {len(DEBUG_PROBLEM_IDS)} PROBLEMS")
    print(f"v2.0 Config: N_REFERENCE_SOLUTIONS={N_REFERENCE_SOLUTIONS}, MIN_VIABLE_ORACLES={MIN_VIABLE_ORACLES}")
    
    debug_progress_db = 'debug.db'
    debug_workspace_db = 'debug_workspace.db'
    
    if os.path.exists(debug_progress_db): os.remove(debug_progress_db)
    if os.path.exists(debug_workspace_db): os.remove(debug_workspace_db)
    
    db.PROGRESS_DB_PATH = debug_progress_db
    db.WORKSPACE_DB_PATH = debug_workspace_db
    db_writer.set_db_path(debug_progress_db)
    
    # --- SETUP DATABASES ---
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(CREATE_PROBLEMS_TABLE_SQL)
        conn.execute(CREATE_WORKERS_TABLE_SQL)
        conn.execute(CREATE_PROCESS_HISTORY_TABLE_SQL)
        conn.execute(CREATE_METRICS_TABLE_SQL)
        conn.execute(CREATE_DYNAMIC_CONFIG_TABLE_SQL)
        conn.execute(CREATE_KEY_STATUS_TABLE_SQL)

        for pid in DEBUG_PROBLEM_IDS:
            conn.execute("INSERT INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (pid, 'Debug', '2066', 'B', time.time(), 'pending_ingestion'))
        # ... (worker and dynamic_config setup is the same)
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(CREATE_WORKSPACE_TABLE_SQL)

    db_writer.start()

    # --- INITIALIZE RESOURCES ---
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
            
            problem_statuses = [s['status'] for s in statuses.values()]
            terminal_states = {'completed', 'quarantined'} | {f'failed_{s}' for s in ['ingestion', 'calibration', 'analysis', 'implementation', 'vjs', 'data_assembly']}
            if all(s in terminal_states for s in problem_statuses):
                logging.info("All problems have reached a terminal state. Ending debug run.")
                break

            # --- Dispatch jobs based on current status ---
            for pid, p_state in statuses.items():
                status = p_state['status']
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

        if iteration >= MAX_ITERATIONS and not all(s in terminal_states for s in [s['status'] for s in get_all_problem_statuses().values()]):
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