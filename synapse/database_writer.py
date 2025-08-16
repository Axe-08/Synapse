# synapse/database_writer.py
import sqlite3
import threading
from queue import Queue
import logging
from typing import Any, Tuple, Optional

# --- Configuration ---
PROGRESS_DB_PATH = 'progress.db'
SENTINEL = object() # Used to signal the worker thread to stop

class DatabaseWriter:
    """
    A dedicated, thread-safe service for writing to the SQLite database.
    This pattern uses a single writer thread and a queue to serialize all
    database write operations, preventing `database is locked` errors.
    """
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._queue: Queue[Tuple[str, Tuple[Any, ...]]] = Queue()
        self._thread: Optional[threading.Thread] = None

    def _worker_loop(self):
        """The main loop for the consumer thread."""
        logging.info("Database writer thread started.")
        # Each thread must create its own connection
        conn = sqlite3.connect(self._db_path, timeout=15)
        # WAL mode is critical for allowing concurrent reads from other processes
        conn.execute("PRAGMA journal_mode=WAL;")
        
        while True:
            try:
                item = self._queue.get()
                if item is SENTINEL:
                    break # Exit loop if sentinel is received
                
                sql, params = item
                conn.execute(sql, params)
                conn.commit()

            except sqlite3.Error as e:
                logging.error(f"Database writer error: {e}. SQL: {sql}")
            except Exception as e:
                logging.error(f"An unexpected error occurred in the DB writer thread: {e}")
        
        conn.close()
        logging.info("Database writer thread stopped.")

    def execute(self, sql: str, params: Tuple[Any, ...] = ()):
        """Public method for other threads to enqueue a write operation."""
        self._queue.put((sql, params))

    def start(self):
        """Starts the background writer thread."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._worker_loop, name="DatabaseWriterThread", daemon=True)
            self._thread.start()

    def stop(self):
        """Stops the background writer thread gracefully."""
        if self._thread and self._thread.is_alive():
            self._queue.put(SENTINEL)
            self._thread.join(timeout=5)

# Create a single, global instance to be used by the entire application
db_writer = DatabaseWriter(PROGRESS_DB_PATH)