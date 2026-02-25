# synapse/database.py
"""
Data Access Layer (DAL) for Project Synapse — supports SQLite (dev/test) and
PostgreSQL (production on DGX).

Backend is selected by the DATABASE_URL environment variable:
  - DATABASE_URL set → psycopg2 / PostgreSQL
  - DATABASE_URL absent → sqlite3 / SQLite (WAL mode)

API is identical from the caller's perspective. The only internal difference
is placeholder style (? vs %s) and connection management.

Async writes (db_writer):
  Most state-change functions enqueue SQL via the background DatabaseWriter
  thread, which serialises writes and prevents contention.

Synchronous atomic operations:
  get_next_jobs() is always synchronous and uses BEGIN/UPDATE/COMMIT to
  atomically claim a batch of jobs, preventing double-dispatch.
"""
import logging
import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional

from synapse.database_writer import db_writer

# ── Connection parameters ───────────────────────────────────────────────────
_DATABASE_URL = os.getenv('DATABASE_URL', '')
USE_POSTGRES = bool(_DATABASE_URL)

# SQLite paths (used when DATABASE_URL is not set)
PROGRESS_DB_PATH: str = 'progress.db'
WORKSPACE_DB_PATH: str = 'workspace.db'

# Logical DB name → PostgreSQL schema name
_PG_SCHEMAS = {
    PROGRESS_DB_PATH:  'progress',
    WORKSPACE_DB_PATH: 'workspace',
}


def _pg_schema(db_path: str) -> str:
    return _PG_SCHEMAS.get(db_path, 'progress')


# ── Connection factory ──────────────────────────────────────────────────────

@contextmanager
def _get_db_connection(db_path: str):
    """
    Context manager that returns a ready-to-use database connection.
    Handles both SQLite and PostgreSQL transparently.
    Commits on clean exit, rolls back on exception.
    """
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(_DATABASE_URL,
                                options=f"-c search_path={_pg_schema(db_path)},public")
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _ph(n: int = 1) -> str:
    """Return n comma-separated placeholders for the current backend."""
    ph = '%s' if USE_POSTGRES else '?'
    return ', '.join([ph] * n)


def _adapt_sql(sql: str) -> str:
    """Convert SQLite-style ? placeholders to %s for PostgreSQL."""
    if USE_POSTGRES:
        return sql.replace('?', '%s')
    return sql


# ── Async write helpers ─────────────────────────────────────────────────────

def _async_execute(sql: str, params: tuple = ()) -> None:
    """Enqueue a write via the background DatabaseWriter thread."""
    db_writer.execute(_adapt_sql(sql), params)


# ── Async write operations ──────────────────────────────────────────────────

def update_worker_status(
    worker_id: str, pool: str, problem_id: Optional[str],
    stage: Optional[str], status: str
) -> None:
    """(Async) Updates the live status of a single worker row."""
    timestamp = datetime.now().isoformat()
    sql = ("UPDATE live_workers SET problem_id = ?, stage = ?, status = ?, "
           "last_heartbeat = ? WHERE worker_id = ? AND pool = ?")
    _async_execute(sql, (problem_id, stage, timestamp, worker_id, pool, timestamp))


def reset_all_workers_to_idle() -> None:
    """(Async) Resets all worker rows to 'idle'."""
    logging.info("Resetting all worker statuses to 'idle'.")
    timestamp = datetime.now().isoformat()
    _async_execute(
        "UPDATE live_workers SET problem_id = NULL, stage = NULL, status = 'idle', last_heartbeat = ?",
        (timestamp,)
    )


def _update_problem_status(
    problem_id: str, new_status: str,
    extra_updates: Optional[Dict[str, Any]] = None
) -> None:
    """(Async) Updates a problem's status and optional extra fields."""
    timestamp = datetime.now().isoformat()
    base_query = "UPDATE problems SET status = ?, last_updated = ?"
    params: list = [new_status, timestamp]

    # Columns that use += semantics (increment, not set)
    INCREMENT_COLS = {'analysis_try_count', 'implementation_try_count',
                      'rescraping_attempts', 'priority'}

    if extra_updates:
        for col, val in extra_updates.items():
            if col in INCREMENT_COLS:
                base_query += f", {col} = {col} + ?"
            else:
                base_query += f", {col} = ?"
            params.append(val)

    base_query += " WHERE id = ?"
    params.append(problem_id)
    _async_execute(base_query, tuple(params))


def save_process_history(
    problem_id: str, stage: str, event_type: str, details: str
) -> None:
    """(Async) Logs a lifecycle event to process_history."""
    timestamp = datetime.now().isoformat()
    sql = ("INSERT INTO process_history "
           "(timestamp, problem_id, stage, event_type, details) "
           "VALUES (?, ?, ?, ?, ?)")
    _async_execute(sql, (timestamp, problem_id, stage, event_type, details))


def log_metric(
    worker_pool: str, event_type: str, duration_ms: Optional[int],
    success: bool, details: Optional[Dict] = None
) -> None:
    """(Async) Logs a performance metric to the metrics table."""
    timestamp = datetime.now().isoformat()
    details_json = json.dumps(details) if details else None
    sql = ("INSERT INTO metrics "
           "(timestamp, worker_pool, event_type, duration_ms, success, details_json) "
           "VALUES (?, ?, ?, ?, ?, ?)")
    _async_execute(sql, (timestamp, worker_pool, event_type, duration_ms, success, details_json))


# ── Atomic synchronous operations ──────────────────────────────────────────

def get_next_jobs(status: str, limit: int) -> List[Dict[str, Any]]:
    """
    (Sync & Atomic) Fetches and locks the next available jobs for a stage.
    Jobs are returned ordered by priority DESC, rating ASC so that retried
    problems bubble to the front of the queue.
    """
    in_progress_status = f"in_progress_{status.split('_')[-1]}"
    timestamp = datetime.now().isoformat()
    max_retries = 5

    for attempt in range(max_retries):
        try:
            with _get_db_connection(PROGRESS_DB_PATH) as conn:
                if USE_POSTGRES:
                    import psycopg2
                    cur = conn.cursor()
                    # Use FOR UPDATE SKIP LOCKED for PostgreSQL — eliminates waits
                    cur.execute(
                        "SELECT id, rating FROM problems "
                        "WHERE status = %s "
                        "ORDER BY priority DESC, rating ASC "
                        "LIMIT %s FOR UPDATE SKIP LOCKED",
                        (status, limit)
                    )
                    rows = cur.fetchall()
                    if not rows:
                        return []
                    problem_ids = [r[0] for r in rows]
                    jobs = [{'id': r[0], 'rating': r[1]} for r in rows]
                    cur.execute(
                        "UPDATE problems SET status = %s, last_updated = %s "
                        "WHERE id = ANY(%s)",
                        (in_progress_status, timestamp, problem_ids)
                    )
                    conn.commit()
                else:
                    import sqlite3
                    cursor = conn.cursor()
                    cursor.execute("BEGIN;")
                    cursor.execute(
                        "SELECT id, rating FROM problems "
                        "WHERE status = ? "
                        "ORDER BY priority DESC, rating ASC LIMIT ?",
                        (status, limit)
                    )
                    rows = cursor.fetchall()
                    if not rows:
                        conn.commit()
                        return []
                    problem_ids = [r[0] for r in rows]
                    jobs = [{'id': r[0], 'rating': r[1]} for r in rows]
                    placeholders = ','.join('?' for _ in problem_ids)
                    cursor.execute(
                        f"UPDATE problems SET status = ?, last_updated = ? WHERE id IN ({placeholders})",
                        (in_progress_status, timestamp, *problem_ids)
                    )
                    conn.commit()

                logging.info(f"Locked {len(jobs)} problems for stage '{status}'.")
                return jobs

        except Exception as e:
            err_str = str(e)
            if ("database is locked" in err_str or "deadlock" in err_str.lower()) \
                    and attempt < max_retries - 1:
                import time
                logging.warning(f"DB contention on attempt {attempt+1}/{max_retries}. Retrying...")
                time.sleep(0.5)
                continue
            logging.error(f"Failed to get next jobs: {e}", exc_info=True)
            return []
    return []


# ── Problem state transitions ───────────────────────────────────────────────

def transition_to_pending_analysis(problem_id: str) -> None:
    _update_problem_status(problem_id, 'pending_analysis')
    save_process_history(problem_id, 'INGESTION', 'SUCCESS', 'Data ingested. Ready for analysis.')


def transition_to_pending_calibration(problem_id: str) -> None:
    _update_problem_status(problem_id, 'pending_calibration')
    save_process_history(problem_id, 'INGESTION', 'SUCCESS',
                         'Multi-oracle data ingested. Ready for calibration.')


def transition_batch_to_pending_implementation(problem_ids: List[str]) -> None:
    for pid in problem_ids:
        _update_problem_status(pid, 'pending_implementation', {'analysis_try_count': 1})
        save_process_history(pid, 'ANALYSIS', 'SUCCESS',
                             'Pseudocode generated. Ready for implementation.')


def transition_to_pending_vjs(problem_id: str) -> None:
    _update_problem_status(problem_id, 'pending_vjs', {'implementation_try_count': 1})
    save_process_history(problem_id, 'IMPLEMENTATION', 'SUCCESS',
                         'Code generated. Ready for VJS.')


def transition_to_pending_implementation_retry(problem_id: str, report: str) -> None:
    _update_problem_status(problem_id, 'pending_implementation',
                           {'last_vjs_report': report, 'priority': 1})
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP',
                         f'Syntax/Compile error. Retrying. Report: {report[:500]}')


def transition_to_pending_analysis_retry(problem_id: str, report: str) -> None:
    _update_problem_status(problem_id, 'pending_analysis',
                           {'last_vjs_report': report, 'implementation_try_count': 0,
                            'priority': 1})
    save_process_history(problem_id, 'VJS', 'RETRY_LOOP',
                         f'Logic/Test error. Retrying. Report: {report[:500]}')


def transition_to_pending_data_assembly(problem_id: str) -> None:
    _update_problem_status(problem_id, 'pending_data_assembly')
    save_process_history(problem_id, 'VJS', 'SUCCESS', 'All tests passed. Ready for final assembly.')


def transition_to_completed(problem_id: str) -> None:
    _update_problem_status(problem_id, 'completed')
    save_process_history(problem_id, 'DATA_ASSEMBLY', 'SUCCESS', 'Golden record created and saved.')


def transition_to_failed(problem_id: str, stage: str, notes: str) -> None:
    _update_problem_status(problem_id, f"failed_{stage.lower()}", {'notes': notes})
    save_process_history(problem_id, stage.upper(), 'FAILURE',
                         f'Failed with error: {notes[:1000]}')


def transition_to_quarantined(problem_id: str, reason: str) -> None:
    _update_problem_status(problem_id, 'quarantined', {'notes': reason})
    save_process_history(problem_id, 'SYSTEM', 'QUARANTINED',
                         f'Quarantined due to: {reason}')


# ── Workspace read/write operations ────────────────────────────────────────

def save_calibration_results(
    problem_id: str, successful_oracles: int,
    compiled_paths: list, validated_pretests: list,
    slowness_factor: float, checker_mode: str
) -> None:
    """Saves calibration stage output to workspace (sync) and progress (async)."""
    if USE_POSTGRES:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE problem_data_cache
                   SET compiled_oracle_paths_json = %s, validated_pretests_json = %s,
                       slowness_factor = %s, checker_mode = %s
                   WHERE problem_id = %s""",
                (json.dumps(compiled_paths), json.dumps(validated_pretests),
                 slowness_factor, checker_mode, problem_id)
            )
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.execute(
                """UPDATE problem_data_cache
                   SET compiled_oracle_paths_json = ?, validated_pretests_json = ?,
                       slowness_factor = ?, checker_mode = ?
                   WHERE problem_id = ?""",
                (json.dumps(compiled_paths), json.dumps(validated_pretests),
                 slowness_factor, checker_mode, problem_id)
            )
    sql = "UPDATE problems SET successful_oracles = ?, confidence_level = 1 WHERE id = ?"
    _async_execute(sql, (successful_oracles, problem_id))


def save_ingested_data(problem_id: str, data: Dict[str, Any]) -> None:
    """(Sync) Saves all scraped data to the workspace cache."""
    ph = '%s' if USE_POSTGRES else '?'
    sql = f"""INSERT INTO problem_data_cache
               (problem_id, problem_statement_html, reference_solution_json,
                reference_solution_code, secondary_reference_codes_json,
                pretests_json, time_limit_raw, memory_limit_raw)
             VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})"""
    params = (
        problem_id,
        data.get('problem_statement_html'),
        data.get('reference_solution_json'),
        data.get('reference_solution_code'),
        data.get('secondary_reference_codes_json', '[]'),
        data.get('pretests_json', '[]'),
        data.get('time_limit_raw'),
        data.get('memory_limit_raw'),
    )
    if USE_POSTGRES:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                sql + " ON CONFLICT (problem_id) DO UPDATE SET "
                "problem_statement_html = EXCLUDED.problem_statement_html, "
                "reference_solution_json = EXCLUDED.reference_solution_json, "
                "reference_solution_code = EXCLUDED.reference_solution_code, "
                "secondary_reference_codes_json = EXCLUDED.secondary_reference_codes_json, "
                "pretests_json = EXCLUDED.pretests_json, "
                "time_limit_raw = EXCLUDED.time_limit_raw, "
                "memory_limit_raw = EXCLUDED.memory_limit_raw",
                params
            )
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.execute(
                sql.replace(
                    "INSERT INTO", "INSERT OR REPLACE INTO"
                ),
                params
            )


def save_analysis_results(
    problem_id: str, pseudocode: str, analysis_json: str
) -> None:
    """(Sync) Saves analysis results to workspace."""
    ph = '%s' if USE_POSTGRES else '?'
    if USE_POSTGRES:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.cursor().execute(
                f"UPDATE problem_data_cache SET arl_pseudocode = {ph}, quality_analysis_json = {ph} WHERE problem_id = {ph}",
                (pseudocode, analysis_json, problem_id)
            )
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.execute(
                "UPDATE problem_data_cache SET arl_pseudocode = ?, quality_analysis_json = ? WHERE problem_id = ?",
                (pseudocode, analysis_json, problem_id)
            )


def save_implementation_result(problem_id: str, code: str) -> None:
    """(Sync) Saves generated code to workspace."""
    if USE_POSTGRES:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.cursor().execute(
                "UPDATE problem_data_cache SET arl_reconstructed_code = %s WHERE problem_id = %s",
                (code, problem_id)
            )
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.execute(
                "UPDATE problem_data_cache SET arl_reconstructed_code = ? WHERE problem_id = ?",
                (code, problem_id)
            )


def get_batch_data_from_workspace(
    problem_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """(Sync) Fetches workspace rows for a batch of problem IDs."""
    if not problem_ids:
        return {}

    if USE_POSTGRES:
        import psycopg2.extras
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                "SELECT * FROM problem_data_cache WHERE problem_id = ANY(%s)",
                (problem_ids,)
            )
            rows = cur.fetchall()
            return {row['problem_id']: dict(row) for row in rows}
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in problem_ids)
            cursor = conn.execute(
                f"SELECT * FROM problem_data_cache WHERE problem_id IN ({placeholders})",
                problem_ids
            )
            rows = cursor.fetchall()
            return {row['problem_id']: dict(row) for row in rows}


def get_workspace_data(problem_id: str) -> Optional[Dict[str, Any]]:
    """(Sync) Fetches the workspace row for a single problem."""
    result = get_batch_data_from_workspace([problem_id])
    return result.get(problem_id)


def cleanup_workspace(problem_id: str) -> None:
    """(Sync) Deletes the workspace row after final assembly."""
    if USE_POSTGRES:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.cursor().execute(
                "DELETE FROM problem_data_cache WHERE problem_id = %s",
                (problem_id,)
            )
    else:
        with _get_db_connection(WORKSPACE_DB_PATH) as conn:
            conn.execute(
                "DELETE FROM problem_data_cache WHERE problem_id = ?",
                (problem_id,)
            )

# ── Backward-compatibility aliases used by worker modules ───────────────────
def update_workspace_with_analysis_results(
    problem_id: str, pseudocode: str, analysis_json: str
) -> None:
    save_analysis_results(problem_id, pseudocode, analysis_json)


def update_workspace_with_implementation_results(
    problem_id: str, code: str
) -> None:
    save_implementation_result(problem_id, code)
