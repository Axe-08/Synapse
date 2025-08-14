# synapse/data_manager.py
import os
import json
import logging
import shutil

DATA_DIR = "data"
FINAL_DATASET_FILE = "dataset.jsonl"

def save_problem_files(problem_id: str, problem_data: dict) -> str:
    """
    Saves the scraped problem data into a structured temporary directory.
    Returns the path to the created directory.
    """
    problem_dir = os.path.join(DATA_DIR, problem_id)
    pretests_dir = os.path.join(problem_dir, "pretests")
    
    os.makedirs(pretests_dir, exist_ok=True)
    logging.info(f"Created temporary data directory: {problem_dir}")

    # Save reference solution
    solution_path = os.path.join(problem_dir, "reference.cpp")
    with open(solution_path, 'w', encoding='utf-8') as f:
        f.write(problem_data['reference_solution_code'])

    # Save pretests if they exist
    if problem_data.get('pretests'):
        for i, pretest in enumerate(problem_data['pretests']):
            in_path = os.path.join(pretests_dir, f"{i+1}.in")
            out_path = os.path.join(pretests_dir, f"{i+1}.out")
            with open(in_path, 'w', encoding='utf-8') as f:
                f.write(pretest['input'])
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(pretest['output'])
    
    # Save metadata for easy inspection
    metadata = {
        "problem_id": problem_data["problem_id"],
        "name": problem_data["name"]
    }
    metadata_path = os.path.join(problem_dir, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)
    
    logging.info(f"Saved intermediate files for {problem_id}.")
    return problem_dir

def append_to_dataset(final_problem_data: dict):
    """Appends a single processed problem record to the final .jsonl dataset."""
    try:
        with open(FINAL_DATASET_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(final_problem_data) + '\n')
        logging.info(f"Appended final data for problem {final_problem_data.get('problem_id')} to {FINAL_DATASET_FILE}")
    except IOError as e:
        logging.error(f"Failed to append to dataset file {FINAL_DATASET_FILE}: {e}")

def cleanup_problem_files(problem_id: str):
    """Removes the temporary directory for a given problem to save space."""
    problem_dir = os.path.join(DATA_DIR, problem_id)
    if os.path.isdir(problem_dir):
        try:
            shutil.rmtree(problem_dir)
            logging.info(f"Successfully cleaned up temporary directory: {problem_dir}")
        except OSError as e:
            logging.error(f"Error removing directory {problem_dir}: {e}")