# debugging_and_testing/debug_ingestion.py
import os
import sys
import time
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

import synapse.database as db
from synapse.scraper import fetch_problem_data, get_authenticated_driver, classify_problem
from synapse.account_manager import AccountManager
from debugging_and_testing.debug_database import setup_debug_dbs, DEBUG_PROGRESS_DB, DEBUG_WORKSPACE_DB
from synapse.database_writer import db_writer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# The 5 problems of varied difficulty requested by user
DEBUG_PROBLEMS = ["4A", "50A", "1324C", "158A", "2000B"]

def run_ingestion_test():
    # 1. Initialize Databases
    setup_debug_dbs()
    
    # 2. Redirect DB paths and start writer
    db.PROGRESS_DB_PATH = DEBUG_PROGRESS_DB
    db.WORKSPACE_DB_PATH = DEBUG_WORKSPACE_DB
    db_writer.set_db_path(DEBUG_PROGRESS_DB)
    db_writer.start()
    
    # 3. Insert fresh problem rows into progress DB
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        for pid in DEBUG_PROBLEMS:
            # Simple contest/index split heuristic for creation
            contest_id = "".join(filter(str.isdigit, pid))
            index = "".join(filter(str.isalpha, pid))
            conn.execute(
                "INSERT OR IGNORE INTO problems (id, name, contest_id, problem_index, last_updated, status) VALUES (?, ?, ?, ?, ?, ?)",
                (pid, f'TestProblem_{pid}', contest_id, index, time.time(), 'pending_ingestion')
            )
            # Update status to pending_ingestion directly if already exists
            conn.execute(
                "UPDATE problems SET status = 'pending_ingestion' WHERE id = ?",
                (pid,)
            )
            
    print("\n--- Starting Isolated Ingestion Scrape Test ---\n")
    
    # 4. Scrape logic
    load_dotenv()
    account_mgr = AccountManager.from_env()
    driver = get_authenticated_driver(account_manager=account_mgr)
    
    try:
        for pid in DEBUG_PROBLEMS:
            logging.info(f"[{pid}] Scraping data from Codeforces...")
            data = fetch_problem_data(pid, driver, exclude_submission_ids=[])
            
            if not data:
                logging.error(f"[{pid}] fetch_problem_data returned None!")
                continue
            
            p_class = classify_problem(statement_html=data['page_details']['problem_statement_html'])
            
            logging.info(f"[{pid}] Finished Scraping. Saving to Cache DB...")
            db.save_multi_oracle_ingestion_data(
                pid, 
                data['page_details']['problem_statement_html'],
                data['pretests'], 
                data['successful_solutions'],
                data['page_details']['time_limit_raw'], 
                data['page_details']['memory_limit_raw'],
                p_class
            )
            
            # Transition status
            db.transition_to_pending_calibration(pid)
            
            logging.info(f"[{pid}] Ingestion complete -> pending_calibration\n")
            time.sleep(2) # Give rate-limits breathing room
            
    finally:
        driver.quit()
        db_writer.wait_for_completion()
        db_writer.stop()
        
    print("\n--- Summary of Database Workspace Rows ---")
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        rows = conn.execute("SELECT problem_id FROM problem_data_cache").fetchall()
        print(f"Total problems ingested into workspace cache: {len(rows)}")
        for r in rows:
            print(f" - {r[0]}")

if __name__ == "__main__":
    run_ingestion_test()
