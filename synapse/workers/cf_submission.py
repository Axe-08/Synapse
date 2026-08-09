# synapse/workers/cf_submission.py
"""
Stage: CF Submission Worker

Routes non-standard problems (interactive, special_judge, constructive) through
Codeforces' own online judge instead of the local VJS.

Pipeline:
1. Retrieve the generated code + problem metadata from workspace.
2. Submit code to Codeforces via authenticated scraper account.
3. Poll the submission verdict.
4. Record result in database — ACCEPTED → pending_data_assembly, else retry/quarantine.
"""
from ._shared import (
    logging, json, time,
    Dict, Any,
    db,
    MAX_IMPLEMENTATION_RETRIES,
)

import re
from queue import Queue
from typing import Optional

# Submission polling config
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 60     # 5 min max wait
SUBMIT_DELAY_SECONDS = 3   # Courtesy delay before submission


def _extract_verdict_from_page(page_source: str) -> Optional[str]:
    """
    Parse the submission verdict from the CF submission page HTML.

    Returns one of:
        'ACCEPTED', 'WRONG_ANSWER', 'TIME_LIMIT_EXCEEDED',
        'MEMORY_LIMIT_EXCEEDED', 'RUNTIME_ERROR', 'COMPILATION_ERROR',
        'IDLENESS_LIMIT_EXCEEDED', 'TESTING', None (if not yet judged).
    """
    verdict_map = {
        'accepted': 'ACCEPTED',
        'wrong answer': 'WRONG_ANSWER',
        'time limit exceeded': 'TIME_LIMIT_EXCEEDED',
        'memory limit exceeded': 'MEMORY_LIMIT_EXCEEDED',
        'runtime error': 'RUNTIME_ERROR',
        'compilation error': 'COMPILATION_ERROR',
        'idleness limit exceeded': 'IDLENESS_LIMIT_EXCEEDED',
    }
    page_lower = page_source.lower()
    for pattern, verdict in verdict_map.items():
        if f'verdict-{pattern.replace(" ", "")}' in page_lower.replace(' ', ''):
            return verdict
        if f'>{pattern}<' in page_lower:
            return verdict

    if 'testing' in page_lower or 'in queue' in page_lower:
        return 'TESTING'

    return None


def _extract_submission_id(page_source: str) -> Optional[str]:
    """Extract the submission ID from the CF page after submitting."""
    match = re.search(r'/submission/(\d+)', page_source)
    if match:
        return match.group(1)
    return None


def cf_submission_worker(
    problem: Dict[str, Any],
    worker_id: str,
    browser_queue: Queue,
) -> None:
    """
    Submit generated code to Codeforces for judging.

    For non-standard problems (interactive, special_judge, constructive)
    where local VJS cannot verify correctness, we rely on CF's own judge.

    Args:
        problem: Dict with 'id' and optionally 'problem_class'.
        worker_id: Worker thread identifier.
        browser_queue: Queue for acquiring authenticated browser instances.
    """
    problem_id = problem['id']
    problem_class = problem.get('problem_class', 'standard')
    start_time = time.perf_counter()
    db.update_worker_status(worker_id, 'CF_SUBMISSION', problem_id, 'PROCESSING', 'active')

    try:
        # 1. Retrieve generated code from workspace
        workspace_data = db.get_workspace_data(problem_id)
        if not workspace_data:
            raise Exception(f"No workspace data found for {problem_id}")

        code = workspace_data.get('arl_reconstructed_code')
        if not code:
            raise Exception(f"No implementation code found for {problem_id}")

        # Parse problem ID into contest_id and index
        match = re.match(r'(\d+)([A-Z]\d?)', problem_id)
        if not match:
            raise Exception(f"Cannot parse problem ID: {problem_id}")
        contest_id = match.group(1)
        problem_index = match.group(2)

        # 2. Acquire browser and submit
        driver = browser_queue.get(timeout=300)
        if driver is None:
            from synapse.scraper import get_authenticated_driver
            driver = get_authenticated_driver()
            if not driver:
                raise Exception("Failed to get authenticated browser.")

        try:
            submission_id = _submit_solution(driver, contest_id, problem_index, code)
            if not submission_id:
                raise Exception("Failed to submit solution — no submission ID returned.")

            logging.info(
                f"[{problem_id}] Submitted as #{submission_id}. Polling for verdict..."
            )

            # 3. Poll for verdict
            verdict = _poll_verdict(driver, contest_id, submission_id)
            logging.info(f"[{problem_id}] CF verdict: {verdict}")

            # 4. Process result
            if verdict == 'ACCEPTED':
                db.save_process_history(
                    problem_id, 'CF_SUBMISSION', 'SUCCESS',
                    f'CF accepted (class={problem_class}, sub={submission_id})'
                )
                db._update_problem_status(problem_id, 'pending_data_assembly', {})
            else:
                _handle_rejection(problem_id, verdict, submission_id)

        finally:
            try:
                browser_queue.put(driver)
            except Exception:
                pass

        elapsed = time.perf_counter() - start_time
        db.log_metric('CF_SUBMISSION', 'submission_complete', elapsed, verdict == 'ACCEPTED', {
            'problem_class': problem_class,
            'verdict': verdict,
            'submission_id': submission_id,
        })

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        logging.error(f"[{problem_id}] CF submission failed: {e}", exc_info=True)
        db.save_process_history(problem_id, 'CF_SUBMISSION', 'FAILURE', str(e)[:500])
        db.log_metric('CF_SUBMISSION', 'submission_error', elapsed, False, {'error': str(e)[:200]})
        # Re-queue for retry if under limit
        _handle_rejection(problem_id, 'ERROR', '')

    finally:
        db.update_worker_status(worker_id, 'CF_SUBMISSION', '', 'IDLE', 'active')


def _submit_solution(driver, contest_id: str, index: str, code: str) -> Optional[str]:
    """
    Submit a C++ solution to Codeforces via the browser.

    Returns the submission ID string, or None on failure.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC

    submit_url = f"https://codeforces.com/contest/{contest_id}/submit"
    driver.get(submit_url)
    time.sleep(SUBMIT_DELAY_SECONDS)

    try:
        wait = WebDriverWait(driver, 15)

        # Select problem index
        problem_select = wait.until(
            EC.presence_of_element_located((By.NAME, "submittedProblemIndex"))
        )
        Select(problem_select).select_by_value(index)

        # Select language (GNU G++23 = language ID 91)
        lang_select = wait.until(
            EC.presence_of_element_located((By.NAME, "programTypeId"))
        )
        Select(lang_select).select_by_value("91")

        # Ensure the plain text editor is enabled (bypassing CodeMirror overlay)
        try:
            driver.execute_script(
                "var t = document.getElementById('toggleEditorCheckbox'); "
                "if (t && !t.checked) t.click();"
            )
            time.sleep(0.5)
        except Exception:
            pass

        # Paste code
        source_input = wait.until(
            EC.presence_of_element_located((By.ID, "sourceCodeTextarea"))
        )
        source_input.clear()
        source_input.send_keys(code)

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "input.submit")
        submit_btn.click()

        # Wait for redirect to my submissions page
        time.sleep(3)
        return _extract_submission_id(driver.page_source)

    except Exception as e:
        logging.error(f"Failed to submit solution: {e}")
        return None


def _poll_verdict(driver, contest_id: str, submission_id: str) -> str:
    """
    Poll the CF submission page until a final verdict is reached.

    Returns the verdict string (ACCEPTED, WRONG_ANSWER, etc.).
    """
    url = f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}"

    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            driver.get(url)
            time.sleep(POLL_INTERVAL_SECONDS)
            verdict = _extract_verdict_from_page(driver.page_source)

            if verdict and verdict != 'TESTING':
                return verdict

            logging.debug(
                f"Submission #{submission_id}: still testing (poll {attempt + 1}/{MAX_POLL_ATTEMPTS})"
            )
        except Exception as e:
            logging.warning(f"Poll error for #{submission_id}: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)

    return 'TIMEOUT'


def _handle_rejection(problem_id: str, verdict: str, submission_id: str) -> None:
    """Handle a non-ACCEPTED verdict from CF."""
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        row = conn.execute(
            "SELECT implementation_try_count FROM problems WHERE id = ?",
            (problem_id,)
        ).fetchone()
        tries = (row[0] if row else 0) or 0

    if tries < MAX_IMPLEMENTATION_RETRIES:
        # Retry: go back to implementation with feedback
        report = f"CF verdict: {verdict} (submission #{submission_id}). Retry #{tries + 1}."
        db._update_problem_status(problem_id, 'pending_implementation', {
            'implementation_try_count': tries + 1,
            'last_vjs_report': report,
            'priority': 1,
        })
        db.save_process_history(problem_id, 'CF_SUBMISSION', 'RETRY', report)
    else:
        reason = f"Exhausted {MAX_IMPLEMENTATION_RETRIES} tries. Last verdict: {verdict}."
        db.transition_to_quarantined(problem_id, reason)
