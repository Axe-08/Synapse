# config.py
"""
This file contains the complete default configuration for Project Synapse.
It defines the pipeline's baseline behavior and safe operational limits.
All values here are considered the "default" state and can be overridden
by the dynamic configuration managed by the optimizer.
"""
# --- Core Infrastructure & Database ---
PROGRESS_DB_NAME: str = 'progress.db'
WORKSPACE_DB_PATH: str = 'workspace.db'
FINAL_DATASET_FILE: str = "dataset.jsonl"
API_URL: str = "https://codeforces.com/api/problemset.problems"
# --- Worker Concurrency (Default Values & Limits) ---
# These are the primary "levers" the optimizer can adjust.
DEFAULT_INGESTION_WORKER_COUNT: int = 1
DEFAULT_ANALYSIS_WORKER_COUNT: int = 4
DEFAULT_IMPLEMENTATION_WORKER_COUNT: int = 4
DEFAULT_VJS_WORKER_COUNT: int = 2
DEFAULT_DATA_ASSEMBLY_WORKER_COUNT: int = 1

# BUGFIX: Added hard limits for ALL worker types.
# This allows create_database.py to provision enough "slots" in the
# live_workers table for the optimizer to scale up to.
MAX_INGESTION_WORKERS: int = 2
MAX_ANALYSIS_WORKERS: int = 8
MAX_IMPLEMENTATION_WORKERS: int = 8
MAX_VJS_WORKERS: int = 4
MAX_DATA_ASSEMBLY_WORKERS: int = 2


# --- API & Batching Controls ---
DEFAULT_ANALYSIS_BATCH_SIZE: int = 5
# --- Resilience & Retry Logic ---
MAX_ANALYSIS_RETRIES: int = 3
MAX_IMPLEMENTATION_RETRIES: int = 5
MAX_RESCRAPING_ATTEMPTS: int = 2
# --- Scraper & Ingestion Timeouts (in seconds) ---
DEFAULT_SCRAPER_REQUEST_TIMEOUT: int = 40
DEFAULT_SELENIUM_LONG_WAIT: int = 120
DEFAULT_SELENIUM_SHORT_WAIT: int = 10
DEFAULT_SCRAPER_DELAY_SECONDS: float = 2.5
MAX_SCRAPER_DELAY_SECONDS: float = 10.0
# --- VJS Timeouts (in seconds) ---
VJS_COMPILATION_TIMEOUT: int = 15
# A generous multiplier for the first calibration run to account for local
# machine speed vs. judging servers.
INITIAL_CALIBRATION_TOLERANCE_FACTOR: float = 3.0

# -----------------------------------------------------------------------------
# --- Optimizer & Control System Configuration ---
# -----------------------------------------------------------------------------
# --- Optimizer Settings ---
# The frequency (in seconds) at which the optimizer runs its analysis loop.
OPTIMIZER_LOOP_DELAY_SECONDS: int = 60
# After making a change, the optimizer will wait this long (in seconds)
# before making another change to the same parameter, allowing the system to stabilize.
OPTIMIZER_COOLDOWN_PERIOD_SECONDS: int = 300  # 5 minutes
# --- PID Controller Setpoints ---
# The target number of tasks to maintain in a queue. This represents a healthy
# buffer, ensuring workers are not idle without creating excessive latency.
TARGET_VJS_QUEUE_SIZE: int = 20
TARGET_ANALYSIS_QUEUE_SIZE: int = 50