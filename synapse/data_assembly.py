# synapse/data_assembly.py
"""
This module is responsible for assembling the final "golden record" for a
successfully processed problem. It contains helper functions for parsing
raw data and a main assembly function that constructs the final, structured
JSON object to be saved to the dataset.
"""
import logging
import json
from bs4 import BeautifulSoup
from typing import Dict, Any

# Global constants for URL templates
PROBLEM_URL_TEMPLATE: str = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE: str = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

def _parse_time_limit(text: str) -> int:
    """Parses a raw time limit string (e.g., '2 seconds') into milliseconds."""
    try:
        # Handles both integer and float values like "1.5"
        return int(float(text.split()[0]) * 1000)
    except (ValueError, IndexError):
        logging.warning(f"Could not parse time limit from text: '{text}'")
        return 2000 # Return a safe default

def _parse_memory_limit(text: str) -> int:
    """Parses a raw memory limit string (e.g., '256 megabytes') into kilobytes."""
    try:
        return int(text.split()[0]) * 1024
    except (ValueError, IndexError):
        logging.warning(f"Could not parse memory limit from text: '{text}'")
        return 262144 # Return a safe default

def _assemble_golden_record(problem_id: str, workspace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assembles the final JSON object (the "golden record") from all the data
    stored in the workspace database for a given problem.

    This function should only be called after all verification steps are complete.

    Args:
        problem_id: The unique ID of the problem.
        workspace_data: A dictionary containing all the cached data for this
                        problem from the `problem_data_cache` table.

    Returns:
        A dictionary representing the final, structured data record.
    """
    ref_submission = json.loads(workspace_data['reference_solution_json'])
    html_statement = workspace_data['problem_statement_html']
    pretests = json.loads(workspace_data['pretests_json'])
    
    # Re-parse limits from the raw text for the final record to ensure accuracy
    soup = BeautifulSoup(html_statement, 'html.parser')
    time_limit_raw = soup.find('div', class_='time-limit').text.replace('time limit per test', '').strip()
    memory_limit_raw = soup.find('div', class_='memory-limit').text.replace('memory limit per test', '').strip()

    final_record = {
        "problem_id": problem_id,
        "problem_url": PROBLEM_URL_TEMPLATE.format(
            contestId=ref_submission['problem']['contestId'],
            index=ref_submission['problem']['index']
        ),
        "problem_metadata": {
            "name": ref_submission['problem']['name'],
            "tags": ref_submission['problem']['tags'],
            "time_limit_ms": _parse_time_limit(time_limit_raw),
            "memory_limit_kb": _parse_memory_limit(memory_limit_raw),
        },
        "problem_statement_html": html_statement,
        "pretests": pretests,
        "reference_solution": {
            "submission_id": ref_submission['id'],
            "submission_url": SUBMISSION_URL_TEMPLATE.format(
                contestId=ref_submission['contestId'],
                submissionId=ref_submission['id']
            ),
            "author_handle": ref_submission['author']['members'][0]['handle'],
            "author_rating": ref_submission['author'].get('rating'),
            "language": ref_submission['programmingLanguage'],
            "code": workspace_data.get('reference_solution_code')
        },
        "verified_pseudocode": workspace_data.get('arl_pseudocode'),
        "verified_solution_code": workspace_data.get('arl_reconstructed_code')
    }
    
    # Add the code quality analysis if it exists
    analysis_json = workspace_data.get('quality_analysis_json')
    if analysis_json:
        try:
            final_record['code_quality_analysis'] = json.loads(analysis_json)
        except json.JSONDecodeError:
            logging.warning(f"Could not parse quality_analysis_json for {problem_id}")
            final_record['code_quality_analysis'] = None

    return final_record