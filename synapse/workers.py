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
from typing import List, Optional, Dict, Any
import os
# Project-specific imports
import synapse.database as db
from synapse.scraper import get_authenticated_driver, fetch_problem_data, IPBanException
from synapse.api_clients import call_gemini_analyst_batch, call_groq_implementer
from synapse.key_manager import KeyManager
from synapse.vjs import run_vjs, run_static_analysis, run_semantic_analysis
from synapse.data_assembly import _assemble_golden_record, _parse_memory_limit, _parse_time_limit
from synapse.data_manager import append_to_dataset
from config import (
    MAX_ANALYSIS_RETRIES, 
    MAX_IMPLEMENTATION_RETRIES, 
    MAX_RESCRAPING_ATTEMPTS,
    INITIAL_CALIBRATION_TOLERANCE_FACTOR
)
MAX_BROWSER_USES=25
from .vjs import run_vjs, run_static_analysis, run_semantic_analysis
from .data_assembly import _parse_memory_limit, _parse_time_limit
import shutil
import subprocess
import tempfile


def _voter(outputs: List[str]) -> Optional[str]:
    """Determines the majority consensus from a list of outputs."""
    if not outputs:
        return None
    # Count the occurrences of each unique output
    counts = Counter(outputs)
    # Find the most common output and its count
    most_common, count = counts.most_common(1)[0]
    # A true majority requires more than half the votes
    if count > len(outputs) / 2:
        return most_common
    return None # Hung jury


# --- STAGE 1: INGESTION & RE-SCRAPING ---
def ingestion_worker(problem: Dict[str, Any], worker_id: str, browser_queue: Queue):
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
    db.update_worker_status(worker_id, 'INGESTION', problem_id, 'PROCESSING', 'active')

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
        # db.update_worker_status(worker_id, 'INGESTION', problem_id, 'GET_BROWSER', 'active')
        driver = browser_queue.get(timeout=300) # Long timeout to wait for a browser
        if driver is None:
            # db.update_worker_status(worker_id, 'INGESTION', problem_id, 'INITIALIZING', 'active')
            driver = get_authenticated_driver()
            if not driver: raise Exception("Failed to initialize a new browser session.")

        # Perform the scrape
        # db.update_worker_status(worker_id, 'INGESTION', problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver, exclude_submission_ids=exclude_ids)
        
        html_statement = scraped_data['page_details']['problem_statement_html']
        if "interaction protocol" in html_statement.lower() or "note that the program" in html_statement.lower():
            reason = "Skipping interactive problem."
            logging.warning(f"QUARANTINING {problem_id}: {reason}")
            db.transition_to_quarantined(problem_id, reason)
            return # Exit the worker cleanly


        if not scraped_data:
            reason = "Failed to find a new valid reference solution."
            logging.warning(f"QUARANTINING {problem_id}: {reason}")
            db.transition_to_quarantined(problem_id, reason)
            raise Exception(reason)

        # Save data and transition state
        # db.update_worker_status(worker_id, 'INGESTION', problem_id, 'SAVING', 'active')        
        db.save_multi_oracle_ingestion_data(
            problem_id=problem_id,
            html=html_statement,
            pretests=scraped_data['pretests'],
            successful_solutions=scraped_data['successful_solutions']
        )
        if is_rescraping:
            db.reset_retry_counts(problem_id)
        db.transition_to_pending_calibration(problem_id)
        logging.info(f"SUCCESS [Ingestion/Re-scrape] for {problem_id}. -> pending_calibration")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('INGESTION', 'ingestion_task', duration_ms, True, {'problem_id': problem_id, 'rescraped': is_rescraping})
    except IPBanException as e:
        logging.critical(f"STOPPING INGESTION for {problem_id} due to IP BAN.")
        # Revert the status so it can be picked up again after the ban lifts
        db.transition_to_failed(problem_id, 'ingestion', 'IP_BAN_DETECTED')
    except Exception as e:
        import traceback
        logging.error(f"Full traceback for ingestion failure on {problem_id}:")
        traceback.print_exc()
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
            if not hasattr(driver, 'uses_count'):
                driver.uses_count =0
            driver.uses_count += 1
            if driver.uses_count >= MAX_BROWSER_USES:
                logging.warning(f"Retiring browser instance after {driver.uses_count} uses to maintain stability.")
                try:
                    driver.quit()
                except Exception as e:
                    logging.error(f"Error while quitting retired browser: {e}")
                # Signal for a new driver to be created on the next run
                browser_queue.put(None)
            else:
                # Return the still-healthy driver to the queue
                browser_queue.put(driver)

        db.update_worker_status(worker_id, 'INGESTION', None, None, 'idle')

# --- NEW STAGE 2: CALIBRATION ---
def calibration_worker(problem: Dict[str, Any], worker_id: str):
    """
    Compiles all N reference solutions ("oracles"), verifies a minimum number
    are viable, and calculates a performance baseline (slowness_factor).
    """
    problem_id = problem['id']
    logging.info(f"[{problem_id}] Starting CALIBRATION stage...")
    db.update_worker_status(worker_id, 'CALIBRATION', problem_id, 'COMPILING_ORACLES', 'active')
    
    temp_dirs_to_clean = []
    try:
        # 1. Fetch all oracle codes from the workspace
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found for calibration.")

        primary_code = workspace_data.get('reference_solution_code')
        secondary_codes = json.loads(workspace_data.get('secondary_reference_codes_json', '[]'))
        all_oracle_codes = [primary_code] + secondary_codes

        # 2. Compile each oracle using the new compile_only flag
        compiled_oracle_paths = []
        for i, code in enumerate(all_oracle_codes):
            if not code: continue
            
            # Use a unique suffix for each oracle's VJS run
            vjs_suffix = f"_oracle_{i}"
            
            # The time/memory limits don't matter for compile_only, but the function requires them
            result = run_vjs(problem_id, code, [], 1000, 262144, suffix=vjs_suffix, compile_only=True)
            
            if result['status'] == 'SUCCESS':
                compiled_oracle_paths.append(result['executable_path'])
                # Keep track of the temp directory VJS created so we can clean it up
                temp_dirs_to_clean.append(os.path.dirname(result['executable_path']))
            else:
                logging.warning(f"[{problem_id}] Oracle {i} failed to compile.")

        # 3. Check if we have a quorum of viable oracles
        successful_oracles_count = len(compiled_oracle_paths)
        logging.info(f"[{problem_id}] Successfully compiled {successful_oracles_count}/{len(all_oracle_codes)} oracles.")
        
        if successful_oracles_count < MIN_VIABLE_ORACLES:
            reason = f"Failed to compile minimum number of oracles. Needed {MIN_VIABLE_ORACLES}, got {successful_oracles_count}."
            db.transition_to_quarantined(problem_id, reason)
            return

        # 4. If quorum is met, run the primary oracle to get slowness factor and validate pretests
        db.update_worker_status(worker_id, 'CALIBRATION', problem_id, 'CALCULATING_SLOWNESS', 'active')
        
        # This is a full VJS run, not compile_only
        # We use the primary oracle's code, not its pre-compiled binary for simplicity
        pretests = json.loads(workspace_data.get('pretests_json', '[]'))
        time_limit_ms = _parse_time_limit(workspace_data.get('time_limit_raw', '1s'))
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256mb'))
        
        calib_run_result = run_vjs(problem_id, primary_code, pretests, int(time_limit_ms * 2), memory_limit_kb, suffix="_calib_run")
        
        if calib_run_result['status'] not in ['SUCCESS', 'PRESENTATION_ERROR']:
            raise Exception(f"Primary oracle failed full run during calibration: {calib_run_result['status']}")

        # 5. Calculate slowness factor and determine checker mode
        ref_submission = json.loads(workspace_data.get('reference_solution_json', '{}'))
        official_time_ms = ref_submission.get('timeConsumedMillis', 500)
        local_time_ms = calib_run_result.get('execution_time_ms', official_time_ms)
        slowness_factor = max(1.0, local_time_ms / official_time_ms if official_time_ms > 0 else 2.0)
        checker_mode = 'set_based' if calib_run_result['status'] == 'PRESENTATION_ERROR' else 'strict'

        # 6. Save results to the database and transition
        db.save_calibration_results(
            problem_id, 
            successful_oracles_count,
            compiled_oracle_paths, 
            pretests, # The pretests are now "validated" by the primary oracle
            slowness_factor, 
            checker_mode
        )
        db.transition_to_pending_analysis(problem_id)
        logging.info(f"[{problem_id}] Calibration SUCCEEDED. Oracles: {successful_oracles_count}. Slowness: {slowness_factor:.2f}x. -> pending_analysis")

    except Exception as e:
        logging.error(f"FAILED [Calibration] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'calibration', str(e))
    finally:
        # Clean up all the directories left by the compile_only runs
        for d in temp_dirs_to_clean:
            if os.path.exists(d):
                shutil.rmtree(d)
        db.update_worker_status(worker_id, 'CALIBRATION', None, None, 'idle')
       
       
# --- STAGE 2: ANALYSIS (BATCHED) ---
def analysis_worker(batch: List[Dict[str, Any]], worker_id: str, gemini_km: KeyManager):
    """
    Processes a batch of problems, sending them to the Gemini "Analyst" LLM
    with multiple reference solutions to synthesize a canonical pseudocode.
    """
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting analysis for batch of {len(batch_ids)}: {batch_ids}")
    start_time = time.perf_counter()
    problem_ids_in_api_call = [] # Define here for wider scope
    try:
        # --- 1. PRE-FLIGHT CHECKS (Handles retries and quarantines) ---
        problems_to_process = []
        batch_ids_to_query = [p['id'] for p in batch]
        
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in batch_ids_to_query)
            cursor = conn.execute(f"SELECT id, analysis_try_count, rescraping_attempts FROM problems WHERE id IN ({placeholders})", batch_ids_to_query)
            problem_states = {row[0]: {'analysis_tries': row[1], 'rescrapes': row[2]} for row in cursor.fetchall()}
        
        workspace_data = db.get_batch_data_from_workspace(batch_ids_to_query)

        for problem in batch:
            p_id = problem['id']
            state = problem_states.get(p_id)
            if not state: continue
            
            if state['analysis_tries'] >= MAX_ANALYSIS_RETRIES:
                if state['rescrapes'] >= MAX_RESCRAPING_ATTEMPTS:
                    reason = f"Exceeded max analysis retries ({MAX_ANALYSIS_RETRIES}) and re-scraping attempts ({MAX_RESCRAPING_ATTEMPTS})."
                    db.transition_to_quarantined(p_id, reason)
                else:
                    ref_sol_json = workspace_data.get(p_id, {}).get('reference_solution_json', '{}')
                    failed_sub_id = json.loads(ref_sol_json).get('id', 'unknown')
                    db.transition_to_pending_rescraping(p_id, str(failed_sub_id))
            elif p_id in workspace_data:
                problems_to_process.append(problem)

        if not problems_to_process:
            logging.info("Batch is empty after pre-flight checks.")
            return

        # --- 2. NEW: CONSTRUCT THE MULTI-ORACLE API PAYLOAD ---
        final_api_batch = []
        problem_ids_in_api_call = [p['id'] for p in problems_to_process]
        
        for p_info in problems_to_process:
            p_id = p_info['id']
            p_data = workspace_data.get(p_id)
            if not p_data: continue

            primary_code = p_data.get('reference_solution_code')
            secondary_codes = json.loads(p_data.get('secondary_reference_codes_json', '[]'))
            
            all_codes = [primary_code] + secondary_codes
            all_codes = [code for code in all_codes if code] # Filter out potential None or empty strings

            if not all_codes:
                logging.warning(f"No reference codes found in workspace for {p_id}, removing from this batch.")
                problem_ids_in_api_call.remove(p_id)
                continue

            final_api_batch.append({
                "problem_id": p_id,
                "html_statement": p_data.get('problem_statement_html'),
                "reference_solutions": all_codes, # Key change: Pass the list of all oracle codes
                "vjs_report": p_data.get('vjs_last_report')
            })

        if not final_api_batch:
            logging.warning("API batch is empty after processing workspace data.")
            return

        # --- 3. API CALL AND DATABASE UPDATE ---
        db.update_worker_status(worker_id, 'ANALYSIS', ','.join(problem_ids_in_api_call), 'API_CALL', 'active')
        pseudocode_results = call_gemini_analyst_batch(final_api_batch, gemini_km)
        db.update_worker_status(worker_id, 'ANALYSIS', ','.join(pseudocode_results.keys()), 'UPDATING_DB', 'active')
        
        for problem_id, pseudocode in pseudocode_results.items():
            db.update_workspace_with_analysis_results(problem_id, pseudocode)
            
        db.transition_batch_to_pending_implementation(list(pseudocode_results.keys()))
        logging.info(f"SUCCESS [Analysis] for {len(pseudocode_results)} problems. -> pending_implementation")

    except Exception as e:
        logging.error(f"FAILED [Analysis] for batch {batch_ids}: {e}", exc_info=False)
        if problem_ids_in_api_call:
            for problem_id in problem_ids_in_api_call:
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
def vjs_worker(problem: Dict[str, Any], worker_id: str):
    """
    Judges the AI-generated code using N-Version Differential VJS.
    It runs N compiled oracles to generate a consensus ground truth for each
    test case and judges the AI's solution against that dynamic truth.
    """
    problem_id = problem['id']
    logging.info(f"[{problem_id}] Starting N-Version Differential VJS...")
    db.update_worker_status(worker_id, 'VJS', problem_id, 'SETUP', 'active')

    ai_executable_path = None
    try:
        # 1. Fetch all calibration data from the workspace
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found for VJS.")

        reconstructed_code = workspace_data.get('arl_reconstructed_code')
        oracle_paths = json.loads(workspace_data.get('compiled_oracle_paths_json', '[]'))
        pretests = json.loads(workspace_data.get('validated_pretests_json', '[]'))
        slowness_factor = workspace_data.get('slowness_factor', 2.0)
        time_limit_ms = int(_parse_time_limit(workspace_data.get('time_limit_raw', '1s')) * slowness_factor)
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256mb'))

        if not all([reconstructed_code, oracle_paths, pretests]):
            raise Exception("Missing critical data for VJS (code, oracles, or pretests).")

        # 2. Compile the AI's solution
        db.update_worker_status(worker_id, 'VJS', problem_id, 'COMPILING_AI', 'active')
        compile_result = run_vjs(problem_id, reconstructed_code, [], 1000, 262144, suffix="_ai_compile", compile_only=True)
        if compile_result['status'] != 'SUCCESS':
            db.transition_to_pending_implementation_retry(problem_id, compile_result.get('report', ''))
            return

        ai_executable_path = compile_result['executable_path']
        ai_executable_dir = os.path.dirname(ai_executable_path)

        # 3. Iterate through each pretest and perform differential verification
        for i, test in enumerate(pretests):
            test_num_str = f"Test {i+1}/{len(pretests)}"
            db.update_worker_status(worker_id, 'VJS', problem_id, f'RUNNING {test_num_str}', 'active')

            # A. Run all oracles in parallel to get their outputs
            # This is I/O bound (waiting for subprocesses), so threading is perfect.
            oracle_outputs = []
            with ThreadPoolExecutor(max_workers=len(oracle_paths)) as executor:
                # Docker command to run a pre-compiled binary
                def run_binary(exec_path, test_input):
                    host_dir = os.path.dirname(exec_path)
                    exec_name = os.path.basename(exec_path)
                    # We assume the input is small enough to be passed via stdin pipe
                    run_cmd = ["docker", "run", "--rm", "-i", f"--memory={memory_limit_kb}k", "-v", f"{host_dir}:/app:ro", "-w", "/app", "synapse-judge", "timeout", str(time_limit_ms/1000 + 1), f"./{exec_name}"]
                    proc = subprocess.run(run_cmd, input=test_input, capture_output=True, text=True, timeout=time_limit_ms/1000 + 5)
                    if proc.returncode != 0: return f"RUNTIME_ERROR_OR_TLE_{proc.returncode}"
                    return proc.stdout.strip().replace('\r\n', '\n')

                futures = {executor.submit(run_binary, path, test['input']): path for path in oracle_paths}
                for future in as_completed(futures):
                    oracle_outputs.append(future.result())

            # B. Vote to find the consensus ground truth
            consensus_output = _voter(oracle_outputs)

            # C. Handle a "Hung Jury"
            if consensus_output is None:
                reason = f"Hung Jury on {test_num_str}. Oracle outputs: {oracle_outputs}"
                db.transition_to_quarantined(problem_id, reason)
                return

            # D. Run the AI's solution
            ai_output = run_binary(ai_executable_path, test['input'])

            # E. Compare AI output to the consensus truth using our checker
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.in') as f_in, \
                 tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ans') as f_ans, \
                 tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.out') as f_out:

                f_in.write(test['input'])
                f_ans.write(consensus_output)
                f_out.write(ai_output)

                in_path, ans_path, out_path = f_in.name, f_ans.name, f_out.name

            checker_cmd = ["python", "-m", "synapse.checker", in_path, out_path, ans_path]
            checker_proc = subprocess.run(checker_cmd, capture_output=True, text=True)

            os.remove(in_path); os.remove(ans_path); os.remove(out_path)

            # F. Handle failure
            if checker_proc.returncode != 0: # 0 is ACCEPTED
                verdict = "WA" if checker_proc.returncode == 1 else "PE"
                report = (
                    f"{verdict} on {test_num_str} vs Oracle Consensus.\n"
                    f"Checker Msg: {checker_proc.stdout.strip()}\n"
                    f"--- INPUT ---\n{test['input'][:1000]}\n"
                    f"--- ORACLE CONSENSUS ---\n{consensus_output[:1000]}\n"
                    f"--- AI OUTPUT ---\n{ai_output[:1000]}"
                )
                db.transition_to_pending_analysis_retry(problem_id, report)
                return

        # 4. If all tests pass, the problem is verified!
        db.update_problem_status(problem_id, None, extra_updates={'confidence_level': 2})
        db.transition_to_pending_data_assembly(problem_id)
        logging.info(f"SUCCESS [VJS] for {problem_id}. All {len(pretests)} tests passed by consensus. -> pending_data_assembly")

    except Exception as e:
        logging.error(f"FAILED [VJS] for {problem_id}: {e}", exc_info=True)
        db.transition_to_failed(problem_id, 'vjs', str(e))
    finally:
        if ai_executable_path and os.path.exists(os.path.dirname(ai_executable_path)):
            shutil.rmtree(os.path.dirname(ai_executable_path))
        db.update_worker_status(worker_id, 'VJS', None, None, 'idle')

    # --- STAGE 5: DATA ASSEMBLY ---
def data_assembly_worker(problem: Dict[str, Any], worker_id: str):
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