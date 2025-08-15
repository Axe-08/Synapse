# synapse/api_clients.py (Corrected with Import)
import os
import logging
import time
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
from synapse.key_manager import KeyManager, KeyStatus # <<< KEY FIX: Import KeyManager

# --- Configuration and API Key Loading ---
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not GEMINI_API_KEY or not GROQ_API_KEY:
    raise ValueError("Please set GEMINI_API_KEY and GROQ_API_KEY in your .env file.")

# Configure the clients
genai.configure(api_key=GEMINI_API_KEY) # This is just a default, will be overridden
groq_client = Groq(api_key=GROQ_API_KEY) # This is just a default, will be overridden

# --- LLM Models ---
gemini_model_name = 'gemini-1.5-flash-latest'
groq_model_name = "llama3-8b-8192"

# --- Prompt Engineering ---

GEMINI_ANALYST_PROMPT = """
You are an expert software engineer and algorithm designer. Your task is to analyze a C++ solution to a competitive programming problem and produce a high-quality, language-agnostic pseudocode.

**RULES:**
1.  **Analyze Context:** Read the provided problem statement HTML to understand the goal.
2.  **Analyze Code:** Read the provided reference C++ solution to understand the implementation.
3.  **Generate Pseudocode:** Write clear, step-by-step pseudocode that describes the core logic of the algorithm.
4.  **Be Language-Agnostic:** Do NOT use any C++ specific syntax (e.g., pointers, templates, #include). Describe the logic in plain, universal terms.
5.  **Focus on Logic:** Explain the data structures used (e.g., "Initialize a hash map", "Use a priority queue"), the main loops, and the key decision-making steps.
6.  **Clarity is Key:** The output must be clean, well-structured, and easy for another AI or a human programmer to understand and re-implement in any language.
7.  **Output ONLY Pseudocode:** Do not include any explanations, greetings, or introductory text. Your entire output should be the pseudocode itself.

**PROBLEM CONTEXT (HTML):**
{problem_html}

**REFERENCE SOLUTION (C++):**
```cpp
{solution_code}
```

**PSEUDOCODE:**
"""

GROQ_IMPLEMENTER_PROMPT = """
You are a world-class competitive programmer specializing in writing clean, efficient, and correct C++ code. Your task is to implement a solution based *only* on the provided problem context and detailed pseudocode.

**RULES:**
1.  **Adhere to Pseudocode:** Follow the logic specified in the pseudocode exactly. Do not add, remove, or change the core algorithm.
2.  **Use Context:** Read the problem statement HTML to understand data types, constraints, and input/output formats.
3.  **Write Production-Ready C++:** The code must be a complete, runnable program. Include necessary headers (like `<bits/stdc++.h>`) and fast I/O operations (`ios_base::sync_with_stdio(false); cin.tie(NULL);`).
4.  **Output ONLY Code:** Do not include any explanations, greetings, or markdown formatting like ```cpp. Your entire output must be the raw C++ code.

**PROBLEM CONTEXT (HTML):**
{problem_html}

**PSEUDOCODE:**
{pseudocode}

**C++ SOLUTION:**
"""

# --- API Call Functions with Resilience and Key Rotation ---

def call_gemini_analyst(problem_html: str, solution_code: str, key_manager: KeyManager) -> str:
    """Calls the Gemini API using a key from the KeyManager."""
    prompt = GEMINI_ANALYST_PROMPT.format(problem_html=problem_html, solution_code=solution_code)
    max_retries = 5
    
    for attempt in range(max_retries):
        managed_key = None
        try:
            managed_key = key_manager.get_key()
            if not managed_key:
                raise Exception("No available Gemini API keys in the pool.")

            genai.configure(api_key=managed_key.key_string)
            model = genai.GenerativeModel(gemini_model_name)
            
            logging.info(f"Calling Gemini Analyst (key ending '...{managed_key.key_string[-4:]}')...")
            response = model.generate_content(prompt)
            
            key_manager.release_key(managed_key, KeyStatus.AVAILABLE)
            logging.info("Gemini Analyst call successful.")
            return response.text.strip()

        except Exception as e:
            logging.warning(f"Gemini API call failed on attempt {attempt + 1}: {e}")
            if "429" in str(e) and managed_key: # Check for rate limit error
                key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED)
                logging.info(f"Key ...{managed_key.key_string[-4:]} was rate-limited. Placing in cooldown.")
            elif managed_key:
                key_manager.release_key(managed_key, KeyStatus.AVAILABLE)

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff before next attempt
            else:
                logging.error("Gemini API call failed after all retries.")
                raise

def call_groq_implementer(problem_html: str, pseudocode: str, key_manager: KeyManager) -> str:
    """Calls the Groq API using a key from the KeyManager."""
    prompt = GROQ_IMPLEMENTER_PROMPT.format(problem_html=problem_html, pseudocode=pseudocode)
    max_retries = 5
    
    for attempt in range(max_retries):
        managed_key = None
        try:
            managed_key = key_manager.get_key()
            if not managed_key:
                raise Exception("No available Groq API keys in the pool.")

            client = Groq(api_key=managed_key.key_string)
            
            logging.info(f"Calling Groq Implementer (key ending '...{managed_key.key_string[-4:]}')...")
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=groq_model_name,
            )
            
            key_manager.release_key(managed_key, KeyStatus.AVAILABLE)
            logging.info("Groq Implementer call successful.")
            return chat_completion.choices[0].message.content.strip()
            
        except Exception as e:
            logging.warning(f"Groq API call failed on attempt {attempt + 1}: {e}")
            if "429" in str(e) and managed_key:
                key_manager.release_key(managed_key, KeyStatus.RATE_LIMITED)
                logging.info(f"Key ...{managed_key.key_string[-4:]} was rate-limited. Placing in cooldown.")
            elif managed_key:
                key_manager.release_key(managed_key, KeyStatus.AVAILABLE)

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logging.error("Groq API call failed after all retries.")
                raise
