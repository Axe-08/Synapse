# tests/e2e/test_pipeline_smoke.py
"""
End-to-end smoke test: analysis → implementation pipeline.

Skipped automatically when:
- GEMINI_API_KEYS / GROQ_API_KEYS are not set in the environment
- Running in CI without real credentials

How to run manually:
    pytest tests/e2e/ -m e2e -s
"""
import json
import os
import pytest

pytestmark = pytest.mark.e2e

GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
GROQ_KEYS   = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]

skip_no_gemini = pytest.mark.skipif(not GEMINI_KEYS, reason="GEMINI_API_KEYS not set")
skip_no_groq   = pytest.mark.skipif(not GROQ_KEYS,   reason="GROQ_API_KEYS not set")

SIMPLE_HTML = """
<div class="problem-statement">
<p>You are given an array of <strong>n</strong> integers. Print their sum.</p>
<p><strong>Input:</strong> First line contains n. Second line contains n integers.</p>
<p><strong>Output:</strong> Print the sum.</p>
<p><strong>Constraints:</strong> 1 ≤ n ≤ 10^5, 1 ≤ a_i ≤ 10^9</p>
</div>
"""

ORACLE_CPP = (
    "#include<bits/stdc++.h>\n"
    "using namespace std;\n"
    "int main(){\n"
    "    long long s=0,n,x;\n"
    "    cin>>n;\n"
    "    while(n--){cin>>x;s+=x;}\n"
    "    cout<<s;\n"
    "}\n"
)


@skip_no_gemini
def test_analysis_worker_real_api(tmp_progress_db, tmp_workspace_db):
    """
    Calls the real Gemini API with a simple sum-array problem.
    Asserts that analysis_worker produces a non-null pseudocode and
    transitions the problem to pending_implementation.
    """
    import synapse.database as db
    from synapse.key_manager import KeyManager
    from synapse.workers.analysis import analysis_worker

    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO problems (id, status, rating, analysis_try_count, rescraping_attempts) "
            "VALUES ('E2E_TEST_001', 'pending_analysis', 800, 0, 0)"
        )
        conn.commit()
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO workspace (problem_id, problem_statement_html, "
            "reference_solution_code, secondary_reference_codes_json) "
            "VALUES (?, ?, ?, ?)",
            ("E2E_TEST_001", SIMPLE_HTML, ORACLE_CPP, "[]")
        )
        conn.commit()

    km = KeyManager(GEMINI_KEYS)
    analysis_worker([{"id": "E2E_TEST_001"}], "e2e_worker", km)

    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        row = conn.execute(
            "SELECT status FROM problems WHERE id='E2E_TEST_001'"
        ).fetchone()

    assert row[0] == "pending_implementation", (
        f"Expected pending_implementation but got {row[0]}. "
        "Check API key validity and quota."
    )

    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        row = conn.execute(
            "SELECT arl_pseudocode FROM workspace WHERE problem_id='E2E_TEST_001'"
        ).fetchone()
    assert row is not None and row[0], "Pseudocode should be non-empty after analysis."
    print(f"\n[E2E] Got pseudocode: {row[0][:200]}...")


@skip_no_groq
def test_implementation_worker_real_api(tmp_progress_db, tmp_workspace_db):
    """
    Calls the real Groq API with pre-set pseudocode.
    Asserts implementation_worker produces C++ code and transitions to pending_vjs.
    """
    import synapse.database as db
    from synapse.key_manager import KeyManager
    from synapse.workers.implementation import implementation_worker

    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO problems (id, status, rating, implementation_try_count) "
            "VALUES ('E2E_TEST_002', 'pending_implementation', 800, 0)"
        )
        conn.commit()
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO workspace (problem_id, problem_statement_html, arl_pseudocode) "
            "VALUES (?, ?, ?)",
            (
                "E2E_TEST_002",
                SIMPLE_HTML,
                "Read integer n. Read n integers into array. Print sum of all integers.",
            )
        )
        conn.commit()

    km = KeyManager(GROQ_KEYS)
    implementation_worker({"id": "E2E_TEST_002"}, "e2e_worker", km)

    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        row = conn.execute(
            "SELECT status FROM problems WHERE id='E2E_TEST_002'"
        ).fetchone()

    assert row[0] == "pending_vjs", (
        f"Expected pending_vjs but got {row[0]}. "
        "Check Groq API key validity."
    )

    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        row = conn.execute(
            "SELECT arl_reconstructed_code FROM workspace WHERE problem_id='E2E_TEST_002'"
        ).fetchone()
    assert row is not None and row[0], "Reconstructed C++ code should be non-empty."
    assert "#include" in row[0], "Should contain valid C++ code."
    print(f"\n[E2E] Got code snippet: {row[0][:300]}...")
