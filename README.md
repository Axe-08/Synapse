# Project Synapse 🧠

**Status:** Completed  
**Description:** A resilient, self-tuning, multi-stage data pipeline for building high-fidelity datasets from competitive programming platforms.

## Overview

Project Synapse is an automated pipeline designed to solve a complex data collection problem: generating a verified, high-quality dataset of programming problems, solutions, and their logical representations (pseudocode). It orchestrates a series of workers that scrape data, use LLMs for analysis and code generation, and run a local sandboxed judge for verification.

The system is built with a "Patient Resilience" philosophy, emphasizing fault tolerance, graceful error handling, and the ability to run for extended periods without supervision. Its most advanced feature is a self-tuning `optimizer` that monitors the pipeline's health and dynamically adjusts parameters like worker counts and batch sizes to maintain stability and performance.

---

## Architecture

The pipeline operates as a decoupled, multi-stage system where problems flow from one status to the next. Two SQLite databases (`progress.db` and `workspace.db`) manage the state and temporary data for the entire system. The orchestrator (`main.py`) dispatches jobs to workers running in separate thread pools.



The data flows through the following stages:

1.  **Ingestion:** A hybrid scraper fetches problem details. It uses `requests` for public data and an authenticated Selenium browser for protected content (like solution source code).
2.  **Analysis (ARL):** A batch of problems is sent to an "Analyst" LLM (e.g., Gemini 1.5 Pro) to convert the reference C++ solution into language-agnostic pseudocode. This stage is batch-capable to respect API rate limits.
3.  **Implementation (ARL):** The generated pseudocode is sent to an "Implementer" LLM (e.g., Llama 3 on Groq) to reconstruct the C++ code. This stage is optimized for high speed.
4.  **Verification (VJS):** The reconstructed code is compiled and run inside a secure Docker container against all known pretests. The VJS enforces strict time and memory limits.
    * **Success:** The problem proceeds to the next stage.
    * **Compile Error:** The compiler error is fed back to the *Implementer* for a syntax fix.
    * **Logic/Runtime Error:** A detailed failure report is fed back to the *Analyst* to correct the core algorithm.
5.  **Data Assembly:** Once a problem passes verification, a final "golden record" is assembled, including code quality metrics (Cyclomatic Complexity, etc.), and appended to `dataset.jsonl`. All intermediate data is then deleted to conserve space.

### Key Components

* **Databases:**
    * `progress.db`: The "single source of truth." Tracks the status of every problem, worker activity, performance metrics, and dynamic configuration. Uses WAL mode for high concurrency.
    * `workspace.db`: A transient cache for intermediate data like HTML, scraped code, and LLM outputs for problems currently being processed.
* **Optimizer (`optimizer.py`):** A separate process that acts as the pipeline's "brain." It reads the `metrics` table and uses control algorithms (like AIMD) to adjust parameters in the `dynamic_config` table to respond to events like API rate-limiting or queue overflows.
* **Dashboard (`status.py`):** A terminal-based live dashboard that provides a real-time overview of all pipeline queues, worker activity, and optimizer levers.

---

## Features

* **Resilient & Resumable:** The entire pipeline is stateful. You can stop and restart it at any time, and it will pick up exactly where it left off.
* **Self-Tuning:** The `optimizer.py` process automatically adjusts pipeline parameters to prevent API rate limit errors and balance workloads between stages.
* **Intelligent Retry Logic:** The pipeline can distinguish between syntax errors and logic errors, routing failed jobs back to the appropriate LLM with structured feedback for self-correction.
* **Hybrid Scraping:** Minimizes the use of resource-heavy browsers by using lightweight `requests` for the majority of scraping tasks.
* **Local Verification Sandbox:** Uses Docker to create a secure, consistent environment for compiling and judging code, preventing any risk to the host machine.
* **Data Enrichment:** Automatically runs static and semantic analysis on both the reference and verified solutions, adding valuable code quality metrics to the final dataset.

---

## Tech Stack

* **Orchestration:** Python 3.10+
* **Concurrency:** `concurrent.futures.ThreadPoolExecutor`
* **Databases:** SQLite 3
* **LLM APIs:** Google Gemini, Groq
* **Web Scraping:** `requests`, `BeautifulSoup4`, `undetected-chromedriver`
* **Verification Sandbox:** Docker
* **Data Versioning:** DVC (Data Version Control)
* **Dashboard:** `rich`
* **Code Quality:** `lizard`, `cppcheck`

---

## Setup and Installation

**Prerequisites:**
* Git
* Python 3.10+ and `pip`
* Docker Desktop (must be running)
* Google Chrome

**1. Clone the Repository**
```bash
git clone [https://github.com/your-username/axe-08-synapse.git](https://github.com/your-username/axe-08-synapse.git)
cd axe-08-synapse
````

**2. Install Dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure Environment Variables**
Create a `.env` file in the project root and add your credentials:

```env
# .env
GEMINI_API_KEYS=your_gemini_api_key_1,your_gemini_api_key_2
GROQ_API_KEYS=your_groq_api_key_1,your_groq_api_key_2

# Codeforces Login
CF_HANDLE=your_codeforces_handle
CF_PASSWORD=your_codeforces_password

# A custom user agent for respectful scraping
MY_USER_AGENT=YourName/ProjectSynapse/1.0 (your.email@example.com)
```

**4. Build the VJS Docker Image**
This command creates the `synapse-judge` image used for code verification.

```bash
docker build -t synapse-judge .
```

**5. Initialize the Databases**
This script will fetch the complete Codeforces problem list and set up the pipeline's initial state.

```bash
python create_database.py
```

*You will be prompted to confirm if databases already exist.*

**6. (Optional) Configure DVC Remote Storage**
To back up your final dataset, configure a DVC remote (e.g., Google Drive).

```bash
# Follow instructions from DVC for your chosen cloud storage
dvc remote add -d myremote gdrive://<your_gdrive_folder_id>
```

-----

## Usage

The pipeline is designed to be run as three separate, long-running processes in different terminal windows.

**Terminal 1: Run the Main Orchestrator**
This is the core of the pipeline. It starts all the worker threads.

```bash
python main.py
```

**Terminal 2: Run the Optimizer**
This process will monitor the pipeline and tune its parameters.

```bash
python synapse/optimizer.py
```

**Terminal 3: Run the Status Dashboard**
This will display a live, full-screen dashboard of the system's status.

```bash
python status.py
```

-----

## Finalizing and Versioning the Dataset

Once the pipeline has processed a significant number of problems, the `dataset.jsonl` file will contain your final output.

**1. Track with DVC**
Use `dvc add` to have DVC start tracking the file's hash.

```bash
dvc add dataset.jsonl
```

**2. Commit the Changes**
Commit the resulting `dataset.jsonl.dvc` file to Git. This small pointer file represents the specific version of your dataset.

```bash
git add dataset.jsonl.dvc .gitignore
git commit -m "feat: version final dataset"
```

**3. Push to Remote Storage**
Push the actual data file to your configured remote storage.

```bash
dvc push
```

Your dataset is now versioned and backed up.

-----

## Directory Structure

```
axe-08-synapse/
├── .dvc/
├── .dvcignore
├── config.py                 # Static configuration and constants
├── create_database.py        # One-time script to initialize databases
├── dataset.jsonl.dvc         # DVC pointer to the final dataset
├── debug_pipeline.py         # Sequential debugger for the pipeline
├── Dockerfile                # Defines the VJS sandbox environment
├── llm.txt                   # Master context prompt for development
├── main.py                   # Main orchestrator entry point
├── plan.md                   # Project implementation plan
├── requirements.txt
├── status.py                 # Live terminal dashboard
└── synapse/
    ├── __init__.py
    ├── api_clients.py        # Manages calls to external LLM APIs
    ├── config_manager.py     # Singleton for managing dynamic config
    ├── data_assembly.py      # Assembles the final golden record
    ├── data_manager.py       # Handles writing to the final dataset file
    ├── database.py           # Data Access Layer (DAL) for databases
    ├── database_writer.py    # Dedicated async writer thread for SQLite
    ├── key_manager.py        # Intelligent API key and rate-limit management
    ├── optimizer.py          # Self-tuning "brain" of the pipeline
    ├── scraper.py            # Hybrid web scraper for Codeforces
    ├── vjs.py                # Verification & Judging Subsystem (Docker-based)
    └── workers.py            # Core logic for each pipeline stage
```

-----

## License

This project is licensed under the MIT License.
