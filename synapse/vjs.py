# synapse/vjs.py
import docker
import os
import shutil
import logging
from typing import List, Dict

# Initialize the Docker client from the environment
try:
    client = docker.from_env()
except docker.errors.DockerException:
    logging.error("Docker is not running or accessible. The VJS will not function.")
    client = None

def run_vjs(problem_id: str, code: str, pretests: List[Dict], time_limit_ms: int, memory_limit_kb: int) -> dict:
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
                
                if actual_output != expected_output:
                    return {'status': 'WRONG_ANSWER', 'report': f'Wrong answer on test {i+1}'}
                
                container.remove()
                container = None
    
    except Exception as e:
        return {'status': 'VJS_ERROR', 'report': f'An unexpected VJS error occurred: {e}'}
    finally:
        # --- NEW ROBUST CLEANUP ---
        if container:
            try:
                container.kill()
            except docker.errors.APIError:
                pass # Ignore error if container is already stopped
            finally:
                try:
                    container.remove()
                except docker.errors.APIError:
                    pass # Ignore error if container is already removed
        if os.path.exists(host_dir):
            shutil.rmtree(host_dir)

    return {'status': 'SUCCESS', 'report': f'All {len(pretests)} tests passed'}