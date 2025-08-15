# synapse/database.py (Definitive Phase 1 Version)
import sqlite3
from datetime import datetime
import logging
import json
from typing import List, Dict, Any, Optional

PROGRESS_DB_PATH = 'progress.db'
WORKSPACE_DB_PATH = 'workspace.db'

# --- Connection Management ---
def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes a connection to a SQLite database, enabling WAL mode."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- Worker & Job Management (progress.db) ---
def update_worker_status(worker_id: int, pool: str, problem_id: Optional[str], stage: Optional[str], status: str):
    """Updates the live status of a single worker."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        conn.execute(
            "UPDATE live_workers SET problem_id = ?, stage = ?, status = ?, last_heartbeat = ? WHERE worker_id = ? AND pool = ?",
            (problem_id, stage, status, timestamp, worker_id, pool)
        )

def reset_all_workers_to_idle():
    """Resets all workers to idle at the start of a run."""
    logging.info("Resetting all worker statuses to 'idle'.")
    timestamp = datetime.now().isoformat()
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        conn.execute("UPDATE live_workers SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?", (timestamp,))

def get_next_jobs(status: str, limit: int) -> List[Dict[str, Any]]:
    """
    Atomically fetches and locks the next available jobs for a given stage.
    Supports fetching single jobs (limit=1) or batches (limit > 1).
    """
    new_status = f"in_progress_{status.split('_')[-1]}"
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, rating FROM problems WHERE status = ? ORDER BY rating ASC, id ASC LIMIT ?",
            (status, limit)
        )
        rows = cursor.fetchall()
        if not rows:
            return []
        
        problem_ids = [row[0] for row in rows]
        jobs_to_process = [{'id': row[0], 'rating': row[1]} for row in rows]
        
        timestamp = datetime.now().isoformat()
        placeholders = ','.join('?' for _ in problem_ids)
        update_query = f"UPDATE problems SET status = ?, last_updated = ? WHERE id IN ({placeholders})"
        
        conn.execute(update_query, (new_status, timestamp, *problem_ids))
    
    logging.info(f"Locked {len(jobs_to_process)} problems for stage '{status}'.")
    return jobs_to_process

# --- Problem State Transitions (progress.db) ---
def _update_problem_status(problem_id: str, new_status: str, extra_updates: Optional[Dict[str, Any]] = None):
    """Generic internal function to update a problem's status and other fields."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        base_query = "UPDATE problems SET status = ?, last_updated = ?"
        params = [new_status, timestamp]
        
        if extra_updates:
            # Note: This is a safe way to build dynamic queries for a known set of columns.
            # It is not vulnerable to SQL injection as the column names are not from user input.
            for col, val in extra_updates.items():
                if col in ['analysis_try_count', 'implementation_try_count']:
                    # Special handling for incremental updates
                    base_query += f", {col} = {col} + ?"
                else:
                    base_query += f", {col} = ?"
                params.append(val)
        
        base_query += " WHERE id = ?"
        params.append(problem_id)
        
        conn.execute(base_query, tuple(params))

def transition_to_pending_analysis(problem_id: str):
    _update_problem_status(problem_id, 'pending_analysis')
    save_process_history(problem_id, 'INGESTION', 'SUCCESS', 'Data ingested. Ready for analysis.')

def transition_batch_to_pending_implementation(problem_ids: List[str]):
    for pid in problem_ids:
        _update_problem_status(pid, 'pending_implementation', {'analysis_try_count': 1})
        save_process_history(pid, 'ANALYSIS', 'SUCCESS', 'Pseudocode generated. Ready for implementation.')

def transition_to_pending_vjs(problem_id: str):
    _update_problem_status(problem_id, 'pending_vjs', {'implementation_try_count': 1})
    save_process_history(problem_id, 'IMPLEMENTATION', 'SUCCESS', 'Code generated. Ready for VJS.')
    
def transition_to_pending_implementation_retry(problem_id: str, report: str):
    _update_problem_status(problem_id, 'pending_implementation', {'last_vjs_report': report})
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP', f'Syntax/Compile error. Retrying implementation. Report: {report}')

def transition_to_pending_analysis_retry(problem_id: str, report: str):
    _update_problem_status(problem_id, 'pending_analysis', {'last_vjs_report': report, 'implementation_try_count': 0})
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP', f'Logic/Test error. Retrying analysis. Report: {report}')

def transition_to_pending_data_assembly(problem_id: str):
    _update_problem_status(problem_id, 'pending_data_assembly')
    save_process_history(problem_id, 'VJS', 'SUCCESS', 'All tests passed. Ready for final assembly.')

def transition_to_completed(problem_id: str):
    _update_problem_status(problem_id, 'completed')
    save_process_history(problem_id, 'DATA_ASSEMBLY', 'SUCCESS', 'Golden record created and saved.')

def transition_to_failed(problem_id: str, stage: str, notes: str):
    new_status = f"failed_{stage.lower()}"
    _update_problem_status(problem_id, new_status, {'notes': notes})
    save_process_history(problem_id, stage.upper(), 'FAILURE', f'Failed with error: {notes}')

# --- Process History Logging (progress.db) ---
def save_process_history(problem_id: str, stage: str, event_type: str, details: str):
    """Logs a significant event in a problem's lifecycle."""
    timestamp = datetime.now().isoformat()
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO process_history (timestamp, problem_id, stage, event_type, details) VALUES (?, ?, ?, ?, ?)",
            (timestamp, problem_id, stage, event_type, details)
        )

# --- Workspace Data Management (workspace.db) ---
def save_ingestion_data_to_workspace(problem_id: str, html: str, ref_solution_obj: dict, ref_solution_code: str, pretests: list):
    """Saves the initial data blobs from ingestion."""
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO problem_data_cache 
               (problem_id, problem_statement_html, reference_solution_json, reference_solution_code, pretests_json) 
               VALUES (?, ?, ?, ?, ?)""",
            (problem_id, html, json.dumps(ref_solution_obj), ref_solution_code, json.dumps(pretests))
        )

def get_batch_data_from_workspace(problem_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Retrieves all data for a batch of problems from the workspace."""
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ','.join('?' for _ in problem_ids)
        cursor = conn.execute(f"SELECT * FROM problem_data_cache WHERE problem_id IN ({placeholders})", problem_ids)
        rows = cursor.fetchall()
        return {row['problem_id']: dict(row) for row in rows} if rows else {}

def update_workspace_with_analysis_results(problem_id: str, pseudocode: str):
    """Updates a workspace record with the generated pseudocode."""
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("UPDATE problem_data_cache SET arl_pseudocode = ? WHERE problem_id = ?", (pseudocode, problem_id))

def update_workspace_with_implementation_results(problem_id: str, code: str):
    """Updates a workspace record with the generated C++ code."""
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("UPDATE problem_data_cache SET arl_reconstructed_code = ? WHERE problem_id = ?", (code, problem_id))

def delete_data_from_workspace(problem_id: str):
    """Purges a problem's temporary data after it has been successfully finalized."""
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("DELETE FROM problem_data_cache WHERE problem_id = ?", (problem_id,))