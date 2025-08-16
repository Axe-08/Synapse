# synapse/workers.py (Phase 4A - Fully Instrumented)
import logging
import json
import time
from queue import Queue
from typing import Dict, Any, List

# Project-specific imports
import synapse.database as db
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.api_clients import call_gemini_analyst_batch, call_groq_implementer
from synapse.key_manager import KeyManager
from synapse.vjs import run_vjs, run_static_analysis
from synapse.data_assembly import _assemble_golden_record, _parse_memory_limit, _parse_time_limit
from synapse.data_manager import append_to_dataset

# Import config constants for retry logic
from config import MAX_ANALYSIS_RETRIES, MAX_IMPLEMENTATION_RETRIES


# --- STAGE 1: INGESTION ---
def ingestion_worker(problem: Dict[str, Any], worker_id: int, browser_queue: Queue):
    problem_id = problem['id']
    driver = None
    start_time = time.perf_counter()
    try:
        db.update_worker_status(worker_id, 'INGESTION', problem_id, 'GET_BROWSER', 'active')
        driver = browser_queue.get(timeout=30)
        if driver is None:
            db.update_worker_status(worker_id, 'INGESTION', problem_id, 'INITIALIZING', 'active')
            driver = get_authenticated_driver()
            if not driver: raise Exception("Failed to initialize a new browser session.")
        
        db.update_worker_status(worker_id, 'INGESTION', problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver)
        if not scraped_data: raise Exception("Scraper returned no data.")

        db.update_worker_status(worker_id, 'INGESTION', problem_id, 'SAVING', 'active')
        db.save_ingestion_data_to_workspace(
            problem_id=problem_id,
            html=scraped_data['page_details']['problem_statement_html'],
            ref_solution_obj=scraped_data['ref_submission'],
            ref_solution_code=scraped_data['solution_code'],
            pretests=scraped_data['pretests'],
            time_limit_raw=scraped_data['page_details']['time_limit_raw'],
            memory_limit_raw=scraped_data['page_details']['memory_limit_raw']
        )
        db.transition_to_pending_analysis(problem_id)
        logging.info(f"SUCCESS [Ingestion] for {problem_id}. -> pending_analysis")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('INGESTION', 'ingestion_task', duration_ms, True, {'problem_id': problem_id})

    except Exception as e:
        logging.error(f"FAILED [Ingestion] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'ingestion', str(e))
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('INGESTION', 'ingestion_task', duration_ms, False, {'problem_id': problem_id, 'error': str(e)})

        if driver:
            try: driver.quit()
            except: pass
        driver = None # Ensure a failed browser is discarded
    finally:
        browser_queue.put(driver)
        db.update_worker_status(worker_id, 'INGESTION', None, None, 'idle')

# --- STAGE 2: ANALYSIS (BATCHED) ---
def analysis_worker(batch: List[Dict[str, Any]], worker_id: int, gemini_km: KeyManager):
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting analysis for batch of {len(batch_ids)}: {batch_ids}")
    start_time = time.perf_counter()
    try:
        # --- Quarantine Check ---
        valid_batch_for_api = []
        batch_ids_to_query = [p['id'] for p in batch]
        
        # Use a direct connection for this read to ensure we have the latest data
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in batch_ids_to_query)
            cursor = conn.execute(f"SELECT id, analysis_try_count FROM problems WHERE id IN ({placeholders})", batch_ids_to_query)
            problem_try_counts = {row[0]: row[1] for row in cursor.fetchall()}

        workspace_data = db.get_batch_data_from_workspace(batch_ids_to_query)

        for problem in batch:
            p_id = problem['id']
            if problem_try_counts.get(p_id, 0) >= MAX_ANALYSIS_RETRIES:
                reason = f"Exceeded max analysis retries ({MAX_ANALYSIS_RETRIES})."
                logging.warning(f"QUARANTINING {p_id}: {reason}")
                db.transition_to_quarantined(p_id, reason)
            elif p_id in workspace_data:
                p_data = workspace_data[p_id]
                valid_batch_for_api.append({
                    "problem_id": p_id,
                    "html_statement": p_data.get('problem_statement_html'),
                    "reference_code": p_data.get('reference_solution_code'),
                    "vjs_report": p_data.get('last_vjs_report')
                })

        if not valid_batch_for_api:
            logging.info("Batch is empty after quarantine/data check.")
            return

        db.update_worker_status(worker_id, 'ANALYSIS', ','.join(p['problem_id'] for p in valid_batch_for_api), 'API_CALL', 'active')
        pseudocode_results = call_gemini_analyst_batch(valid_batch_for_api, gemini_km)

        db.update_worker_status(worker_id, 'ANALYSIS', ','.join(pseudocode_results.keys()), 'UPDATING_DB', 'active')
        successful_ids = list(pseudocode_results.keys())
        for problem_id, pseudocode in pseudocode_results.items():
            db.update_workspace_with_analysis_results(problem_id, pseudocode)
        
        if successful_ids:
            db.transition_batch_to_pending_implementation(successful_ids)
        
        logging.info(f"SUCCESS [Analysis] for {len(successful_ids)} problems. -> pending_implementation")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('ANALYSIS', 'analysis_batch_task', duration_ms, True, {'batch_size': len(batch_ids)})

    except Exception as e:
        logging.error(f"FAILED [Analysis] for batch {batch_ids}: {e}", exc_info=True)
        for problem_id in batch_ids:
            db.transition_to_failed(problem_id, 'analysis', str(e))
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('ANALYSIS', 'analysis_batch_task', duration_ms, False, {'batch_size': len(batch_ids), 'error': str(e)})
    finally:
        db.update_worker_status(worker_id, 'ANALYSIS', None, None, 'idle')

# --- STAGE 3: IMPLEMENTATION ---
def implementation_worker(problem: Dict[str, Any], worker_id: int, groq_km: KeyManager):
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute("SELECT implementation_try_count FROM problems WHERE id = ?", (problem_id,))
            result = cursor.fetchone()
        
        if result and result[0] >= MAX_IMPLEMENTATION_RETRIES:
            reason = f"Exceeded max implementation retries ({MAX_IMPLEMENTATION_RETRIES})."
            logging.warning(f"QUARANTINING {problem_id}: {reason}")
            db.transition_to_quarantined(problem_id, reason)
            return

        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'FETCH_DATA', 'active')
        p_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not p_data: raise Exception("Workspace data not found.")
        if not p_data.get('arl_pseudocode'): raise Exception("Pseudocode not found in workspace data.")

        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'API_CALL', 'active')
        reconstructed_code = call_groq_implementer(
            problem_html=p_data.get('problem_statement_html'),
            pseudocode=p_data.get('arl_pseudocode'),
            vjs_report=p_data.get('last_vjs_report'),
            key_manager=groq_km
        )

        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'SAVING', 'active')
        db.update_workspace_with_implementation_results(problem_id, reconstructed_code)
        db.transition_to_pending_vjs(problem_id)
        logging.info(f"SUCCESS [Implementation] for {problem_id}. -> pending_vjs")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('IMPLEMENTATION', 'implementation_task', duration_ms, True, {'problem_id': problem_id})

    except Exception as e:
        logging.error(f"FAILED [Implementation] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'implementation', str(e))
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('IMPLEMENTATION', 'implementation_task', duration_ms, False, {'problem_id': problem_id, 'error': str(e)})
    finally:
        db.update_worker_status(worker_id, 'IMPLEMENTATION', None, None, 'idle')

# --- STAGE 4: VJS (Verification & Judging Service) ---
def vjs_worker(problem: Dict[str, Any], worker_id: int):
    problem_id = problem['id']
    vjs_result = {}
    try:
        db.update_worker_status(worker_id, 'VJS', problem_id, 'FETCHING', 'active')
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found for VJS.")

        code = workspace_data.get('arl_reconstructed_code')
        pretests = json.loads(workspace_data.get('pretests_json', '[]'))
        time_limit_ms = _parse_time_limit(workspace_data.get('time_limit_raw', '1 second'))
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256 megabytes'))
        if not all([code, pretests]): raise Exception("Missing code or pretests in workspace.")

        db.update_worker_status(worker_id, 'VJS', problem_id, 'JUDGING', 'active')
        
        vjs_start_time = time.perf_counter()
        try:
            vjs_result = run_vjs(problem_id, code, pretests, time_limit_ms, memory_limit_kb)
        finally:
            # This metric is critical and must always be logged.
            duration_ms = int((time.perf_counter() - vjs_start_time) * 1000)
            success = vjs_result.get('status') == 'SUCCESS'
            db.log_metric('VJS', 'vjs_run', duration_ms, success, {'problem_id': problem_id, 'status': vjs_result.get('status')})

        logging.info(f"VJS result for {problem_id}: {vjs_result['status']}")

        if vjs_result['status'] == 'SUCCESS':
            db.update_worker_status(worker_id, 'VJS', problem_id, 'ANALYZING', 'active')
            ref_code = workspace_data.get('reference_solution_code')
            analysis_results = {
                'reference_analysis': run_static_analysis(ref_code) if ref_code else {},
                'reconstructed_analysis': run_static_analysis(code)
            }
            db.update_workspace_with_static_analysis(problem_id, json.dumps(analysis_results))
            db.transition_to_pending_data_assembly(problem_id)
        elif vjs_result['status'] == 'COMPILE_ERROR':
            db.transition_to_pending_implementation_retry(problem_id, vjs_result['report'])
        elif vjs_result['status'] in ['TIME_LIMIT_EXCEEDED', 'WRONG_ANSWER', 'RUNTIME_ERROR']:
            db.transition_to_pending_analysis_retry(problem_id, vjs_result['report'])
        else:
            raise Exception(f"VJS system error: {vjs_result.get('report', 'Unknown')}")

    except Exception as e:
        logging.error(f"FAILED [VJS] for {problem_id}: {e}", exc_info=True)
        db.transition_to_failed(problem_id, 'vjs', str(e))
    finally:
        db.update_worker_status(worker_id, 'VJS', None, None, 'idle')

# --- STAGE 5: DATA ASSEMBLY ---
def data_assembly_worker(problem: Dict[str, Any], worker_id: int):
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', problem_id, 'ASSEMBLING', 'active')
        
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found for final assembly.")

        golden_record = _assemble_golden_record(problem_id, workspace_data)
        append_to_dataset(golden_record)
        db.delete_data_from_workspace(problem_id)
        db.transition_to_completed(problem_id)

        logging.info(f"SUCCESS [Data Assembly] for {problem_id}. -> completed")
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('DATA_ASSEMBLY', 'assembly_task', duration_ms, True, {'problem_id': problem_id})
        
    except Exception as e:
        logging.error(f"FAILED [Data Assembly] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'data_assembly', str(e))
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('DATA_ASSEMBLY', 'assembly_task', duration_ms, False, {'problem_id': problem_id, 'error': str(e)})
    finally:
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', None, None, 'idle')
