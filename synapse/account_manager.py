# synapse/account_manager.py
"""
Multi-account manager for Codeforces scraping.

Provides round-robin account rotation with ban detection, cooldown tracking,
and telemetry logging to the scraper_stats table.

Accounts are parsed from the CF_ACCOUNTS environment variable in the format:
    handle1:password1,handle2:password2,...

If CF_ACCOUNTS is not set, falls back to the single CF_HANDLE/CF_PASSWORD pair.
"""
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import synapse.database as db


# ── Account States ──────────────────────────────────────────────────────────

ACCOUNT_ACTIVE = "ACTIVE"
ACCOUNT_COOLING = "COOLING"
ACCOUNT_BANNED = "BANNED"

# Default cooldown after ban detection (seconds)
DEFAULT_BAN_COOLDOWN = 600   # 10 minutes
MAX_BAN_COOLDOWN = 7200      # 2 hours cap


@dataclass
class ScraperAccount:
    """Represents a single Codeforces scraping account."""
    handle: str
    password: str
    status: str = ACCOUNT_ACTIVE

    # Telemetry
    total_requests: int = 0
    successful_requests: int = 0
    blocks_count: int = 0
    last_block_at: float = 0.0
    requests_since_last_block: int = 0
    cooldown_until: float = 0.0

    # Adaptive pacing
    _ban_durations: List[float] = field(default_factory=list)

    @property
    def avg_ban_duration(self) -> float:
        """Average ban duration in seconds (for adaptive cooldown)."""
        if not self._ban_durations:
            return DEFAULT_BAN_COOLDOWN
        return sum(self._ban_durations) / len(self._ban_durations)

    @property
    def safe_request_interval(self) -> float:
        """
        Calculate a safe delay between requests based on ban history.
        More bans → longer delays.
        """
        if self.blocks_count == 0:
            return 2.0  # Default safe pace
        # Increase delay by 1s per ban, capped at 15s
        interval = min(2.0 + self.blocks_count * 1.0, 15.0)
        # If last ban was recent (< 30 min ago), add extra caution
        if self.last_block_at and (time.time() - self.last_block_at) < 1800:
            interval *= 1.5
        return interval


class AccountManager:
    """
    Thread-safe manager for multiple Codeforces scraping accounts.

    Provides round-robin rotation with ban detection, adaptive cooldowns,
    and telemetry logging.
    """

    def __init__(self, accounts: List[Dict[str, str]]):
        """
        Initialize with a list of account dicts.

        Args:
            accounts: List of {'handle': '...', 'password': '...'} dicts.
        """
        if not accounts:
            raise ValueError("Account list cannot be empty.")

        self._accounts: List[ScraperAccount] = [
            ScraperAccount(handle=a['handle'], password=a['password'])
            for a in accounts
        ]
        self._lock = threading.Lock()
        self._round_robin_idx = 0
        logging.info(
            f"AccountManager initialized with {len(self._accounts)} accounts: "
            f"{[a.handle for a in self._accounts]}"
        )

    @classmethod
    def from_env(cls) -> 'AccountManager':
        """
        Create an AccountManager from environment variables.

        Tries CF_ACCOUNTS first (format: handle1:pass1,handle2:pass2,...),
        falls back to CF_HANDLE + CF_PASSWORD.
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()

        cf_accounts_str = os.getenv("CF_ACCOUNTS", "")
        if cf_accounts_str:
            accounts = []
            for pair in cf_accounts_str.split(","):
                pair = pair.strip()
                if ":" in pair:
                    handle, password = pair.split(":", 1)
                    accounts.append({"handle": handle.strip(), "password": password.strip()})
            if accounts:
                return cls(accounts)

        # Fallback: single account from CF_HANDLE and CF_PASSWORD
        handle = os.getenv("CF_HANDLE", "")
        password = os.getenv("CF_PASSWORD", "")
        if handle and password:
            return cls([{"handle": handle, "password": password}])

        raise ValueError(
            "No CF accounts found. Set CF_ACCOUNTS='handle:pass,...' or CF_HANDLE + CF_PASSWORD."
        )

    def get_active_account(self) -> Optional[ScraperAccount]:
        """
        Return the next available account using round-robin rotation.
        Skips accounts that are COOLING or BANNED.

        Returns:
            A ScraperAccount, or None if all accounts are unavailable.
        """
        with self._lock:
            now = time.time()
            n = len(self._accounts)

            # First, unblock any accounts whose cooldown has expired
            for acct in self._accounts:
                if acct.status == ACCOUNT_COOLING and now >= acct.cooldown_until:
                    acct.status = ACCOUNT_ACTIVE
                    acct.cooldown_until = 0.0
                    logging.info(f"Account {acct.handle} cooldown expired → ACTIVE")
                    self.log_telemetry(acct.handle, "ban_lifted", {"auto": True})

            # Round-robin through accounts
            for _ in range(n):
                acct = self._accounts[self._round_robin_idx % n]
                self._round_robin_idx = (self._round_robin_idx + 1) % n
                if acct.status == ACCOUNT_ACTIVE:
                    acct.total_requests += 1
                    acct.requests_since_last_block += 1
                    return acct

            return None

    def mark_banned(self, handle: str) -> None:
        """
        Mark an account as COOLING with an adaptive cooldown.

        Args:
            handle: The CF handle of the banned account.
        """
        with self._lock:
            acct = self._find_account(handle)
            if not acct:
                return

            acct.status = ACCOUNT_COOLING
            acct.blocks_count += 1
            acct.last_block_at = time.time()
            acct.requests_since_last_block = 0

            # Adaptive cooldown: increases with ban count, capped at MAX
            cooldown = min(
                DEFAULT_BAN_COOLDOWN * (1.5 ** (acct.blocks_count - 1)),
                MAX_BAN_COOLDOWN,
            )
            acct.cooldown_until = time.time() + cooldown
            acct._ban_durations.append(cooldown)

            logging.warning(
                f"Account {handle} BANNED. "
                f"Cooldown: {cooldown:.0f}s. Total bans: {acct.blocks_count}."
            )
            self.log_telemetry(handle, "ban_detected", {
                "cooldown_seconds": cooldown,
                "total_bans": acct.blocks_count,
            })

    def mark_unbanned(self, handle: str) -> None:
        """Manually restore an account to ACTIVE."""
        with self._lock:
            acct = self._find_account(handle)
            if acct:
                acct.status = ACCOUNT_ACTIVE
                acct.cooldown_until = 0.0
                logging.info(f"Account {handle} manually unbanned → ACTIVE")
                self.log_telemetry(handle, "ban_lifted", {"manual": True})

    def get_safe_rate(self, handle: str) -> float:
        """Get the safe request interval (seconds) for an account."""
        with self._lock:
            acct = self._find_account(handle)
            return acct.safe_request_interval if acct else 5.0

    def get_all_stats(self) -> List[Dict]:
        """Return telemetry stats for all accounts (for dashboard)."""
        with self._lock:
            return [
                {
                    "handle": a.handle,
                    "status": a.status,
                    "total_requests": a.total_requests,
                    "successful_requests": a.successful_requests,
                    "blocks_count": a.blocks_count,
                    "requests_since_last_block": a.requests_since_last_block,
                    "safe_interval": a.safe_request_interval,
                    "cooldown_remaining": max(0, a.cooldown_until - time.time()),
                }
                for a in self._accounts
            ]

    def has_healthy_account(self) -> bool:
        """True if at least one account is ACTIVE."""
        with self._lock:
            return any(a.status == ACCOUNT_ACTIVE for a in self._accounts)

    def log_telemetry(self, handle: str, event_type: str, details: dict = None) -> None:
        """
        Write a scraper event to the scraper_stats table.

        Args:
            handle: CF account handle.
            event_type: One of scrape_success, scrape_fail, ban_detected, ban_lifted.
            details: Optional dict of additional info.
        """
        import json
        try:
            db._async_execute(
                db._adapt_sql(
                    "INSERT INTO scraper_stats (account, event_type, details_json) "
                    "VALUES (?, ?, ?)"
                ),
                (handle, event_type, json.dumps(details or {})),
            )
        except Exception as e:
            logging.debug(f"Failed to log scraper telemetry: {e}")

    def mark_success(self, handle: str) -> None:
        """Record a successful scrape for an account."""
        with self._lock:
            acct = self._find_account(handle)
            if acct:
                acct.successful_requests += 1
        self.log_telemetry(handle, "scrape_success", {})

    def _find_account(self, handle: str) -> Optional[ScraperAccount]:
        """Find account by handle (must be called under lock)."""
        for acct in self._accounts:
            if acct.handle == handle:
                return acct
        return None
