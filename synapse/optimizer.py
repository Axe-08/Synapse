# synapse/optimizer.py
"""
The "brain" of Project Synapse. This is a standalone process that implements
a self-tuning control system for the main pipeline.

It operates on a continuous Sense-Act loop:
1.  **Sense:** It periodically queries the `progress.db` to gather a snapshot of
    the system's health, such as queue sizes and recent API failure rates.
2.  **Act:** It applies control algorithms (AIMD and PID) to make intelligent
    decisions based on the current state. For example, if it detects API rate
    limiting, it reduces the number of analysis workers. If a downstream queue
    (like VJS) is overflowing, it throttles the upstream stage that feeds it.

These decisions are written to the `dynamic_config` table, which the main
orchestrator reads on each cycle, allowing the pipeline to adapt in near real-time.
"""
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any

from synapse.config_manager import config_manager
from config import (
    PROGRESS_DB_NAME,
    OPTIMIZER_LOOP_DELAY_SECONDS,
    OPTIMIZER_COOLDOWN_PERIOD_SECONDS,
    MAX_ANALYSIS_WORKERS,
    TARGET_VJS_QUEUE_SIZE
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - OPTIMIZER - %(levelname)s - %(message)s')

class AIMDController:
    """Implements the Additive Increase, Multiplicative Decrease (AIMD) algorithm."""
    def __init__(self, param_name: str, increase_val: int = 1, decrease_factor: float = 0.7, min_val: int = 1, max_val: int = 8):
        self.param_name = param_name
        self.increase_val = increase_val
        self.decrease_factor = decrease_factor
        self.min_val = min_val
        self.max_val = max_val

    def update(self, has_congestion: bool) -> bool:
        """
        Updates the parameter based on congestion signal.

        Args:
            has_congestion: True if congestion is detected, False otherwise.

        Returns:
            True if a change was made, False otherwise.
        """
        current_val = config_manager.get_param(self.param_name)
        new_val = current_val

        if has_congestion:
            # Multiplicative Decrease
            new_val = max(self.min_val, int(current_val * self.decrease_factor))
            if new_val != current_val:
                logging.warning(f"AIMD: Congestion for '{self.param_name}'. Decreasing from {current_val} -> {new_val}")
        else:
            # Additive Increase
            new_val = min(self.max_val, current_val + self.increase_val)

        if new_val != current_val:
            config_manager.set_param(self.param_name, new_val)
            return True
        return False

class SystemState:
    """A simple class to hold the current calculated state of the pipeline."""
    def __init__(self):
        self.analysis_api_rate_limited: bool = False
        self.vjs_queue_size: int = 0
        self.last_action_time: Dict[str, float] = {}  # Tracks cooldowns

    def is_in_cooldown(self, param_name: str) -> bool:
        """Checks if a parameter is currently in a cooldown period."""
        last_time = self.last_action_time.get(param_name, 0)
        return (time.time() - last_time) < OPTIMIZER_COOLDOWN_PERIOD_SECONDS

    def record_action(self, param_name: str) -> None:
        """Records that an action was taken on a parameter."""
        self.last_action_time[param_name] = time.time()

def get_pipeline_state(conn: sqlite3.Connection) -> SystemState:
    """Queries the database to build a snapshot of the current system state."""
    state = SystemState()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM problems WHERE status = 'pending_vjs'")
        state.vjs_queue_size = cursor.fetchone()[0]
    except sqlite3.Error:
        state.vjs_queue_size = 0

    try:
        since = (datetime.now() - timedelta(minutes=2)).isoformat()
        cursor.execute(
            "SELECT details_json FROM metrics WHERE worker_pool = 'ANALYSIS' AND success = 0 AND timestamp > ?", (since,)
        )
        for (details_json,) in cursor.fetchall():
            if details_json and 'rate' in details_json.lower():
                state.analysis_api_rate_limited = True
                break
    except sqlite3.Error:
        state.analysis_api_rate_limited = False

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
            with sqlite3.connect(f'file:{PROGRESS_DB_NAME}?mode=ro', uri=True) as conn:
                current_state = get_pipeline_state(conn)
                logging.info(f"State -> VJS Queue: {current_state.vjs_queue_size}, Analysis Rate Limited: {current_state.analysis_api_rate_limited}")

                # --- Control Loop 1: AIMD for Analysis API Congestion ---
                param = 'analysis_worker_count'
                if not state.is_in_cooldown(param):
                    if analysis_worker_controller.update(current_state.analysis_api_rate_limited):
                        state.record_action(param)

                # --- Control Loop 2: Proportional Controller for VJS Queue Size ---
                # This throttles the analysis stage to keep the VJS queue at its target size.
                if not state.is_in_cooldown(param):
                    error = TARGET_VJS_QUEUE_SIZE - current_state.vjs_queue_size
                    current_workers = config_manager.get_param(param)

                    if error < -10: # Hysteresis: act only on significant error
                        new_workers = max(1, current_workers - 1)
                        if new_workers != current_workers:
                            logging.warning(f"VJS queue too long ({current_state.vjs_queue_size}). Throttling analysis: {current_workers} -> {new_workers}")
                            config_manager.set_param(param, new_workers)
                            state.record_action(param)

                    elif error > 10: # Hysteresis
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