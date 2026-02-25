# Data Flow Diagrams (DFD) — Project Synapse

---

## Level 0 — Context Diagram

The context diagram shows Project Synapse as a single process interacting with all external entities.

```mermaid
graph LR
    CF["🌐 Codeforces\n(External Platform)"]
    GEMINI["🤖 Google Gemini API\n(Analyst LLM)"]
    GROQ["⚡ Groq API\n(Implementer LLM)"]
    DOCKER["🐳 Docker Daemon\n(Judge Sandbox)"]
    OPERATOR["👤 Pipeline Operator"]
    CONSUMER["📊 Data Consumer"]

    subgraph SYNAPSE["  Project Synapse Pipeline  "]
        P0["0\nProject Synapse\nData Pipeline"]
    end

    CF -->|"Problem statements,\n accepted submissions,\n pretests"| P0
    GEMINI -->|"Oracle quality ratings,\n generated pseudocode"| P0
    GROQ -->|"Reconstructed C++ code"| P0
    DOCKER -->|"Compilation results,\n execution outputs,\n checker verdicts"| P0
    OPERATOR -->|"Config (.env),\n Credentials,\n CAPTCHA solutions"| P0

    P0 -->|"Scraping requests,\n session cookies"| CF
    P0 -->|"Batched analysis prompts"| GEMINI
    P0 -->|"Implementation prompts\n + VJS reports"| GROQ
    P0 -->|"Compile + run commands"| DOCKER
    P0 -->|"dataset.jsonl\n (final dataset)"| CONSUMER
    P0 -->|"Live terminal dashboard,\n Log output"| OPERATOR
```

---

## Level 1 — Main Pipeline DFD

This diagram decomposes the pipeline into its 6 primary processing stages with data stores.

```mermaid
graph TD
    %% External Entities
    CF["🌐 Codeforces"]
    GEMINI_API["🤖 Gemini API"]
    GROQ_API["⚡ Groq API"]
    DOCKER_ENV["🐳 Docker Sandbox"]
    OUTPUT["📄 dataset.jsonl"]

    %% Data Stores
    DS1[("📦 progress.db\nPipeline State")]
    DS2[("🗄️ workspace.db\nIntermediate Cache")]

    %% Processes
    P1["1\nIngestion\nWorker"]
    P2["2\nCalibration\nWorker"]
    P3["3\nAnalysis\nWorker\nBatched"]
    P4["4\nImplementation\nWorker"]
    P5["5\nVJS\nWorker"]
    P6["6\nData Assembly\nWorker"]

    %% Orchestration
    ORCH["0\nOrchestrator\nmain.py"]

    %% Flows
    ORCH -->|"pending_ingestion jobs"| P1
    ORCH -->|"pending_calibration jobs"| P2
    ORCH -->|"pending_analysis jobs"| P3
    ORCH -->|"pending_implementation jobs"| P4
    ORCH -->|"pending_vjs jobs"| P5
    ORCH -->|"pending_data_assembly jobs"| P6

    CF -->|"problem HTML,\n time/mem limits,\n example tests"| P1
    CF -->|"submission source code\n (via Selenium)"| P1
    CF -->|"full pretests\n (via auth API)"| P1

    P1 -->|"HTML, oracle codes,\n pretests, limits"| DS2
    P1 -->|"status → pending_calibration"| DS1

    DS2 -->|"oracle codes,\n pretests"| P2
    DOCKER_ENV -->|"compile results,\n oracle run outputs"| P2
    P2 -->|"compiled paths,\n slowness_factor,\n checker_mode"| DS2
    P2 -->|"status → pending_analysis"| DS1

    DS2 -->|"HTML, preprocessed codes,\n last VJS report"| P3
    P3 -->|"batch prompt"| GEMINI_API
    GEMINI_API -->|"analysis JSON +\n pseudocode"| P3
    P3 -->|"pseudocode,\n quality_analysis_json"| DS2
    P3 -->|"status → pending_implementation"| DS1

    DS2 -->|"HTML, pseudocode,\n VJS report"| P4
    P4 -->|"implementation prompt"| GROQ_API
    GROQ_API -->|"reconstructed C++ code"| P4
    P4 -->|"reconstructed_code"| DS2
    P4 -->|"status → pending_vjs"| DS1

    DS2 -->|"reconstructed code,\n oracle paths, pretests,\n slowness_factor"| P5
    DOCKER_ENV -->|"oracle outputs,\n compile verdict,\n AI run verdict,\n checker verdict"| P5
    P5 -->|"failure report"| DS2
    P5 -->|"status → pending_data_assembly\n OR retry routing"| DS1

    DS2 -->|"all problem data"| P6
    P6 -->|"golden record"| OUTPUT
    P6 -->|"cleanup workspace entry"| DS2
    P6 -->|"status → completed"| DS1
```

---

## Level 2 — Scraper Subsystem DFD

Detailed data flows within the Ingestion Stage's hybrid scraping strategy.

```mermaid
graph TD
    subgraph SCRAPER["Scraper Subsystem (scraper.py)"]
        P1_1["1.1\nFetch Problem Page\n(requests — public)"]
        P1_2["1.2\nFind Top N Submissions\n(API — public)"]
        P1_3["1.3\nScrape Source Code\n(Selenium — auth)"]
        P1_4["1.4\nEnrich Pretests\n(Internal API — auth)"]
        P1_5["1.5\nAssemble Result"]
    end

    CF_PUB["🌐 CF Public Pages"]
    CF_API["🌐 CF Contest API"]
    CF_SUB["🌐 CF Submission Pages\n(Login Required)"]
    CF_INT["🌐 CF Internal Data API\n(Cookie Auth)"]
    BQ["Browser Queue\n(Selenium Driver Pool)"]

    CF_PUB -->|"problem HTML,\n limits, examples"| P1_1
    CF_API -->|"accepted C++ submissions\n (top N by rating)"| P1_2
    BQ -->|"authenticated driver"| P1_3
    CF_SUB -->|"source code\n (program-source-text)"| P1_3
    CF_INT -->|"full pretests JSON\n (testCount, input#N, answer#N)"| P1_4

    P1_1 -->|"page_details"| P1_5
    P1_2 -->|"candidate submissions"| P1_3
    P1_3 -->|"source codes"| P1_4
    P1_3 -->|"session cookies"| P1_4
    P1_4 -->|"validated pretests"| P1_5
    P1_5 -->|"assembled problem data"| OUT["To Calibration Stage"]
```

---

## Level 2 — VJS Subsystem DFD

Detailed data flows within the Verification & Judging Stage.

```mermaid
graph TD
    subgraph VJS["VJS Subsystem (workers.py — vjs_worker)"]
        V1["1\nFetch Workspace Data"]
        V2["2\nRun All Oracles\n(Parallel Docker)"]
        V3["3\nTiered Consensus\nVoting"]
        V4["4\nCompile AI Code\n(Docker)"]
        V5["5\nRun AI Code\n(Docker)"]
        V6["6\nCheck Output\n(synapse.checker)"]
    end

    DS2_IN[("workspace.db")]
    DOCKER["🐳 Docker Sandbox"]
    DS1_OUT[("progress.db")]

    DS2_IN -->|"reconstructed_code, oracle_paths,\n pretests, slowness_factor,\n quality_analysis_json"| V1
    V1 -->|"data"| V2
    DOCKER -->|"oracle stdout\n (full test suite)"| V2
    V2 -->|"oracle_outputs[]"| V3
    V3 -->|"consensus_output\n (golden expected)"| V4
    V3 -->|"FAIL → quarantine"| DS1_OUT
    DOCKER -->|"compile exit code +\n stderr"| V4
    V4 -->|"FAIL → retry impl"| DS1_OUT
    V4 -->|"compiled binary"| V5
    DOCKER -->|"AI stdout + exit code"| V5
    V5 -->|"FAIL → retry analysis"| DS1_OUT
    V5 -->|"ai_output"| V6
    V6 -->|"PASS → pending_data_assembly"| DS1_OUT
    V6 -->|"FAIL → retry analysis"| DS1_OUT
```
