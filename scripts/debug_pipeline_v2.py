# scripts/debug_pipeline_v2.py
"""
Sequential, state-driven E2E debugging script for Project Synapse v2.0.
Simulates the full pipeline for a single problem (1022A) in one thread,
allowing for easy inspection of artifacts and logs at each step.
"""
import logging
import json
import os
import time
import sqlite3
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# --- Project Imports ---
from synapse.database_writer import db_writer
import synapse.database as db
from synapse.key_manager import KeyManager
from synapse.account_manager import AccountManager
from synapse.workers.calibration import calibration_worker
from synapse.workers.vjs import vjs_worker
from synapse.workers.data_assembly import data_assembly_worker
from synapse.workers.cf_submission import cf_submission_worker
from synapse.scraper import fetch_problem_data, get_authenticated_driver, classify_problem
from synapse.api_clients import call_gemini_analyst_batch, call_groq_implementer
from synapse.workers._shared import _score_code_quality
from synapse.api_clients import _preprocess_code_for_llm
from create_database import (
    SQLITE_PROGRESS_TABLES_SQL, SQLITE_WORKSPACE_TABLES_SQL
)

# --- Configuration ---
DEBUG_PROBLEM_ID: str = sys.argv[1] if len(sys.argv) > 1 else "4A"
MAX_ITERATIONS: int = 15
CACHE_FILE = f'debug_v2_cache_{DEBUG_PROBLEM_ID}.json'

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
GEMINI_API_KEYS: List[str] = [k.strip() for k in os.getenv('GEMINI_API_KEYS', '').split(',') if k.strip()]
GROQ_API_KEYS: List[str] = [k.strip() for k in os.getenv('GROQ_API_KEYS', '').split(',') if k.strip()]

def print_header(title: str) -> None:
    print(f"\n{'='*80}\n--- {title.upper()} ---\n{'='*80}")

def print_artifacts(problem_id: str, stage: str):
    print(f"\n--- ARTIFACTS AFTER {stage.upper()} ---")
    try:
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM problem_data_cache WHERE problem_id = ?", (problem_id,)).fetchone()
            if row:
                fields = {
                    'INGESTION': ['reference_solution_code', 'pretests_json'],
                    'CALIBRATION': ['compiled_oracle_paths_json', 'validated_pretests_json'],
                    'ANALYSIS': ['arl_pseudocode', 'quality_analysis_json'],
                    'FUZZ_GENERATION': ['input_generator_py'],
                    'IMPLEMENTATION': ['arl_reconstructed_code'],
                }
                for f in fields.get(stage.upper(), []):
                    print(f"\n>>> WORKSPACE: {f}\n")
                    content = row[f]
                    if not content: print("[EMPTY]")
                    else:
                        try: print(json.dumps(json.loads(content), indent=2)[:1000] + "\n...[truncated]")
                        except: print(str(content)[:1000] + "\n...[truncated]")
        
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
            if row:
                fields = {
                    'INGESTION': ['problem_class'],
                    'CALIBRATION': ['successful_oracles'],
                    'VJS': ['last_vjs_report'],
                    'CF_SUBMISSION': ['last_vjs_report'],
                }
                for f in fields.get(stage.upper(), []):
                    print(f"\n>>> PROGRESS: {f}\n")
                    content = row[f]
                    if not content: print("[EMPTY]")
                    else: print(str(content)[:500])
    except Exception as e:
        print(f"Artifact print failed: {e}")
    print("-" * 50)


def setup_dbs(progress_db, workspace_db):
    db.PROGRESS_DB_PATH = progress_db
    db.WORKSPACE_DB_PATH = workspace_db
    db_writer.set_db_path(progress_db)
    
    if os.path.exists(progress_db): os.remove(progress_db)
    if os.path.exists(workspace_db): os.remove(workspace_db)
    
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.executescript(SQLITE_PROGRESS_TABLES_SQL)
        conn.execute(
            "INSERT INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)",
            (DEBUG_PROBLEM_ID, 'DebugV2', '2000', 'B', time.time(), 'pending_ingestion')
        )
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.executescript(SQLITE_WORKSPACE_TABLES_SQL)

def main():
    print_header(f"V2 E2E DEBUG RUN: {DEBUG_PROBLEM_ID}")
    
    progress_db = f'debug_v2_{DEBUG_PROBLEM_ID}.db'
    workspace_db = f'debug_v2_workspace_{DEBUG_PROBLEM_ID}.db'
    setup_dbs(progress_db, workspace_db)
    db_writer.start()

    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)

    gemini_km = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_km = KeyManager(GROQ_API_KEYS, "GROQ")
    account_mgr = AccountManager.from_env()
    
    # Mock browser queue for CF submission
    class MockBrowserQueue:
        def get(self, timeout=None):
            return get_authenticated_driver(account_manager=account_mgr)
        def put(self, driver):
            driver.quit()
    
    iteration = 0
    try:
        while iteration < MAX_ITERATIONS:
            iteration += 1
            db_writer.wait_for_completion()
            time.sleep(1)
            
            with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
                row = conn.execute("SELECT status, problem_class FROM problems WHERE id = ?", (DEBUG_PROBLEM_ID,)).fetchone()
                status = row[0]
                p_class = row[1]
            
            print_header(f"ITERATION {iteration} | STATUS: {status} | CLASS: {p_class}")
            
            if status in ('completed', 'quarantined') or status.startswith('failed_'):
                break

            job = {'id': DEBUG_PROBLEM_ID, 'rating': 0, 'problem_class': p_class}
            
            if status == 'pending_ingestion':
                if 'ingestion' in cache:
                    print("Using cached ingestion data...")
                    data = cache['ingestion']
                else:
                    print("Scraping live...")
                    driver = get_authenticated_driver(account_manager=account_mgr)
                    if not driver:
                        print(f"FAILED TO SCRAPE {DEBUG_PROBLEM_ID} - Driver is None")
                        break
                    data = fetch_problem_data(DEBUG_PROBLEM_ID, driver, exclude_submission_ids=[])
                    driver.quit()
                    if not data:
                        print(f"FAILED TO SCRAPE {DEBUG_PROBLEM_ID} - Data is None")
                        break
                    cache['ingestion'] = data
                
                tags = []
                try: tags = data['successful_solutions'][0]['submission_object']['problem']['tags']
                except: pass

                p_class = classify_problem(statement_html=data['page_details']['problem_statement_html'], tags=tags)
                db.save_multi_oracle_ingestion_data(
                    DEBUG_PROBLEM_ID, data['page_details']['problem_statement_html'],
                    data['pretests'], data['successful_solutions'],
                    data['page_details']['time_limit_raw'], data['page_details']['memory_limit_raw'],
                    p_class
                )
                db.transition_to_pending_calibration(DEBUG_PROBLEM_ID)
                db_writer.wait_for_completion()
                print_artifacts(DEBUG_PROBLEM_ID, 'ingestion')

            elif status == 'pending_calibration':
                calibration_worker(job, 'CAL-1')
                db_writer.wait_for_completion()
                print_artifacts(DEBUG_PROBLEM_ID, 'calibration')

            elif status == 'pending_analysis':
                if 'analysis' in cache:
                    print("Using cached analysis...")
                    parsed_json = cache['analysis']
                else:
                    print("Calling Gemini Analyst...")
                    p_data = db.get_batch_data_from_workspace([DEBUG_PROBLEM_ID])[DEBUG_PROBLEM_ID]
                    codes = [p_data['reference_solution_code']] + json.loads(p_data.get('secondary_reference_codes_json', '[]'))
                    top_codes = [sorted([(_score_code_quality(c), c) for c in codes if c])[0][1]]
                    processed = [_preprocess_code_for_llm(c) for c in top_codes]
                    
                    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
                        vjs_rpt = conn.execute("SELECT last_vjs_report FROM problems WHERE id=?", (DEBUG_PROBLEM_ID,)).fetchone()[0]
                    
                    batch = [{"problem_id": DEBUG_PROBLEM_ID, "html_statement": p_data['problem_statement_html'], "reference_solutions": processed, "vjs_report": vjs_rpt}]
                    # Pass simplify=True if this is a retry (vjs_report present)
                    is_retry = bool(vjs_rpt)
                    parsed_json, _ = call_gemini_analyst_batch(batch, gemini_km, simplify=is_retry)
                    cache['analysis'] = parsed_json

                pseudo_dict = parsed_json.get("final_pseudocode", {})
                pseudo = pseudo_dict.get(DEBUG_PROBLEM_ID)
                if not pseudo:
                    for k, v in pseudo_dict.items():
                        if DEBUG_PROBLEM_ID in k:
                            pseudo = v
                            break
                            
                if pseudo:
                    db.update_workspace_with_analysis_results(DEBUG_PROBLEM_ID, pseudo, json.dumps(parsed_json.get("analysis", {})))
                    db.transition_batch_to_pending_fuzz_generation([DEBUG_PROBLEM_ID])
                else:
                    db.transition_to_quarantined(DEBUG_PROBLEM_ID, "Analysis failed.")
                db_writer.wait_for_completion()
                print_artifacts(DEBUG_PROBLEM_ID, 'analysis')

            elif status == 'pending_fuzz_generation':
                if 'fuzz_generation' in cache:
                    print("Using cached fuzz generation...")
                    parsed_json = cache['fuzz_generation']
                else:
                    print("Calling Gemini Fuzz Generator...")
                    p_data = db.get_batch_data_from_workspace([DEBUG_PROBLEM_ID])[DEBUG_PROBLEM_ID]
                    codes = [p_data['reference_solution_code']] + json.loads(p_data.get('secondary_reference_codes_json', '[]'))
                    analysis_doc = json.loads(p_data.get('quality_analysis_json', '{}'))
                    best_oracle_id = analysis_doc.get('analysis', {}).get('best_oracle_id', 'oracle_0')
                    oracle_index = 0
                    if 'oracle_' in best_oracle_id:
                        try: oracle_index = int(best_oracle_id.replace('oracle_', ''))
                        except: pass
                    best_oracle_code = codes[oracle_index] if oracle_index < len(codes) else codes[0]
                    
                    batch = [{"problem_id": DEBUG_PROBLEM_ID, "problem_html": p_data['problem_statement_html'], "best_oracle_code": best_oracle_code}]
                    
                    from synapse.api_clients import call_gemini_fuzz_generator_batch
                    parsed_json, _ = call_gemini_fuzz_generator_batch(batch, gemini_km)
                    cache['fuzz_generation'] = parsed_json

                gen_dict = parsed_json.get("generators", {})
                py_script = gen_dict.get(DEBUG_PROBLEM_ID)
                if not py_script:
                    for k, v in gen_dict.items():
                        if DEBUG_PROBLEM_ID in k:
                            py_script = v
                            break
                            
                if py_script:
                    py_script = py_script.replace('\\n', '\n').replace('\\"', '"')
                    db.update_workspace_with_fuzzer(DEBUG_PROBLEM_ID, py_script)
                    db.transition_batch_to_pending_implementation([DEBUG_PROBLEM_ID])
                else:
                    db.transition_to_quarantined(DEBUG_PROBLEM_ID, "Fuzz generation failed.")
                db_writer.wait_for_completion()
                print_artifacts(DEBUG_PROBLEM_ID, 'fuzz_generation')

            elif status == 'pending_implementation':
                p_data = db.get_batch_data_from_workspace([DEBUG_PROBLEM_ID])[DEBUG_PROBLEM_ID]
                with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT last_vjs_report, analysis_try_count FROM problems WHERE id=?",
                        (DEBUG_PROBLEM_ID,)
                    ).fetchone()
                vjs_rpt = row[0] if row else None
                analysis_tries = row[1] if row else 0

                from synapse.api_clients import call_gemini_implementer
                if analysis_tries >= 2:
                    print(f"Calling Gemini Implementer (ESCALATION, analysis_tries={analysis_tries})...")
                    code = call_gemini_implementer(
                        p_data['problem_statement_html'], p_data['arl_pseudocode'],
                        vjs_rpt, gemini_km, p_class
                    )
                else:
                    print("Calling Groq Implementer...")
                    code = call_groq_implementer(
                        p_data['problem_statement_html'], p_data['arl_pseudocode'],
                        vjs_rpt, groq_km, p_class
                    )

                db.update_workspace_with_implementation_results(DEBUG_PROBLEM_ID, code)

                # Routing logic
                if p_class in ('interactive', 'special_judge', 'constructive'):
                    db._update_problem_status(DEBUG_PROBLEM_ID, 'pending_cf_submission', {})
                else:
                    db.transition_to_pending_vjs(DEBUG_PROBLEM_ID)

                db_writer.wait_for_completion()
                print_artifacts(DEBUG_PROBLEM_ID, 'implementation')

            elif status == 'pending_vjs':
                print("Running local VJS...")
                vjs_worker(job, 'VJS-1')
                db_writer.wait_for_completion()
                
                with db._get_db_connection(db.PROGRESS_DB_PATH) as c:
                    new_stat = c.execute("SELECT status FROM problems WHERE id=?", (DEBUG_PROBLEM_ID,)).fetchone()[0]
                if new_stat == 'pending_implementation':
                    print("VJS failed (Compile/Logic). Retrying implementation.")
                    cache.pop('implementation', None)
                elif new_stat == 'pending_fuzz_generation':
                    print("VJS failed (Fuzz Consensus). Retrying fuzz generation.")
                    cache.pop('fuzz_generation', None)
                print_artifacts(DEBUG_PROBLEM_ID, 'vjs')

            elif status == 'pending_cf_submission':
                print("Running CF Submission Worker (Browser)...")
                q = MockBrowserQueue()
                cf_submission_worker(job, 'CF-1', q)
                db_writer.wait_for_completion()
                
                with db._get_db_connection(db.PROGRESS_DB_PATH) as c:
                    new_stat = c.execute("SELECT status FROM problems WHERE id=?", (DEBUG_PROBLEM_ID,)).fetchone()[0]
                if new_stat == 'pending_implementation':
                    print("CF rejected the solution. Retrying implementation.")
                print_artifacts(DEBUG_PROBLEM_ID, 'cf_submission')

            elif status == 'pending_data_assembly':
                print("Running Data Assembly...")
                data_assembly_worker(job, 'ASSEMBLY-1')
                db_writer.wait_for_completion()

    finally:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        print_header("FINAL STATUS")
        with db._get_db_connection(db.PROGRESS_DB_PATH) as c:
            row = c.execute("SELECT status FROM problems WHERE id=?", (DEBUG_PROBLEM_ID,)).fetchone()
            print(f"Problem {DEBUG_PROBLEM_ID}: {row[0]}")
        db_writer.stop()
        if os.path.exists(progress_db): os.remove(progress_db)
        if os.path.exists(workspace_db): os.remove(workspace_db)

if __name__ == "__main__":
    main()
