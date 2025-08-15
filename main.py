# main.py (The Final, Corrected Orchestrator)
import argparse
import logging
import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from queue import Queue

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s')

# Import core orchestration functions
from synapse.database import (
    get_next_jobs,
    update_worker_status,
    reset_all_workers_to_idle,
    update_key_statuses,
)
from synapse.key_manager import KeyManager
from create_database import INGESTION_WORKER_COUNT, ARL_WORKER_COUNT, VJS_WORKER_COUNT

# Import the refactored worker functions
from synapse.workers import (
    ingestion_worker,
    arl_worker,
    vjs_worker
)

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEYS = [key.strip() for key in os.getenv('GEMINI_API_KEY', '').split(',') if key.strip()]
GROQ_API_KEYS = [key.strip() for key in os.getenv('GROQ_API_KEY', '').split(',') if key.strip()]

if not GEMINI_API_KEYS or not GROQ_API_KEYS:
    logging.warning("API keys for ARL not found in .env file. ARL workers will fail.")

# --- Background Heartbeat Thread ---
def key_status_heartbeat(stop_event: threading.Event, gemini_km: KeyManager, groq_km: KeyManager):
    """A background thread that periodically saves key statuses to the DB."""
    while not stop_event.is_set():
        try:
            update_key_statuses('GEMINI', gemini_km._keys)
            update_key_statuses('GROQ', groq_km._keys)
        except Exception as e:
            logging.warning(f"Key status heartbeat failed: {e}")
        for _ in range(5):
            if stop_event.is_set(): break
            time.sleep(1)

# --- The Main Orchestrator ---
def main(args):
    """Manages worker pools for each pipeline stage."""
    reset_all_workers_to_idle()
    
    browser_queue = Queue(maxsize=INGESTION_WORKER_COUNT)
    for _ in range(INGESTION_WORKER_COUNT):
        browser_queue.put(None)

    gemini_key_manager = KeyManager(GEMINI_API_KEYS)
    groq_key_manager = KeyManager(GROQ_API_KEYS)
    
    stop_event = threading.Event()
    heartbeat_thread = threading.Thread(
        target=key_status_heartbeat, 
        args=(stop_event, gemini_key_manager, groq_key_manager),
        name="KeyHeartbeat",
        daemon=True
    )
    heartbeat_thread.start()

    with ThreadPoolExecutor(max_workers=INGESTION_WORKER_COUNT, thread_name_prefix='INGEST-WORKER') as ingest_pool, \
         ThreadPoolExecutor(max_workers=ARL_WORKER_COUNT, thread_name_prefix='ARL-WORKER') as arl_pool, \
         ThreadPoolExecutor(max_workers=VJS_WORKER_COUNT, thread_name_prefix='VJS-WORKER') as vjs_pool:
        try:
            while not stop_event.is_set():
                ingestion_jobs = get_next_jobs('pending_ingestion', INGESTION_WORKER_COUNT, args.min_rating, args.max_rating)
                for i, job in enumerate(ingestion_jobs):
                    ingest_pool.submit(ingestion_worker, job, i + 1, browser_queue)
                
                arl_jobs = get_next_jobs('pending_arl', ARL_WORKER_COUNT)
                for i, job in enumerate(arl_jobs):
                    arl_pool.submit(arl_worker, job, i + 1 + INGESTION_WORKER_COUNT, gemini_key_manager, groq_key_manager)
                
                vjs_jobs = get_next_jobs('pending_vjs', VJS_WORKER_COUNT)
                for i, job in enumerate(vjs_jobs):
                    vjs_pool.submit(vjs_worker, job, i + 1 + INGESTION_WORKER_COUNT + ARL_WORKER_COUNT)

                if args.run_once:
                    logging.info("--run-once: processing one batch of jobs and then exiting.")
                    break
                
                if not any([ingestion_jobs, arl_jobs, vjs_jobs]):
                    logging.info("No pending jobs in any stage. Waiting for 30 seconds...")
                    time.sleep(30)
                else:
                    time.sleep(15)

        except KeyboardInterrupt:
            logging.info("Shutdown signal received...")
        finally:
            stop_event.set()
            # Shut down all browsers gracefully
            while not browser_queue.empty():
                driver = browser_queue.get_nowait()
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
            heartbeat_thread.join(timeout=2)

    logging.info("All worker pools have shut down. Project Synapse signing off.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse stage-centric pipeline.")
    parser.add_argument("--min_rating", type=int, help="Minimum rating of problems to ingest.")
    parser.add_argument("--max_rating", type=int, help="Maximum rating of problems to ingest.")
    parser.add_argument("--run-once", action='store_true', help="Run one cycle of job fetching and then exit.")
    args = parser.parse_args()
    main(args)