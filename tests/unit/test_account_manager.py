# tests/unit/test_account_manager.py
"""
Unit tests for the multi-account scraper manager.
"""
import time
import pytest
from synapse.account_manager import (
    AccountManager, ScraperAccount,
    ACCOUNT_ACTIVE, ACCOUNT_COOLING, ACCOUNT_BANNED,
    DEFAULT_BAN_COOLDOWN,
)


@pytest.fixture
def two_accounts():
    """Two test accounts."""
    return AccountManager([
        {"handle": "user1", "password": "pass1"},
        {"handle": "user2", "password": "pass2"},
    ])


@pytest.fixture
def three_accounts():
    """Three test accounts."""
    return AccountManager([
        {"handle": "alpha", "password": "p1"},
        {"handle": "beta", "password": "p2"},
        {"handle": "gamma", "password": "p3"},
    ])


class TestAccountManagerInit:

    def test_init_with_accounts(self, two_accounts):
        stats = two_accounts.get_all_stats()
        assert len(stats) == 2
        assert stats[0]["handle"] == "user1"
        assert stats[1]["handle"] == "user2"

    def test_init_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            AccountManager([])

    def test_from_env_with_cf_accounts(self, monkeypatch):
        monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
        monkeypatch.setenv("CF_ACCOUNTS", "h1:p1,h2:p2")
        am = AccountManager.from_env()
        stats = am.get_all_stats()
        assert len(stats) == 2
        assert stats[0]["handle"] == "h1"
        assert stats[1]["handle"] == "h2"

    def test_from_env_fallback_single(self, monkeypatch):
        monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
        monkeypatch.delenv("CF_ACCOUNTS", raising=False)
        monkeypatch.setenv("CF_HANDLE", "solo")
        monkeypatch.setenv("CF_PASSWORD", "pass")
        am = AccountManager.from_env()
        stats = am.get_all_stats()
        assert len(stats) == 1
        assert stats[0]["handle"] == "solo"


class TestRoundRobin:

    def test_rotation(self, two_accounts):
        a1 = two_accounts.get_active_account()
        a2 = two_accounts.get_active_account()
        assert a1.handle != a2.handle

    def test_full_cycle(self, three_accounts):
        handles = [three_accounts.get_active_account().handle for _ in range(6)]
        assert handles[:3] == ["alpha", "beta", "gamma"]
        assert handles[3:] == ["alpha", "beta", "gamma"]


class TestBanManagement:

    def test_mark_banned_sets_cooling(self, two_accounts):
        two_accounts.mark_banned("user1")
        stats = two_accounts.get_all_stats()
        u1 = next(s for s in stats if s["handle"] == "user1")
        assert u1["status"] == ACCOUNT_COOLING
        assert u1["blocks_count"] == 1

    def test_banned_account_skipped_in_rotation(self, two_accounts):
        two_accounts.mark_banned("user1")
        acct = two_accounts.get_active_account()
        assert acct.handle == "user2"

    def test_all_banned_returns_none(self, two_accounts):
        two_accounts.mark_banned("user1")
        two_accounts.mark_banned("user2")
        assert two_accounts.get_active_account() is None

    def test_mark_unbanned_restores(self, two_accounts):
        two_accounts.mark_banned("user1")
        two_accounts.mark_unbanned("user1")
        stats = two_accounts.get_all_stats()
        u1 = next(s for s in stats if s["handle"] == "user1")
        assert u1["status"] == ACCOUNT_ACTIVE

    def test_escalating_cooldown(self, two_accounts):
        # First ban: base cooldown
        two_accounts.mark_banned("user1")
        stats1 = two_accounts.get_all_stats()
        cd1 = next(s for s in stats1 if s["handle"] == "user1")["cooldown_remaining"]

        two_accounts.mark_unbanned("user1")
        # Second ban: should be 1.5x longer
        two_accounts.mark_banned("user1")
        stats2 = two_accounts.get_all_stats()
        cd2 = next(s for s in stats2 if s["handle"] == "user1")["cooldown_remaining"]
        assert cd2 > cd1 * 1.3  # At least 1.3x (accounting for time passage)


class TestSafeRate:

    def test_default_rate_no_bans(self, two_accounts):
        rate = two_accounts.get_safe_rate("user1")
        assert rate == 2.0

    def test_rate_increases_with_bans(self, two_accounts):
        two_accounts.mark_banned("user1")
        two_accounts.mark_unbanned("user1")
        rate = two_accounts.get_safe_rate("user1")
        assert rate > 2.0

    def test_unknown_handle_returns_default(self, two_accounts):
        rate = two_accounts.get_safe_rate("nobody")
        assert rate == 5.0


class TestHealthCheck:

    def test_has_healthy_when_active(self, two_accounts):
        assert two_accounts.has_healthy_account() is True

    def test_not_healthy_when_all_banned(self, two_accounts):
        two_accounts.mark_banned("user1")
        two_accounts.mark_banned("user2")
        assert two_accounts.has_healthy_account() is False

    def test_healthy_if_one_active(self, two_accounts):
        two_accounts.mark_banned("user1")
        assert two_accounts.has_healthy_account() is True


class TestTelemetry:

    def test_mark_success_increments(self, two_accounts):
        two_accounts.mark_success("user1")
        two_accounts.mark_success("user1")
        stats = two_accounts.get_all_stats()
        u1 = next(s for s in stats if s["handle"] == "user1")
        assert u1["successful_requests"] == 2

    def test_total_requests_incremented_on_get(self, two_accounts):
        two_accounts.get_active_account()
        stats = two_accounts.get_all_stats()
        assert any(s["total_requests"] == 1 for s in stats)
