# synapse/key_manager.py
import threading
import time
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional

class KeyStatus(Enum):
    AVAILABLE = auto()
    IN_USE = auto()
    RATE_LIMITED = auto()
    INVALID = auto()

@dataclass
class ManagedKey:
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    cooldown_until: float = 0.0

class KeyManager:
    """A thread-safe manager for a pool of API keys."""
    def __init__(self, api_keys: List[str], cooldown_seconds: int = 60):
        self._keys: List[ManagedKey] = [ManagedKey(key) for key in api_keys]
        self._lock = threading.Lock()
        self._cooldown_seconds = cooldown_seconds
        if not self._keys:
            raise ValueError("API key list cannot be empty.")

    def _check_cooldowns(self):
        """Checks if any rate-limited keys can be made available again."""
        now = time.time()
        for key in self._keys:
            if key.status == KeyStatus.RATE_LIMITED and now >= key.cooldown_until:
                key.status = KeyStatus.AVAILABLE
                key.cooldown_until = 0.0

    def get_key(self) -> Optional[ManagedKey]:
        """
        Gets the next available key from the pool in a thread-safe manner.
        Returns None if no keys are available after a short wait.
        """
        wait_time = 5  # Total time to wait for a key in seconds
        start_time = time.time()
        while time.time() - start_time < wait_time:
            with self._lock:
                self._check_cooldowns()
                
                # Start searching from a random position to distribute load
                start_index = random.randint(0, len(self._keys) - 1)
                for i in range(len(self._keys)):
                    idx = (start_index + i) % len(self._keys)
                    key = self._keys[idx]
                    if key.status == KeyStatus.AVAILABLE:
                        key.status = KeyStatus.IN_USE
                        return key
            
            time.sleep(0.5) # Wait before retrying
        
        return None # No key became available in time

    def release_key(self, key: ManagedKey, outcome: KeyStatus):
        """
        Releases a key back to the pool, updating its status based on the API call outcome.
        """
        with self._lock:
            # Find the key in our list to update its state
            for managed_key in self._keys:
                if managed_key.key_string == key.key_string:
                    if outcome == KeyStatus.RATE_LIMITED:
                        managed_key.status = KeyStatus.RATE_LIMITED
                        managed_key.cooldown_until = time.time() + self._cooldown_seconds
                    elif outcome == KeyStatus.INVALID:
                        managed_key.status = KeyStatus.INVALID
                    else: # Assumes success
                        managed_key.status = KeyStatus.AVAILABLE
                    break