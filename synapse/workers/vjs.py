# synapse/workers/vjs.py
"""
Stage 5: VJS (Verification & Judging Service) Worker

Judges code using a tiered, weighted consensus model with an adaptive
quality threshold.
"""
from ._shared import (
    logging, json, os, shutil, subprocess, tempfile,
    ThreadPoolExecutor, as_completed,
    Dict, Any,
    db, MIN_VIABLE_ORACLES, VJS_COMPILATION_TIMEOUT,
)
from synapse.data_assembly import _parse_time_limit, _parse_memory_limit

def __save_generated_tests(problem_id: str, test_arr: list):
    ph = '%s' if db.USE_POSTGRES else '?'
    sql = f"UPDATE problem_data_cache SET generated_tests_json = {ph} WHERE problem_id = {ph}"
    if db.USE_POSTGRES:
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.cursor().execute(sql, (json.dumps(test_arr), problem_id))
    else:
        with db._get_db_connection(db.WORKSPACE_DB_PATH) as conn:
            conn.execute(sql, (json.dumps(test_arr), problem_id))

def vjs_worker(problem: Dict[str, Any], worker_id: str):
    """
    (DEFINITIVE with User's Adaptive Threshold Logic)
    Judges code using a tiered, weighted consensus model with an adaptive
    quality threshold.
    """
    problem_id = problem['id']
    logging.info(f"[{problem_id}] Starting VJS with Adaptive Threshold...")
    db.update_worker_status(worker_id, 'VJS', problem_id, 'SETUP', 'active')

    vjs_temp_dir = tempfile.mkdtemp(prefix=f"vjs_{problem_id}_")

    try:
        # --- Data Fetching ---
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data:
            raise Exception("Workspace data not found for VJS.")

        reconstructed_code = workspace_data.get('arl_reconstructed_code')
        oracle_paths = json.loads(workspace_data.get('compiled_oracle_paths_json', '[]'))
        pretests = json.loads(workspace_data.get('validated_pretests_json', '[]'))
        slowness_factor = workspace_data.get('slowness_factor', 3.0)
        time_limit_ms = int(
            _parse_time_limit(workspace_data.get('time_limit_raw', '1s')) * slowness_factor
        )
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256mb'))
        analysis_json = json.loads(workspace_data.get('quality_analysis_json', '{}'))
        oracle_ratings = analysis_json.get('oracle_ratings', {})
        rating_weights = {'Excellent': 4, 'Good': 3, 'Fair': 2, 'Poor': 1}

        if not all([reconstructed_code, oracle_paths, pretests]):
            raise Exception("Missing critical data for VJS.")

        # --- STAGE 1: Run Oracles ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'ORACLE_EXECUTION', 'active')
        full_golden_input = f"{len(pretests)}\n" + "\n".join(t['input'] for t in pretests)
        golden_input_path = os.path.join(vjs_temp_dir, "golden.in")
        with open(golden_input_path, "w") as f:
            f.write(full_golden_input)

        oracle_full_outputs = []
        user_id = f"{os.getuid()}:{os.getgid()}"

        with ThreadPoolExecutor(max_workers=len(oracle_paths)) as executor:
            def run_binary_full(exec_path):
                host_dir = os.path.dirname(exec_path)
                exec_name = os.path.basename(exec_path)
                total_oracle_time_sec = (time_limit_ms / 1000.0) * len(pretests) + 5.0
                run_cmd = [
                    "docker", "run", "--rm", "-u", user_id, "-i",
                    "--ulimit", "stack=268435456",
                    f"--memory={memory_limit_kb}k",
                    "-v", f"{host_dir}:/app:ro", "-w", "/app",
                    "synapse-judge",
                    "timeout", str(total_oracle_time_sec), f"./{exec_name}",
                ]
                with open(golden_input_path, 'r') as stdin_f:
                    proc = subprocess.run(
                        run_cmd, stdin=stdin_f, capture_output=True, text=True,
                        timeout=total_oracle_time_sec + 5,
                    )
                if proc.returncode != 0:
                    return f"ORACLE_RUNTIME_ERROR_CODE_{proc.returncode}"
                return proc.stdout.strip().replace('\r\n', '\n')

            futures = {executor.submit(run_binary_full, path): path for path in oracle_paths}
            for future in as_completed(futures):
                oracle_full_outputs.append(future.result())

        # --- STAGE 2: Tiered Consensus ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'CONSENSUS_VOTE', 'active')
        consensus_output = None

        # Tier 1: Weighted Vote
        scores = {out: 0 for out in oracle_full_outputs if "RUNTIME_ERROR" not in out}
        for i, output in enumerate(oracle_full_outputs):
            if output in scores:
                rating = oracle_ratings.get(f"oracle_{i}", {}).get("rating", "Poor")
                scores[output] += rating_weights.get(rating, 1)

        if scores:
            best_output = max(scores, key=scores.get)
            if scores[best_output] >= (MIN_VIABLE_ORACLES * rating_weights['Fair']):
                consensus_output = best_output
                logging.info(f"[{problem_id}] Consensus found by main weighted vote.")

        # Tier 2: Recount with trusted council if main vote fails
        if consensus_output is None:
            logging.warning(f"[{problem_id}] Main vote failed. Performing a recount.")
            recount_scores = {}
            trusted_council_size = 0
            for i, output in enumerate(oracle_full_outputs):
                rating = oracle_ratings.get(f"oracle_{i}", {}).get("rating", "Poor")
                if rating in ['Excellent', 'Good', 'Fair']:
                    trusted_council_size += 1
                    if "RUNTIME_ERROR" not in output:
                        weight = rating_weights.get(rating, 1)
                        recount_scores[output] = recount_scores.get(output, 0) + weight

            if recount_scores:
                best_output = max(recount_scores, key=recount_scores.get)
                max_score = recount_scores[best_output]
                min_score_threshold = (
                    min(MIN_VIABLE_ORACLES, trusted_council_size) * rating_weights['Fair']
                )
                if max_score >= min_score_threshold:
                    consensus_output = best_output
                    logging.info(
                        f"[{problem_id}] Consensus found by RECOUNT. "
                        f"Score: {max_score}, Threshold: {min_score_threshold}"
                    )

        # Tier 3: Quarantine if all else fails
        if consensus_output is None:
            reason = f"Consensus failed after recount. Oracle outputs: {oracle_full_outputs}"
            db.transition_to_quarantined(problem_id, reason)
            return

        golden_output_path = os.path.join(vjs_temp_dir, "golden.out")
        with open(golden_output_path, "w") as f:
            f.write(consensus_output)

        # --- STAGE 3: Judge AI Code ---
        db.update_worker_status(worker_id, 'VJS', problem_id, 'JUDGING_AI', 'active')
        ai_code_path = os.path.join(vjs_temp_dir, "main.cpp")
        with open(ai_code_path, "w") as f:
            f.write(reconstructed_code)

        compile_cmd = [
            "docker", "run", "--rm", "-u", user_id,
            "-v", f"{vjs_temp_dir}:/app", "-w", "/app",
            "synapse-judge", "g++", "main.cpp", "-o", "main",
            "-O2", "-std=c++23", "-static",
        ]
        compile_proc = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=VJS_COMPILATION_TIMEOUT
        )

        if compile_proc.returncode != 0:
            db.transition_to_pending_implementation_retry(problem_id, compile_proc.stderr[:2000])
            return

        ai_output_path = os.path.join(vjs_temp_dir, "ai.out")
        total_time_sec = (time_limit_ms / 1000.0) * len(pretests) + 2.0
        docker_run_cmd = [
            "docker", "run", "--rm", "-u", user_id, "-i",
            "--ulimit", "stack=268435456",
            f"--memory={memory_limit_kb}k",
            "-v", f"{vjs_temp_dir}:/app:ro", "-w", "/app",
            "synapse-judge", "timeout", str(total_time_sec), "./main",
        ]

        with open(golden_input_path, 'r') as stdin_f, open(ai_output_path, 'w') as stdout_f:
            run_proc = subprocess.run(
                docker_run_cmd, stdin=stdin_f, stdout=stdout_f,
                stderr=subprocess.PIPE, text=True, timeout=total_time_sec + 5,
            )

        if run_proc.returncode != 0:
            report = (
                f"AI code failed execution (exit code {run_proc.returncode}). "
                f"Stderr: {run_proc.stderr}"
            )
            db.transition_to_pending_analysis_retry(problem_id, report)
            return

        checker_cmd = [
            "python", "-m", "synapse.checker",
            golden_input_path, ai_output_path, golden_output_path,
        ]
        checker_proc = subprocess.run(checker_cmd, capture_output=True, text=True)

        if checker_proc.returncode != 0:
            report = f"WA/PE on full test suite.\nChecker Msg: {checker_proc.stdout.strip()}"
            db.transition_to_pending_analysis_retry(problem_id, report)
            return

            return

        # =====================================================================
        # --- STAGE 4: Fuzz Testing ---
        # =====================================================================
        input_generator_py = workspace_data.get('input_generator_py')
    
        if not input_generator_py:
            # No fuzzer available, bypass fuzzing sequence entirely!
            logging.info(f"[{problem_id}] No Python fuzzer attached. Skipping STAGE 4 Fuzzing.")
            db._update_problem_status(problem_id, None, extra_updates={'confidence_level': 2})
            db.transition_to_pending_data_assembly(problem_id)
            return

        db.update_worker_status(worker_id, 'VJS', problem_id, 'FUZZ_TESTING', 'active')
        logging.info(f"[{problem_id}] Pretests passed! Proceeding to STAGE 4 (Fuzz Testing)")

        MAX_FUZZ_RETRIES = 3
        fuzz_retries = 0
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            query = "SELECT COUNT(*) FROM process_history WHERE problem_id=? AND event_type='RETRY_LOOP' AND details LIKE 'Fuzzer logic bad%'"
            if db.USE_POSTGRES:
                cur = conn.cursor()
                cur.execute(query.replace('?', '%s'), (problem_id,))
                fuzz_retries = cur.fetchone()[0]
            else:
                cur = conn.execute(query, (problem_id,))
                fuzz_retries = cur.fetchone()[0]

        fuzzer_script_path = os.path.join(vjs_temp_dir, "fuzzer.py")
        with open(fuzzer_script_path, "w") as f:
            f.write(input_generator_py)

        N_FUZZ_TESTS = 10
        fuzz_tests_list = []
        for i in range(N_FUZZ_TESTS):
            # Run Fuzzer natively
            proc = subprocess.run(["python", fuzzer_script_path], capture_output=True, text=True, timeout=5.0)
            if proc.returncode != 0:
                if fuzz_retries >= MAX_FUZZ_RETRIES:
                    logging.warning(f"[{problem_id}] MAX Fuzzer retries ({fuzz_retries}) exceeded. Skipping fuzzing.")
                    break
                report = f"Fuzz test generator script crashed!\nStderr:\n{proc.stderr}"
                db.transition_to_pending_fuzz_generation_retry(problem_id, report)
                return
            
            raw_input = proc.stdout.strip()
            if not raw_input:
                continue
            
            fuzz_in_path = os.path.join(vjs_temp_dir, f"fuzz_{i}.in")
            with open(fuzz_in_path, "w") as f:
                f.write(f"1\n{raw_input}")

            # 1. Oracle Consensus on this fuzz test
            fuzz_oracle_outputs = []
            with ThreadPoolExecutor(max_workers=len(oracle_paths)) as executor:
                def run_oracle_fuzz(exec_path):
                    host_dir = os.path.dirname(exec_path)
                    exec_name = os.path.basename(exec_path)
                    run_cmd = [
                        "docker", "run", "--rm", "-u", user_id, "-i",
                        "--ulimit", "stack=268435456",
                        f"--memory={memory_limit_kb}k",
                        "-v", f"{host_dir}:/app:ro", "-w", "/app",
                        "synapse-judge", "timeout", "5.0", f"./{exec_name}",
                    ]
                    with open(fuzz_in_path, 'r') as stdin_f:
                        opro = subprocess.run(run_cmd, stdin=stdin_f, capture_output=True, text=True, timeout=10.0)
                    if opro.returncode != 0: return "RUNTIME_ERROR"
                    return opro.stdout.strip().replace('\r\n', '\n')

                futures = {executor.submit(run_oracle_fuzz, path): path for path in oracle_paths}
                for f_fut in as_completed(futures):
                    fuzz_oracle_outputs.append(f_fut.result())

            # Tier 1 Consensus
            scores = {out: 0 for out in fuzz_oracle_outputs if "RUNTIME_ERROR" not in out}
            for j, out in enumerate(fuzz_oracle_outputs):
                if out in scores:
                    rating = oracle_ratings.get(f"oracle_{j}", {}).get("rating", "Poor")
                    scores[out] += rating_weights.get(rating, 1)

            consensus_out = None
            if scores:
                best_out = max(scores, key=scores.get)
                if scores[best_out] >= (MIN_VIABLE_ORACLES * rating_weights['Fair']):
                    consensus_out = best_out
            
            if consensus_out is None:
                if fuzz_retries >= MAX_FUZZ_RETRIES:
                    logging.warning(f"[{problem_id}] MAX Fuzzer retries exceeded. Corrupt generation sequence. Skipping Fuzz testing.")
                    break
                report = f"Fuzz test #{i+1} caused Oracle Consensus Failure! The fuzzer generated invalid boundaries.\nInput generated:\n{raw_input[:500]}"
                db.transition_to_pending_fuzz_generation_retry(problem_id, report)
                return
            
            fuzz_out_path = os.path.join(vjs_temp_dir, f"fuzz_{i}.out")
            with open(fuzz_out_path, "w") as f:
                f.write(consensus_out)

            # 2. Run AI Binary on fuzz test
            ai_fuzz_out_path = os.path.join(vjs_temp_dir, f"ai_fuzz_{i}.out")
            with open(fuzz_in_path, 'r') as stdin_f, open(ai_fuzz_out_path, 'w') as stdout_f:
                run_proc = subprocess.run(docker_run_cmd, stdin=stdin_f, stdout=stdout_f, stderr=subprocess.PIPE, text=True, timeout=10.0)
            
            if run_proc.returncode != 0:
                report = f"AI code execution crashed on FUZZ Test #{i+1}.\nGenerated Fuzz Input:\n{raw_input}\nStderr:\n{run_proc.stderr}"
                db.transition_to_pending_analysis_retry(problem_id, report)
                return

            fuzz_checker_proc = subprocess.run(["python", "-m", "synapse.checker", fuzz_in_path, ai_fuzz_out_path, fuzz_out_path], capture_output=True, text=True)
            if fuzz_checker_proc.returncode != 0:
                report = f"WA/PE on FUZZ Test #{i+1}.\nGenerated Input:\n{raw_input}\nExpected output:\n{consensus_out}\nChecker Msg: {fuzz_checker_proc.stdout.strip()}"
                db.transition_to_pending_analysis_retry(problem_id, report)
                return

            fuzz_tests_list.append({
                "input": f"1\n{raw_input}",
                "output": consensus_out
            })

        if fuzz_tests_list:
            __save_generated_tests(problem_id, fuzz_tests_list)
            db._update_problem_status(problem_id, None, extra_updates={'confidence_level': 3})
            logging.info(f"SUCCESS [Final VJS] for {problem_id}. All Fuzz tests passed. -> pending_data_assembly")
        else:
            db._update_problem_status(problem_id, None, extra_updates={'confidence_level': 2})
            logging.info(f"SUCCESS [Final VJS] for {problem_id}. -> pending_data_assembly")

        db.transition_to_pending_data_assembly(problem_id)

    except Exception as e:
        logging.error(f"FAILED [Final VJS] for {problem_id}: {e}", exc_info=True)
        db.transition_to_failed(problem_id, 'vjs', str(e))
    finally:
        if os.path.exists(vjs_temp_dir):
            shutil.rmtree(vjs_temp_dir)
        db.update_worker_status(worker_id, 'VJS', None, None, 'idle')
