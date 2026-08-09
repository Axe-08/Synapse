# synapse/vjs.py
"""
Verification & Judging Subsystem (VJS) and Code Quality Analysis.
This module provides the core functionality for verifying the correctness of
AI-generated code and analyzing its quality.
-   `run_vjs`: Creates a secure Docker sandbox to compile and run C++ code
    against a set of pretests, enforcing time and memory limits.
-   `run_static_analysis`: Uses `cppcheck` to find potential bugs, style
    errors, and performance issues in C++ code.
-   `run_semantic_analysis`: Uses `lizard` to calculate code complexity metrics
    like Cyclomatic Complexity and the Maintainability Index.
"""
import docker
import os
import shutil
import logging
from typing import List, Dict, Any, Optional
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import math
import lizard
from config import VJS_COMPILATION_TIMEOUT

try:
    client = docker.from_env()
except docker.errors.DockerException:
    logging.error("Docker is not running or accessible. The VJS will not function.")
    client = None

# Verdict constants, to be used by the worker
ACCEPTED = 0
WRONG_ANSWER = 1
PRESENTATION_ERROR = 2

def _truncate_text(text: str, max_len: int = 2000) -> str:
    """Truncates text to a max length, showing the start and end."""
    return text
def run_vjs(problem_id: str, code: str, pretests: List[Dict], time_limit_ms: int, memory_limit_kb: int, suffix: str = "", compile_only: bool = False) -> Dict[str, Any]:
    """
    Compiles and runs C++ code in a Docker sandbox.
    If compile_only is True, it only compiles and returns the executable path.
    """
    logging.info(f"--- VJS START: Problem {problem_id}{suffix} ---")
    dir_name = f"{problem_id}{suffix.replace(' ', '_')}"
    host_dir = os.path.join(os.getcwd(), "temp_vjs", dir_name)
    os.makedirs(host_dir, exist_ok=True)
    abs_host_dir = os.path.abspath(host_dir)
    user_id = f"{os.getuid()}:{os.getgid()}"
    try:
        # --- STAGE 1: Compilation ---
        logging.info(f"[{problem_id}] Stage 1: Compiling source code...")
        source_path = os.path.join(host_dir, "main.cpp")
        with open(source_path, "w", encoding="utf-8") as f: f.write(code)

        compile_cmd = ["docker", "run", "--rm","-u",user_id, "-v", f"{abs_host_dir}:/app", "-w", "/app", "synapse-judge", "g++", "main.cpp", "-o", "main", "-O2", "-std=c++23", "-static"]
        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=VJS_COMPILATION_TIMEOUT)

        if compile_proc.returncode != 0:
            logging.error(f"[{problem_id}] Compilation FAILED.")
            return {'status': 'COMPILE_ERROR', 'report': compile_proc.stderr[:2000]}
        
        logging.info(f"[{problem_id}] Compilation SUCCEEDED.")
        
        if compile_only:
            executable_path = os.path.join(abs_host_dir, "main")
            return {'status': 'SUCCESS', 'executable_path': executable_path}

        if not pretests:
            logging.warning(f"[{problem_id}] No pretests provided for full run. VJS complete.")
            return {'status': 'SUCCESS', 'report': 'No pretests to run.', 'execution_time_ms': 0}

        # --- STAGE 2: Execution & Checking per Test Case ---
        total_execution_time_ms = 0
        logging.info(f"[{problem_id}] Stage 2: Executing {len(pretests)} test cases...")
        for i, test in enumerate(pretests):
            test_num_str = f"Test {i+1}/{len(pretests)}"
            logging.info(f"[{problem_id}] Running {test_num_str}...")

            input_path = os.path.join(host_dir, f"{i+1}.in")
            answer_path = os.path.join(host_dir, f"{i+1}.ans")
            output_path = os.path.join(host_dir, f"{i+1}.out")

            with open(input_path, "w", encoding='utf-8') as f: f.write(test['input'])
            with open(answer_path, "w", encoding='utf-8') as f: f.write(test['output'])

            timeout_sec = (time_limit_ms / 1000.0) + 2.0
            run_cmd_inside = f"/usr/bin/time -f \"%e\" ./main"
            docker_run_cmd = ["docker", "run", "--rm","-u",user_id, "-i","--ulimit", "stack=268435456", "--memory", f"{memory_limit_kb}k", "-v", f"{abs_host_dir}:/app:ro", "-w", "/app", "synapse-judge", "timeout", str(timeout_sec), "/bin/sh", "-c", run_cmd_inside]

            with open(input_path, 'r') as stdin_f, open(output_path, 'w') as stdout_f:
                try:
                    run_proc = subprocess.run(docker_run_cmd, stdin=stdin_f, stdout=stdout_f, stderr=subprocess.PIPE, text=True, timeout=timeout_sec + 5)
                except subprocess.TimeoutExpired:
                    report = f"TLE on {test_num_str} (VJS Subsystem Timeout).\n\n--- INPUT ---\n{test['input'][:2000]}"
                    return {'status': 'TIME_LIMIT_EXCEEDED', 'report': report}

            if run_proc.returncode == 124:
                report = f"TLE on {test_num_str}.\n\n--- INPUT ---\n{test['input'][:2000]}"
                return {'status': 'TIME_LIMIT_EXCEEDED', 'report': report}
            if run_proc.returncode == 137:
                report = f"MLE on {test_num_str}.\n\n--- INPUT ---\n{test['input'][:2000]}"
                return {'status': 'MEMORY_LIMIT_EXCEEDED', 'report': report}
            if run_proc.returncode != 0:
                report = f"RE on {test_num_str} (exit code {run_proc.returncode}).\n\n--- INPUT ---\n{test['input'][:2000]}"
                return {'status': 'RUNTIME_ERROR', 'report': report}

            try:
                time_output = run_proc.stderr.strip()
                elapsed_sec = float(time_output.splitlines()[-1])
                total_execution_time_ms += int(elapsed_sec * 1000)
            except (ValueError, IndexError):
                logging.warning(f"[{problem_id}] Could not parse execution time for {test_num_str}.")

            checker_cmd = ["python", "-m", "synapse.checker", input_path, output_path, answer_path]
            checker_proc = subprocess.run(checker_cmd, capture_output=True, text=True)

            if checker_proc.returncode in [1, 2]: # WRONG_ANSWER or PRESENTATION_ERROR
                user_output = "[Could not read user output file]"
                try:
                    with open(output_path, 'r', encoding='utf-8') as f: user_output = f.read()
                except IOError: pass
                
                verdict = "WA" if checker_proc.returncode == 1 else "PE"
                report = (
                    f"{verdict} on {test_num_str}: {checker_proc.stdout.strip()}\n\n"
                    f"--- INPUT ---\n{test['input'][:2000]}\n\n"
                    f"--- EXPECTED OUTPUT ---\n{test['output'][:2000]}\n\n"
                    f"--- ACTUAL OUTPUT ---\n{user_output[:2000]}"
                )
                status = 'WRONG_ANSWER' if verdict == "WA" else 'PRESENTATION_ERROR'
                return {'status': status, 'report': report}

            if checker_proc.returncode != 0: # ACCEPTED is 0
                return {'status': 'VJS_ERROR', 'report': f'Checker failed on {test_num_str}: {checker_proc.stdout.strip()}'}
            
            logging.info(f"[{problem_id}] {test_num_str}: PASSED.")

        logging.info(f"--- VJS SUCCESS: All {len(pretests)} tests passed for {problem_id}{suffix} ---")
        return {'status': 'SUCCESS', 'report': f'All {len(pretests)} tests passed', 'execution_time_ms': total_execution_time_ms}
    finally:
        # Only clean up the directory if we were doing a full run.
        # The calibration_worker is responsible for cleaning up compile_only directories.
        if os.path.exists(host_dir) and not compile_only:
            shutil.rmtree(host_dir)

def run_static_analysis(code: str) -> Dict[str, Any]:
    """Runs cppcheck for static analysis on a C++ code string."""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.cpp', delete=False) as temp_f:
        temp_filepath = temp_f.name
        temp_f.write(code)
    try:
        cmd = ["cppcheck", "--enable=all", "--xml", temp_filepath]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        xml_output = result.stderr
        summary = {'errors': [], 'error_counts': {}}
        if not xml_output: return summary

        root = ET.fromstring(xml_output)
        errors_node = root.find('errors')
        if errors_node is None: return summary

        for error in errors_node:
            severity = error.get('severity', 'unknown')
            summary['errors'].append({'id': error.get('id'), 'severity': severity, 'msg': error.get('msg')})
            summary['error_counts'][severity] = summary['error_counts'].get(severity, 0) + 1
        return summary
    except ET.ParseError as e:
        return {'error': 'PARSE_ERROR', 'report': str(e)}
    except Exception as e:
        return {'error': 'ANALYSIS_ERROR', 'report': str(e)}
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

def run_semantic_analysis(code: str) -> Dict[str, Any]:
    """
    Performs semantic analysis using 'lizard' to calculate complexity metrics.
    """
    if not code: return {}
    try:
        analysis = lizard.analyze_source_code("input.cpp", code)
        if not analysis.function_list:
            return {"error": "No functions found by lizard."}

        total_nloc = sum(f.nloc for f in analysis.function_list)
        avg_cc = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)

        # Calculate Maintainability Index (MI)
        mi_log_loc = math.log2(total_nloc) if total_nloc > 0 else 0
        mi = 171 - (0.23 * avg_cc) - (16.2 * mi_log_loc)
        # Normalize MI to a 0-100 scale
        normalized_mi = max(0, mi * 100 / 171)

        return {
            "avg_cyclomatic_complexity": round(avg_cc, 2),
            "total_nloc": total_nloc,
            "maintainability_index": round(normalized_mi, 2),
            "function_count": len(analysis.function_list)
        }
    except Exception as e:
        return {"error": str(e)}


# ── Fuzz Test Generator Pipeline ─────────────────────────────────────────

import hashlib


def run_fuzz_generator(generator_py: str, count: int = 20, timeout_per_run: int = 5) -> List[str]:
    """
    Execute a Python generator script `count` times, capturing stdout each time.

    The generator script should print a valid random test input to stdout.

    Args:
        generator_py: Python source code that generates a random test input.
        count: Number of times to run the generator.
        timeout_per_run: Max seconds per execution.

    Returns:
        List of generated input strings (only successful runs).
    """
    inputs = []
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        gen_path = f.name
        f.write(generator_py)

    try:
        for i in range(count):
            try:
                result = subprocess.run(
                    ['python3', gen_path],
                    capture_output=True, text=True,
                    timeout=timeout_per_run,
                )
                if result.returncode == 0 and result.stdout.strip():
                    inputs.append(result.stdout.strip())
                else:
                    logging.debug(
                        f"Fuzz generator run {i+1}/{count} failed: "
                        f"exit={result.returncode} stderr={result.stderr[:200]}"
                    )
            except subprocess.TimeoutExpired:
                logging.debug(f"Fuzz generator run {i+1}/{count} timed out.")
            except Exception as e:
                logging.debug(f"Fuzz generator run {i+1}/{count} error: {e}")
    finally:
        if os.path.exists(gen_path):
            os.remove(gen_path)

    logging.info(f"Fuzz generator produced {len(inputs)}/{count} valid inputs.")
    return inputs


def validate_generated_inputs(
    inputs: List[str],
    oracle_paths: List[str],
    time_limit_ms: int = 5000,
    memory_limit_kb: int = 262144,
) -> List[Dict[str, str]]:
    """
    For each generated input, run ALL compiled oracles.
    Keep only inputs where all oracles agree on the output.

    Args:
        inputs: List of test input strings from fuzz generator.
        oracle_paths: List of absolute paths to compiled oracle executables.
        time_limit_ms: Time limit per oracle run in milliseconds.
        memory_limit_kb: Memory limit per oracle run.

    Returns:
        List of {'input': ..., 'output': ...} dicts for validated cases.
    """
    if not oracle_paths or not inputs:
        return []

    validated = []
    timeout_sec = (time_limit_ms / 1000.0) + 2.0
    user_id = f"{os.getuid()}:{os.getgid()}"

    for test_input in inputs:
        outputs = []
        all_agree = True

        for oracle_path in oracle_paths:
            oracle_dir = os.path.dirname(oracle_path)
            oracle_name = os.path.basename(oracle_path)
            try:
                run_cmd = [
                    "docker", "run", "--rm", "-u", user_id, "-i",
                    "--memory", f"{memory_limit_kb}k",
                    "-v", f"{oracle_dir}:/app:ro",
                    "-w", "/app",
                    "synapse-judge",
                    "timeout", str(timeout_sec),
                    f"./{oracle_name}",
                ]
                proc = subprocess.run(
                    run_cmd,
                    input=test_input, capture_output=True, text=True,
                    timeout=timeout_sec + 5,
                )
                if proc.returncode != 0:
                    all_agree = False
                    break
                outputs.append(proc.stdout.strip())
            except (subprocess.TimeoutExpired, Exception):
                all_agree = False
                break

        if all_agree and outputs and len(set(outputs)) == 1:
            validated.append({'input': test_input, 'output': outputs[0]})

    logging.info(
        f"Fuzz validation: {len(validated)}/{len(inputs)} inputs passed oracle consensus."
    )
    return validated


def build_combined_test_suite(
    validated_pretests: List[Dict[str, str]],
    validated_generated: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Merge pretests and generated tests into a single suite.
    Deduplicates by input hash.

    Args:
        validated_pretests: List of {'input': ..., 'output': ...} from scraping.
        validated_generated: List of {'input': ..., 'output': ...} from fuzz gen.

    Returns:
        Combined, deduplicated test suite.
    """
    seen_hashes = set()
    combined = []

    # Pretests first (they take priority)
    for test in validated_pretests:
        h = hashlib.md5(test['input'].encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            combined.append(test)

    # Then generated tests
    for test in validated_generated:
        h = hashlib.md5(test['input'].encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            combined.append(test)

    logging.info(
        f"Combined test suite: {len(combined)} tests "
        f"({len(validated_pretests)} pretests + "
        f"{len(combined) - len(validated_pretests)} generated)"
    )
    return combined