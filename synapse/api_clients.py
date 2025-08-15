# synapse/api_clients.py (Corrected Formatting)
import logging
import time
import json
from typing import List, Dict, Any

import google.generativeai as genai
from groq import Groq

from synapse.key_manager import KeyManager, KeyStatus

# --- Model Configuration ---
GEMINI_MODEL_NAME = 'gemini-2.5-pro-latest'
GROQ_MODEL_NAME = "llama3-8b-8192"

# --- Prompt Engineering ---
GEMINI_ANALYST_BATCH_PROMPT = """
You are an expert algorithm designer. Your task is to analyze a batch of C++ solutions for competitive programming problems and produce high-quality, language-agnostic pseudocode for each.

**RULES:**
1.  You will be given a list of JSON objects. Each object contains a `problem_id`, the problem's `html_statement`, and the `reference_code`.
2.  For each problem, you must analyze the context and the code to understand the core algorithm.
3.  Your output **MUST** be a single JSON object (a dictionary) where the keys are the `problem_id`s from the input, and the values are the corresponding pseudocode strings.
4.  The pseudocode must be clear, step-by-step, and language-agnostic. Do NOT use C++ specific syntax. Focus on logic, data structures, and key operations.
5.  If a problem has feedback from a previous failed attempt (`vjs_report`), use it to correct your logic.
6.  Ensure your final output is a valid JSON that can be parsed directly. Do not include any text or explanations outside of the final JSON object.

**INPUT BATCH:**
{batch_input_json}


**OUTPUT JSON:**
"""

GROQ_IMPLEMENTER_PROMPT = """
You are a world-class competitive programmer specializing in writing clean, efficient, and correct C++ code. Your task is to implement a solution based *only* on the provided problem context and detailed pseudocode.

**RULES:**

1.  **Adhere to Pseudocode:** Follow the logic specified in the pseudocode exactly. Do not add, remove, or change the core algorithm.
2.  **Use Context:** Read the problem statement HTML to understand data types, constraints, and input/output formats.
3.  **Write Production-Ready C++:** The code must be a complete, runnable program. Include necessary headers (like `<bits/stdc++.h>`) and fast I/O operations (`ios_base::sync_with_stdio(false); cin.tie(NULL);`).
4.  **Output ONLY Code:** Do not include any explanations, greetings, or markdown formatting like \`\`\`cpp. Your entire output must be the raw C++ code.
5.  **Correction (if applicable):** A report from a previous failed compilation (`vjs_report`) is provided. Use it to fix the error.

**PROBLEM CONTEXT (HTML):**
{problem_html}

**PSEUDOCODE:**
{pseudocode}

**PREVIOUS COMPILE ERROR (VJS REPORT):**
{vjs_report}

**C++ SOLUTION:**
"""

def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Dict[str, str]:
"""Calls the Gemini API with a batch of problems."""
# TODO: Implement token estimation for the batch
estimated_tokens = len(str(batch_data)) # A very rough starting point
managed_key = None
try:
    managed_key = key_manager.get_key(estimated_tokens)
    if not managed_key:
        raise Exception("No available Gemini API keys in the pool.")

    genai.configure(api_key=managed_key.key_string)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    
    prompt = GEMINI_ANALYST_BATCH_PROMPT.format(batch_input_json=json.dumps(batch_data, indent=2))
    
    logging.info(f"Calling Gemini Analyst with a batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
    response = model.generate_content(prompt)
    
    # TODO: Calculate actual tokens used from response for better key management
    key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0) 
    return json.loads(response.text)

except Exception as e:
    # TODO: Add more specific error handling to differentiate between RATE_LIMITED, EXHAUSTED, etc.
    if managed_key:
        key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)
    logging.error(f"Gemini API batch call failed: {e}")
    raise

def call_groq_implementer(problem_html: str, pseudocode: str, vjs_report: str, key_manager: KeyManager) -> str:
"""Calls the Groq API to generate C++ code."""
# TODO: Implement token estimation
estimated_tokens = len(problem_html) + len(pseudocode)
managed_key = None
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
    
    # TODO: Calculate actual tokens
    key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0)
    return chat_completion.choices[0].message.content.strip()

except Exception as e:
    if managed_key:
        key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)
    logging.error(f"Groq API call failed: {e}")
    raise