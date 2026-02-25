# synapse/workers/calibration.py
"""
Stage 2: Calibration Worker

Compiles all N reference solutions ("oracles"), verifies a minimum number
are viable, and calculates a performance baseline (slowness_factor).
"""
from ._shared import (
    logging, json, os, Dict, Any,
    db, MIN_VIABLE_ORACLES, INITIAL_CALIBRATION_TOLERANCE_FACTOR,
)
from synapse.vjs import run_vjs
from synapse.data_assembly import _parse_time_limit, _parse_memory_limit


def calibration_worker(problem: Dict[str, Any], worker_id: str):
    """
    Compiles all N reference solutions ("oracles"), verifies a minimum number
    are viable, and calculates a performance baseline (slowness_factor).
    """
    problem_id = problem['id']
    logging.info(f"[{problem_id}] Starting CALIBRATION stage...")
    db.update_worker_status(worker_id, 'CALIBRATION', problem_id, 'COMPILING_ORACLES', 'active')

    temp_dirs_to_clean = []
    try:
        # 1. Fetch all oracle codes from the workspace
        workspace_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not workspace_data:
            raise Exception("Workspace data not found for calibration.")

        primary_code = workspace_data.get('reference_solution_code')
        secondary_codes = json.loads(workspace_data.get('secondary_reference_codes_json', '[]'))
        all_oracle_codes = [primary_code] + secondary_codes

        # 2. Compile each oracle using the compile_only flag
        compiled_oracle_paths = []
        for i, code in enumerate(all_oracle_codes):
            if not code:
                continue
            vjs_suffix = f"_oracle_{i}"
            result = run_vjs(
                problem_id, code, [], 1000, 262144,
                suffix=vjs_suffix, compile_only=True,
            )
            if result['status'] == 'SUCCESS':
                compiled_oracle_paths.append(result['executable_path'])
                temp_dirs_to_clean.append(os.path.dirname(result['executable_path']))
            else:
                logging.warning(f"[{problem_id}] Oracle {i} failed to compile.")

        # 3. Check quorum of viable oracles
        successful_oracles_count = len(compiled_oracle_paths)
        logging.info(
            f"[{problem_id}] Compiled {successful_oracles_count}/{len(all_oracle_codes)} oracles."
        )
        if successful_oracles_count < MIN_VIABLE_ORACLES:
            reason = (
                f"Failed to compile minimum number of oracles. "
                f"Needed {MIN_VIABLE_ORACLES}, got {successful_oracles_count}."
            )
            db.transition_to_quarantined(problem_id, reason)
            return

        # 4. Run primary oracle to get slowness factor
        db.update_worker_status(
            worker_id, 'CALIBRATION', problem_id, 'CALCULATING_SLOWNESS', 'active'
        )
        pretests = json.loads(workspace_data.get('pretests_json', '[]'))
        time_limit_ms = _parse_time_limit(workspace_data.get('time_limit_raw', '1s'))
        memory_limit_kb = _parse_memory_limit(workspace_data.get('memory_limit_raw', '256mb'))

        calib_run_result = run_vjs(
            problem_id, primary_code, pretests[:1],
            int(time_limit_ms * 2), memory_limit_kb, suffix="_calib_run",
        )
        if calib_run_result['status'] not in ['SUCCESS', 'PRESENTATION_ERROR']:
            raise Exception(
                f"Primary oracle failed full run during calibration: {calib_run_result['status']}"
            )

        # 5. Calculate slowness factor and checker mode
        slowness_factor = INITIAL_CALIBRATION_TOLERANCE_FACTOR
        checker_mode = (
            'set_based' if calib_run_result['status'] == 'PRESENTATION_ERROR' else 'strict'
        )

        # 6. Save and transition
        db.save_calibration_results(
            problem_id,
            successful_oracles_count,
            compiled_oracle_paths,
            pretests,
            slowness_factor,
            checker_mode,
        )
        db.transition_to_pending_analysis(problem_id)
        logging.info(
            f"[{problem_id}] Calibration SUCCEEDED. "
            f"Oracles: {successful_oracles_count}. Slowness: {slowness_factor:.2f}x. "
            f"-> pending_analysis"
        )

    except Exception as e:
        logging.error(f"FAILED [Calibration] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'calibration', str(e))
    finally:
        db.update_worker_status(worker_id, 'CALIBRATION', None, None, 'idle')
