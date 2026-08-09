# synapse/workers/assembly.py
"""
Stage 6: Data Assembly Worker

Performs the final step for a successfully verified problem. Assembles
the "golden record" from all workspace data, appends it to dataset.jsonl,
and cleans up temporary files.
"""
from ._shared import (
    logging, json, os, shutil, time,
    Dict, Any,
    db,
)
from synapse.data_assembly import _assemble_golden_record
from synapse.data_manager import append_to_dataset


def data_assembly_worker(problem: Dict[str, Any], worker_id: str):
    """
    Performs the final step for a successfully verified problem. It assembles
    the "golden record" from all the data in the workspace, appends it to the
    final dataset.jsonl file, and cleans up the temporary data.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', problem_id, 'ASSEMBLING', 'active')
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data:
            raise Exception("Workspace data not found.")

        golden_record = _assemble_golden_record(problem_id, workspace_data)
        append_to_dataset(golden_record)

        # Clean up compiled oracle temp directories
        logging.info(f"[{problem_id}] Performing final cleanup of temporary files.")
        compiled_paths = json.loads(workspace_data.get('compiled_oracle_paths_json', '[]'))
        dirs_to_delete = {os.path.dirname(p) for p in compiled_paths}
        for d in dirs_to_delete:
            if os.path.exists(d):
                shutil.rmtree(d)
                logging.info(f"[{problem_id}] Removed temporary directory: {d}")

        # Clean workspace DB entry and transition to completed
        db.cleanup_workspace(problem_id)
        db.transition_to_completed(problem_id)
        logging.info(f"SUCCESS [Data Assembly] for {problem_id}. -> completed")

    except Exception as e:
        logging.error(f"FAILED [Data Assembly] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'data_assembly', str(e))
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        success = 'e' not in locals() or locals()['e'] is None
        db.log_metric(
            'DATA_ASSEMBLY', 'assembly_task', duration_ms, success,
            {'problem_id': problem_id},
        )
        db.update_worker_status(worker_id, 'DATA_ASSEMBLY', None, None, 'idle')
