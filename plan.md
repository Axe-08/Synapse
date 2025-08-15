Project Synapse: Definitive Master Implementation Plan (Revision 4)

Phase 1: Foundation - Implementing the Intelligent, Batch-Capable Pipeline Core 🏗️

Objective: To build the complete, decoupled, multi-stage worker architecture from the ground up. This version will be batch-capable from day one to handle API limits, incorporate the intelligent KeyManager, and establish the full data lifecycle for a single problem.

    Step 1.1: Evolve the Database Schema

        Objective: Create the foundational data structures in SQLite to support our entire workflow, including retries, caching, and auditing.

        File to Modify: create_database.py

        Detailed Actions & Rationale:

            Enable WAL Mode: Immediately after creating a connection to both progress.db and workspace.db, execute PRAGMA journal_mode=WAL;. This is the implementation of my suggestion to improve concurrency, allowing the status.py monitor and other processes to read from the databases without being blocked by worker writes.

            Update problems Table (progress.db):

                Add analysis_try_count INTEGER DEFAULT 0: Tracks the "outer loop" retries triggered by logical failures in the VJS.

                Add implementation_try_count INTEGER DEFAULT 0: Tracks the "inner loop" retries triggered by syntax/compilation failures in the VJS.

                Add last_vjs_report TEXT: Stores the error message from a VJS failure, which is fed back into the Analyst/Implementer prompts for self-correction.

            Update problem_data_cache Table (workspace.db):

                Add reference_solution_code TEXT: Stores the raw C++ code separately from its JSON metadata for direct and easy access by the analysis_worker.

                Add arl_pseudocode TEXT, arl_reconstructed_code TEXT: To store the outputs of the LLM stages.

                Add static_analysis_json TEXT: To store the structured output from the static analysis tool we'll add in Phase 3.

            Create process_history Table (progress.db): Implement the full schema for our audit trail. This is essential for debugging the complex interactions in our pipeline from day one.

        Acceptance Criteria: Running python create_database.py successfully generates progress.db and workspace.db files with the complete, correct schemas.

    Step 1.2: Engineer the Intelligent Hybrid KeyManager

        Objective: Build our smart API key controller to proactively manage rate limits and reactively handle errors with nuanced strategies.

        File to Modify: synapse/key_manager.py

        Detailed Actions & Rationale:

            Update Configuration Constants: Set the constants at the top of the file to the correct, known limits for our target models: RPM_LIMIT_GEMINI = 5, TPM_LIMIT_GEMINI = 2_000_000.

            Enhance KeyStatus Enum: Add the EXHAUSTED state to specifically handle daily quota breaches, which require a different cooldown strategy than temporary rate limits.

            Enhance ManagedKey Dataclass: Add all attributes for our hybrid strategy: requests_in_window, tokens_in_window, window_start_time (for proactive tracking) and backoff_level, successive_successes (for reactive backoff).

            Implement get_key(estimated_tokens): The logic must perform proactive checks: first, reset any expired 60-second windows, then filter keys by AVAILABLE status, and finally, filter by whether the key has enough requests_in_window and tokens_in_window capacity for the upcoming call.

            Implement release_key(outcome, tokens_used): The logic must handle all outcomes. On SUCCESS, update the proactive counters. On RATE_LIMITED, apply exponential backoff. On EXHAUSTED, calculate the time until the next midnight UTC and set that as the cooldown.

        Acceptance Criteria: The KeyManager correctly manages a pool of keys in memory, applying different cooldown strategies based on the outcome and proactively reserving keys based on estimated usage.

    Step 1.3: Refactor Database Interface

        Objective: Create a robust and intuitive data access layer (DAL) that our workers will use to interact with the databases.

        File to Modify: synapse/database.py

        Detailed Actions & Rationale:

            Implement Batch-Aware get_next_jobs(status, limit): This function is critical for the analysis_worker. It must atomically select limit problems with the given status and update all their statuses to in_progress... in a single transaction to prevent race conditions between multiple orchestrator threads.

            Implement get_batch_data_from_workspace(problem_ids): Create this function to efficiently retrieve all necessary data for a batch of problems in a single query.

            Implement All State Transition Functions: Create a specific, explicit function for every arrow in our pipeline diagram (e.g., transition_to_pending_vjs, transition_to_pending_analysis_retry(problem_id, report)). This makes the worker code clean and readable.

            Implement save_process_history(): This function will be called by the transition functions to ensure every state change is logged.

        Acceptance Criteria: All data access functions are present and tested, correctly interacting with the schemas defined in Step 1.1.

    Step 1.4: Deconstruct and Rebuild the Workers

        Objective: Implement the core logic of our pipeline, with each worker performing its specialized task.

        File to Modify: synapse/workers.py

        Detailed Actions & Rationale:

            analysis_worker: This worker must be built for batching. It will:

                Fetch a batch of jobs using database.get_next_jobs(limit=ANALYSIS_BATCH_SIZE).

                Construct a single, large prompt for the Gemini 2.5 Pro API containing all problems in the batch.

                Make one API call via the KeyManager.

                Parse the structured response to get the pseudocode for each individual problem.

                Loop through the results, updating each problem's status and workspace data.

            vjs_worker: This worker must implement our full retry logic. It will execute the reconstructed code and, based on the result:

                On Success: Call transition_to_pending_data_assembly.

                On Compilation/Syntax Error: Call transition_to_pending_implementation_retry, passing the compiler error as the report.

                On Logical/Test Case Error: Call transition_to_pending_analysis_retry, passing the test failure details as the report.

            Implement the simpler, single-problem logic for the ingestion, implementation, and data_assembly workers.

        Acceptance Criteria: Each worker function correctly processes its input, calls the necessary database and KeyManager functions, and transitions problems to their correct next state.

    Step 1.5: Update the Orchestrator

        Objective: To manage and coordinate all the new worker pools and background threads.

        File to Modify: main.py

        Detailed Actions & Rationale:

            Define Configuration Constants: At the top of the file, define the worker counts for all new pools and, critically, the static ANALYSIS_BATCH_SIZE = 5 (or another safe starting number). This implements our "static foundation" for batching.

            Instantiate Thread Pools: Create ThreadPoolExecutor instances for all five worker types: Ingestion, Analysis, Implementation, VJS, and Data Assembly.

            Update Main Loop: The orchestrator's main while loop will now query for and dispatch jobs to all five pools, using the ANALYSIS_BATCH_SIZE constant when calling get_next_jobs for the analysis stage.

            Implement Key Health Monitor Thread: Launch the background thread responsible for proactive key health checks and resetting EXHAUSTED keys daily.

        Acceptance Criteria: Running python main.py starts the entire pipeline, all worker pools are active, and problems begin flowing from pending_ingestion through the entire system.

---
### **Phase 2: Performance & Robustness Enhancements ⚡**

**Objective:** To evolve the working pipeline from a functional prototype into a performant and resilient system by implementing our key creative suggestions for efficiency and error handling.

* **Step 2.1: Implement Quarantine Logic**
    * **Objective:** To automatically isolate problems that repeatedly fail, preventing them from consuming pipeline resources indefinitely.
    * **Files to Modify:** `main.py` (or a new `config.py`), `synapse/workers.py`, `synapse/database.py`.
    * **Detailed Actions & Rationale:**
        1.  **Define Thresholds:** In `main.py`, establish constants like `MAX_ANALYSIS_RETRIES = 3` and `MAX_IMPLEMENTATION_RETRIES = 5`. This centralizes our core logic parameters.
        2.  **Create Database Function:** In `database.py`, create a new function `transition_to_quarantined(problem_id: str, reason: str)`. This function will update the problem's status to `'quarantined'` and log a definitive final event to the `process_history` table.
        3.  **Implement Worker Logic:**
            * In the **`analysis_worker`**, before processing a batch, check the `analysis_try_count` for each problem. If a problem exceeds `MAX_ANALYSIS_RETRIES`, remove it from the current batch and call `transition_to_quarantined` for it.
            * In the **`implementation_worker`**, if it receives a problem that has failed the VJS syntax check too many times (`implementation_try_count >= MAX_IMPLEMENTATION_RETRIES`), it should not send it back to analysis. Instead, it should call `transition_to_quarantined` with a reason like "Failed to generate compilable code after multiple attempts."
    * **Acceptance Criteria:** A problem that consistently fails is automatically moved to a `quarantined` state in `progress.db` and is no longer picked up by the orchestrator's `get_next_jobs` calls.

* **Step 2.2: Implement Hybrid Scraping**
    * **Objective:** To drastically reduce the runtime and resource footprint of the ingestion stage by minimizing the use of the full browser.
    * **Files to Modify:** `synapse/scraper.py`, `synapse/workers.py`.
    * **Detailed Actions & Rationale:**
        1.  **Refactor `scraper.py`:** Modify the `fetch_problem_data` function. It should no longer be responsible for creating or managing the `undetected-chromedriver` instance. Instead, it will accept an optional `driver` object as an argument: `fetch_problem_data(problem_id: str, driver: uc.Chrome | None)`.
        2.  **Initial Scrape with `requests`:** The function will *always* begin by using the lightweight `requests` library to fetch the public problem URL. It will parse the page content with `BeautifulSoup` to extract the problem statement HTML, time/memory limits, and example pretests.
        3.  **Conditional Browser Usage:** The function will only use the passed-in `driver` object for the one step that requires an authenticated session: navigating to the submission page and scraping the reference solution's source code.
        4.  **Update `ingestion_worker`:** In `workers.py`, the `ingestion_worker`'s logic will be: get a browser from the shared queue, then call `fetch_problem_data`, passing that browser instance to it.
    * **Acceptance Criteria:** The ingestion process completes noticeably faster. Logs and system monitoring show that browser CPU/memory usage is intermittent rather than constant during the ingestion phase.

---
### **Phase 3: Data Enrichment 🧬**

**Objective:** To go beyond functional correctness and add a layer of qualitative, structured data to our final dataset, making it unique and more valuable for academic research.

* **Step 3.1: Integrate Static Code Analysis**
    * **Objective:** To programmatically analyze and store code quality metrics for both the reference and reconstructed solutions.
    * **Files to Modify:** `synapse/vjs.py`, `synapse/workers.py`, `synapse/data_assembly.py`.
    * **Detailed Actions & Rationale:**
        1.  **Create Analysis Core Function:** In `vjs.py`, create a new function `run_static_analysis(code: str) -> dict`. This function will:
            * Write the input code string to a temporary file (e.g., `/tmp/analysis_XYZ.cpp`).
            * Use Python's `subprocess` module to execute the command: `cppcheck --enable=all --xml /tmp/analysis_XYZ.cpp`.
            * Capture the XML output, which `cppcheck` writes to `stderr`.
            * Use Python's built-in `xml.etree.ElementTree` to parse the XML string into a structured Python dictionary containing a summary of errors, styles, and performance warnings.
            * Ensure the temporary file is deleted in a `finally` block.
        2.  **Update `vjs_worker`:** After a reconstructed solution successfully passes all functional tests, the `vjs_worker` will call `run_static_analysis` twice: once on the reference code (retrieved from `workspace.db`) and once on the reconstructed code. It will then save this dictionary as a JSON string to the `static_analysis_json` column in the problem's `workspace.db` row.
        3.  **Update `data_assembly_worker`:** The `data_assembly_worker` will retrieve this JSON string, parse it back into a dictionary, and add it to the final golden record under a key like `code_quality_analysis`.
    * **Acceptance Criteria:** The final `dataset.jsonl` file contains entries with a `code_quality_analysis` field, providing a side-by-side comparison of metrics for the human and AI-generated code.

---
### **Phase 4: Automation & "Meta" Intelligence (Advanced) 🧠**

**Objective:** To make the pipeline self-tuning by building a system that monitors its own performance and dynamically adjusts key parameters.

* **Step 4.1: Build the Monitoring Layer**
    * **Objective:** To collect granular performance data from all parts of the pipeline.
    * **Files to Modify:** `create_database.py`, all worker files in `synapse/workers.py`, `synapse/database.py`.
    * **Detailed Actions:**
        1.  **Create `metrics` Table:** Add the schema for the `metrics` table to `create_database.py`. It will store fields like `timestamp`, `worker_pool`, `event_type` ('api_call', 'vjs_run'), `duration_ms`, `success` (boolean), and `details_json`.
        2.  **Create Logging Function:** Add a `log_metric(...)` function to `database.py`.
        3.  **Instrument Workers:** Wrap all key, time-sensitive operations in the worker functions (API calls, VJS test runs, etc.) with a simple timer (`start = time.perf_counter()`, `duration = ...`) and call `log_metric` within a `finally` block to record the performance data.
    * **Acceptance Criteria:** As the pipeline runs, the `metrics` table in `progress.db` is continuously populated with performance data points.

* **Step 4.2: Build the Optimizer**
    * **Objective:** To create a standalone process that analyzes performance data and makes intelligent tuning decisions.
    * **Files to Modify:** `create_database.py` (for new table), `synapse/optimizer.py` (new file).
    * **Detailed Actions:**
        1.  **Create `dynamic_config` Table:** Add the schema for this simple key-value table to `create_database.py`.
        2.  **Create `optimizer.py`:** This script will be the "brain." Its main loop will periodically connect to `progress.db`, query the `metrics` table to calculate recent averages (e.g., "average Gemini API failure rate in the last 15 minutes"), apply a set of predefined heuristic rules (e.g., "IF failure rate > 10% THEN decrease batch size"), and write its decisions to the `dynamic_config` table.
    * **Acceptance Criteria:** The optimizer process runs independently and can be observed updating values in the `dynamic_config` table based on the pipeline's performance.

* **Step 4.3: Make the Orchestrator Dynamic**
    * **Objective:** To enable the main pipeline to react to the optimizer's decisions in near real-time.
    * **File to Modify:** `main.py`.
    * **Detailed Actions:** At the very beginning of the main `while` loop, add a small block of code that queries the `dynamic_config` table and loads the latest parameters (like `analysis_batch_size`) into local variables. These variables will then be used throughout that loop iteration, replacing the static constants.
    * **Acceptance Criteria:** Manually changing a value in the `dynamic_config` table (e.g., reducing `analysis_batch_size` from 5 to 2) is reflected in the orchestrator's behavior, with logs showing that it starts fetching smaller batches.

---
### **Phase 5: Final Documentation & Code Review 📝**

**Objective:** To clean, document, and finalize the codebase, ensuring the project is understandable, maintainable, and presentable.

* **Detailed Actions:**
    1.  **Update `README.md`:** Write a comprehensive overview of the final architecture, including a diagram of the multi-stage pipeline and an explanation of the self-optimization loop. Provide clear, step-by-step instructions for setup and execution.
    2.  **Add Docstrings and Type Hinting:** Methodically go through every Python file and function, adding clear docstrings explaining what each component does, its parameters, and what it returns. Add full Python type hints to improve code clarity and enable static analysis.
    3.  **Code Cleanup:** Perform a final pass to remove all commented-out "dead" code, unused imports, and placeholder print statements, replacing them with proper logging.
    4.  **Finalize Dataset Tracking:** Run `dvc add dataset.jsonl` to track the final state of the generated dataset, commit the `.dvc` file, and run `dvc push` to back it up to our remote storage (e.g., Google Drive).