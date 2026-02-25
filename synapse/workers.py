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
from synapse.api_clients import (
    call_gemini_analyst_batch, 
    call_groq_implementer, 
    _preprocess_code_for_llm, 
    AnalysisFailedException
)
from synapse.key_manager import KeyManager
from synapse.vjs import run_vjs, run_static_analysis, run_semantic_analysis
from synapse.data_assembly import _assemble_golden_record, _parse_memory_limit, _parse_time_limit
from synapse.data_manager import append_to_dataset
from config import (
    MAX_ANALYSIS_RETRIES, 
    MAX_IMPLEMENTATION_RETRIES, 
    MAX_RESCRAPING_ATTEMPTS,
    INITIAL_CALIBRATION_TOLERANCE_FACTOR,
    N_REFERENCE_SOLUTIONS,
    MIN_VIABLE_ORACLES,
    VJS_COMPILATION_TIMEOUT
)
from concurrent.futures import ThreadPoolExecutor, as_completed # ADD THIS
from collections import Counter # ADD THIS
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

def _score_code_quality(code: str) -> int:
    """
    Calculates a simple quality score for a C++ solution.
    A lower score is better (cleaner, more standard code).
    """
    score = 0
    score += code.count("#define") * 5 
    score += code.count("#include")
    score += code.count("scanf") * 2
    score += code.count("printf") * 2
    return score

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
            successful_solutions=scraped_data['successful_solutions'],
            time_limit_raw=scraped_data['page_details']['time_limit_raw'],
            memory_limit_raw=scraped_data['page_details']['memory_limit_raw']
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
        
        calib_run_result = run_vjs(problem_id, primary_code, pretests[:1], int(time_limit_ms * 2), memory_limit_kb, suffix="_calib_run")
        
        if calib_run_result['status'] not in ['SUCCESS', 'PRESENTATION_ERROR']:
            raise Exception(f"Primary oracle failed full run during calibration: {calib_run_result['status']}")

        # 5. Calculate slowness factor and determine checker mode
        # ref_submission = json.loads(workspace_data.get('reference_solution_json', '{}'))
        # official_time_ms = ref_submission.get('timeConsumedMillis', 500)
        # local_time_ms = calib_run_result.get('execution_time_ms', official_time_ms)
        # slowness_factor = max(1.0, local_time_ms / official_time_ms if official_time_ms > 0 else 2.0)
        slowness_factor = INITIAL_CALIBRATION_TOLERANCE_FACTOR
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
        # for d in temp_dirs_to_clean:
        #     if os.path.exists(d):
        #         shutil.rmtree(d)
        db.update_worker_status(worker_id, 'CALIBRATION', None, None, 'idle')
       
       
# --- STAGE 2: ANALYSIS (BATCHED) ---

def analysis_worker(batch: List[Dict[str, Any]], worker_id: str, gemini_km: KeyManager):
    """
    Processes a batch of problems using quality filtering, pre-processing,
    and intelligent handling of partial batch success.
    (MODIFIED FOR NEW XML PROMPT AND JSON STRUCTURE)
    """
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting analysis for batch of {len(batch_ids)}: {batch_ids}")
    problem_ids_in_api_call = []

    try:
        # Pre-flight checks for retries and quarantines
        problems_to_process = []
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in batch_ids)
            cursor = conn.execute(f"SELECT id, analysis_try_count, rescraping_attempts FROM problems WHERE id IN ({placeholders})", batch_ids)
            problem_states = {row[0]: {'analysis_tries': row[1], 'rescrapes': row[2]} for row in cursor.fetchall()}

        workspace_data = db.get_batch_data_from_workspace(batch_ids)

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

        final_api_batch = []
        problem_ids_in_api_call = [p['id'] for p in problems_to_process]

        for p_info in problems_to_process:
            p_id = p_info['id']
            p_data = workspace_data.get(p_id)
            if not p_data: continue

            primary_code = p_data.get('reference_solution_code')
            secondary_codes = json.loads(p_data.get('secondary_reference_codes_json', '[]'))
            all_codes = [code for code in [primary_code] + secondary_codes if code]

            if not all_codes:
                logging.warning(f"No reference codes found for {p_id}, skipping.")
                continue

            scored_solutions = [(_score_code_quality(code), code) for code in all_codes]
            scored_solutions.sort(key=lambda x: x[0])
            top_solutions = [code for score, code in scored_solutions[:3]]
            processed_codes = [_preprocess_code_for_llm(code) for code in top_solutions]

            final_api_batch.append({
                "problem_id": p_id,
                "html_statement": p_data.get('problem_statement_html'),
                "reference_solutions": processed_codes,
                "vjs_report": p_data.get('vjs_last_report')
            })

        if not final_api_batch:
            logging.warning("API batch is empty after quality filtering.")
            return

        # --- INTELLIGENT BATCH HANDLING ---
        # NOTE: call_gemini_analyst_batch now returns the parsed JSON object directly
        parsed_json_output, raw_response_text = call_gemini_analyst_batch(final_api_batch, gemini_km)
        
        # Extract the relevant part of the JSON for processing
        pseudocode_results = parsed_json_output.get("final_pseudocode", {})
        
        successful_ids = []
        failed_ids = []

        for problem_id, pseudocode in pseudocode_results.items():
            if pseudocode is not None:
                successful_ids.append(problem_id)
            else:
                failed_ids.append(problem_id)

        if successful_ids:
            logging.info(f"SUCCESS [Analysis] for problems: {successful_ids}. -> pending_implementation")
            for problem_id in successful_ids:
                pseudocode = pseudocode_results[problem_id]
                analysis_details_json = json.dumps(parsed_json_output.get("analysis", {}))
                db.update_workspace_with_analysis_results(problem_id, pseudocode,analysis_details_json)
                db.transition_batch_to_pending_implementation([problem_id])

        if failed_ids:
            logging.warning(f"PARTIAL FAILURE [Analysis] for problems: {failed_ids}. Model returned null.")
            reasoning_data = parsed_json_output.get("reasoning", {})
            for problem_id in failed_ids:
                reason = reasoning_data.get(problem_id, "Model returned null without reasoning.")
                db.transition_to_quarantined(problem_id, f"LLM Null Failure: {reason[:1500]}")

    except Exception as e:
        logging.error(f"CRITICAL FAILURE [Analysis] for batch {batch_ids}: {e}", exc_info=True)
        for problem_id in batch_ids:
            db.transition_to_failed(problem_id, 'analysis', str(e))
    finally:
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
# In synapse/workers.py

def vjs_worker(problem: Dict[str, Any], worker_id: str):
    """
    (DEFINITIVE with User's Adaptive Threshold Logic)
    Judges code using a tiered, weighted consensus model with an adaptive
    quality threshold.
    """
    problem_id = problem['id']
    logging.info(f"[{problem_id}] Starting VJS with Adaptive Threshold...")
    db.update_worker_status(worker_id, 'VJS', problem_id, 'SETUP', 'active')
    
    vjs_temp_dir = tempfile.mkdtemp(prefix=f"vjs_{problem_id}_")
    
    try:
        # --- Data Fetching ---
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data: raise Exception("Workspace data not found for VJS.")

        reconstructed_code = workspace_data.get('arl_reconstructed_code')
        oracle_paths = json.loads(workspace_data.get('compiled_oracle_paths_json', '[]'))
        pretests = json.loads(workspace_data.get('validated_pretests_json', '[]'))
        slowness_factor = workspace_data.get('slowness_factor', 3.0)
        time_limit_ms = int(_parse_time_limit(workspace_data.get('time_limit_raw', '1s')) * slowness_factor)
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256mb'))
        analysis_json = json.loads(workspace_data.get('quality_analysis_json', '{}'))
        oracle_ratings = analysis_json.get('oracle_ratings', {})
        rating_weights = {'Excellent': 4, 'Good': 3, 'Fair': 2, 'Poor': 1}

        if not all([reconstructed_code, oracle_paths, pretests]):
            raise Exception("Missing critical data for VJS.")

        # --- STAGE 1: Run Oracles ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'ORACLE_EXECUTION', 'active')
        full_golden_input = f"{len(pretests)}\n" + "\n".join(test['input'] for test in pretests)
        golden_input_path = os.path.join(vjs_temp_dir, "golden.in")
        with open(golden_input_path, "w") as f: f.write(full_golden_input)

        oracle_full_outputs = []
        with ThreadPoolExecutor(max_workers=len(oracle_paths)) as executor:
            def run_binary_full(exec_path):
                host_dir = os.path.dirname(exec_path)
                exec_name = os.path.basename(exec_path)
                user_id = f"{os.getuid()}:{os.getgid()}"
                total_oracle_time_sec = (time_limit_ms / 1000.0) * len(pretests) + 5.0
                run_cmd = ["docker", "run", "--rm", "-u", user_id, "-i", "--ulimit", "stack=268435456", f"--memory={memory_limit_kb}k", "-v", f"{host_dir}:/app:ro", "-w", "/app", "synapse-judge", "timeout", str(total_oracle_time_sec), f"./{exec_name}"]
                with open(golden_input_path, 'r') as stdin_f:
                    proc = subprocess.run(run_cmd, stdin=stdin_f, capture_output=True, text=True, timeout=total_oracle_time_sec + 5)
                if proc.returncode != 0: return f"ORACLE_RUNTIME_ERROR_CODE_{proc.returncode}"
                return proc.stdout.strip().replace('\r\n', '\n')

            futures = {executor.submit(run_binary_full, path): path for path in oracle_paths}
            for future in as_completed(futures):
                oracle_full_outputs.append(future.result())

        # --- STAGE 2: Tiered Consensus ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'CONSENSUS_VOTE', 'active')
        consensus_output = None
        
        # Tier 1: Weighted Vote with all oracles
        scores = {out: 0 for out in oracle_full_outputs if "RUNTIME_ERROR" not in out}
        for i, output in enumerate(oracle_full_outputs):
            if output in scores:
                rating = oracle_ratings.get(f"oracle_{i}", {}).get("rating", "Poor")
                scores[output] += rating_weights.get(rating, 1)
        
        if scores:
            best_output = max(scores, key=scores.get)
            if scores[best_output] >= (MIN_VIABLE_ORACLES * rating_weights['Fair']):
                consensus_output = best_output
                logging.info(f"[{problem_id}] Consensus found by main weighted vote.")

        # Tier 2: Recount with trusted council if main vote fails
        if consensus_output is None:
            logging.warning(f"[{problem_id}] Main vote failed. Performing a recount.")
            recount_scores = {}
            trusted_council_size = 0
            for i, output in enumerate(oracle_full_outputs):
                rating = oracle_ratings.get(f"oracle_{i}", {}).get("rating", "Poor")
                if rating in ['Excellent', 'Good', 'Fair']:
                    trusted_council_size += 1
                    if "RUNTIME_ERROR" not in output:
                        weight = rating_weights.get(rating, 1)
                        if output not in recount_scores: recount_scores[output] = 0
                        recount_scores[output] += weight
            
            # --- USER'S ADAPTIVE THRESHOLD LOGIC ---
            if recount_scores:
                best_output = max(recount_scores, key=recount_scores.get)
                max_score = recount_scores[best_output]
                
                # NOTE FOR FUTURE REFINEMENT:
                # The logic below is a lenient, adaptive threshold. A stricter future version might
                # implement a "quorum check" (if trusted_council_size < MIN_VIABLE_ORACLES, fail)
                # or trigger a "re-election" (re-scraping) to find better oracles.
                min_score_threshold = min(MIN_VIABLE_ORACLES, trusted_council_size) * rating_weights['Fair']
                
                if max_score >= min_score_threshold:
                    consensus_output = best_output
                    logging.info(f"[{problem_id}] Consensus found by RECOUNT with adaptive threshold. Score: {max_score}, Threshold: {min_score_threshold}")

        # Tier 3: Quarantine if all else fails
        if consensus_output is None:
            reason = f"Consensus failed after recount. Oracle outputs: {oracle_full_outputs}"
            db.transition_to_quarantined(problem_id, reason)
            return

        golden_output_path = os.path.join(vjs_temp_dir, "golden.out")
        with open(golden_output_path, "w") as f: f.write(consensus_output)

        # --- STAGE 3: Judge AI Code ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'JUDGING_AI', 'active')
        ai_code_path = os.path.join(vjs_temp_dir, "main.cpp")
        with open(ai_code_path, "w") as f: f.write(reconstructed_code)

        user_id = f"{os.getuid()}:{os.getgid()}"
        compile_cmd = ["docker", "run", "--rm", "-u", user_id, "-v", f"{vjs_temp_dir}:/app", "-w", "/app", "synapse-judge", "g++", "main.cpp", "-o", "main", "-O2", "-std=c++23", "-static"]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=VJS_COMPILATION_TIMEOUT)

        if compile_proc.returncode != 0:
            db.transition_to_pending_implementation_retry(problem_id, compile_proc.stderr[:2000])
            return

        ai_output_path = os.path.join(vjs_temp_dir, "ai.out")
        total_time_sec = (time_limit_ms / 1000.0) * len(pretests) + 2.0
        
        docker_run_cmd = ["docker", "run", "--rm", "-u", user_id, "-i", "--ulimit", "stack=268435456", f"--memory={memory_limit_kb}k", "-v", f"{vjs_temp_dir}:/app:ro", "-w", "/app", "synapse-judge", "timeout", str(total_time_sec), "./main"]
        
        with open(golden_input_path, 'r') as stdin_f, open(ai_output_path, 'w') as stdout_f:
            run_proc = subprocess.run(docker_run_cmd, stdin=stdin_f, stdout=stdout_f, stderr=subprocess.PIPE, text=True, timeout=total_time_sec + 5)

        if run_proc.returncode != 0:
            report = f"AI code failed execution (exit code {run_proc.returncode}). Stderr: {run_proc.stderr}"
            db.transition_to_pending_analysis_retry(problem_id, report)
            return

        checker_cmd = ["python", "-m", "synapse.checker", golden_input_path, ai_output_path, golden_output_path]
        checker_proc = subprocess.run(checker_cmd, capture_output=True, text=True)

        if checker_proc.returncode != 0:
            with open(ai_output_path, 'r') as f: ai_output_text = f.read()
            report = (f"WA/PE on full test suite.\nChecker Msg: {checker_proc.stdout.strip()}")
            db.transition_to_pending_analysis_retry(problem_id, report)
            return
        
        # SUCCESS
        db.update_problem_status(problem_id, None, extra_updates={'confidence_level': 2})
        db.transition_to_pending_data_assembly(problem_id)
        logging.info(f"SUCCESS [Final VJS] for {problem_id}. All tests passed. -> pending_data_assembly")

    except Exception as e:
        logging.error(f"FAILED [Final VJS] for {problem_id}: {e}", exc_info=True)
        db.transition_to_failed(problem_id, 'vjs', str(e))
    finally:
        if os.path.exists(vjs_temp_dir):
            shutil.rmtree(vjs_temp_dir)
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
                # Clean up the compiled oracle directories after we are completely done.
        logging.info(f"[{problem_id}] Performing final cleanup of temporary files.")
        compiled_paths_json = workspace_data.get('compiled_oracle_paths_json', '[]')
        compiled_paths = json.loads(compiled_paths_json)
        # Use a set to avoid deleting the same directory multiple times
        dirs_to_delete = {os.path.dirname(p) for p in compiled_paths}
        for d in dirs_to_delete:
            if os.path.exists(d):
                shutil.rmtree(d)
                logging.info(f"[{problem_id}] Removed temporary directory: {d}")
        
        # Also clean up the workspace DB entry
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