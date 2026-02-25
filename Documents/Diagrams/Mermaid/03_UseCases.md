# Use Case Diagrams — Project Synapse

---

## Use Case Diagram 1: Pipeline Operator

```mermaid
graph LR
    OP(["👤 Pipeline Operator"])

    subgraph UC_OP["Pipeline Operator Use Cases"]
        UC1["Configure Credentials\n(.env file)"]
        UC2["Initialize Databases\n(create_database.py)"]
        UC3["Build VJS Docker Image\n(docker build)"]
        UC4["Start Main Orchestrator\n(python main.py)"]
        UC5["Start Optimizer\n(python synapse/optimizer.py)"]
        UC6["Monitor Live Dashboard\n(python status.py)"]
        UC7["Resolve CAPTCHA\n(browser interaction)"]
        UC8["Stop Pipeline\n(KeyboardInterrupt)"]
        UC9["Track Dataset with DVC\n(dvc add / push)"]
        UC10["Configure Filter Range\n(--min_rating, --max_rating)"]
    end

    OP --- UC1
    OP --- UC2
    OP --- UC3
    OP --- UC4
    OP --- UC5
    OP --- UC6
    OP --- UC7
    OP --- UC8
    OP --- UC9
    OP --- UC10

    UC4 -.->|"includes"| UC1
    UC4 -.->|"includes"| UC3
    UC7 -.->|"extends"| UC4
```

---

## Use Case Diagram 2: Automated Pipeline Actor

```mermaid
graph LR
    PIPELINE(["🤖 Automated Pipeline"])

    subgraph SCRAPING["Scraping Use Cases"]
        UC_S1["Fetch Problem Statement"]
        UC_S2["Find Top N Submissions"]
        UC_S3["Scrape Source Code\n(via Selenium)"]
        UC_S4["Enrich Pretests\n(via Internal API)"]
        UC_S5["Detect & Handle IP Ban"]
        UC_S6["Quarantine Interactive Problem"]
    end

    subgraph CALIBRATION["Calibration Use Cases"]
        UC_C1["Compile Oracle Solutions"]
        UC_C2["Run Oracle on Pretests"]
        UC_C3["Calculate Slowness Factor"]
        UC_C4["Determine Checker Mode"]
    end

    subgraph ANALYSIS["Analysis Use Cases"]
        UC_A1["Batch Send Problems to Gemini"]
        UC_A2["Rate Oracle Quality"]
        UC_A3["Generate Pseudocode"]
        UC_A4["Handle Partial Batch Failure"]
    end

    subgraph IMPL["Implementation Use Cases"]
        UC_I1["Send Pseudocode to Groq"]
        UC_I2["Apply VJS Compile Feedback"]
        UC_I3["Apply VJS Logic Feedback"]
    end

    subgraph VJS["VJS Use Cases"]
        UC_V1["Run Oracles in Parallel"]
        UC_V2["Establish Consensus Output"]
        UC_V3["Compile AI C++ Code"]
        UC_V4["Run AI Code vs. Pretests"]
        UC_V5["Check Output Correctness"]
        UC_V6["Route Retry Feedback"]
    end

    subgraph ASSEMBLY["Assembly Use Cases"]
        UC_AS1["Assemble Golden Record"]
        UC_AS2["Compute Code Quality Metrics"]
        UC_AS3["Append to dataset.jsonl"]
        UC_AS4["Cleanup Workspace"]
    end

    subgraph OPTIMIZER["Optimizer Use Cases"]
        UC_O1["Monitor Pipeline Metrics"]
        UC_O2["Throttle Scraper on Failures"]
        UC_O3["Adjust Analysis Workers\n(AIMD)"]
        UC_O4["Balance VJS Queue\n(P-Controller)"]
        UC_O5["Activate Panic Mode\n(IP Ban)"]
    end

    PIPELINE --- UC_S1
    PIPELINE --- UC_C1
    PIPELINE --- UC_A1
    PIPELINE --- UC_I1
    PIPELINE --- UC_V1
    PIPELINE --- UC_AS1
    PIPELINE --- UC_O1

    UC_S1 -.->|"includes"| UC_S2
    UC_S2 -.->|"includes"| UC_S3
    UC_S3 -.->|"includes"| UC_S4
    UC_S5 -.->|"extends"| UC_S1
    UC_S6 -.->|"extends"| UC_S1

    UC_C1 -.->|"includes"| UC_C2
    UC_C2 -.->|"includes"| UC_C3
    UC_C2 -.->|"includes"| UC_C4

    UC_A1 -.->|"includes"| UC_A2
    UC_A1 -.->|"includes"| UC_A3
    UC_A4 -.->|"extends"| UC_A1

    UC_I2 -.->|"extends"| UC_I1
    UC_I3 -.->|"extends"| UC_I1

    UC_V1 -.->|"includes"| UC_V2
    UC_V2 -.->|"includes"| UC_V3
    UC_V3 -.->|"includes"| UC_V4
    UC_V4 -.->|"includes"| UC_V5
    UC_V6 -.->|"extends"| UC_V5

    UC_AS1 -.->|"includes"| UC_AS2
    UC_AS1 -.->|"includes"| UC_AS3
    UC_AS1 -.->|"includes"| UC_AS4

    UC_O1 -.->|"includes"| UC_O2
    UC_O1 -.->|"includes"| UC_O3
    UC_O1 -.->|"includes"| UC_O4
    UC_O5 -.->|"extends"| UC_O1
```

---

## Use Case Diagram 3: External Systems

```mermaid
graph LR
    CF(["🌐 Codeforces"])
    GEMINI(["🤖 Google Gemini"])
    GROQ(["⚡ Groq"])
    DOCKER(["🐳 Docker"])

    subgraph CF_UC["Codeforces Interactions"]
        UC_CF1["Provide Problem Statement HTML"]
        UC_CF2["Provide Time & Memory Limits"]
        UC_CF3["Provide Example Pretests"]
        UC_CF4["List Accepted Submissions"]
        UC_CF5["Serve Submission Source Code"]
        UC_CF6["Provide Full Pretests via Internal API"]
        UC_CF7["Enforce Rate Limits / IP Ban"]
    end

    subgraph AI_UC["LLM Interactions"]
        UC_AI1["Return Oracle Quality Ratings"]
        UC_AI2["Return Pseudocode"]
        UC_AI3["Return Reconstructed C++ Code"]
        UC_AI4["Signal Rate Limit Error"]
    end

    subgraph DOCKER_UC["Docker Interactions"]
        UC_D1["Compile C++ Code"]
        UC_D2["Execute Binary with Input"]
        UC_D3["Enforce Memory Limits"]
        UC_D4["Enforce Execution Timeout"]
        UC_D5["Return stdout / exit code"]
    end

    CF --- UC_CF1
    CF --- UC_CF4
    CF --- UC_CF5
    CF --- UC_CF7

    GEMINI --- UC_AI1
    GEMINI --- UC_AI2
    GEMINI --- UC_AI4

    GROQ --- UC_AI3
    GROQ --- UC_AI4

    DOCKER --- UC_D1
    DOCKER --- UC_D2
    DOCKER --- UC_D3
    DOCKER --- UC_D4
    DOCKER --- UC_D5
```

---

## Key Use Case Descriptions

### UC-SP: Start Pipeline

**Actor:** Pipeline Operator  
**Description:** Launch main orchestrator, optimizer, and status dashboard  
**Preconditions:**
- `.env` file populated with valid credentials
- `progress.db` and `workspace.db` initialized
- `synapse-judge` Docker image built

**Main Flow:**
1. Operator runs `python main.py`
2. System resets all worker statuses to idle
3. System starts `db_writer` background thread
4. System initializes `KeyManager` for Gemini and Groq
5. System starts `KeyHealthMonitor` background thread
6. System enters main dispatch loop
7. Operator runs `python synapse/optimizer.py`
8. Operator runs `python status.py`

**Postconditions:** Pipeline is actively processing problems

---

### UC-VJS: Verify Problem

**Actor:** Automated Pipeline  
**Description:** Verify AI-generated code correctness using oracle consensus  
**Preconditions:** Problem is in `pending_vjs` state; workspace has code + oracle paths + pretests

**Main Flow:**
1. Fetch workspace data for problem
2. Run all compiled oracle binaries in parallel on full pretest suite
3. Compute weighted consensus output (Tier 1)
4. If Tier 1 fails, run trusted council recount (Tier 2)
5. If consensus found, compile AI code in Docker
6. Run AI binary on same input, compare to consensus output
7. If output matches: transition to `pending_data_assembly`
8. If compile failure: route back to `pending_implementation` with stderr report
9. If runtime/logic failure: route back to `pending_analysis` with failure report

**Postconditions:** Problem moves forward or retry is initiated

---

### UC-OPT: Optimize Pipeline

**Actor:** Automated Optimizer  
**Description:** Monitor and tune pipeline parameters  
**Preconditions:** `progress.db` exists and is accessible

**Main Flow:**
1. Sync dynamic config from DB
2. Query recent metrics (last 5 minutes)
3. Check for IP ban → activate PANIC MODE if detected
4. Check ingestion failure rate → adjust scraper delay
5. Check API rate limits → apply AIMD to analysis workers
6. Check VJS queue depth → apply P-control to analysis workers
7. Sleep for 60 seconds
8. Repeat

**Postconditions:** `dynamic_config` table updated; main pipeline adapts within 1 cycle
