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
from typing import List, Dict, Any
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

def run_vjs(problem_id: str, code: str, pretests: List[Dict], time_limit_ms: int, memory_limit_kb: int) -> Dict[str, Any]:
    """
    Compiles and runs C++ code in a Docker sandbox against pretests.

    Args:
        problem_id: The ID of the problem being tested.
        code: The C++ source code to test.
        pretests: A list of {'input': str, 'output': str} dictionaries.
        time_limit_ms: The time limit in milliseconds.
        memory_limit_kb: The memory limit in kilobytes.

    Returns:
        A dictionary with the outcome ('SUCCESS', 'COMPILE_ERROR', etc.) and a report.
    """
    if not client:
        return {'status': 'VJS_ERROR', 'report': 'Docker client not available.'}

    host_dir = os.path.join(os.getcwd(), "temp_vjs", problem_id)
    os.makedirs(host_dir, exist_ok=True)
    container = None
    try:
        with open(os.path.join(host_dir, "main.cpp"), "w", encoding="utf-8") as f:
            f.write(code)
        for i, test in enumerate(pretests):
            with open(os.path.join(host_dir, f"{i+1}.in"), "w", encoding="utf-8") as f:
                f.write(test['input'])

        # Compile
        compile_cmd = "g++ main.cpp -o main -O2 -std=c++17 -static"
        container = client.containers.run("synapse-judge", command=compile_cmd, volumes={host_dir: {'bind': '/app', 'mode': 'rw'}}, working_dir="/app", detach=True)
        result = container.wait(timeout=VJS_COMPILATION_TIMEOUT)
        if result['StatusCode'] != 0:
            logs = container.logs(stderr=True, stdout=False).decode('utf-8', 'ignore')
            return {'status': 'COMPILE_ERROR', 'report': logs[:1000]}
        container.remove()
        container = None

        # Run against pretests
        for i, test in enumerate(pretests):
            timeout_sec = (time_limit_ms / 1000.0) + 1.0
            run_cmd = f"/usr/bin/timeout {timeout_sec}s ./main"
            
            with open(os.path.join(host_dir, f"{i+1}.in"), "rb") as stdin_file:
                container = client.containers.run("synapse-judge", command=run_cmd, stdin_open=True, volumes={host_dir: {'bind': '/app', 'mode': 'ro'}}, working_dir="/app", mem_limit=f"{memory_limit_kb}k", detach=True)
                
                # Stream input to the container
                s = container.attach_socket()
                os.write(s.fileno(), stdin_file.read())
                s.close()

                result = container.wait()

                if result['StatusCode'] == 124: # Timeout exit code
                    return {'status': 'TIME_LIMIT_EXCEEDED', 'report': f'Time limit exceeded on test {i+1}'}
                elif result['StatusCode'] != 0:
                    return {'status': 'RUNTIME_ERROR', 'report': f'Runtime error on test {i+1} with exit code {result["StatusCode"]}'}

                actual_output = container.logs(stdout=True, stderr=False).decode('utf-8', 'ignore').strip().replace('\r\n', '\n')
                expected_output = test['output'].strip().replace('\r\n', '\n')

                if actual_output != expected_output:
                    return {'status': 'WRONG_ANSWER', 'report': f'Wrong answer on test {i+1}', 'details': {
                            'test_case': i + 1, 'input': test['input'],
                            'expected_output': expected_output, 'actual_output': actual_output }}
                container.remove()
                container = None
        return {'status': 'SUCCESS', 'report': f'All {len(pretests)} tests passed'}
    except Exception as e:
        return {'status': 'VJS_ERROR', 'report': f'An unexpected VJS error occurred: {e}'}
    finally:
        if container:
            try: container.remove(force=True)
            except docker.errors.APIError: pass
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