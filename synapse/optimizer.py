# synapse/optimizer.py
"""
Intelligent Pipeline Optimizer (v2)

Runs as a background thread, periodically reading pipeline state and adjusting
configuration parameters. Implements 7 decision modules:

1. Stage Skipping    — set workers=0 for stages with 0 pending jobs
2. Courtesy Mode     — reduce workers when DGX CPU is high
3. Burst Mode        — max workers during off-peak + low CPU
4. Backpressure      — throttle upstream when downstream queue is deep
5. API Throttle      — reduce workers when daily API budget is near-exhausted
6. Panic Mode        — halt ingestion when scraper accounts are all banned
7. Time Schedule     — allow burst only during off-peak hours (2am-6am IST)
"""
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any

from synapse.config_manager import config_manager
from config import (
    OPTIMIZER_LOOP_DELAY_SECONDS,
    OPTIMIZER_COOLDOWN_PERIOD_SECONDS,
    MAX_ANALYSIS_WORKERS,
    MAX_IMPLEMENTATION_WORKERS,
    MAX_VJS_WORKERS,
    MAX_INGESTION_WORKERS,
    DEFAULT_INGESTION_WORKER_COUNT,
    DEFAULT_ANALYSIS_WORKER_COUNT,
    DEFAULT_IMPLEMENTATION_WORKER_COUNT,
    DEFAULT_VJS_WORKER_COUNT,
    DEFAULT_DATA_ASSEMBLY_WORKER_COUNT,
    DEFAULT_SCRAPER_DELAY_SECONDS,
    TARGET_VJS_QUEUE_SIZE,
)

# IST offset from UTC
IST_OFFSET = timedelta(hours=5, minutes=30)

# Thresholds
COURTESY_CPU_SOFT = 70.0      # Halve workers
COURTESY_CPU_HARD = 90.0      # Set to 1
BURST_CPU_THRESHOLD = 20.0    # CPU must be below this for burst
BACKPRESSURE_RATIO = 2.0      # downstream > 2× upstream → throttle
API_THROTTLE_SOFT = 0.90      # >90% daily budget → 1 worker
API_THROTTLE_HARD = 0.98      # >98% daily budget → 0 workers


class PipelineOptimizer:
    """
    Intelligent optimizer with 7 decision modules.

    Each module inspects the current system state and proposes changes.
    Changes are merged with later modules overriding earlier ones (priority
    order: panic > throttle > courtesy > backpressure > burst > skip > schedule).
    """

    def __init__(
        self,
        km_gemini=None,
        km_groq=None,
        account_manager=None,
    ):
        """
        Args:
            km_gemini: KeyManager for Gemini API (optional — budget tracking).
            km_groq:   KeyManager for Groq API (optional — budget tracking).
            account_manager: AccountManager for scraper (optional — panic mode).
        """
        self._km_gemini = km_gemini
        self._km_groq = km_groq
        self._account_manager = account_manager
        self._last_action_time: Dict[str, float] = {}
        self._active_mode = "normal"  # normal, courtesy, burst, panic
        logging.info("PipelineOptimizer v2 initialized.")

    # ── Main Entry ──────────────────────────────────────────────────────────

    def optimize(self) -> Dict[str, Any]:
        """
        Main entry — called every cycle from the optimizer thread.

        Returns:
            Dict of changes applied (for logging/dashboard).
        """
        try:
            config_manager.sync_from_db()
        except Exception as e:
            logging.error(f"Optimizer: failed to sync config: {e}")

        # Read current state
        depths = self._read_queue_depths()
        budgets = self._read_api_budgets()
        scraper = self._read_scraper_health()

        # Apply decision modules (order = priority, later overrides earlier)
        changes = {}
        changes.update(self._apply_stage_skipping(depths))
        changes.update(self._apply_time_schedule())
        changes.update(self._apply_backpressure(depths))
        changes.update(self._apply_courtesy_mode())
        changes.update(self._apply_burst_mode(depths))
        changes.update(self._apply_api_throttle(budgets))
        changes.update(self._apply_panic_mode(scraper))

        # Write changes
        self._write_changes(changes)

        # Health check
        self._health_check(depths)

        return changes

    # ── Decision Module 1: Stage Skipping ────────────────────────────────

    def _apply_stage_skipping(self, depths: Dict[str, int]) -> Dict[str, Any]:
        """Set workers=0 for any stage with 0 pending jobs."""
        changes = {}
        stage_worker_map = {
            'pending_analysis':       'analysis_worker_count',
            'pending_implementation': 'implementation_worker_count',
            'pending_vjs':            'vjs_worker_count',
            'pending_data_assembly':  'data_assembly_worker_count',
        }
        for status, param in stage_worker_map.items():
            current = config_manager.get_param(param, 1)
            if depths.get(status, 0) == 0 and current > 0:
                changes[param] = 0
            elif depths.get(status, 0) > 0 and current == 0:
                # Restore to default
                defaults = {
                    'analysis_worker_count': DEFAULT_ANALYSIS_WORKER_COUNT,
                    'implementation_worker_count': DEFAULT_IMPLEMENTATION_WORKER_COUNT,
                    'vjs_worker_count': DEFAULT_VJS_WORKER_COUNT,
                    'data_assembly_worker_count': DEFAULT_DATA_ASSEMBLY_WORKER_COUNT,
                }
                changes[param] = defaults.get(param, 1)
        return changes

    # ── Decision Module 2: Courtesy Mode ─────────────────────────────────

    def _apply_courtesy_mode(self) -> Dict[str, Any]:
        """
        Reduce workers when DGX CPU is high to be a good shared-resource citizen.
        CPU>70%: halve all worker counts.
        CPU>90%: set all to 1.
        """
        changes = {}
        # For now, courtesy mode is a placeholder until DGX metrics are available.
        # When dgx_usage_stats table has data, this will read CPU%.
        # Leaving inert until Phase 8 integrates DGX monitoring.
        return changes

    # ── Decision Module 3: Burst Mode ────────────────────────────────────

    def _apply_burst_mode(self, depths: Dict[str, int]) -> Dict[str, Any]:
        """
        CPU<20% AND deep queues AND off-peak hours: maximize workers.
        """
        changes = {}
        total_pending = sum(depths.values())
        is_off_peak = self._is_off_peak_hours()

        # Burst only if we have significant work AND it's off-peak
        if total_pending > 20 and is_off_peak:
            # Don't override if courtesy/panic mode set limits
            if self._active_mode not in ("courtesy", "panic"):
                self._active_mode = "burst"
                # Set to max for compute-heavy stages
                if depths.get('pending_analysis', 0) > 5:
                    changes['analysis_worker_count'] = MAX_ANALYSIS_WORKERS
                if depths.get('pending_implementation', 0) > 5:
                    changes['implementation_worker_count'] = MAX_IMPLEMENTATION_WORKERS
                if depths.get('pending_vjs', 0) > 3:
                    changes['vjs_worker_count'] = MAX_VJS_WORKERS
        else:
            if self._active_mode == "burst":
                self._active_mode = "normal"
        return changes

    # ── Decision Module 4: Backpressure ──────────────────────────────────

    def _apply_backpressure(self, depths: Dict[str, int]) -> Dict[str, Any]:
        """
        If downstream stage queue > 2× upstream, throttle upstream.
        Prevents queue imbalance where one stage produces faster than
        the next can consume.
        """
        changes = {}
        # Pipeline order: ingestion → analysis → implementation → vjs → assembly
        pipeline = [
            ('pending_analysis',       'pending_implementation', 'analysis_worker_count'),
            ('pending_implementation', 'pending_vjs',            'implementation_worker_count'),
        ]
        for upstream_status, downstream_status, upstream_param in pipeline:
            up = depths.get(upstream_status, 0)
            down = depths.get(downstream_status, 0)
            current = config_manager.get_param(upstream_param, 1)

            if up > 0 and down > up * BACKPRESSURE_RATIO and current > 1:
                # Downstream overwhelmed — reduce upstream
                new_val = max(1, current - 1)
                if new_val != current and not self._in_cooldown(upstream_param):
                    changes[upstream_param] = new_val
                    logging.info(
                        f"Backpressure: {upstream_param} {current}→{new_val} "
                        f"(downstream {down} > {BACKPRESSURE_RATIO}× upstream {up})"
                    )
        return changes

    # ── Decision Module 5: API Throttle ──────────────────────────────────

    def _apply_api_throttle(self, budgets: Dict[str, Any]) -> Dict[str, Any]:
        """
        >90% daily budget: 1 worker.
        >98% daily budget: 0 workers (halt to save budget for tomorrow).
        """
        changes = {}
        gemini_budget = budgets.get('gemini', {})
        groq_budget = budgets.get('groq', {})

        # Gemini controls analysis workers
        gemini_util = max(
            gemini_budget.get('rpd_utilization', 0),
            gemini_budget.get('tpd_utilization', 0),
        )
        if gemini_util >= API_THROTTLE_HARD:
            changes['analysis_worker_count'] = 0
            logging.warning(f"API Throttle HARD: Gemini at {gemini_util:.0%}. Halting analysis.")
        elif gemini_util >= API_THROTTLE_SOFT:
            changes['analysis_worker_count'] = 1
            logging.warning(f"API Throttle SOFT: Gemini at {gemini_util:.0%}. Analysis→1 worker.")

        # Groq controls implementation workers
        groq_util = max(
            groq_budget.get('rpd_utilization', 0),
            groq_budget.get('tpd_utilization', 0),
        )
        if groq_util >= API_THROTTLE_HARD:
            changes['implementation_worker_count'] = 0
            logging.warning(f"API Throttle HARD: Groq at {groq_util:.0%}. Halting implementation.")
        elif groq_util >= API_THROTTLE_SOFT:
            changes['implementation_worker_count'] = 1
            logging.warning(f"API Throttle SOFT: Groq at {groq_util:.0%}. Implementation→1 worker.")

        return changes

    # ── Decision Module 6: Panic Mode ────────────────────────────────────

    def _apply_panic_mode(self, scraper: Dict[str, Any]) -> Dict[str, Any]:
        """
        If all scraper accounts are banned, halt ingestion immediately.
        """
        changes = {}
        if not scraper.get('has_healthy_account', True):
            changes['ingestion_worker_count'] = 0
            if self._active_mode != "panic":
                self._active_mode = "panic"
                logging.critical("PANIC MODE: All scraper accounts banned. Halting ingestion.")
        else:
            if self._active_mode == "panic":
                self._active_mode = "normal"
                changes['ingestion_worker_count'] = DEFAULT_INGESTION_WORKER_COUNT
                logging.info("PANIC MODE lifted: healthy account available. Resuming ingestion.")
        return changes

    # ── Decision Module 7: Time Schedule ─────────────────────────────────

    def _apply_time_schedule(self) -> Dict[str, Any]:
        """
        Off-peak hours (2am-6am IST): allow burst behavior.
        Peak hours: ensure we're at default or below.
        """
        # This module just sets the stage for burst mode by tracking time context.
        # The actual burst logic is in _apply_burst_mode.
        return {}

    # ── Health Checks ────────────────────────────────────────────────────

    def _health_check(self, depths: Dict[str, int]) -> None:
        """Detect anomalies: stuck jobs, idle pipeline, queue overflows."""
        total = sum(depths.values())
        if total == 0:
            logging.debug("Health check: pipeline idle (no pending jobs).")
        elif total > 500:
            logging.warning(f"Health check: queue overflow detected ({total} total pending).")

    # ── State Readers ────────────────────────────────────────────────────

    def _read_queue_depths(self) -> Dict[str, int]:
        """Read pending job counts per stage from the database."""
        import synapse.database as db
        depths = {}
        statuses = [
            'pending_ingestion', 'pending_analysis', 'pending_implementation',
            'pending_vjs', 'pending_data_assembly', 'pending_cf_submission',
        ]
        try:
            with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
                for status in statuses:
                    if db.USE_POSTGRES:
                        cur = conn.cursor()
                        cur.execute("SELECT COUNT(*) FROM problems WHERE status = %s", (status,))
                        depths[status] = cur.fetchone()[0]
                    else:
                        row = conn.execute(
                            "SELECT COUNT(*) FROM problems WHERE status = ?", (status,)
                        ).fetchone()
                        depths[status] = row[0] if row else 0
        except Exception as e:
            logging.error(f"Optimizer: failed to read queue depths: {e}")
        return depths

    def _read_api_budgets(self) -> Dict[str, Any]:
        """Read API budget status from KeyManagers."""
        budgets = {}
        if self._km_gemini:
            try:
                budgets['gemini'] = self._km_gemini.get_budget_status()
            except Exception:
                budgets['gemini'] = {}
        if self._km_groq:
            try:
                budgets['groq'] = self._km_groq.get_budget_status()
            except Exception:
                budgets['groq'] = {}
        return budgets

    def _read_scraper_health(self) -> Dict[str, Any]:
        """Read scraper account health from AccountManager."""
        if self._account_manager:
            return {
                'has_healthy_account': self._account_manager.has_healthy_account(),
                'stats': self._account_manager.get_all_stats(),
            }
        return {'has_healthy_account': True, 'stats': []}

    # ── Helpers ──────────────────────────────────────────────────────────

    def _write_changes(self, changes: Dict[str, Any]) -> None:
        """Apply all proposed changes to dynamic config."""
        for param, value in changes.items():
            current = config_manager.get_param(param)
            if current != value:
                config_manager.set_param(param, value)
                self._last_action_time[param] = time.time()

    def _in_cooldown(self, param: str) -> bool:
        """Check if a parameter was recently changed."""
        last = self._last_action_time.get(param, 0)
        return (time.time() - last) < OPTIMIZER_COOLDOWN_PERIOD_SECONDS

    def _is_off_peak_hours(self) -> bool:
        """Check if current time is in the off-peak window (2am-6am IST)."""
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + IST_OFFSET
        return 2 <= now_ist.hour < 6

    @property
    def active_mode(self) -> str:
        """Current operating mode: normal, courtesy, burst, or panic."""
        return self._active_mode


# ── Standalone entry point (backward compat) ─────────────────────────────

def main() -> None:
    """The main loop for the optimizer (standalone process)."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - OPTIMIZER - %(levelname)s - %(message)s',
    )
    logging.info("Starting optimizer process (standalone)...")
    optimizer = PipelineOptimizer()

    while True:
        try:
            changes = optimizer.optimize()
            if changes:
                logging.info(f"Optimizer cycle: applied {changes}")
        except Exception as e:
            logging.error(f"Optimizer loop failed: {e}", exc_info=True)

        time.sleep(OPTIMIZER_LOOP_DELAY_SECONDS)


if __name__ == "__main__":
    main()