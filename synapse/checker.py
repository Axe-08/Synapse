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

def normalize_text(text: str) -> List[str]:
    """Splits text into a list of tokens, ignoring all whitespace and blank lines."""
    return [token for line in text.strip().split('\n') for token in line.strip().split()]

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

    # 1. Direct comparison (fastest check)
    if user_content.strip() == answer_content.strip():
        sys.exit(ACCEPTED)

    # 2. Token-based comparison (handles whitespace differences)
    user_tokens = normalize_text(user_content)
    answer_tokens = normalize_text(answer_content)

    if len(user_tokens) != len(answer_tokens):
        print(f"Wrong Answer: Expected {len(answer_tokens)} tokens, but found {len(user_tokens)}.")
        sys.exit(WRONG_ANSWER)

    for i, (user_token, answer_token) in enumerate(zip(user_tokens, answer_tokens)):
        is_float_comparison = ('.' in user_token or '.' in answer_token)

        if is_float_comparison:
            if not compare_floats(answer_token, user_token):
                print(f"Wrong Answer: Mismatch on token {i+1}. Expected float '{answer_token}', got '{user_token}'.")
                sys.exit(WRONG_ANSWER)
        elif user_token != answer_token:
            print(f"Wrong Answer: Mismatch on token {i+1}. Expected '{answer_token}', got '{user_token}'.")
            sys.exit(WRONG_ANSWER)
            
    # If all tokens match (potentially with float tolerance), but the raw files didn't, it's a Presentation Error.
    print("Presentation Error: Output is numerically correct but differs in whitespace.")
    sys.exit(PRESENTATION_ERROR)


if __name__ == "__main__":
    main()