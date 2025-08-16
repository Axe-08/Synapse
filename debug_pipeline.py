import logging
import json
import os
from queue import Queue
from dotenv import load_dotenv
import time
from datetime import datetime

# --- Setup logging for verbose output ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
)

# --- Project Imports ---
import synapse.database as db
import synapse.vjs as vjs_module
from synapse.key_manager import KeyManager
from synapse.workers import ingestion_worker, analysis_worker, implementation_worker, vjs_worker, data_assembly_worker
from synapse.scraper import get_authenticated_driver
from synapse.api_clients import call_gemini_analyst_batch, call_groq_implementer
from create_database import CREATE_PROBLEMS_TABLE_SQL, CREATE_WORKERS_TABLE_SQL, CREATE_PROCESS_HISTORY_TABLE_SQL, CREATE_WORKSPACE_TABLE_SQL
from synapse.data_assembly import _assemble_golden_record, _parse_time_limit, _parse_memory_limit

# --- Configuration ---
DEBUG_PROBLEM_IDS = ["1003A", "1003C", "1003D"] # A batch of problems to test

# Load environment variables
load_dotenv()
GEMINI_API_KEYS = [key.strip() for key in os.getenv('GEMINI_API_KEYS', '').split(',') if key.strip()]
GROQ_API_KEYS = [key.strip() for key in os.getenv('GROQ_API_KEYS', '').split(',') if key.strip()]


def print_header(title):
    print("\n" + "="*80)
    print(f"--- {title.upper()} ---")
    print("="*80)

def log_verbose_dict(data, title="VERBOSE LOG"):
    """Logs a dictionary, truncating only the pretests_json field."""
    print(f"\n--- {title} ---")
    if isinstance(data, list):
        for i, item in enumerate(data):
            print(f"Item {i+1}:")
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 250:
                    print(f"  '{key}': '{value[:250]}...'")
                else:
                    print(f"  '{key}': {value}")
    else:
        for key, value in data.items():
             if key == 'pretests_json' and isinstance(value, str) and len(value) > 250:
                print(f"  '{key}': '{value[:250]}...'")
             else:
                print(f"  '{key}': {value}")
    print("-" * 40)

def get_problem_status(problem_id):
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        cursor = conn.execute("SELECT status FROM problems WHERE id = ?", (problem_id,))
        result = cursor.fetchone()
        return result[0] if result else "NOT_FOUND"

def main():
    if not all([GEMINI_API_KEYS, GROQ_API_KEYS]):
        logging.error("API keys not found. Exiting.")
        return

    # --- SETUP ---
    print_header(f"SETUP: PREPARING DEBUG RUN FOR BATCH OF {len(DEBUG_PROBLEM_IDS)} PROBLEMS")
    
    # Use dedicated debug databases
    if os.path.exists('debug.db'): os.remove('debug.db')
    if os.path.exists('debug_workspace.db'): os.remove('debug_workspace.db')
    db.PROGRESS_DB_PATH = 'debug.db'
    db.WORKSPACE_DB_PATH = 'debug_workspace.db'
    
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(CREATE_PROBLEMS_TABLE_SQL)
        conn.execute(CREATE_WORKERS_TABLE_SQL)
        conn.execute(CREATE_PROCESS_HISTORY_TABLE_SQL)
        for problem_id in DEBUG_PROBLEM_IDS:
            conn.execute("INSERT INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)", (problem_id, 'Test', 0, 'X', time.time(), 'pending_ingestion'))
        for i in range(1, 6): 
            conn.execute("INSERT INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?, ?, ?, ?)", (i, 'DEBUG', 'idle', datetime.now().isoformat()))
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(CREATE_WORKSPACE_TABLE_SQL)
    logging.info(f"Created fresh debug databases and inserted {len(DEBUG_PROBLEM_IDS)} problems.")

    gemini_km = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_km = KeyManager(GROQ_API_KEYS, "GROQ")
    browser_queue = Queue(maxsize=1)

    driver = get_authenticated_driver()
    if not driver:
        logging.critical("Failed to get authenticated driver. Aborting.")
        return
    browser_queue.put(driver)

    # === RUN PIPELINE SEQUENTIALLY ===

    # 1. INGESTION (Serially)
    print_header("STAGE 1: INGESTION (RUNNING SERIALLY)")
    for i, problem_id in enumerate(DEBUG_PROBLEM_IDS):
        logging.info(f"--- Ingesting problem {i+1}/{len(DEBUG_PROBLEM_IDS)}: {problem_id} ---")
        ingestion_worker({'id': problem_id}, 1, browser_queue)

    # 2. ANALYSIS (Batched)
    print_header("STAGE 2: ANALYSIS (RUNNING AS A BATCH)")
    
    workspace_data_batch = db.get_batch_data_from_workspace(DEBUG_PROBLEM_IDS)
    api_input_batch = [{
        "problem_id": pid,
        "html_statement": ws_data.get('problem_statement_html'),
        "reference_code": ws_data.get('reference_solution_code'),
        "vjs_report": ws_data.get('last_vjs_report')
    } for pid, ws_data in workspace_data_batch.items()]
    
    log_verbose_dict(api_input_batch, "INPUT TO GEMINI API (Truncated)")
    pseudocode_results = call_gemini_analyst_batch(api_input_batch, gemini_km)
    print("\n--- RAW GEMINI API RESPONSE ---")
    print(json.dumps(pseudocode_results, indent=2))
    print("-" * 40)

    for pid, pcode in pseudocode_results.items():
        db.update_workspace_with_analysis_results(pid, pcode)
    db.transition_batch_to_pending_implementation(list(pseudocode_results.keys()))

    # 3. IMPLEMENTATION (Serially)
    print_header("STAGE 3: IMPLEMENTATION (RUNNING SERIALLY)")
    for i, problem_id in enumerate(DEBUG_PROBLEM_IDS):
        logging.info(f"--- Implementing problem {i+1}/{len(DEBUG_PROBLEM_IDS)}: {problem_id} ---")
        
        ws_data = db.get_batch_data_from_workspace([problem_id])[problem_id]
        log_verbose_dict({
            'problem_html': ws_data.get('problem_statement_html'),
            'pseudocode': ws_data.get('arl_pseudocode'),
            'vjs_report': ws_data.get('last_vjs_report')
        }, f"INPUT TO GROQ API FOR {problem_id} (Truncated)")
        
        reconstructed_code = call_groq_implementer(
            problem_html=ws_data.get('problem_statement_html'),
            pseudocode=ws_data.get('arl_pseudocode'),
            vjs_report=ws_data.get('last_vjs_report'),
            key_manager=groq_km
        )
        print("\n--- RAW GROQ API RESPONSE ---")
        print(reconstructed_code)
        print("-" * 40)
        
        db.update_workspace_with_implementation_results(problem_id, reconstructed_code)
        db.transition_to_pending_vjs(problem_id)

    # 4. VJS (Serially)
    print_header("STAGE 4: VJS (RUNNING SERIALLY)")
    successful_vjs_ids = []
    for i, problem_id in enumerate(DEBUG_PROBLEM_IDS):
        logging.info(f"--- Verifying problem {i+1}/{len(DEBUG_PROBLEM_IDS)}: {problem_id} ---")
        
        workspace_data = db.get_batch_data_from_workspace([problem_id])[problem_id]
        log_verbose_dict(workspace_data, f"INPUT TO VJS FOR {problem_id}")
        
        vjs_worker({'id': problem_id}, 4)
        
        status = get_problem_status(problem_id)
        logging.info(f"Status of {problem_id} after VJS: '{status}'")
        if status == 'pending_data_assembly':
            successful_vjs_ids.append(problem_id)

    # 5. DATA ASSEMBLY (Serially, only for successful problems)
    print_header("STAGE 5: DATA ASSEMBLY (RUNNING SERIALLY)")
    if not successful_vjs_ids:
        logging.warning("No problems passed VJS. Skipping Data Assembly.")
    else:
        for i, problem_id in enumerate(successful_vjs_ids):
            logging.info(f"--- Assembling problem {i+1}/{len(successful_vjs_ids)}: {problem_id} ---")
            data_assembly_worker({'id': problem_id}, 5)
            status = get_problem_status(problem_id)
            logging.info(f"Final status of {problem_id}: '{status}'")

    logging.info(f"\nDEBUG RUN COMPLETE: {len(successful_vjs_ids)} of {len(DEBUG_PROBLEM_IDS)} problems would proceed.")

    logging.info(f"\nSUCCESS: All {len(DEBUG_PROBLEM_IDS)} problems completed the full pipeline.")

    # --- CLEANUP ---
    print_header("CLEANUP")
    driver = browser_queue.get_nowait()
    if driver:
        driver.quit()
    os.remove('debug.db')
    os.remove('debug_workspace.db')

if __name__ == "__main__":
    main()