# synapse/key_manager.py (Definitive Phase 1 Version)
import threading
import time
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta, timezone

# --- Configuration ---
# Based on our latest intelligence for the target models.

# Gemini 2.5 Pro (Analyst)
RPM_LIMIT_GEMINI = 5
TPM_LIMIT_GEMINI = 2_000_000
RPD_LIMIT_GEMINI = 2_880 # For monitoring; logic reacts to the EXHAUSTED error.

# Meta Llama on Groq (Implementer)
RPM_LIMIT_GROQ = 30
TPM_LIMIT_GROQ = 25000 # A reasonable estimate for a high RPM model.

SUCCESS_RESET_THRESHOLD = 5 # Successes needed to reset a key's backoff level.

class KeyStatus(Enum):
    """Defines the possible states of an API key."""
    AVAILABLE = auto()    # Ready for use
    IN_USE = auto()       # Currently held by a worker
    RATE_LIMITED = auto() # In a short-term, exponential backoff cooldown
    EXHAUSTED = auto()    # In a long-term cooldown until the next daily reset
    INVALID = auto()      # Permanently disabled

@dataclass
class ManagedKey:
    """Represents a single API key and its state."""
    key_string: str
    status: KeyStatus = KeyStatus.AVAILABLE
    cooldown_until: float = 0.0
    
    # --- Proactive Tracking Attributes (for error prevention) ---
    requests_in_window: int = 0
    tokens_in_window: int = 0
    window_start_time: float = field(default_factory=time.time)
    
    # --- Reactive Tracking Attributes (for error recovery) ---
    backoff_level: int = 0
    successive_successes: int = 0

class KeyManager:
    """A thread-safe, intelligent manager for a pool of API keys."""
    def __init__(self, api_keys: List[str], service_name: str, cooldown_seconds: int = 60):
        if not api_keys:
            raise ValueError(f"API key list for {service_name} cannot be empty.")
        
        self._keys: List[ManagedKey] = [ManagedKey(key) for key in api_keys]
        self._lock = threading.Lock()
        self._service_name = service_name
        self._base_cooldown = cooldown_seconds
        
        # Assign limits based on the service this manager handles
        if "GEMINI" in self._service_name.upper():
            self.rpm_limit = RPM_LIMIT_GEMINI
            self.tpm_limit = TPM_LIMIT_GEMINI
        elif "GROQ" in self._service_name.upper():
            self.rpm_limit = RPM_LIMIT_GROQ
            self.tpm_limit = TPM_LIMIT_GROQ
        else: # Safe defaults
            self.rpm_limit = 5
            self.tpm_limit = 1_000_000

    def _get_next_day_reset_time(self) -> float:
        """Calculates the timestamp for the next midnight UTC."""
        now_utc = datetime.now(timezone.utc)
        tomorrow_utc = now_utc + timedelta(days=1)
        reset_time = tomorrow_utc.replace(hour=0, minute=0, second=5, microsecond=0)
        return reset_time.timestamp()

    def _check_and_reset_windows(self):
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
        """Gets an available key that has proactive capacity for the request."""
        wait_time = 15
        start_time = time.time()
        while time.time() - start_time < wait_time:
            with self._lock:
                self._check_and_reset_windows()
                
                viable_keys = []
                for key in self._keys:
                    has_capacity = (key.requests_in_window < self.rpm_limit and 
                                    key.tokens_in_window + estimated_tokens < self.tpm_limit)
                    if key.status == KeyStatus.AVAILABLE and has_capacity:
                        viable_keys.append(key)
                
                if viable_keys:
                    # Prioritize the key that has been used the least in the current window
                    best_key = min(viable_keys, key=lambda k: k.requests_in_window)
                    best_key.status = KeyStatus.IN_USE
                    return best_key
            
            time.sleep(0.5)
        
        return None

    def release_key(self, key: ManagedKey, outcome: KeyStatus, tokens_used: int = 0):
        """Releases a key, updating its state based on the API call outcome."""
        with self._lock:
            for managed_key in self._keys:
                if managed_key.key_string == key.key_string:
                    if outcome == KeyStatus.AVAILABLE: # Success
                        managed_key.status = KeyStatus.AVAILABLE
                        managed_key.requests_in_window += 1
                        managed_key.tokens_in_window += tokens_used
                        managed_key.successive_successes += 1
                        if managed_key.successive_successes >= SUCCESS_RESET_THRESHOLD:
                            managed_key.backoff_level = 0
                    
                    elif outcome == KeyStatus.RATE_LIMITED: # Short-term RPM/TPM limit
                        managed_key.status = KeyStatus.RATE_LIMITED
                        cooldown = self._base_cooldown * (2 ** managed_key.backoff_level)
                        managed_key.cooldown_until = time.time() + cooldown
                        managed_key.backoff_level += 1
                        managed_key.successive_successes = 0

                    elif outcome == KeyStatus.EXHAUSTED: # Long-term daily quota limit
                        managed_key.status = KeyStatus.EXHAUSTED
                        managed_key.cooldown_until = self._get_next_day_reset_time()
                        managed_key.successive_successes = 0

                    elif outcome == KeyStatus.INVALID: # Permanent failure
                        managed_key.status = KeyStatus.INVALID
                        managed_key.successive_successes = 0
                    
                    break