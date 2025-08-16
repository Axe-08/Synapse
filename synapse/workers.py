# synapse/workers.py
"""
This module contains the core logic for each stage of the pipeline.

Each `_worker` function is designed to be executed by a thread in a
ThreadPoolExecutor. These functions are responsible for a single, discrete
task in the data generation process. They handle fetching data from the
database, calling the necessary services (scrapers, APIs, VJS), and then
transitioning the problem to the next state based on the outcome.

The workers are the "hands" of the orchestrator, performing the actual
work required at each step of the pipeline. They are designed to be
resilient and to log their actions and performance metrics comprehensively.
"""
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
from synapse.vjs import run_vjs, run_static_analysis, run_semantic_analysis
from synapse.data_assembly import _assemble_golden_record, _parse_memory_limit, _parse_time_limit
from synapse.data_manager import append_to_dataset
from config import MAX_ANALYSIS_RETRIES, MAX_IMPLEMENTATION_RETRIES, MAX_RESCRAPING_ATTEMPTS

# --- STAGE 1: INGESTION & RE-SCRAPING ---
def ingestion_worker(problem: Dict[str, Any], worker_id: int, browser_queue: Queue):
    """
    Handles scraping all necessary data for a problem from Codeforces.
    This worker can also perform re-scraping to find a new reference solution
    if a problem fails analysis too many times.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
        browser_queue: A queue to get/return a shared browser instance.
    """
    problem_id = problem['id']
    driver = None
    start_time = time.perf_counter()
    is_rescraping = False
    try:
        # Check current state to see if this is a re-scrape job
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute("SELECT status, tried_submission_ids FROM problems WHERE id = ?", (problem_id,))
            result = cursor.fetchone()
            if not result: raise Exception(f"Problem {problem_id} not found.")
            current_status, tried_ids_str = result
            is_rescraping = current_status == 'in_progress_rescraping'
            exclude_ids = tried_ids_str.split(',') if tried_ids_str else []

        # Acquire a browser instance
        db.update_worker_status(worker_id, 'INGESTION', problem_id, 'GET_BROWSER', 'active')
        driver = browser_queue.get(timeout=300) # Long timeout to wait for a browser
        if driver is None:
            db.update_worker_status(worker_id, 'INGESTION', problem_id, 'INITIALIZING', 'active')
            driver = get_authenticated_driver()
            if not driver: raise Exception("Failed to initialize a new browser session.")

        # Perform the scrape
        db.update_worker_status(worker_id, 'INGESTION', problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver, exclude_submission_ids=exclude_ids)

        if not scraped_data:
            reason = "Failed to find a new valid reference solution."
            logging.warning(f"QUARANTINING {problem_id}: {reason}")
            db.transition_to_quarantined(problem_id, reason)
            raise Exception(reason)

        # Save data and transition state
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
        if is_rescraping:
            db.reset_retry_counts(problem_id)
        db.transition_to_pending_analysis(problem_id)
        logging.info(f"SUCCESS [Ingestion/Re-scrape] for {problem_id}. -> pending_analysis")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('INGESTION', 'ingestion_task', duration_ms, True, {'problem_id': problem_id, 'rescraped': is_rescraping})

    except Exception as e:
        if "Failed to find a new" not in str(e):
            logging.error(f"FAILED [Ingestion] for {problem_id}: {e}", exc_info=False)
            db.transition_to_failed(problem_id, 'ingestion', str(e))

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('INGESTION', 'ingestion_task', duration_ms, False, {'problem_id': problem_id, 'error': str(e)})

        # If driver creation failed or it crashed, put None back so a new one is made next time
        if 'driver' in locals() and driver is None:
            browser_queue.put(None)
            return # Don't try to put it back again in finally
            
    finally:
        if 'driver' in locals() and driver is not None:
             browser_queue.put(driver)
        db.update_worker_status(worker_id, 'INGESTION', None, None, 'idle')


# --- STAGE 2: ANALYSIS (BATCHED) ---
def analysis_worker(batch: List[Dict[str, Any]], worker_id: int, gemini_km: KeyManager):
    """
    Processes a batch of problems, sending them to the Gemini "Analyst" LLM
    to generate pseudocode. It also handles the logic for quarantining or
    triggering re-scraping for problems that have failed too many times.

    Args:
        batch: A list of problem dictionaries to process.
        worker_id: The ID of this worker thread.
        gemini_km: The KeyManager for Gemini API keys.
    """
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting analysis for batch of {len(batch_ids)}: {batch_ids}")
    start_time = time.perf_counter()
    try:
        valid_batch_for_api = []
        batch_ids_to_query = [p['id'] for p in batch]

        # Pre-fetch states and workspace data to perform checks
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in batch_ids_to_query)
            cursor = conn.execute(f"SELECT id, analysis_try_count, rescraping_attempts FROM problems WHERE id IN ({placeholders})", batch_ids_to_query)
            problem_states = {row[0]: {'analysis_tries': row[1], 'rescrapes': row[2]} for row in cursor.fetchall()}
        workspace_data = db.get_batch_data_from_workspace(batch_ids_to_query)

        # Filter the batch, applying quarantine/re-scrape logic
        for problem in batch:
            p_id = problem['id']
            state = problem_states.get(p_id)
            if not state: continue

            if state['analysis_tries'] >= MAX_ANALYSIS_RETRIES:
                if state['rescrapes'] >= MAX_RESCRAPING_ATTEMPTS:
                    reason = f"Exceeded max analysis retries ({MAX_ANALYSIS_RETRIES}) and re-scraping attempts ({MAX_RESCRAPING_ATTEMPTS})."
                    db.transition_to_quarantined(p_id, reason)
                else:
                    failed_sub_id = json.loads(workspace_data.get(p_id, {}).get('reference_solution_json', '{}')).get('id', 'unknown')
                    db.transition_to_pending_rescraping(p_id, str(failed_sub_id))
            elif p_id in workspace_data:
                p_data = workspace_data[p_id]
                valid_batch_for_api.append({
                    "problem_id": p_id,
                    "html_statement": p_data.get('problem_statement_html'),
                    "reference_code": p_data.get('reference_solution_code'),
                    "vjs_report": p_data.get('last_vjs_report')
                })

        if not valid_batch_for_api:
            logging.info("Batch is empty after pre-flight checks.")
            return

        # Call API and update database
        problem_ids_str = ','.join(p['problem_id'] for p in valid_batch_for_api)
        db.update_worker_status(worker_id, 'ANALYSIS', problem_ids_str, 'API_CALL', 'active')
        pseudocode_results = call_gemini_analyst_batch(valid_batch_for_api, gemini_km)

        db.update_worker_status(worker_id, 'ANALYSIS', ','.join(pseudocode_results.keys()), 'UPDATING_DB', 'active')
        for problem_id, pseudocode in pseudocode_results.items():
            db.update_workspace_with_analysis_results(problem_id, pseudocode)
        db.transition_batch_to_pending_implementation(list(pseudocode_results.keys()))
        logging.info(f"SUCCESS [Analysis] for {len(pseudocode_results)} problems. -> pending_implementation")

    except Exception as e:
        logging.error(f"FAILED [Analysis] for batch {batch_ids}: {e}", exc_info=False)
        for problem_id in batch_ids:
            db.transition_to_failed(problem_id, 'analysis', str(e))
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        success = 'e' not in locals() or locals()['e'] is None
        db.log_metric('ANALYSIS', 'analysis_batch_task', duration_ms, success, {'batch_size': len(batch_ids)})
        db.update_worker_status(worker_id, 'ANALYSIS', None, None, 'idle')

# --- STAGE 3: IMPLEMENTATION ---
def implementation_worker(problem: Dict[str, Any], worker_id: int, groq_km: KeyManager):
    """
    Takes pseudocode for a single problem and uses the Groq "Implementer" LLM
    to generate a C++ solution. Handles quarantine logic for problems that
    repeatedly fail to produce compilable code.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
        groq_km: The KeyManager for Groq API keys.
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        # Check for max implementation retries
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute("SELECT implementation_try_count FROM problems WHERE id = ?", (problem_id,))
            result = cursor.fetchone()
        if result and result[0] >= MAX_IMPLEMENTATION_RETRIES:
            reason = f"Exceeded max implementation retries ({MAX_IMPLEMENTATION_RETRIES})."
            db.transition_to_quarantined(problem_id, reason)
            return

        # Get data from workspace
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'FETCH_DATA', 'active')
        p_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not p_data or not p_data.get('arl_pseudocode'):
            raise Exception("Pseudocode not found in workspace data.")

        # Call API and update database
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'API_CALL', 'active')
        reconstructed_code = call_groq_implementer(
            problem_html=p_data.get('problem_statement_html'),
            pseudocode=p_data.get('arl_pseudocode'),
            vjs_report=p_data.get('last_vjs_report'),
            key_manager=groq_km
        )
        db.update_workspace_with_implementation_results(problem_id, reconstructed_code)
        db.transition_to_pending_vjs(problem_id)
        logging.info(f"SUCCESS [Implementation] for {problem_id}. -> pending_vjs")

    except Exception as e:
        logging.error(f"FAILED [Implementation] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'implementation', str(e))
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        success = 'e' not in locals() or locals()['e'] is None
        db.log_metric('IMPLEMENTATION', 'implementation_task', duration_ms, success, {'problem_id': problem_id})
        db.update_worker_status(worker_id, 'IMPLEMENTATION', None, None, 'idle')

# --- STAGE 4: VJS (Verification & Judging Service) ---
def vjs_worker(problem: Dict[str, Any], worker_id: int):
    """
    Runs the full verification and judging process for a single problem.
    It compiles and runs the AI-generated code against pretests in a Docker
    sandbox. Based on the result, it either passes the problem, sends it
    back for a retry with structured feedback, or fails it.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        db.update_worker_status(worker_id, 'VJS', problem_id, 'FETCHING', 'active')
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found.")

        code = workspace_data.get('arl_reconstructed_code')
        pretests = json.loads(workspace_data.get('pretests_json', '[]'))
        time_limit_ms = _parse_time_limit(workspace_data.get('time_limit_raw', '1 second'))
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256 megabytes'))
        if not all([code, pretests, time_limit_ms, memory_limit_kb]):
            raise Exception("Missing required data for VJS.")

        db.update_worker_status(worker_id, 'VJS', problem_id, 'JUDGING', 'active')
        vjs_result = run_vjs(problem_id, code, pretests, time_limit_ms, memory_limit_kb)
        db.log_metric('VJS', 'vjs_run', int((time.perf_counter() - start_time) * 1000), vjs_result.get('status') == 'SUCCESS', {'problem_id': problem_id, 'status': vjs_result.get('status')})

        logging.info(f"VJS result for {problem_id}: {vjs_result['status']}")

        # --- Handle VJS Outcome ---
        if vjs_result['status'] == 'SUCCESS':
            db.update_worker_status(worker_id, 'VJS', problem_id, 'ANALYZING', 'active')
            ref_code = workspace_data.get('reference_solution_code')
            analysis = {'reference_analysis': {}, 'reconstructed_analysis': {}}
            if ref_code:
                analysis['reference_analysis'] = {'cppcheck': run_static_analysis(ref_code), 'semantic': run_semantic_analysis(ref_code)}
            analysis['reconstructed_analysis'] = {'cppcheck': run_static_analysis(code), 'semantic': run_semantic_analysis(code)}
            db.update_workspace_with_quality_analysis(problem_id, json.dumps(analysis))
            db.transition_to_pending_data_assembly(problem_id)

        elif vjs_result['status'] == 'COMPILE_ERROR':
            report = f"**Compiler Output:**\n```\n{vjs_result['report']}\n```\nAnalyze the error. Common causes include missing headers or syntax errors. Fix the code so it compiles."
            db.transition_to_pending_implementation_retry(problem_id, report)

        elif vjs_result['status'] in ['TIME_LIMIT_EXCEEDED', 'WRONG_ANSWER', 'RUNTIME_ERROR']:
            report = ""
            if vjs_result['status'] == 'WRONG_ANSWER' and 'details' in vjs_result:
                d = vjs_result['details']
                report = f"**Analysis of Failure on Test Case #{d.get('test_case')}**:\n**Input:**\n```\n{d.get('input')}\n```\n**Expected Output:**\n```\n{d.get('expected_output')}\n```\n**Your Code's Output:**\n```\n{d.get('actual_output')}\n```\n"
            else:
                report = f"**Failure Type:** {vjs_result['status']}\n**Report:** {vjs_result['report']}\n"
            report += "The algorithm is flawed. Re-evaluate the logic and generate new, correct pseudocode."
            db.transition_to_pending_analysis_retry(problem_id, report)
        else:
            raise Exception(f"VJS system error: {vjs_result.get('report', 'Unknown')}")

    except Exception as e:
        logging.error(f"FAILED [VJS] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'vjs', str(e))
    finally:
        db.update_worker_status(worker_id, 'VJS', None, None, 'idle')

# --- STAGE 5: DATA ASSEMBLY ---
def data_assembly_worker(problem: Dict[str, Any], worker_id: int):
    """
    Performs the final step for a successfully verified problem. It assembles
    the "golden record" from all the data in the workspace, appends it to the
    final dataset.jsonl file, and cleans up the temporary data.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', problem_id, 'ASSEMBLING', 'active')
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found.")

        golden_record = _assemble_golden_record(problem_id, workspace_data)
        append_to_dataset(golden_record)
        db.delete_data_from_workspace(problem_id)
        db.transition_to_completed(problem_id)

        logging.info(f"SUCCESS [Data Assembly] for {problem_id}. -> completed")

    except Exception as e:
        logging.error(f"FAILED [Data Assembly] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'data_assembly', str(e))
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        success = 'e' not in locals() or locals()['e'] is None
        db.log_metric('DATA_ASSEMBLY', 'assembly_task', duration_ms, success, {'problem_id': problem_id})
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', None, None, 'idle')