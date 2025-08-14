# main.py (The Final, Stabilized Factory Manager)
import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import os
from dotenv import load_dotenv

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from synapse.database import (
    get_next_jobs,
    update_problem_status_to_pending_arl,
    update_problem_status_to_failed,
    update_worker_status,
    reset_all_workers_to_idle
)
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.data_manager import append_to_dataset
from create_database import INGESTION_WORKER_COUNT, ARL_WORKER_COUNT, VJS_WORKER_COUNT

# Selenium imports for the warm-up wait
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Load environment variables to get CF_HANDLE
load_dotenv()
CF_HANDLE = os.getenv('CF_HANDLE')

# --- Data Assembly Helpers ---
PROBLEM_URL_TEMPLATE = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

def _parse_time_limit(text: str) -> int:
    try: return int(float(text.split()[0]) * 1000)
    except: return 0

def _parse_memory_limit(text: str) -> int:
    try: return int(text.split()[0]) * 1024
    except: return 0

def _assemble_golden_record(scraped_data: dict) -> dict:
    ref = scraped_data['ref_submission']
    page = scraped_data['page_details']
    return {
        "problem_id": scraped_data['problem_id'],
        "problem_url": PROBLEM_URL_TEMPLATE.format(contestId=ref['problem']['contestId'], index=ref['problem']['index']),
        "problem_metadata": {
            "name": ref['problem']['name'], "tags": ref['problem']['tags'],
            "time_limit_ms": _parse_time_limit(page['time_limit_raw']),
            "memory_limit_kb": _parse_memory_limit(page['memory_limit_raw']),
            "pretest_source": scraped_data['pretest_source']
        },
        "problem_statement_html": page['problem_statement_html'],
        "pretests": scraped_data['pretests'],
        "reference_solution": {
            "submission_id": ref['id'],
            "submission_url": SUBMISSION_URL_TEMPLATE.format(contestId=ref['contestId'], submissionId=ref['id']),
            "author_handle": ref['author']['members'][0]['handle'],
            "author_rating": ref['author'].get('rating', None),
            "language": ref['programmingLanguage'], "code": scraped_data['solution_code']
        },
        "verified_pseudocode": None,
        "verified_solution_code": None
    }

# --- Specialized Worker Functions ---

def ingestion_worker(problem: dict, worker_id: int):
    """Worker for Stage 1: Fetches all raw data for a problem."""
    problem_id = problem['id']
    driver = None
    try:
        update_worker_status(worker_id, problem_id, 'INITIALIZING', 'active')
        driver = get_authenticated_driver()
        if not driver: raise Exception("Failed to initialize browser.")

        # --- KEY ADDITION: Session Warm-up ---
        if CF_HANDLE:
            update_worker_status(worker_id, problem_id, 'WARM-UP', 'active')
            logging.info(f"Worker {worker_id}: Warming up session...")
            driver.get(f"https://codeforces.com/profile/{CF_HANDLE}")
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.LINK_TEXT, CF_HANDLE)))
            logging.info(f"Worker {worker_id}: Session stabilized.")
        # ------------------------------------

        update_worker_status(worker_id, problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver)
        if not scraped_data: raise Exception("Scraper returned no data.")

        update_worker_status(worker_id, problem_id, 'SAVING', 'active')
        final_record = _assemble_golden_record(scraped_data)
        append_to_dataset(final_record)
        
        pretest_count = len(final_record['pretests'])
        update_problem_status_to_pending_arl(problem_id, pretest_count)
        logging.info(f"INGESTION Worker {worker_id}: SUCCESS for {problem_id}")
    except Exception as e:
        logging.error(f"INGESTION Worker {worker_id}: FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'ingestion', str(e))
    finally:
        if driver: driver.quit()
        update_worker_status(worker_id, None, None, 'idle')

def arl_worker(problem: dict, worker_id: int):
    """Worker for Stage 2: Processes data with LLMs. (Placeholder)"""
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'ARL_ANALYST', 'active')
        logging.info(f"ARL Worker {worker_id}: Processing {problem_id}...")
        time.sleep(10) # Simulate LLM API call
        logging.warning(f"ARL Worker {worker_id}: Placeholder complete for {problem_id}. Moving to 'failed_arl' for now.")
        update_problem_status_to_failed(problem_id, 'arl', 'ARL stage not yet implemented.')
    except Exception as e:
        logging.error(f"ARL Worker {worker_id}: FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'arl', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')

def vjs_worker(problem: dict, worker_id: int):
    """Worker for Stage 3: Verifies code in Docker. (Placeholder)"""
    problem_id = problem['id']
    try:
        update_worker_status(worker_id, problem_id, 'VJS_VERIFYING', 'active')
        logging.info(f"VJS Worker {worker_id}: Verifying {problem_id}...")
        time.sleep(5) # Simulate Docker verification
        logging.warning(f"VJS Worker {worker_id}: Placeholder complete for {problem_id}. Moving to 'failed_vjs' for now.")
        update_problem_status_to_failed(problem_id, 'vjs', 'VJS stage not yet implemented.')
    except Exception as e:
        logging.error(f"VJS Worker {worker_id}: FAILED for {problem_id}: {e}", exc_info=False)
        update_problem_status_to_failed(problem_id, 'vjs', str(e))
    finally:
        update_worker_status(worker_id, None, None, 'idle')

# --- The Main Orchestrator ---

def main(args):
    """The Factory Manager: Manages worker pools for each pipeline stage."""
    reset_all_workers_to_idle()
    
    with ThreadPoolExecutor(max_workers=INGESTION_WORKER_COUNT, thread_name_prefix='INGEST') as ingest_pool, \
         ThreadPoolExecutor(max_workers=ARL_WORKER_COUNT, thread_name_prefix='ARL') as arl_pool, \
         ThreadPoolExecutor(max_workers=VJS_WORKER_COUNT, thread_name_prefix='VJS') as vjs_pool:

        stop_event = threading.Event()
        def shutdown():
            logging.info("Shutdown signal received. Finishing active jobs...")
            stop_event.set()

        try:
            while not stop_event.is_set():
                ingestion_jobs = get_next_jobs('pending_ingestion', INGESTION_WORKER_COUNT, args.min_rating, args.max_rating)
                arl_jobs = get_next_jobs('pending_arl', ARL_WORKER_COUNT)
                vjs_jobs = get_next_jobs('pending_vjs', VJS_WORKER_COUNT)

                if not any([ingestion_jobs, arl_jobs, vjs_jobs]):
                    logging.info("No pending jobs in any stage. All work is done. Shutting down.")
                    break

                for i, job in enumerate(ingestion_jobs):
                    ingest_pool.submit(ingestion_worker, job, i + 1)
                for i, job in enumerate(arl_jobs):
                    arl_pool.submit(arl_worker, job, i + 1 + INGESTION_WORKER_COUNT)
                for i, job in enumerate(vjs_jobs):
                    vjs_pool.submit(vjs_worker, job, i + 1 + INGESTION_WORKER_COUNT + ARL_WORKER_COUNT)

                if args.run_once:
                    logging.info("--run-once flag detected. Shutting down after this batch.")
                    break
                
                logging.info("Cycle complete. Waiting for 15 seconds before checking for new jobs...")
                time.sleep(15)

        except KeyboardInterrupt:
            shutdown()

    logging.info("All worker pools have shut down. Project Synapse signing off.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse stage-centric pipeline.")
    parser.add_argument("--min_rating", type=int, help="Minimum rating of problems to ingest.")
    parser.add_argument("--max_rating", type=int, help="Maximum rating of problems to ingest.")
    parser.add_argument("--run-once", action='store_true', help="Run one cycle of job fetching and then exit.")
    args = parser.parse_args()
    main(args)