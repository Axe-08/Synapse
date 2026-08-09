# tests/unit/test_stats_monitor.py
"""
Unit tests for the stats monitor module.
"""
import pytest
from unittest.mock import MagicMock
from synapse.stats_monitor import (
    get_pipeline_stats,
    get_problem_class_distribution,
    get_dashboard_snapshot,
    log_snapshot_summary,
)


class TestPipelineStats:

    def test_returns_dict(self, tmp_progress_db):
        stats = get_pipeline_stats()
        assert isinstance(stats, dict)
        assert 'total' in stats

    def test_counts_problems(self, tmp_progress_db):
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating) VALUES (?, ?, ?)",
                ("1A", "pending_analysis", 1200),
            )
            conn.execute(
                "INSERT INTO problems (id, status, rating) VALUES (?, ?, ?)",
                ("2A", "completed", 1500),
            )
            conn.commit()
        stats = get_pipeline_stats()
        assert stats['pending_analysis'] == 1
        assert stats['completed'] == 1
        assert stats['total'] == 2


class TestClassDistribution:

    def test_returns_dict(self, tmp_progress_db):
        dist = get_problem_class_distribution()
        assert isinstance(dist, dict)

    def test_counts_classes(self, tmp_progress_db):
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating, problem_class) VALUES (?, ?, ?, ?)",
                ("1A", "pending_analysis", 1200, "interactive"),
            )
            conn.execute(
                "INSERT INTO problems (id, status, rating, problem_class) VALUES (?, ?, ?, ?)",
                ("2A", "pending_analysis", 1200, "standard"),
            )
            conn.execute(
                "INSERT INTO problems (id, status, rating, problem_class) VALUES (?, ?, ?, ?)",
                ("3A", "pending_analysis", 1200, "interactive"),
            )
            conn.commit()
        dist = get_problem_class_distribution()
        assert dist.get('interactive', 0) == 2
        assert dist.get('standard', 0) == 1


class TestDashboardSnapshot:

    def test_snapshot_structure(self, tmp_progress_db):
        snapshot = get_dashboard_snapshot()
        assert 'timestamp' in snapshot
        assert 'pipeline' in snapshot
        assert 'classes' in snapshot
        assert 'api_budget' in snapshot

    def test_snapshot_with_km(self, tmp_progress_db):
        km = MagicMock()
        km.get_budget_status.return_value = {'rpd_utilization': 0.5}
        snapshot = get_dashboard_snapshot(km_gemini=km)
        assert 'gemini' in snapshot['api_budget']

    def test_snapshot_with_am(self, tmp_progress_db):
        am = MagicMock()
        am.has_healthy_account.return_value = True
        am.get_all_stats.return_value = [{'handle': 'user1'}]
        snapshot = get_dashboard_snapshot(account_manager=am)
        assert snapshot['scraper']['healthy'] is True

    def test_snapshot_with_optimizer(self, tmp_progress_db):
        opt = MagicMock()
        opt.active_mode = "burst"
        snapshot = get_dashboard_snapshot(optimizer=opt)
        assert snapshot['optimizer']['mode'] == "burst"

    def test_log_summary_no_crash(self, tmp_progress_db, caplog):
        snapshot = get_dashboard_snapshot()
        log_snapshot_summary(snapshot)  # Should not raise
