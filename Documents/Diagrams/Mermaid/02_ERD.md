# Entity-Relationship Diagram (ERD) — Project Synapse

This diagram covers both databases: `progress.db` (pipeline state) and `workspace.db` (intermediate cache).

---

## Complete ERD

```mermaid
erDiagram

    %% ============================
    %% progress.db Entities
    %% ============================

    PROBLEMS {
        TEXT id PK "Problem ID (e.g. 1234A)"
        INTEGER contest_id "Codeforces Contest ID"
        TEXT problem_index "Letter index (A, B1, etc.)"
        INTEGER rating "Difficulty rating"
        TEXT status "Current pipeline stage status"
        TEXT notes "Failure or quarantine reason"
        INTEGER analysis_try_count "# of analysis attempts"
        INTEGER implementation_try_count "# of impl. attempts"
        INTEGER rescraping_attempts "# of rescrape attempts"
        TEXT tried_submission_ids "Comma-separated tried IDs"
        TEXT reference_submissions_json "JSON oracle submission list"
        INTEGER successful_oracles "# of compiled oracles"
        INTEGER confidence_level "0=init, 1=calibrated, 2=verified"
        TEXT last_vjs_report "Last VJS feedback for LLM retry"
        TEXT last_updated "ISO timestamp"
    }

    LIVE_WORKERS {
        TEXT worker_id PK "Worker identifier string"
        TEXT pool PK "Stage pool (INGESTION, ANALYSIS...)"
        TEXT problem_id FK "Currently processing problem"
        TEXT stage "Sub-stage label"
        TEXT status "'idle' or 'active'"
        TEXT last_heartbeat "ISO timestamp"
    }

    METRICS {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO timestamp"
        TEXT worker_pool "Stage name"
        TEXT event_type "api_call, ingestion_task, etc."
        INTEGER duration_ms "Duration in milliseconds"
        BOOLEAN success "Event success flag"
        TEXT details_json "Extra JSON details"
    }

    PROCESS_HISTORY {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO timestamp"
        TEXT problem_id FK "Associated problem"
        TEXT stage "Pipeline stage"
        TEXT event_type "SUCCESS, FAILURE, RETRY_LOOP, QUARANTINED"
        TEXT details "Human-readable description"
    }

    DYNAMIC_CONFIG {
        TEXT key PK "Parameter name"
        TEXT value "Current runtime value"
    }

    %% ============================
    %% workspace.db Entities
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
        TEXT validated_pretests_json "Calibration-validated pretests"
        REAL slowness_factor "Local speed multiplier"
        TEXT checker_mode "strict or set_based"
        TEXT arl_pseudocode "Gemini-generated pseudocode"
        TEXT quality_analysis_json "Oracle ratings from Gemini"
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
```

---

## Attribute Details & Enumerated Values

### `PROBLEMS.status` — Valid States

| Status Value | Description |
|---|---|
| `pending_ingestion` | Awaiting scraper |
| `in_progress_ingestion` | Being scraped |
| `pending_calibration` | Awaiting oracle compilation |
| `in_progress_calibration` | Oracles being compiled/run |
| `pending_analysis` | Awaiting Gemini analysis |
| `in_progress_analysis` | Gemini API in flight |
| `pending_rescraping` | Awaiting re-scrape (new oracle) |
| `in_progress_rescraping` | Being re-scraped |
| `pending_implementation` | Awaiting Groq implementation |
| `in_progress_implementation` | Groq API in flight |
| `pending_vjs` | Awaiting Docker verification |
| `in_progress_vjs` | Docker judging in progress |
| `pending_data_assembly` | Awaiting final record assembly |
| `in_progress_data_assembly` | Record being assembled |
| `completed` | Dataset record written |
| `quarantined` | Permanently excluded |
| `failed_ingestion` | Transient ingestion failure |
| `failed_calibration` | Transient calibration failure |
| `failed_analysis` | Transient analysis failure |
| `failed_implementation` | Transient implementation failure |
| `failed_vjs` | Transient VJS failure |
| `failed_data_assembly` | Transient assembly failure |

### `DYNAMIC_CONFIG.key` — Optimizer Levers

| Key | Default | Min | Max | Description |
|---|---|---|---|---|
| `ingestion_worker_count` | 1 | 0 | 2 | Active scraper threads |
| `analysis_worker_count` | 4 | 1 | 8 | Active Gemini API threads |
| `implementation_worker_count` | 4 | 1 | 8 | Active Groq API threads |
| `vjs_worker_count` | 2 | 1 | 4 | Active Docker judge threads |
| `data_assembly_worker_count` | 1 | 1 | 2 | Active assembly threads |
| `analysis_batch_size` | 5 | 1 | — | Problems per Gemini API call |
| `scraper_delay_seconds` | 2.5 | 2.5 | 10.0 | Delay between scraper requests |

---

## Cross-Database Relationship

Although stored in separate SQLite files, `problem_id` is the linking key between `progress.db` and `workspace.db`:

```
progress.db::problems.id  ←——————— (logical FK) ———————→  workspace.db::problem_data_cache.problem_id
```

The workspace entry is created on ingestion and **deleted** upon completion (Data Assembly Stage), making `workspace.db` a purely transient store.
