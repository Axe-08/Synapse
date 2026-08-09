# Entity-Relationship Diagram (ERD) — Project Synapse v2.0

This diagram covers the PostgreSQL database with two schemas: `progress` (pipeline state) and `workspace` (intermediate cache).

---


## Complete ERD

```mermaid
erDiagram

    %% ============================
    %% progress schema Entities
    %% ============================

    PROBLEMS {
        TEXT id PK "Problem ID (e.g. 1234A)"
        INTEGER contest_id "Codeforces Contest ID"
        TEXT problem_index "Letter index (A, B1, etc.)"
        INTEGER rating "Difficulty rating"
        TEXT status "Current pipeline stage status"
        INTEGER priority "Queue priority — higher processed first"
        TEXT problem_class "standard, special_judge, interactive, constructive"
        TEXT notes "Failure or quarantine reason"
        INTEGER analysis_try_count "Analysis attempts"
        INTEGER implementation_try_count "Implementation attempts"
        INTEGER rescraping_attempts "Rescrape attempts"
        TEXT tried_submission_ids "Comma-separated tried IDs"
        TEXT reference_submissions_json "JSON oracle submission list"
        INTEGER successful_oracles "Compiled oracle count"
        INTEGER confidence_level "0=init 1=calibrated 2=verified"
        TEXT last_vjs_report "Last VJS feedback for LLM retry"
        TEXT submission_account "CF account used for CF submission"
        TEXT last_updated "ISO timestamp"
    }

    LIVE_WORKERS {
        TEXT worker_id PK "Worker identifier"
        TEXT pool PK "Stage pool (INGESTION ANALYSIS etc.)"
        TEXT problem_id FK "Currently processing problem"
        TEXT stage "Sub-stage label"
        TEXT status "idle or active"
        TEXT last_heartbeat "ISO timestamp"
    }

    METRICS {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO timestamp"
        TEXT worker_pool "Stage name"
        TEXT event_type "api_call ingestion_task vjs_run etc."
        INTEGER duration_ms "Duration in milliseconds"
        BOOLEAN success "Event success flag"
        TEXT details_json "Extra JSON details (tokens error etc.)"
    }

    PROCESS_HISTORY {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO timestamp"
        TEXT problem_id FK "Associated problem"
        TEXT stage "Pipeline stage"
        TEXT event_type "SUCCESS FAILURE RETRY_LOOP QUARANTINED"
        TEXT details "Human-readable description"
    }

    DYNAMIC_CONFIG {
        TEXT key PK "Parameter name"
        TEXT value "Current runtime value"
    }

    SCRAPER_STATS {
        INTEGER id PK "Auto-increment"
        TEXT account "Scraper account handle"
        TEXT timestamp "ISO timestamp"
        TEXT event_type "scrape_success scrape_fail ban_detected ban_lifted"
        TEXT details_json "Response time error code request count etc."
    }

    DGX_USAGE_STATS {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO timestamp"
        INTEGER hour "Hour of day 0-23"
        INTEGER weekday "Day of week 0=Mon 6=Sun"
        REAL cpu_percent "System-wide CPU utilization"
        REAL ram_percent "System-wide RAM utilization"
        INTEGER our_active_workers "Our currently active threads"
        INTEGER queue_depth "Total pending jobs across all stages"
    }

    %% ============================
    %% workspace schema Entities
    %% ============================

    PROBLEM_DATA_CACHE {
        TEXT problem_id PK "Problem ID (FK to PROBLEMS)"
        TEXT problem_statement_html "Raw problem HTML"
        TEXT reference_solution_json "Primary oracle metadata JSON"
        TEXT reference_solution_code "Primary oracle C++ code"
        TEXT secondary_reference_codes_json "JSON array of secondary codes"
        TEXT pretests_json "JSON array of test pairs"
        TEXT time_limit_raw "Raw time limit string"
        TEXT memory_limit_raw "Raw memory limit string"
        TEXT compiled_oracle_paths_json "Paths to compiled binaries"
        TEXT validated_pretests_json "Oracle-crash-filtered pretests"
        REAL slowness_factor "Local speed multiplier"
        TEXT checker_mode "strict or set_based"
        TEXT arl_pseudocode "Gemini-generated pseudocode"
        TEXT quality_analysis_json "Oracle ratings from Gemini"
        TEXT input_generator_py "AI-generated Python test generator"
        TEXT generated_tests_json "Generated test suite from fuzz generator"
        TEXT arl_reconstructed_code "Groq-generated C++ code"
        TEXT vjs_last_report "Last VJS failure report"
    }

    %% ============================
    %% Relationships
    %% ============================

    PROBLEMS ||--o{ LIVE_WORKERS : "is processed by"
    PROBLEMS ||--o{ PROCESS_HISTORY : "has lifecycle events"
    PROBLEMS ||--o{ METRICS : "generates performance data"
    PROBLEMS ||--o| PROBLEM_DATA_CACHE : "has intermediate cache"
    SCRAPER_STATS }o--|| PROBLEMS : "records scraping events"
    DGX_USAGE_STATS }o--|| DYNAMIC_CONFIG : "informs optimizer decisions"
```

---

## Attribute Details & Enumerated Values

### `PROBLEMS.status` — Valid States

| Status Value | Description | Machine |
|---|---|---|
| `pending_ingestion` | Awaiting scraper | Laptop |
| `in_progress_ingestion` | Being scraped | Laptop |
| `pending_calibration` | Awaiting oracle compilation | DGX |
| `in_progress_calibration` | Oracles being compiled/run | DGX |
| `pending_analysis` | Awaiting Gemini analysis | DGX |
| `in_progress_analysis` | Gemini API in flight | DGX |
| `pending_rescraping` | Awaiting re-scrape (new oracle) | Laptop |
| `in_progress_rescraping` | Being re-scraped | Laptop |
| `pending_implementation` | Awaiting Groq implementation | DGX |
| `in_progress_implementation` | Groq API in flight | DGX |
| `pending_vjs` | Awaiting Docker verification | DGX |
| `in_progress_vjs` | Docker judging in progress | DGX |
| `pending_cf_submission` | Awaiting CF submission (interactive/special) | DGX |
| `in_progress_cf_submission` | CF submission pending verdict | DGX |
| `pending_data_assembly` | Awaiting final record assembly | DGX |
| `in_progress_data_assembly` | Record being assembled | DGX |
| `completed` | Dataset record written | — |
| `quarantined` | Permanently excluded | — |
| `failed_*` | Transient failure, retried with higher priority | — |

### `PROBLEMS.problem_class` — Classification

| Class | Detection | Pipeline Route |
|-------|-----------|----------------|
| `standard` | Default | → VJS (local Docker) |
| `special_judge` | CF tags / "you may print any" | → VJS then CF Submission Worker |
| `interactive` | `type: INTERACTIVE` from CF API | → CF Submission Worker directly |
| `constructive` | "output any valid" in statement | → VJS with oracle-as-verifier |

### `DYNAMIC_CONFIG.key` — Optimizer Levers

| Key | Default | Min | Max | Description |
|---|---|---|---|---|
| `ingestion_worker_count` | 1 | 0 | 2 | Active scraper threads (laptop) |
| `calibration_worker_count` | 1 | 0 | 2 | Active calibration threads (DGX) |
| `analysis_worker_count` | 4 | 0 | 8 | Active Gemini API threads (DGX) |
| `implementation_worker_count` | 4 | 0 | 8 | Active Groq API threads (DGX) |
| `vjs_worker_count` | 2 | 0 | 4 | Active Docker judge threads (DGX) |
| `cf_submission_worker_count` | 1 | 0 | 2 | Active CF submission threads (DGX) |
| `data_assembly_worker_count` | 1 | 0 | 2 | Active assembly threads (DGX) |
| `analysis_batch_size` | 5 | 1 | — | Problems per Gemini API call |
| `scraper_delay_seconds` | 2.5 | 2.5 | 10.0 | Delay between scraper requests |

---

## Database Architecture

```
                     PostgreSQL 16 (DGX Docker)
                    ┌─────────────────────────────────────┐
                    │  synapse_db                          │
                    │                                      │
                    │  ┌── progress schema ──────────────┐ │
                    │  │  problems                       │ │
                    │  │  live_workers                    │ │
                    │  │  metrics                        │ │
                    │  │  process_history                │ │
                    │  │  dynamic_config                 │ │
                    │  │  scraper_stats                  │ │
                    │  │  dgx_usage_stats                │ │
                    │  └─────────────────────────────────┘ │
                    │                                      │
                    │  ┌── workspace schema ─────────────┐ │
                    │  │  problem_data_cache              │ │
                    │  └─────────────────────────────────┘ │
                    └───────────────┬──────────────────────┘
                                    │
                    ┌───────────────┴──────────────────────┐
                    │                                      │
            DGX (Docker network)              Laptop (SSH tunnel)
            pipeline container                ingestion_node.py
            main.py                           :5432 → localhost:5432
```
