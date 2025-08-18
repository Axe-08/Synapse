# synapse/checker.py
import sys
import math
from typing import List

# Verdict exit codes, inspired by testlib.h and DOMjudge conventions
ACCEPTED = 0
WRONG_ANSWER = 1
PRESENTATION_ERROR = 2
INTERNAL_ERROR = 3 # Used for checker errors, e.g., file not found

def compare_floats(expected_str: str, actual_str: str, tolerance: float = 1e-6) -> bool:
    """Compares two strings as floats with a relative or absolute tolerance."""
    try:
        expected_f = float(expected_str)
        actual_f = float(actual_str)
        
        # Check for absolute tolerance near zero
        if abs(expected_f - actual_f) < tolerance:
            return True
        
        # Check for relative tolerance for larger numbers, avoiding division by zero
        if expected_f != 0:
            if abs((expected_f - actual_f) / expected_f) < tolerance:
                return True
                
    except (ValueError, TypeError):
        # If conversion to float fails, it's not a valid float comparison
        return False
        
    return False

def normalize_text_strict(text: str) -> List[str]:
    """Splits text into a list of tokens, preserving order but ignoring whitespace."""
    return [token for line in text.strip().split('\n') for token in line.strip().split()]

def compare_tokens(user_tokens: List[str], answer_tokens: List[str]) -> bool:
    """Compares two lists of tokens, handling floats."""
    if len(user_tokens) != len(answer_tokens):
        return False

    for user_token, answer_token in zip(user_tokens, answer_tokens):
        # Attempt float comparison if either token looks like a float
        is_float_comparison = ('.' in user_token or '.' in answer_token)
        if is_float_comparison:
            if not compare_floats(answer_token, user_token):
                return False
        elif user_token != answer_token:
            return False
    return True

def main():
    if len(sys.argv) != 4:
        print("Usage: python checker.py <input_file> <user_output_file> <answer_file>")
        sys.exit(INTERNAL_ERROR)

    _, input_path, user_output_path, answer_path = sys.argv

    try:
        with open(user_output_path, 'r', encoding='utf-8') as f:
            user_content = f.read()
        with open(answer_path, 'r', encoding='utf-8') as f:
            answer_content = f.read()
    except FileNotFoundError as e:
        print(f"Checker Error: Could not find file {e.filename}")
        sys.exit(INTERNAL_ERROR)

    # 1. Direct comparison (fastest check for perfect match)
    if user_content.strip() == answer_content.strip():
        sys.exit(ACCEPTED)

    user_tokens = normalize_text_strict(user_content)
    answer_tokens = normalize_text_strict(answer_content)

    # 2. Strict token-by-token comparison (handles whitespace differences)
    if compare_tokens(user_tokens, answer_tokens):
        print("Presentation Error: Output is numerically correct but differs in whitespace.")
        sys.exit(PRESENTATION_ERROR)

    # 3. Fallback: Sort-and-compare for problems with unordered output
    if sorted(user_tokens) == sorted(answer_tokens):
        print("Presentation Error: Output is correct as a set of tokens but is in the wrong order.")
        sys.exit(PRESENTATION_ERROR)

    # 4. If all checks fail, it's a Wrong Answer
    if len(user_tokens) != len(answer_tokens):
        print(f"Wrong Answer: Expected {len(answer_tokens)} tokens, but found {len(user_tokens)}.")
    else:
        # Find the first differing token for a helpful message
        for i, (user_token, answer_token) in enumerate(zip(user_tokens, answer_tokens)):
            if user_token != answer_token:
                print(f"Wrong Answer: Mismatch on token {i+1}. Expected '{answer_token}', got '{user_token}'.")
                break
        else:
             print("Wrong Answer: Content mismatch.")
             
    sys.exit(WRONG_ANSWER)

if __name__ == "__main__":
    main()