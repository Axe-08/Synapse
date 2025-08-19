# synapse/scraper.py
"""
Handles all web scraping and data gathering from Codeforces.

This module implements a hybrid scraping strategy:
1.  Uses the lightweight `requests` library for public-facing pages like the
    main problem statement to quickly gather HTML, time/memory limits, and
    example pretests.
2.  Uses an authenticated `undetected-chromedriver` session (managed by a
    shared queue in `main.py`) to access pages requiring login, specifically
    the submission page to get a reference solution's source code.
3.  Uses an authenticated `requests` session (by transferring browser cookies)
    to access internal Codeforces APIs for enriching pretest data.
"""
import requests
import time
import logging
import json
import os
import shutil
import re
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Selenium Imports
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config import DEFAULT_SELENIUM_LONG_WAIT, DEFAULT_SELENIUM_SHORT_WAIT, DEFAULT_SCRAPER_REQUEST_TIMEOUT, DEFAULT_SCRAPER_DELAY_SECONDS
import synapse.database as db # To log the ban event
from synapse.config_manager import config_manager # BUGFIX: Added import

class IPBanException(Exception):
    """Custom exception for IP bans."""
    pass

# Suppress noisy logs from Selenium
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


def _parse_pre_tag(pre_tag):
    """
    Parses the content of a <pre> tag, intelligently handling both
    plain text and the newer div-based line-by-line format.
    """
    text = ""
    if not pre_tag:
        return ""
    
    line_divs = pre_tag.find_all('div', class_='test-example-line')
    if line_divs:
        text = '\n'.join(div.text for div in line_divs)
    else:
        text = '\n'.join(line for line in pre_tag.stripped_strings)
    
    # Normalize Windows-style newlines to Linux-style
    return text.replace('\r\n', '\n').strip()

def fetch_problem_page_details(contest_id: int, problem_index: str) -> dict:
    """
    Scrapes the public problem page for statement, metadata, and example pretests.
    This does NOT require a logged-in session.

    Args:
        contest_id: The contest ID of the problem.
        problem_index: The index of the problem (e.g., 'A', 'B1').

    Returns:
        A dictionary containing the problem statement HTML, raw limits, and
        any example pretests found on the page. Returns an empty dict on failure.
    """
    delay = config_manager.get_param('scraper_delay_seconds', DEFAULT_SCRAPER_DELAY_SECONDS)
    time.sleep(delay)

    url = PROBLEM_URL_TEMPLATE.format(contestId=contest_id, index=problem_index)
    logging.info(f"Scraping problem page: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': MY_USER_AGENT}, timeout=DEFAULT_SCRAPER_REQUEST_TIMEOUT)
        response.raise_for_status()
        if "blocked by administrator" in response.text.lower() or "you have been blocked" in response.text.lower():
            logging.critical(f"IP BAN DETECTED from URL: {url}")
            db.log_metric('INGESTION', 'scrape_blocked', 0, False, {'url': url})
            raise IPBanException("Scraper was blocked by administrator.")

        soup = BeautifulSoup(response.content, 'html.parser')

        problem_statement_div = soup.find('div', class_='problem-statement')
        if not problem_statement_div:
            raise Exception("Problem statement div not found.")

        time_limit_text = problem_statement_div.find('div', class_='time-limit').text.replace('time limit per test', '').strip()
        memory_limit_text = problem_statement_div.find('div', class_='memory-limit').text.replace('memory limit per test', '').strip()

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
        if isinstance(e, IPBanException):
            raise
        return {}


def get_authenticated_driver() -> Optional[uc.Chrome]:
    """
    Launches a new undetected_chromedriver instance and handles the login
    process for Codeforces, maintaining a persistent session.

    It will first try to use an existing session from the user data directory.
    If that fails, it will perform a login using credentials from the .env file.
    Manual intervention (solving a CAPTCHA) may be required.

    Returns:
        An authenticated Selenium driver instance, or None on failure.
    """
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
            long_wait = WebDriverWait(driver, DEFAULT_SELENIUM_LONG_WAIT)
            logging.info("Waiting for page... If Cloudflare appears, please solve it.")
            long_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "problems")))
            logging.info("Main page content loaded.")
        except TimeoutException:
            logging.critical(f"Page did not load after {DEFAULT_SELENIUM_LONG_WAIT} seconds.")
            driver.save_screenshot("debug_cloudflare_failure.png")
            return None

        try:
            WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
            logging.info("SUCCESS: Codeforces session is active.")
            return driver
        except TimeoutException:
            logging.info("Codeforces session not found. Proceeding to login.")
            driver.get("https://codeforces.com/enter")
            wait = WebDriverWait(driver, DEFAULT_SELENIUM_SHORT_WAIT)
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

    except WebDriverException as e:
        logging.critical(f"A WebDriver error occurred during login: {e}", exc_info=True)
        if driver:
            driver.save_screenshot("debug_webdriver_failure.png")
            driver.quit()
        return None
    except Exception:
        logging.critical("An unrecoverable error occurred during login.", exc_info=True)
        if driver:
            driver.save_screenshot("debug_login_failure.png")
            driver.quit()
        return None


def _get_source_from_page(driver: uc.Chrome, url: str) -> Optional[str]:
    """
    Navigates to a specific submission URL and scrapes the source code.

    Args:
        driver: The authenticated Selenium driver.
        url: The URL of the submission page.

    Returns:
        The scraped source code as a string, or None on failure.
    """
    try:
        logging.info(f"Navigating to submission URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, DEFAULT_SELENIUM_SHORT_WAIT)
        code_element = wait.until(EC.presence_of_element_located((By.ID, "program-source-text")))
        time.sleep(0.5)
        final_text = code_element.text.strip()
        if not final_text or final_text == "N/A":
            logging.error("Source code element found but content was empty or 'N/A'.")
            return None
        return final_text
    except Exception:
        logging.error(f"Failed to scrape source code from {url}", exc_info=False)
        return None


def _fetch_submission_page(url: str) -> Optional[dict]:
    """Helper function to fetch a single page of contest status from the API."""
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None


def _get_best_submission(contest_id: str, problem_index: str, exclude_ids: List[str]) -> Optional[List[Dict]]:
    """
    Finds suitable 'Accepted' C++ submissions for a problem via the API.

    Args:
        contest_id: The contest ID.
        problem_index: The problem index.
        exclude_ids: A list of submission IDs to ignore (from previous failed attempts).

    Returns:
        A list of candidate submission objects, sorted by author rating, or None.
    """
    all_candidates = []
    max_submissions_to_check = 1000
    batch_size = 200
    logging.info(f"Searching for candidate submissions for {contest_id}{problem_index}...")
    urls = [f"{API_BASE}/contest.status?contestId={contest_id}&from={i}&count={batch_size}" for i in range(1, max_submissions_to_check + 1, batch_size)]

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(_fetch_submission_page, url): url for url in urls}
        for future in as_completed(future_to_url):
            data = future.result()
            if not data or data.get('status') != 'OK' or not data.get('result'):
                continue

            for sub in data['result']:
                if str(sub.get('id')) in exclude_ids:
                    continue
                if ('C++' in sub.get('programmingLanguage', '') and
                        sub.get('problem', {}).get('index') == problem_index and
                        sub.get('verdict') == 'OK'):
                    all_candidates.append(sub)

    if not all_candidates:
        logging.error(f"No suitable new accepted C++ submissions found for {contest_id}{problem_index}.")
        return None

    all_candidates.sort(key=lambda x: x['author'].get('rating', -1), reverse=True)
    logging.info(f"Found {len(all_candidates)} candidate submissions.")
    return all_candidates


def fetch_problem_data(problem_id: str, driver: uc.Chrome, exclude_submission_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the fetching of all problem data using a hybrid approach.

    Args:
        problem_id: The unique ID of the problem (e.g., "1003A").
        driver: An authenticated Selenium driver instance.
        exclude_submission_ids: A list of submission IDs to exclude from the search.

    Returns:
        A dictionary containing all aggregated data for the problem, or None on critical failure.
    """
    if exclude_submission_ids is None:
        exclude_submission_ids = []
        
    match = re.match(r"(\d+)([A-Z]\d*)", problem_id)
    if not match:
        logging.error(f"Invalid problem_id format: {problem_id}")
        return None
    contest_id, problem_index = int(match.group(1)), match.group(2)

    # Step 1: Fast, public scrape with `requests`
    page_details = fetch_problem_page_details(contest_id, problem_index)
    if not page_details:
        return None

    # Step 2: Find the best reference submission via the API
    candidate_submissions = _get_best_submission(str(contest_id), problem_index, exclude_ids=exclude_submission_ids)
    if not candidate_submissions:
        return None

    # Step 3: Use the browser to scrape the source code
    solution_code, ref_submission = None, None
    for candidate in candidate_submissions[:5]:  # Try top 5 candidates
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

    # Step 4: Hybrid Pretest Strategy (enrich with internal API)
    pretests = page_details['example_pretests']
    browser_cookies = driver.get_cookies()
    for cookie in browser_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    csrf_token_meta = soup.find('meta', {'name': 'X-Csrf-Token'})

    if csrf_token_meta:
        csrf_token = csrf_token_meta['content']
        payload = {'submissionId': ref_submission['id'], 'csrf_token': csrf_token}
        try:
            logging.info(f"[{problem_id}] Attempting to enrich pretests via internal API...")
            response = session.post(f"{INTERNAL_API_BASE}/submitSource", data=payload, headers={'Referer': driver.current_url})
            response.raise_for_status()
            data = response.json()
            api_pretests = []
            for i in range(1, int(data.get('testCount', 0)) + 1):
                input_data, answer_data = data.get(f'input#{i}'), data.get(f'answer#{i}')
                if input_data is not None and answer_data is not None:
                    clean_input = input_data.replace('\r\n', '\n').strip()
                    clean_output = answer_data.replace('\r\n', '\n').strip()
                    api_pretests.append({'input': clean_input, 'output': clean_output})
            # --- CORRECTED LOGIC ---
            # If the API returned any tests, it is the definitive source.
            if api_pretests:
                pretests = api_pretests
                logging.info(f"[{problem_id}] SUCCESS: Replaced example tests with {len(pretests)} full pretests from API.")
            else:
                logging.warning(f"[{problem_id}] API enrichment returned no pretests. Falling back to {len(pretests)} examples scraped from HTML.")
            # --- END CORRECTION ---

        except Exception as e:
            logging.warning(f"[{problem_id}] Internal API call for pretests failed: {e}")


    # Step 5: Assemble and return
    return {
        "problem_id": problem_id,
        "page_details": page_details,
        "ref_submission": ref_submission,
        "solution_code": solution_code,
        "pretests": pretests,
    }