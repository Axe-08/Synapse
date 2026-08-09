# Test Plan & Debugging Guide — Project Synapse v2.0

**Version:** 2.0  
**Date:** March 2026  
**Author:** Axe-08

---

## Table of Contents

1. [Test Architecture Overview](#1-test-architecture-overview)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Tier 1: Unit Tests](#3-tier-1-unit-tests)
4. [Tier 2: Integration Tests](#4-tier-2-integration-tests)
5. [Tier 3: Contract Tests](#5-tier-3-contract-tests)
6. [Tier 4: End-to-End Tests](#6-tier-4-end-to-end-tests)
7. [Tier 5: Runtime Health Checks](#7-tier-5-runtime-health-checks)
8. [Debugging Toolkit](#8-debugging-toolkit)
9. [Test Data & Fixtures](#9-test-data--fixtures)
10. [CI/CD Integration](#10-cicd-integration)
11. [Coverage Goals](#11-coverage-goals)

---

## 1. Test Architecture Overview

### Test Pyramid

```
                    ╔═══════════╗
                    ║   E2E     ║  2 tests — real API calls (manual)
                    ║  (Smoke)  ║  Skip if no keys
                    ╠═══════════╣
                ╔═══╩═══════════╩═══╗
                ║   Contract Tests  ║  ~10 tests — schema validation
                ║ (Gemini/Groq/CF)  ║  JSON schemas, response parsing
                ╠═══════════════════╣
            ╔═══╩═══════════════════╩═══╗
            ║   Integration Tests       ║  ~40 tests — workers with mocked APIs
            ║ (Worker → DB → Routing)   ║  Real SQLite, mocked externals
            ╠═══════════════════════════╣
        ╔═══╩═══════════════════════════╩═══╗
        ║       Unit Tests                  ║  ~100 tests — pure function logic
        ║ (Database, KeyManager, Optimizer,  ║  Temp DBs, no network, no Docker
        ║  AccountManager, Checker, etc.)   ║
        ╚═══════════════════════════════════╝
```

### Dual-Backend Testing Strategy

Every database test runs against **both backends** automatically:

```python
@pytest.fixture(params=["sqlite", "postgres"])
def db_backend(request, tmp_path):
    if request.param == "postgres":
        pytest.importorskip("psycopg2")
        # Use test PostgreSQL container
        yield postgres_test_connection()
    else:
        yield sqlite_test_connection(tmp_path)
```

PostgreSQL tests are skipped when Docker is not available (CI-safe).

---

## 2. Test Environment Setup

### Dependencies

```bash
pip install pytest pytest-cov pytest-mock pytest-timeout pytest-xdist
```

### Running Tests

```bash
# All unit tests (fast, no deps)
pytest tests/unit/ -m unit -v

# All integration tests (mocked APIs)
pytest tests/integration/ -m integration -v

# PostgreSQL backend tests only (requires Docker)
pytest tests/ -m postgres -v

# E2E tests (requires real API keys)
GEMINI_API_KEYS=... GROQ_API_KEYS=... pytest tests/e2e/ -m e2e -s

# Full suite with coverage
pytest tests/ --cov=synapse --cov-report=term-missing

# Parallel execution (faster)
pytest tests/unit/ -n auto
```

### Test PostgreSQL Setup

```bash
# Start test PostgreSQL container
docker run -d --name synapse-test-pg \
  -e POSTGRES_USER=synapse_test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=synapse_test_db \
  -p 5433:5432 \
  postgres:16

# Tests auto-detect via TEST_DATABASE_URL env var
export TEST_DATABASE_URL="postgresql://synapse_test:test@localhost:5433/synapse_test_db"
```

---

## 3. Tier 1: Unit Tests

### 3.1 Database Adapter (`test_database.py`)

**Existing (16 tests) + New (24 tests) = 40 tests**

| Test Class | Tests | New? | Focus |
|-----------|-------|------|-------|
| `TestGetNextJobs` | 4 | ❌ | Empty result, correct status, limit, locking |
| `TestGetNextJobsPriority` | 4 | ✅ | Higher priority first, equal priority → lower rating first, priority+rating ordering |
| `TestGetNextJobsPostgres` | 4 | ✅ | `FOR UPDATE SKIP LOCKED`, `ANY(%s)`, placeholder conversion |
| `TestStatusTransitions` | 14 | partial | All transitions + **retry increments priority** |
| `TestPriorityIncrement` | 3 | ✅ | `transition_to_pending_implementation_retry` increments priority, `transition_to_pending_analysis_retry` increments priority, max priority cap |
| `TestProblemClass` | 4 | ✅ | Store/retrieve `problem_class`, filter by class, default value |
| `TestScraperStats` | 3 | ✅ | Insert events, query by account, query by time window |
| `TestDgxUsageStats` | 2 | ✅ | Insert snapshot, query by hour/weekday |
| `TestWorkerStatus` | 1 | ❌ | Insert/update without error |
| `TestLogMetric` | 1 | ❌ | Insert row with correct fields |

```python
# Example: Priority ordering test
class TestGetNextJobsPriority:
    def test_higher_priority_comes_first(self, db_backend):
        """Problems with higher retry priority should be fetched first."""
        # Insert: problem A (priority=0, rating=1500), problem B (priority=3, rating=1800)
        insert_problems([
            {"id": "A", "priority": 0, "rating": 1500, "status": "pending_analysis"},
            {"id": "B", "priority": 3, "rating": 1800, "status": "pending_analysis"},
        ])
        jobs = db.get_next_jobs("pending_analysis", limit=2)
        assert jobs[0]["id"] == "B"  # higher priority
        assert jobs[1]["id"] == "A"

    def test_same_priority_lower_rating_first(self, db_backend):
        """Equal priority → lower-rated (easier) problems first."""
        insert_problems([
            {"id": "A", "priority": 0, "rating": 2000, "status": "pending_analysis"},
            {"id": "B", "priority": 0, "rating": 800, "status": "pending_analysis"},
        ])
        jobs = db.get_next_jobs("pending_analysis", limit=2)
        assert jobs[0]["id"] == "B"  # lower rating
```

### 3.2 KeyManager Budget Tracking (`test_key_manager.py`)

**Existing (12 tests) + New (15 tests) = 27 tests**

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestKeyManagerBasic` | 5 | get_key, round-robin, key_string |
| `TestReleaseKey` | 4 | success, rate_limited, exhausted |
| `TestEdgeCases` | 4 | empty list, service config |
| `TestBudgetTracking` | 6 | ✅ `log_usage`, `tokens_today` accumulation, `requests_today` count, midnight reset |
| `TestBudgetStatus` | 4 | ✅ `get_budget_status()` returns correct remaining, `should_throttle()` at 80%/90%/98% thresholds |
| `TestRateLimitHeaders` | 5 | ✅ Parse Groq `x-ratelimit-remaining-*` headers, update internal counters from server response |

```python
class TestBudgetTracking:
    def test_log_usage_accumulates_tokens(self):
        km = KeyManager(["k1"], "GEMINI", limits={"tpd": 2_500_000})
        key = km.get_key()
        km.log_usage(key, tokens_in=1000, tokens_out=500)
        km.release_key(key, KeyStatus.AVAILABLE)
        status = km.get_budget_status()
        assert status["tokens_today"] == 1500
        assert status["tpd_remaining"] == 2_498_500

    def test_should_throttle_at_90_percent(self):
        km = KeyManager(["k1"], "GEMINI", limits={"tpd": 100})
        key = km.get_key()
        km.log_usage(key, tokens_in=85, tokens_out=6)  # 91 tokens = 91%
        km.release_key(key, KeyStatus.AVAILABLE)
        assert km.should_throttle() == True
```

### 3.3 Account Manager (`test_account_manager.py`) — NEW

**15 tests**

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestAccountRotation` | 4 | Round-robin, skip banned, skip cooling, all-banned returns None |
| `TestBanManagement` | 4 | `mark_banned` sets cooldown, `mark_unbanned` clears it, automatic expiry, ban count increment |
| `TestSafeRateCalc` | 3 | Calculate from history, no bans → unlimited, multiple bans → conservative |
| `TestTelemetryLogging` | 4 | Log scrape_success, log ban_detected, query per-account stats, safe_request_rate calculation |

```python
class TestAccountRotation:
    def test_skips_banned_account(self):
        am = AccountManager([
            {"handle": "AXE08", "password": "p1"},
            {"handle": "ProjectSynapse", "password": "p2"},
        ])
        am.mark_banned("AXE08")
        account = am.get_active_account()
        assert account.handle == "ProjectSynapse"

    def test_all_banned_returns_none(self):
        am = AccountManager([{"handle": "AXE08", "password": "p1"}])
        am.mark_banned("AXE08")
        assert am.get_active_account() is None
```

### 3.4 Optimizer Decision Rules (`test_optimizer.py`) — NEW

**25 tests** — Each decision rule tested independently

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestStageSkipping` | 3 | Empty queue → 0 workers, non-empty → restore, multiple empty stages |
| `TestCourtesyMode` | 3 | CPU > 70% → halve workers, CPU < 70% → no change, CPU > 90% → minimum workers |
| `TestBurstMode` | 3 | CPU < 20% + deep queue → max workers, CPU < 20% + shallow queue → moderate, only during low-usage hours |
| `TestBackpressure` | 4 | VJS > 2× analysis → throttle analysis, balanced queues → no change, backpressure release when normalized, cascading backpressure |
| `TestAPIThrottle` | 4 | 90% TPD → 1 worker, 98% TPD → 0 workers, 80% RPM → pause 10s, budget OK → no change |
| `TestPanicMode` | 3 | Ban detected → ingestion=0, no ban → no panic, recovery after cooldown |
| `TestTimeSchedule` | 3 | Off-peak hours → allow burst, peak hours → cap workers, weekend → allow burst |
| `TestCooldown` | 2 | Action within cooldown → skip, action after cooldown → allowed |

```python
class TestBackpressure:
    def test_throttles_analysis_when_vjs_overloaded(self):
        """VJS queue > 2× upstream → throttle analysis."""
        opt = PipelineOptimizer(cfg=mock_cfg)
        depths = {"pending_analysis": 5, "pending_implementation": 8, "pending_vjs": 40}
        changes = opt._apply_backpressure(depths)
        assert changes["analysis_worker_count"] < 4  # reduced from default

    def test_no_backpressure_when_balanced(self):
        opt = PipelineOptimizer(cfg=mock_cfg)
        depths = {"pending_analysis": 10, "pending_implementation": 8, "pending_vjs": 12}
        changes = opt._apply_backpressure(depths)
        assert changes == {}  # no changes needed
```

### 3.5 Checker (`test_checker.py`) — NEW

**12 tests**

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestStrictMode` | 4 | Exact match, trailing whitespace tolerance, trailing newline, case sensitivity |
| `TestSetBasedMode` | 4 | Order-independent, duplicate handling, subset mismatch, empty sets |
| `TestEdgeCases` | 4 | Empty output, very large output, floating point tolerance, multi-line |

### 3.6 Config Manager (`test_config_manager.py`) — NEW

**8 tests**

| Test Class | Tests | Focus |
|-----------|-------|-------|
| `TestSingleton` | 2 | Same instance, thread-safe creation |
| `TestGetSetParam` | 3 | Get existing, get default, set and retrieve |
| `TestSyncFromDB` | 3 | Loads all keys, handles missing table gracefully, reflects DB changes |

---

## 4. Tier 2: Integration Tests

### 4.1 Worker Integration Tests

Each worker is tested with **mocked external services** but **real database operations**.

#### `test_ingestion_worker.py` — NEW (8 tests)

| Test | Mocked | Asserts |
|------|--------|---------|
| `test_happy_path_standard_problem` | CF HTTP responses | Data saved to workspace, status → pending_calibration, telemetry logged |
| `test_happy_path_interactive_problem` | CF with type=INTERACTIVE | `problem_class` set to "interactive" |
| `test_ip_ban_handling` | CF returns "blocked" | IPBanException raised, `scraper_stats` ban event logged |
| `test_account_rotation_on_ban` | Ban on first account | Second account used, first marked cooling |
| `test_pretest_enrichment` | CF Internal API | Full pretests stored in workspace |
| `test_rescraping_with_new_submissions` | Second CF scrape | New submission IDs, `tried_submission_ids` updated |
| `test_quarantine_interactive` | CF with type=INTERACTIVE, old v1 behavior | Problem quarantined (backward compat) |
| `test_telemetry_logged_per_scrape` | Normal CF scrape | `scraper_stats` row for account/timestamp |

#### `test_calibration_worker.py` — NEW (6 tests)

| Test | Mocked | Asserts |
|------|--------|---------|
| `test_happy_path_all_oracles_compile` | Docker subprocess (all OK) | compiled_paths, slowness_factor, status → pending_analysis |
| `test_min_oracles_threshold` | Docker (2/5 compile) | Quarantined — fewer than MIN_VIABLE_ORACLES |
| `test_oracle_crash_filter_discards_bad_pretests` | Docker (oracle crashes on test 3) | Pretest 3 removed from validated_pretests |
| `test_oracle_disagree_discards_pretest` | Docker (oracles return different outputs on test 2) | Pretest 2 removed |
| `test_set_based_detection` | Docker (PRESENTATION_ERROR pattern) | `checker_mode = 'set_based'` |
| `test_slowness_factor_calculation` | Docker (oracle runs in 1.5s, limit is 2s) | `slowness_factor` ≈ 1.5/2 = 0.75 |

#### `test_analysis_worker.py` — Expanded (5 existing + 5 new = 10 tests)

| Test | New? | Focus |
|------|------|-------|
| `test_happy_path_batch` | ❌ | Batch of 5, all succeed, pseudocode stored |
| `test_partial_batch_failure` | ❌ | 3/5 succeed, 2 quarantined |
| `test_retry_with_vjs_report` | ❌ | VJS failure report included in prompt |
| `test_quarantine_on_max_retries` | ❌ | analysis_try_count ≥ 3 → quarantined |
| `test_rescraping_redirect` | ❌ | Max retries + rescraping attempts remaining → pending_rescraping |
| `test_structured_output_schema` | ✅ | Response includes `input_generator_py` field |
| `test_problem_class_in_prompt` | ✅ | Prompt context includes problem_class, rating, tags |
| `test_batch_includes_correct_oracle_count` | ✅ | Top 3 oracles selected per problem |
| `test_priority_incremented_on_retry` | ✅ | Retry transition bumps priority |
| `test_gemini_budget_logged` | ✅ | `km.log_usage()` called with token counts |

#### `test_vjs_worker.py` — Expanded (4 existing + 6 new = 10 tests)

| Test | New? | Focus |
|------|------|-------|
| `test_passes_to_data_assembly_on_all_correct` | ❌ | Oracle consensus + AI pass → data_assembly |
| `test_compile_failure_retries_implementation` | ❌ | g++ fail → pending_implementation |
| `test_oracle_runtime_error_triggers_quarantine` | ❌ | All oracles crash → quarantined |
| `test_missing_workspace_data_transitions_to_failed` | ❌ | No workspace row → failed_vjs |
| `test_fuzz_generator_runs_and_adds_tests` | ✅ | Generator script produces inputs, oracles validate, combined suite |
| `test_fuzz_generator_discards_crash_inputs` | ✅ | Input where oracle crashes → excluded from suite |
| `test_fuzz_generator_discards_disagree_inputs` | ✅ | Input where oracles disagree → excluded |
| `test_combined_suite_includes_both_sources` | ✅ | pretests + generated tests in final suite |
| `test_wrong_answer_includes_test_diff` | ✅ | Failure report has expected vs actual diff |
| `test_confidence_level_set_on_pass` | ✅ | `confidence_level = 2` after VJS pass |

#### `test_cf_submission_worker.py` — NEW (8 tests)

| Test | Mocked | Asserts |
|------|--------|---------|
| `test_accepted_transitions_to_data_assembly` | CF verdict: Accepted | status → pending_data_assembly |
| `test_wrong_answer_routes_to_analysis` | CF verdict: WA test 5 | status → pending_analysis, feedback includes test 5 |
| `test_tle_routes_to_implementation` | CF verdict: TLE test 3 | status → pending_implementation, complexity hint |
| `test_compile_error_routes_to_implementation` | CF verdict: CE | status → pending_implementation, stderr |
| `test_timeout_quarantines` | 5 min poll timeout | status → quarantined |
| `test_account_rotation` | Selenium submit | Round-robin through submission accounts |
| `test_rate_limit_respected` | Timer mock | No more than 10/hr/account |
| `test_submission_account_recorded` | CF submit OK | `submission_account` column set |

#### `test_optimizer.py` (Integration) — NEW (6 tests)

| Test | Focus |
|------|-------|
| `test_full_cycle_reads_all_inputs` | Optimizer reads queue + CPU + API + scraper in one cycle |
| `test_writes_updated_config` | dynamic_config table values change after optimize() |
| `test_logs_usage_snapshot` | dgx_usage_stats row inserted |
| `test_respects_cooldown_between_actions` | No same-param change within cooldown |
| `test_multiple_rules_compose_correctly` | Backpressure + API throttle both active → picks most restrictive |
| `test_health_check_detects_stuck_jobs` | Job in_progress > 30min → warning logged |

### 4.2 Database Writer Integration (`test_database_writer.py`) — NEW (6 tests)

| Test | Focus |
|------|-------|
| `test_sqlite_worker_loop` | Writes complete and are visible |
| `test_pg_worker_loop` | Writes to PostgreSQL with `%s` placeholders |
| `test_pg_rollback_on_error` | Bad SQL → rollback, queue continues |
| `test_queue_drains_on_stop` | Stop signal → remaining items processed |
| `test_concurrent_writes` | 100 writes from 10 threads → all committed |
| `test_backend_selection_by_env` | DATABASE_URL set → PG, unset → SQLite |

---

## 5. Tier 3: Contract Tests

### 5.1 Gemini Structured Output Schema

```python
class TestGeminiSchema:
    def test_schema_contains_required_fields(self):
        """Our schema must include pseudocode, input_generator_py, oracle_quality_ratings."""
        schema = get_gemini_response_schema()
        assert "pseudocode" in schema["properties"]
        assert "input_generator_py" in schema["properties"]
        assert "oracle_quality_ratings" in schema["properties"]

    def test_sample_response_validates(self):
        """A well-formed response passes schema validation."""
        sample = {
            "pseudocode": "Read n integers, print sum",
            "input_generator_py": "import random\nn=random.randint(1,100)\nprint(n)\nprint(*[random.randint(1,1000) for _ in range(n)])",
            "oracle_quality_ratings": [
                {"oracle_id": "oracle_0", "rating": "Excellent"},
                {"oracle_id": "oracle_1", "rating": "Good"},
            ]
        }
        validate(sample, get_gemini_response_schema())  # no exception

    def test_malformed_response_caught(self):
        """Missing required field is detected."""
        bad = {"pseudocode": "...", "oracle_quality_ratings": []}
        with pytest.raises(ValidationError):
            validate(bad, get_gemini_response_schema())
```

### 5.2 Groq Response Parsing

```python
class TestGroqResponseParsing:
    def test_strips_cpp_markdown(self):
        raw = "```cpp\n#include<iostream>\nint main(){}\n```"
        assert "#include<iostream>" in _sanitize_cpp_code(raw)

    def test_strips_plain_markdown(self):
        raw = "```\n#include<iostream>\n```"
        assert "```" not in _sanitize_cpp_code(raw)

    def test_handles_no_markdown(self):
        raw = "#include<iostream>\nint main(){}"
        assert _sanitize_cpp_code(raw) == raw

    def test_handles_explanation_before_code(self):
        raw = "Here is my solution:\n```cpp\n#include<bits/stdc++.h>\nint main(){}\n```\nThis should work."
        result = _sanitize_cpp_code(raw)
        assert "Here is my solution" not in result
        assert "#include" in result
```

### 5.3 Fuzz Generator Output Validation

```python
class TestFuzzGeneratorOutput:
    def test_generator_produces_valid_input(self):
        """Generated script must produce text that oracles can accept."""
        generator_py = "import random\nn=random.randint(1,10)\nprint(n)\nprint(*[random.randint(1,100) for _ in range(n)])"
        output = run_generator(generator_py, timeout=5)
        # Must be parseable: first line is int, second line is space-separated ints
        lines = output.strip().split("\n")
        n = int(lines[0])
        nums = list(map(int, lines[1].split()))
        assert len(nums) == n

    def test_generator_timeout_handled(self):
        """Infinite loop generator is killed after timeout."""
        bad_generator = "while True: pass"
        with pytest.raises(TimeoutError):
            run_generator(bad_generator, timeout=2)
```

---

## 6. Tier 4: End-to-End Tests

### 6.1 Existing E2E Tests (2 tests)

| Test | Requires | Purpose |
|------|----------|---------|
| `test_analysis_worker_real_api` | `GEMINI_API_KEYS` | Real Gemini call → pseudocode returned |
| `test_implementation_worker_real_api` | `GROQ_API_KEYS` | Real Groq call → C++ code returned |

### 6.2 New E2E Tests (4 tests)

| Test | Requires | Purpose |
|------|----------|---------|
| `test_analysis_returns_generator_script` | `GEMINI_API_KEYS` | Gemini structured output includes `input_generator_py` |
| `test_vjs_full_pipeline_with_docker` | Docker running | Compile + run oracle + compile AI code + checker |
| `test_priority_queue_ordering_pg` | Docker + PG | Insert 10 problems with varying priority → correct fetch order |
| `test_optimizer_full_cycle` | Docker + PG | Insert metrics + queue data → optimizer produces sensible config |

---

## 7. Tier 5: Runtime Health Checks

These run **inside the live pipeline**, not in pytest.

### 7.1 Optimizer Health Checks

```python
def _health_check(self):
    """Run every optimizer cycle to detect anomalies."""

    # 1. Stuck Jobs Detection
    stuck_jobs = get_jobs_by_condition(
        "status LIKE 'in_progress_%' AND last_updated < ?",
        (thirty_minutes_ago,)
    )
    if stuck_jobs:
        logging.warning(f"HEALTH: {len(stuck_jobs)} stuck jobs (in_progress > 30min)")
        for job in stuck_jobs:
            # Reset to pending state so they get retried
            transition_to_failed(job["id"], extract_stage(job["status"]), "stuck_timeout")

    # 2. Zombie Worker Detection
    zombies = get_workers_by_condition(
        "status = 'active' AND last_heartbeat < ?",
        (five_minutes_ago,)
    )
    if zombies:
        logging.warning(f"HEALTH: {len(zombies)} zombie workers")
        for z in zombies:
            update_worker_status(z["worker_id"], z["pool"], None, None, "idle")

    # 3. Orphaned Workspace Entries
    orphans = query("""
        SELECT w.problem_id FROM workspace.problem_data_cache w
        LEFT JOIN progress.problems p ON w.problem_id = p.id
        WHERE p.id IS NULL
    """)
    if orphans:
        logging.warning(f"HEALTH: {len(orphans)} orphaned workspace entries")

    # 4. API Budget Warning
    for service in ["gemini", "groq"]:
        status = self._km[service].get_budget_status()
        if status["tpd_remaining"] < status["tpd_limit"] * 0.1:
            logging.warning(f"HEALTH: {service} API budget < 10% remaining")

    # 5. Scraper Account Exhaustion
    active_accounts = [a for a in self._account_mgr.accounts if a.status == "ACTIVE"]
    if len(active_accounts) == 0:
        logging.error("HEALTH: ALL scraper accounts are banned/cooling!")
```

### 7.2 Data Quality Assertions

```python
# Run after every data assembly:
def _validate_golden_record(record: dict) -> list[str]:
    """Return list of quality warnings for a golden record."""
    warnings = []
    if not record.get("pseudocode"):
        warnings.append("missing pseudocode")
    if not record.get("reconstructed_code"):
        warnings.append("missing reconstructed code")
    if "include" not in record.get("reconstructed_code", ""):
        warnings.append("reconstructed code may not be valid C++")
    if not record.get("pretests") or len(record["pretests"]) == 0:
        warnings.append("no pretests in golden record")
    if record.get("confidence_level", 0) < 2:
        warnings.append(f"low confidence: {record.get('confidence_level')}")
    return warnings
```

---

## 8. Debugging Toolkit

### 8.1 Command-Line Debug Tools

| Tool | Command | Purpose |
|------|---------|---------|
| `debug_problem.py` | `python debug_problem.py 1234A` | Full state dump for a single problem |
| `inspect_queue.py` | `python inspect_queue.py` | Queue depths + problematic jobs per stage |
| `replay_stage.py` | `python replay_stage.py 1234A analysis` | Re-run a stage with verbose logging |
| `check_api_budget.py` | `python check_api_budget.py` | API usage vs limits per key |
| `scraper_health.py` | `python scraper_health.py` | Account health: bans, rates, cooldowns |
| `validate_dataset.py` | `python validate_dataset.py` | Scan dataset for quality issues |

### 8.2 `debug_problem.py` — Detailed Design

```
$ python debug_problem.py 1847F

═══ PROBLEM 1847F ═══

Status:     quarantined
Rating:     2200
Class:      standard
Priority:   7
Confidence: 1 (calibrated, not VJS-verified)

Retry Counts:
  analysis_try: 3/3 (EXHAUSTED)
  impl_try:     2/5
  rescraping:   0/1

Notes: "VJS consensus failed: 0/3 oracles agree on test 4"

Last VJS Report:
  Oracle 0 (Excellent): output="YES\n"
  Oracle 1 (Good):      output="NO\n"
  Oracle 2 (Fair):      TIMEOUT after 2000ms

Timeline (process_history):
  [2026-03-02 14:32:01] INGESTION → SUCCESS (scraped 5 oracles)
  [2026-03-02 14:32:45] CALIBRATION → SUCCESS (3/5 compiled, slowness=2.1)
  [2026-03-02 14:33:12] ANALYSIS → SUCCESS (try 1)
  [2026-03-02 14:33:45] IMPLEMENTATION → SUCCESS (try 1)
  [2026-03-02 14:34:20] VJS → FAILURE (WA on test 3)
  [2026-03-02 14:34:21] → pending_analysis (priority bumped to 3)
  [2026-03-02 14:35:00] ANALYSIS → SUCCESS (try 2, with WA feedback)
  [2026-03-02 14:35:30] IMPLEMENTATION → SUCCESS (try 2)
  [2026-03-02 14:36:00] VJS → FAILURE (consensus: 0/3 agree on test 4)
  [2026-03-02 14:36:01] → pending_analysis (priority bumped to 5)
  [2026-03-02 14:37:00] ANALYSIS → SUCCESS (try 3, with consensus report)
  [2026-03-02 14:37:30] IMPLEMENTATION → FAILURE (try 3, compile error)
  [2026-03-02 14:37:31] → pending_implementation (priority bumped to 7)
  [2026-03-02 14:38:00] IMPLEMENTATION → SUCCESS (try 4)
  [2026-03-02 14:38:30] VJS → QUARANTINED (max analysis retries)

Workspace Cache:
  HTML:          ✅ (2.3 KB)
  Oracles:       3 compiled paths
  Pretests:      8 validated (12 scraped, 4 crash-filtered)
  Pseudocode:    ✅ (v3 — after 2 retries)
  Generator:     ✅ (input_generator_py present)
  Generated:     15 tests (20 generated, 5 discarded)
  Reconstructed: ✅ (v4 — after compile fix)
```

### 8.3 `replay_stage.py` — Re-run Failed Stages

```bash
# Re-run analysis for a quarantined problem with debug logging
$ python replay_stage.py 1847F analysis --verbose --dry-run

[REPLAY] Loading workspace data for 1847F...
[REPLAY] Problem class: standard, rating: 2200
[REPLAY] Using oracle codes: oracle_0 (Excellent), oracle_1 (Good), oracle_2 (Fair)
[REPLAY] Last VJS report included in prompt: YES
[REPLAY] --- Gemini Prompt (preview) ---
[REPLAY] ... (truncated, full prompt logged to replay_1847F.log)
[REPLAY] --- DRY RUN: Would call Gemini API here ---
[REPLAY] Set --live to actually make the API call
```

### 8.4 `validate_dataset.py` — Dataset Quality Scanner

```
$ python validate_dataset.py

═══ DATASET VALIDATION ═══

Records:           127
Unique problems:   127 (0 duplicates)
Rating range:      800 — 2400

Field completeness:
  problem_id:         127/127 ✅
  pseudocode:         127/127 ✅
  reconstructed_code: 127/127 ✅
  pretests:           127/127 ✅ (avg 6.3 tests/problem)
  fuzz_test_count:     89/127 ⚠️  (38 have 0 — pre-generator problems)
  confidence_level:   127/127 ✅ (all = 2)

Quality flags:
  ⚠️  3 records have reconstructed code < 50 bytes (suspiciously short)
  ⚠️  1 record has pseudocode == "N/A" (should have been blocked)

SHA256 integrity: All 127 records have unique dedup hashes ✅
```

---

## 9. Test Data & Fixtures

### 9.1 Shared Fixtures (`conftest.py` updates for v2)

New fixtures needed:

```python
# --- New tables in schema ---
PROGRESS_SCHEMA += """
CREATE TABLE IF NOT EXISTS scraper_stats (...);
CREATE TABLE IF NOT EXISTS dgx_usage_stats (...);
"""

WORKSPACE_SCHEMA → add input_generator_py, generated_tests_json columns

# --- New fixtures ---
@pytest.fixture
def sample_classified_problem(tmp_progress_db):
    """Problem with problem_class set."""
    ...

@pytest.fixture
def sample_interactive_problem(tmp_progress_db):
    """Interactive problem that should route to CF submission."""
    ...

@pytest.fixture
def mock_account_manager():
    """AccountManager with 2 test accounts."""
    ...

@pytest.fixture
def mock_optimizer_inputs():
    """Pre-configured optimizer inputs for testing decision rules."""
    ...

@pytest.fixture(scope="session")
def postgres_container():
    """Session-scoped PostgreSQL test container."""
    ...
```

### 9.2 Canned CF Responses

```python
# tests/fixtures/cf_responses.py
STANDARD_PROBLEM_HTML = """..."""
INTERACTIVE_PROBLEM_HTML = """..."""
SPECIAL_JUDGE_PROBLEM_HTML = """..."""
CONSTRUCTIVE_PROBLEM_HTML = """..."""

CONTEST_STATUS_RESPONSE = {
    "status": "OK",
    "result": [
        {"id": 123456, "verdict": "OK", "programmingLanguage": "GNU C++20 (64)"},
        ...
    ]
}
```

---

## 10. CI/CD Integration

### pytest.ini Configuration

```ini
[pytest]
markers =
    unit: Unit tests (no external deps)
    integration: Integration tests (mocked APIs, real DB)
    postgres: Tests requiring PostgreSQL (Docker)
    e2e: End-to-end tests (real API keys required)
    slow: Tests that take > 10 seconds

testpaths = tests
addopts = --strict-markers -v --tb=short
```

### Recommended CI Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Unit Tests  │────▶│ Integration │────▶│  PG Tests   │
│  (always)    │     │  (always)   │     │ (if Docker) │
│  ~30 sec     │     │  ~2 min     │     │  ~3 min     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  E2E Tests  │
                                        │ (manual/    │
                                        │  nightly)   │
                                        └─────────────┘
```

---

## 11. Coverage Goals

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `database.py` | ~50% | 90% | 🔴 P0 |
| `key_manager.py` | ~60% | 85% | 🟡 P1 |
| `optimizer.py` | 0% | 80% | 🔴 P0 |
| `account_manager.py` | 0% | 85% | 🟡 P1 |
| `database_writer.py` | 0% | 70% | 🟡 P1 |
| `config_manager.py` | 0% | 75% | 🟢 P2 |
| `checker.py` | 0% | 90% | 🟡 P1 |
| `workers/ingestion.py` | 0% | 60% | 🟢 P2 |
| `workers/analysis.py` | ~40% | 75% | 🟡 P1 |
| `workers/vjs.py` | ~45% | 75% | 🟡 P1 |
| `workers/cf_submission.py` | 0% | 70% | 🟢 P2 |
| **Overall** | **~30%** | **75%** | — |

### Test Count Summary

| Layer | Existing | New | Total |
|-------|----------|-----|-------|
| Unit | 56 | ~85 | ~141 |
| Integration | 14 | ~40 | ~54 |
| Contract | 0 | ~10 | ~10 |
| E2E | 2 | ~4 | ~6 |
| **Total** | **72** | **~139** | **~211** |
