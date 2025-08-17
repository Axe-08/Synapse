# synapse/database_writer.py
"""
Implements a dedicated, single-threaded writer for the progress database.

This class uses the Producer-Consumer pattern to solve the "database is locked"
problem common in multi-threaded SQLite applications. All worker threads act
as producers, adding their SQL write operations to a queue. A single, dedicated
consumer thread (started by this class) reads from the queue and executes the
database writes serially. This ensures that all writes are ordered and contention-free.
"""
import sqlite3
import threading
from queue import Queue
import logging
from typing import Any, Tuple, Optional

from config import PROGRESS_DB_NAME

# A sentinel object used to signal the worker thread to stop
SENTINEL = object()

class DatabaseWriter:
    """
    A thread-safe service for writing to a SQLite database.
    """
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._queue: Queue[Tuple[str, Tuple[Any, ...]] | object] = Queue()
        self._thread: Optional[threading.Thread] = None

    def _worker_loop(self) -> None:
        """
        The main loop for the consumer thread.

        It continuously fetches operations from the queue and executes them
        against a single, persistent database connection.
        """
        logging.info("Database writer thread started.")
        # Each thread must create its own connection
        conn = sqlite3.connect(self._db_path, timeout=15)
        # WAL mode is critical for allowing concurrent reads from other processes
        conn.execute("PRAGMA journal_mode=WAL;")

        while True:
            try:
                item = self._queue.get()
                if item is SENTINEL:
                    break  # Exit loop if sentinel is received

                sql, params = item
                conn.execute(sql, params)
                conn.commit()

            except sqlite3.Error as e:
                logging.error(f"Database writer error: {e}. SQL: {sql}")
                # Consider adding logic to rollback or handle the error
            except Exception as e:
                logging.error(f"An unexpected error occurred in the DB writer thread: {e}")
            finally:
                if item is not SENTINEL:
                    self._queue.task_done()
        conn.close()
        logging.info("Database writer thread stopped.")

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        """
        Public method for other threads to enqueue a write operation.

        Args:
            sql: The SQL query string to execute.
            params: A tuple of parameters to bind to the query.
        """
        self._queue.put((sql, params))

    def start(self) -> None:
        """Starts the background writer thread if it's not already running."""
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._worker_loop, name="DatabaseWriterThread", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stops the background writer thread gracefully."""
        if self._thread and self._thread.is_alive():
            self._queue.put(SENTINEL)
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logging.warning("Database writer thread did not stop in time.")
            self._thread = None
    def wait_for_completion(self) -> None: # <--- ADD THIS ENTIRE NEW METHOD
        """
        Blocks until the queue of pending write operations is empty.
        This is essential for scripts that need to ensure writes are
        persisted before performing a critical read.
        """
        logging.info("Waiting for database writer to flush queue...")
        self._queue.join()
        logging.info("Database writer queue flushed.")

# Create a single, global instance to be used by the entire application
db_writer = DatabaseWriter(PROGRESS_DB_NAME)