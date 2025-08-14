# synapse/scraper.py
# Final Production Version: Smart, Semi-Automated Login

import requests
import time
import logging
import json
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Selenium Imports
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Quieter Logging for Selenium/urllib3 ---
logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

load_dotenv()

# --- Session and Constants ---
session = requests.Session()
CF_HANDLE = os.getenv('CF_HANDLE')
CF_PASSWORD = os.getenv('CF_PASSWORD')

if not CF_HANDLE or not CF_PASSWORD:
    raise ValueError("Please set CF_HANDLE and CF_PASSWORD in your .env file.")

MY_USER_AGENT = os.getenv('MY_USER_AGENT')
session.headers.update({'User-Agent': MY_USER_AGENT})

API_BASE = "https://codeforces.com/api"
INTERNAL_API_BASE = "https://codeforces.com/data"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

# --- Browser Automation Logic ---
def _get_logged_in_driver() -> uc.Chrome | None:
    """
    Creates a visible Google Chrome instance and attempts a semi-automated login.
    It will try to enter credentials automatically, but will ask for help with CAPTCHAs.
    """
    logging.info("Attempting smart login using Google Chrome...")
    driver = None
    browser_executable_path = "/usr/bin/google-chrome-stable"
    
    try:
        options = uc.ChromeOptions()
        driver = uc.Chrome(
            options=options,
            browser_executable_path=browser_executable_path
        )
        
        driver.get("https://codeforces.com/enter")
        logging.info("Navigated to login page.")
        
        wait = WebDriverWait(driver, 5)
        
        try:
            handle_input = wait.until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
            logging.info("Login form found immediately. Proceeding automatically.")
        except TimeoutException:
            logging.warning("Login form not found. Assuming CAPTCHA is present.")
            print("\a") # Terminal bell
            logging.warning(">>> ACTION REQUIRED: Please solve the CAPTCHA in the browser window.")
            input(">>> After the LOGIN FORM is visible, press Enter here to continue...")
            
            long_wait = WebDriverWait(driver, 60)
            handle_input = long_wait.until(EC.presence_of_element_located((By.ID, "handleOrEmail")))

        password_input = driver.find_element(By.ID, "password")
        logging.info("Entering credentials automatically...")
        handle_input.send_keys(CF_HANDLE)
        password_input.send_keys(CF_PASSWORD)
        
        remember_checkbox = driver.find_element(By.ID, "remember")
        if not remember_checkbox.is_selected():
             remember_checkbox.click()
        
        login_button = driver.find_element(By.CLASS_NAME, "submit")
        login_button.click()
        
        logging.info("Login submitted. Waiting for confirmation...")
        final_wait = WebDriverWait(driver, 20)
        final_wait.until(lambda d: "enter" not in d.current_url)
        final_wait.until(EC.presence_of_element_located((By.LINK_TEXT, CF_HANDLE)))
        
        logging.info("SUCCESS: Login confirmed. Browser session is authenticated.")
        return driver
        
    except Exception:
        logging.critical("Failed to complete the login process.", exc_info=True)
        if driver:
            driver.save_screenshot("debug_login_failure.png")
            driver.quit()
        return None

def _get_source_from_page(driver: uc.Chrome, url: str) -> str | None:
    """Uses a pre-authenticated driver to patiently scrape the source code."""
    try:
        logging.info(f"Navigating to submission URL: {url}")
        driver.get(url)
        
        wait = WebDriverWait(driver, 20)
        code_element = wait.until(EC.presence_of_element_located((By.ID, "program-source-text")))
        
        polling_timeout = 15
        start_time = time.time()
        final_text = ""
        while time.time() - start_time < polling_timeout:
            current_text = code_element.text
            if current_text and current_text.strip() and current_text.strip() != "N/A":
                logging.info(f"Dynamic content loaded after {time.time() - start_time:.2f} seconds.")
                final_text = current_text
                break
            time.sleep(0.5)
        
        if not final_text:
            logging.error("Timeout: Element content remained empty or 'N/A'.")
            return None

        return final_text

    except Exception:
        logging.error(f"Failed to scrape source code from {url}", exc_info=True)
        return None

# --- Main Fetching Logic ---
def _get_best_submission(contest_id: str, problem_index: str) -> list | None:
    all_candidates = []
    max_submissions_to_check = 1000
    batch_size = 200
    logging.info(f"Searching for candidate submissions for {contest_id}{problem_index}...")
    for start_index in range(1, max_submissions_to_check + 1, batch_size):
        url = f"{API_BASE}/contest.status?contestId={contest_id}&from={start_index}&count={batch_size}"
        time.sleep(2)
        try:
            response = session.get(url)
            response.raise_for_status()
            submissions = response.json().get('result', [])
            if not submissions: break
            for sub in submissions:
                if 'C++' in sub.get('programmingLanguage', '') and \
                   sub.get('problem', {}).get('index') == problem_index and \
                   sub.get('verdict') == 'OK':
                    all_candidates.append(sub)
        except Exception as e:
            logging.error(f"Failed to fetch submissions batch: {e}")
            break
    if not all_candidates:
        logging.error(f"No suitable accepted C++ submissions found for {contest_id}{problem_index}.")
        return None
    all_candidates.sort(key=lambda x: x['author'].get('rating', -1), reverse=True)
    logging.info(f"Found {len(all_candidates)} candidates.")
    return all_candidates

def fetch_problem_data(problem_id: str) -> dict | None:
    logging.info(f"--- Starting data fetch for problem {problem_id} ---")
    
    driver = _get_logged_in_driver()
    if not driver: return None

    try:
        contest_id, problem_index = problem_id[:-1], problem_id[-1]
        candidate_submissions = _get_best_submission(contest_id, problem_index)
        if not candidate_submissions: return None

        solution_code = None
        ref_submission = None

        for candidate in candidate_submissions[:5]:
            submission_id = candidate['id']
            submission_url = SUBMISSION_URL_TEMPLATE.format(contestId=contest_id, submissionId=submission_id)
            author_handle = candidate['author'].get('handle', 'unknown_user')
            
            logging.info(f"Attempting to scrape submission {submission_id} from '{author_handle}'.")
            
            source_code_text = _get_source_from_page(driver, submission_url)
            
            if source_code_text:
                solution_code = source_code_text.strip()
                ref_submission = candidate
                logging.info(f"SUCCESS: Found valid source code in submission {submission_id}.")
                break 
            else:
                logging.warning(f"Failed to get valid source for submission {submission_id}. Trying next candidate.")
        
        if not solution_code or not ref_submission:
            logging.critical(f"Could not find any valid submissions with source code for problem {problem_id}.")
            return None

        submission_id = ref_submission['id']
        problem_name = ref_submission['problem']['name']
        submission_url = SUBMISSION_URL_TEMPLATE.format(contestId=contest_id, submissionId=submission_id)

        logging.info("Re-authenticating requests session and finding CSRF token...")
        browser_cookies = driver.get_cookies()
        for cookie in browser_cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        meta_tag = soup.find('meta', {'name': 'X-Csrf-Token'})
        
        if not meta_tag or not meta_tag.get('content'):
            logging.error("Could not find X-Csrf-Token meta tag on the page.")
            return None
        csrf_token = meta_tag['content']
        
        time.sleep(2)
        api_url = f"{INTERNAL_API_BASE}/submitSource"
        payload = {'submissionId': submission_id, 'csrf_token': csrf_token}
        headers = {'Referer': submission_url}
        response = session.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        pretests = []
        for i in range(1, int(data.get('testCount', 0)) + 1):
            input_data, answer_data = data.get(f'input#{i}'), data.get(f'answer#{i}')
            if input_data is not None and answer_data is not None:
                pretests.append({'input': input_data.strip(), 'output': answer_data.strip()})
        logging.info(f"SUCCESS: Fetched {len(pretests)} pretests via internal API.")
        
        return {
            "problem_id": problem_id, "name": problem_name,
            "pretests": pretests, "reference_solution_code": solution_code
        }
    finally:
        if driver:
            driver.quit()
            logging.info("Browser session closed.")