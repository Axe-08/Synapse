# ingestion_node.py
"""
Laptop-side ingestion process for the hybrid Synapse pipeline.

This is the ONLY script that runs on the laptop. It polls the shared
PostgreSQL database (via SSH tunnel) for pending_ingestion problems,
scrapes them using Selenium/Chrome, and writes the results back.

Start the SSH tunnel first:
    make tunnel

Then run:
    python ingestion_node.py
"""
import logging
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
)

load_dotenv()

# Validate DATABASE_URL is set (SSH tunnel must be open)
_DATABASE_URL = os.getenv('DATABASE_URL', '')
if not _DATABASE_URL:
    logging.critical(
        "DATABASE_URL not set. "
        "Open the SSH tunnel first: make tunnel\n"
        "Then set DATABASE_URL=postgresql://synapse:synapse@localhost:5432/synapse_db"
    )
    raise SystemExit(1)

from synapse import database as db
from synapse.database_writer import db_writer
from synapse.config_manager import config_manager
from synapse.workers import ingestion_worker


def main() -> None:
    """Ingestion-only orchestration loop."""
    db.reset_all_workers_to_idle()
    db_writer.start()
    time.sleep(1)

    # Browser queue — each ingestion worker holds one browser instance
    browser_queue: Queue = Queue()

    pool: ThreadPoolExecutor | None = None
    current_worker_count = 0
    stop_event = threading.Event()

    logging.info("Ingestion node started. Polling for pending_ingestion problems...")

    try:
        while not stop_event.is_set():
            config_manager.sync_from_db()
            desired = config_manager.get_param('ingestion_worker_count')

            # Resize pool if needed
            if desired != current_worker_count:
                logging.info(f"Resizing ingestion pool: {current_worker_count} → {desired}")
                if pool:
                    pool.shutdown(wait=True)
                # Adjust browser queue size
                while browser_queue.qsize() < desired:
                    browser_queue.put(None)
                pool = ThreadPoolExecutor(
                    max_workers=desired,
                    thread_name_prefix="Ingestion"
                )
                current_worker_count = desired

            if not pool or desired == 0:
                time.sleep(10)
                continue

            jobs = db.get_next_jobs('pending_ingestion', desired)
            if jobs:
                for i, job in enumerate(jobs):
                    pool.submit(ingestion_worker, job, f"INGESTION-{i+1}", browser_queue)
                time.sleep(5)
            else:
                logging.info("No pending ingestion jobs. Waiting 20s...")
                time.sleep(20)

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    finally:
        stop_event.set()
        if pool:
            pool.shutdown(wait=True, cancel_futures=False)
        # Clean up browser instances
        while not browser_queue.empty():
            driver = browser_queue.get_nowait()
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        db_writer.stop()
        logging.info("Ingestion node stopped.")


if __name__ == "__main__":
    main()
