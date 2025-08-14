# main.py (Final Ingestion Phase Version)
import argparse
import logging
import time
import os
from dotenv import load_dotenv

# Set up basic logging FIRST
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Now import our project modules
from synapse.database import get_problem_status, update_problem_status
from synapse.scraper import get_authenticated_driver, fetch_problem_data
from synapse.data_manager import save_problem_files, cleanup_problem_files, append_to_dataset

# Selenium imports for the warm-up wait
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Load environment variables to get CF_HANDLE
load_dotenv()
CF_HANDLE = os.getenv('CF_HANDLE')

def process_single_problem(problem_id: str, driver):
    """The pipeline function for processing one problem, using a shared driver."""
    logging.info(f"--- Starting Pipeline for Problem: {problem_id} ---")
    
    status = get_problem_status(problem_id)
    if status == 'completed':
        logging.warning(f"Problem {problem_id} is already marked as 'completed'. Skipping.")
        return True # Indicate success
    if status == 'in_progress':
        logging.warning(f"Problem {problem_id} is 'in_progress'. Re-running.")

    update_problem_status(problem_id, 'in_progress')
    
    try:
        problem_data = fetch_problem_data(problem_id, driver)
        if not problem_data:
            raise Exception("Failed to fetch problem data.")

        logging.info(f"Successfully scraped '{problem_data['name']}'.")
        
        problem_dir = save_problem_files(problem_id, problem_data)
        
        final_data_object = problem_data
        
        append_to_dataset(final_data_object)
        
        update_problem_status(problem_id, 'completed')
        cleanup_problem_files(problem_id)
        
        logging.info(f"SUCCESS: Pipeline finished for problem: {problem_id}")
        return True

    except Exception as e:
        logging.error(f"An error occurred while processing {problem_id}: {e}", exc_info=False)
        update_problem_status(problem_id, 'failed')
        logging.warning(f"Intermediate files for failed problem {problem_id} are kept for debugging.")
        return False

def main(problem_ids: list[str]):
    """Orchestrates the batch processing of multiple problems."""
    
    driver = get_authenticated_driver()
    if not driver:
        logging.critical("Could not get an authenticated browser driver. Aborting batch.")
        return

    successful_count = 0
    failed_count = 0
    
    try:
        # --- KEY ADDITION: Session Warm-up ---
        if CF_HANDLE:
            logging.info("Performing a warm-up navigation to stabilize session...")
            warmup_url = f"https://codeforces.com/profile/{CF_HANDLE}"
            driver.get(warmup_url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.LINK_TEXT, CF_HANDLE)))
            logging.info("Session stabilized successfully.")
        else:
            logging.warning("CF_HANDLE not found in .env, skipping session warm-up.")
        # ------------------------------------

        for i, problem_id in enumerate(problem_ids):
            logging.info(f"--- Processing Batch Item {i+1}/{len(problem_ids)}: {problem_id} ---")
            
            if i > 0:
                time.sleep(5) 
                
            success = process_single_problem(problem_id, driver)
            if success:
                successful_count += 1
            else:
                failed_count += 1
            
    finally:
        logging.info("Batch finished. Closing browser session.")
        driver.quit()
        logging.info(f"--- Batch Summary ---")
        logging.info(f"Successfully processed: {successful_count}")
        logging.info(f"Failed to process: {failed_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline in batch mode.")
    parser.add_argument("problem_ids", nargs='+', help="One or more Codeforces problem IDs (e.g., 1A 7C 100A).")
    args = parser.parse_args()
    main(args.problem_ids)