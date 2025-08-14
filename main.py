# main.py (Thread-Safe Orchestrator)
import argparse
import logging
import time
import os
import re
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading # <<< CHANGE 1: Import threading

# --- Configuration ---
WORKER_COUNT = 4 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Module Imports ---
from synapse.database import (
    get_problems_by_ids, update_problem_on_success, update_problem_on_failure, 
    get_next_pending_problems, update_worker_status, reset_all_workers_to_idle
)
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.data_manager import append_to_dataset

# --- Constants & Globals ---
PROBLEM_URL_TEMPLATE = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"
UC_INIT_LOCK = threading.Lock() # <<< CHANGE 2: Create a global lock

# --- Helper Functions for Data Assembly (no changes here) ---
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
        "verified_pseudocode": None, "verified_solution_code": None
    }

# --- This is the function each worker thread will execute ---
def process_single_problem(problem: dict, worker_id: int):
    problem_id = problem['id']
    driver = None
    
    try:
        update_worker_status(worker_id, problem_id, 'INITIALIZING', 'active')
        
        # <<< CHANGE 3: Use the lock to make browser creation thread-safe
        with UC_INIT_LOCK:
            logging.info(f"Worker {worker_id} acquiring lock to initialize browser...")
            driver = get_authenticated_driver()
            logging.info(f"Worker {worker_id} initialized browser and released lock.")
        
        if not driver:
            raise Exception("Failed to initialize authenticated browser session.")

        update_worker_status(worker_id, problem_id, 'SCRAPING', 'active')
        scraped_data = fetch_problem_data(problem_id, driver)
        if not scraped_data:
            raise Exception("Scraper returned no data.")

        update_worker_status(worker_id, problem_id, 'SAVING', 'active')
        final_record = _assemble_golden_record(scraped_data)
        append_to_dataset(final_record)
        
        pretest_count = len(final_record['pretests'])
        update_problem_on_success(problem_id, pretest_count)
        
        logging.info(f"Worker {worker_id}: SUCCESS for problem {problem_id}")
        return True

    except Exception as e:
        logging.error(f"Worker {worker_id}: FAILED for problem {problem_id}: {e}", exc_info=False)
        update_problem_on_failure(problem_id, str(e))
        return False
    
    finally:
        if driver:
            driver.quit()
        update_worker_status(worker_id, None, None, 'idle')


def main(args):
    """Orchestrates the multi-threaded processing of problems."""
    reset_all_workers_to_idle()

    if args.ids:
        problems_to_process = get_problems_by_ids(args.ids)
    else:
        problems_to_process = get_next_pending_problems(args.limit, args.min_rating, args.max_rating)

    if not problems_to_process:
        logging.info("No problems to process. Exiting.")
        return

    successful_count, failed_count = 0, 0
    
    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        futures = {
            executor.submit(process_single_problem, problem, (i % WORKER_COUNT) + 1): problem
            for i, problem in enumerate(problems_to_process)
        }
        for future in as_completed(futures):
            problem = futures[future]
            try:
                success = future.result()
                if success: successful_count += 1
                else: failed_count += 1
            except Exception as e:
                logging.error(f"An unexpected error occurred for problem {problem['id']}: {e}")
                failed_count += 1
    
    logging.info(f"\n--- Batch Complete ---")
    logging.info(f"  Successfully processed: {successful_count}")
    logging.info(f"  Failed to process:     {failed_count}")
    logging.info(f"----------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline.", formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ids", nargs='+', help="Manual mode: A specific list of problem IDs to process (e.g., 1A 7C).")
    group.add_argument("--limit", type=int, help="Automated mode: Number of pending problems to process from the DB.")
    parser.add_argument("--min_rating", type=int, help="[Auto Mode] Minimum rating of problems to fetch.")
    parser.add_argument("--max_rating", type=int, help="[Auto Mode] Maximum rating of problems to fetch.")
    args = parser.parse_args()
    main(args)