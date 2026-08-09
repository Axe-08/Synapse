# synapse/api_clients.py
"""
This module is responsible for all interactions with external LLM APIs.

It contains dedicated functions for calling the "Analyst" model (Gemini)
and the "Implementer" model (Groq). These functions incorporate robust
error handling, interaction with the KeyManager to prevent rate-limiting,
budget tracking via log_usage(), and performance logging to the metrics database.

V2 Changes:
-   Upgraded Groq model to qwen-qwq-32b (competitive programming specialist)
-   Added fuzz generator prompt + call_gemini_fuzz_generator()
-   Prompts are problem_class-aware (interactive/special_judge/constructive)
-   KeyManager.log_usage() called after every successful API interaction
-   Removed debug print statements from production code
"""
import logging
import time
import json
from typing import List, Dict, Any, Tuple, Optional
import re
from google import genai
from google.genai import types
from groq import Groq, RateLimitError

import synapse.database as db
from synapse.key_manager import KeyManager, KeyStatus, ManagedKey

# ── Model Configuration ─────────────────────────────────────────────────────
# Gemini 2.5 Flash: best free-tier analysis model (5 RPM, 250K TPM, ~50 RPD)
GEMINI_MODEL_NAME: str = 'gemini-2.5-flash'
# Llama 3.3 70B is safer for code generation without reasoning tokens leaking into the output
GROQ_MODEL_NAME: str = 'llama-3.3-70b-versatile'
# Fallback if primary Groq model is unavailable
GROQ_FALLBACK_MODEL: str = 'openai/gpt-oss-120b'


# ── Prompt Engineering ───────────────────────────────────────────────────────

GEMINI_ANALYST_BATCH_PROMPT: str = """\
<ROLE>
You are an expert algorithm designer and competitive programming coach. Your goal is to:
1. Analyze multiple C++ reference solutions (oracles) for a problem
2. Rate each oracle's quality
3. Produce a canonical, language-agnostic pseudocode from the best oracle
</ROLE>

<INSTRUCTIONS>
For each problem in the input batch:

1. **Analyze & Rate Each Oracle**: Examine the core algorithm. Rate each oracle:
   - 'Excellent': Optimal time/space, clean, handles all edge cases
   - 'Good': Correct and efficient, minor style issues
   - 'Fair': Correct but suboptimal approach or poor readability
   - 'Poor': Incorrect, TLE-prone, or unreadable

2. **Select the Best**: Choose the highest-rated oracle as the canonical basis.

3. **Write Pseudocode**: Clear, language-agnostic pseudocode that captures:
   - The core algorithm (not boilerplate)
   - All edge cases the best oracle handles
   - Input/output format expectations
   - Time/space complexity in a comment

4. **Handle Failures**: If no oracle is 'Fair' or better, return `null` for pseudocode.
</INSTRUCTIONS>

<OUTPUT_FORMAT>
Your entire response must be a single JSON block. Keys: "analysis" and "final_pseudocode".
**CRITICAL**: Escape all backslashes properly.

```json
{{
  "analysis": {{
    "best_oracle_id": "oracle_0",
    "oracle_ratings": {{
      "oracle_0": {{"rating": "Excellent", "justification": "Optimal O(N) two-pointer approach. Clean and edge-case safe."}},
      "oracle_1": {{"rating": "Fair", "justification": "Correct but O(N log N) where O(N) suffices."}}
    }}
  }},
  "final_pseudocode": {{
    "problem_id_1": "// O(N) time, O(1) space\\n1. Read n\\n2. For each test case...\\n"
  }}
}}
```
</OUTPUT_FORMAT>

<INPUT_BATCH>
{batch_input_json}
</INPUT_BATCH>
"""

# Appended to the analyst prompt when simplification is requested (retry >= 1)
GEMINI_ANALYST_SIMPLIFY_ADDON: str = """
<SIMPLIFICATION_REQUIRED>
IMPORTANT: A previous attempt to implement this pseudocode FAILED. The implementer model could not correctly translate the pseudocode into working code.
Your task now is to rewrite the pseudocode to be simpler and more explicit:
- Avoid high-level mathematical abstractions and notation
- Use concrete loops with explicit index variables instead of set-builder notation
- Spell out every step as if writing for a junior developer, not a math expert
- Prefer verbosity over conciseness — clarity is more important than elegance
- Make all data structures and their operations fully explicit
</SIMPLIFICATION_REQUIRED>
"""

GROQ_IMPLEMENTER_PROMPT: str = """\
You are a world-class competitive programmer. Implement a C++ solution based *only* on the provided context.

**CRITICAL RULES:**
1. Output **ONLY raw C++ code**. No markdown, no explanations, no ```cpp blocks.
2. All helper functions must be defined globally (not inside main or other functions).
3. Must be a complete, compilable program with proper I/O handling.
4. Follow the pseudocode logic precisely.
5. Use fast I/O: `ios_base::sync_with_stdio(false); cin.tie(NULL);`
6. Use `#include <bits/stdc++.h>` for simplicity.
7. Handle multiple test cases if the problem specifies them.

{class_instructions}

**PROBLEM CONTEXT (HTML):**
{problem_html}

**PSEUDOCODE:**
{pseudocode}

**PREVIOUS ATTEMPT FEEDBACK:**
{vjs_report}

**C++ SOLUTION:**
"""

# Class-specific instructions injected into the implementer prompt
_CLASS_INSTRUCTIONS = {
    'standard': '',
    'interactive': (
        '**INTERACTIVE PROBLEM**: This problem requires live interaction with the judge.\n'
        '- Use `cout << ... << endl;` or `cout.flush()` after EVERY output line.\n'
        '- Read judge responses with `cin >>` after each query.\n'
        '- Do NOT use `\\n` without flushing — always use `endl` or explicit flush.\n'
    ),
    'special_judge': (
        '**SPECIAL JUDGE**: Multiple valid outputs exist.\n'
        '- Focus on producing ANY valid output that satisfies constraints.\n'
        '- The checker will verify validity, not exact match.\n'
    ),
    'constructive': (
        '**CONSTRUCTIVE PROBLEM**: You must construct a valid answer.\n'
        '- Any valid construction is accepted.\n'
        '- Prioritize simplicity and correctness over optimality.\n'
    ),
}


GEMINI_FUZZ_GENERATOR_BATCH_PROMPT: str = """\
<ROLE>
You are an expert test case generator for competitive programming problems.
Your task is to write a Python script that generates random valid test inputs based on constraints.
</ROLE>

<INSTRUCTIONS>
For each problem in the input batch, write a Python script that:
1. Generates a SINGLE random test input that respects ALL constraints
2. Prints the test input to stdout (exactly as the judge expects)
3. Uses `import random` for randomness
4. Includes edge cases with some probability (empty, min, max values)
5. Must complete in under 5 seconds

You will be provided both the HTML problem statement constraints AND the compiled C++ Oracle Code that correctly solves it. Use the C++ code to perfectly understand what variables and loops the judge expects in the input.

**CRITICAL**: Your entire response must be a single JSON block containing the raw generator script for each problem. Do NOT use markdown code blocks inside the JSON strings. Escape all quotes and newlines properly.

```json
{{
  "generators": {{
    "problem_id_1": "import random\\nn = random.randint(1, 100)\\nprint(n)\\n"
  }}
}}
```
</INSTRUCTIONS>

<INPUT_BATCH>
{batch_input_json}
</INPUT_BATCH>
"""


# ── Helper Functions ─────────────────────────────────────────────────────────

class AnalysisFailedException(Exception):
    """Custom exception for when the LLM provides a failure analysis."""
    pass


def _preprocess_code_for_llm(code: str) -> str:
    """
    Strips common boilerplate and comments from C++ code to focus
    the LLM on the core algorithm.
    """
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//.*', '', code)
    lines = code.split('\n')
    processed_lines = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith(('#include', 'using namespace', 'ios_base::sync_with_stdio', 'cin.tie')):
            continue
        if stripped_line:
            processed_lines.append(line)
    return '\n'.join(processed_lines)


def _sanitize_cpp_code(raw_output: str) -> str:
    """
    Strips Markdown code blocks and any surrounding text from the LLM output.
    """
    if raw_output.startswith("```cpp\n"):
        raw_output = raw_output[6:]
    elif raw_output.startswith("```\n"):
        raw_output = raw_output[4:]

    if raw_output.endswith("\n```"):
        raw_output = raw_output[:-4]

    return raw_output.strip()


def _sanitize_python_code(raw_output: str) -> str:
    """
    Strips Markdown code blocks from Python generator output.
    """
    if raw_output.startswith("```python\n"):
        raw_output = raw_output[10:]
    elif raw_output.startswith("```py\n"):
        raw_output = raw_output[6:]
    elif raw_output.startswith("```\n"):
        raw_output = raw_output[4:]

    if raw_output.endswith("\n```"):
        raw_output = raw_output[:-4]

    return raw_output.strip()


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


# ── API Call Functions ───────────────────────────────────────────────────────

_SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]


# Max number of different keys to attempt before giving up on a Gemini call
_MAX_GEMINI_KEY_RETRIES: int = 10


def call_gemini_analyst_batch(
    batch_data: List[Dict[str, Any]],
    key_manager: KeyManager,
    simplify: bool = False,
) -> Tuple[Dict[str, Any], str]:
    """
    Calls the Gemini API to analyze a batch of problems.

    Returns:
        Tuple of (parsed_json, raw_response_text).
    """
    estimated_tokens = _estimate_tokens(str(batch_data))
    last_error = None

    for _attempt in range(_MAX_GEMINI_KEY_RETRIES):
        managed_key = None
        response_text = ""
        start_time = time.perf_counter()
        try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Gemini API keys in the pool.")

        client = genai.Client(api_key=managed_key.key_string)
        prompt = GEMINI_ANALYST_BATCH_PROMPT.format(
            batch_input_json=json.dumps(batch_data, indent=2)
        )

        if simplify:
            prompt = prompt + GEMINI_ANALYST_SIMPLIFY_ADDON

        logging.info(
            f"Calling Gemini Analyst with batch of {len(batch_data)} problems "
            f"(key: ...{managed_key.key_string[-4:]})"
            + (" [SIMPLIFY MODE]" if simplify else "")
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(safety_settings=_SAFETY_SETTINGS)
        )

        if not response.text:
            block_reason = "Unknown"
            if response.candidates and response.candidates[0].finish_reason:
                block_reason = response.candidates[0].finish_reason.name
            raise Exception(f"Gemini API call was blocked or returned no text. Reason: {block_reason}")

        response_text = response.text

        # Parse JSON from markdown block
        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not match:
            raise ValueError(
                "Could not find a valid JSON markdown block in the model's response."
            )

        json_string = match.group(1)
        try:
            parsed_json = json.loads(json_string)
        except json.JSONDecodeError as json_err:
            # Attempt a repair pass: truncate after the last clean top-level }
            # This handles cases where Gemini truncates mid-string value
            logging.warning(f"JSON parse failed ({json_err}). Attempting repair...")
            last_brace = json_string.rfind('}', 0, json_err.pos)
            repaired = json_string[:last_brace + 1] if last_brace >= 0 else None
            if repaired:
                try:
                    parsed_json = json.loads(repaired + '}')
                    logging.info("JSON repair succeeded (truncated at last clean brace).")
                except json.JSONDecodeError:
                    raise ValueError(
                        f"JSON parse failed and repair unsuccessful. "
                        f"Original error: {json_err}. Raw snippet: {json_string[max(0,json_err.pos-50):json_err.pos+50]!r}"
                    )
            else:
                raise ValueError(
                    f"JSON parse failed with no repair point found. Error: {json_err}"
                )

        # Track usage
        tokens_in = getattr(response, 'usage_metadata', None)

            # Track usage
            tokens_in = getattr(response, 'usage_metadata', None)
            if tokens_in and hasattr(tokens_in, 'prompt_token_count'):
                key_manager.log_usage(
                    managed_key,
                    tokens_in=tokens_in.prompt_token_count,
                    tokens_out=getattr(tokens_in, 'candidates_token_count', 0),
                )

            key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=estimated_tokens)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            db.log_metric(
                'ANALYSIS', 'api_call', duration_ms, True,
                {'service': 'gemini', 'batch_size': len(batch_data)},
            )

            return (parsed_json, response_text)

        except Exception as e:
            last_error = e
            outcome = KeyStatus.RATE_LIMITED
            error_str = str(e).lower()
            if managed_key and ("api key not valid" in error_str or "permission_denied" in error_str):
                logging.warning(f"DETECTED INVALID API KEY: ...{managed_key.key_string[-4:]}. Marking INVALID.")
                outcome = KeyStatus.INVALID
            elif managed_key and ("resource_exhausted" in error_str or "quota" in error_str or "429" in error_str):
                logging.warning(
                    f"DAILY QUOTA EXHAUSTED for key ...{managed_key.key_string[-4:]}. "
                    f"Marking EXHAUSTED until midnight UTC. Retrying with next key..."
                )
                outcome = KeyStatus.EXHAUSTED
            if managed_key:
                key_manager.release_key(managed_key, outcome, tokens_used=0)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            db.log_metric(
                'ANALYSIS', 'api_call', duration_ms, False,
                {'service': 'gemini', 'error': str(e)[:200]},
            )
            logging.error(f"Gemini API batch call failed (attempt {_attempt + 1}): {e}")
            if response_text:
                logging.error(f"--- RAW RESPONSE START ---\n{response_text[:2000]}\n--- RAW RESPONSE END ---")

            # Only retry on exhaustion/rate-limit; reraise immediately on other errors
            if outcome not in (KeyStatus.EXHAUSTED, KeyStatus.RATE_LIMITED):
                raise

    raise last_error


def call_groq_implementer(
    problem_html: str,
    pseudocode: str,
    vjs_report: str,
    key_manager: KeyManager,
    problem_class: str = 'standard',
) -> str:
    """
    Calls the Groq API to generate C++ code from pseudocode.

    Args:
        problem_html: The HTML statement of the problem.
        pseudocode: The language-agnostic pseudocode for the solution.
        vjs_report: Feedback from any previous failed verification attempt.
        key_manager: The KeyManager instance for Groq API keys.
        problem_class: One of standard/interactive/special_judge/constructive.

    Returns:
        The raw C++ code as a string.
    """
    estimated_tokens = _estimate_tokens(problem_html + pseudocode)
    managed_key = None
    start_time = time.perf_counter()

    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Groq API keys in the pool.")

        class_instructions = _CLASS_INSTRUCTIONS.get(problem_class, '')
        client = Groq(api_key=managed_key.key_string)
        prompt = GROQ_IMPLEMENTER_PROMPT.format(
            problem_html=problem_html[:8000],
            pseudocode=pseudocode,
            vjs_report=(vjs_report or "None")[:2000],
            class_instructions=class_instructions,
        )

        logging.info(
            f"Calling Groq Implementer [{GROQ_MODEL_NAME}] "
            f"(key: ...{managed_key.key_string[-4:]}, class: {problem_class})"
        )

        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_MODEL_NAME,
            )
        except Exception as primary_err:
            # Fallback to secondary model if primary fails
            logging.warning(
                f"Primary model {GROQ_MODEL_NAME} failed: {primary_err}. "
                f"Falling back to {GROQ_FALLBACK_MODEL}."
            )
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=GROQ_FALLBACK_MODEL,
            )

        tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0

        # Track token budget
        if chat_completion.usage:
            key_manager.log_usage(
                managed_key,
                tokens_in=chat_completion.usage.prompt_tokens or 0,
                tokens_out=chat_completion.usage.completion_tokens or 0,
            )

        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=tokens_used)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'IMPLEMENTATION', 'api_call', duration_ms, True,
            {'service': 'groq', 'tokens_used': tokens_used, 'problem_class': problem_class},
        )

        raw_code = chat_completion.choices[0].message.content
        return _sanitize_cpp_code(raw_code)

    except RateLimitError as e:
        if managed_key:
            key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)
        logging.error(f"Groq API call failed due to rate limit: {e}")
        raise

    except Exception as e:
        if managed_key:
            key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'IMPLEMENTATION', 'api_call', duration_ms, False,
            {'service': 'groq', 'error': str(e)[:200]},
        )
        logging.error(f"Groq API call failed: {e}")
        raise


def call_gemini_implementer(
    problem_html: str,
    pseudocode: str,
    vjs_report: str,
    key_manager: KeyManager,
    problem_class: str = 'standard',
) -> str:
    """
    Calls the Gemini API to generate C++ code from pseudocode.
    Escalation fallback used when Groq repeatedly fails to implement complex pseudocode.
    """
    estimated_tokens = _estimate_tokens(problem_html + pseudocode)
    managed_key = None
    start_time = time.perf_counter()

    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Gemini API keys in the pool.")

        client = genai.Client(api_key=managed_key.key_string)
        class_instructions = _CLASS_INSTRUCTIONS.get(problem_class, '')
        prompt = GROQ_IMPLEMENTER_PROMPT.format(
            problem_html=problem_html[:8000],
            pseudocode=pseudocode,
            vjs_report=(vjs_report or "None")[:2000],
            class_instructions=class_instructions,
        )

        logging.info(
            f"Calling Gemini Implementer (ESCALATION) [{GEMINI_MODEL_NAME}] "
            f"(key: ...{managed_key.key_string[-4:]}, class: {problem_class})"
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(safety_settings=_SAFETY_SETTINGS),
        )

        if not response.text:
            raise Exception("Gemini Implementer returned empty response.")

        tokens_in = getattr(response, 'usage_metadata', None)
        if tokens_in and hasattr(tokens_in, 'prompt_token_count'):
            key_manager.log_usage(
                managed_key,
                tokens_in=tokens_in.prompt_token_count,
                tokens_out=getattr(tokens_in, 'candidates_token_count', 0),
            )

        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=estimated_tokens)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'IMPLEMENTATION', 'api_call', duration_ms, True,
            {'service': 'gemini_escalation', 'problem_class': problem_class},
        )
        return _sanitize_cpp_code(response.text)

    except Exception as e:
        outcome = KeyStatus.RATE_LIMITED
        error_str = str(e).lower()
        if managed_key and ("api key not valid" in error_str or "permission_denied" in error_str):
            logging.warning(f"DETECTED INVALID API KEY: ...{managed_key.key_string[-4:]}. Marking INVALID.")
            outcome = KeyStatus.INVALID
        elif managed_key and ("resource_exhausted" in error_str or "quota" in error_str or "429" in error_str):
            logging.warning(
                f"DAILY QUOTA EXHAUSTED for key ...{managed_key.key_string[-4:]}. "
                f"Marking EXHAUSTED until midnight UTC."
            )
            outcome = KeyStatus.EXHAUSTED
        if managed_key:
            key_manager.release_key(managed_key, outcome, tokens_used=0)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric(
            'IMPLEMENTATION', 'api_call', duration_ms, False,
            {'service': 'gemini_escalation', 'error': str(e)[:200]},
        )
        logging.error(f"Gemini Implementer escalation failed: {e}")
        raise


def call_gemini_fuzz_generator_batch(
    batch_data: List[Dict[str, Any]],
    key_manager: KeyManager,
) -> Tuple[Dict[str, str], str]:
    """
    Calls Gemini to generate a Python fuzz test input generator script for a batch.

    Returns:
        Tuple of (parsed_json, raw_response_text).
    """
    estimated_tokens = _estimate_tokens(str(batch_data))
    managed_key = None
    response_text = ""
    start_time = time.perf_counter()

    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Gemini API keys for fuzz generation in the pool.")

        client = genai.Client(api_key=managed_key.key_string)
        prompt = GEMINI_FUZZ_GENERATOR_BATCH_PROMPT.format(
            batch_input_json=json.dumps(batch_data, indent=2)[:50000]
        )

        logging.info(f"Calling Gemini Fuzz Generator for batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
        
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(safety_settings=_SAFETY_SETTINGS)
        )

        if not response.text:
            block_reason = "Unknown"
            if response.candidates and response.candidates[0].finish_reason:
                block_reason = response.candidates[0].finish_reason.name
            raise Exception(f"Gemini API call blocked/empty. Reason: {block_reason}")

        response_text = response.text

        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not match:
            raise ValueError("Could not find a valid JSON markdown block in the model's response.")
        
        json_string = match.group(1)
        try:
            parsed_json = json.loads(json_string)
        except json.JSONDecodeError as json_err:
            logging.warning(f"Fuzz generator JSON parse failed ({json_err}). Attempting repair...")
            last_brace = json_string.rfind('}', 0, json_err.pos)
            repaired = json_string[:last_brace + 1] if last_brace >= 0 else None
            if repaired:
                try:
                    parsed_json = json.loads(repaired + '}')
                    logging.info("Fuzz generator JSON repair succeeded.")
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Fuzz generator JSON parse failed and repair unsuccessful. Error: {json_err}"
                    )
            else:
                raise ValueError(f"Fuzz generator JSON parse failed with no repair point. Error: {json_err}")

        tokens_in = getattr(response, 'usage_metadata', None)
        if tokens_in and hasattr(tokens_in, 'prompt_token_count'):
            key_manager.log_usage(
                managed_key,
                tokens_in=tokens_in.prompt_token_count,
                tokens_out=getattr(tokens_in, 'candidates_token_count', 0),
            )

        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=estimated_tokens)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('FUZZ_GENERATOR', 'api_call', duration_ms, True, {'service': 'gemini', 'batch_size': len(batch_data)})

        return (parsed_json, response_text)

    except Exception as e:
        outcome = KeyStatus.RATE_LIMITED
        error_str = str(e).lower()
        if managed_key and ("api key not valid" in error_str or "permission_denied" in error_str):
            logging.warning(f"DETECTED INVALID API KEY: ...{managed_key.key_string[-4:]}. Marking INVALID.")
            outcome = KeyStatus.INVALID
        elif managed_key and ("resource_exhausted" in error_str or "quota" in error_str or "429" in error_str):
            logging.warning(
                f"DAILY QUOTA EXHAUSTED for key ...{managed_key.key_string[-4:]}. "
                f"Marking EXHAUSTED until midnight UTC."
            )
            outcome = KeyStatus.EXHAUSTED
        if managed_key:
            key_manager.release_key(managed_key, outcome, tokens_used=0)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        db.log_metric('FUZZ_GENERATOR', 'api_call', duration_ms, False, {'service': 'gemini', 'error': str(e)[:200]})
        logging.error(f"Gemini fuzz generator failed: {e}")
        if response_text:
            logging.error(f"--- RAW RESPONSE START ---\n{response_text[:2000]}\n--- RAW RESPONSE END ---")
        raise