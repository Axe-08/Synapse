# synapse/workers/implementation.py
"""
Stage 4: Implementation Worker

Takes pseudocode for a single problem and uses the Groq "Implementer" LLM
to generate a C++ solution. Handles quarantine logic for problems that
repeatedly fail to produce compilable code.

Escalation ladder (uses existing retry counters, no new DB columns):
  analysis_try_count == 0: Normal Groq implementation
  analysis_try_count == 1: Groq again with simplified pseudocode (analysis re-ran in simplify mode)
  analysis_try_count >= 2: Escalate to Gemini Flash for implementation
  analysis_try_count >= 3: Quarantine (Gemini also failed)
"""
from ._shared import (
    logging, time, Dict, Any,
    db, KeyManager, MAX_IMPLEMENTATION_RETRIES,
)
from synapse.api_clients import call_groq_implementer, call_gemini_implementer


def implementation_worker(
    problem: Dict[str, Any],
    worker_id: int,
    groq_km: KeyManager,
    gemini_km: KeyManager = None,
):
    """
    Takes pseudocode for a single problem and generates a C++ solution.

    Args:
        problem: A dictionary containing the problem ID.
        worker_id: The ID of this worker thread.
        groq_km: The KeyManager for Groq API keys (primary implementer).
        gemini_km: The KeyManager for Gemini API keys (escalation fallback).
    """
    problem_id = problem['id']
    start_time = time.perf_counter()
    try:
        # Read both retry counters from DB
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT implementation_try_count, analysis_try_count FROM problems WHERE id = ?",
                (problem_id,),
            )
            result = cursor.fetchone()

        impl_tries = (result[0] if result else 0) or 0
        analysis_tries = (result[1] if result else 0) or 0

        # Quarantine guard: only quarantine if we've also exhausted Gemini escalation
        # (i.e. analysis_tries >= 3 means Gemini was tried and also failed)
        if impl_tries >= MAX_IMPLEMENTATION_RETRIES and analysis_tries >= 3:
            reason = (
                f"Exhausted all escalation paths: "
                f"{impl_tries} Groq attempts + Gemini escalation failed."
            )
            db.transition_to_quarantined(problem_id, reason)
            return

        # Get data from workspace
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'FETCH_DATA', 'active')
        p_data = db.get_batch_data_from_workspace([problem_id]).get(problem_id)
        if not p_data or not p_data.get('arl_pseudocode'):
            raise Exception("Pseudocode not found in workspace data.")

        problem_class = p_data.get('problem_class', 'standard')

        # Route to Gemini when analysis has been retried >= 2 times
        # (means Groq failed on both normal and simplified pseudocode)
        db.update_worker_status(worker_id, 'IMPLEMENTATION', problem_id, 'API_CALL', 'active')
        if analysis_tries >= 2:
            if gemini_km is None:
                raise Exception("Gemini KeyManager not provided for escalation.")
            logging.info(
                f"[{problem_id}] analysis_tries={analysis_tries}: "
                f"Escalating to Gemini Flash implementer."
            )
            reconstructed_code = call_gemini_implementer(
                problem_html=p_data.get('problem_statement_html'),
                pseudocode=p_data.get('arl_pseudocode'),
                vjs_report=p_data.get('last_vjs_report'),
                key_manager=gemini_km,
                problem_class=problem_class,
            )
        else:
            reconstructed_code = call_groq_implementer(
                problem_html=p_data.get('problem_statement_html'),
                pseudocode=p_data.get('arl_pseudocode'),
                vjs_report=p_data.get('last_vjs_report'),
                key_manager=groq_km,
                problem_class=problem_class,
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

