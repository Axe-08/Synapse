# Deployment Diagram — Project Synapse

---

## Deployment Architecture

This diagram shows how all components of Project Synapse are deployed on the host machine, including software environments and external service connections.

```mermaid
graph TB
    %% ============================
    %% HOST MACHINE NODE
    %% ============================
    subgraph HOST["🖥️ Host Machine (Linux)"]

        subgraph PYTHON_ENV["Python 3.10+ Virtual Environment (venv/)"]
            direction TB
            
            subgraph PROC_MAIN["Process 1: python main.py"]
                P_ORCH["Orchestrator + Worker Threads\n─────────────────\n• Ingestion Workers (Selenium)\n• Calibration Workers\n• Analysis Workers (Gemini)\n• Implementation Workers (Groq)\n• VJS Workers (Docker subprocess)\n• Assembly Workers\n• KeyHealthMonitor Thread\n• DatabaseWriter Thread"]
            end

            subgraph PROC_OPT["Process 2: python synapse/optimizer.py"]
                P_OPT["Optimizer Process\n─────────────────\n• AIMDController\n• P-Controller\n• SystemState checker\n• Runs every 60 seconds"]
            end

            subgraph PROC_DASH["Process 3: python status.py"]
                P_DASH["Dashboard Process\n─────────────────\n• Rich Live terminal UI\n• Read-only DB polling\n• Refreshes every 2 seconds"]
            end
        end

        subgraph CHROME_BROWSER["Google Chrome (undetected-chromedriver)"]
            SELENIUM["Selenium Browser Session\n─────────────────\n• Managed by ingestion workers\n• Shared via Queue\n• Max 25 uses per instance\n• user_data_dir: ./chrome_profile/"]
        end

        subgraph DOCKER["Docker Runtime"]
            subgraph CONTAINER["synapse-judge Container"]
                direction TB
                CPP_COMPILER["g++ Compiler\n(C++23, -O2, -static)"]
                JUDGE_EXEC["Sandboxed Executor\n─────────────────\n• Memory limit enforced\n• Stack limit: 256MB\n• Timeout: per-problem\n• Non-root user"]
                PYTHON_CHECK["Python Checker\n(synapse.checker)"]
            end
        end

        subgraph SQLITE_FILES["SQLite Databases (WAL mode)"]
            PDB[("progress.db\n─────────────────\nPipeline state, metrics,\nworker status, dynamic config\n~WAL with read concurrency")]
            WDB[("workspace.db\n─────────────────\nIntermediate problem data,\noracle codes, pretests,\nVJS reports\n~Transient, cleaned on completion")]
        end

        subgraph FS["File System"]
            DATASET["dataset.jsonl\n(append-only, final output)"]
            DVC_FILE["dataset.jsonl.dvc\n(DVC version pointer)"]
            CHROME_PROF["chrome_profile/\n(persistent browser session)"]
            TMP_DIRS["tmp/vjs_<problem>_*/\n(VJS temp compilation dirs)"]
            ENV_FILE[".env\n(credentials, API keys)"]
        end
    end

    %% ============================
    %% EXTERNAL SERVICES
    %% ============================
    subgraph INTERNET["🌐 Internet / External Services"]
        CF_SVC["Codeforces\ncodeforces.com\n─────────────────\n• HTTPS (requests)\n• Selenium browser\n• Internal cookie API"]
        GEMINI_SVC["Google Gemini API\ngenerativelanguage.googleapis.com\n─────────────────\n• Model: gemini-2.5-pro\n• HTTPS / gRPC"]
        GROQ_SVC["Groq API\napi.groq.com\n─────────────────\n• Model: llama-3.3-70b-versatile\n• HTTPS / OpenAI-compatible"]
        DVC_REMOTE["DVC Remote Storage\n(Google Drive / S3 / GCS)\n─────────────────\n• Optional backup\n• Triggered manually by operator"]
    end

    %% ============================
    %% CONNECTIONS
    %% ============================
    PROC_MAIN -->|"requests + Selenium\nHTTPS"| CF_SVC
    PROC_MAIN -->|"Gemini SDK\nHTTPS"| GEMINI_SVC
    PROC_MAIN -->|"Groq SDK\nHTTPS"| GROQ_SVC

    PROC_MAIN -->|"subprocess docker run\n(compile + execute)"| DOCKER
    PROC_MAIN <-->|"WAL read/write"| PDB
    PROC_MAIN <-->|"sync read/write"| WDB
    PROC_MAIN -->|"append records"| DATASET

    PROC_OPT <-->|"read/write dynamic_config"| PDB
    PROC_DASH -->|"read-only mode"| PDB

    DATASET --> DVC_FILE -->|"dvc push (manual)"| DVC_REMOTE
    ENV_FILE -->|"credentials loaded\nat startup"| PROC_MAIN

    DOCKER -->|"volume mount\n(read/write)"| TMP_DIRS
    CHROME_BROWSER -->|"persistent session"| CHROME_PROF
    PROC_MAIN --> CHROME_BROWSER
```

---

## Deployment Configuration Summary

### Process Inventory

| Process | Command | Role | Restartable? |
|---------|---------|------|-------------|
| Main Orchestrator | `python main.py` | Pipeline dispatch + worker threads | ✅ Yes (stateful DB) |
| Optimizer | `python synapse/optimizer.py` | Self-tuning loop | ✅ Yes |
| Dashboard | `python status.py` | Monitoring only | ✅ Yes |

### Port & Network Usage

| Component | Protocol | Direction | Endpoint |
|-----------|----------|-----------|----------|
| Codeforces scraper (requests) | HTTPS | Outbound | `codeforces.com` |
| Codeforces scraper (Selenium) | HTTPS | Outbound | `codeforces.com` |
| Gemini API | HTTPS/gRPC | Outbound | `generativelanguage.googleapis.com` |
| Groq API | HTTPS | Outbound | `api.groq.com` |
| Docker daemon | Unix Socket | Local | `/var/run/docker.sock` |
| SQLite databases | File I/O | Local | `./progress.db`, `./workspace.db` |

> **Note:** Project Synapse opens **no inbound network ports**. It is a purely outbound, client-side application.

### Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU Cores | 4 | 8+ |
| RAM | 8 GB | 16 GB |
| Disk Space | 5 GB | 20 GB+ |
| Docker Memory per container | 256 MB (configurable) | — |
| Python Version | 3.10 | 3.11+ |
| Google Chrome | Latest stable | — |

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEYS` | ✅ | Comma-separated Gemini API keys |
| `GROQ_API_KEYS` | ✅ | Comma-separated Groq API keys |
| `CF_HANDLE` | ✅ | Codeforces login handle |
| `CF_PASSWORD` | ✅ | Codeforces login password |
| `MY_USER_AGENT` | ✅ | HTTP User-Agent string for respectful scraping |

### Docker Image (`synapse-judge`)

| Property | Value |
|----------|-------|
| Base Image | Minimal Debian/Alpine with GCC |
| Tag | `synapse-judge` |
| Build Command | `docker build -t synapse-judge .` |
| Ports Exposed | None |
| Run Mode | `--rm` (ephemeral, auto-deleted after each run) |
| User | Non-root (`--user uid:gid`) |
| Memory Limit | `--memory=<memory_limit_kb>k` (per-problem) |
| Stack Limit | `--ulimit stack=268435456` (256 MB) |
| Volume Mounts | `/app` — problem temp directory (read-only for execution) |

### Startup Order

```
1. docker build -t synapse-judge .
2. python create_database.py          (one-time)
3. python main.py                     (Terminal 1)
4. python synapse/optimizer.py        (Terminal 2)
5. python status.py                   (Terminal 3)
```

### Shutdown Procedure

```
1. Press Ctrl+C in Terminal 1 (main.py)
   → main.py catches KeyboardInterrupt
   → Gracefully drains all ThreadPoolExecutors
   → Quits all active browser instances
   → Stops DatabaseWriter thread
   → All in-progress problems reset on next startup
2. Press Ctrl+C in Terminal 2 (optimizer.py) and Terminal 3 (status.py)
```
