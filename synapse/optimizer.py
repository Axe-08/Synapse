# synapse/optimizer.py
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict

from synapse.config_manager import config_manager
from config import (
    PROGRESS_DB_NAME,
    OPTIMIZER_LOOP_DELAY_SECONDS,
    OPTIMIZER_COOLDOWN_PERIOD_SECONDS,
    MAX_ANALYSIS_WORKERS,
    TARGET_VJS_QUEUE_SIZE,
    DEFAULT_SCRAPER_DELAY_SECONDS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - OPTIMIZER - %(levelname)s - %(message)s')

class AIMDController:
    """Implements the Additive Increase, Multiplicative Decrease (AIMD) algorithm."""
    def __init__(self, param_name: str, increase_val: int = 1, decrease_factor: float = 0.5, min_val: int = 1, max_val: int = 8):
        self.param_name = param_name
        self.increase_val = increase_val
        self.decrease_factor = decrease_factor
        self.min_val = min_val
        self.max_val = max_val

    def update(self, has_congestion: bool) -> bool:
        current_val = config_manager.get_param(self.param_name)
        new_val = current_val
        if has_congestion:
            new_val = max(self.min_val, int(current_val * self.decrease_factor))
        else:
            new_val = min(self.max_val, current_val + self.increase_val)
        
        if new_val != current_val:
            config_manager.set_param(self.param_name, new_val)
            return True
        return False

class SystemState:
    """A simple class to hold the current calculated state of the pipeline."""
    def __init__(self):
        self.is_ip_banned: bool = False
        self.ingestion_recent_failures: int = 0
        self.analysis_api_rate_limited: bool = False
        self.vjs_queue_size: int = 0
        self.last_action_time: Dict[str, float] = {}

    def is_in_cooldown(self, param_name: str) -> bool:
        last_time = self.last_action_time.get(param_name, 0)
        return (time.time() - last_time) < OPTIMIZER_COOLDOWN_PERIOD_SECONDS

    def record_action(self, param_name: str) -> None:
        self.last_action_time[param_name] = time.time()

def get_pipeline_state(conn: sqlite3.Connection) -> SystemState:
    """Queries the database to build a snapshot of the current system state."""
    state = SystemState()
    cursor = conn.cursor()
    since_5_min = (datetime.now() - timedelta(minutes=5)).isoformat()
    try:
        cursor.execute("SELECT 1 FROM metrics WHERE event_type = 'scrape_blocked' AND timestamp > ?", (since_5_min,))
        state.is_ip_banned = cursor.fetchone() is not None

        cursor.execute("SELECT COUNT(*) FROM metrics WHERE worker_pool = 'INGESTION' AND success = 0 AND details_json NOT LIKE '%IP_BAN_DETECTED%' AND timestamp > ?", (since_5_min,))
        state.ingestion_recent_failures = cursor.fetchone()[0]
        
        cursor.execute("SELECT 1 FROM metrics WHERE worker_pool = 'ANALYSIS' AND success = 0 AND details_json LIKE '%rate%' AND timestamp > ?", (since_5_min,))
        state.analysis_api_rate_limited = cursor.fetchone() is not None

        cursor.execute("SELECT COUNT(*) FROM problems WHERE status = 'pending_vjs'")
        state.vjs_queue_size = cursor.fetchone()[0]
    except sqlite3.Error as e:
        logging.error(f"Failed to get pipeline state: {e}")
    return state

def main() -> None:
    """The main loop for the optimizer."""
    logging.info("Starting optimizer process...")
    state = SystemState()
    analysis_worker_controller = AIMDController(
        'analysis_worker_count',
        increase_val=1,
        decrease_factor=0.5,
        min_val=1,
        max_val=MAX_ANALYSIS_WORKERS
    )

    while True:
        try:
            config_manager.sync_from_db()
            with sqlite3.connect(f'file:{PROGRESS_DB_NAME}?mode=ro', uri=True) as conn:
                current_state = get_pipeline_state(conn)

            logging.info(
                f"State -> IP Banned: {current_state.is_ip_banned}, "
                f"Ingestion Fails: {current_state.ingestion_recent_failures}, "
                f"API Rate Limited: {current_state.analysis_api_rate_limited}, "
                f"VJS Queue: {current_state.vjs_queue_size}"
            )

            # --- PANIC MODE - HIGHEST PRIORITY ---
            if current_state.is_ip_banned and not state.is_in_cooldown('panic_mode'):
                logging.critical("PANIC MODE: IP Ban Detected! Pausing all scraping activities for 2 hours.")
                config_manager.set_param('ingestion_worker_count', 0)
                state.record_action('panic_mode')
                time.sleep(7200) # 2 hours
                
                logging.warning("PANIC MODE: Resuming cautiously with one ingestion worker.")
                config_manager.set_param('ingestion_worker_count', 1)
                state.record_action('ingestion_worker_count')
                continue

            # --- ADAPTIVE SCRAPER THROTTLE ---
            param = 'scraper_delay_seconds'
            if not state.is_in_cooldown(param):
                current_delay = config_manager.get_param(param, DEFAULT_SCRAPER_DELAY_SECONDS)
                if current_state.ingestion_recent_failures > 2:
                    new_delay = min(10.0, current_delay + 0.5)
                    if new_delay != current_delay:
                        logging.warning(f"Throttling scraper due to failures. Delay: {current_delay:.2f}s -> {new_delay:.2f}s")
                        config_manager.set_param(param, new_delay)
                        state.record_action(param)
                elif current_delay > DEFAULT_SCRAPER_DELAY_SECONDS:
                    new_delay = max(DEFAULT_SCRAPER_DELAY_SECONDS, current_delay - 0.25)
                    if new_delay != current_delay:
                        config_manager.set_param(param, new_delay)
                        state.record_action(param)

            # --- BUGFIX: REFINED ANALYSIS WORKER CONTROL LOGIC ---
            param = 'analysis_worker_count'
            if not state.is_in_cooldown(param):
                is_congested = current_state.analysis_api_rate_limited
                
                # AIMD controller has priority for congestion signals. It will decrease workers.
                if is_congested:
                    if analysis_worker_controller.update(True):
                        logging.warning("AIMD: API rate limit detected. Reducing analysis workers.")
                        state.record_action(param)
                else:
                    # If no congestion, use P-controller for queue management.
                    error = TARGET_VJS_QUEUE_SIZE - current_state.vjs_queue_size
                    current_workers = config_manager.get_param(param)
                    
                    if error < -10: # Queue is too long, decrease analysis workers
                        new_workers = max(1, current_workers - 1)
                        if new_workers != current_workers:
                            logging.warning(f"VJS queue too long ({current_state.vjs_queue_size}). Throttling analysis: {current_workers} -> {new_workers}")
                            config_manager.set_param(param, new_workers)
                            state.record_action(param)
                    elif error > 10: # Queue is short, increase analysis workers
                        new_workers = min(MAX_ANALYSIS_WORKERS, current_workers + 1)
                        if new_workers != current_workers:
                            logging.info(f"VJS queue is short ({current_state.vjs_queue_size}). Increasing analysis: {current_workers} -> {new_workers}")
                            config_manager.set_param(param, new_workers)
                            state.record_action(param)

        except Exception as e:
            logging.error(f"Optimizer loop failed: {e}", exc_info=True)
            
        time.sleep(OPTIMIZER_LOOP_DELAY_SECONDS)

if __name__ == "__main__":
    main()