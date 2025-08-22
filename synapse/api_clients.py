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
GEMINI_MODEL_NAME: str = 'gemini-2.5-pro' # Updated to latest stable model
GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"

# --- Prompt Engineering ---
# In synapse/api_clients.py
GEMINI_ANALYST_BATCH_PROMPT: str = """
You are an expert algorithm designer. Your primary goal is to analyze multiple C++ solutions for each problem in a batch and synthesize a single, canonical pseudocode.

**INPUT:**
You will receive a list of JSON objects. Each object represents a single problem and contains:
1.  `problem_id`: A unique identifier.
2.  `html_statement`: The full problem description.
3.  `reference_solutions`: A list of verified, correct C++ solutions. These may vary in style and include boilerplate or macros.

**OUTPUT RULES:**
YOU MUST follow this output structure precisely. Use the exact markdown headings.

1.  **`## REASONING` Section:**
    - Create a sub-heading for each problem (e.g., `### Problem 123A`).
    - Under each sub-heading, explain your chain of thought: Analyze the solutions (ignoring boilerplate), compare the approaches, select the best one, and formulate your pseudocode plan.

2.  **`## FINAL JSON` Section:**
    - This section must contain ONLY a single JSON object inside a markdown code block.
    - This JSON object must contain entries for all problems you successfully processed.

3.  **Handling Failures:**
    - If you cannot process a problem, explain why in its `### Problem ID` subsection within the `## REASONING` section.
    - Omit any failed problems from the final JSON object.

---
**EXAMPLE OUTPUT:**

## REASONING

### Problem 123A
Analysis: The solutions use a simple two-pointer approach.
Comparison: All solutions are fundamentally the same.
Selection: The two-pointer method is optimal.
Formulation: I will write pseudocode that initializes two pointers, left and right, and moves them inwards based on a condition.

### Problem 456B
Analysis: I was unable to process this problem because the provided solutions were too contradictory and a single canonical algorithm could not be determined. I will omit it from the final JSON.

## FINAL JSON
```json
{{
  "123A": "1. Initialize left_ptr = 0, right_ptr = n-1\\n2. While left_ptr < right_ptr:\\n   ..."
}}
```
---
INPUT BATCH:
{batch_input_json}
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

def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Tuple[Dict[str, str], str]:
    """
    Calls the Gemini API and intelligently parses the response, looking for
    the '## FINAL JSON' heading.
    Returns a tuple of (parsed_json, raw_response_text).
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
        response_text = response.text

        if not response.parts and not response_text:
            logging.error(f"Gemini API Blocked Response Details: {response.prompt_feedback}")
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback else "Unknown"
            raise Exception(f"Gemini API call was blocked. Reason: {block_reason}")

        # --- FINAL PARSING LOGIC FOR MARKDOWN HEADERS ---
        
        # 1. Find the '## FINAL JSON' heading.
        start_heading_pos = response_text.find('## FINAL JSON')
        if start_heading_pos == -1:
            raise ValueError("Model response did not contain the required '## FINAL JSON' heading.")

        # 2. Define the search area as everything after the heading.
        json_search_area = response_text[start_heading_pos:]
        
        # 3. Find the first opening brace and the last closing brace in that area.
        json_start_index = json_search_area.find('{')
        json_end_index = json_search_area.rfind('}')

        if json_start_index == -1 or json_end_index == -1:
            raise ValueError("Could not find a valid JSON object after '## FINAL JSON' heading.")
        
        # 4. Slice precisely to get the JSON string.
        json_string = json_search_area[json_start_index : json_end_index + 1]
        
        parsed_json = json.loads(json_string)
        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0)
        db.log_metric('ANALYSIS', 'api_call', int((time.perf_counter() - start_time) * 1000), True, {'service': 'gemini', 'batch_size': len(batch_data)})
        
        # The worker will handle partial success by comparing keys; this function just returns what it found.
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