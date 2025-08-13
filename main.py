# main.py (Final Clean Version for Phase 1)

import argparse
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from synapse.database import get_problem_status, update_problem_status
from synapse.scraper import fetch_problem_data


def process_problem(problem_id: str):
    """The main pipeline function for processing a single problem."""
    logging.info(f"Starting pipeline for problem: {problem_id}")
    
    status = get_problem_status(problem_id)
    if status == 'completed':
        logging.warning(f"Problem {problem_id} is already marked as 'completed'. Skipping.")
        return
    if status == 'in_progress':
        logging.warning(f"Problem {problem_id} is marked as 'in_progress'. Skipping to avoid conflicts.")
        return

    update_problem_status(problem_id, 'in_progress')
    logging.info(f"Processing problem: {problem_id}")

    try:
        # Step 1: Scrape all problem data
        problem_data = fetch_problem_data(problem_id)
        if not problem_data:
            raise Exception("Failed to fetch problem data.")

        logging.info(f"Successfully scraped '{problem_data['name']}'.")
        logging.info(f"Found {len(problem_data['pretests'])} pretest(s).")
        logging.info(f"Reference solution code is {len(problem_data['reference_solution_code'])} characters long.")

        # --- NEXT STEPS: ARL (LLM Calls) and VJS (Judge) will go here ---

        update_problem_status(problem_id, 'completed')
        logging.info(f"Successfully processed and saved problem: {problem_id}")

    except Exception as e:
        logging.error(f"An error occurred while processing {problem_id}: {e}", exc_info=False)
        update_problem_status(problem_id, 'failed')

    logging.info(f"Pipeline finished for problem: {problem_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline.")
    parser.add_argument("--problem_id", type=str, required=True, help="The Codeforces problem ID (e.g., '1A').")
    args = parser.parse_args()
    process_problem(args.problem_id)