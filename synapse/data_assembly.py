# synapse/data_assembly.py
import json
from bs4 import BeautifulSoup

# Global constants for URL templates
PROBLEM_URL_TEMPLATE = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

def _parse_time_limit(text: str) -> int:
    try:
        return int(float(text.split()[0]) * 1000)
    except:
        return 0

def _parse_memory_limit(text: str) -> int:
    try:
        return int(text.split()[0]) * 1024
    except:
        return 0

def _assemble_golden_record(problem_id: str, workspace_data: dict) -> dict:
    """
    Assembles the final JSON object (the "golden record") from data stored in the workspace.
    This function should only be called after all verification steps are complete.
    """
    ref = json.loads(workspace_data['reference_solution_json'])
    page_html = workspace_data['problem_statement_html']
    pretests = json.loads(workspace_data['pretests_json'])
    
    # Re-parse the raw limits from the HTML for the final record
    soup = BeautifulSoup(page_html, 'html.parser')
    time_limit_raw = soup.find('div', class_='time-limit').text.replace('time limit per test', '').strip()
    memory_limit_raw = soup.find('div', class_='memory-limit').text.replace('memory limit per test', '').strip()

    return {
        "problem_id": problem_id,
        "problem_url": PROBLEM_URL_TEMPLATE.format(contestId=ref['problem']['contestId'], index=ref['problem']['index']),
        "problem_metadata": {
            "name": ref['problem']['name'], "tags": ref['problem']['tags'],
            "time_limit_ms": _parse_time_limit(time_limit_raw),
            "memory_limit_kb": _parse_memory_limit(memory_limit_raw),
        },
        "problem_statement_html": page_html,
        "pretests": pretests,
        "reference_solution": {
            "submission_id": ref['id'],
            "submission_url": SUBMISSION_URL_TEMPLATE.format(contestId=ref['contestId'], submissionId=ref['id']),
            "author_handle": ref['author']['members'][0]['handle'],
            "author_rating": ref['author'].get('rating', None),
            "language": ref['programmingLanguage'], "code": "code_is_in_workspace_db"
        },
        "verified_pseudocode": workspace_data.get('arl_pseudocode'),
        "verified_solution_code": workspace_data.get('arl_reconstructed_code')
    }