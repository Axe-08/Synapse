# config.py
# This file contains the complete default configuration for Project Synapse.
# It defines the pipeline's baseline behavior and safe operational limits.

# --- Core Infrastructure & Database ---
PROGRESS_DB_NAME = 'progress.db'
WORKSPACE_DB_PATH = 'workspace.db' # Correct variable name
FINAL_DATASET_FILE = "dataset.jsonl"
API_URL = "https://codeforces.com/api/problemset.problems" # ADDED

# --- Worker Concurrency (Default Values & Limits) ---
# These are the primary "levers" the optimizer can adjust.
DEFAULT_INGESTION_WORKER_COUNT = 1
DEFAULT_ANALYSIS_WORKER_COUNT = 4
DEFAULT_IMPLEMENTATION_WORKER_COUNT = 4
DEFAULT_VJS_WORKER_COUNT = 2
DEFAULT_DATA_ASSEMBLY_WORKER_COUNT = 1

# Hard limits to prevent the optimizer from setting unsafe values.
MAX_VJS_WORKERS = 4 # Based on local hardware cores/memory
MAX_ANALYSIS_WORKERS = 8

# --- API & Batching Controls ---
DEFAULT_ANALYSIS_BATCH_SIZE = 5

# --- Resilience & Retry Logic ---
MAX_ANALYSIS_RETRIES = 3
MAX_IMPLEMENTATION_RETRIES = 5

# --- Scraper & Ingestion Timeouts (in seconds) ---
DEFAULT_SCRAPER_REQUEST_TIMEOUT = 40
DEFAULT_SELENIUM_LONG_WAIT = 120
DEFAULT_SELENIUM_SHORT_WAIT = 10

# --- VJS Timeouts (in seconds) ---
VJS_COMPILATION_TIMEOUT = 15

# -----------------------------------------------------------------------------
# --- Optimizer & Control System Configuration ---
# -----------------------------------------------------------------------------

# --- Optimizer Settings ---
# The frequency (in seconds) at which the optimizer runs its analysis loop.
OPTIMIZER_LOOP_DELAY_SECONDS = 60
# After making a change, the optimizer will wait this long (in seconds)
# before making another change to the same parameter, allowing the system to stabilize.
OPTIMIZER_COOLDOWN_PERIOD_SECONDS = 300 # 5 minutes

# --- PID Controller Setpoints ---
# The target number of tasks to maintain in a queue. This represents a healthy
# buffer, ensuring workers are not idle without creating excessive latency.
TARGET_VJS_QUEUE_SIZE = 20
TARGET_ANALYSIS_QUEUE_SIZE = 50
