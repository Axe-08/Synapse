# synapse/database.py (The Dual-Database Librarian)
import sqlite3
from datetime import datetime
import logging
import json
from typing import List, Dict, Any, Optional

PROGRESS_DB_PATH = 'progress.db'
WORKSPACE_DB_PATH = 'workspace.db'

def _get_progress_db_connection():
    return sqlite3.connect(PROGRESS_DB_PATH, timeout=10)

def _get_workspace_db_connection():
    return sqlite3.connect(WORKSPACE_DB_PATH, timeout=10)

# --- Live Worker Monitoring (operates on progress.db) ---
def update_worker_status(worker_id: int, problem_id: Optional[str], stage: Optional[str], status: str):
    timestamp = datetime.now().isoformat()
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE live_workers SET problem_id = ?, stage = ?, status = ?, last_heartbeat = ? WHERE worker_id = ?",
            (problem_id, stage, status, timestamp, worker_id)
        )
        conn.commit()

def reset_all_workers_to_idle():
    logging.info("Resetting all worker statuses to 'idle'.")
    timestamp = datetime.now().isoformat()
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE live_workers SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?", (timestamp,))
        conn.commit()

# --- Pipeline Job Management (operates on progress.db) ---
def get_next_jobs(status: str, limit: int, min_rating: Optional[int] = None, max_rating: Optional[int] = None) -> List[Dict[str, Any]]:
    problems_to_process = []
    new_status = f"in_progress_{status.split('_')[-1]}"
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT id, rating FROM problems WHERE status = ? "
        params = [status]
        if min_rating is not None: query += " AND rating >= ?"; params.append(min_rating)
        if max_rating is not None: query += " AND rating <= ?"; params.append(max_rating)
        query += " ORDER BY rating ASC, id ASC LIMIT ?"
        params.append(limit)
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        if not rows: return []
        problem_ids = [row[0] for row in rows]
        problems_to_process = [{'id': row[0], 'rating': row[1]} for row in rows]
        timestamp = datetime.now().isoformat()
        update_query = f"UPDATE problems SET status = ?, last_updated = ? WHERE id IN ({','.join('?' for _ in problem_ids)})"
        cursor.execute(update_query, (new_status, timestamp, *problem_ids))
        conn.commit()
    logging.info(f"Locked {len(problems_to_process)} problems for stage '{status}'.")
    return problems_to_process

def update_problem_status_to_pending_arl(problem_id: str):
    timestamp = datetime.now().isoformat()
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE problems SET status = 'pending_arl', notes = NULL, last_updated = ? WHERE id = ?",
            (timestamp, problem_id)
        )
        conn.commit()

def update_problem_status_to_failed(problem_id: str, stage: str, notes: str):
    new_status = f"failed_{stage}"
    timestamp = datetime.now().isoformat()
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE problems SET status = ?, retry_count = retry_count + 1, notes = ?, last_updated = ? WHERE id = ?",
            (new_status, notes, timestamp, problem_id)
        )
        conn.commit()

# --- NEW: Workspace Data Management (operates on workspace.db) ---
def save_data_to_workspace(problem_id: str, html: str, ref_solution: dict, pretests: list):
    """Saves the large data blobs for a problem to the workspace cache."""
    ref_solution_json = json.dumps(ref_solution)
    pretests_json = json.dumps(pretests)
    with _get_workspace_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO problem_data_cache (problem_id, problem_statement_html, reference_solution_json, pretests_json) VALUES (?, ?, ?, ?)",
            (problem_id, html, ref_solution_json, pretests_json)
        )
        conn.commit()

def get_data_from_workspace(problem_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves all data for a problem from the workspace for ARL/VJS processing."""
    with _get_workspace_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_data_from_workspace(problem_id: str):
    """Purges a problem's temporary data after it has been successfully finalized."""
    with _get_workspace_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
        conn.commit()

def update_key_statuses(service: str, managed_keys: List['ManagedKey']):
    """Updates the status of all keys for a given service."""
    timestamp = datetime.now().isoformat()
    records = []
    for key in managed_keys:
        fingerprint = f"...{key.key_string[-4:]}"
        records.append((
            fingerprint,
            service,
            key.status.name,
            key.cooldown_until
        ))
    
    with _get_progress_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO key_status (key_fingerprint, service, status, cooldown_until) VALUES (?, ?, ?, ?)",
            records
        )
        conn.commit()

# We will implement update_workspace_with_arl_data later when we build the ARL worker.