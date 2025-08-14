# main.py (Definitive Production Version)

import argparse
import logging

# Set up basic logging FIRST
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Now import our project modules
from synapse.database import get_problem_status, update_problem_status
from synapse.scraper import fetch_problem_data

def process_problem(problem_id: str):
    """The main pipeline function for processing a single problem."""
    logging.info(f"--- Starting Pipeline for Problem: {problem_id} ---")
    
    status = get_problem_status(problem_id)
    if status == 'completed':
        logging.warning(f"Problem {problem_id} is already marked as 'completed'. Skipping.")
        return
    if status == 'in_progress':
        logging.warning(f"Problem {problem_id} is marked as 'in_progress'. Skipping.")
        return

    update_problem_status(problem_id, 'in_progress')
    logging.info(f"Processing problem: {problem_id}")

    try:
        # Step 1: Scrape all problem data
        problem_data = fetch_problem_data(problem_id)
        if not problem_data:
            raise Exception("Failed to fetch problem data. See scraper logs for details.")

        logging.info(f"Successfully scraped '{problem_data['name']}'.")
        logging.info(f"Found {len(problem_data['pretests'])} pretest(s).")
        logging.info(f"Reference solution code is {len(problem_data['reference_solution_code'])} characters long.")

        # --- NEXT STEPS WILL GO HERE ---
        # 1. Save problem_data to a file in the 'data/' directory.
        # 2. Call ARL (LLM APIs).
        # 3. Call VJS (Local Judge).
        # -----------------------------

        update_problem_status(problem_id, 'completed')
        logging.info(f"SUCCESS: Pipeline finished for problem: {problem_id}")

    except Exception as e:
        logging.error(f"An error occurred while processing {problem_id}: {e}", exc_info=False)
        update_problem_status(problem_id, 'failed')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline.")
    parser.add_argument("--problem_id", type=str, required=True, help="The Codeforces problem ID (e.g., '1A').")
    args = parser.parse_args()
    process_problem(args.problem_id)