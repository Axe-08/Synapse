# System Architecture Diagram — Project Synapse

---

## High-Level System Architecture

```mermaid
graph TB
    %% =====================
    %% OPERATOR LAYER
    %% =====================
    subgraph OPERATOR_LAYER["👤 Operator Interface Layer"]
        ENV[".env Credentials File"]
        CLI_MAIN["python main.py\n(CLI Entry Point)"]
        CLI_OPT["python synapse/optimizer.py\n(Optimizer Process)"]
        CLI_STATUS["python status.py\n(Live Dashboard)"]
    end

    %% =====================
    %% ORCHESTRATION LAYER
    %% =====================
    subgraph ORCH_LAYER["🎛️ Orchestration Layer (main.py)"]
        direction LR
        GEMINI_KM["KeyManager\n(Gemini Keys)"]
        GROQ_KM["KeyManager\n(Groq Keys)"]
        KHM["KeyHealthMonitor\nThread"]
        POOLS["ThreadPoolExecutor\nPools (per stage)"]
        CFG["ConfigManager\n(Singleton)"]
        DB_WRITER["DatabaseWriter\n(Singleton Thread)"]
    end

    %% =====================
    %% PIPELINE STAGES
    %% =====================
    subgraph PIPELINE_LAYER["⚙️ Pipeline Stage Workers (workers.py)"]
        direction LR
        W1["ingestion_worker\n× 1-2 threads"]
        W2["calibration_worker\n× 1-2 threads"]
        W3["analysis_worker\n× 1-8 threads"]
        W4["implementation_worker\n× 1-8 threads"]
        W5["vjs_worker\n× 1-4 threads"]
        W6["data_assembly_worker\n× 1-2 threads"]
    end

    %% =====================
    %% SERVICES LAYER
    %% =====================
    subgraph SERVICES_LAYER["🛠️ Internal Services"]
        SCRAPER["scraper.py\nHybrid Web Scraper"]
        CHECKER["checker.py\nOutput Validator"]
        API_CLIENTS["api_clients.py\nLLM API Adapter"]
        VJS_MOD["vjs.py\nVJS Controller"]
        DATA_ASM["data_assembly.py\nRecord Assembler"]
        DATA_MGR["data_manager.py\nFile Writer"]
    end

    %% =====================
    %% DATA LAYER
    %% =====================
    subgraph DATA_LAYER["💾 Data Layer"]
        PROGRESS_DB[("progress.db\n(Pipeline State)\nSQLite WAL")]
        WORKSPACE_DB[("workspace.db\n(Intermediate Cache)\nSQLite WAL")]
        DATASET["dataset.jsonl\n(Final Output)\nAppend-only"]
        DVC["DVC Pointer\ndataset.jsonl.dvc"]
    end

    %% =====================
    %% EXTERNAL SYSTEMS
    %% =====================
    subgraph EXTERNAL["🌐 External Systems"]
        CF["Codeforces\nhttps://codeforces.com"]
        GEMINI_API["Google Gemini API\ngemini-2.5-pro"]
        GROQ_API["Groq API\nllama-3.3-70b-versatile"]
        DOCKER["Docker Daemon\nsynapse-judge image"]
        DVC_REMOTE["DVC Remote Storage\n(Google Drive or S3)"]
    end

    %% =====================
    %% CONNECTIONS
    %% =====================
    CLI_MAIN --> ORCH_LAYER
    CLI_OPT --> CFG
    CLI_STATUS --> PROGRESS_DB

    ORCH_LAYER --> PIPELINE_LAYER
    GEMINI_KM --> W3
    GROQ_KM --> W4
    KHM --> GEMINI_KM & GROQ_KM
    POOLS --> W1 & W2 & W3 & W4 & W5 & W6
    CFG --> POOLS

    W1 --> SCRAPER
    W2 --> VJS_MOD
    W3 --> API_CLIENTS
    W4 --> API_CLIENTS
    W5 --> VJS_MOD & CHECKER
    W6 --> DATA_ASM & DATA_MGR

    SCRAPER --> CF
    API_CLIENTS --> GEMINI_API & GROQ_API
    VJS_MOD --> DOCKER
    CHECKER --> DOCKER

    PIPELINE_LAYER --> DATA_LAYER
    DB_WRITER --> PROGRESS_DB
    W1 & W2 --> WORKSPACE_DB
    W3 & W4 --> WORKSPACE_DB
    W5 --> WORKSPACE_DB
    W6 --> DATASET
    W6 --> WORKSPACE_DB

    DATASET --> DVC --> DVC_REMOTE
    ENV --> ORCH_LAYER
```

---

## Self-Tuning Feedback Loop Architecture

```mermaid
graph LR
    subgraph MEASUREMENTS["📊 Measurement"]
        MET["metrics table\n(success rates, durations)"]
        QUEUES["Queue Depths\n(pending_* counts)"]
        BAN["IP Ban Detection\n(scrape_blocked events)"]
    end

    subgraph OPTIMIZER["🧠 Optimizer (optimizer.py)"]
        AIMD_C["AIMD Controller\n(analysis_worker_count)"]
        P_CTRL["P-Controller\n(VJS queue balancing)"]
        PANIC["PANIC MODE\n(IP ban response)"]
        THROTTLE["Scraper Throttle\n(delay_seconds)"]
    end

    subgraph EFFECTORS["⚙️ Effectors (main.py)"]
        DYN_CFG[("dynamic_config\ntable")]
        POOL_MGR["manage_pools()\n(resize ThreadPools)"]
    end

    subgraph PIPELINE["🔄 Pipeline Workers"]
        WORKERS["Active Worker\nThreads"]
    end

    WORKERS --> MET
    WORKERS --> QUEUES
    WORKERS --> BAN

    MET --> AIMD_C & THROTTLE
    QUEUES --> P_CTRL
    BAN --> PANIC

    AIMD_C --> DYN_CFG
    P_CTRL --> DYN_CFG
    PANIC --> DYN_CFG
    THROTTLE --> DYN_CFG

    DYN_CFG --> POOL_MGR
    POOL_MGR --> WORKERS
```

---

## Concurrency Architecture

```mermaid
graph TD
    subgraph MAIN_THREAD["Main Thread"]
        MAIN_LOOP["Dispatch Loop\n(every 10-20s)"]
        POOL_MGR["manage_pools()"]
    end

    subgraph BG_THREADS["Background Daemon Threads"]
        KHM_T["KeyHealthMonitor\n(every 10s)"]
        DBW_T["DatabaseWriter\n(queue consumer)"]
    end

    subgraph EXT_POOLS["External Process"]
        OPT_P["Optimizer Process\n(every 60s)"]
        DASH_P["Status Dashboard Process\n(every 2s)"]
    end

    subgraph THREADPOOLS["ThreadPoolExecutors (per stage)"]
        ING_POOL["Ingestion Pool\n1-2 threads"]
        CAL_POOL["Calibration Pool\n1-2 threads"]
        ANA_POOL["Analysis Pool\n1-8 threads"]
        IMP_POOL["Implementation Pool\n1-8 threads"]
        VJS_POOL["VJS Pool\n1-4 threads"]
        ASM_POOL["Assembly Pool\n1-2 threads"]
    end

    subgraph INNER_POOLS["Inner Parallel Executions"]
        SCRAPER_POOL["CF API Scraper\nThreadPoolExecutor\n(5 workers)"]
        ORACLE_POOL["Oracle Runner\nThreadPoolExecutor\n(N oracle workers)"]
    end

    MAIN_THREAD -->|"submits"| ING_POOL & CAL_POOL & ANA_POOL & IMP_POOL & VJS_POOL & ASM_POOL
    MAIN_THREAD --> BG_THREADS
    DBW_T -->|"serial writes"| SQLITE["progress.db\n(WAL mode)"]

    ING_POOL -->|"uses"| SCRAPER_POOL
    VJS_POOL -->|"uses"| ORACLE_POOL

    OPT_P -->|"reads/writes dynamic_config"| SQLITE
    DASH_P -->|"reads (read-only)"| SQLITE
```

---

## File System Layout

```
axe-08-synapse/
│
├── main.py                 ← Orchestrator entry point
├── config.py               ← Static configuration constants  
├── status.py               ← Live terminal dashboard
├── create_database.py      ← One-time DB initializer
├── Dockerfile              ← synapse-judge image definition
├── requirements.txt        ← Python dependencies
├── .env                    ← API keys + credentials (gitignored)
│
├── synapse/                ← Core pipeline package
│   ├── __init__.py
│   ├── api_clients.py      ← Gemini + Groq API wrappers
│   ├── checker.py          ← Output comparison utility
│   ├── config_manager.py   ← Singleton dynamic config
│   ├── data_assembly.py    ← Golden record builder
│   ├── data_manager.py     ← dataset.jsonl writer
│   ├── database.py         ← Data Access Layer (DAL)
│   ├── database_writer.py  ← Async SQLite write queue
│   ├── key_manager.py      ← API key pool manager
│   ├── optimizer.py        ← Self-tuning optimizer
│   ├── scraper.py          ← Codeforces hybrid scraper
│   ├── vjs.py              ← Docker judge controller
│   └── workers.py          ← All stage worker functions
│
├── progress.db             ← Pipeline state (SQLite)
├── workspace.db            ← Intermediate cache (SQLite)
├── dataset.jsonl           ← Final output dataset
├── dataset.jsonl.dvc       ← DVC version pointer
│
├── .dvc/                   ← DVC configuration
├── chrome_profile/         ← Persistent Selenium session
├── data/                   ← (DVC-tracked data directory)
└── Documents/              ← Project documentation
    ├── SRS.md
    └── Diagrams/
        ├── 01_DFD.md
        ├── 02_ERD.md
        ├── 03_UseCases.md
        ├── 04_SequenceDiagrams.md
        ├── 05_ClassDiagram.md
        ├── 06_Architecture.md
        └── 07_Deployment.md
```
