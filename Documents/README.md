# Project Synapse — Documentation Index

**Project:** Project Synapse 🧠  
**Description:** A resilient, self-tuning, **distributed** multi-stage data pipeline for building high-fidelity datasets from competitive programming platforms.  
**Architecture:** Hybrid — Laptop (ingestion) + DGX/Server (processing) via shared PostgreSQL

---

## Documents

| File | Description |
|------|-------------|
| [SRS.md](./SRS.md) | Software Requirements Specification v1.0 — original single-node architecture |
| [SRS_v2.md](./SRS_v2.md) | Software Requirements Specification v2.0 — multi-oracle, distributed, N-version programming |
| [TestPlan.md](./TestPlan.md) | Test Plan & Debugging Guide — 5 test tiers, dual-backend strategy, debug toolkit |
| [Architecture.md](./Architecture.md) | Architecture overview, tech stack, and deployment quick reference |

---

## Diagram Index

All Mermaid source diagrams are in [`Diagrams/Mermaid/`](./Diagrams/Mermaid/):

| # | Diagram | Description |
|---|---------|-------------|
| 1 | [01_DFD.md](./Diagrams/Mermaid/01_DFD.md) | Data Flow Diagrams (Level 0 + Level 1 + VJS subsystem) |
| 2 | [02_ERD.md](./Diagrams/Mermaid/02_ERD.md) | Entity-Relationship Diagram (8 tables, 2 schemas) |
| 3 | [03_UseCases.md](./Diagrams/Mermaid/03_UseCases.md) | Use Case Diagrams (Operator, Pipeline, External Systems) |
| 4 | [04_SequenceDiagrams.md](./Diagrams/Mermaid/04_SequenceDiagrams.md) | Sequence Diagrams (happy path, retries, optimizer, scraper) |
| 5 | [05_ClassDiagram.md](./Diagrams/Mermaid/05_ClassDiagram.md) | Class Diagram (all modules, workers package) |
| 6 | [06_Architecture.md](./Diagrams/Mermaid/06_Architecture.md) | System Architecture (6-layer, optimizer feedback loop) |
| 7 | [07_Deployment.md](./Diagrams/Mermaid/07_Deployment.md) | Deployment Diagram (laptop + DGX + Docker + SSH tunnel) |

Visual wireframe images are in [`Diagrams/Wireframes/`](./Diagrams/Wireframes/).
