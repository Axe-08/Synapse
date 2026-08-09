# tests/unit/test_cf_submission.py
"""
Unit tests for the CF submission worker utility functions.
Tests verdict parsing, submission ID extraction, and rejection handling.
"""
import pytest
from unittest.mock import patch, MagicMock

from synapse.workers.cf_submission import (
    _extract_verdict_from_page,
    _extract_submission_id,
    _handle_rejection,
)


class TestExtractVerdict:

    def test_accepted(self):
        html = '<span class="verdict-accepted">Accepted</span>'
        assert _extract_verdict_from_page(html) == 'ACCEPTED'

    def test_wrong_answer(self):
        html = '<td>Wrong answer</td> on test 3'
        assert _extract_verdict_from_page(html) == 'WRONG_ANSWER'

    def test_tle(self):
        html = '<span>Time limit exceeded</span>'
        assert _extract_verdict_from_page(html) == 'TIME_LIMIT_EXCEEDED'

    def test_mle(self):
        html = '<td>Memory limit exceeded</td>'
        assert _extract_verdict_from_page(html) == 'MEMORY_LIMIT_EXCEEDED'

    def test_runtime_error(self):
        html = '<span>Runtime error</span> on test 1'
        assert _extract_verdict_from_page(html) == 'RUNTIME_ERROR'

    def test_compilation_error(self):
        html = '<div>Compilation error</div>'
        assert _extract_verdict_from_page(html) == 'COMPILATION_ERROR'

    def test_testing(self):
        html = '<span class="verdict-waiting">Testing</span>'
        assert _extract_verdict_from_page(html) == 'TESTING'

    def test_in_queue(self):
        html = '<span>In queue</span>'
        assert _extract_verdict_from_page(html) == 'TESTING'

    def test_unknown_returns_none(self):
        html = '<div>Some random page content</div>'
        assert _extract_verdict_from_page(html) is None

    def test_idleness(self):
        html = '<td>Idleness limit exceeded</td>'
        assert _extract_verdict_from_page(html) == 'IDLENESS_LIMIT_EXCEEDED'


class TestExtractSubmissionId:

    def test_valid_id(self):
        html = '<a href="/contest/1234/submission/56789">56789</a>'
        assert _extract_submission_id(html) == '56789'

    def test_no_id(self):
        html = '<div>No submission here</div>'
        assert _extract_submission_id(html) is None

    def test_multiple_ids_returns_first(self):
        html = '<a href="/submission/111">#1</a> <a href="/submission/222">#2</a>'
        assert _extract_submission_id(html) == '111'


class TestHandleRejection:

    def test_retry_when_under_limit(self, tmp_progress_db):
        """Should re-queue for implementation if under retry limit."""
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating, implementation_try_count) "
                "VALUES (?, ?, ?, ?)",
                ("100A", "in_progress_cf_submission", 1200, 1),
            )
            conn.commit()

        _handle_rejection("100A", "WRONG_ANSWER", "12345")

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id = ?", ("100A",)).fetchone()
        assert row[0] == "pending_implementation"

    def test_quarantine_when_exhausted(self, tmp_progress_db):
        """Should quarantine if retries exhausted."""
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating, implementation_try_count) "
                "VALUES (?, ?, ?, ?)",
                ("100B", "in_progress_cf_submission", 1200, 5),
            )
            conn.commit()

        _handle_rejection("100B", "WRONG_ANSWER", "12346")

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id = ?", ("100B",)).fetchone()
        assert row[0] == "quarantined"
