# synapse/workers/ingestion.py
"""
Stage 1: Ingestion Worker

Handles scraping all necessary data for a problem from Codeforces.
Can also perform re-scraping to find a new reference solution if a
problem fails analysis too many times.
"""
from ._shared import (
    logging, json, time, os, Queue, Dict, Any,
    db, MAX_BROWSER_USES,
)
from synapse.scraper import get_authenticated_driver, fetch_problem_data, IPBanException, classify_problem


def ingestion_worker(problem: Dict[str, Any], worker_id: str, browser_queue: Queue):
    """
    Handles scraping all necessary data for a problem from Codeforces.
    This worker can also perform re-scraping to find a new reference solution
    if a problem fails analysis too many times.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
        browser_queue: A queue to get/return a shared browser instance.
    """
    problem_id = problem['id']
    driver = None
    start_time = time.perf_counter()
    is_rescraping = False
    db.update_worker_status(worker_id, 'INGESTION', problem_id, 'PROCESSING', 'active')

    try:
        # Check current state to see if this is a re-scrape job
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT status, tried_submission_ids FROM problems WHERE id = ?",
                (problem_id,)
            )
            result = cursor.fetchone()
            if not result:
                raise Exception(f"Problem {problem_id} not found.")
            current_status, tried_ids_str = result
            is_rescraping = current_status == 'in_progress_rescraping'
            exclude_ids = tried_ids_str.split(',') if tried_ids_str else []

        # Acquire a browser instance
        driver = browser_queue.get(timeout=300)
        if driver is None:
            driver = get_authenticated_driver()
            if not driver:
                raise Exception("Failed to initialize a new browser session.")

        # Perform the scrape
        scraped_data = fetch_problem_data(problem_id, driver, exclude_submission_ids=exclude_ids)

        html_statement = scraped_data['page_details']['problem_statement_html']

        # Classify the problem instead of quarantining interactive ones
        problem_class = classify_problem(
            problem_type=scraped_data.get('problem_type', ''),
            tags=scraped_data.get('tags', []),
            statement_html=html_statement,
        )
        if problem_class != 'standard':
            logging.info(f"Classified {problem_id} as '{problem_class}'")

        if not scraped_data:
            reason = "Failed to find a new valid reference solution."
            logging.warning(f"QUARANTINING {problem_id}: {reason}")
            db.transition_to_quarantined(problem_id, reason)
            raise Exception(reason)

        # Save data and transition state
        db.save_multi_oracle_ingestion_data(
            problem_id=problem_id,
            html=html_statement,
            pretests=scraped_data['pretests'],
            successful_solutions=scraped_data['successful_solutions'],
            time_limit_raw=scraped_data['page_details']['time_limit_raw'],
            memory_limit_raw=scraped_data['page_details']['memory_limit_raw'],
            problem_class=problem_class,
        )
        if is_rescraping:
            db.reset_retry_counts(problem_id)
        db.transition_to_pending_calibration(problem_id)
        logging.info(f"SUCCESS [Ingestion/Re-scrape] for {problem_id}. -> pending_calibration")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'INGESTION', 'ingestion_task', duration_ms, True,
            {'problem_id': problem_id, 'rescraped': is_rescraping},
        )

    except IPBanException:
        logging.critical(f"STOPPING INGESTION for {problem_id} due to IP BAN.")
        db.transition_to_failed(problem_id, 'ingestion', 'IP_BAN_DETECTED')

    except Exception as e:
        import traceback
        logging.error(f"Full traceback for ingestion failure on {problem_id}:")
        traceback.print_exc()
        if "Failed to find a new" not in str(e):
            logging.error(f"FAILED [Ingestion] for {problem_id}: {e}", exc_info=False)
            db.transition_to_failed(problem_id, 'ingestion', str(e))

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'INGESTION', 'ingestion_task', duration_ms, False,
            {'problem_id': problem_id, 'error': str(e)},
        )

        if 'driver' in locals() and driver is None:
            browser_queue.put(None)
            return

    finally:
        if 'driver' in locals() and driver is not None:
            if not hasattr(driver, 'uses_count'):
                driver.uses_count = 0
            driver.uses_count += 1
            if driver.uses_count >= MAX_BROWSER_USES:
                logging.warning(
                    f"Retiring browser instance after {driver.uses_count} uses."
                )
                try:
                    driver.quit()
                except Exception as quit_err:
                    logging.error(f"Error quitting retired browser: {quit_err}")
                browser_queue.put(None)
            else:
                browser_queue.put(driver)

        db.update_worker_status(worker_id, 'INGESTION', None, None, 'idle')
