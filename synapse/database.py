# synapse/database.py (The Live-Monitoring Librarian)
import sqlite3
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional

DB_PATH = 'progress.db'

def _get_db_connection():
    """Establishes a connection to the database."""
    return sqlite3.connect(DB_PATH, timeout=10)

# --- Worker Status Management (for Live Monitoring) ---

def update_worker_status(worker_id: int, problem_id: Optional[str], stage: Optional[str], status: str):
    """
    Updates the status of a specific worker on the 'live_workers' table.
    This is the core function for our live dashboard.
    """
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE live_workers
        SET problem_id = ?, stage = ?, status = ?, last_heartbeat = ?
        WHERE worker_id = ?
        """, (problem_id, stage, status, timestamp, worker_id))
        conn.commit()

def reset_all_workers_to_idle():
    """
    Resets all workers to 'idle' at the start of a new batch run.
    This cleans up any stale states from a previous crash.
    """
    logging.info("Resetting all worker statuses to 'idle' for a new run.")
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE live_workers
        SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?
        """, (timestamp,))
        conn.commit()

# --- Problem Progress Management ---

def get_next_pending_problems(limit: int, min_rating: Optional[int] = None, max_rating: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Atomically fetches the next batch of 'pending' problems and marks them as 'in_progress'.
    """
    problems_to_process = []
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT id, rating FROM problems WHERE status = 'pending'"
        params = []
        if min_rating is not None: query += " AND rating >= ?"; params.append(min_rating)
        if max_rating is not None: query += " AND rating <= ?"; params.append(max_rating)
        query += " ORDER BY rating ASC, id ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        if not rows:
            logging.info("No pending problems found matching the criteria.")
            return []

        problem_ids = [row[0] for row in rows]
        problems_to_process = [{'id': row[0], 'rating': row[1]} for row in rows]
        
        timestamp = datetime.now().isoformat()
        update_query = f"UPDATE problems SET status = 'in_progress', last_updated = ? WHERE id IN ({','.join('?' for _ in problem_ids)})"
        cursor.execute(update_query, (timestamp, *problem_ids))
        conn.commit()
        
        logging.info(f"Locked {len(problems_to_process)} problems for processing.")
    return problems_to_process

def get_problems_by_ids(problem_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches a specific list of problems by their IDs for manual runs.
    """
    problems_to_process = []
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT id, rating FROM problems WHERE id IN ({','.join('?' for _ in problem_ids)})"
        cursor.execute(query, tuple(problem_ids))
        rows = cursor.fetchall()
        id_map = {row[0]: {'id': row[0], 'rating': row[1]} for row in rows}
        for pid in problem_ids:
            if pid in id_map: problems_to_process.append(id_map[pid])
            else: logging.warning(f"Problem ID '{pid}' not found in the database.")
    logging.info(f"Fetched {len(problems_to_process)} problems for manual processing run.")
    return problems_to_process

def update_problem_on_success(problem_id: str, pretest_count: int):
    """Updates a problem's status to 'completed' after a successful run."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE problems SET status = 'completed', pretest_count = ?, notes = NULL, last_updated = ? WHERE id = ?", (pretest_count, timestamp, problem_id))
        conn.commit()

def update_problem_on_failure(problem_id: str, notes: str):
    """Updates a problem's status to 'failed' and increments the retry counter."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE problems SET status = 'failed', retry_count = retry_count + 1, notes = ?, last_updated = ? WHERE id = ?", (notes, timestamp, problem_id))
        conn.commit()