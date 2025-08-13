import sqlite3
from datetime import datetime

DB_PATH = 'progress.db'

def get_problem_status(problem_id :str)->str|None:
    """Checks the status of a problem in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM problems WHERE id = ?", (problem_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def update_problem_status(problem_id: str, status: str):
    """Inserts or updates the status of a problem."""
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO problems (id, status, last_updated) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET status = excluded.status, last_updated = excluded.last_updated
        """, (problem_id, status, timestamp))