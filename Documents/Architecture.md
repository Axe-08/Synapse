# Project Synapse v2.0 — Documentation Index

**Project:** Project Synapse 🧠  
**Description:** A resilient, self-tuning, **distributed** multi-stage data pipeline for building high-fidelity datasets from competitive programming platforms.  
**Architecture:** Hybrid — Laptop (ingestion) + DGX (processing) via shared PostgreSQL

---

## Documents

| File | Description |
|------|-------------|
| [SRS.md](./SRS.md) | Software Requirements Specification v2.0 — functional & non-functional requirements, DB schema, state machine |
| [TestPlan.md](./TestPlan.md) | Test Plan & Debugging Guide — 5 test tiers, dual-backend strategy, debug toolkit, coverage goals |
| [Diagrams/README.md](./Diagrams/README.md) | Mermaid diagram sources + visual wireframe images |

---

## Diagram Index

| # | Diagram | Description |
|---|---------|-------------|
| 1 | [01_DFD.md](./Diagrams/Mermaid/01_DFD.md) | Data Flow Diagrams (Level 0 + Level 1 + VJS subsystem) |
| 2 | [02_ERD.md](./Diagrams/Mermaid/02_ERD.md) | Entity-Relationship Diagram (8 tables, 2 schemas) |
| 3 | [03_UseCases.md](./Diagrams/Mermaid/03_UseCases.md) | Use Case Diagrams (Operator, Pipeline, External Systems) |
| 4 | [04_SequenceDiagrams.md](./Diagrams/Mermaid/04_SequenceDiagrams.md) | Sequence Diagrams (happy path, retries, optimizer, scraper) |
| 5 | [05_ClassDiagram.md](./Diagrams/Mermaid/05_ClassDiagram.md) | Class Diagram (all modules, workers package) |
| 6 | [06_Architecture.md](./Diagrams/Mermaid/06_Architecture.md) | System Architecture (6-layer, optimizer feedback loop) |
| 7 | [07_Deployment.md](./Diagrams/Mermaid/07_Deployment.md) | Deployment Diagram (laptop + DGX + Docker + SSH tunnel) |

---

## Quick Reference

### Pipeline Stages (in order)

```
[LAPTOP]  Ingestion → classify problem
                         │
          ┌──────────────┴──────────────┐
          │ standard                    │ interactive/special
          ▼                             ▼
[DGX]   Calibration → Analysis → Implementation
          │                             │
          ▼                             ▼
        VJS (local judge)       CF Submission Worker
          │                             │
          └──────────┬──────────────────┘
                     ▼
              Data Assembly → ✅ Completed
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Python 3.10+ `ThreadPoolExecutor` per stage |
| Database | **PostgreSQL 16** (production) / SQLite 3 WAL (dev/tests) |
| Analyst LLM | Google Gemini 2.5 Pro (structured JSON output) |
| Implementer LLM | Groq — DeepSeek-V3.2 (or latest top code model) |
| Web Scraping | `requests`, `BeautifulSoup4`, `undetected-chromedriver` |
| Judge Sandbox | Docker (`synapse-judge` image, `g++ -O2 -std=c++23`) |
| Optimizer | `psutil` (DGX load), `KeyManager` (API budget), `scraper_stats` (telemetry) |
| Deployment | Docker Compose (DGX), SSH tunnel, git-based deploy via `Makefile` |
| Code Metrics | `lizard` |
| Data Versioning | DVC |

### Deployment Quick Start

```bash
# LAPTOP — SSH tunnel + ingestion
make tunnel                     # background: SSH port forward 5432
python ingestion_node.py        # scrapes CF, writes to PG

# DGX — processing pipeline
make dgx-pull                   # git pull latest code
make dgx-up                     # docker compose up -d (postgres + pipeline)
make init-db                    # create PG schemas (one-time)
```
