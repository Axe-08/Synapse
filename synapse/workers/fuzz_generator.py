# synapse/workers/fuzz_generator.py
"""
Stage 4: Fuzz Generator Worker (batched)

Takes problems out of post-analysis queue, finds the highest-rated oracle
from the Analysis JSON, and feeds both HTML and Oracle code into Gemini
to generate a Python random edge-case tester (Fuzzer script).
"""
import logging
import json
from typing import Dict, Any, List

from ._shared import db, KeyManager
from synapse.api_clients import call_gemini_fuzz_generator_batch

def fuzz_generator_worker(batch: List[Dict[str, Any]], worker_id: str, gemini_km: KeyManager):
    """
    Processes a batch of problems to generate their python fuzzers.
    """
    batch_ids = [p['id'] for p in batch]
    logging.info(f"Starting fuzz generation for batch of {len(batch_ids)}: {batch_ids}")
    
    try:
        workspace_data = db.get_batch_data_from_workspace(batch_ids)
        final_api_batch = []
        problems_to_process = []

        for p_info in batch:
            p_id = p_info['id']
            p_data = workspace_data.get(p_id)
            if not p_data:
                continue

            # Need HTML context
            html_statement = p_data.get('problem_statement_html', '')

            # Need the best oracle C++ snippet
            analysis_json_raw = p_data.get('quality_analysis_json', '{}')
            try:
                analysis_doc = json.loads(analysis_json_raw)
            except:
                analysis_doc = {}

            best_oracle_id = analysis_doc.get('analysis', {}).get('best_oracle_id', 'oracle_0')
            
            primary_code = p_data.get('reference_solution_code')
            secondary_codes = json.loads(p_data.get('secondary_reference_codes_json', '[]'))
            all_codes = [c for c in [primary_code] + secondary_codes if c]

            oracle_index = 0
            if 'oracle_' in best_oracle_id:
                try: oracle_index = int(best_oracle_id.replace('oracle_', ''))
                except ValueError: pass
                
            best_oracle_code = all_codes[oracle_index] if oracle_index < len(all_codes) else (all_codes[0] if all_codes else "")
            
            if not html_statement or not best_oracle_code:
                logging.warning(f"Missing HTML or Oracle context for {p_id}. Skipping fuzz.")
                db.transition_batch_to_pending_implementation([p_id]) # bypass
                continue

            problems_to_process.append(p_id)
            final_api_batch.append({
                "problem_id": p_id,
                "problem_html": html_statement,
                "best_oracle_code": best_oracle_code
            })

        if not final_api_batch:
            logging.info("Batch is empty after pre-flight checks in fuzz generator.")
            return

        parsed_json_output, _raw = call_gemini_fuzz_generator_batch(final_api_batch, gemini_km)
        generator_results = parsed_json_output.get("generators", {})

        successful_ids = []
        failed_ids = []

        for problem_id in problems_to_process:
            py_fuzzer = generator_results.get(problem_id)
            if py_fuzzer:
                py_fuzzer = py_fuzzer.replace('\\n', '\n').replace('\\"', '"')
                successful_ids.append(problem_id)
                db.update_workspace_with_fuzzer(problem_id, py_fuzzer)
            else:
                failed_ids.append(problem_id)

        if successful_ids:
            logging.info(f"SUCCESS [Fuzz Generation] for problems: {successful_ids}. -> pending_implementation")
            db.transition_batch_to_pending_implementation(successful_ids)

        if failed_ids:
            logging.warning(f"PARTIAL FAILURE [Fuzz Generation] for problems: {failed_ids}.")
            for problem_id in failed_ids:
                db.transition_to_quarantined(problem_id, "Fuzzer LLM failed to output python generator correctly")

    except Exception as e:
        logging.error(f"CRITICAL FAILURE [Fuzz Generation] for batch {batch_ids}: {e}", exc_info=True)
        for problem_id in batch_ids:
            db.transition_to_failed(problem_id, 'fuzz_generation', str(e))
    finally:
        db.update_worker_status(worker_id, 'FUZZ_GENERATOR', None, None, 'idle')
