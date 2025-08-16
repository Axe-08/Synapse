# synapse/config_manager.py
"""
Implements a thread-safe, observable Singleton for managing dynamic configuration.

This ConfigManager is a central point for accessing pipeline parameters that can
be changed at runtime by the optimizer. It follows the Singleton pattern to ensure
only one instance exists, and the Observer pattern to notify other components
(like the optimizer's controllers) of changes to configuration values.
"""
import threading
from typing import Any, List, Protocol

import config  # Import the static default values

class IConfigObserver(Protocol):
    """
    Defines the interface for objects that need to be notified of config changes.
    This is the "Observer" in the Observer design pattern.
    """
    def on_config_change(self, key: str, new_value: Any) -> None:
        """This method is called by the ConfigManager when a parameter changes."""
        ...

class ConfigManager:
    """
    A thread-safe Singleton that manages the pipeline's dynamic configuration.

    It loads initial values from config.py and allows the optimizer to
    update them at runtime. It also notifies registered observers of changes.

    Attributes:
        _instance: The single instance of the class.
        _lock: A re-entrant lock to ensure thread safety.
    """
    _instance = None
    _lock = threading.RLock()  # Re-entrant lock for complex, nested calls

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                # Double-check locking to ensure thread safety
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initializes the ConfigManager, loading defaults only once."""
        if not hasattr(self, '_initialized'):
            with self._lock:
                if not hasattr(self, '_initialized'):
                    self._config_data: dict[str, Any] = {}
                    self._observers: List[IConfigObserver] = []
                    self._load_defaults()
                    self._initialized: bool = True

    def _load_defaults(self) -> None:
        """Loads all tunable parameters from the static config.py file."""
        self._config_data = {
            'ingestion_worker_count': config.DEFAULT_INGESTION_WORKER_COUNT,
            'analysis_worker_count': config.DEFAULT_ANALYSIS_WORKER_COUNT,
            'implementation_worker_count': config.DEFAULT_IMPLEMENTATION_WORKER_COUNT,
            'vjs_worker_count': config.DEFAULT_VJS_WORKER_COUNT,
            'analysis_batch_size': config.DEFAULT_ANALYSIS_BATCH_SIZE,
            'scraper_request_timeout': config.DEFAULT_SCRAPER_REQUEST_TIMEOUT,
        }

    def attach(self, observer: IConfigObserver) -> None:
        """
        Registers an observer to be notified of changes.

        Args:
            observer: The observer object to register.
        """
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def detach(self, observer: IConfigObserver) -> None:
        """
        Unregisters an observer.

        Args:
            observer: The observer object to unregister.
        """
        with self._lock:
            try:
                self._observers.remove(observer)
            except ValueError:
                pass  # Observer not found

    def _notify(self, key: str, value: Any) -> None:
        """Notifies all registered observers of a configuration change."""
        # The notification happens outside the main lock to prevent deadlocks
        # if an observer's update method tries to access the config again.
        observers_to_notify = []
        with self._lock:
            observers_to_notify = self._observers[:]

        for observer in observers_to_notify:
            observer.on_config_change(key, value)

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        Gets a configuration parameter in a thread-safe way.

        Args:
            key: The name of the parameter.
            default: The value to return if the key is not found.

        Returns:
            The value of the configuration parameter.
        """
        with self._lock:
            return self._config_data.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """
        Sets a configuration parameter and notifies observers if it changed.
        This is the primary method the optimizer will use.

        Args:
            key: The name of the parameter to set.
            value: The new value for the parameter.
        """
        with self._lock:
            current_value = self._config_data.get(key)
            if current_value == value:
                return  # No change, no notification needed

            self._config_data[key] = value

        # Notify observers of the change *after* releasing the lock.
        self._notify(key, value)

# Global instance to be imported by other modules
config_manager = ConfigManager()