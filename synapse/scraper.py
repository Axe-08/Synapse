# synapse/scraper.py
# FINAL BATCH-READY VERSION: With Parallel Candidate Search

import requests
import time
import logging
import json
import os
import shutil
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

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
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"

# --- Browser Automation Logic (no changes in this section) ---
def get_authenticated_driver() -> uc.Chrome | None:
    logging.info("Attempting to launch and authenticate a persistent browser session...")
    driver = None
    browser_executable_path = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    if not browser_executable_path:
        logging.critical("Could not find Google Chrome executable. Please ensure it is installed and in your PATH.")
        return None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        driver = uc.Chrome(
            options=options,
            browser_executable_path=browser_executable_path,
            user_data_dir="./chrome_profile"
        )
        driver.get("https://codeforces.com/problemset")
        try:
            long_wait = WebDriverWait(driver, 120) 
            logging.info("Waiting for page to load. If you see a Cloudflare 'Verify you are human' page, please solve it.")
            long_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "problems")))
            logging.info("Main page content loaded. Proceeding.")
        except TimeoutException:
            logging.critical("Page did not load after 2 minutes. Could not get past Cloudflare or other issue.")
            driver.save_screenshot("debug_cloudflare_failure.png")
            return None
        try:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
            logging.info("SUCCESS: Codeforces session is active.")
            return driver
        except TimeoutException:
            logging.info("Codeforces session not found. Proceeding to login page.")
            driver.get("https://codeforces.com/enter")
            wait = WebDriverWait(driver, 10)
            try:
                handle_input = wait.until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
            except TimeoutException:
                logging.warning("Login form not found. ACTION REQUIRED: Please solve the Codeforces CAPTCHA.")
                input(">>> After the LOGIN FORM is visible, press Enter here to continue...")
                handle_input = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
            password_input = driver.find_element(By.ID, "password")
            handle_input.send_keys(CF_HANDLE)
            password_input.send_keys(CF_PASSWORD)
            remember_checkbox = driver.find_element(By.ID, "remember")
            if not remember_checkbox.is_selected():
                remember_checkbox.click()
            driver.find_element(By.CLASS_NAME, "submit").click()
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.LINK_TEXT, CF_HANDLE)))
            logging.info("SUCCESS: Login to Codeforces confirmed.")
            return driver
    except Exception:
        logging.critical("An unrecoverable error occurred during the login process.", exc_info=True)
        if driver:
            driver.save_screenshot("debug_login_failure.png")
            driver.quit()
        return None

def _get_source_from_page(driver: uc.Chrome, url: str) -> str | None:
    try:
        logging.info(f"Navigating to submission URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        code_element = wait.until(EC.presence_of_element_located((By.ID, "program-source-text")))
        final_text = code_element.text.strip()
        if not final_text or final_text == "N/A":
             logging.error("Element found but content was empty or 'N/A'.")
             return None
        logging.info(f"Dynamic content loaded successfully.")
        return final_text
    except Exception:
        logging.error(f"Failed to scrape source code from {url}", exc_info=True)
        driver.save_screenshot(f"debug_scrape_exception_{url.split('/')[-1]}.png")
        return None

# --- Main Fetching Logic ---

def _fetch_submission_page(url: str) -> dict | None:
    """Worker function to fetch a single page of submissions."""
    try:
        # A small delay can be added here if we want to be extra careful,
        # but the concurrency limit from max_workers is our main tool.
        # time.sleep(random.uniform(0.5, 1.5)) 
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def _get_best_submission(contest_id: str, problem_index: str) -> list | None:
    """
    Searches for candidate submissions in parallel to speed up the process.
    """
    all_candidates = []
    max_submissions_to_check = 1000
    batch_size = 200
    logging.info(f"Searching for candidate submissions for {contest_id}{problem_index} in parallel...")

    # 1. Create all the URLs we need to fetch
    urls = [
        f"{API_BASE}/contest.status?contestId={contest_id}&from={start_index}&count={batch_size}"
        for start_index in range(1, max_submissions_to_check + 1, batch_size)
    ]

    # 2. Use ThreadPoolExecutor to fetch URLs concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Map each future to its URL for better error logging
        future_to_url = {executor.submit(_fetch_submission_page, url): url for url in urls}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                if not data or data.get('status') != 'OK':
                    continue

                submissions = data.get('result', [])
                if not submissions:
                    # This means we've reached the end of the submissions list for this contest
                    logging.info(f"No more submissions found from {url}, stopping this thread's search.")
                    continue
                
                # Filter the results from this page
                for sub in submissions:
                    if 'C++' in sub.get('programmingLanguage', '') and \
                       sub.get('problem', {}).get('index') == problem_index and \
                       sub.get('verdict') == 'OK':
                        all_candidates.append(sub)

            except Exception as e:
                logging.error(f"An exception occurred processing result from {url}: {e}")

    if not all_candidates:
        logging.error(f"No suitable accepted C++ submissions found for {contest_id}{problem_index}.")
        return None
    
    # 3. Sort all collected candidates by rating
    all_candidates.sort(key=lambda x: x['author'].get('rating', -1), reverse=True)
    logging.info(f"Found {len(all_candidates)} candidates after parallel search.")
    return all_candidates


def fetch_problem_data(problem_id: str, driver: uc.Chrome) -> dict | None:
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

    problem_name = ref_submission['problem']['name']
    
    browser_cookies = driver.get_cookies()
    for cookie in browser_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    logging.warning("Pretest fetching is currently disabled for stability.")
    pretests = []
    
    return {
        "problem_id": problem_id, "name": problem_name,
        "pretests": pretests, "reference_solution_code": solution_code
    }