# tests/unit/test_optimizer.py
"""
Unit tests for the intelligent pipeline optimizer (v2).
Tests each decision module independently using mocked state.
"""
import time
import pytest
from unittest.mock import MagicMock, patch

from synapse.optimizer import PipelineOptimizer
from synapse.key_manager import KeyManager, ManagedKey, KeyStatus


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_optimizer(km_gemini=None, km_groq=None, account_mgr=None):
    """Create an optimizer with optional mocked dependencies."""
    return PipelineOptimizer(
        km_gemini=km_gemini,
        km_groq=km_groq,
        account_manager=account_mgr,
    )


def _mock_config(values: dict):
    """Patch config_manager.get_param to return values from a dict."""
    def _get(key, default=None):
        return values.get(key, default)
    return _get


# ── Module 1: Stage Skipping ────────────────────────────────────────────────

class TestStageSkipping:

    def test_zero_workers_when_no_pending(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 0, 'pending_implementation': 5}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({
                'analysis_worker_count': 4,
                'implementation_worker_count': 4,
            })
            changes = opt._apply_stage_skipping(depths)
        assert changes.get('analysis_worker_count') == 0

    def test_restore_workers_when_jobs_appear(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 10, 'pending_implementation': 0}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({
                'analysis_worker_count': 0,
                'implementation_worker_count': 4,
            })
            changes = opt._apply_stage_skipping(depths)
        assert changes.get('analysis_worker_count', 0) > 0

    def test_no_change_when_workers_match(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 5}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({'analysis_worker_count': 4})
            changes = opt._apply_stage_skipping(depths)
        assert 'analysis_worker_count' not in changes


# ── Module 4: Backpressure ──────────────────────────────────────────────────

class TestBackpressure:

    def test_throttle_when_downstream_overwhelmed(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 5, 'pending_implementation': 20}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({'analysis_worker_count': 4})
            changes = opt._apply_backpressure(depths)
        assert changes.get('analysis_worker_count', 4) < 4

    def test_no_throttle_when_balanced(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 10, 'pending_implementation': 10}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({'analysis_worker_count': 4})
            changes = opt._apply_backpressure(depths)
        assert 'analysis_worker_count' not in changes

    def test_no_throttle_when_upstream_empty(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 0, 'pending_implementation': 50}
        with patch('synapse.optimizer.config_manager') as cm:
            cm.get_param.side_effect = _mock_config({'analysis_worker_count': 4})
            changes = opt._apply_backpressure(depths)
        assert 'analysis_worker_count' not in changes


# ── Module 5: API Throttle ──────────────────────────────────────────────────

class TestAPIThrottle:

    def test_soft_throttle_gemini_90pct(self):
        opt = _make_optimizer()
        budgets = {'gemini': {'rpd_utilization': 0.91, 'tpd_utilization': 0.5}}
        changes = opt._apply_api_throttle(budgets)
        assert changes['analysis_worker_count'] == 1

    def test_hard_throttle_gemini_98pct(self):
        opt = _make_optimizer()
        budgets = {'gemini': {'rpd_utilization': 0.99, 'tpd_utilization': 0.5}}
        changes = opt._apply_api_throttle(budgets)
        assert changes['analysis_worker_count'] == 0

    def test_soft_throttle_groq_90pct(self):
        opt = _make_optimizer()
        budgets = {'groq': {'rpd_utilization': 0.92, 'tpd_utilization': 0.5}}
        changes = opt._apply_api_throttle(budgets)
        assert changes['implementation_worker_count'] == 1

    def test_hard_throttle_groq_98pct(self):
        opt = _make_optimizer()
        budgets = {'groq': {'rpd_utilization': 0.5, 'tpd_utilization': 0.99}}
        changes = opt._apply_api_throttle(budgets)
        assert changes['implementation_worker_count'] == 0

    def test_no_throttle_under_90pct(self):
        opt = _make_optimizer()
        budgets = {'gemini': {'rpd_utilization': 0.5, 'tpd_utilization': 0.3}}
        changes = opt._apply_api_throttle(budgets)
        assert 'analysis_worker_count' not in changes


# ── Module 6: Panic Mode ────────────────────────────────────────────────────

class TestPanicMode:

    def test_panic_halts_ingestion(self):
        opt = _make_optimizer()
        scraper = {'has_healthy_account': False}
        changes = opt._apply_panic_mode(scraper)
        assert changes['ingestion_worker_count'] == 0
        assert opt.active_mode == "panic"

    def test_panic_lifts_when_account_returns(self):
        opt = _make_optimizer()
        opt._active_mode = "panic"
        scraper = {'has_healthy_account': True}
        changes = opt._apply_panic_mode(scraper)
        assert changes['ingestion_worker_count'] > 0
        assert opt.active_mode == "normal"

    def test_no_panic_when_healthy(self):
        opt = _make_optimizer()
        scraper = {'has_healthy_account': True}
        changes = opt._apply_panic_mode(scraper)
        assert 'ingestion_worker_count' not in changes


# ── Module 3: Burst Mode ────────────────────────────────────────────────────

class TestBurstMode:

    def test_burst_activates_on_deep_queue_off_peak(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 30, 'pending_implementation': 10}
        with patch.object(opt, '_is_off_peak_hours', return_value=True):
            changes = opt._apply_burst_mode(depths)
        assert changes.get('analysis_worker_count', 0) > 0

    def test_no_burst_during_peak(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 30, 'pending_implementation': 10}
        with patch.object(opt, '_is_off_peak_hours', return_value=False):
            changes = opt._apply_burst_mode(depths)
        assert 'analysis_worker_count' not in changes

    def test_no_burst_on_small_queue(self):
        opt = _make_optimizer()
        depths = {'pending_analysis': 3, 'pending_implementation': 2}
        with patch.object(opt, '_is_off_peak_hours', return_value=True):
            changes = opt._apply_burst_mode(depths)
        assert 'analysis_worker_count' not in changes

    def test_no_burst_in_panic(self):
        opt = _make_optimizer()
        opt._active_mode = "panic"
        depths = {'pending_analysis': 30, 'pending_implementation': 10}
        with patch.object(opt, '_is_off_peak_hours', return_value=True):
            changes = opt._apply_burst_mode(depths)
        assert 'analysis_worker_count' not in changes


# ── Integration: Full Optimize Cycle ─────────────────────────────────────────

class TestOptimizeCycle:

    @patch('synapse.optimizer.config_manager')
    def test_full_cycle_returns_changes(self, mock_cm, tmp_progress_db):
        """Full optimize() call should not crash and return a dict."""
        mock_cm.get_param.side_effect = _mock_config({
            'analysis_worker_count': 4,
            'implementation_worker_count': 4,
            'vjs_worker_count': 2,
            'data_assembly_worker_count': 1,
            'ingestion_worker_count': 1,
        })
        mock_cm.sync_from_db.return_value = None

        opt = _make_optimizer()
        changes = opt.optimize()
        assert isinstance(changes, dict)

    def test_active_mode_default_is_normal(self):
        opt = _make_optimizer()
        assert opt.active_mode == "normal"

    def test_budget_reader_with_no_km(self):
        opt = _make_optimizer()
        budgets = opt._read_api_budgets()
        assert budgets == {}

    def test_budget_reader_with_km(self):
        km = MagicMock()
        km.get_budget_status.return_value = {'rpd_utilization': 0.5}
        opt = _make_optimizer(km_gemini=km)
        budgets = opt._read_api_budgets()
        assert 'gemini' in budgets

    def test_scraper_reader_without_am(self):
        opt = _make_optimizer()
        health = opt._read_scraper_health()
        assert health['has_healthy_account'] is True

    def test_scraper_reader_with_am(self):
        am = MagicMock()
        am.has_healthy_account.return_value = False
        am.get_all_stats.return_value = []
        opt = _make_optimizer(account_mgr=am)
        health = opt._read_scraper_health()
        assert health['has_healthy_account'] is False
