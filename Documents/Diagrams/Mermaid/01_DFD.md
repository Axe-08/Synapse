# Data Flow Diagrams (DFD) — Project Synapse v2.0

---

## Level 0 — Context Diagram

```mermaid
graph LR
    CF["🌐 Codeforces\n(External Platform)"]
    GEMINI["🤖 Google Gemini API\n(Analyst LLM)"]
    GROQ["⚡ Groq API\n(Implementer LLM)"]
    DOCKER["🐳 Docker Daemon\n(Judge Sandbox)"]
    OPERATOR["👤 Pipeline Operator"]
    CONSUMER["📊 Data Consumer"]

    subgraph SYNAPSE["  Project Synapse Hybrid Pipeline  "]
        P0_L["Laptop Node\n(Ingestion)"]
        P0_D["DGX Node\n(Processing)"]
        PG[("PostgreSQL\n(Shared State)")]
    end

    CF -->|"Problem statements,\n accepted submissions,\n pretests"| P0_L
    P0_L -->|"Scraping requests,\n session cookies"| CF

    P0_L <-->|"Read/Write\nvia SSH tunnel"| PG
    P0_D <-->|"Read/Write\nvia Docker network"| PG

    GEMINI -->|"Oracle quality ratings,\n pseudocode,\n test generator script"| P0_D
    GROQ -->|"Reconstructed C++ code"| P0_D
    DOCKER -->|"Compilation results,\n execution outputs,\n checker verdicts"| P0_D

    P0_D -->|"Batched analysis prompts"| GEMINI
    P0_D -->|"Implementation prompts\n + VJS reports"| GROQ
    P0_D -->|"Compile + run commands"| DOCKER
    P0_D -->|"dataset.jsonl\n (final dataset)"| CONSUMER

    OPERATOR -->|"Config (.env),\n Credentials,\n CAPTCHA solutions"| P0_L
    OPERATOR -->|"make dgx-pull,\n make dgx-up"| P0_D
    P0_D -->|"Status dashboard,\n Log output"| OPERATOR
```

---

## Level 1 — Main Pipeline DFD

```mermaid
graph TD
    %% External Entities
    CF["🌐 Codeforces"]
    GEMINI_API["🤖 Gemini API"]
    GROQ_API["⚡ Groq API"]
    DOCKER_ENV["🐳 Docker Sandbox"]
    CF_SUBMIT["🌐 CF Submission\n(Burner Accounts)"]
    OUTPUT["📄 dataset.jsonl"]

    %% Data Store
    PG[("📦 PostgreSQL\nprogress + workspace schemas")]

    %% Processes
    P1["1\nIngestion\nWorker\n(LAPTOP)"]
    P1C["1b\nProblem\nClassifier"]
    P2["2\nCalibration\nWorker"]
    P2F["2b\nOracle Crash\nFilter"]
    P3["3\nAnalysis\nWorker\n(Gemini)"]
    P4["4\nImplementation\nWorker\n(Groq)"]
    P4S["4b\nSyntax\nPre-check"]
    P5["5\nVJS\nWorker"]
    P5G["5b\nFuzz\nGenerator"]
    P7["7\nCF Submission\nWorker"]
    P6["6\nData Assembly\nWorker"]
    OPT["0\nOptimizer\nModule"]

    %% Flows — Ingestion
    CF -->|"HTML, limits,\noracle codes, pretests"| P1
    P1 -->|"raw problem data"| PG
    P1 -->|"problem metadata"| P1C
    P1C -->|"problem_class"| PG
    P1 -->|"scraper telemetry"| PG

    %% Flows — Calibration
    PG -->|"oracle codes,\npretests"| P2
    DOCKER_ENV -->|"compile results,\noracle run outputs"| P2
    P2 -->|"pretests"| P2F
    P2F -->|"validated pretests\n(crash-filtered)"| PG
    P2 -->|"compiled paths,\nslowness_factor"| PG

    %% Flows — Analysis
    PG -->|"HTML, codes,\nlast VJS report,\nproblem_class"| P3
    P3 -->|"batch prompt\n(structured JSON schema)"| GEMINI_API
    GEMINI_API -->|"pseudocode +\ninput_generator_py +\noracle ratings"| P3
    P3 -->|"analysis results"| PG

    %% Flows — Implementation
    PG -->|"HTML, pseudocode,\nVJS report"| P4
    P4 -->|"implementation prompt"| GROQ_API
    GROQ_API -->|"reconstructed C++ code"| P4
    P4 -->|"code"| P4S
    P4S -->|"syntax-checked code"| PG

    %% Flows — VJS
    PG -->|"code, oracle paths,\npretests, generator"| P5
    P5 -->|"generator script"| P5G
    P5G -->|"synthetic inputs"| P5
    DOCKER_ENV -->|"oracle outputs,\ncompile/run verdicts"| P5
    P5 -->|"failure report\nOR success"| PG

    %% Flows — CF Submission
    PG -->|"code, problem ID"| P7
    P7 -->|"submit code"| CF_SUBMIT
    CF_SUBMIT -->|"verdict"| P7
    P7 -->|"result"| PG

    %% Flows — Assembly
    PG -->|"all problem data"| P6
    P6 -->|"golden record"| OUTPUT
    P6 -->|"cleanup + completed"| PG

    %% Flows — Optimizer
    PG -->|"queue depths,\nmetrics, scraper stats,\nDGX usage"| OPT
    OPT -->|"updated worker counts,\nusage snapshots"| PG
```

---

## Level 2 — VJS Subsystem DFD (with Fuzz Generator)

```mermaid
graph TD
    subgraph VJS["VJS Subsystem (workers/vjs.py)"]
        V1["1\nFetch Workspace Data"]
        V1G["2\nRun Fuzz Generator\n(input_generator_py × N)"]
        V2["3\nRun All Oracles\n(Parallel Docker)"]
        V2F["3b\nDiscard Crash/\nDisagree Inputs"]
        V3["4\nTiered Consensus\nVoting"]
        V4["5\nCompile AI Code\n(Docker)"]
        V5["6\nRun AI Code\n(Docker)"]
        V6["7\nCheck Output\n(synapse.checker)"]
    end

    DS_IN[("PostgreSQL\nworkspace schema")]
    DOCKER["🐳 Docker Sandbox"]
    DS_OUT[("PostgreSQL\nprogress schema")]

    DS_IN -->|"code, oracle_paths,\npretests, generator,\nslowness_factor"| V1

    V1 -->|"generator script"| V1G
    V1G -->|"generated inputs"| V2
    V1 -->|"validated pretests"| V2

    DOCKER -->|"oracle stdout\n(per input)"| V2
    V2 -->|"oracle outputs per input"| V2F
    V2F -->|"keep: all oracles agree\ndiscard: crash/disagree"| V3

    V3 -->|"combined test suite\n(pretests + generated)"| V4
    V3 -->|"FAIL → quarantine"| DS_OUT

    DOCKER -->|"compile exit code +\nstderr"| V4
    V4 -->|"FAIL → retry impl"| DS_OUT
    V4 -->|"compiled binary"| V5

    DOCKER -->|"AI stdout + exit code"| V5
    V5 -->|"FAIL → retry analysis"| DS_OUT
    V5 -->|"ai_output"| V6

    V6 -->|"PASS → pending_data_assembly"| DS_OUT
    V6 -->|"FAIL → retry analysis"| DS_OUT
```

---

## Level 2 — Scraper Subsystem DFD (Multi-Account)

```mermaid
graph TD
    subgraph SCRAPER["Scraper Subsystem (scraper.py + account_manager.py)"]
        P1_0["1.0\nAccount Manager\n(round-robin rotation)"]
        P1_1["1.1\nFetch Problem Page\n(requests — public)"]
        P1_2["1.2\nFind Top N Submissions\n(API — public)"]
        P1_3["1.3\nScrape Source Code\n(Selenium — auth)"]
        P1_4["1.4\nEnrich Pretests\n(Internal API — auth)"]
        P1_5["1.5\nClassify Problem"]
        P1_6["1.6\nAssemble Result"]
        P1_7["1.7\nLog Telemetry"]
    end

    CF_PUB["🌐 CF Public Pages"]
    CF_API["🌐 CF Contest API"]
    CF_SUB["🌐 CF Submission Pages\n(Login Required)"]
    CF_INT["🌐 CF Internal Data API\n(Cookie Auth)"]
    BQ["Browser Queue\n(Selenium Driver Pool)"]
    PG[("PostgreSQL\nscraper_stats")]

    P1_0 -->|"active account"| P1_3
    CF_PUB -->|"problem HTML,\nlimits, examples"| P1_1
    CF_API -->|"accepted C++ submissions\n(top N by rating)"| P1_2
    BQ -->|"authenticated driver"| P1_3
    CF_SUB -->|"source code"| P1_3
    CF_INT -->|"full pretests JSON"| P1_4
    CF_API -->|"problem.type,\nproblem.tags"| P1_5

    P1_1 -->|"page_details"| P1_6
    P1_2 -->|"candidates"| P1_3
    P1_3 -->|"source codes"| P1_4
    P1_3 -->|"session cookies"| P1_4
    P1_4 -->|"validated pretests"| P1_6
    P1_5 -->|"problem_class"| P1_6
    P1_6 -->|"assembled problem data"| OUT["To Calibration Stage"]

    P1_3 -->|"scrape event"| P1_7
    P1_7 -->|"telemetry record"| PG
```
