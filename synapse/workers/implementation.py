# synapse/workers/implementation.py
"""
Stage 4: Implementation Worker

Takes pseudocode for a single problem and uses the Groq "Implementer" LLM
to generate a C++ solution. Handles quarantine logic for problems that
repeatedly fail to produce compilable code.
"""
from ._shared import (
    logging, time, Dict, Any,
    db, KeyManager, MAX_IMPLEMENTATION_RETRIES,
)
from synapse.api_clients import call_groq_implementer


def implementation_worker(problem: Dict[str, Any], worker_id: int, groq_km: KeyManager):
    """
    Takes pseudocode for a single problem and uses the Groq "Implementer" LLM
    to generate a C++ solution. Handles quarantine logic for problems that
    repeatedly fail to produce compilable code.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
        groq_km: The KeyManager for Groq API keys.
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        # Check for max implementation retries
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT implementation_try_count FROM problems WHERE id = ?",
                (problem_id,),
            )
            result = cursor.fetchone()
        if result and result[0] >= MAX_IMPLEMENTATION_RETRIES:
            reason = f"Exceeded max implementation retries ({MAX_IMPLEMENTATION_RETRIES})."
            db.transition_to_quarantined(problem_id, reason)
            return

        # Get data from workspace
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'FETCH_DATA', 'active')
        p_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not p_data or not p_data.get('arl_pseudocode'):
            raise Exception("Pseudocode not found in workspace data.")

        # Call API and update database
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'API_CALL', 'active')
        reconstructed_code = call_groq_implementer(
            problem_html=p_data.get('problem_statement_html'),
            pseudocode=p_data.get('arl_pseudocode'),
            vjs_report=p_data.get('last_vjs_report'),
            key_manager=groq_km,
        )
        db.update_workspace_with_implementation_results(problem_id, reconstructed_code)
        db.transition_to_pending_vjs(problem_id)
        logging.info(f"SUCCESS [Implementation] for {problem_id}. -> pending_vjs")

    except Exception as e:
        logging.error(f"FAILED [Implementation] for {problem_id}: {e}", exc_info=False)
        db.transition_to_failed(problem_id, 'implementation', str(e))
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        success = 'e' not in locals() or locals()['e'] is None
        db.log_metric(
            'IMPLEMENTATION', 'implementation_task', duration_ms, success,
            {'problem_id': problem_id},
        )
        db.update_worker_status(worker_id, 'IMPLEMENTATION', None, None, 'idle')
