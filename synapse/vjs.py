# synapse/vjs.py
import docker
import os
import shutil
import logging
from typing import List, Dict
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import math
import lizard # <-- NEW IMPORT

# Initialize the Docker client from the environment
try:
    client = docker.from_env()
except docker.errors.DockerException:
    logging.error("Docker is not running or accessible. The VJS will not function.")
    client = None

def run_vjs(problem_id: str, code: str, pretests: List[Dict], time_limit_ms: int, memory_limit_kb: int) -> dict:
    """
    Compiles and runs C++ code in a Docker sandbox against a set of pretests.
    Returns a detailed dictionary with the outcome.
    """
    if not client:
        return {'status': 'VJS_ERROR', 'report': 'Docker client not available.'}

    host_dir = os.path.join(os.getcwd(), "temp_vjs", problem_id)
    os.makedirs(host_dir, exist_ok=True)
    
    container = None
    try:
        # 1. Write files
        with open(os.path.join(host_dir, "main.cpp"), "w", encoding="utf-8") as f:
            f.write(code)
        for i, test in enumerate(pretests):
            with open(os.path.join(host_dir, f"{i+1}.in"), "w", encoding="utf-8") as f:
                f.write(test['input'])

        # 2. Compile
        compile_cmd = "g++ main.cpp -o main -O2 -std=c++17 -static"
        container = client.containers.run("synapse-judge", command=compile_cmd, volumes={host_dir: {'bind': '/app', 'mode': 'rw'}}, working_dir="/app", detach=True)
        result = container.wait(timeout=15)
        if result['StatusCode'] != 0:
            logs = container.logs(stderr=True, stdout=False).decode('utf-8', 'ignore')
            return {'status': 'COMPILE_ERROR', 'report': logs[:1000]}
        container.remove()
        container = None

        # 3. Run against pretests
        for i, test in enumerate(pretests):
            timeout_sec = (time_limit_ms / 1000.0) + 1.0 
            run_cmd = f"/usr/bin/timeout {timeout_sec}s ./main"
            
            with open(os.path.join(host_dir, f"{i+1}.in"), "r", encoding="utf-8") as stdin_file:
                container = client.containers.run("synapse-judge", command=run_cmd, stdin_open=True, volumes={host_dir: {'bind': '/app', 'mode': 'ro'}}, working_dir="/app", mem_limit=f"{memory_limit_kb}k", detach=True)
                
                s = container.attach_socket()
                os.write(s.fileno(), stdin_file.read().encode('utf-8'))
                s.close()
                
                result = container.wait()
                
                if result['StatusCode'] == 124:
                    return {'status': 'TIME_LIMIT_EXCEEDED', 'report': f'Time limit exceeded on test {i+1}'}
                elif result['StatusCode'] != 0:
                    return {'status': 'RUNTIME_ERROR', 'report': f'Runtime error on test {i+1}'}

                actual_output = container.logs(stdout=True, stderr=False).decode('utf-8', 'ignore').strip().replace('\r\n', '\n')
                expected_output = test['output'].strip().replace('\r\n', '\n')
                
                # --- ENHANCEMENT START ---
                if actual_output != expected_output:
                    return {
                        'status': 'WRONG_ANSWER',
                        'report': f'Wrong answer on test {i+1}',
                        'details': {
                            'test_case': i + 1,
                            'input': test['input'],
                            'expected_output': expected_output,
                            'actual_output': actual_output
                        }
                    }
                # --- ENHANCEMENT END ---
                
                container.remove()
                container = None
    
    except Exception as e:
        return {'status': 'VJS_ERROR', 'report': f'An unexpected VJS error occurred: {e}'}
    finally:
        if container:
            try: container.kill()
            except docker.errors.APIError: pass
            finally:
                try: container.remove()
                except docker.errors.APIError: pass
        if os.path.exists(host_dir):
            shutil.rmtree(host_dir)

    return {'status': 'SUCCESS', 'report': f'All {len(pretests)} tests passed'}

def run_static_analysis(code: str) -> dict:
    # ... (this function remains the same) ...
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.cpp', delete=False) as temp_f:
            temp_filepath = temp_f.name
            temp_f.write(code)

        cmd = ["cppcheck", f"--enable=all", "--xml", temp_filepath]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        xml_output = result.stderr

        summary = {'errors': [], 'error_counts': {}}
        if not xml_output:
            return summary

        root = ET.fromstring(xml_output)
        errors_node = root.find('errors')
        if errors_node is None:
            return summary

        for error in errors_node:
            summary['errors'].append({
                'id': error.get('id'),
                'severity': error.get('severity'),
                'msg': error.get('msg'),
                'verbose': error.get('verbose'),
                'file': error.find('location').get('file') if error.find('location') is not None else None,
                'line': int(error.find('location').get('line', 0)) if error.find('location') is not None else 0
            })
            severity = error.get('severity', 'unknown')
            summary['error_counts'][severity] = summary['error_counts'].get(severity, 0) + 1
        
        return summary

    except ET.ParseError as e:
        logging.warning(f"Failed to parse cppcheck XML output: {e}")
        return {'status': 'PARSE_ERROR', 'report': str(e)}
    except Exception as e:
        logging.error(f"An unexpected error occurred in run_static_analysis: {e}")
        return {'status': 'ANALYSIS_ERROR', 'report': str(e)}
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)

# --- NEW FUNCTION ---
def run_semantic_analysis(code: str) -> dict:
    """
    Performs semantic analysis on a C++ code string using 'lizard'.
    Calculates Cyclomatic Complexity (CC), NLOC, and Maintainability Index (MI).
    """
    if not code:
        return {}

    try:
        # Use lizard to analyze the code string directly
        # The 'input.cpp' is just a placeholder filename for the analysis context
        analysis = lizard.analyze_source_code("input.cpp", code)

        if not analysis.function_list:
            return {"error": "No functions found by lizard."}

        # Aggregate metrics across all functions in the file
        total_nloc = sum(f.nloc for f in analysis.function_list)
        # We use the average complexity as a representative metric
        avg_cyclomatic_complexity = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)

        # Calculate Maintainability Index (simplified version without Halstead)
        # MI = 171 - 5.2 * log2(avg_volume) - 0.23 * avg_cc - 16.2 * log2(avg_loc)
        # Since Halstead Volume is complex, we use a common variant that omits it.
        # A higher MI score (0-100) is better.
        mi_log_loc = math.log2(total_nloc) if total_nloc > 0 else 0
        maintainability_index = 171 - (0.23 * avg_cyclomatic_complexity) - (16.2 * mi_log_loc)

        return {
            "avg_cyclomatic_complexity": round(avg_cyclomatic_complexity, 2),
            "total_nloc": total_nloc,
            "maintainability_index": round(max(0, maintainability_index * 100 / 171), 2),
            "function_count": len(analysis.function_list)
        }
    except Exception as e:
        logging.error(f"Lizard analysis failed: {e}")
        return {"error": str(e)}
