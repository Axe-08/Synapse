# debug_scraper.py
"""
A focused debugging script to test the complete scraping and pretest 
enrichment pipeline on a range of old and new problems.

This script:
1. Initializes a single authenticated browser session.
2. Iterates through a list of problem IDs.
3. For each problem, it calls the main `fetch_problem_data` function, which
   includes both the initial HTML scrape and the internal API enrichment.
4. Prints the final, structured pretest JSON to the console for verification.

Usage:
  python debug_scraper.py
  
To save the output to a file:
  python debug_scraper.py > raw_scraper_debug.log 2>&1
"""
import json
import logging
import re
from typing import List

from dotenv import load_dotenv

# Import the complete data fetching function
from synapse.scraper import get_authenticated_driver, fetch_problem_data

# --- Configuration ---
# A mix of old, mid-era, and new problems to test different formats.
PROBLEM_IDS_TO_TEST: List[str] = ["2066B"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()


def print_header(title: str) -> None:
    """Prints a formatted header to the console."""
    bar = "=" * 80
    print(f"\n{bar}\n--- {title.upper()} ---\n{bar}")


def test_scraper_pipeline():
    """Main function to run the full scraper test."""
    print_header("Starting Full Scraper Pipeline Test")

    driver = get_authenticated_driver()
    if not driver:
        logging.error("Failed to initialize browser. Aborting test.")
        return

    try:
        for problem_id in PROBLEM_IDS_TO_TEST:
            print_header(f"Testing Problem: {problem_id}")

            # We call the main fetch_problem_data function which encapsulates
            # the entire process, including finding a reference solution
            # and enriching the pretests via the internal API.
            scraped_data = fetch_problem_data(problem_id, driver, exclude_submission_ids=[])

            if not scraped_data:
                logging.error(f"Failed to fetch complete data for {problem_id}")
                print("-" * 50)
                continue

            # Extract and print the crucial final pretest data
            final_pretests = scraped_data.get("pretests", [])
            print(f">>> Final Pretests JSON for {problem_id}:")
            print(json.dumps(final_pretests, indent=2))
            print("-" * 50)

    except Exception as e:
        logging.critical("Scraper test failed unexpectedly.", exc_info=True)
    finally:
        print_header("Scraper Test Finished")
        if driver:
            driver.quit()
        logging.info("Cleaned up browser instance.")


if __name__ == "__main__":
    test_scraper_pipeline()
