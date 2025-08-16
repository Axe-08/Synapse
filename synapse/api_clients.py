# synapse/api_clients.py (Corrected Formatting)
import logging
import time
import json
from typing import List, Dict, Any

import google.generativeai as genai
from groq import Groq

from synapse.key_manager import KeyManager, KeyStatus
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# --- Model Configuration ---
GEMINI_MODEL_NAME = 'gemini-2.5-pro'
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

**PREVIOUS COMPILE ERROR (VJS REPORT):**
{vjs_report}

**C++ SOLUTION:**
"""

def call_gemini_analyst_batch(batch_data: List[Dict[str, Any]], key_manager: KeyManager) -> Dict[str, str]:
    """Calls the Gemini API with a batch of problems, with adjusted safety settings."""
    estimated_tokens = len(str(batch_data))
    
    managed_key = None
    response_text = ""
    try:
        managed_key = key_manager.get_key(estimated_tokens)
        if not managed_key:
            raise Exception("No available Gemini API keys in the pool.")

        genai.configure(api_key=managed_key.key_string)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        prompt = GEMINI_ANALYST_BATCH_PROMPT.format(batch_input_json=json.dumps(batch_data, indent=2))

        # --- NEW: Define permissive safety settings ---
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logging.info(f"Calling Gemini Analyst with a batch of {len(batch_data)} problems (key: ...{managed_key.key_string[-4:]})")
        
        # --- MODIFIED: Pass safety_settings to the API call ---
        response = model.generate_content(prompt, safety_settings=safety_settings)
        response_text = response.text 
             # 1. Strip markdown code block formatting if it exists
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
        
        # 2. Find the start and end of the JSON object within the cleaned text
        json_start_index = cleaned_text.find('{')
        json_end_index = cleaned_text.rfind('}')
        
        if json_start_index == -1 or json_end_index == -1:
            raise ValueError(f"Could not find a valid JSON object in the model's response.")

        json_string = cleaned_text[json_start_index : json_end_index + 1]
              
        # --- NEW: Add a check for a blocked response before parsing ---
        if not response.parts:
            # This indicates the response was blocked despite the settings
            block_reason = "Unknown"
            if response.prompt_feedback:
                block_reason = response.prompt_feedback.block_reason.name
            raise Exception(f"Gemini API call was blocked. Reason: {block_reason}")
            
        key_manager.release_key(managed_key, KeyStatus.AVAILABLE, tokens_used=0) 
        return json.loads(json_string)

    except json.JSONDecodeError as e:

        # This will now catch cases where the model ignores instructions and returns non-JSON
        # Log the problematic response text for debugging
        logging.error(f"Gemini API returned non-JSON response. Error: {e}")
        logging.error(f"--- RAW RESPONSE START ---\n{response_text}\n--- RAW RESPONSE END ---")
        
        if managed_key:
             key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED, tokens_used=0)
        raise # Re-raise the exception to let the worker handle the failure

    except Exception as e:
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