# create_database.py
"""
Initializes the project's databases (SQLite or PostgreSQL).

Usage:
  python create_database.py            # SQLite (progress.db + workspace.db)
  python create_database.py --postgres # PostgreSQL via DATABASE_URL
"""
import argparse
import logging
import os
import time
from datetime import datetime

import requests

from config import (
    DEFAULT_INGESTION_WORKER_COUNT, DEFAULT_ANALYSIS_WORKER_COUNT,
    DEFAULT_IMPLEMENTATION_WORKER_COUNT, DEFAULT_VJS_WORKER_COUNT,
    DEFAULT_CF_SUBMISSION_WORKER_COUNT, DEFAULT_DATA_ASSEMBLY_WORKER_COUNT,
    DEFAULT_ANALYSIS_BATCH_SIZE, DEFAULT_SCRAPER_DELAY_SECONDS,
    PROGRESS_DB_NAME, WORKSPACE_DB_PATH, API_URL,
    MAX_INGESTION_WORKERS, MAX_ANALYSIS_WORKERS,
    MAX_IMPLEMENTATION_WORKERS, MAX_VJS_WORKERS,
    MAX_CF_SUBMISSION_WORKERS, MAX_DATA_ASSEMBLY_WORKERS,
    MAX_FUZZ_GENERATOR_WORKERS, DEFAULT_FUZZ_GENERATOR_WORKER_COUNT,
    DEFAULT_FUZZ_BATCH_SIZE
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_DATABASE_URL = os.getenv('DATABASE_URL', '')

# ── Progress schema ──────────────────────────────────────────────────────────

PROGRESS_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    contest_id INTEGER NOT NULL DEFAULT 0,
    problem_index TEXT NOT NULL DEFAULT 'A',
    name TEXT NOT NULL DEFAULT '',
    rating INTEGER DEFAULT 0,
    tags TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_ingestion',
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    analysis_try_count INTEGER DEFAULT 0,
    implementation_try_count INTEGER DEFAULT 0,
    rescraping_attempts INTEGER DEFAULT 0,
    tried_submission_ids TEXT,
    reference_submissions_json TEXT,
    successful_oracles INTEGER DEFAULT 0,
    confidence_level INTEGER DEFAULT 0,
    problem_class TEXT NOT NULL DEFAULT 'standard',
    submission_account TEXT,
    last_vjs_report TEXT,
    notes TEXT,
    last_updated TEXT NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS live_workers (
    worker_id TEXT PRIMARY KEY,
    pool TEXT NOT NULL,
    problem_id TEXT,
    stage TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TEXT NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS key_status (
    key_fingerprint TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    cooldown_until REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS process_history (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT now(),
    problem_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT now(),
    worker_pool TEXT NOT NULL,
    event_type TEXT NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS dynamic_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    last_updated TEXT NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scraper_stats (
    id SERIAL PRIMARY KEY,
    account TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT now(),
    event_type TEXT NOT NULL,
    details_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS dgx_usage_stats (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT now(),
    hour INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    cpu_percent REAL,
    ram_percent REAL,
    our_active_workers INTEGER,
    queue_depth INTEGER
);
"""

WORKSPACE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS problem_data_cache (
    problem_id TEXT PRIMARY KEY,
    problem_statement_html TEXT,
    reference_solution_json TEXT,
    reference_solution_code TEXT,
    secondary_reference_codes_json TEXT DEFAULT '[]',
    compiled_oracle_paths_json TEXT DEFAULT '[]',
    pretests_json TEXT DEFAULT '[]',
    validated_pretests_json TEXT DEFAULT '[]',
    slowness_factor REAL DEFAULT 3.0,
    checker_mode TEXT DEFAULT 'strict',
    arl_pseudocode TEXT,
    arl_reconstructed_code TEXT,
    arl_feedback TEXT,
    vjs_last_report TEXT,
    quality_analysis_json TEXT DEFAULT '{}',
    time_limit_raw TEXT DEFAULT '2 seconds',
    memory_limit_raw TEXT DEFAULT '256 megabytes',
    input_generator_py TEXT,
    generated_tests_json TEXT DEFAULT '[]'
);
"""

# ── SQLite-compatible variants (default() → literals, SERIAL → AUTOINCREMENT)
SQLITE_PROGRESS_TABLES_SQL = PROGRESS_TABLES_SQL \
    .replace("DEFAULT now()", "DEFAULT (datetime('now'))") \
    .replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT") \
    .replace("BOOLEAN NOT NULL DEFAULT FALSE", "INTEGER NOT NULL DEFAULT 0")

SQLITE_WORKSPACE_TABLES_SQL = WORKSPACE_TABLES_SQL


# ── PostgreSQL setup ─────────────────────────────────────────────────────────

def _pg_setup(database_url: str) -> None:
    import psycopg2

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Create schemas
    cur.execute("CREATE SCHEMA IF NOT EXISTS progress;")
    cur.execute("CREATE SCHEMA IF NOT EXISTS workspace;")

    # Progress tables
    cur.execute("SET search_path TO progress;")
    cur.execute(PROGRESS_TABLES_SQL)
    logging.info("PostgreSQL progress schema created.")

    # Add priority column if upgrading from old schema
    cur.execute("""
        ALTER TABLE progress.problems
        ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0;
    """)

    # Workspace tables
    cur.execute("SET search_path TO workspace;")
    cur.execute(WORKSPACE_TABLES_SQL)
    logging.info("PostgreSQL workspace schema created.")

    conn.close()


def _pg_populate_problems(database_url: str) -> bool:
    """Fetches problems from CF API and inserts them into PostgreSQL."""
    import psycopg2
    import psycopg2.extras

    logging.info("Fetching problem list from Codeforces API...")
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.critical(f"Failed to fetch from CF API: {e}")
        return False

    if data.get('status') != 'OK':
        logging.critical(f"CF API error: {data.get('comment')}")
        return False

    problems = data['result']['problems']
    rows = []
    now = datetime.now().isoformat()
    for p in problems:
        if 'rating' not in p:
            continue
        pid = f"{p['contestId']}{p['index']}"
        tags = ", ".join(p.get('tags', []))
        rows.append((pid, p['contestId'], p['index'], p['name'], p['rating'], tags, now))

    conn = psycopg2.connect(database_url, options="-c search_path=progress")
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO problems (id, contest_id, problem_index, name, rating, tags, last_updated)
                   VALUES %s ON CONFLICT (id) DO NOTHING""",
                rows
            )
        conn.commit()
        logging.info(f"Inserted {len(rows)} problems into PostgreSQL.")
        return True
    except Exception as e:
        conn.rollback()
        logging.error(f"Failed to insert problems: {e}")
        return False
    finally:
        conn.close()


def _pg_init_workers(database_url: str) -> None:
    import psycopg2
    now = datetime.now().isoformat()
    pools = {
        'INGESTION': MAX_INGESTION_WORKERS,
        'ANALYSIS': MAX_ANALYSIS_WORKERS,
        'FUZZ_GENERATOR': MAX_FUZZ_GENERATOR_WORKERS,
        'IMPLEMENTATION': MAX_IMPLEMENTATION_WORKERS,
        'VJS': MAX_VJS_WORKERS,
        'CF_SUBMISSION': MAX_CF_SUBMISSION_WORKERS,
        'DATA_ASSEMBLY': MAX_DATA_ASSEMBLY_WORKERS,
    }
    workers = []
    for pool, count in pools.items():
        for i in range(1, count + 1):
            workers.append((f"{pool}-{i}", pool, 'idle', now))

    conn = psycopg2.connect(database_url, options="-c search_path=progress")
    conn.autocommit = False
    with conn.cursor() as cur:
        for wid, pool, status, ts in workers:
            cur.execute(
                """INSERT INTO live_workers (worker_id, pool, status, last_heartbeat)
                   VALUES (%s, %s, %s, %s) ON CONFLICT (worker_id) DO NOTHING""",
                (wid, pool, status, ts)
            )
    conn.commit()
    conn.close()
    logging.info("Worker slots initialized in PostgreSQL.")


def _pg_init_dynamic_config(database_url: str) -> None:
    import psycopg2
    now = datetime.now().isoformat()
    configs = [
        ('ingestion_worker_count', str(DEFAULT_INGESTION_WORKER_COUNT), now),
        ('analysis_worker_count', str(DEFAULT_ANALYSIS_WORKER_COUNT), now),
        ('fuzz_generator_worker_count', str(DEFAULT_FUZZ_GENERATOR_WORKER_COUNT), now),
        ('implementation_worker_count', str(DEFAULT_IMPLEMENTATION_WORKER_COUNT), now),
        ('vjs_worker_count', str(DEFAULT_VJS_WORKER_COUNT), now),
        ('cf_submission_worker_count', str(DEFAULT_CF_SUBMISSION_WORKER_COUNT), now),
        ('data_assembly_worker_count', str(DEFAULT_DATA_ASSEMBLY_WORKER_COUNT), now),
        ('analysis_batch_size', str(DEFAULT_ANALYSIS_BATCH_SIZE), now),
        ('fuzz_batch_size', str(DEFAULT_FUZZ_BATCH_SIZE), now),
        ('scraper_delay_seconds', str(DEFAULT_SCRAPER_DELAY_SECONDS), now),
    ]
    conn = psycopg2.connect(database_url, options="-c search_path=progress")
    conn.autocommit = False
    with conn.cursor() as cur:
        for key, val, ts in configs:
            cur.execute(
                """INSERT INTO dynamic_config (key, value, last_updated)
                   VALUES (%s, %s, %s) ON CONFLICT (key) DO NOTHING""",
                (key, val, ts)
            )
    conn.commit()
    conn.close()
    logging.info("Default dynamic config inserted into PostgreSQL.")


# ── SQLite setup ─────────────────────────────────────────────────────────────

def _sqlite_setup() -> None:
    import sqlite3

    for db_name in [PROGRESS_DB_NAME, WORKSPACE_DB_PATH]:
        if os.path.exists(db_name):
            resp = input(f"'{db_name}' already exists. Delete and recreate? (y/n): ").lower()
            if resp != 'y':
                logging.info("Cancelled.")
                return
            os.remove(db_name)

    with sqlite3.connect(PROGRESS_DB_NAME) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SQLITE_PROGRESS_TABLES_SQL)
        _sqlite_populate_problems(conn.cursor())
        _sqlite_init_workers(conn.cursor())
        _sqlite_init_dynamic_config(conn.cursor())
        conn.commit()
    logging.info(f"'{PROGRESS_DB_NAME}' setup complete.")

    with sqlite3.connect(WORKSPACE_DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(SQLITE_WORKSPACE_TABLES_SQL)
        conn.commit()
    logging.info(f"'{WORKSPACE_DB_PATH}' setup complete.")


def _sqlite_populate_problems(cursor) -> bool:
    import sqlite3
    logging.info("Fetching problem list from Codeforces API...")
    try:
        resp = requests.get(API_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.critical(f"Failed to fetch from CF API: {e}")
        return False
    now = datetime.now().isoformat()
    rows = []
    for p in data['result']['problems']:
        if 'rating' not in p:
            continue
        pid = f"{p['contestId']}{p['index']}"
        rows.append((pid, p['contestId'], p['index'], p['name'],
                     p['rating'], ", ".join(p.get('tags', [])), now))
    try:
        cursor.executemany(
            "INSERT OR IGNORE INTO problems (id, contest_id, problem_index, name, rating, tags, last_updated) VALUES (?,?,?,?,?,?,?)",
            rows
        )
        logging.info(f"Inserted {cursor.rowcount} problems.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Failed to bulk insert: {e}")
        return False


def _sqlite_init_workers(cursor) -> None:
    now = datetime.now().isoformat()
    pools = {
        'INGESTION': MAX_INGESTION_WORKERS, 'ANALYSIS': MAX_ANALYSIS_WORKERS,
        'FUZZ_GENERATOR': MAX_FUZZ_GENERATOR_WORKERS,
        'IMPLEMENTATION': MAX_IMPLEMENTATION_WORKERS, 'VJS': MAX_VJS_WORKERS,
        'CF_SUBMISSION': MAX_CF_SUBMISSION_WORKERS, 'DATA_ASSEMBLY': MAX_DATA_ASSEMBLY_WORKERS,
    }
    workers = [(f"{p}-{i}", p, 'idle', now)
               for p, n in pools.items() for i in range(1, n + 1)]
    cursor.executemany(
        "INSERT OR REPLACE INTO live_workers (worker_id, pool, status, last_heartbeat) VALUES (?,?,?,?)",
        workers
    )
    logging.info("Worker slots initialized.")


def _sqlite_init_dynamic_config(cursor) -> None:
    now = datetime.now().isoformat()
    configs = [
        ('ingestion_worker_count', str(DEFAULT_INGESTION_WORKER_COUNT), now),
        ('analysis_worker_count', str(DEFAULT_ANALYSIS_WORKER_COUNT), now),
        ('fuzz_generator_worker_count', str(DEFAULT_FUZZ_GENERATOR_WORKER_COUNT), now),
        ('implementation_worker_count', str(DEFAULT_IMPLEMENTATION_WORKER_COUNT), now),
        ('vjs_worker_count', str(DEFAULT_VJS_WORKER_COUNT), now),
        ('cf_submission_worker_count', str(DEFAULT_CF_SUBMISSION_WORKER_COUNT), now),
        ('data_assembly_worker_count', str(DEFAULT_DATA_ASSEMBLY_WORKER_COUNT), now),
        ('analysis_batch_size', str(DEFAULT_ANALYSIS_BATCH_SIZE), now),
        ('fuzz_batch_size', str(DEFAULT_FUZZ_BATCH_SIZE), now),
        ('scraper_delay_seconds', str(DEFAULT_SCRAPER_DELAY_SECONDS), now),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO dynamic_config (key, value, last_updated) VALUES (?,?,?)",
        configs
    )
    logging.info("Default dynamic config set.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Synapse databases.")
    parser.add_argument('--postgres', action='store_true',
                        help='Initialize PostgreSQL (requires DATABASE_URL env var)')
    args = parser.parse_args()

    if args.postgres:
        url = _DATABASE_URL
        if not url:
            logging.critical("DATABASE_URL not set. Cannot initialize PostgreSQL.")
            return
        logging.info(f"Setting up PostgreSQL at {url.split('@')[-1]}...")
        _pg_setup(url)
        if _pg_populate_problems(url):
            _pg_init_workers(url)
            _pg_init_dynamic_config(url)
            logging.info("PostgreSQL setup complete.")
        else:
            logging.error("Problem population failed. Setup incomplete.")
    else:
        _sqlite_setup()


if __name__ == "__main__":
    main()