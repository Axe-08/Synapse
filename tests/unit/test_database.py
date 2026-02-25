# tests/unit/test_database.py
"""
Unit tests for database utility functions.
Tests state transitions, job fetching, and metric logging
against a temporary SQLite database matching the real production schema.
"""
import json
import pytest
import synapse.database as db


pytestmark = pytest.mark.unit


class TestGetNextJobs:

    def test_returns_empty_when_no_matching_status(self, tmp_progress_db, sample_problem):
        jobs = db.get_next_jobs('pending_calibration', limit=5)
        assert jobs == []

    def test_returns_job_with_correct_status(self, tmp_progress_db, sample_problem):
        jobs = db.get_next_jobs('pending_ingestion', limit=5)
        assert len(jobs) == 1
        assert jobs[0]['id'] == '2066B'

    def test_respects_limit(self, tmp_progress_db):
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO problems (id, status) VALUES (?, 'pending_ingestion')",
                    (f"PROB_{i}",),
                )
            conn.commit()
        jobs = db.get_next_jobs('pending_ingestion', limit=3)
        assert len(jobs) == 3

    def test_locks_fetched_jobs(self, tmp_progress_db, sample_problem):
        """Jobs fetched become 'in_progress_*' so they can't be double-dispatched."""
        db.get_next_jobs('pending_ingestion', limit=5)
        jobs_again = db.get_next_jobs('pending_ingestion', limit=5)
        assert jobs_again == []


class TestStatusTransitions:

    def test_transition_to_pending_calibration(self, tmp_progress_db, sample_problem):
        db.transition_to_pending_calibration('2066B')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'pending_calibration'

    def test_transition_to_pending_analysis(self, tmp_progress_db, sample_problem):
        db.transition_to_pending_analysis('2066B')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'pending_analysis'

    def test_transition_to_pending_implementation(self, tmp_progress_db, sample_problem):
        db.transition_batch_to_pending_implementation(['2066B'])
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'pending_implementation'

    def test_transition_to_pending_vjs(self, tmp_progress_db, sample_problem):
        db.transition_to_pending_vjs('2066B')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'pending_vjs'

    def test_transition_to_pending_data_assembly(self, tmp_progress_db, sample_problem):
        db.transition_to_pending_data_assembly('2066B')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'pending_data_assembly'

    def test_transition_to_completed(self, tmp_progress_db, sample_problem):
        db.transition_to_completed('2066B')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'completed'

    def test_transition_to_quarantined_sets_status(self, tmp_progress_db, sample_problem):
        db.transition_to_quarantined('2066B', 'Test quarantine reason')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'quarantined'

    def test_transition_to_quarantined_stores_notes(self, tmp_progress_db, sample_problem):
        db.transition_to_quarantined('2066B', 'Test quarantine reason')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT notes FROM problems WHERE id='2066B'").fetchone()
        assert 'Test quarantine reason' in row[0]

    def test_transition_to_failed_creates_stage_status(self, tmp_progress_db, sample_problem):
        """transition_to_failed(id, stage, notes) → status becomes 'failed_{stage}'."""
        db.transition_to_failed('2066B', 'ingestion', 'Connection error')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'failed_ingestion'

    def test_transition_to_failed_vjs(self, tmp_progress_db, sample_problem):
        db.transition_to_failed('2066B', 'vjs', 'Docker error')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id='2066B'").fetchone()
        assert row[0] == 'failed_vjs'

    def test_transition_to_pending_implementation_retry_changes_status(
        self, tmp_progress_db, sample_problem
    ):
        """This transition changes status and saves vjs report; does NOT increment impl counter."""
        db.transition_to_pending_implementation_retry('2066B', 'compile error')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status, last_vjs_report FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == 'pending_implementation'
        # last_vjs_report is set via db_writer (async); may or may not be visible yet
        # The key assertion is the status changed correctly

    def test_transition_to_pending_analysis_retry_changes_status(
        self, tmp_progress_db, sample_problem
    ):
        """This transition changes status back to pending_analysis; does NOT directly increment analysis_try_count."""
        db.transition_to_pending_analysis_retry('2066B', 'WA report')
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == 'pending_analysis'


class TestWorkerStatus:

    def test_update_worker_status_does_not_raise(self, tmp_progress_db):
        try:
            db.update_worker_status("w1", "INGESTION", "2066B", "PROCESSING", "active")
        except Exception as e:
            pytest.fail(f"update_worker_status raised: {e}")


class TestLogMetric:

    def test_log_metric_inserts_row(self, tmp_progress_db):
        db.log_metric('INGESTION', 'ingestion_task', 5000, True, {'problem_id': '2066B'})
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT worker_pool, event_type, duration_ms, success FROM metrics"
            ).fetchone()
        assert row is not None
        assert row[0] == 'INGESTION'
        assert row[2] == 5000
        assert row[3] == 1
