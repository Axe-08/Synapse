import os
import google.generativeai as genai
import sys
from dotenv import load_dotenv

load_dotenv()
def test_api_key(api_key):
    """
    Tests a single Gemini API key by trying to list available models.

    Args:
        api_key (str): The API key to test.

    Returns:
        bool: True if the key is valid and working, False otherwise.
    """
    try:
        # Configure the generative AI library with the provided API key.
        # This is a necessary step before making any API calls.
        genai.configure(api_key=api_key)

        # Make a simple, low-cost API call to list the available models.
        # If this call succeeds, it means the API key is valid and authenticated.
        # We only need to check if the list is not empty.
        models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # If we get a list of models, the key is working.
        if models:
            print(f"✅ Key ending in '...{api_key[-4:]}': SUCCESS")
            return True
        else:
            # This case is unlikely if the configure step passed, but included for completeness.
            print(f"❌ Key ending in '...{api_key[-4:]}': FAILED (No models found)")
            return False

    except Exception as e:
        # If any exception occurs during configuration or the API call,
        # it's likely due to an invalid or unresponsive key.
        print(f"❌ Key ending in '...{api_key[-4:]}': FAILED")
        # Optional: Uncomment the line below to see the specific error message.
        # print(f"   Error: {e}")
        return False

def main():
    """
    Main function to retrieve, split, and test the API keys.
    """
    print("--- Starting Gemini API Key Test ---")

    # Retrieve the environment variable 'GEMINI_API_KEYS'.
    # If the variable is not set, os.getenv returns None.
    api_keys_string = os.getenv('GEMINI_API_KEYS')

    if not api_keys_string:
        print("\nError: The environment variable 'GEMINI_API_KEYS' is not set.")
        print("Please set it with your comma-separated API keys.")
        # Exit the script if the environment variable is missing.
        sys.exit(1)

    # Split the string of keys into a list.
    # The .strip() method is used on each key to remove any accidental whitespace.
    api_keys = [key.strip() for key in api_keys_string.split(',')]

    print(f"Found {len(api_keys)} API key(s) to test.\n")

    working_keys = []
    failed_keys = []

    # Loop through each key and test it.
    for key in api_keys:
        if not key: # Skip any empty strings that might result from extra commas
            continue
        if test_api_key(key):
            working_keys.append(key[-4:]) # Store last 4 digits for summary
        else:
            failed_keys.append(key[-4:]) # Store last 4 digits for summary

    # Print a summary of the results.
    print("\n--- Test Summary ---")
    print(f"Total keys tested: {len(api_keys)}")
    print(f"Working keys: {len(working_keys)}")
    print(f"Failed keys: {len(failed_keys)}")
    if failed_keys:
        print(f"Keys that failed (last 4 digits): {', '.join(failed_keys)}")
    print("--------------------\n")


if __name__ == "__main__":
    # Before running, make sure you have the library installed:
    # pip install google-generativeai
    main()
