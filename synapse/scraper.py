# synapse/scraper.py
# GOLDEN SCHEMA VERSION: Gathers all required data points.

import requests
import time
import logging
import json
import os
import shutil
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Selenium Imports
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
load_dotenv()

session = requests.Session()
CF_HANDLE = os.getenv('CF_HANDLE')
CF_PASSWORD = os.getenv('CF_PASSWORD')
MY_USER_AGENT = os.getenv('MY_USER_AGENT')
if not all([CF_HANDLE, CF_PASSWORD, MY_USER_AGENT]):
    raise ValueError("Please set CF_HANDLE, CF_PASSWORD, and MY_USER_AGENT in your .env file.")
session.headers.update({'User-Agent': MY_USER_AGENT})

API_BASE = "https://codeforces.com/api"
PROBLEM_URL_TEMPLATE = "https://codeforces.com/problemset/problem/{contestId}/{index}"
SUBMISSION_URL_TEMPLATE = "https://codeforces.com/contest/{contestId}/submission/{submissionId}"
INTERNAL_API_BASE = "https://codeforces.com/data"


def fetch_problem_page_details(contest_id: int, problem_index: str) -> dict:
    """
    Scrapes the public problem page for statement, metadata, and example pretests.
    This does NOT require a logged-in session.
    """
    url = PROBLEM_URL_TEMPLATE.format(contestId=contest_id, index=problem_index)
    logging.info(f"Scraping problem page: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': MY_USER_AGENT}, timeout=40)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        problem_statement_div = soup.find('div', class_='problem-statement')
        if not problem_statement_div:
            raise Exception("Problem statement div not found.")

        # --- Extract Metadata ---
        time_limit_text = problem_statement_div.find('div', class_='time-limit').text.replace('time limit per test', '').strip()
        memory_limit_text = problem_statement_div.find('div', class_='memory-limit').text.replace('memory limit per test', '').strip()
        
        # --- Extract Pretests ---
        pretests = []
        example_div = problem_statement_div.find('div', class_='sample-tests')
        if example_div:
            inputs = example_div.find_all('div', class_='input')
            outputs = example_div.find_all('div', class_='output')
            for i in range(min(len(inputs), len(outputs))):
                input_text = inputs[i].find('pre').text.strip()
                output_text = outputs[i].find('pre').text.strip()
                pretests.append({'input': input_text, 'output': output_text})

        return {
            "problem_statement_html": str(problem_statement_div),
            "time_limit_raw": time_limit_text,
            "memory_limit_raw": memory_limit_text,
            "example_pretests": pretests
        }
    except Exception as e:
        logging.error(f"Failed to scrape problem page {url}: {e}")
        return {}


# get_authenticated_driver and _get_source_from_page remain the same...
def get_authenticated_driver() -> uc.Chrome | None:
    logging.info("Attempting to launch and authenticate a persistent browser session...")
    driver = None
    browser_executable_path = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    if not browser_executable_path:
        logging.critical("Could not find Google Chrome executable.")
        return None
    try:
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1920,1080')
        driver = uc.Chrome(options=options, browser_executable_path=browser_executable_path, user_data_dir="./chrome_profile")
        driver.get("https://codeforces.com/problemset")
        try:
            long_wait = WebDriverWait(driver, 120) 
            logging.info("Waiting for page... If Cloudflare appears, please solve it.")
            long_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "problems")))
            logging.info("Main page content loaded.")
        except TimeoutException:
            logging.critical("Page did not load after 2 minutes.")
            driver.save_screenshot("debug_cloudflare_failure.png")
            return None
        try:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
            logging.info("SUCCESS: Codeforces session is active.")
            return driver
        except TimeoutException:
            logging.info("Codeforces session not found. Proceeding to login.")
            driver.get("https://codeforces.com/enter")
            wait = WebDriverWait(driver, 10)
            try:
                handle_input = wait.until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
            except TimeoutException:
                logging.warning("Login form not found. ACTION REQUIRED: Please solve CAPTCHA.")
                input(">>> After LOGIN FORM is visible, press Enter...")
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
        logging.critical("An unrecoverable error occurred during login.", exc_info=True)
        if driver:
            driver.save_screenshot("debug_login_failure.png")
            driver.quit()
        return None

def _get_source_from_page(driver: uc.Chrome, url: str) -> str | None:
    try:
        logging.info(f"Navigating to submission URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 10)
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

# _fetch_submission_page and _get_best_submission remain the same...
def _fetch_submission_page(url: str) -> dict | None:
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def _get_best_submission(contest_id: str, problem_index: str) -> list | None:
    all_candidates = []
    max_submissions_to_check = 1000
    batch_size = 200
    logging.info(f"Searching for candidate submissions for {contest_id}{problem_index} in parallel...")
    urls = [f"{API_BASE}/contest.status?contestId={contest_id}&from={i}&count={batch_size}" for i in range(1, max_submissions_to_check + 1, batch_size)]
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(_fetch_submission_page, url): url for url in urls}
        for future in as_completed(future_to_url):
            data = future.result()
            if not data or data.get('status') != 'OK' or not data.get('result'):
                continue
            for sub in data['result']:
                if sub.get('id') in exclude_ids:
                    continue
                if 'C++' in sub.get('programmingLanguage', '') and sub.get('problem', {}).get('index') == problem_index and sub.get('verdict') == 'OK':
                    all_candidates.append(sub)
    if not all_candidates:
        logging.error(f"No suitable accepted C++ submissions found for {contest_id}{problem_index}.")
        return None
    all_candidates.sort(key=lambda x: x['author'].get('rating', -1), reverse=True)
    logging.info(f"Found {len(all_candidates)} candidates after parallel search.")
    return all_candidates

# --- This is now the master data aggregation function ---
def fetch_problem_data(problem_id: str, driver: uc.Chrome, exclude_submission_ids: Optional[List[str]] = Non) -> dict | None:
    """
    Fetches all problem data using a hybrid approach:
    1. Lightweight requests for public data.
    2. Authenticated browser for protected data (solution code).
    """
    match = re.match(r"(\d+)([A-Z]\d*)", problem_id)
    if not match:
        logging.error(f"Invalid problem_id format: {problem_id}")
        return None
    contest_id, problem_index = int(match.group(1)), match.group(2)

    # Step 1: Fast, public scrape with `requests`
    logging.info(f"[{problem_id}] Step 1: Performing fast scrape for public data.")
    page_details = fetch_problem_page_details(contest_id, problem_index)
    if not page_details:
        return None # Critical failure if we can't get the problem page

    # Step 2: Find the best reference submission using the API
    logging.info(f"[{problem_id}] Step 2: Finding best reference submission via API.")
    candidate_submissions = _get_best_submission(
        str(contest_id), 
        problem_index, 
        exclude_ids=exclude_submission_ids
    )
    if not candidate_submissions:
        return None # No new submissions found

    # Step 3: Use the resource-heavy browser ONLY for authenticated scraping
    logging.info(f"[{problem_id}] Step 3: Using authenticated browser to fetch source code.")
    solution_code, ref_submission = None, None
    for candidate in candidate_submissions[:5]: # Try top 5 candidates
        submission_url = SUBMISSION_URL_TEMPLATE.format(contestId=candidate['contestId'], submissionId=candidate['id'])
        source_code_text = _get_source_from_page(driver, submission_url)
        if source_code_text:
            solution_code = source_code_text
            ref_submission = candidate
            logging.info(f"[{problem_id}] SUCCESS: Found valid source code in submission {candidate['id']}.")
            break
        else:
            logging.warning(f"[{problem_id}] Failed to get source for submission {candidate['id']}. Trying next.")
    
    if not solution_code or not ref_submission:
        logging.critical(f"[{problem_id}] Could not find any submissions with accessible source code.")
        return None

    # Step 4: Hybrid Pretest Strategy
    pretests = page_details['example_pretests']
    pretest_source = 'problem_page_examples'
    
    # Re-auth the requests session and try the internal API for more pretests
    browser_cookies = driver.get_cookies()
    for cookie in browser_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    csrf_token = soup.find('meta', {'name': 'X-Csrf-Token'})
    
    if csrf_token:
        payload = {'submissionId': ref_submission['id'], 'csrf_token': csrf_token['content']}
        try:
            logging.info(f"[{problem_id}] Step 4: Attempting to enrich pretests via internal API...")
            response = session.post(f"{INTERNAL_API_BASE}/submitSource", data=payload, headers={'Referer': driver.current_url})
            response.raise_for_status()
            data = response.json()
            api_pretests = []
            for i in range(1, int(data.get('testCount', 0)) + 1):
                input_data, answer_data = data.get(f'input#{i}'), data.get(f'answer#{i}')
                if input_data is not None and answer_data is not None:
                    api_pretests.append({'input': input_data.strip(), 'output': answer_data.strip()})
            
            if len(api_pretests) > len(pretests):
                pretests = api_pretests
                pretest_source = 'internal_api'
                logging.info(f"[{problem_id}] SUCCESS: Enriched to {len(pretests)} total pretests.")
            else:
                logging.info(f"[{problem_id}] Internal API did not provide additional pretests.")

        except Exception as e:
            logging.warning(f"[{problem_id}] Internal API call for pretests failed: {e}. Falling back to page examples.")
    else:
        logging.warning(f"[{problem_id}] Could not find CSRF token for internal API call.")

    # Step 5: Assemble and return all collected data
    return {
        "problem_id": problem_id,
        "page_details": page_details,
        "ref_submission": ref_submission,
        "solution_code": solution_code,
        "pretests": pretests,
        "pretest_source": pretest_source
    }