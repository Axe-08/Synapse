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
from typing import List, Dict, Any, Tuple
import re # Make sure 're' is imported
import google.generativeai as genai
from groq import Groq, RateLimitError

import synapse.database as db
from synapse.key_manager import KeyManager, KeyStatus
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- Model Configuration ---
GEMINI_MODEL_NAME: str = 'gemini-2.5-flash' # Updated to latest stable model
GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"

# --- Prompt Engineering ---
# In synapse/api_clients.py
GEMINI_ANALYST_BATCH_PROMPT: str = """
<ROLE>
You are an expert algorithm designer and code reviewer. Your goal is to analyze multiple C++ solutions (oracles) for a problem, produce a canonical pseudocode from the best one, and provide a rating for each oracle.
</ROLE>

<INSTRUCTIONS>
For the problem in the input batch:
1.  **Analyze & Rate Each Oracle**: Examine the core logic of all provided C++ solutions. For each one, provide a rating ('Excellent', 'Good', 'Fair', 'Poor') and a brief justification based on algorithmic efficiency, correctness, and code clarity.
2.  **Select the Best**: Choose the oracle with the highest rating as the basis for your canonical pseudocode.
3.  **Formulate Pseudocode**: Write a clear, language-agnostic pseudocode that captures the selected best algorithm.
4.  **Handle Failures**: If no oracle is of 'Fair' quality or better, you may return `null` for the pseudocode.
</INSTRUCTIONS>

<OUTPUT_FORMAT>
Your entire response must be a single markdown code block containing a single JSON object. The JSON must have two keys: "analysis" and "final_pseudocode".
**CRITICAL**: All backslashes `\\` must be properly escaped as `\\\\`.

```json
{{
  "analysis": {{
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {{
      "oracle_0": {{"rating": "Excellent", "justification": "Clear, efficient O(N) approach using a two-pass strategy."}},
      "oracle_1": {{"rating": "Fair", "justification": "Correct, but uses a less efficient O(N log N) data structure where not needed."}},
      "oracle_2": {{"rating": "Poor", "justification": "Overly complex and hard to read. Fails on certain edge cases."}}
    }}
  }},
  "final_pseudocode": {{
    "problem_id_1": "1. Pseudocode based on the best oracle..."
  }}
}}
```
</OUTPUT_FORMAT>

<INPUT_BATCH>
{batch_input_json}
</INPUT_BATCH>
"""
# In synapse/api_clients.py

# In synapse/api_clients.py

GROQ_IMPLEMENTER_PROMPT: str = """
You are a world-class competitive programmer. Your task is to implement a solution in C++ based *only* on the provided problem context and pseudocode.

**CRITICAL RULES:**
1.  **All helper functions must be defined globally. Do not define functions inside other functions.**
2.  Your entire output must be **ONLY the raw C++ code**.
3.  **DO NOT** include any introductory text, explanations, or conversational filler.
4.  **DO NOT** wrap the code in Markdown code blocks like ```cpp.
5.  The code must be a complete, runnable program that handles multiple test cases as specified in the problem statement.
6.  Follow the logic from the pseudocode precisely.

**PROBLEM CONTEXT (HTML):**
{problem_html}

**PSEUDOCODE:**
{pseudocode}

**PREVIOUS FAILED ATTEMPT (VJS REPORT):**
This section contains feedback from the automated judge on your last attempt. Ignore this if the report is empty. If it's a compile error, fix the syntax. If it's a logic error, use the test case analysis to correct your implementation.
{vjs_report}

**C++ SOLUTION:**
"""
class AnalysisFailedException(Exception):
    """Custom exception for when the LLM provides a failure analysis."""
    pass

def _preprocess_code_for_llm(code: str) -> str:
    """
    Strips common boilerplate and comments from C++ code to focus 
    the LLM on the core algorithm.
    """
    # 1. Remove multi-line comments (/* ... */)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # 2. Remove single-line comments (// ...)
    code = re.sub(r'//.*', '', code)
    # 3. Remove includes, using namespace, and common fast I/O setup
    lines = code.split('\n')
    processed_lines = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('#include', 'using namespace', 'ios_base::sync_with_stdio', 'cin.tie')):
            continue
        # Remove empty lines that might result from comment removal
        if stripped_line:
            processed_lines.append(line)
    return '\n'.join(processed_lines)
# In synapse/api_clients.py

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
# def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Tuple[Dict[str, str], str]:
#     """
#     Calls the Gemini API.
#     (MODIFIED to use robust regex parsing for the final JSON output).
#     """
#     estimated_tokens = len(str(batch_data))
#     managed_key = None
#     response_text = ""
#     start_time = time.perf_counter()

#     try:
#         managed_key = key_manager.get_key(estimated_tokens)
#         if not managed_key:
#             raise Exception("No available Gemini API keys in the pool.")

#         genai.configure(api_key=managed_key.key_string)
#         model = genai.GenerativeModel(GEMINI_MODEL_NAME)
#         prompt = GEMINI_ANALYST_BATCH_PROMPT.format(batch_input_json=json.dumps(batch_data, indent=2))
#         safety_settings = {
#             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
#             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
#         }

#         logging.info(f"Calling Gemini Analyst with a batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
#         response = model.generate_content(prompt, safety_settings=safety_settings)

#         if not response.parts:
#             logging.error(f"Gemini API Blocked Response. Feedback: {response.prompt_feedback}")
#             block_reason = "Unknown"
#             if response.prompt_feedback:
#                 block_reason = response.prompt_feedback.block_reason.name
#             raise Exception(f"Gemini API call was blocked. Reason: {block_reason}")

#         response_text = response.text

#         # --- ROBUST PARSING LOGIC START ---
#         # Use regex to find the JSON content within the markdown block
#         match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
#         if not match:
#             raise ValueError("Could not find a valid JSON markdown block in the model's response.")
        
#         json_string = match.group(1)
#         parsed_json = json.loads(json_string)
#         # --- ROBUST PARSING LOGIC END ---

#         key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0)
#         db.log_metric('ANALYSIS', 'api_call', int((time.perf_counter() - start_time) * 1000), True, {'service': 'gemini', 'batch_size': len(batch_data)})
        
#         # The worker now expects the full parsed JSON object
#         return (parsed_json, response_text)

#     except Exception as e:
#         outcome = KeyStatus.RATE_LIMITED
#         error_str = str(e).lower()
#         if managed_key and ("api key not valid" in error_str or "permission_denied" in error_str):
#             logging.warning(f"DETECTED INVALID API KEY: ...{managed_key.key_string[-4:]}")
#             outcome = KeyStatus.INVALID
#         if managed_key:
#             key_manager.release_key(managed_key, outcome, tokens_used=0)
        
#         db.log_metric('ANALYSIS', 'api_call', int((time.perf_counter() - start_time) * 1000), False, {'service': 'gemini', 'error': str(e)})
#         logging.error(f"Gemini API batch call failed: {e}")
#         if response_text:
#             logging.error(f"--- RAW RESPONSE START ---\n{response_text}\n--- RAW RESPONSE END ---")
#         raise

# In synapse/api_clients.py

def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Tuple[Dict[str, str], str]:
    """
    Calls the Gemini API.
    (MODIFIED for full verbose debugging).
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

        # --- START: FULL VERBOSE DEBUGGING ---
        print("\n" + "="*80)
        print("--- GEMINI API CALL: VERBOSE DEBUG ---")
        print("="*80)
        
        # 1. Estimate tokens
        estimated_prompt_tokens = len(prompt) // 4 
        print(f"\n[DEBUG] ESTIMATED PROMPT TOKENS: ~{estimated_prompt_tokens}\n")
        
        # 2. Print the full prompt
        print("[DEBUG] FULL PROMPT BEING SENT TO API:")
        print("-" * 50)
        print(prompt)
        print("-" * 50 + "\n")
        # --- END: FULL VERBOSE DEBUGGING ---

        logging.info(f"Calling Gemini Analyst with a batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
        response = model.generate_content(prompt, safety_settings=safety_settings)

        # --- START: FULL VERBOSE DEBUGGING ---
        # 3. Print the raw response object
        print("\n[DEBUG] RAW RESPONSE RECEIVED FROM API:")
        print("-" * 50)
        print(response)
        print("-" * 50 + "\n")

        # 4. Print usage metadata specifically
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            print(f"[DEBUG] USAGE METADATA FROM API: {response.usage_metadata}\n")
        
        print("="*80)
        print("--- END OF VERBOSE DEBUG ---")
        print("="*80 + "\n")
        # --- END: FULL VERBOSE DEBUGGING ---

        if not response.parts:
            logging.error(f"Gemini API Blocked Response. Feedback: {response.prompt_feedback}")
            block_reason = "Unknown"
            if response.prompt_feedback:
                block_reason = response.prompt_feedback.block_reason.name
            raise Exception(f"Gemini API call was blocked. Reason: {block_reason}")

        response_text = response.text

        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not match:
            raise ValueError("Could not find a valid JSON markdown block in the model's response.")
        
        json_string = match.group(1)
        parsed_json = json.loads(json_string)

        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0)
        db.log_metric('ANALYSIS', 'api_call', int((time.perf_counter() - start_time) * 1000), True, {'service': 'gemini', 'batch_size': len(batch_data)})
        
        return (parsed_json, response_text)

    except Exception as e:
        outcome = KeyStatus.RATE_LIMITED
        error_str = str(e).lower()
        if managed_key and ("api key not valid" in error_str or "permission_denied" in error_str):
            logging.warning(f"DETECTED INVALID API KEY: ...{managed_key.key_string[-4:]}")
            outcome = KeyStatus.INVALID
        if managed_key:
            key_manager.release_key(managed_key, outcome, tokens_used=0)
        
        db.log_metric('ANALYSIS', 'api_call', int((time.perf_counter() - start_time) * 1000), False, {'service': 'gemini', 'error': str(e)})
        logging.error(f"Gemini API batch call failed: {e}")
        if response_text:
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