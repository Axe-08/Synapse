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

from dotenv import load_dotenv

# --- Project Imports ---
from synapse.database_writer import db_writer
import synapse.database as db
from synapse.key_manager import KeyManager
from synapse.workers import calibration_worker, vjs_worker, data_assembly_worker
from synapse.scraper import fetch_problem_data, get_authenticated_driver
from synapse.api_clients import call_gemini_analyst_batch, call_groq_implementer
from synapse.workers import _score_code_quality
from synapse.api_clients import _preprocess_code_for_llm
from create_database import (
    CREATE_PROBLEMS_TABLE_SQL, CREATE_WORKERS_TABLE_SQL,
    CREATE_PROCESS_HISTORY_TABLE_SQL, CREATE_WORKSPACE_TABLE_SQL,
    CREATE_METRICS_TABLE_SQL,
    CREATE_DYNAMIC_CONFIG_TABLE_SQL,
    CREATE_KEY_STATUS_TABLE_SQL
)
from config import N_REFERENCE_SOLUTIONS, MIN_VIABLE_ORACLES

# --- Configuration ---
DEBUG_PROBLEM_IDS: List[str] = ["2066B"]
MAX_ITERATIONS: int = 20
CACHE_FILE = 'scraped_data_cache.json'

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
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
            row = cursor.fetchone()
            if row:
                fields_to_print = {
                    'INGESTION': ['reference_solution_code', 'secondary_reference_codes_json', 'pretests_json'],
                    'CALIBRATION': ['compiled_oracle_paths_json', 'validated_pretests_json', 'slowness_factor', 'checker_mode'],
                    'ANALYSIS': ['arl_pseudocode'],
                    'IMPLEMENTATION': ['arl_reconstructed_code'],
                }
                for field in fields_to_print.get(stage_name.upper(), []):
                    print(f"\n>>> WORKSPACE Field: {field}\n")
                    content = row[field]
                    if not content: print("[EMPTY]")
                    else:
                        try: print(json.dumps(json.loads(content), indent=2))
                        except (json.JSONDecodeError, TypeError): print(content)
        
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
            row = cursor.fetchone()
            if row:
                fields_to_print_progress = {
                    'INGESTION': ['reference_submissions_json'],
                    'CALIBRATION': ['successful_oracles', 'confidence_level'],
                    'VJS': ['confidence_level', 'last_vjs_report','notes']
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
    # CORRECTED: Use the global db path instead of a hardcoded string
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        placeholders = ','.join('?' for _ in DEBUG_PROBLEM_IDS)
        cursor = conn.execute(f"SELECT id, status, successful_oracles, confidence_level FROM problems WHERE id IN ({placeholders})", DEBUG_PROBLEM_IDS)
        for row in cursor.fetchall():
            statuses[row[0]] = { "status": row[1], "successful_oracles": row[2], "confidence_level": row[3] }
    return statuses

def main() -> None:
    """Main execution function for the debug script."""
    if not all([GEMINI_API_KEYS, GROQ_API_KEYS]):
        logging.error("API keys not found in .env file. Exiting.")
        return

    print_header(f"SETUP: PREPARING DEBUG RUN FOR {len(DEBUG_PROBLEM_IDS)} PROBLEMS")
    
    debug_progress_db = 'debug.db'
    debug_workspace_db = 'debug_workspace.db'
    
    # These lines set the paths for ALL other modules, which is why using them is important.
    db.PROGRESS_DB_PATH = debug_progress_db
    db.WORKSPACE_DB_PATH = debug_workspace_db
    db_writer.set_db_path(debug_progress_db)
    
    if os.path.exists(debug_progress_db): os.remove(debug_progress_db)
    if os.path.exists(debug_workspace_db): os.remove(debug_workspace_db)
    
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
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(CREATE_WORKSPACE_TABLE_SQL)

    db_writer.start()

    debug_cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            loaded_cache = json.load(f)
        for pid, data in loaded_cache.items():
            if "ingestion_data" not in data: debug_cache[pid] = {"ingestion_data": data}
            else: debug_cache[pid] = data
        logging.info(f"Loaded and upgraded debug cache from {CACHE_FILE}")

    gemini_km = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_km = KeyManager(GROQ_API_KEYS, "GROQ")
    driver = None
    
    iteration = 0
    try:
        while iteration < MAX_ITERATIONS:
            iteration += 1
            db_writer.wait_for_completion()
            time.sleep(1)
            statuses = get_all_problem_statuses()
            print_header(f"ITERATION {iteration} | CURRENT STATUSES")
            print(json.dumps(statuses, indent=2))
            
            if all(s['status'] in {'completed', 'quarantined'} or s['status'].startswith('failed_') for s in statuses.values()):
                break

            for pid, p_state in statuses.items():
                status = p_state['status']
                job = {'id': pid, 'rating': 0}
                if pid not in debug_cache: debug_cache[pid] = {}

                if status == 'pending_ingestion':
                    if 'ingestion_data' in debug_cache[pid]:
                        print_header(f"USING CACHED INGESTION DATA for '{pid}'")
                        scraped_data = debug_cache[pid]['ingestion_data']
                    else:
                        print_header(f"SCRAPING INGESTION DATA for '{pid}'")
                        if not driver:
                            driver = get_authenticated_driver()
                            if not driver: return
                        scraped_data = fetch_problem_data(pid, driver, exclude_submission_ids=[])
                        if scraped_data:
                            debug_cache[pid]['ingestion_data'] = scraped_data
                    
                    if scraped_data:
                        db.save_multi_oracle_ingestion_data(
                            problem_id=pid, html=scraped_data['page_details']['problem_statement_html'],
                            pretests=scraped_data['pretests'], successful_solutions=scraped_data['successful_solutions'],
                            time_limit_raw=scraped_data['page_details']['time_limit_raw'], memory_limit_raw=scraped_data['page_details']['memory_limit_raw']
                        )
                        db.transition_to_pending_calibration(pid)
                    else:
                        db.transition_to_failed(pid, 'ingestion', 'Scraping returned no data.')
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'ingestion')

                elif status == 'pending_calibration':
                    print_header(f"Dispatching '{pid}' to CALIBRATION worker")
                    calibration_worker(job, 'CALIBRATION-1')
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'calibration')

                elif status == 'pending_analysis':
                    if 'analysis_data' in debug_cache[pid]:
                        print_header(f"USING CACHED ANALYSIS DATA for '{pid}'")
                        parsed_json = debug_cache[pid]['analysis_data']
                    else:
                        print_header(f"Dispatching '{pid}' to ANALYSIS service")
                        p_data = db.get_batch_data_from_workspace([pid]).get(pid)
                        state_data = get_problem_states([pid]).get(pid) # Use helper
                        # Simplified solution selection for debug
                        all_codes = [p_data.get('reference_solution_code')] + json.loads(p_data.get('secondary_reference_codes_json', '[]'))
                        top_solutions = [sorted([(_score_code_quality(c), c) for c in all_codes if c])[0][1]]
                        processed_codes = [_preprocess_code_for_llm(code) for code in top_solutions]
                        
                        api_batch = [{"problem_id": pid, "html_statement": p_data.get('problem_statement_html'), "reference_solutions": processed_codes, "vjs_report": state_data.get('vjs_report')}]
                        parsed_json, _ = call_gemini_analyst_batch(api_batch, gemini_km)
                        debug_cache[pid]['analysis_data'] = parsed_json
                    
                    pseudocode = parsed_json.get("final_pseudocode", {}).get(pid)
                    if pseudocode:
                        # Correctly save both pseudocode AND the analysis ratings JSON
                        analysis_details_json = json.dumps(parsed_json.get("analysis", {}))
                        db.update_workspace_with_analysis_results(pid, pseudocode, analysis_details_json)
                        db.transition_batch_to_pending_implementation([pid])
                    else:
                        db.transition_to_quarantined(pid, "Analysis result was null.")
           
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'analysis')

                elif status == 'pending_implementation':
                    if 'implementation_data' in debug_cache[pid]:
                        print_header(f"USING CACHED IMPLEMENTATION DATA for '{pid}'")
                        reconstructed_code = debug_cache[pid]['implementation_data']
                    else:
                        print_header(f"Dispatching '{pid}' to IMPLEMENTATION service")
                        p_data = db.get_batch_data_from_workspace([pid]).get(pid)
                        state_data = get_problem_states([pid]).get(pid) # Use helper
                        reconstructed_code = call_groq_implementer(
                            problem_html=p_data.get('problem_statement_html'), pseudocode=p_data.get('arl_pseudocode'),
                            vjs_report=state_data.get('vjs_report'), key_manager=groq_km
                        )
                        debug_cache[pid]['implementation_data'] = reconstructed_code

                    db.update_workspace_with_implementation_results(pid, reconstructed_code)
                    db.transition_to_pending_vjs(pid)
                    db_writer.wait_for_completion()
                    print_workspace_details(pid, 'implementation')
                
                elif status == 'pending_vjs':
                    print_header(f"Dispatching '{pid}' to VJS worker")
                    vjs_worker(job, 'VJS-1')
                    db_writer.wait_for_completion()
                    
                    # --- CHANGE IS HERE ---
                    new_status = get_all_problem_statuses()[pid]['status']
                    if new_status == 'pending_analysis':
                        logging.warning(f"VJS failed (Logic Error), invalidating analysis and implementation cache for '{pid}'.")
                        debug_cache[pid].pop('analysis_data', None)
                        debug_cache[pid].pop('implementation_data', None)
                    # ADD THIS BLOCK to handle compile errors
                    elif new_status == 'pending_implementation':
                        logging.warning(f"VJS failed (Compile Error), invalidating implementation cache for '{pid}'.")
                        debug_cache[pid].pop('implementation_data', None)
                    # --- END CHANGE ---
                    
                    print_workspace_details(pid, 'vjs')               
                elif status == 'pending_data_assembly':
                    print_header(f"Dispatching '{pid}' to DATA ASSEMBLY worker")
                    data_assembly_worker(job, 'DATA_ASSEMBLY-1')
                
                elif status == 'pending_rescraping':
                    print_header(f"No Rescraping logic here")
                    # ... re-scraping logic ...
            

            time.sleep(2)
    finally:
        with open(CACHE_FILE, 'w') as f:
            json.dump(debug_cache, f, indent=2)
            logging.info(f"Saved debug cache to {CACHE_FILE}")

        print_header("FINAL PROBLEM STATUSES")
        print(json.dumps(get_all_problem_statuses(), indent=2))
        print_header("CLEANUP")
        db_writer.stop()
        if driver: driver.quit()
        if os.path.exists(debug_progress_db): os.remove(debug_progress_db)
        if os.path.exists(debug_workspace_db): os.remove(debug_workspace_db)
        logging.info("Cleaned up debug assets.")

# Helper function to get states from the correct DB
def get_problem_states(problem_ids: List[str]) -> Dict[str, Dict]:
    states = {}
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        placeholders = ','.join('?' for _ in problem_ids)
        cursor = conn.execute(f"SELECT id, last_vjs_report FROM problems WHERE id IN ({placeholders})", problem_ids)
        for row in cursor.fetchall():
            states[row[0]] = {"vjs_report": row[1]}
    return states

if __name__ == "__main__":
    main()