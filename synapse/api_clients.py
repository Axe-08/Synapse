# synapse/api_clients.py
"""
This module is responsible for all interactions with external LLM APIs.

It contains dedicated functions for calling the "Analyst" model (Gemini)
and the "Implementer" model (Groq). These functions incorporate robust
error handling, interaction with the KeyManager to prevent rate-limiting,
and performance logging to the metrics database. The prompts are centrally
managed here for easy tuning.
"""
import logging
import time
import json
from typing import List, Dict, Any

import google.generativeai as genai
from groq import Groq, RateLimitError

import synapse.database as db
from synapse.key_manager import KeyManager, KeyStatus
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Model Configuration ---
GEMINI_MODEL_NAME: str = 'gemini-2.5-pro' # Updated to latest stable model
GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"

# --- Prompt Engineering ---
GEMINI_ANALYST_BATCH_PROMPT: str = """
You are an expert algorithm designer. Your task is to analyze a batch of C++ solutions for competitive programming problems and produce high-quality, language-agnostic pseudocode for each.

**RULES:**
1.  You will be given a list of JSON objects. Each object contains a `problem_id`, the problem's `html_statement`, and the `reference_code`.
2.  For each problem, you must analyze the context and the code to understand the core algorithm.
3.  Your output **MUST** be a single JSON object (a dictionary) where the keys are the `problem_id`s from the input, and the values are the corresponding pseudocode strings.
4.  The pseudocode must be clear, step-by-step, and language-agnostic. Do NOT use C++ specific syntax. Focus on logic, data structures, and key operations.
5.  If a problem has feedback from a previous failed attempt (`vjs_report`), it will contain a detailed analysis of the failure. You MUST use this information to create a new, corrected algorithm. The feedback is your most important clue.
6.  Ensure your final output is a valid JSON that can be parsed directly. Do not include any text or explanations outside of the final JSON object.

**INPUT BATCH:**
{batch_input_json}


**OUTPUT JSON:**
"""

GROQ_IMPLEMENTER_PROMPT: str = """
You are a world-class competitive programmer. Your task is to implement a solution in C++ based *only* on the provided problem context and pseudocode.

**CRITICAL RULES:**
1.  Your entire output must be **ONLY the raw C++ code**.
2.  **DO NOT** include any introductory text, explanations, or conversational filler like "Here is the code".
3.  **DO NOT** wrap the code in Markdown code blocks like ```cpp.
4.  The code must be a complete, runnable program, including necessary headers and fast I/O.
5.  Follow the logic from the pseudocode precisely.

**PROBLEM CONTEXT (HTML):**
{problem_html}

**PSEUDOCODE:**
{pseudocode}

**PREVIOUS FAILED ATTEMPT (VJS REPORT):**
This section contains feedback from the automated judge on your last attempt. Ignore this if the report is empty. If it's a compile error, fix the syntax. If it's a logic error, use the test case analysis to correct your implementation.
{vjs_report}

**C++ SOLUTION:**
"""
def _sanitize_cpp_code(raw_output: str) -> str:
    """
    Strips Markdown code blocks and any surrounding text from the LLM output.
    This provides a robust defense against the model's tendency to add formatting.
    """
    # Remove the starting ```cpp or ```
    if raw_output.startswith("```cpp\n"):
        raw_output = raw_output[6:]
    elif raw_output.startswith("```\n"):
        raw_output = raw_output[4:]
    
    # Remove the ending ```
    if raw_output.endswith("\n```"):
        raw_output = raw_output[:-4]

    return raw_output.strip()

def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Dict[str, str]:
    """
    Calls the Gemini API with a batch of problems to generate pseudocode.

    Args:
        batch_data: A list of dictionaries, each containing problem data.
        key_manager: The KeyManager instance for Gemini API keys.

    Returns:
        A dictionary mapping problem_id to the generated pseudocode string.

    Raises:
        Exception: If no API keys are available or the API call fails critically.
    """
    estimated_tokens = len(str(batch_data))
    managed_key = None
    response_text = ""
    start_time = time.perf_counter()

    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Gemini API keys in the pool.")

        genai.configure(api_key=managed_key.key_string)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        prompt = GEMINI_ANALYST_BATCH_PROMPT.format(batch_input_json=json.dumps(batch_data, indent=2))
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        logging.info(f"Calling Gemini Analyst with a batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
        response = model.generate_content(prompt, safety_settings=safety_settings)

        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Unknown"
            raise Exception(f"Gemini API call was blocked. Reason: {block_reason}")

        response_text = response.text
        # Clean the response to extract only the JSON object
        cleaned_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        json_start_index = cleaned_text.find('{')
        json_end_index = cleaned_text.rfind('}')
        if json_start_index == -1 or json_end_index == -1:
            raise ValueError("Could not find a valid JSON object in the model's response.")
        json_string = cleaned_text[json_start_index : json_end_index + 1]

        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0) # Token count not available for batch
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('ANALYSIS', 'api_call', duration_ms, True, {'service': 'gemini', 'batch_size': len(batch_data)})

        return json.loads(json_string)

    except Exception as e:
        outcome = KeyStatus.RATE_LIMITED # Assume rate limiting on any error for safety
        if managed_key:
            key_manager.release_key(managed_key, outcome, tokens_used=0)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('ANALYSIS', 'api_call', duration_ms, False, {'service': 'gemini', 'error': str(e), 'batch_size': len(batch_data)})

        logging.error(f"Gemini API batch call failed: {e}")
        if "json" in str(e).lower():
            logging.error(f"--- RAW RESPONSE START ---\n{response_text}\n--- RAW RESPONSE END ---")
        raise

def call_groq_implementer(problem_html: str, pseudocode: str, vjs_report: str, key_manager: KeyManager) -> str:
    """
    Calls the Groq API to generate C++ code from pseudocode.

    Args:
        problem_html: The HTML statement of the problem.
        pseudocode: The language-agnostic pseudocode for the solution.
        vjs_report: Feedback from any previous failed verification attempt.
        key_manager: The KeyManager instance for Groq API keys.

    Returns:
        The raw C++ code as a string.

    Raises:
        Exception: If no API keys are available or the API call fails critically.
    """
    estimated_tokens = (len(problem_html) + len(pseudocode)) // 4
    managed_key = None
    start_time = time.perf_counter()

    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Groq API keys in the pool.")

        client = Groq(api_key=managed_key.key_string)
        prompt = GROQ_IMPLEMENTER_PROMPT.format(
            problem_html=problem_html,
            pseudocode=pseudocode,
            vjs_report=vjs_report or "None"
        )

        logging.info(f"Calling Groq Implementer (key: ...{managed_key.key_string[-4:]})")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL_NAME,
        )

        tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0
        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=tokens_used)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('IMPLEMENTATION', 'api_call', duration_ms, True, {'service': 'groq', 'tokens_used': tokens_used})

        raw_code = chat_completion.choices[0].message.content
        return _sanitize_cpp_code(raw_code)

    except RateLimitError as e:
        if managed_key:
            key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)
        logging.error(f"Groq API call failed due to rate limit: {e}")
        raise
    except Exception as e:
        if managed_key:
            key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0) # Treat other errors as potential rate limits

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('IMPLEMENTATION', 'api_call', duration_ms, False, {'service': 'groq', 'error': str(e)})

        logging.error(f"Groq API call failed: {e}")
        raise