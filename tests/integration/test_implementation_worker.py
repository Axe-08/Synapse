# tests/integration/test_implementation_worker.py
"""
Integration tests for implementation_worker.

Uses real temporary SQLite DB and mocks the Groq API call.
"""
import json
import pytest
from unittest.mock import patch

import synapse.database as db
from synapse.workers.implementation import implementation_worker

pytestmark = pytest.mark.integration

FAKE_CPP = "#include<bits/stdc++.h>\nusing namespace std;\nint main(){long long s=0,n,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}"


@pytest.fixture
def impl_ready_problem(tmp_progress_db, tmp_workspace_db):
    """Problem in pending_implementation with pseudocode in workspace."""
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO problems
               (id, status, rating, implementation_try_count)
               VALUES ('2066B', 'pending_implementation', 1500, 0)"""
        )
        conn.commit()
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO problem_data_cache
               (problem_id, problem_statement_html, arl_pseudocode)
               VALUES (?, ?, ?)""",
            ("2066B", "<p>Sum array</p>", "Read n integers, print their sum.")
        )
        conn.commit()
    return {"id": "2066B"}


class TestImplementationWorkerSuccess:

    @patch("synapse.workers.implementation.call_groq_implementer")
    def test_transitions_to_pending_vjs_on_success(
        self, mock_groq, impl_ready_problem, mock_groq_km
    ):
        mock_groq.return_value = FAKE_CPP
        implementation_worker(impl_ready_problem, "w1", mock_groq_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "pending_vjs"

    @patch("synapse.workers.implementation.call_groq_implementer")
    def test_saves_code_to_workspace(
        self, mock_groq, impl_ready_problem, mock_groq_km
    ):
        mock_groq.return_value = FAKE_CPP
        implementation_worker(impl_ready_problem, "w1", mock_groq_km)

        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            row = conn.execute(
                "SELECT arl_reconstructed_code FROM problem_data_cache WHERE problem_id='2066B'"
            ).fetchone()
        assert row is not None
        assert "#include" in row[0]


class TestImplementationWorkerFailure:

    @patch("synapse.workers.implementation.call_groq_implementer")
    def test_api_exception_transitions_to_failed(
        self, mock_groq, impl_ready_problem, mock_groq_km
    ):
        mock_groq.side_effect = Exception("Groq rate limit")
        implementation_worker(impl_ready_problem, "w1", mock_groq_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        # transition_to_failed(id, 'implementation', ...) → 'failed_implementation'
        assert row[0] == "failed_implementation"

    @patch("synapse.workers.implementation.call_groq_implementer")
    def test_max_retries_quarantines(
        self, mock_groq, tmp_progress_db, tmp_workspace_db, mock_groq_km
    ):
        from config import MAX_IMPLEMENTATION_RETRIES
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO problems
                   (id, status, rating, implementation_try_count)
                   VALUES ('2066B', 'pending_implementation', 1500, ?)""",
                (MAX_IMPLEMENTATION_RETRIES,)
            )
            conn.commit()
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problem_data_cache (problem_id, arl_pseudocode) VALUES ('2066B', 'pseudocode')"
            )
            conn.commit()

        implementation_worker({"id": "2066B"}, "w1", mock_groq_km)
        mock_groq.assert_not_called()

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "quarantined"

    @patch("synapse.workers.implementation.call_groq_implementer")
    def test_missing_pseudocode_transitions_to_failed(
        self, mock_groq, tmp_progress_db, tmp_workspace_db, mock_groq_km
    ):
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating) VALUES ('2066B', 'pending_implementation', 1500)"
            )
            conn.commit()
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problem_data_cache (problem_id) VALUES ('2066B')"
            )
            conn.commit()

        implementation_worker({"id": "2066B"}, "w1", mock_groq_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "failed_implementation"
