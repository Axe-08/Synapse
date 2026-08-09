# synapse/stats_monitor.py
"""
Unified stats monitor for the Synapse V2 pipeline.

Aggregates metrics from:
- Pipeline queue depths (from progress.db)
- API budget status (from KeyManagers)
- Scraper health (from AccountManager)
- Optimizer state (from PipelineOptimizer)

Provides get_dashboard_snapshot() for API endpoints and logging.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

import synapse.database as db


def get_pipeline_stats() -> Dict[str, int]:
    """Get job counts per status from the progress database."""
    stats = {}
    statuses = [
        'pending_ingestion', 'in_progress_ingestion',
        'pending_analysis', 'in_progress_analysis',
        'pending_implementation', 'in_progress_implementation',
        'pending_vjs', 'in_progress_vjs',
        'pending_cf_submission', 'in_progress_cf_submission',
        'pending_data_assembly', 'in_progress_data_assembly',
        'completed', 'quarantined',
    ]
    try:
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            for status in statuses:
                if db.USE_POSTGRES:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM problems WHERE status = %s", (status,))
                    stats[status] = cur.fetchone()[0]
                else:
                    row = conn.execute(
                        "SELECT COUNT(*) FROM problems WHERE status = ?", (status,)
                    ).fetchone()
                    stats[status] = row[0] if row else 0

            # Also get total
            if db.USE_POSTGRES:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM problems")
                stats['total'] = cur.fetchone()[0]
            else:
                row = conn.execute("SELECT COUNT(*) FROM problems").fetchone()
                stats['total'] = row[0] if row else 0

    except Exception as e:
        logging.error(f"Stats monitor: failed to read pipeline stats: {e}")
    return stats


def get_problem_class_distribution() -> Dict[str, int]:
    """Get count of problems by problem_class."""
    dist = {}
    try:
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            if db.USE_POSTGRES:
                cur = conn.cursor()
                cur.execute(
                    "SELECT problem_class, COUNT(*) FROM problems GROUP BY problem_class"
                )
                for row in cur.fetchall():
                    dist[row[0] or 'standard'] = row[1]
            else:
                for row in conn.execute(
                    "SELECT problem_class, COUNT(*) FROM problems GROUP BY problem_class"
                ).fetchall():
                    dist[row[0] or 'standard'] = row[1]
    except Exception as e:
        logging.error(f"Stats monitor: failed to read class distribution: {e}")
    return dist


def get_recent_metrics(limit: int = 50) -> list:
    """Get the most recent metric entries."""
    metrics = []
    try:
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            if db.USE_POSTGRES:
                cur = conn.cursor()
                cur.execute(
                    "SELECT worker_pool, event_type, value, success, timestamp "
                    "FROM metrics ORDER BY timestamp DESC LIMIT %s",
                    (limit,)
                )
                for row in cur.fetchall():
                    metrics.append({
                        'worker_pool': row[0], 'event_type': row[1],
                        'value': row[2], 'success': bool(row[3]),
                        'timestamp': row[4],
                    })
            else:
                for row in conn.execute(
                    "SELECT worker_pool, event_type, value, success, timestamp "
                    "FROM metrics ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall():
                    metrics.append({
                        'worker_pool': row[0], 'event_type': row[1],
                        'value': row[2], 'success': bool(row[3]),
                        'timestamp': row[4],
                    })
    except Exception as e:
        logging.error(f"Stats monitor: failed to read metrics: {e}")
    return metrics


def get_dashboard_snapshot(
    km_gemini=None,
    km_groq=None,
    account_manager=None,
    optimizer=None,
) -> Dict[str, Any]:
    """
    Build a complete dashboard snapshot aggregating all subsystems.

    Args:
        km_gemini: Optional Gemini KeyManager.
        km_groq: Optional Groq KeyManager.
        account_manager: Optional AccountManager.
        optimizer: Optional PipelineOptimizer.

    Returns:
        Dict with keys: pipeline, classes, api_budget, scraper, optimizer, timestamp.
    """
    snapshot = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'pipeline': get_pipeline_stats(),
        'classes': get_problem_class_distribution(),
        'api_budget': {},
        'scraper': {},
        'optimizer': {},
    }

    if km_gemini:
        try:
            snapshot['api_budget']['gemini'] = km_gemini.get_budget_status()
        except Exception:
            pass

    if km_groq:
        try:
            snapshot['api_budget']['groq'] = km_groq.get_budget_status()
        except Exception:
            pass

    if account_manager:
        try:
            snapshot['scraper'] = {
                'healthy': account_manager.has_healthy_account(),
                'accounts': account_manager.get_all_stats(),
            }
        except Exception:
            pass

    if optimizer:
        try:
            snapshot['optimizer'] = {
                'mode': optimizer.active_mode,
            }
        except Exception:
            pass

    return snapshot


def log_snapshot_summary(snapshot: Dict[str, Any]) -> None:
    """Log a compact one-line summary of the dashboard snapshot."""
    p = snapshot.get('pipeline', {})
    total = p.get('total', 0)
    completed = p.get('completed', 0)
    quarantined = p.get('quarantined', 0)
    pending = sum(v for k, v in p.items() if k.startswith('pending_'))
    in_progress = sum(v for k, v in p.items() if k.startswith('in_progress_'))

    mode = snapshot.get('optimizer', {}).get('mode', 'unknown')
    scraper_healthy = snapshot.get('scraper', {}).get('healthy', '?')

    logging.info(
        f"DASHBOARD | total={total} done={completed} quarantined={quarantined} "
        f"pending={pending} active={in_progress} | mode={mode} scraper={scraper_healthy}"
    )
