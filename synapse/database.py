# synapse/database.py (Phase 4A - Refactored for Async Writes)
import sqlite3
from datetime import datetime
import logging
import json
from typing import List, Dict, Any, Optional

from synapse.database_writer import db_writer # Import the new writer service

PROGRESS_DB_PATH = 'progress.db'
WORKSPACE_DB_PATH = 'workspace.db'

# --- Connection Management (for READS and ATOMIC operations) ---
def _get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes a connection to a SQLite database, enabling WAL mode."""
    conn = sqlite3.connect(db_path, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# --- ASYNC WRITE Operations (progress.db) ---
# These functions enqueue their operations and do not block.

def update_worker_status(worker_id: int, pool: str, problem_id: Optional[str], stage: Optional[str], status: str):
    """(Async) Updates the live status of a single worker."""
    timestamp = datetime.now().isoformat()
    sql = "UPDATE live_workers SET problem_id = ?, stage = ?, status = ?, last_heartbeat = ? WHERE worker_id = ? AND pool = ?"
    params = (problem_id, stage, status, timestamp, worker_id, pool)
    db_writer.execute(sql, params)

def reset_all_workers_to_idle():
    """(Async) Resets all workers to idle at the start of a run."""
    logging.info("Resetting all worker statuses to 'idle'.")
    timestamp = datetime.now().isoformat()
    sql = "UPDATE live_workers SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?"
    db_writer.execute(sql, (timestamp,))

def _update_problem_status(problem_id: str, new_status: str, extra_updates: Optional[Dict[str, Any]] = None):
    """(Async) Generic internal function to update a problem's status and other fields."""
    timestamp = datetime.now().isoformat()
    base_query = "UPDATE problems SET status = ?, last_updated = ?"
    params = [new_status, timestamp]
    if extra_updates:
        for col, val in extra_updates.items():
            if col in ['analysis_try_count', 'implementation_try_count']:
                base_query += f", {col} = {col} + ?"
            else:
                base_query += f", {col} = ?"
            params.append(val)
    base_query += " WHERE id = ?"
    params.append(problem_id)
    db_writer.execute(base_query, tuple(params))

def save_process_history(problem_id: str, stage: str, event_type: str, details: str):
    """(Async) Logs a significant event in a problem's lifecycle."""
    timestamp = datetime.now().isoformat()
    sql = "INSERT INTO process_history (timestamp, problem_id, stage, event_type, details) VALUES (?, ?, ?, ?, ?)"
    params = (timestamp, problem_id, stage, event_type, details)
    db_writer.execute(sql, params)

def log_metric(worker_pool: str, event_type: str, duration_ms: Optional[int], success: bool, details: Optional[Dict] = None):
    """(Async) Logs a performance or event metric to the database."""
    timestamp = datetime.now().isoformat()
    details_json = json.dumps(details) if details else None
    sql = "INSERT INTO metrics (timestamp, worker_pool, event_type, duration_ms, success, details_json) VALUES (?, ?, ?, ?, ?, ?)"
    params = (timestamp, worker_pool, event_type, duration_ms, success, details_json)
    db_writer.execute(sql, params)

# --- SYNCHRONOUS Operations ---
# These functions block and interact with the DB directly.
# Used for reads or critical atomic read-then-write operations.

def get_next_jobs(status: str, limit: int) -> List[Dict[str, Any]]:
    """
    (Sync & Atomic) Fetches and locks the next available jobs for a given stage.
    This MUST remain synchronous to prevent race conditions.
    """
    new_status = f"in_progress_{status.split('_')[-1]}"
    # This operation is critical and must be atomic, so it uses a direct connection.
    with _get_db_connection(PROGRESS_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN;")
        try:
            cursor.execute(
                "SELECT id, rating FROM problems WHERE status = ? ORDER BY rating ASC, id ASC LIMIT ?",
                (status, limit)
            )
            rows = cursor.fetchall()
            if not rows:
                conn.commit()
                return []
            
            problem_ids = [row[0] for row in rows]
            jobs_to_process = [{'id': row[0], 'rating': row[1]} for row in rows]
            
            timestamp = datetime.now().isoformat()
            placeholders = ','.join('?' for _ in problem_ids)
            update_query = f"UPDATE problems SET status = ?, last_updated = ? WHERE id IN ({placeholders})"
            
            cursor.execute(update_query, (new_status, timestamp, *problem_ids))
            conn.commit()
            
            logging.info(f"Locked {len(jobs_to_process)} problems for stage '{status}'.")
            return jobs_to_process
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Failed to get next jobs atomically: {e}", exc_info=True)
            return []

def get_dynamic_config() -> Dict[str, Any]:
    """(Sync) Reads the entire dynamic configuration from the database."""
    try:
        with _get_db_connection(PROGRESS_DB_PATH) as conn:
            cursor = conn.execute("SELECT key, value FROM dynamic_config")
            rows = cursor.fetchall()
            config = {}
            for key, value in rows:
                try:
                    config[key] = int(value)
                except (ValueError, TypeError):
                    config[key] = value
            return config
    except sqlite3.Error as e:
        logging.error(f"Could not read dynamic_config, returning empty dict: {e}")
        return {}

# --- Problem State Transition Wrappers ---
# These functions provide a clean API for workers and internally call the async writers.

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
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP', f'Syntax/Compile error. Retrying. Report: {report[:500]}')

def transition_to_pending_analysis_retry(problem_id: str, report: str):
    _update_problem_status(problem_id, 'pending_analysis', {'last_vjs_report': report, 'implementation_try_count': 0})
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP', f'Logic/Test error. Retrying. Report: {report[:500]}')

def transition_to_pending_data_assembly(problem_id: str):
    _update_problem_status(problem_id, 'pending_data_assembly')
    save_process_history(problem_id, 'VJS', 'SUCCESS', 'All tests passed. Ready for final assembly.')

def transition_to_completed(problem_id: str):
    _update_problem_status(problem_id, 'completed')
    save_process_history(problem_id, 'DATA_ASSEMBLY', 'SUCCESS', 'Golden record created and saved.')

def transition_to_failed(problem_id: str, stage: str, notes: str):
    new_status = f"failed_{stage.lower()}"
    _update_problem_status(problem_id, new_status, {'notes': notes})
    save_process_history(problem_id, stage.upper(), 'FAILURE', f'Failed with error: {notes[:1000]}')

def transition_to_quarantined(problem_id: str, reason: str):
    new_status = "quarantined"
    _update_problem_status(problem_id, new_status, {'notes': reason})
    save_process_history(problem_id, 'SYSTEM', 'QUARANTINED', f'Quarantined due to: {reason}')

# --- Workspace Data Management (workspace.db) ---
# These are less contended and can remain synchronous for simplicity.

def save_ingestion_data_to_workspace(problem_id: str, html: str, ref_solution_obj: dict, ref_solution_code: str, pretests: list, time_limit_raw: str, memory_limit_raw: str):
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO problem_data_cache 
               (problem_id, problem_statement_html, reference_solution_json, reference_solution_code, pretests_json, time_limit_raw, memory_limit_raw) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (problem_id, html, json.dumps(ref_solution_obj), ref_solution_code, json.dumps(pretests), time_limit_raw, memory_limit_raw)
        )

def get_batch_data_from_workspace(problem_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ','.join('?' for _ in problem_ids)
        cursor = conn.execute(f"SELECT * FROM problem_data_cache WHERE problem_id IN ({placeholders})", problem_ids)
        rows = cursor.fetchall()
        return {row['problem_id']: dict(row) for row in rows} if rows else {}

def update_workspace_with_static_analysis(problem_id: str, analysis_json: str):
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("UPDATE problem_data_cache SET static_analysis_json = ? WHERE problem_id = ?", (analysis_json, problem_id))

def update_workspace_with_analysis_results(problem_id: str, pseudocode: str):
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("UPDATE problem_data_cache SET arl_pseudocode = ? WHERE problem_id = ?", (pseudocode, problem_id))

def update_workspace_with_implementation_results(problem_id: str, code: str):
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("UPDATE problem_data_cache SET arl_reconstructed_code = ? WHERE problem_id = ?", (code, problem_id))

def delete_data_from_workspace(problem_id: str):
    with _get_db_connection(WORKSPACE_DB_PATH) as conn:
        conn.execute("DELETE FROM problem_data_cache WHERE problem_id = ?", (problem_id,))
