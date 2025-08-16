# synapse/key_manager.py
"""
Provides an intelligent, thread-safe manager for a pool of API keys.

This module is critical for maintaining pipeline health when interacting with
rate-limited external services. It implements a hybrid strategy for managing keys:

-   **Proactive Management:** It tracks requests and estimated tokens within a
    60-second window for each key, preventing the use of a key that is likely
    to be rate-limited.
-   **Reactive Management:** When an API call fails with a rate-limit error,
    the key is placed in an exponential backoff cooldown. Daily quota exhaustion
    triggers a longer cooldown until the next UTC midnight.
"""
import threading
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta, timezone

# --- Configuration ---
# Known limits for the target models.
RPM_LIMIT_GEMINI: int = 5
TPM_LIMIT_GEMINI: int = 2_000_000
RPM_LIMIT_GROQ: int = 30
TPM_LIMIT_GROQ: int = 25000 # Estimated based on service tier

# Number of consecutive successes required to reset a key's backoff level.
SUCCESS_RESET_THRESHOLD: int = 5

class KeyStatus(Enum):
    """Defines the possible states of an API key."""
    AVAILABLE = auto()      # Ready for use
    IN_USE = auto()         # Currently held by a worker
    RATE_LIMITED = auto()   # In a short-term, exponential backoff cooldown
    EXHAUSTED = auto()      # In a long-term cooldown until the next daily reset
    INVALID = auto()        # Permanently disabled

@dataclass
class ManagedKey:
    """Represents a single API key and its state."""
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    cooldown_until: float = 0.0

    # Proactive tracking attributes
    requests_in_window: int = 0
    tokens_in_window: int = 0
    window_start_time: float = field(default_factory=time.time)

    # Reactive tracking attributes
    backoff_level: int = 0
    successive_successes: int = 0

class KeyManager:
    """
    A thread-safe, intelligent manager for a pool of API keys.
    """
    def __init__(self, api_keys: List[str], service_name: str, cooldown_seconds: int = 60):
        if not api_keys:
            raise ValueError(f"API key list for {service_name} cannot be empty.")

        self._keys: List[ManagedKey] = [ManagedKey(key) for key in api_keys]
        self._lock = threading.Lock()
        self._service_name = service_name
        self._base_cooldown = cooldown_seconds

        # Assign rate limits based on the service this manager handles
        if "GEMINI" in self._service_name.upper():
            self.rpm_limit = RPM_LIMIT_GEMINI
            self.tpm_limit = TPM_LIMIT_GEMINI
        elif "GROQ" in self._service_name.upper():
            self.rpm_limit = RPM_LIMIT_GROQ
            self.tpm_limit = TPM_LIMIT_GROQ
        else: # Safe defaults for unknown services
            self.rpm_limit = 5
            self.tpm_limit = 1_000_000

    def _get_next_day_reset_time(self) -> float:
        """Calculates the Unix timestamp for the next midnight UTC."""
        now_utc = datetime.now(timezone.utc)
        tomorrow_utc = now_utc + timedelta(days=1)
        reset_time = tomorrow_utc.replace(hour=0, minute=0, second=5, microsecond=0)
        return reset_time.timestamp()

    def _check_and_reset_windows(self) -> None:
        """Internal method to update key statuses and proactive tracking windows."""
        now = time.time()
        for key in self._keys:
            if key.status in [KeyStatus.RATE_LIMITED, KeyStatus.EXHAUSTED] and now >= key.cooldown_until:
                key.status = KeyStatus.AVAILABLE
                key.cooldown_until = 0.0

            if now - key.window_start_time > 60:
                key.window_start_time = now
                key.requests_in_window = 0
                key.tokens_in_window = 0

    def get_key(self, estimated_tokens: int = 2000) -> Optional[ManagedKey]:
        """
        Gets an available key that has proactive capacity for the request.

        This method will wait for up to 15 seconds for a key to become available.

        Args:
            estimated_tokens: An estimate of the tokens the API call will consume.

        Returns:
            A ManagedKey object if one is available, otherwise None.
        """
        wait_time = 15
        start_time = time.time()
        while time.time() - start_time < wait_time:
            with self._lock:
                self._check_and_reset_windows()

                viable_keys = [
                    k for k in self._keys
                    if k.status == KeyStatus.AVAILABLE and
                       k.requests_in_window < self.rpm_limit and
                       k.tokens_in_window + estimated_tokens < self.tpm_limit
                ]

                if viable_keys:
                    # Prioritize the key with the fewest requests in the current window
                    best_key = min(viable_keys, key=lambda k: k.requests_in_window)
                    best_key.status = KeyStatus.IN_USE
                    return best_key

            time.sleep(0.5)
        return None

    def release_key(self, key: ManagedKey, outcome: KeyStatus, tokens_used: int = 0) -> None:
        """
        Releases a key, updating its state based on the API call outcome.

        Args:
            key: The ManagedKey object to release.
            outcome: The result of the API call (e.g., AVAILABLE for success).
            tokens_used: The number of tokens consumed by the call.
        """
        with self._lock:
            # Find the actual key object in our list to update its state
            managed_key = next((k for k in self._keys if k.key_string == key.key_string), None)
            if not managed_key: return

            if outcome == KeyStatus.AVAILABLE: # Success
                managed_key.status = KeyStatus.AVAILABLE
                managed_key.requests_in_window += 1
                managed_key.tokens_in_window += tokens_used
                managed_key.successive_successes += 1
                if managed_key.successive_successes >= SUCCESS_RESET_THRESHOLD:
                    managed_key.backoff_level = 0

            elif outcome == KeyStatus.RATE_LIMITED:
                managed_key.status = KeyStatus.RATE_LIMITED
                cooldown = self._base_cooldown * (2 ** managed_key.backoff_level)
                managed_key.cooldown_until = time.time() + cooldown
                managed_key.backoff_level = min(managed_key.backoff_level + 1, 5) # Cap backoff
                managed_key.successive_successes = 0

            elif outcome == KeyStatus.EXHAUSTED:
                managed_key.status = KeyStatus.EXHAUSTED
                managed_key.cooldown_until = self._get_next_day_reset_time()
                managed_key.successive_successes = 0

            elif outcome == KeyStatus.INVALID:
                managed_key.status = KeyStatus.INVALID
                managed_key.successive_successes = 0