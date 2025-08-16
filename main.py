# main.py (Phase 4 - Dynamic Orchestrator)
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
from synapse.database_writer import db_writer
from synapse.config_manager import config_manager
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
    """Manages worker pools for each pipeline stage, with dynamic configuration."""
    db.reset_all_workers_to_idle()
    db_writer.start()
    
    # Initialize shared resources
    # NOTE: For this phase, we are not dynamically changing the number of
    # threads in the pools, as it's complex. We will control throughput
    # via batch sizes and other parameters first.
    ingestion_worker_count = config_manager.get_param('ingestion_worker_count')
    analysis_worker_count = config_manager.get_param('analysis_worker_count')
    implementation_worker_count = config_manager.get_param('implementation_worker_count')
    vjs_worker_count = config_manager.get_param('vjs_worker_count')
    data_assembly_worker_count = config_manager.get_param('data_assembly_worker_count')

    browser_queue = Queue(maxsize=ingestion_worker_count)
    for _ in range(ingestion_worker_count):
        browser_queue.put(None)

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
        'INGESTION': (ThreadPoolExecutor(max_workers=ingestion_worker_count, thread_name_prefix='Ingestion'), ingestion_worker, ('browser_queue',)),
        'ANALYSIS': (ThreadPoolExecutor(max_workers=analysis_worker_count, thread_name_prefix='Analysis'), analysis_worker, ('gemini_key_manager',)),
        'IMPLEMENTATION': (ThreadPoolExecutor(max_workers=implementation_worker_count, thread_name_prefix='Implementation'), implementation_worker, ('groq_key_manager',)),
        'VJS': (ThreadPoolExecutor(max_workers=vjs_worker_count, thread_name_prefix='VJS'), vjs_worker, ()),
        'DATA_ASSEMBLY': (ThreadPoolExecutor(max_workers=data_assembly_worker_count, thread_name_prefix='DataAssembly'), data_assembly_worker, ()),
    }
    
    resource_map = {
        'browser_queue': browser_queue,
        'gemini_key_manager': gemini_key_manager,
        'groq_key_manager': groq_key_manager
    }

    try:
        while not stop_event.is_set():
            # --- DYNAMIC CONFIGURATION IS NOW READ DIRECTLY BY WORKERS/FUNCTIONS ---
            # The main loop no longer needs to fetch it. We just log it for visibility.
            current_analysis_batch_size = config_manager.get_param('analysis_batch_size')
            logging.info(f"Cycle Start. Live Config: analysis_batch_size={current_analysis_batch_size}")

            active_jobs = 0
            for stage_name, (pool, worker_func, resource_names) in pools.items():
                status_to_fetch = f"pending_{stage_name.lower()}"
                
                # The number of jobs to fetch is now based on the live config
                batch_size = 1
                if stage_name == 'ANALYSIS':
                    batch_size = config_manager.get_param('analysis_batch_size')

                jobs_to_fetch = batch_size * pool._max_workers
                jobs = db.get_next_jobs(status_to_fetch, jobs_to_fetch)
                
                if jobs:
                    active_jobs += len(jobs)
                    worker_args = [resource_map[name] for name in resource_names]
                    
                    if batch_size > 1:
                        for j in range(0, len(jobs), batch_size):
                            batch = jobs[j:j+batch_size]
                            pool.submit(worker_func, batch, (j // batch_size) + 1, *worker_args)
                    else:
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
        db_writer.stop()
        logging.info("All systems nominal. Project Synapse signing off.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Project Synapse pipeline.")
    parser.add_argument("--min_rating", type=int, help="Minimum rating of problems to ingest.")
    parser.add_argument("--max_rating", type=int, help="Maximum rating of problems to ingest.")
    parser.add_argument("--run-once", action='store_true', help="Run one cycle and then exit.")
    args = parser.parse_args()
    main(args)
