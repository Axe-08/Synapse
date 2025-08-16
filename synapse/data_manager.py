# synapse/data_manager.py
"""
Handles final data persistence for Project Synapse.
The primary responsibility of this module is to append completed,
verified data records to the final dataset file.
"""
import json
import logging

from config import FINAL_DATASET_FILE

def append_to_dataset(final_problem_data: dict) -> None:
    """
    Appends a single processed problem record to the final .jsonl dataset.

    This function is thread-safe due to the nature of 'a' (append) mode
    in file I/O, where writes are typically atomic.

    Args:
        final_problem_data: The final, complete dictionary for a problem.
    """
    try:
        with open(FINAL_DATASET_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(final_problem_data) + '\n')
        logging.info(f"Appended final data for problem {final_problem_data.get('problem_id')} to {FINAL_DATASET_FILE}")
    except IOError as e:
        logging.error(f"Failed to append to dataset file {FINAL_DATASET_FILE}: {e}")