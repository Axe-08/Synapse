# main.py
"""
The main entry point and orchestrator for the Project Synapse pipeline.
This script initializes all components, including the database writer,
configuration manager, and API key managers. It creates and manages thread
pools for each stage of the pipeline (Ingestion, Analysis, Implementation,
VJS, Data Assembly).
The main loop periodically queries the database for pending jobs in each
stage and submits them to the appropriate worker pool. It is designed for
continuous, resilient operation and graceful shutdown on KeyboardInterrupt.
"""
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
GEMINI_API_KEYS: list[str] = [key.strip() for key in os.getenv('GEMINI_API_KEYS', '').split(',') if key.strip()]
GROQ_API_KEYS: list[str] = [key.strip() for key in os.getenv('GROQ_API_KEYS', '').split(',') if key.strip()]
if not GEMINI_API_KEYS or not GROQ_API_KEYS:
    logging.warning("API keys not found in .env file. ARL workers may fail.")
def key_health_monitor(stop_event: threading.Event, gemini_km: KeyManager, groq_km: KeyManager) -> None:
    """
    A background thread that periodically triggers the internal state-check
    mechanism in the KeyManagers. This helps reset rate-limit windows and
    cooldowns, ensuring keys become available again over time.
    Args:
        stop_event: An event to signal when the thread should terminate.
        gemini_km: The KeyManager instance for Gemini keys.
        groq_km: The KeyManager instance for Groq keys.
    """
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

# BUGFIX: Helper function to manage dynamic pool resizing
def manage_pools(current_pools: dict, current_counts: dict) -> tuple[dict, dict]:
    """Checks config for worker count changes and resizes pools accordingly."""
    # Get the latest desired counts from the now DB-backed config manager
    desired_counts = {
        'INGESTION': config_manager.get_param('ingestion_worker_count'),
        'ANALYSIS': config_manager.get_param('analysis_worker_count'),
        'IMPLEMENTATION': config_manager.get_param('implementation_worker_count'),
        'VJS': config_manager.get_param('vjs_worker_count'),
        'DATA_ASSEMBLY': config_manager.get_param('data_assembly_worker_count')
    }

    for stage_name, desired_count in desired_counts.items():
        current_count = current_counts.get(stage_name, 0)
        if desired_count != current_count:
            logging.warning(f"CONFIG CHANGE: Resizing {stage_name} pool from {current_count} to {desired_count} workers.")
            
            # Shutdown the old pool if it exists
            if stage_name in current_pools:
                current_pools[stage_name].shutdown(wait=True)
            
            # Create a new pool with the desired size
            if desired_count > 0:
                current_pools[stage_name] = ThreadPoolExecutor(max_workers=desired_count, thread_name_prefix=stage_name.capitalize())
            elif stage_name in current_pools:
                del current_pools[stage_name] # Remove pool if count is zero
            
            current_counts[stage_name] = desired_count
            
    return current_pools, current_counts


def main(args: argparse.Namespace) -> None:
    """
    Manages worker pools for each pipeline stage, with dynamic configuration.
    This function sets up the entire application state and enters a continuous
    loop to dispatch jobs to worker threads.
    Args:
        args: Command-line arguments from argparse.
    """
    db.reset_all_workers_to_idle()
    db_writer.start()
    time.sleep(1)

    # Initialize shared resources
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

    # BUGFIX: Initialize pool and count tracking dictionaries
    # These will now be managed inside the loop to allow for dynamic resizing
    active_pools = {}
    worker_counts = {}

    # This mapping is static
    stage_definitions = {
        'INGESTION': (ingestion_worker, ('browser_queue',)),
        'ANALYSIS': (analysis_worker, ('gemini_key_manager',)),
        'IMPLEMENTATION': (implementation_worker, ('groq_key_manager',)),
        'VJS': (vjs_worker, ()),
        'DATA_ASSEMBLY': (data_assembly_worker, ()),
    }

    try:
        # BUGFIX: The browser queue size must also be dynamic.
        # We will manage the browser queue manually based on the ingestion worker count.
        browser_queue: Queue = Queue()

        while not stop_event.is_set():
            # BUGFIX: Sync config from DB at the start of each cycle
            config_manager.sync_from_db()
            
            # BUGFIX: Manage worker pools dynamically
            active_pools, worker_counts = manage_pools(active_pools, worker_counts)
            
            # BUGFIX: Adjust browser queue size to match ingestion workers
            current_ingestion_workers = worker_counts.get('INGESTION', 0)
            while browser_queue.qsize() < current_ingestion_workers:
                browser_queue.put(None) # Add placeholders for new workers
            
            # This map holds the actual resource objects
            resource_map = {
                'browser_queue': browser_queue,
                'gemini_key_manager': gemini_key_manager,
                'groq_key_manager': groq_key_manager
            }

            current_analysis_batch_size = config_manager.get_param('analysis_batch_size')
            logging.info(f"Cycle Start. Live Config: analysis_batch_size={current_analysis_batch_size}, workers={worker_counts}")
            
            active_jobs = 0
            for stage_name, pool in active_pools.items():
                if not pool or pool._shutdown: continue

                worker_func, resource_names = stage_definitions[stage_name]
                status_to_fetch = f"pending_{stage_name.lower()}"
                
                batch_size = 1
                if stage_name == 'ANALYSIS':
                    batch_size = current_analysis_batch_size

                # Fetch enough jobs to keep all workers in the pool busy
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
        for stage_name, pool in active_pools.items():
            pool.shutdown(wait=True, cancel_futures=False)
            logging.info(f"{stage_name.capitalize()} pool has shut down.")
        
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