# Project Synapse — Documentation Index

**Project:** Project Synapse 🧠  
**Description:** A resilient, self-tuning, multi-stage data pipeline for building high-fidelity datasets from competitive programming platforms.

---

## Documents

| File | Description |
|------|-------------|
| [SRS.md](./SRS.md) | Software Requirements Specification — functional & non-functional requirements, DB schema, state machine |
| [Diagrams/README.md](./Diagrams/README.md) | All wireframe diagrams + Mermaid source index |

---

## Diagram Index

Wireframe images → `Diagrams/Wireframes/`  
Mermaid source files → `Diagrams/Mermaid/`  

| # | Wireframe | Mermaid Source |
|---|-----------|---------------|
| 0 | [Dashboard UI Wireframe](./Diagrams/Wireframes/00_Dashboard_UI_Wireframe.png) | *(status.py layout)* |
| 1 | [DFD Wireframe](./Diagrams/Wireframes/01_DFD_Wireframe.png) | [01_DFD.md](./Diagrams/Mermaid/01_DFD.md) |
| 2 | [ERD Wireframe](./Diagrams/Wireframes/02_ERD_Wireframe.png) | [02_ERD.md](./Diagrams/Mermaid/02_ERD.md) |
| 3 | [Use Case Wireframe](./Diagrams/Wireframes/03_UseCase_Wireframe.png) | [03_UseCases.md](./Diagrams/Mermaid/03_UseCases.md) |
| 4 | [Sequence Wireframe](./Diagrams/Wireframes/04_Sequence_Wireframe.png) | [04_SequenceDiagrams.md](./Diagrams/Mermaid/04_SequenceDiagrams.md) |
| 5 | [Class Diagram Wireframe](./Diagrams/Wireframes/05_Class_Wireframe.png) | [05_ClassDiagram.md](./Diagrams/Mermaid/05_ClassDiagram.md) |
| 6 | [Architecture Wireframe](./Diagrams/Wireframes/06_Architecture_Wireframe.png) | [06_Architecture.md](./Diagrams/Mermaid/06_Architecture.md) |
| 7 | [Deployment Wireframe](./Diagrams/Wireframes/07_Deployment_Wireframe.png) | [07_Deployment.md](./Diagrams/Mermaid/07_Deployment.md) |

---

## Quick Reference

### Pipeline Stages (in order)

```
Ingestion → Calibration → Analysis → Implementation → VJS → Data Assembly → ✅ Completed
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Python 3.10+ `concurrent.futures.ThreadPoolExecutor` |
| Database | SQLite 3 (WAL mode) |
| Analyst LLM | Google Gemini (`gemini-2.5-pro`) |
| Implementer LLM | Groq (`llama-3.3-70b-versatile`) |
| Web Scraping | `requests`, `BeautifulSoup4`, `undetected-chromedriver` |
| Judge Sandbox | Docker (`synapse-judge` image, `g++ -O2 -std=c++23`) |
| Dashboard | `rich` terminal UI |
| Code Metrics | `lizard`, `cppcheck` |
| Data Versioning | DVC |
