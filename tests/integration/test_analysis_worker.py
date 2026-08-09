# tests/integration/test_analysis_worker.py
"""
Integration tests for analysis_worker.

Uses a real temporary SQLite DB and mocks the Gemini API call.
Verifies correct state transitions based on API response.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

import synapse.database as db
from synapse.workers.analysis import analysis_worker

pytestmark = pytest.mark.integration


MOCK_GEMINI_RESPONSE = {
    "final_pseudocode": {
        "2066B": "Read n integers, print their sum."
    },
    "analysis": {
        "oracle_ratings": {
            "oracle_0": {"rating": "Good"},
            "oracle_1": {"rating": "Fair"},
        }
    },
    "reasoning": {}
}


@pytest.fixture
def analysis_ready_problem(tmp_progress_db, tmp_workspace_db):
    """Problem in pending_analysis state with workspace data populated."""
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO problems
               (id, status, rating, analysis_try_count, rescraping_attempts)
               VALUES ('2066B', 'pending_analysis', 1500, 0, 0)"""
        )
        conn.commit()
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO problem_data_cache
               (problem_id, problem_statement_html, reference_solution_code,
                secondary_reference_codes_json, pretests_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "2066B",
                "<p>Sum array</p>",
                "#include<bits/stdc++.h>\nusing namespace std;\nint main(){long long s=0,n,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}",
                json.dumps(["#include<iostream>\nusing namespace std;\nint main(){int n,s=0,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}"]),
                json.dumps([{"input": "3\n1 2 3", "output": "6"}]),
            )
        )
        conn.commit()
    return {"id": "2066B"}


class TestAnalysisWorkerSuccess:

    @patch("synapse.workers.analysis.call_gemini_analyst_batch")
    def test_transitions_to_pending_implementation_on_success(
        self, mock_gemini, analysis_ready_problem, mock_gemini_km
    ):
        mock_gemini.return_value = (MOCK_GEMINI_RESPONSE, "raw_text")
        analysis_worker([analysis_ready_problem], "w1", mock_gemini_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "pending_implementation"

    @patch("synapse.workers.analysis.call_gemini_analyst_batch")
    def test_saves_pseudocode_to_workspace(
        self, mock_gemini, analysis_ready_problem, mock_gemini_km
    ):
        mock_gemini.return_value = (MOCK_GEMINI_RESPONSE, "raw_text")
        analysis_worker([analysis_ready_problem], "w1", mock_gemini_km)

        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            row = conn.execute(
                "SELECT arl_pseudocode FROM problem_data_cache WHERE problem_id='2066B'"
            ).fetchone()
        assert row is not None
        assert "sum" in row[0].lower()


class TestAnalysisWorkerFailure:

    @patch("synapse.workers.analysis.call_gemini_analyst_batch")
    def test_null_pseudocode_quarantines_problem(
        self, mock_gemini, analysis_ready_problem, mock_gemini_km
    ):
        null_response = {
            "final_pseudocode": {"2066B": None},
            "analysis": {},
            "reasoning": {"2066B": "Model could not understand the problem."}
        }
        mock_gemini.return_value = (null_response, "raw_text")
        analysis_worker([analysis_ready_problem], "w1", mock_gemini_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "quarantined"

    @patch("synapse.workers.analysis.call_gemini_analyst_batch")
    def test_api_exception_transitions_to_failed(
        self, mock_gemini, analysis_ready_problem, mock_gemini_km
    ):
        mock_gemini.side_effect = Exception("API timeout")
        analysis_worker([analysis_ready_problem], "w1", mock_gemini_km)

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        # transition_to_failed(id, 'analysis', ...) → 'failed_analysis'
        assert row[0] == "failed_analysis"

    @patch("synapse.workers.analysis.call_gemini_analyst_batch")
    def test_exceeded_max_retries_quarantines(
        self, mock_gemini, tmp_progress_db, tmp_workspace_db, mock_gemini_km
    ):
        from config import MAX_ANALYSIS_RETRIES
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                """INSERT INTO problems
                   (id, status, rating, analysis_try_count, rescraping_attempts)
                   VALUES ('2066B', 'pending_analysis', 1500, ?, 99)""",
                (MAX_ANALYSIS_RETRIES,)
            )
            conn.commit()
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.execute("INSERT INTO problem_data_cache (problem_id) VALUES ('2066B')")
            conn.commit()

        analysis_worker([{"id": "2066B"}], "w1", mock_gemini_km)
        mock_gemini.assert_not_called()

        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM problems WHERE id='2066B'"
            ).fetchone()
        assert row[0] == "quarantined"
