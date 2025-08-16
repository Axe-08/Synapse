# main.py (Definitive Phase 1 Version)
import argparse
import logging
import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from queue import Queue

# --- Configuration & Setup ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
)

# Import from our project modules
from synapse import database as db
from synapse.key_manager import KeyManager
from synapse.workers import (
    ingestion_worker,
    analysis_worker,
    implementation_worker,
    vjs_worker,
    data_assembly_worker
)
# Import configuration constants
from create_database import (
    INGESTION_WORKER_COUNT,
    ANALYSIS_WORKER_COUNT,
    IMPLEMENTATION_WORKER_COUNT,
    VJS_WORKER_COUNT,
    DATA_ASSEMBLY_WORKER_COUNT
)

# Static batch size for the analysis stage (can be made dynamic in Phase 4)
ANALYSIS_BATCH_SIZE = 5
MAX_ANALYSIS_RETRIES = 3    # Max times a problem can be sent back for re-analysis
MAX_IMPLEMENTATION_RETRIES = 5 # Max times a problem can be sent back for re-implementation

# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEYS = [key.strip() for key in os.getenv('GEMINI_API_KEYS', '').split(',') if key.strip()]
GROQ_API_KEYS = [key.strip() for key in os.getenv('GROQ_API_KEYS', '').split(',') if key.strip()]

if not GEMINI_API_KEYS or not GROQ_API_KEYS:
    logging.warning("API keys not found in .env file. ARL workers may fail.")

# --- Background Health Monitor Thread ---
def key_health_monitor(stop_event: threading.Event, gemini_km: KeyManager, groq_km: KeyManager):
    """Periodically triggers the internal state-check mechanism in the KeyManagers."""
    while not stop_event.is_set():
        try:
            with gemini_km._lock:
                gemini_km._check_and_reset_windows()
            with groq_km._lock:
                groq_km._check_and_reset_windows()
        except Exception as e:
            logging.warning(f"Key health monitor encountered an error: {e}")
        
        # Sleep for a short duration, checking the stop_event frequently
        for _ in range(10):
            if stop_event.is_set():
                break
            time.sleep(1)

# --- The Main Orchestrator ---
def main(args):
    """Manages worker pools for each pipeline stage."""
    db.reset_all_workers_to_idle()
    
    # Initialize shared resources
    browser_queue = Queue(maxsize=INGESTION_WORKER_COUNT)
    for _ in range(INGESTION_WORKER_COUNT):
        browser_queue.put(None) # None acts as a signal to create a new browser

    gemini_key_manager = KeyManager(GEMINI_API_KEYS, "GEMINI")
    groq_key_manager = KeyManager(GROQ_API_KEYS, "GROQ")
    
    stop_event = threading.Event()
    health_monitor_thread = threading.Thread(
        target=key_health_monitor,
        args=(stop_event, gemini_key_manager, groq_key_manager),
        name="KeyHealthMonitor",
        daemon=True
    )
    health_monitor_thread.start()

    pools = {
        'INGESTION': (ThreadPoolExecutor(max_workers=INGESTION_WORKER_COUNT, thread_name_prefix='Ingestion'), ingestion_worker, 1, ('browser_queue',)),
        'ANALYSIS': (ThreadPoolExecutor(max_workers=ANALYSIS_WORKER_COUNT, thread_name_prefix='Analysis'), analysis_worker, ANALYSIS_BATCH_SIZE, ('gemini_key_manager',)),
        'IMPLEMENTATION': (ThreadPoolExecutor(max_workers=IMPLEMENTATION_WORKER_COUNT, thread_name_prefix='Implementation'), implementation_worker, 1, ('groq_key_manager',)),
        'VJS': (ThreadPoolExecutor(max_workers=VJS_WORKER_COUNT, thread_name_prefix='VJS'), vjs_worker, 1, ()),
        'DATA_ASSEMBLY': (ThreadPoolExecutor(max_workers=DATA_ASSEMBLY_WORKER_COUNT, thread_name_prefix='DataAssembly'), data_assembly_worker, 1, ()),
    }
    
    resource_map = {
        'browser_queue': browser_queue,
        'gemini_key_manager': gemini_key_manager,
        'groq_key_manager': groq_key_manager
    }

    try:
        while not stop_event.is_set():
            active_jobs = 0
            # Dispatch jobs for all stages
            for i, (stage_name, (pool, worker_func, batch_size, resource_names)) in enumerate(pools.items()):
                status_to_fetch = f"pending_{stage_name.lower()}"
                jobs = db.get_next_jobs(status_to_fetch, batch_size * pool._max_workers)
                
                if jobs:
                    active_jobs += len(jobs)
                    worker_args = [resource_map[name] for name in resource_names]
                    
                    if batch_size > 1: # Batch processing for Analysis stage
                        for j in range(0, len(jobs), batch_size):
                            batch = jobs[j:j+batch_size]
                            pool.submit(worker_func, batch, j//batch_size + 1, *worker_args)
                    else: # Single job processing for all other stages
                        for j, job in enumerate(jobs):
                            pool.submit(worker_func, job, j + 1, *worker_args)
            
            if args.run_once:
                logging.info("--run-once specified. Exiting after one cycle.")
                break

            if not active_jobs:
                logging.info("No pending jobs in any stage. Waiting...")
                time.sleep(20)
            else:
                time.sleep(10)

    except KeyboardInterrupt:
        logging.info("Shutdown signal received. Stopping job dispatch...")
    finally:
        stop_event.set()
        
        logging.info("Shutting down all worker pools...")
        for stage_name, (pool, _, _, _) in pools.items():
            pool.shutdown(wait=True, cancel_futures=False)
            logging.info(f"{stage_name} pool has shut down.")

        logging.info("Cleaning up browser instances...")
        while not browser_queue.empty():
            driver = browser_queue.get_nowait()
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        
        health_monitor_thread.join(timeout=5)
        logging.info("All systems nominal. Project Synapse signing off.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline.")
    parser.add_argument("--min_rating", type=int, help="Minimum rating of problems to ingest.")
    parser.add_argument("--max_rating", type=int, help="Maximum rating of problems to ingest.")
    parser.add_argument("--run-once", action='store_true', help="Run one cycle and then exit.")
    args = parser.parse_args()
    main(args)