# main.py (The Final, Corrected Orchestrator)
import argparse
import logging
import time
import threading
import os
import json
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from queue import Queue

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s')

from synapse.database import (
    get_next_jobs,
    update_problem_status_to_pending_arl,
    update_problem_status_to_failed,
    update_worker_status,
    reset_all_workers_to_idle,
    save_data_to_workspace,
    update_key_statuses,
    get_data_from_workspace # Added for future ARL use
)
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.data_manager import append_to_dataset
from synapse.key_manager import KeyManager
from synapse.api_clients import call_gemini_analyst, call_groq_implementer
from create_database import INGESTION_WORKER_COUNT, ARL_WORKER_COUNT, VJS_WORKER_COUNT

# Selenium imports for the warm-up wait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# --- Load Environment Variables ---
load_dotenv()
CF_HANDLE = os.getenv('CF_HANDLE')
GEMINI_API_KEYS = [key.strip() for key in os.getenv('GEMINI_API_KEY', '').split(',') if key.strip()]
GROQ_API_KEYS = [key.strip() for key in os.getenv('GROQ_API_KEY', '').split(',') if key.strip()]

if not GEMINI_API_KEYS or not GROQ_API_KEYS:
    logging.warning("API keys for ARL not found in .env file. ARL workers will fail.")

# --- Data Assembly Helpers ---
PROBLEM_URL_TEMPLATE = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

def _parse_time_limit(text: str) -> int:
    try: return int(float(text.split()[0]) * 1000)
    except: return 0

def _parse_memory_limit(text: str) -> int:
    try: return int(text.split()[0]) * 1024
    except: return 0

def _assemble_golden_record(problem_id: str, workspace_data: dict) -> dict:
    """Assembles the final JSON object from data stored in the workspace."""
    ref = json.loads(workspace_data['reference_solution_json'])
    page_html = workspace_data['problem_statement_html']
    pretests = json.loads(workspace_data['pretests_json'])
    
    # We need to re-parse the raw limits from the HTML for the final record
    soup = BeautifulSoup(page_html, 'html.parser')
    time_limit_raw = soup.find('div', class_='time-limit').text.replace('time limit per test', '').strip()
    memory_limit_raw = soup.find('div', class_='memory-limit').text.replace('memory limit per test', '').strip()

    return {
        "problem_id": problem_id,
        "problem_url": PROBLEM_URL_TEMPLATE.format(contestId=ref['problem']['contestId'], index=ref['problem']['index']),
        "problem_metadata": {
            "name": ref['problem']['name'], "tags": ref['problem']['tags'],
            "time_limit_ms": _parse_time_limit(time_limit_raw),
            "memory_limit_kb": _parse_memory_limit(memory_limit_raw),
        },
        "problem_statement_html": page_html,
        "pretests": pretests,
        "reference_solution": {
            "submission_id": ref['id'],
            "submission_url": SUBMISSION_URL_TEMPLATE.format(contestId=ref['contestId'], submissionId=ref['id']),
            "author_handle": ref['author']['members'][0]['handle'],
            "author_rating": ref['author'].get('rating', None),
            "language": ref['programmingLanguage'], "code": "code_is_in_workspace_db"
        },
        "verified_pseudocode": workspace_data.get('arl_pseudocode'),
        "verified_solution_code": workspace_data.get('arl_reconstructed_code')
    }

# --- Specialized Worker Functions ---

def ingestion_worker(problem: dict, worker_id: int, browser_queue: Queue):
    """Worker for Stage 1: Uses a shared, persistent browser from a queue."""
    problem_id = problem['id']
    driver = None
    fault = False
    try:
        update_worker_status(worker_id, problem_id, 'GET_BROWSER', 'active')
        driver = browser_queue.get()

        if driver is None:
            logging.info("No active browser found. Creating a new one...")
            update_worker_status(worker_id, problem_id, 'INITIALIZING', 'active')
            driver = get_authenticated_driver()
            if not driver: raise Exception("Failed to initialize browser.")
            if CF_HANDLE:
                update_worker_status(worker_id, problem_id, 'WARM-UP', 'active')
                driver.get(f"https://codeforces.com/profile/{CF_HANDLE}")
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.LINK_TEXT, CF_HANDLE)))
                logging.info("New session stabilized.")

        update_worker_status(worker_id, problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver)
        if not scraped_data: raise Exception("Scraper returned no data.")

        update_worker_status(worker_id, problem_id, 'SAVING', 'active')
        save_data_to_workspace(
            problem_id=problem_id,
            html=scraped_data['page_details']['problem_statement_html'],
            ref_solution=scraped_data['ref_submission'],
            pretests=scraped_data['pretests']
        )
        update_problem_status_to_pending_arl(problem_id)
        logging.info(f"SUCCESS for {problem_id}")
    except WebDriverException as e:
        logging.error(f"Browser fault detected for {problem_id}: {e}", exc_info=False)
        fault = True
        update_problem_status_to_failed(problem_id, 'ingestion', "WebDriverException")
    except Exception as e:
        logging.error(f"FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'ingestion', str(e))
    finally:
        if fault:
            if driver: driver.quit()
            browser_queue.put(None)
        elif driver:
            browser_queue.put(driver)
        update_worker_status(worker_id, None, None, 'idle')

def arl_worker(problem: dict, worker_id: int, gemini_km: KeyManager, groq_km: KeyManager):
    """Worker for Stage 2: Processes data with LLMs. (Placeholder)"""
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'ARL_PLACEHOLDER', 'active')
        logging.info(f"Processing {problem_id}...")
        time.sleep(10)
        logging.warning(f"Placeholder complete for {problem_id}. Moving to 'failed_arl' for now.")
        update_problem_status_to_failed(problem_id, 'arl', 'ARL stage not yet implemented.')
    except Exception as e:
        logging.error(f"FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'arl', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')

def vjs_worker(problem: dict, worker_id: int):
    """Worker for Stage 3: Verifies code in Docker. (Placeholder)"""
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'VJS_PLACEHOLDER', 'active')
        logging.info(f"Verifying {problem_id}...")
        time.sleep(5)
        logging.warning(f"Placeholder complete for {problem_id}. Moving to 'failed_vjs' for now.")
        update_problem_status_to_failed(problem_id, 'vjs', 'VJS stage not yet implemented.')
    except Exception as e:
        logging.error(f"FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'vjs', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')

def key_status_heartbeat(stop_event: threading.Event, gemini_km: KeyManager, groq_km: KeyManager):
    """A background thread that periodically saves key statuses to the DB."""
    while not stop_event.is_set():
        try:
            update_key_statuses('GEMINI', gemini_km._keys)
            update_key_statuses('GROQ', groq_km._keys)
        except Exception as e:
            logging.warning(f"Key status heartbeat failed: {e}")
        for _ in range(5):
            if stop_event.is_set(): break
            time.sleep(1)

# --- The Main Orchestrator ---
def main(args):
    """Manages worker pools for each pipeline stage."""
    reset_all_workers_to_idle()
    
    browser_queue = Queue(maxsize=1)
    browser_queue.put(None)

    gemini_key_manager = KeyManager(GEMINI_API_KEYS)
    groq_key_manager = KeyManager(GROQ_API_KEYS)
    
    stop_event = threading.Event()
    heartbeat_thread = threading.Thread(
        target=key_status_heartbeat, 
        args=(stop_event, gemini_key_manager, groq_key_manager),
        name="KeyHeartbeat",
        daemon=True
    )
    heartbeat_thread.start()

    with ThreadPoolExecutor(max_workers=INGESTION_WORKER_COUNT, thread_name_prefix='INGEST-WORKER') as ingest_pool, \
         ThreadPoolExecutor(max_workers=ARL_WORKER_COUNT, thread_name_prefix='ARL-WORKER') as arl_pool, \
         ThreadPoolExecutor(max_workers=VJS_WORKER_COUNT, thread_name_prefix='VJS-WORKER') as vjs_pool:
        try:
            while not stop_event.is_set():
                ingestion_jobs = get_next_jobs('pending_ingestion', INGESTION_WORKER_COUNT, args.min_rating, args.max_rating)
                for i, job in enumerate(ingestion_jobs):
                    ingest_pool.submit(ingestion_worker, job, i + 1, browser_queue)
                
                arl_jobs = get_next_jobs('pending_arl', ARL_WORKER_COUNT)
                for i, job in enumerate(arl_jobs):
                    arl_pool.submit(arl_worker, job, i + 1 + INGESTION_WORKER_COUNT, gemini_key_manager, groq_key_manager)
                
                vjs_jobs = get_next_jobs('pending_vjs', VJS_WORKER_COUNT)
                for i, job in enumerate(vjs_jobs):
                    vjs_pool.submit(vjs_worker, job, i + 1 + INGESTION_WORKER_COUNT + ARL_WORKER_COUNT)

                if args.run_once:
                    logging.info("--run-once: processing one batch of jobs and then exiting.")
                    break
                
                if not any([ingestion_jobs, arl_jobs, vjs_jobs]):
                    logging.info("No pending jobs in any stage. Waiting for 30 seconds...")
                    time.sleep(30)
                else:
                    time.sleep(15)

        except KeyboardInterrupt:
            logging.info("Shutdown signal received...")
        finally:
            stop_event.set()
            final_driver = browser_queue.get_nowait()
            if final_driver: final_driver.quit()
            heartbeat_thread.join(timeout=2)

    logging.info("All worker pools have shut down. Project Synapse signing off.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse stage-centric pipeline.")
    parser.add_argument("--min_rating", type=int, help="Minimum rating of problems to ingest.")
    parser.add_argument("--max_rating", type=int, help="Maximum rating of problems to ingest.")
    parser.add_argument("--run-once", action='store_true', help="Run one cycle of job fetching and then exit.")
    args = parser.parse_args()
    main(args)
