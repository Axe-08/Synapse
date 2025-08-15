# synapse/workers.py
import logging
import time
import json
import os
from queue import Queue

# Imports needed for all workers
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Imports from your project's modules
from synapse.database import (
    update_worker_status,
    update_problem_status_to_pending_arl,
    update_problem_status_to_pending_vjs,
    update_problem_status_to_failed,
    update_problem_status_to_done,
    save_data_to_workspace,
    get_data_from_workspace,
    update_workspace_with_arl_data,
    delete_data_from_workspace
)
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.api_clients import call_gemini_analyst, call_groq_implementer
from synapse.vjs import run_vjs # Assuming this module exists
from synapse.data_manager import append_to_dataset
from synapse.key_manager import KeyManager

# Import the new data assembly helpers
from synapse.data_assembly import _assemble_golden_record

# --- Worker Functions ---
# (The ingestion_worker and arl_worker are correct as you provided them)
def ingestion_worker(problem: dict, worker_id: int, browser_queue: Queue):
    problem_id = problem['id']
    driver = None
    try:
        update_worker_status(worker_id, problem_id, 'GET_BROWSER', 'active')
        driver = browser_queue.get(timeout=10) # Wait for a browser
        if driver is None:
            update_worker_status(worker_id, problem_id, 'INITIALIZING', 'active')
            driver = get_authenticated_driver()
            if not driver: raise Exception("Failed to initialize browser.")
        
        # NOTE: Authenticated driver warm-up logic would go here,
        # but for this file, we assume it's handled in main or get_authenticated_driver.
        
        scraped_data = fetch_problem_data(problem_id, driver)
        if not scraped_data: raise Exception("Scraper returned no data.")

        update_worker_status(worker_id, problem_id, 'SAVING', 'active')
        save_data_to_workspace(
            problem_id=problem_id,
            html=scraped_data['page_details']['problem_statement_html'],
            ref_solution=scraped_data['ref_submission'],
            pretests=scraped_data['pretests'],
            ref_solution_code=scraped_data['solution_code']
        )
        update_problem_status_to_pending_arl(problem_id)
        logging.info(f"SUCCESS: Ingestion for {problem_id} complete. -> pending_arl")

    except WebDriverException as e:
        logging.error(f"Browser fault detected for {problem_id}: {e}", exc_info=False)
        if driver: driver.quit()
        driver = None
        update_problem_status_to_failed(problem_id, 'ingestion', "WebDriverException")
    except Exception as e:
        logging.error(f"FAILED Ingestion for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'ingestion', str(e))
    finally:
        if driver:
            browser_queue.put(driver)
        else:
            browser_queue.put(None)
        update_worker_status(worker_id, None, None, 'idle')

# --- Your full ARL worker implementation (as you provided it) ---
MAX_ARL_ATTEMPTS = 5
def arl_worker(problem: dict, worker_id: int, gemini_km: KeyManager, groq_km: KeyManager):
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'ARL_FETCH', 'active')
        workspace_data = get_data_from_workspace(problem_id)
        if not workspace_data:
            raise Exception("Problem data not found in workspace.")

        ref_solution_code = json.loads(workspace_data['reference_solution_json'])['code']
        problem_html = workspace_data['problem_statement_html']
        
        for attempt in range(MAX_ARL_ATTEMPTS):
            update_worker_status(worker_id, problem_id, f'ANALYST_ATTEMPT_{attempt+1}', 'active')
            feedback = workspace_data.get('arl_feedback', '')
            analyst_prompt_input = {
                "problem_html": problem_html,
                "solution_code": ref_solution_code,
                "feedback": feedback
            }
            pseudocode = call_gemini_analyst(analyst_prompt_input, gemini_km)
            
            update_worker_status(worker_id, problem_id, f'IMPLEMENTER_ATTEMPT_{attempt+1}', 'active')
            implementer_prompt_input = {
                "problem_html": problem_html,
                "pseudocode": pseudocode
            }
            reconstructed_code = call_groq_implementer(implementer_prompt_input, groq_km)
            
            update_worker_status(worker_id, problem_id, f'VJS_ATTEMPT_{attempt+1}', 'active')
            vjs_result = run_vjs(
                problem_id=problem_id,
                reconstructed_code=reconstructed_code,
                pretests=json.loads(workspace_data['pretests_json'])
            )

            if vjs_result['status'] == 'SUCCESS':
                update_problem_status_to_pending_vjs(problem_id)
                update_workspace_with_arl_data(problem_id, pseudocode, reconstructed_code)
                logging.info(f"SUCCESS: ARL completed for {problem_id} in {attempt+1} attempts. -> pending_vjs")
                return
            else:
                logging.warning(f"ARL failed for {problem_id} on attempt {attempt+1}. Reason: {vjs_result['report']}")
                workspace_data['arl_feedback'] = vjs_result['report']
        
        update_problem_status_to_failed(problem_id, 'arl', f"Failed after {MAX_ARL_ATTEMPTS} attempts. Last error: {workspace_data.get('arl_feedback', 'N/A')}")
        logging.error(f"ARL failed permanently for {problem_id}.")

    except Exception as e:
        logging.error(f"CRITICAL ARL FAILURE for {problem_id}: {e}", exc_info=True)
        update_problem_status_to_failed(problem_id, 'arl', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')

def vjs_worker(problem: dict, worker_id: int):
    """Worker for Stage 3: Verification, Judgement, Storage."""
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'FETCH_WORKSPACE', 'active')
        workspace_data = get_data_from_workspace(problem_id)
        if not workspace_data:
            raise ValueError("Workspace data not found.")
        
        update_worker_status(worker_id, problem_id, 'ASSEMBLE_RECORD', 'active')
        golden_record = _assemble_golden_record(problem_id, workspace_data)
        
        update_worker_status(worker_id, problem_id, 'SAVE_TO_DATASET', 'active')
        append_to_dataset(golden_record)
        
        # Clean up the workspace after successful processing
        delete_data_from_workspace(problem_id)
        
        update_problem_status_to_done(problem_id)
        logging.info(f"SUCCESS: VJS for {problem_id} complete. -> done")
    except Exception as e:
        logging.error(f"FAILED VJS for {problem_id}: {e}", exc_info=True)
        update_problem_status_to_failed(problem_id, 'vjs', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')