# synapse/optimizer.py (Phase 4D - Advanced Algorithmic Control)
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from collections import deque
from typing import Deque

# --- Project Imports ---
from synapse.config_manager import config_manager
from config import (
    PROGRESS_DB_NAME,
    OPTIMIZER_LOOP_DELAY_SECONDS,
    OPTIMIZER_COOLDOWN_PERIOD_SECONDS,
    DEFAULT_ANALYSIS_WORKER_COUNT,
    MAX_ANALYSIS_WORKERS,
    TARGET_VJS_QUEUE_SIZE
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - OPTIMIZER - %(levelname)s - %(message)s')

# --- Control System Classes ---

class AIMDController:
    """Implements the Additive Increase, Multiplicative Decrease algorithm."""
    def __init__(self, param_name: str, increase_val=1, decrease_factor=0.7, min_val=1, max_val=8):
        self.param_name = param_name
        self.increase_val = increase_val
        self.decrease_factor = decrease_factor
        self.min_val = min_val
        self.max_val = max_val

    def update(self, has_congestion: bool):
        current_val = config_manager.get_param(self.param_name)
        if has_congestion:
            # Multiplicative Decrease
            new_val = max(self.min_val, int(current_val * self.decrease_factor))
            logging.warning(f"AIMD: Congestion detected for {self.param_name}. Decreasing from {current_val} -> {new_val}")
        else:
            # Additive Increase
            new_val = min(self.max_val, current_val + self.increase_val)
        
        if new_val != current_val:
            config_manager.set_param(self.param_name, new_val)

# --- State and Metrics Analysis ---

class SystemState:
    """A simple class to hold the current calculated state of the pipeline."""
    def __init__(self):
        self.metrics_history: Deque[dict] = deque(maxlen=200)
        self.analysis_api_rate_limited = False
        self.vjs_queue_size = 0
        self.last_action_time = {} # Tracks cooldowns for parameters

    def is_in_cooldown(self, param_name: str) -> bool:
        """Checks if a parameter is currently in a cooldown period."""
        last_time = self.last_action_time.get(param_name, 0)
        return (time.time() - last_time) < OPTIMIZER_COOLDOWN_PERIOD_SECONDS

    def record_action(self, param_name: str):
        """Records that an action was taken on a parameter."""
        self.last_action_time[param_name] = time.time()

def get_pipeline_state(conn) -> SystemState:
    """Queries the database to build a snapshot of the current system state."""
    state = SystemState()
    
    # Get VJS Queue Size
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM problems WHERE status = 'pending_vjs'")
        state.vjs_queue_size = cursor.fetchone()[0]
    except sqlite3.Error:
        state.vjs_queue_size = 0

    # Get recent metrics for API rate limit detection
    try:
        since_timestamp = (datetime.now() - timedelta(minutes=2)).isoformat()
        cursor = conn.execute(
            "SELECT details_json FROM metrics WHERE worker_pool = 'ANALYSIS' AND success = 0 AND timestamp > ?",
            (since_timestamp,)
        )
        # Check if any recent failure was due to a rate limit
        for (details_json,) in cursor.fetchall():
            if details_json and 'rate' in details_json.lower():
                state.analysis_api_rate_limited = True
                break
    except sqlite3.Error:
        state.analysis_api_rate_limited = False
        
    return state

def main():
    """The main loop for the optimizer."""
    logging.info("Starting advanced optimizer process...")

    # Initialize controllers
    analysis_worker_controller = AIMDController(
        'analysis_worker_count',
        increase_val=1,
        decrease_factor=0.5, # Aggressive decrease
        min_val=1,
        max_val=MAX_ANALYSIS_WORKERS
    )

    while True:
        try:
            with sqlite3.connect(f'file:{PROGRESS_DB_NAME}?mode=ro', uri=True) as conn:
                # 1. Sense: Gather a snapshot of the current system state
                state = get_pipeline_state(conn)

                logging.info(f"State Snapshot -> VJS Queue: {state.vjs_queue_size}, Analysis API Rate Limited: {state.analysis_api_rate_limited}")

                # 2. Act: Apply control algorithms
                
                # --- Control Loop 1: AIMD for Analysis API Workers ---
                param = 'analysis_worker_count'
                if not state.is_in_cooldown(param):
                    analysis_worker_controller.update(state.analysis_api_rate_limited)
                    # If we took an action, record it to start the cooldown
                    if config_manager.get_param(param) != analysis_worker_controller.max_val:
                         state.record_action(param)

                # --- Control Loop 2: PID for VJS Queue (Simplified P-Controller for now) ---
                # A full PID is complex; a Proportional controller is a great start.
                param = 'analysis_worker_count' # We control the VJS queue by throttling the stage before it
                if not state.is_in_cooldown(param):
                    error = TARGET_VJS_QUEUE_SIZE - state.vjs_queue_size
                    current_workers = config_manager.get_param(param)

                    # If queue is too long (error is negative), we need to slow down analysis.
                    if error < -10: # Hysteresis: only act on significant error
                        new_workers = max(1, current_workers - 1)
                        if new_workers != current_workers:
                            logging.warning(f"VJS queue is too long ({state.vjs_queue_size}). Throttling analysis workers: {current_workers} -> {new_workers}")
                            config_manager.set_param(param, new_workers)
                            state.record_action(param)
                    
                    # If queue is too short (error is positive), we can speed up analysis.
                    elif error > 10: # Hysteresis
                        new_workers = min(MAX_ANALYSIS_WORKERS, current_workers + 1)
                        if new_workers != current_workers:
                            logging.info(f"VJS queue is short ({state.vjs_queue_size}). Increasing analysis workers: {current_workers} -> {new_workers}")
                            config_manager.set_param(param, new_workers)
                            state.record_action(param)

        except Exception as e:
            logging.error(f"Optimizer loop failed: {e}", exc_info=True)
        
        time.sleep(OPTIMIZER_LOOP_DELAY_SECONDS)

if __name__ == "__main__":
    main()
