# synapse/config_manager.py
"""
Implements a thread-safe, observable Singleton for managing dynamic configuration.
This ConfigManager is a central point for accessing pipeline parameters that can
be changed at runtime by the optimizer. It reads from and writes to the
'dynamic_config' table in the progress database, ensuring that all processes
share the same configuration state.
"""
import threading
import sqlite3
import logging
from typing import Any
from datetime import datetime

import config  # Import the static default values
from config import PROGRESS_DB_NAME

class ConfigManager:
    """
    A thread-safe Singleton that manages the pipeline's dynamic configuration
    by using the database as the single source of truth.
    Attributes:
        _instance: The single instance of the class.
        _lock: A re-entrant lock to ensure thread safety.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initializes the ConfigManager, loading defaults only once."""
        if not hasattr(self, '_initialized'):
            with self._lock:
                if not hasattr(self, '_initialized'):
                    self._config_cache: dict[str, Any] = {}
                    self._db_path = PROGRESS_DB_NAME
                    self._load_defaults_into_cache()
                    self.sync_from_db() # Load initial state from DB
                    self._initialized: bool = True

    def _load_defaults_into_cache(self) -> None:
        """Loads all tunable parameters from the static config.py file into the memory cache."""
        self._config_cache = {
            'ingestion_worker_count': config.DEFAULT_INGESTION_WORKER_COUNT,
            'analysis_worker_count': config.DEFAULT_ANALYSIS_WORKER_COUNT,
            'implementation_worker_count': config.DEFAULT_IMPLEMENTATION_WORKER_COUNT,
            'vjs_worker_count': config.DEFAULT_VJS_WORKER_COUNT,
            'data_assembly_worker_count': config.DEFAULT_DATA_ASSEMBLY_WORKER_COUNT,
            'analysis_batch_size': config.DEFAULT_ANALYSIS_BATCH_SIZE,
        }

    def _get_db_connection(self) -> sqlite3.Connection:
        """Establishes a connection to the progress database."""
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def sync_from_db(self) -> None:
        """
        (BUGFIX) Reads all key-value pairs from the `dynamic_config` table
        and updates the in-memory cache. This is the primary way the main
        application stays aware of changes made by the optimizer.
        """
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.execute("SELECT key, value FROM dynamic_config")
                    for key, value in cursor.fetchall():
                        # Try to cast to int, otherwise keep as string
                        try:
                            self._config_cache[key] = int(value)
                        except ValueError:
                            self._config_cache[key] = value
            except sqlite3.Error as e:
                logging.error(f"ConfigManager failed to sync from DB: {e}. Using cached values.")

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        Gets a configuration parameter from the in-memory cache in a thread-safe way.
        Args:
            key: The name of the parameter.
            default: The value to return if the key is not found.
        Returns:
            The value of the configuration parameter.
        """
        with self._lock:
            return self._config_cache.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """
        (BUGFIX) Sets a configuration parameter in the database, making it visible
        to all processes. Also updates the local cache. This is the primary
        method the optimizer will use.
        Args:
            key: The name of the parameter to set.
            value: The new value for the parameter.
        """
        with self._lock:
            current_value = self._config_cache.get(key)
            if str(current_value) == str(value):
                return # No change, no DB write needed

            try:
                with self._get_db_connection() as conn:
                    timestamp = datetime.now().isoformat()
                    conn.execute(
                        "INSERT OR REPLACE INTO dynamic_config (key, value, last_updated) VALUES (?, ?, ?)",
                        (key, str(value), timestamp)
                    )
                    conn.commit()
                # Update cache only after successful DB write
                self._config_cache[key] = value
                logging.info(f"ConfigManager set '{key}' -> '{value}' in database.")
            except sqlite3.Error as e:
                logging.error(f"ConfigManager failed to set param '{key}' in DB: {e}")

# Global instance to be imported by other modules
config_manager = ConfigManager()