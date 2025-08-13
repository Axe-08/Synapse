# synapse/scraper.py (v14 - Paginated Submission Search)

import requests
import time
import logging
import json
import os
from dotenv import load_dotenv

load_dotenv()

# --- Authenticated requests Session Setup ---
session = requests.Session()
MY_USER_AGENT = os.getenv('MY_USER_AGENT')
CF_CSRF_TOKEN = os.getenv('CF_CSRF_TOKEN')

if not MY_USER_AGENT or not CF_CSRF_TOKEN:
    raise ValueError("Please set MY_USER_AGENT and CF_CSRF_TOKEN in your .env file.")

session.headers.update({ 'User-Agent': MY_USER_AGENT, 'X-Csrf-Token': CF_CSRF_TOKEN })

try:
    with open('cookies.json', 'r') as f:
        cookies = json.load(f)
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
except FileNotFoundError:
    logging.critical("CRITICAL: 'cookies.json' not found. Cannot make authenticated requests.")
    exit()

API_BASE = "https://codeforces.com/api"
INTERNAL_API_BASE = "https://codeforces.com/data"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

def _get_best_accepted_submission(contest_id: str, problem_index: str) -> dict | None:
    """
    Finds a suitable accepted C++ submission, searching through multiple pages if necessary.
    """
    batch_size = 200
    max_submissions_to_check = 1000 # Let's check a max of 5 pages

    for start_index in range(1, max_submissions_to_check + 1, batch_size):
        url = f"{API_BASE}/contest.status?contestId={contest_id}&from={start_index}&count={batch_size}"
        logging.info(f"Searching for submissions via API: {url}")
        time.sleep(2)
        try:
            response = session.get(url)
            response.raise_for_status()
            submissions = response.json().get('result', [])
            if not submissions:
                logging.warning(f"API returned no more submissions for contest {contest_id} at start index {start_index}.")
                break # Stop if there are no more submissions to fetch

            logging.info(f"Processing batch of {len(submissions)} submissions...")
            
            best_rated, first_accepted, max_rating = None, None, -1
            for sub in submissions:
                is_cpp = 'C++' in sub.get('programmingLanguage','')
                is_correct_problem = sub.get('problem',{}).get('index') == problem_index
                is_accepted = sub.get('verdict') == 'OK'

                if is_correct_problem and is_accepted and is_cpp:
                    if not first_accepted: first_accepted = sub
                    if 'rating' in sub['author'] and sub['author']['rating'] > max_rating:
                        max_rating = sub['author']['rating']
                        best_rated = sub
            
            if best_rated:
                logging.info(f"Found best submission from rated user {best_rated['author']['handle']} in this batch.")
                return best_rated
            if first_accepted:
                logging.warning("No rated users in this batch. Falling back to first accepted submission.")
                return first_accepted

        except Exception as e:
            logging.error(f"Failed to process submissions for {contest_id}{problem_index}: {e}")
            return None # Stop on error
            
    logging.error(f"Could not find any suitable C++ submissions for {contest_id}{problem_index} after checking {max_submissions_to_check} submissions.")
    return None


def fetch_problem_data(problem_id: str) -> dict | None:
    # This function is complete and requires no changes.
    logging.info(f"Starting data fetch for problem {problem_id}...")
    try:
        contest_id, problem_index = problem_id[:-1], problem_id[-1]
    except (ValueError, IndexError):
        logging.error(f"Invalid problem_id format: {problem_id}")
        return None

    ref_submission = _get_best_accepted_submission(contest_id, problem_index)
    if not ref_submission: return None

    submission_id = ref_submission['id']
    problem_name = ref_submission['problem']['name']
    
    logging.info(f"Found reference submission {submission_id} for problem '{problem_name}'. Calling internal API...")
    try:
        time.sleep(2)
        api_url = f"{INTERNAL_API_BASE}/submitSource"
        submission_url = SUBMISSION_URL_TEMPLATE.format(contestId=contest_id, submissionId=submission_id)
        
        payload = {'submissionId': submission_id, 'csrf_token': CF_CSRF_TOKEN}
        headers = {'Referer': submission_url}
        
        response = session.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        solution_code = data.get('source')
        if not solution_code:
            logging.error(f"API response for {submission_id} missing source code.")
            return None

        pretests = []
        for i in range(1, int(data.get('testCount', 0)) + 1):
            input_data = data.get(f'input#{i}')
            answer_data = data.get(f'answer#{i}')
            if input_data and answer_data:
                pretests.append({'input': input_data.strip(), 'output': answer_data.strip()})
        
        logging.info(f"SUCCESS: Fetched data via internal API. Found {len(pretests)} tests.")

        return {
            "problem_id": problem_id, "name": problem_name,
            "pretests": pretests, "reference_solution_code": solution_code.strip()
        }
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.critical("CRITICAL: Received a 403 Forbidden error. Your session/CSRF token is likely expired.")
            logging.warning("ACTION: Please log out/in on Codeforces, re-export 'cookies.json', and update '.env'.")
        else:
            logging.error(f"HTTP Error for submission {submission_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"A non-HTTP error occurred for submission {submission_id}: {e}")
        return None