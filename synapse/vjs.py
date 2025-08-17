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

# EXPERIMENT: Added an optional `suffix` parameter to create unique directories
# for benchmarking the reference code vs. the reconstructed code.
def run_vjs(problem_id: str, code: str, pretests: List[Dict], time_limit_ms: int, memory_limit_kb: int, suffix: str = "") -> Dict[str, Any]:
    """
    Compiles and runs C++ code in a Docker sandbox against pretests.
    (V3 - Enhanced with verbose logging)
    """
    if not client:
        return {'status': 'VJS_ERROR', 'report': 'Docker client not available.'}
    
    # --- NEW: Verbose Logging ---
    logging.info(f"--- VJS START: Problem {problem_id}{suffix} ---")
    
    dir_name = f"{problem_id}{suffix}"
    host_dir = os.path.join(os.getcwd(), "temp_vjs", dir_name)
    os.makedirs(host_dir, exist_ok=True)
    
    try:
        # --- STAGE 1: Compilation ---
        logging.info(f"[{problem_id}] Stage 1: Compiling source code...")
        source_path = os.path.join(host_dir, "main.cpp")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(code)

        abs_host_dir = os.path.abspath(host_dir)
        
        compile_cmd = [
            "docker", "run", "--rm",
            "-v", f"{abs_host_dir}:/app",
            "-w", "/app",
            "synapse-judge",
            "g++", "main.cpp", "-o", "main", "-O2", "-std=c++20", "-static"
        ]

        compile_proc = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=VJS_COMPILATION_TIMEOUT)

        if compile_proc.returncode != 0:
            logging.error(f"[{problem_id}] Compilation FAILED. Exit code: {compile_proc.returncode}")
            return {'status': 'COMPILE_ERROR', 'report': compile_proc.stderr[:2000]}
        
        logging.info(f"[{problem_id}] Compilation SUCCEEDED.")

        # --- STAGE 2: Execution per Test Case ---
        logging.info(f"[{problem_id}] Stage 2: Executing {len(pretests)} test cases...")
        total_execution_time_ms = 0
        for i, test in enumerate(pretests):
            test_num_str = f"Test {i+1}/{len(pretests)}"
            logging.info(f"[{problem_id}] Running {test_num_str}...")

            timeout_sec = (time_limit_ms / 1000.0) + 2.0
            
            run_cmd_inside_container = f"/usr/bin/time -f \"%e\" ./main"
            
            docker_run_cmd = [
                "docker", "run", "--rm", "-i",
                "--memory", f"{memory_limit_kb}k",
                "-v", f"{abs_host_dir}:/app:ro",
                "-w", "/app",
                "synapse-judge",
                "timeout", str(timeout_sec),
                "/bin/sh", "-c", run_cmd_inside_container
            ]

            input_data = test['input']
            
            try:
                run_proc = subprocess.run(
                    docker_run_cmd,
                    input=input_data,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec + 5
                )
            except subprocess.TimeoutExpired:
                logging.warning(f"[{problem_id}] {test_num_str}: VJS subsystem timed out.")
                return {'status': 'TIME_LIMIT_EXCEEDED', 'report': f'VJS subsystem timed out on test {i+1}.'}

            if run_proc.returncode == 124:
                logging.warning(f"[{problem_id}] {test_num_str}: TIME_LIMIT_EXCEEDED.")
                return {'status': 'TIME_LIMIT_EXCEEDED', 'report': f'Time limit exceeded on test {i+1}'}
            elif run_proc.returncode != 0:
                logging.error(f"[{problem_id}] {test_num_str}: RUNTIME_ERROR (Exit Code: {run_proc.returncode}).")
                return {'status': 'RUNTIME_ERROR', 'report': f'Runtime error on test {i+1} with exit code {run_proc.returncode}. Stderr: {run_proc.stderr}'}

            try:
                time_output = run_proc.stderr.strip()
                elapsed_sec = float(time_output.splitlines()[-1])
                total_execution_time_ms += int(elapsed_sec * 1000)
            except (ValueError, IndexError):
                logging.warning(f"[{problem_id}] Could not parse execution time for {test_num_str}. Stderr: {run_proc.stderr}")

            actual_output = run_proc.stdout.strip().replace('\r\n', '\n')
            expected_output = test['output'].strip().replace('\r\n', '\n')

            if actual_output != expected_output:
                logging.warning(f"[{problem_id}] {test_num_str}: WRONG_ANSWER.")
                # --- NEW: Log the input/output diff for immediate diagnosis ---
                logging.warning(f"--> Input:\n{test['input']}")
                logging.warning(f"--> Expected Output:\n{expected_output}")
                logging.warning(f"--> Actual Output:\n{actual_output}")
                return {'status': 'WRONG_ANSWER', 'report': f'Wrong answer on test {i+1}', 'details': {
                    'test_case': i + 1, 'input': test['input'],
                    'expected_output': expected_output, 'actual_output': actual_output }}
            
            # --- NEW: Log success for the test case ---
            logging.info(f"[{problem_id}] {test_num_str}: PASSED.")
        
        logging.info(f"--- VJS SUCCESS: All {len(pretests)} tests passed for {problem_id}{suffix} ---")
        return {'status': 'SUCCESS', 'report': f'All {len(pretests)} tests passed', 'execution_time_ms': total_execution_time_ms}

    except Exception as e:
        logging.critical(f"--- VJS CRITICAL ERROR: An unexpected exception occurred for {problem_id}{suffix}: {e} ---", exc_info=True)
        return {'status': 'VJS_ERROR', 'report': f'An unexpected VJS error occurred: {e}'}
    finally:
        if os.path.exists(host_dir):
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