# Deployment Diagram — Project Synapse v2.0

---

## Deployment Architecture (Hybrid)

```mermaid
graph TB
    %% ============================
    %% LAPTOP NODE
    %% ============================
    subgraph LAPTOP["💻 Laptop (Linux)"]

        subgraph LAPTOP_PYTHON["Python 3.10+ Virtual Environment (venv/)"]
            LAPTOP_PROC["python ingestion_node.py\n─────────────────\n• Ingestion Workers (Selenium)\n• Browser Queue\n• ThreadPoolExecutor\n• Graceful shutdown (Ctrl+C)"]
        end

        subgraph LAPTOP_CHROME["Google Chrome"]
            SELENIUM["undetected-chromedriver Sessions\n─────────────────\n• Max 25 uses per instance\n• Per-account chrome_profile_{handle}/\n• Multiple scraper accounts"]
        end

        TUNNEL["SSH Tunnel\n─────────────────\nssh -L 5432:localhost:5432\n    dgx-jump -N"]
    end

    %% ============================
    %% DGX NODE
    %% ============================
    subgraph DGX["🖥️ DGX Server (NVIDIA, Shared University Resource)"]

        subgraph DOCKER_COMPOSE["Docker Compose Stack"]

            subgraph PG_CONTAINER["Container: synapse-postgres"]
                PG_SVC["PostgreSQL 16\n─────────────────\n• Port 5432\n• User: synapse\n• DB: synapse_db\n• Schemas: progress, workspace\n• Healthcheck: pg_isready\n• Volume: pgdata"]
            end

            subgraph PIPELINE_CONTAINER["Container: synapse-pipeline"]
                PIPELINE_PROC["python main.py\n─────────────────\n• DISABLE_INGESTION=true\n• DATABASE_URL=postgresql://...\n• Calibration Workers\n• Analysis Workers (Gemini)\n• Implementation Workers (Groq)\n• VJS Workers (Docker subprocess)\n• CF Submission Workers\n• Assembly Workers\n• Optimizer Thread\n• KeyHealthMonitor Thread\n• DatabaseWriter Thread"]
            end
        end

        subgraph DOCKER_JUDGE["Docker Runtime (Host)"]
            JUDGE_CONTAINER["synapse-judge Containers\n─────────────────\n• Ephemeral (--rm)\n• g++ compiler (C++23)\n• Sandboxed executor\n• Memory limit enforced\n• Non-root user"]
        end

        subgraph DGX_FS["File System"]
            DATA_DIR["/home/23uec552/Synapse/data/"]
            DATASET["/home/23uec552/Synapse/dataset.jsonl"]
            ENV_FILE["/home/23uec552/Synapse/.env\n(API keys, manual)"]
        end
    end

    %% ============================
    %% EXTERNAL SERVICES
    %% ============================
    subgraph INTERNET["🌐 Internet / External Services"]
        CF_SVC["Codeforces\ncodeforces.com\n─────────────────\n• HTTPS (requests)\n• Selenium browser\n• Internal cookie API\n• Code submission (burner)"]
        GEMINI_SVC["Google Gemini API\n─────────────────\n• Model: gemini-2.5-pro\n• Structured JSON output\n• Free tier: ~1500 RPD"]
        GROQ_SVC["Groq API\n─────────────────\n• Model: DeepSeek-V3.2\n• Rate limit headers parsed\n• Free tier: ~14400 RPD"]
        GITHUB["GitHub\n─────────────────\n• Code deployment\n• git push / git pull"]
        DVC_REMOTE["DVC Remote Storage"]
    end

    %% ============================
    %% CONNECTIONS
    %% ============================
    LAPTOP_PROC -->|"Selenium\nHTTPS"| CF_SVC
    LAPTOP_PROC <-->|"SSH tunnel\n:5432"| PG_SVC
    TUNNEL -.->|"Encrypted tunnel"| PG_SVC

    PIPELINE_PROC -->|"Gemini SDK\nHTTPS"| GEMINI_SVC
    PIPELINE_PROC -->|"Groq SDK\nHTTPS"| GROQ_SVC
    PIPELINE_PROC -->|"Selenium (CF submit)\nHTTPS"| CF_SVC
    PIPELINE_PROC -->|"subprocess docker run"| JUDGE_CONTAINER
    PIPELINE_PROC <-->|"Docker network\n:5432"| PG_SVC
    PIPELINE_PROC -->|"append records"| DATASET

    ENV_FILE -->|"loaded at startup"| PIPELINE_PROC

    LAPTOP -->|"git push"| GITHUB
    GITHUB -->|"git pull (make dgx-pull)"| DGX

    DATASET --> DVC_REMOTE
```

---

## Deployment Configuration

### Process Inventory

| Machine | Process | Command | Role |
|---------|---------|---------|------|
| Laptop | Ingestion Node | `python ingestion_node.py` | Scrapes CF, writes to PG via tunnel |
| Laptop | SSH Tunnel | `make tunnel` | Forwards DGX:5432 to localhost:5432 |
| DGX (Docker) | PostgreSQL | `docker compose up` service: postgres | Shared database |
| DGX (Docker) | Pipeline | `docker compose up` service: synapse | All processing stages + optimizer |

### Network Topology

| From | To | Protocol | Port | Purpose |
|------|----|----------|------|---------|
| Laptop | Codeforces | HTTPS | 443 | Scraping |
| Laptop | DGX | SSH | 22 | Tunnel to PostgreSQL |
| Pipeline Container | PostgreSQL Container | TCP | 5432 | Docker internal network |
| Pipeline Container | Gemini API | HTTPS | 443 | Analysis prompts |
| Pipeline Container | Groq API | HTTPS | 443 | Implementation prompts |
| Pipeline Container | Docker Daemon | Unix Socket | — | VJS judge calls |
| Pipeline Container | Codeforces | HTTPS | 443 | CF Submission Worker |
| Laptop | GitHub | HTTPS | 443 | Code deployment |

> **Note:** Neither machine opens inbound ports to the internet. DGX PostgreSQL is only reachable via SSH tunnel or Docker internal network.

### Resource Usage (Courtesy Guidelines)

| Scenario | Our CPU Target | Workers | Mode |
|----------|---------------|---------|------|
| DGX idle (CPU < 20%) | Up to 50% | Full scale | Burst Mode |
| DGX moderate (20-70%) | ~30% | Proportional | Normal Mode |
| DGX busy (CPU > 70%) | < 15% | Minimum | Courtesy Mode |
| Off-peak hours (2am-6am) | Up to 60% | Maximum | Scheduled Burst |

### Environment Variables (`.env`)

| Variable | Machine | Description |
|----------|---------|-------------|
| `GEMINI_API_KEYS` | DGX | Comma-separated Gemini API keys |
| `GROQ_API_KEYS` | DGX | Comma-separated Groq API keys |
| `DATABASE_URL` | Both | PostgreSQL connection string |
| `DISABLE_INGESTION` | DGX | `true` — skip ingestion/calibration imports |
| `CF_ACCOUNTS` | Laptop | `handle1:pass1,handle2:pass2` |
| `CF_SUBMISSION_ACCOUNTS` | DGX | Burner accounts for CF submission worker |

### Deployment Workflow

```
                 LAPTOP                          DGX
                   │                              │
  1. Edit code     │                              │
  2. Run tests     │                              │
  3. git push      │────── GitHub ──────────────►  │
                   │                              │  4. make dgx-pull
                   │                              │  5. make dgx-up (rebuild)
                   │                              │
  6. make tunnel   │ ═════ SSH tunnel ═══════════► │
  7. python        │                              │  (pipeline auto-restarts
     ingestion_    │ ◄═══ PostgreSQL queries ═══► │   with new code)
     node.py       │                              │
```

### Startup Order

```
# DGX (one-time setup)
1. ssh dgx-jump
2. git clone https://github.com/Axe-08/Synapse.git
3. cd Synapse && git checkout new_archi
4. Create .env with API keys + DATABASE_URL + DISABLE_INGESTION=true
5. docker compose up -d
6. DATABASE_URL=... python create_database.py --postgres

# DGX (every session)
1. make dgx-pull           (laptop terminal)
2. make dgx-up             (laptop terminal)

# LAPTOP (every session)
1. make tunnel              (background terminal)
2. python ingestion_node.py (main terminal)
```

### Shutdown

```
1. Ctrl+C on ingestion_node.py (laptop) → graceful drain
2. make dgx-down (laptop) → stops Docker containers
3. Ctrl+C on tunnel terminal
```
