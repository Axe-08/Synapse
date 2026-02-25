# synapse/database_writer.py
"""
Implements a dedicated, single-threaded writer for the progress database.

Supports both SQLite and PostgreSQL backends. The backend is selected by
whether DATABASE_URL is set in the environment (PostgreSQL) or not (SQLite).

SQLite: Uses the existing WAL-mode, single-connection approach.
PostgreSQL: Uses psycopg2 with autocommit off; commits after every write.
"""
import threading
from queue import Queue
import logging
import os
from typing import Any, Tuple, Optional

from config import PROGRESS_DB_NAME

SENTINEL = object()

_DATABASE_URL = os.getenv('DATABASE_URL', '')


class DatabaseWriter:
    """
    A thread-safe, backend-agnostic write queue for the progress database.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._queue: Queue[Tuple[str, Tuple[Any, ...]] | object] = Queue()
        self._thread: Optional[threading.Thread] = None
        self._use_postgres = bool(_DATABASE_URL)

    def set_db_path(self, db_path: str) -> None:
        if self._thread and self._thread.is_alive():
            logging.error("Cannot change the database path while the writer thread is running.")
            return
        self._db_path = db_path

    # ------------------------------------------------------------------ #
    # Internal worker loops
    # ------------------------------------------------------------------ #

    def _worker_loop(self) -> None:
        if self._use_postgres:
            self._pg_worker_loop()
        else:
            self._sqlite_worker_loop()

    def _sqlite_worker_loop(self) -> None:
        import sqlite3
        logging.info("Database writer thread started (SQLite).")
        conn = sqlite3.connect(self._db_path, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        while True:
            item = self._queue.get()
            if item is SENTINEL:
                break
            sql, params = item
            try:
                conn.execute(sql, params)
                conn.commit()
            except sqlite3.Error as e:
                logging.error(f"DB writer (SQLite) error: {e}. SQL: {sql}")
            except Exception as e:
                logging.error(f"DB writer (SQLite) unexpected error: {e}")
            finally:
                self._queue.task_done()
        conn.close()
        logging.info("Database writer thread stopped (SQLite).")

    def _pg_worker_loop(self) -> None:
        import psycopg2
        logging.info("Database writer thread started (PostgreSQL).")
        conn = psycopg2.connect(_DATABASE_URL)
        conn.autocommit = False
        while True:
            item = self._queue.get()
            if item is SENTINEL:
                break
            sql, params = item
            # Convert SQLite-style ? placeholders to %s for psycopg2
            sql_pg = sql.replace('?', '%s')
            try:
                with conn.cursor() as cur:
                    cur.execute(sql_pg, params)
                conn.commit()
            except psycopg2.Error as e:
                conn.rollback()
                logging.error(f"DB writer (PG) error: {e}. SQL: {sql_pg}")
            except Exception as e:
                conn.rollback()
                logging.error(f"DB writer (PG) unexpected error: {e}")
            finally:
                self._queue.task_done()
        conn.close()
        logging.info("Database writer thread stopped (PostgreSQL).")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        """Enqueue a write operation (thread-safe)."""
        self._queue.put((sql, params))

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._worker_loop, name="DatabaseWriterThread", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._queue.put(SENTINEL)
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logging.warning("Database writer thread did not stop in time.")
            self._thread = None

    def wait_for_completion(self) -> None:
        """Block until all enqueued writes have been executed."""
        logging.info("Waiting for database writer to flush queue...")
        self._queue.join()
        logging.info("Database writer queue flushed.")


# Single global instance used by the entire application
db_writer = DatabaseWriter(PROGRESS_DB_NAME)