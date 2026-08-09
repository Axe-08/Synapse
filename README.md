# Project Synapse 🧠

> A resilient, self-tuning, **distributed** multi-stage data pipeline for building high-fidelity AI training datasets from competitive programming platforms.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## What is Synapse?

Synapse solves a hard data problem: **generating a verified, high-quality dataset of competitive programming problems** where every entry contains a problem statement, multiple oracle C++ solutions, language-agnostic pseudocode, a reconstructed implementation, and proof of correctness via a live judge.

The pipeline is designed for **unattended, long-running operation** — you start it, and it runs until it's done (or you stop it). A built-in `optimizer` module monitors health metrics and dynamically tunes worker counts and batch sizes using AIMD control loops.

### Sample Output (Golden Record)

→ See [`Records/809B_golden_record.json`](./Records/809B_golden_record.json) for a full example of what the pipeline produces per problem.

---

## Architecture (v2 — Distributed)

Synapse v2 uses a **hybrid two-node deployment**:

| Node | Role | Entrypoint |
|------|------|-----------|
| **Laptop** | Ingestion — Selenium scraping of Codeforces (auth-required pages) | `ingestion_node.py` |
| **DGX / Server** | Processing — all compute-heavy stages (Calibration → Assembly) | `main.py` via Docker Compose |

Both nodes share a **PostgreSQL 16** database as the message bus. The laptop writes scraped problem data; the DGX reads and processes it. An SSH tunnel bridges them.

### Pipeline Stages

```
[LAPTOP]  ① Ingestion  ──────────── scrape CF problems + classify
                │
[DGX]     ② Calibration ─────────── compile & run N oracle solutions
                │                    establish timing baselines (VJS)
          ③ Analysis ──────────────  Gemini: C++ oracle → pseudocode (batch)
                │
          ④ Fuzz Generation ───────  Gemini: generate adversarial test cases
                │
          ⑤ Implementation ────────  Groq/DeepSeek: pseudocode → C++
                │
          ⑥ VJS (local judge) ─────  Docker sandbox: compile & judge vs oracles
                │       ↑               ┌─ Compile Error → ⑤ Implementer (syntax fix)
                │       └───────────────┤
                │                       └─ Logic Error → ③ Analyst (algorithm fix)
          ⑦ CF Submission ──────────  submit to Codeforces judge (live validation)
                │
          ⑧ Data Assembly ─────────  assemble golden record → dataset.jsonl
```

### Key Components

| Component | File | Description |
|-----------|------|-------------|
| **Orchestrator** | [`main.py`](./main.py) | Manages 8 stage thread pools with dynamic resizing |
| **Ingestion Node** | [`ingestion_node.py`](./ingestion_node.py) | Laptop-only: Selenium scraper entry point |
| **Config** | [`config.py`](./config.py) | All constants, limits, and default parameters |
| **DB Init** | [`create_database.py`](./create_database.py) | One-time schema creation (SQLite or PostgreSQL) |
| **Dashboard** | [`status.py`](./status.py) | Live `rich`-based terminal dashboard |
| **DAL** | [`synapse/database.py`](./synapse/database.py) | Data Access Layer — all SQL behind clean functions |
| **Key Manager** | [`synapse/key_manager.py`](./synapse/key_manager.py) | Intelligent API key rotation with rate-limit tracking |
| **Account Manager** | [`synapse/account_manager.py`](./synapse/account_manager.py) | Multi-account Codeforces session management |
| **API Clients** | [`synapse/api_clients.py`](./synapse/api_clients.py) | Gemini + Groq client wrappers with retry logic |
| **Scraper** | [`synapse/scraper.py`](./synapse/scraper.py) | Hybrid `requests` + `undetected-chromedriver` scraper |
| **VJS** | [`synapse/vjs.py`](./synapse/vjs.py) | Docker-based compilation + judging subsystem |
| **Optimizer** | [`synapse/optimizer.py`](./synapse/optimizer.py) | AIMD control loops — auto-tunes worker counts |
| **Checker** | [`synapse/checker.py`](./synapse/checker.py) | Output comparison for custom-checker problems |
| **Stats Monitor** | [`synapse/stats_monitor.py`](./synapse/stats_monitor.py) | Scraper & API telemetry aggregation |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | Python 3.10+ `ThreadPoolExecutor` per stage |
| **Database** | PostgreSQL 16 (production) / SQLite 3 WAL (dev/local) |
| **Analyst LLM** | Google Gemini 2.5 Pro (structured JSON output, batch API) |
| **Implementer LLM** | Groq — DeepSeek-V3.2 / Llama 3 |
| **Web Scraping** | `requests`, `BeautifulSoup4`, `undetected-chromedriver` |
| **Judge Sandbox** | Docker (`synapse-judge` image, `g++ -O2 -std=c++23`) |
| **Self-Tuning** | AIMD control loops in `optimizer.py` |
| **Deployment** | Docker Compose (DGX), SSH tunnel, Makefile |
| **Code Metrics** | `lizard` (Cyclomatic Complexity) |
| **Data Versioning** | DVC (Data Version Control) |
| **Dashboard** | `rich` |

---

## Setup & Installation

### Prerequisites

- Git
- Python 3.10+
- Docker (running — for VJS sandbox)
- Google Chrome (laptop node only — for Selenium scraping)
- SSH access to DGX/server (for distributed deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/Axe-08/Synapse.git
cd Synapse
git checkout develop
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

**Laptop node** (full — includes Selenium, DVC):
```bash
pip install -r requirements.txt
```

**DGX / server node** (pipeline only — no Selenium/DVC):
```bash
pip install -r requirements-pipeline.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# .env

# LLM API Keys (comma-separated for multi-key rotation)
GEMINI_API_KEYS=your_gemini_key_1,your_gemini_key_2
GROQ_API_KEYS=your_groq_key_1,your_groq_key_2

# Codeforces Login Credentials (multiple accounts supported)
CF_ACCOUNTS=[{"handle": "user1", "password": "pass1"}, {"handle": "user2", "password": "pass2"}]

# Respectful scraping user-agent
MY_USER_AGENT=YourName/ProjectSynapse/1.0 (your.email@example.com)

# PostgreSQL connection (required for distributed mode; SSH tunnel must be open)
# DATABASE_URL=postgresql://synapse:synapse@localhost:5432/synapse_db

# Set to true on the DGX node to disable Selenium ingestion
# DISABLE_INGESTION=true
```

### 5. Build the VJS Docker Image

This creates the `synapse-judge` container used for code compilation and judging:

```bash
docker build -t synapse-judge .
```

### 6. Initialise the Database

**Local SQLite (development):**
```bash
python create_database.py
```

**PostgreSQL (production — run after opening tunnel):**
```bash
make init-db
```

---

## Running the Pipeline

### Local Mode (SQLite, single machine)

Run each in a separate terminal:

```bash
# Terminal 1 — Main orchestrator (all stages including ingestion)
python main.py

# Terminal 2 — Live dashboard
python status.py
```

### Distributed Mode (Laptop + DGX)

```bash
# ── LAPTOP ─────────────────────────────────────────────
# Step 1: Open SSH tunnel to DGX PostgreSQL
make tunnel                        # runs in background

# Step 2: Run ingestion (scrapes CF, writes to shared PG)
python ingestion_node.py

# ── DGX ────────────────────────────────────────────────
# Step 3: Pull latest code on DGX
make dgx-pull

# Step 4: Start the pipeline containers (PostgreSQL + pipeline)
make dgx-up

# Step 5: Check logs
make dgx-logs
```

### Useful Makefile Targets

| Target | Description |
|--------|-------------|
| `make tunnel` | Open SSH tunnel (laptop → DGX:5432) |
| `make dgx-pull` | Pull latest git + reinstall deps on DGX |
| `make dgx-up` | `docker compose up -d` on DGX |
| `make dgx-down` | `docker compose down` on DGX |
| `make dgx-logs` | Tail pipeline logs |
| `make init-db` | Initialise PostgreSQL schema (via tunnel) |
| `make init-db-local` | Initialise local SQLite schema |
| `make test` | Run unit + integration tests |

---

## Testing

The test suite covers unit, integration, and end-to-end tiers:

```bash
# Run all fast tests (unit + integration)
make test

# Or directly:
venv/bin/python -m pytest tests/unit/ tests/integration/ -q

# Run only unit tests
pytest tests/unit/ -m unit

# Run integration tests (needs in-memory DB)
pytest tests/integration/ -m integration

# E2E tests (requires real API keys + Docker — slow)
pytest tests/e2e/ -m e2e
```

---

## Versioning the Dataset

Once the pipeline has processed problems, version the output with DVC:

```bash
# Track the dataset file
dvc add dataset.jsonl

# Commit the DVC pointer
git add dataset.jsonl.dvc .gitignore
git commit -m "feat: version dataset snapshot"

# Push data to remote storage (configure first)
dvc push
```

---

## Directory Structure

```
Synapse/
├── main.py                    # Main orchestrator — 8-stage pipeline (DGX)
├── ingestion_node.py          # Laptop-only ingestion entry point
├── status.py                  # Live terminal dashboard (rich)
├── create_database.py         # One-time DB initialisation
├── config.py                  # All constants and defaults
├── Makefile                   # DGX deployment helpers
├── Dockerfile                 # synapse-judge sandbox (GCC 15, C++23)
├── Dockerfile.pipeline        # Python pipeline image for DGX
├── docker-compose.yml         # DGX: PostgreSQL + pipeline services
├── requirements.txt           # Full deps (laptop)
├── requirements-pipeline.txt  # Minimal deps (DGX, no Selenium/DVC)
├── pytest.ini                 # Test configuration
├── dataset.jsonl.dvc          # DVC pointer to final dataset
│
├── synapse/                   # Core library
│   ├── database.py            # Data Access Layer (DAL)
│   ├── database_writer.py     # Dedicated async SQLite writer thread
│   ├── api_clients.py         # Gemini + Groq client wrappers
│   ├── key_manager.py         # API key rotation + rate-limit tracking
│   ├── account_manager.py     # Multi-account Codeforces sessions
│   ├── scraper.py             # Hybrid requests + Selenium scraper
│   ├── vjs.py                 # Docker-based judge subsystem
│   ├── optimizer.py           # AIMD self-tuning optimizer
│   ├── config_manager.py      # DB-backed dynamic config singleton
│   ├── data_assembly.py       # Golden record assembly logic
│   ├── data_manager.py        # JSONL dataset writer
│   ├── checker.py             # Custom output checker
│   ├── stats_monitor.py       # Scraper + API telemetry
│   └── workers/               # One module per pipeline stage
│       ├── ingestion.py       # Stage 1: scrape + classify
│       ├── calibration.py     # Stage 2: multi-oracle VJS calibration
│       ├── analysis.py        # Stage 3: Gemini pseudocode generation
│       ├── fuzz_generator.py  # Stage 4: adversarial test generation
│       ├── implementation.py  # Stage 5: Groq code reconstruction
│       ├── vjs.py             # Stage 6: local Docker judge
│       ├── cf_submission.py   # Stage 7: Codeforces live submission
│       └── data_assembly.py   # Stage 8: assemble + write golden record
│
├── scripts/                   # Utility & debug scripts
│   ├── debug_pipeline.py      # Sequential single-problem debugger
│   ├── debug_pipeline_v2.py   # v2 debugger with cache replay
│   ├── api_key_checker.py     # Validate all API keys
│   ├── cf_accounts_check.py   # Verify Codeforces account health
│   ├── scraper_health_check.py # Run scraper diagnostics
│   ├── run_scraper_all_accounts.py # Bulk scrape with account rotation
│   ├── mock_scraper_from_dataset.py # Replay scraping from cached data
│   ├── process_logs.py        # Parse and summarise debug logs
│   └── dump_all_golden.py     # Export all golden records to JSON
│
├── tests/                     # Test suite
│   ├── unit/                  # Pure unit tests (no I/O)
│   ├── integration/           # In-memory DB + mocked APIs
│   └── e2e/                   # Full pipeline (real keys + Docker)
│
├── debugging_and_testing/     # Debug DB snapshots and helpers
│
├── Records/                   # Sample golden record outputs
│   └── README.md              # Golden record format documentation
│
└── Documents/                 # Architecture & specifications
    ├── SRS.md                 # SRS v1.0 (original architecture)
    ├── SRS_v2.md              # SRS v2.0 (multi-oracle, distributed)
    ├── TestPlan.md            # Test plan + debug guide
    ├── Architecture.md        # Architecture overview + quick ref
    └── Diagrams/              # Mermaid source + wireframe images
        ├── Mermaid/           # 7 Mermaid diagram files
        └── Wireframes/        # Visual wireframe images
```

---

## Key Design Decisions

### Patient Resilience
The entire pipeline is **stateful and resumable**. Every problem's journey is tracked in the database. Stop the pipeline at any time — restart it and it picks up exactly where it left off.

### N-Version Programming (Multi-Oracle)
Instead of trusting a single reference solution, Synapse scrapes **N top-rated solutions** (default: 5) for each problem. The VJS calibrates against all of them and only proceeds if at least `MIN_VIABLE_ORACLES` (default: 3) compile and produce consistent outputs.

### Self-Tuning Optimizer (AIMD)
The `optimizer.py` runs in a background thread and uses **Additive Increase / Multiplicative Decrease** (same algorithm TCP uses for congestion control) to tune:
- Worker counts per stage
- API batch sizes
- Scraper delays

It responds to events like API rate-limit errors, queue overflows, and idle workers — keeping the pipeline balanced without manual intervention.

### Intelligent Retry Routing
When VJS fails, the pipeline classifies the failure:
- **Compile Error** → routed back to the **Implementer** LLM (syntax fix)
- **Logic/Runtime Error** → routed back to the **Analyst** LLM (algorithm fix)

This self-correction loop significantly increases the final pass rate without human intervention.

---

## License

This project is licensed under the [MIT License](./LICENSE).

---

## Author

Built by [Axe-08](https://github.com/Axe-08) as a research data engineering project.
