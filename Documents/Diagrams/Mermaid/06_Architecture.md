# System Architecture Diagram — Project Synapse v2.0

---

## High-Level System Architecture (Hybrid)

```mermaid
graph TB
    %% =====================
    %% LAPTOP NODE
    %% =====================
    subgraph LAPTOP["💻 Laptop Node"]
        ING_NODE["ingestion_node.py\n(Ingestion Entry Point)"]
        SCRAPER["scraper.py\nHybrid Web Scraper"]
        ACCT_MGR["account_manager.py\nScraper Account Rotation"]
        CHROME["Chrome Browser\n(undetected-chromedriver)"]
    end

    %% =====================
    %% DGX NODE
    %% =====================
    subgraph DGX["🖥️ DGX Server (Docker)"]

        subgraph ORCH_LAYER["🎛️ Orchestration Layer (main.py)"]
            direction LR
            GEMINI_KM["KeyManager\n(Gemini Keys)\n+ Budget Tracker"]
            GROQ_KM["KeyManager\n(Groq Keys)\n+ Budget Tracker"]
            KHM["KeyHealthMonitor\nThread"]
            POOLS["ThreadPoolExecutor\nDynamic Pools"]
            CFG["ConfigManager\n(Singleton)"]
            DB_WRITER["DatabaseWriter\n(Singleton Thread)"]
        end

        subgraph OPTIMIZER["🧠 Optimizer Module"]
            OPT_ENGINE["Decision Engine\n(every 30s)"]
            OPT_INPUTS["Inputs:\n• Queue depths\n• DGX CPU/RAM\n• API budgets\n• Scraper stats\n• Stage durations\n• Time of day"]
        end

        subgraph PIPELINE_LAYER["⚙️ Pipeline Workers (synapse/workers/)"]
            direction LR
            W2["calibration_worker\n× 0-2 threads"]
            W3["analysis_worker\n× 0-8 threads"]
            W4["implementation_worker\n× 0-8 threads"]
            W5["vjs_worker\n× 0-4 threads"]
            W7["cf_submission_worker\n× 0-2 threads"]
            W6["data_assembly_worker\n× 0-2 threads"]
        end

        subgraph SERVICES_LAYER["🛠️ Internal Services"]
            CHECKER["checker.py\nOutput Validator"]
            API_CLIENTS["api_clients.py\nLLM API Adapter"]
            VJS_MOD["vjs.py\nVJS Controller + Fuzz"]
            DATA_ASM["data_assembly.py\nRecord Assembler"]
            DATA_MGR["data_manager.py\nFile Writer"]
        end

        subgraph DOCKER_JUDGE["🐳 Docker Judge"]
            JUDGE["synapse-judge\n(g++ -O2 -std=c++23)"]
        end
    end

    %% =====================
    %% DATA LAYER
    %% =====================
    subgraph DATA["💾 Data Layer"]
        PG[("PostgreSQL 16\nprogress + workspace\nschemas")]
        DATASET["dataset.jsonl\n(Final Output)"]
        DVC["DVC Pointer\ndataset.jsonl.dvc"]
    end

    %% =====================
    %% EXTERNAL SYSTEMS
    %% =====================
    subgraph EXTERNAL["🌐 External Systems"]
        CF["Codeforces\nhttps://codeforces.com"]
        GEMINI_API["Google Gemini API\ngemini-2.5-pro\n(structured output)"]
        GROQ_API["Groq API\nDeepSeek-V3.2"]
        DVC_REMOTE["DVC Remote Storage"]
    end

    %% =====================
    %% CONNECTIONS
    %% =====================
    ING_NODE --> SCRAPER
    SCRAPER --> ACCT_MGR
    SCRAPER --> CHROME
    CHROME --> CF
    ING_NODE <-->|"SSH tunnel\n:5432"| PG

    ORCH_LAYER --> PIPELINE_LAYER
    OPTIMIZER --> CFG
    OPT_INPUTS --> OPT_ENGINE
    OPT_ENGINE --> CFG

    GEMINI_KM --> W3
    GROQ_KM --> W4
    KHM --> GEMINI_KM & GROQ_KM
    CFG --> POOLS
    POOLS --> W2 & W3 & W4 & W5 & W6 & W7

    W2 --> VJS_MOD
    W3 --> API_CLIENTS
    W4 --> API_CLIENTS
    W5 --> VJS_MOD & CHECKER
    W6 --> DATA_ASM & DATA_MGR
    W7 --> CF

    API_CLIENTS --> GEMINI_API & GROQ_API
    VJS_MOD --> JUDGE

    DB_WRITER --> PG
    W2 & W3 & W4 & W5 & W6 & W7 --> PG
    W6 --> DATASET
    DATASET --> DVC --> DVC_REMOTE
```

---

## Optimizer Feedback Loop Architecture

```mermaid
graph LR
    subgraph INPUTS["📊 Optimizer Inputs"]
        QUEUES["Queue Depths\n(pending_* counts)"]
        CPU["DGX CPU/RAM\n(psutil)"]
        API_BUDGET["API Budget\n(RPM/RPD/TPM/TPD\nper key per service)"]
        SCRAPER_TEL["Scraper Telemetry\n(bans, rates,\naccount health)"]
        STAGE_DUR["Stage Durations\n(avg ms per stage)"]
        HISTORY["Historical Patterns\n(dgx_usage_stats)"]
    end

    subgraph OPTIMIZER["🧠 Optimizer"]
        SKIP["Stage Skipping\n(0 queue → 0 workers)"]
        COURTESY["Courtesy Mode\n(CPU>70% → scale down)"]
        BURST["Burst Mode\n(CPU<20% → scale up)"]
        BACKPRESSURE["Backpressure\n(downstream > 2× upstream\n→ throttle upstream)"]
        API_THROTTLE["API Throttle\n(>90% TPD → slow\n>98% TPD → stop)"]
        PANIC["PANIC Mode\n(IP ban → ingestion=0)"]
        SCHEDULE["Time Schedule\n(low-usage hours → burst)"]
    end

    subgraph EFFECTORS["⚙️ Effectors"]
        DYN_CFG[("dynamic_config\ntable")]
        POOL_MGR["manage_pools()\n(resize ThreadPools)"]
    end

    subgraph PIPELINE["🔄 Pipeline Workers"]
        WORKERS["Active Worker\nThreads"]
    end

    QUEUES --> SKIP & BACKPRESSURE & BURST
    CPU --> COURTESY & BURST
    API_BUDGET --> API_THROTTLE
    SCRAPER_TEL --> PANIC
    STAGE_DUR --> BACKPRESSURE
    HISTORY --> SCHEDULE

    SKIP & COURTESY & BURST & BACKPRESSURE --> DYN_CFG
    API_THROTTLE & PANIC & SCHEDULE --> DYN_CFG

    DYN_CFG --> POOL_MGR
    POOL_MGR --> WORKERS
    WORKERS --> QUEUES & STAGE_DUR
```

---

## Concurrency Architecture (Hybrid)

```mermaid
graph TD
    subgraph LAPTOP_PROC["Laptop Process: python ingestion_node.py"]
        ING_MAIN["Main Thread"]
        ING_POOL["Ingestion Pool\n1-2 threads"]
        ING_BQ["Browser Queue\n(Selenium drivers)"]
    end

    subgraph DGX_CONTAINER["DGX Container: python main.py"]
        subgraph MAIN_THREAD["Main Thread"]
            MAIN_LOOP["Dispatch Loop\n(every 10-20s)"]
            POOL_MGR["manage_pools()"]
            OPT_THREAD["Optimizer Thread\n(every 30s)"]
        end

        subgraph BG_THREADS["Background Threads"]
            KHM_T["KeyHealthMonitor\n(every 10s)"]
            DBW_T["DatabaseWriter\n(queue consumer)"]
        end

        subgraph THREADPOOLS["ThreadPoolExecutors"]
            CAL_POOL["Calibration 0-2"]
            ANA_POOL["Analysis 0-8"]
            IMP_POOL["Implementation 0-8"]
            VJS_POOL["VJS 0-4"]
            CF_POOL["CF Submit 0-2"]
            ASM_POOL["Assembly 0-2"]
        end

        subgraph INNER["Inner Parallel"]
            ORACLE_POOL["Oracle Runner\n(N workers)"]
            FUZZ_POOL["Fuzz Generator\n(sequential)"]
        end
    end

    subgraph DGX_POSTGRES["DGX: PostgreSQL Container"]
        PG[("PostgreSQL 16\nFOR UPDATE\nSKIP LOCKED")]
    end

    ING_MAIN --> ING_POOL
    ING_POOL --> ING_BQ

    MAIN_THREAD -->|"submits"| CAL_POOL & ANA_POOL & IMP_POOL & VJS_POOL & CF_POOL & ASM_POOL
    VJS_POOL -->|"uses"| ORACLE_POOL & FUZZ_POOL

    ING_POOL <-->|"SSH tunnel\n:5432"| PG
    DBW_T -->|"serial writes"| PG
    THREADPOOLS <-->|"Docker network\n:5432"| PG
    OPT_THREAD --> PG
```

---

## File System Layout

```
Synapse/
│
├── main.py                 ← DGX orchestrator entry point
├── ingestion_node.py       ← Laptop ingestion entry point
├── config.py               ← Static configuration constants
├── status.py               ← Live terminal dashboard
├── create_database.py      ← DB initializer (--postgres flag)
├── Makefile                ← Deployment automation
├── Dockerfile              ← synapse-judge image
├── Dockerfile.pipeline     ← DGX pipeline container
├── docker-compose.yml      ← DGX: postgres + pipeline
├── requirements.txt        ← Full dependencies (laptop)
├── requirements-pipeline.txt ← Slim dependencies (DGX)
├── .env                    ← API keys + credentials (gitignored)
│
├── synapse/                ← Core pipeline package
│   ├── __init__.py
│   ├── api_clients.py      ← Gemini + Groq API wrappers
│   ├── checker.py          ← Output comparison utility
│   ├── config_manager.py   ← Singleton dynamic config
│   ├── data_assembly.py    ← Golden record builder
│   ├── data_manager.py     ← dataset.jsonl writer
│   ├── database.py         ← DAL (PostgreSQL + SQLite adapter)
│   ├── database_writer.py  ← Async write queue (PG/SQLite)
│   ├── key_manager.py      ← API key pool + budget tracker
│   ├── optimizer.py        ← Intelligent optimizer module
│   ├── scraper.py          ← Codeforces hybrid scraper
│   ├── account_manager.py  ← Scraper account rotation
│   ├── vjs.py              ← Docker judge controller
│   └── workers/            ← Pipeline worker package
│       ├── __init__.py     ← Conditional imports (DISABLE_INGESTION)
│       ├── _shared.py      ← Helpers + common imports
│       ├── ingestion.py    ← ingestion_worker()
│       ├── calibration.py  ← calibration_worker()
│       ├── analysis.py     ← analysis_worker()
│       ├── implementation.py ← implementation_worker()
│       ├── vjs.py          ← vjs_worker() + fuzz generator
│       ├── cf_submission.py ← cf_submission_worker()
│       └── assembly.py     ← data_assembly_worker()
│
├── tests/
│   ├── conftest.py         ← Shared fixtures (temp DB, sync writer)
│   ├── unit/               ← 56 unit tests
│   ├── integration/        ← 14 integration tests
│   └── e2e/                ← Pipeline smoke test
│
└── Documents/
    ├── SRS.md              ← v1 (preserved)
    └── v2/                 ← v2 documentation
        ├── SRS.md
        └── Diagrams/
```
