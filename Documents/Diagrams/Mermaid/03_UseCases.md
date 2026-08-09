# Use Case Diagrams — Project Synapse v2.0

---

## Use Case Diagram 1: Pipeline Operator

```mermaid
graph LR
    OP(["👤 Pipeline Operator"])

    subgraph UC_OP["Pipeline Operator Use Cases"]
        UC1["Configure Credentials\n(.env — laptop + DGX)"]
        UC2["Initialize Databases\n(create_database.py --postgres)"]
        UC3["Build VJS Docker Image\n(docker build)"]
        UC4["Start DGX Pipeline\n(make dgx-up)"]
        UC5["Start Ingestion Node\n(python ingestion_node.py)"]
        UC6["Open SSH Tunnel\n(make tunnel)"]
        UC7["Monitor Status Dashboard\n(python status.py)"]
        UC8["Deploy Code to DGX\n(git push + make dgx-pull)"]
        UC9["Stop Pipeline\n(make dgx-down + Ctrl+C)"]
        UC10["Track Dataset with DVC"]
        UC11["Resolve CAPTCHA\n(browser interaction)"]
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
    OP --- UC11

    UC4 -.->|"includes"| UC2
    UC5 -.->|"includes"| UC6
    UC11 -.->|"extends"| UC5
```

---

## Use Case Diagram 2: Automated Pipeline Actor

```mermaid
graph LR
    PIPELINE(["🤖 Automated Pipeline"])

    subgraph SCRAPING["Scraping Use Cases (Laptop)"]
        UC_S1["Fetch Problem Statement"]
        UC_S2["Find Top N Submissions"]
        UC_S3["Scrape Source Code\n(Selenium — multi-account)"]
        UC_S4["Enrich Pretests"]
        UC_S5["Classify Problem\n(standard/interactive/special)"]
        UC_S6["Detect & Handle IP Ban"]
        UC_S7["Rotate Scraper Account"]
        UC_S8["Log Scraper Telemetry"]
    end

    subgraph CALIBRATION["Calibration Use Cases (DGX)"]
        UC_C1["Compile Oracle Solutions"]
        UC_C2["Run Oracle on Pretests"]
        UC_C3["Oracle Crash Pre-filter\n(discard truncated)"]
        UC_C4["Calculate Slowness Factor"]
        UC_C5["Determine Checker Mode"]
    end

    subgraph ANALYSIS["Analysis Use Cases (DGX)"]
        UC_A1["Batch Send Problems to Gemini\n(structured JSON schema)"]
        UC_A2["Rate Oracle Quality"]
        UC_A3["Generate Pseudocode"]
        UC_A4["Generate Test Input Script"]
        UC_A5["Handle Partial Batch Failure"]
    end

    subgraph IMPL["Implementation Use Cases (DGX)"]
        UC_I1["Send Pseudocode to Groq\n(DeepSeek-V3.2)"]
        UC_I2["g++ Syntax Pre-check"]
        UC_I3["Apply VJS Compile Feedback"]
        UC_I4["Temperature Escalation on Retry"]
    end

    subgraph VJS["VJS Use Cases (DGX)"]
        UC_V1["Run Fuzz Generator Script"]
        UC_V2["Validate Generated Inputs\n(oracle crash filter)"]
        UC_V3["Run Oracles in Parallel"]
        UC_V4["Build Combined Test Suite"]
        UC_V5["Establish Consensus Output"]
        UC_V6["Compile AI C++ Code"]
        UC_V7["Run AI Code vs. Test Suite"]
        UC_V8["Check Output Correctness"]
        UC_V9["Route Retry Feedback"]
    end

    subgraph CF_SUB["CF Submission Use Cases (DGX)"]
        UC_CF1["Submit Code to Codeforces"]
        UC_CF2["Poll for Verdict"]
        UC_CF3["Route Based on Verdict\n(AC/WA/TLE/CE)"]
        UC_CF4["Rotate Submission Account"]
    end

    subgraph ASSEMBLY["Assembly Use Cases (DGX)"]
        UC_AS1["Assemble Golden Record"]
        UC_AS2["Compute Code Quality Metrics"]
        UC_AS3["Add Confidence Metadata"]
        UC_AS4["Deduplicate via SHA256"]
        UC_AS5["Append to dataset.jsonl"]
        UC_AS6["Cleanup Workspace"]
    end

    subgraph OPTIMIZER["Optimizer Use Cases"]
        UC_O1["Monitor Queue Depths"]
        UC_O2["Monitor DGX CPU/RAM"]
        UC_O3["Track API Budget\n(RPM/RPD/TPM/TPD)"]
        UC_O4["Track Scraper Health"]
        UC_O5["Apply Backpressure"]
        UC_O6["Stage Skipping\n(0 queue → 0 workers)"]
        UC_O7["Courtesy Mode\n(CPU>70% → scale down)"]
        UC_O8["Burst Mode\n(off-peak → scale up)"]
        UC_O9["Log DGX Usage Stats"]
        UC_O10["Activate Panic Mode\n(IP Ban)"]
    end

    PIPELINE --- UC_S1
    PIPELINE --- UC_C1
    PIPELINE --- UC_A1
    PIPELINE --- UC_I1
    PIPELINE --- UC_V1
    PIPELINE --- UC_CF1
    PIPELINE --- UC_AS1
    PIPELINE --- UC_O1

    UC_S1 -.->|"includes"| UC_S2
    UC_S2 -.->|"includes"| UC_S3
    UC_S3 -.->|"includes"| UC_S4
    UC_S4 -.->|"includes"| UC_S5
    UC_S6 -.->|"extends"| UC_S3
    UC_S6 -.->|"triggers"| UC_S7
    UC_S3 -.->|"triggers"| UC_S8

    UC_C1 -.->|"includes"| UC_C2
    UC_C2 -.->|"includes"| UC_C3
    UC_C2 -.->|"includes"| UC_C4
    UC_C2 -.->|"includes"| UC_C5

    UC_A1 -.->|"includes"| UC_A2
    UC_A1 -.->|"includes"| UC_A3
    UC_A1 -.->|"includes"| UC_A4
    UC_A5 -.->|"extends"| UC_A1

    UC_I2 -.->|"extends"| UC_I1
    UC_I3 -.->|"extends"| UC_I1
    UC_I4 -.->|"extends"| UC_I1

    UC_V1 -.->|"includes"| UC_V2
    UC_V2 -.->|"includes"| UC_V3
    UC_V3 -.->|"includes"| UC_V4
    UC_V4 -.->|"includes"| UC_V5
    UC_V5 -.->|"includes"| UC_V6
    UC_V6 -.->|"includes"| UC_V7
    UC_V7 -.->|"includes"| UC_V8
    UC_V9 -.->|"extends"| UC_V8

    UC_CF1 -.->|"includes"| UC_CF2
    UC_CF2 -.->|"includes"| UC_CF3
    UC_CF4 -.->|"extends"| UC_CF1

    UC_AS1 -.->|"includes"| UC_AS2
    UC_AS1 -.->|"includes"| UC_AS3
    UC_AS1 -.->|"includes"| UC_AS4
    UC_AS1 -.->|"includes"| UC_AS5
    UC_AS1 -.->|"includes"| UC_AS6

    UC_O1 -.->|"includes"| UC_O5
    UC_O1 -.->|"includes"| UC_O6
    UC_O2 -.->|"includes"| UC_O7
    UC_O2 -.->|"includes"| UC_O8
    UC_O3 -.->|"includes"| UC_O6
    UC_O4 -.->|"includes"| UC_O10
    UC_O1 -.->|"includes"| UC_O9
```

---

## Key Use Case Descriptions

### UC-HYBRID: Start Hybrid Pipeline

**Actor:** Pipeline Operator  
**Description:** Launch the distributed pipeline across laptop and DGX  
**Preconditions:**
- `.env` file on both machines
- PostgreSQL schemas initialized
- `synapse-judge` Docker image built on DGX

**Main Flow:**
1. Operator runs `make dgx-pull` → pulls latest code to DGX
2. Operator runs `make dgx-up` → starts postgres + pipeline containers
3. Operator runs `make tunnel` → SSH tunnel to DGX PostgreSQL
4. Operator runs `python ingestion_node.py` → starts ingestion
5. DGX pipeline auto-starts via Docker Compose

**Postconditions:** Laptop scrapes CF, DGX processes all other stages

---

### UC-OPT: Intelligent Optimization

**Actor:** Automated Optimizer  
**Description:** Monitor and tune pipeline based on 7 data sources  
**Preconditions:** PostgreSQL accessible, psutil available

**Main Flow:**
1. Read queue depths — identify empty stages for skipping
2. Read DGX CPU/RAM — switch between courtesy/normal/burst mode
3. Read API budgets from KeyManager — throttle if near limits
4. Read scraper stats — detect bans, calculate safe rates
5. Read historical patterns — identify best hours for burst
6. Apply backpressure if downstream stages overloaded
7. Write updated config to dynamic_config
8. Log usage snapshot to dgx_usage_stats
9. Sleep 30 seconds, repeat

**Postconditions:** Worker counts adjusted; main pipeline adapts within 1 cycle
