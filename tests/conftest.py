# tests/conftest.py
"""
Shared pytest fixtures for all test levels.
"""
import json
import os
import sqlite3
import time
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

PROGRESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    contest_id INTEGER NOT NULL DEFAULT 0,
    problem_index TEXT NOT NULL DEFAULT 'A',
    name TEXT NOT NULL DEFAULT 'Test Problem',
    rating INTEGER DEFAULT 0,
    tags TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_ingestion',
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    analysis_try_count INTEGER DEFAULT 0,
    implementation_try_count INTEGER DEFAULT 0,
    rescraping_attempts INTEGER DEFAULT 0,
    tried_submission_ids TEXT DEFAULT '',
    reference_submissions_json TEXT,
    successful_oracles INTEGER DEFAULT 0,
    confidence_level INTEGER DEFAULT 0,
    last_vjs_report TEXT,
    notes TEXT,
    last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS live_workers (
    worker_id TEXT PRIMARY KEY,
    pool TEXT NOT NULL,
    problem_id TEXT,
    stage TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS key_status (
    key_fingerprint TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    cooldown_until REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS process_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    problem_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    worker_pool TEXT NOT NULL,
    event_type TEXT NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL,
    details_json TEXT
);
CREATE TABLE IF NOT EXISTS dynamic_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

WORKSPACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS problem_data_cache (
    problem_id TEXT PRIMARY KEY,
    problem_statement_html TEXT,
    pretests_json TEXT DEFAULT '[]',
    validated_pretests_json TEXT DEFAULT '[]',
    reference_solution_code TEXT,
    secondary_reference_codes_json TEXT DEFAULT '[]',
    reference_solution_json TEXT DEFAULT '{}',
    arl_pseudocode TEXT,
    arl_reconstructed_code TEXT,
    quality_analysis_json TEXT DEFAULT '{}',
    compiled_oracle_paths_json TEXT DEFAULT '[]',
    slowness_factor REAL DEFAULT 3.0,
    checker_mode TEXT DEFAULT 'strict',
    time_limit_raw TEXT DEFAULT '2 seconds',
    memory_limit_raw TEXT DEFAULT '256 megabytes',
    vjs_last_report TEXT,
    last_vjs_report TEXT,
    oracle_count INTEGER DEFAULT 0
);
"""


def _create_db(path: str, schema: str):
    conn = sqlite3.connect(path)
    conn.executescript(schema)
    conn.commit()
    conn.close()


@pytest.fixture
def tmp_progress_db(tmp_path, monkeypatch):
    """Temporary progress.db with correct schema, monkeypatched into synapse.database."""
    db_path = str(tmp_path / "progress.db")
    _create_db(db_path, PROGRESS_SCHEMA)

    import synapse.database as db
    monkeypatch.setattr(db, "PROGRESS_DB_PATH", db_path)
    # Also patch the db_writer to write synchronously to the same path
    _patch_db_writer(db, db_path, monkeypatch)
    return db_path


@pytest.fixture
def tmp_workspace_db(tmp_path, monkeypatch):
    """Temporary workspace.db with correct schema, monkeypatched into synapse.database."""
    db_path = str(tmp_path / "workspace.db")
    _create_db(db_path, WORKSPACE_SCHEMA)

    import synapse.database as db
    monkeypatch.setattr(db, "WORKSPACE_DB_PATH", db_path)
    return db_path


def _patch_db_writer(db_module, progress_db_path: str, monkeypatch):
    """
    Replace the async db_writer with a synchronous wrapper so that
    committed writes are immediately visible in test assertions.
    """
    import synapse.database as db

    class SyncWriter:
        def execute(self, sql: str, params: tuple = ()):
            conn = sqlite3.connect(progress_db_path)
            try:
                conn.execute(sql, params)
                conn.commit()
            finally:
                conn.close()

        def start(self): pass
        def stop(self): pass

    monkeypatch.setattr(db, "db_writer", SyncWriter())


# ---------------------------------------------------------------------------
# Problem fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_problem(tmp_progress_db):
    """Insert a sample problem in pending_ingestion state."""
    import synapse.database as db
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO problems (id, status, rating) VALUES (?, ?, ?)",
            ("2066B", "pending_ingestion", 1500),
        )
        conn.commit()
    return {"id": "2066B", "rating": 1500}


@pytest.fixture
def sample_workspace_problem(tmp_progress_db, tmp_workspace_db, sample_problem):
    """Problem with workspace data ready for calibration."""
    import synapse.database as db
    pretests = [{"input": "3\n1 2 3", "output": "6"}]
    with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
        conn.execute(
            """INSERT INTO problem_data_cache (
                problem_id, problem_statement_html, pretests_json,
                validated_pretests_json, reference_solution_code,
                secondary_reference_codes_json, time_limit_raw,
                memory_limit_raw, arl_pseudocode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "2066B", "<p>Sum array</p>",
                json.dumps(pretests), json.dumps(pretests),
                "#include<bits/stdc++.h>\nusing namespace std;\nint main(){long long s=0,n,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}",
                json.dumps(["#include<iostream>\nusing namespace std;\nint main(){int n,s=0,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}"]),
                "2 seconds", "256 megabytes",
                "Read n integers and print their sum.",
            ),
        )
        conn.commit()
    with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
        conn.execute("UPDATE problems SET status='pending_calibration' WHERE id='2066B'")
        conn.commit()
    return sample_problem


# ---------------------------------------------------------------------------
# Mock KeyManager fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_gemini_km():
    """A KeyManager mock that always returns a fake key object."""
    key = MagicMock()
    key.key = "fake-gemini-api-key"
    key.api_key = "fake-gemini-api-key"
    key.__str__ = lambda s: "fake-gemini-api-key"

    km = MagicMock()
    km.get_key.return_value = key
    return km


@pytest.fixture
def mock_groq_km():
    """A KeyManager mock that always returns a fake key object."""
    key = MagicMock()
    key.key = "fake-groq-api-key"
    key.api_key = "fake-groq-api-key"
    key.__str__ = lambda s: "fake-groq-api-key"

    km = MagicMock()
    km.get_key.return_value = key
    return km
