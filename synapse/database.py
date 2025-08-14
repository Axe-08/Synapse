# synapse/database.py (The Stage-Centric Librarian)
import sqlite3
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional

DB_PATH = 'progress.db'

def _get_db_connection():
    """Establishes a connection to the database."""
    return sqlite3.connect(DB_PATH, timeout=10)

# --- Live Worker Monitoring ---

def update_worker_status(worker_id: int, problem_id: Optional[str], stage: Optional[str], status: str):
    """Updates the status of a specific worker on the 'live_workers' table."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE live_workers SET problem_id = ?, stage = ?, status = ?, last_heartbeat = ? WHERE worker_id = ?",
            (problem_id, stage, status, timestamp, worker_id)
        )
        conn.commit()

def reset_all_workers_to_idle():
    """Resets all workers to 'idle' at the start of a new run."""
    logging.info("Resetting all worker statuses to 'idle'.")
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE live_workers SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?", (timestamp,))
        conn.commit()

# --- Pipeline Job Management ---

def get_next_jobs(status: str, limit: int, min_rating: Optional[int] = None, max_rating: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Atomically fetches the next batch of problems for a given status 
    and marks them as 'in_progress_[stage]'.
    """
    problems_to_process = []
    new_status = f"in_progress_{status.split('_')[-1]}" # e.g., pending_ingestion -> in_progress_ingestion
    
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT id, rating FROM problems WHERE status = ? "
        params = [status]
        
        if min_rating is not None: query += " AND rating >= ?"; params.append(min_rating)
        if max_rating is not None: query += " AND rating <= ?"; params.append(max_rating)
        query += " ORDER BY rating ASC, id ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        if not rows:
            return []

        problem_ids = [row[0] for row in rows]
        problems_to_process = [{'id': row[0], 'rating': row[1]} for row in rows]
        
        timestamp = datetime.now().isoformat()
        update_query = f"UPDATE problems SET status = ?, last_updated = ? WHERE id IN ({','.join('?' for _ in problem_ids)})"
        cursor.execute(update_query, (new_status, timestamp, *problem_ids))
        conn.commit()
        
        logging.info(f"Locked {len(problems_to_process)} problems for stage '{status}'.")
    return problems_to_process

def update_problem_status_to_pending_arl(problem_id: str, pretest_count: int):
    """On ingestion success, moves a problem to the next stage in the pipeline."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE problems SET status = 'pending_arl', pretest_count = ?, notes = NULL, last_updated = ? WHERE id = ?",
            (pretest_count, timestamp, problem_id)
        )
        conn.commit()

def update_problem_status_to_failed(problem_id: str, stage: str, notes: str):
    """Updates a problem's status to 'failed_[stage]' and increments the retry counter."""
    new_status = f"failed_{stage}"
    timestamp = datetime.now().isoformat()
    with _get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE problems SET status = ?, retry_count = retry_count + 1, notes = ?, last_updated = ? WHERE id = ?",
            (new_status, notes, timestamp, problem_id)
        )
        conn.commit()

# We will add more update functions like `update_problem_status_to_pending_vjs` later.