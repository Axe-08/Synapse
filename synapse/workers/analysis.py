# synapse/workers/analysis.py
"""
Stage 3: Analysis Worker (batched)

Processes a batch of problems using quality filtering, pre-processing,
and intelligent handling of partial batch success.
"""
from ._shared import (
    logging, json, Dict, Any, List,
    db, KeyManager,
    MAX_ANALYSIS_RETRIES, MAX_RESCRAPING_ATTEMPTS,
)
from ._shared import _score_code_quality
from synapse.api_clients import (
    call_gemini_analyst_batch,
    _preprocess_code_for_llm,
    AnalysisFailedException,
)


def analysis_worker(batch: List[Dict[str, Any]], worker_id: str, gemini_km: KeyManager):
    """
    Processes a batch of problems using quality filtering, pre-processing,
    and intelligent handling of partial batch success.
    """
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting analysis for batch of {len(batch_ids)}: {batch_ids}")
    problem_ids_in_api_call = []

    try:
        # Pre-flight: check retries and quarantine limits
        problems_to_process = []
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            placeholders = ','.join('?' for _ in batch_ids)
            cursor = conn.execute(
                f"SELECT id, analysis_try_count, rescraping_attempts "
                f"FROM problems WHERE id IN ({placeholders})",
                batch_ids,
            )
            problem_states = {
                row[0]: {'analysis_tries': row[1], 'rescrapes': row[2]}
                for row in cursor.fetchall()
            }

        workspace_data = db.get_batch_data_from_workspace(batch_ids)

        for problem in batch:
            p_id = problem['id']
            state = problem_states.get(p_id)
            if not state:
                continue

            if state['analysis_tries'] >= MAX_ANALYSIS_RETRIES:
                if state['rescrapes'] >= MAX_RESCRAPING_ATTEMPTS:
                    reason = (
                        f"Exceeded max analysis retries ({MAX_ANALYSIS_RETRIES}) "
                        f"and re-scraping attempts ({MAX_RESCRAPING_ATTEMPTS})."
                    )
                    db.transition_to_quarantined(p_id, reason)
                else:
                    ref_sol_json = workspace_data.get(p_id, {}).get('reference_solution_json', '{}')
                    failed_sub_id = json.loads(ref_sol_json).get('id', 'unknown')
                    db.transition_to_pending_rescraping(p_id, str(failed_sub_id))
            elif p_id in workspace_data:
                problems_to_process.append(problem)

        if not problems_to_process:
            logging.info("Batch is empty after pre-flight checks.")
            return

        final_api_batch = []
        problem_ids_in_api_call = [p['id'] for p in problems_to_process]

        for p_info in problems_to_process:
            p_id = p_info['id']
            p_data = workspace_data.get(p_id)
            if not p_data:
                continue

            primary_code = p_data.get('reference_solution_code')
            secondary_codes = json.loads(p_data.get('secondary_reference_codes_json', '[]'))
            all_codes = [c for c in [primary_code] + secondary_codes if c]

            if not all_codes:
                logging.warning(f"No reference codes found for {p_id}, skipping.")
                continue

            scored_solutions = [(_score_code_quality(code), code) for code in all_codes]
            scored_solutions.sort(key=lambda x: x[0])
            top_solutions = [code for _score, code in scored_solutions[:3]]
            processed_codes = [_preprocess_code_for_llm(code) for code in top_solutions]

            final_api_batch.append({
                "problem_id": p_id,
                "html_statement": p_data.get('problem_statement_html'),
                "reference_solutions": processed_codes,
                "vjs_report": p_data.get('vjs_last_report'),
            })

        if not final_api_batch:
            logging.warning("API batch is empty after quality filtering.")
            return

        # Determine if simplification is needed for any problem in the batch
        # Use simplify=True for the whole batch if ANY problem is on retry >= 1
        # (Batch is usually size 1 for retries, so this is safe)
        any_retry = any(
            problem_states.get(p['id'], {}).get('analysis_tries', 0) >= 1
            for p in problems_to_process
        )

        parsed_json_output, _raw = call_gemini_analyst_batch(
            final_api_batch, gemini_km, simplify=any_retry
        )
        pseudocode_results = parsed_json_output.get("final_pseudocode", {})

        successful_ids = []
        failed_ids = []
        for problem_id, pseudocode in pseudocode_results.items():
            if pseudocode is not None:
                successful_ids.append(problem_id)
            else:
                failed_ids.append(problem_id)

        if successful_ids:
            logging.info(f"SUCCESS [Analysis] for problems: {successful_ids}. -> pending_fuzz_generation")
            for problem_id in successful_ids:
                pseudocode = pseudocode_results[problem_id]
                analysis_details_json = json.dumps(parsed_json_output.get("analysis", {}))
                db.update_workspace_with_analysis_results(problem_id, pseudocode, analysis_details_json)
                # If analysis_tries >= 2, the problem has now received simplified pseudocode
                # AND still needs implementation — mark it so implementation.py know to use Gemini
                a_tries = problem_states.get(problem_id, {}).get('analysis_tries', 0)
                if a_tries >= 2:
                    logging.info(f"[{problem_id}] analysis_tries={a_tries} >= 2: will escalate to Gemini implementation.")
                    db.transition_batch_to_pending_fuzz_generation([problem_id])
                else:
                    db.transition_batch_to_pending_fuzz_generation([problem_id])

        if failed_ids:
            logging.warning(f"PARTIAL FAILURE [Analysis] for problems: {failed_ids}.")
            reasoning_data = parsed_json_output.get("reasoning", {})
            for problem_id in failed_ids:
                reason = reasoning_data.get(problem_id, "Model returned null without reasoning.")
                db.transition_to_quarantined(problem_id, f"LLM Null Failure: {reason[:1500]}")

    except Exception as e:
        logging.error(f"CRITICAL FAILURE [Analysis] for batch {batch_ids}: {e}", exc_info=True)
        for problem_id in batch_ids:
            db.transition_to_failed(problem_id, 'analysis', str(e))
    finally:
        db.update_worker_status(worker_id, 'ANALYSIS', None, None, 'idle')
