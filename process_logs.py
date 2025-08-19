# process_logs.py
"""
A utility script to process and compress the verbose output from debug_pipeline.py.

This script reads a raw log file, identifies common patterns of long, repetitive
text (like large test cases) and overly long single lines (like HTML),
and replaces them with concise summaries. This makes the log much more readable
and easier to share for analysis.

Usage:
1. Run the debug pipeline and save its output to a file:
   python debug_pipeline.py > raw_debug.log 2>&1

2. Run this script on the raw log file:
   python process_logs.py raw_debug.log

3. A compressed log file named `processed_raw_debug.log` will be created.
"""
import re
import sys
import os
from collections import Counter

# --- Configuration ---
# Lines longer than this will be truncated if not otherwise compressed.
TRUNCATION_LENGTH = 1000
# A pattern needs to repeat at least this many times to be compressed.
MIN_REPETITIONS = 10
# The maximum length of a token to consider for repetition compression.
MAX_TOKEN_LENGTH = 50

def compress_line(line: str) -> str:
    """
    Applies various compression techniques to a single line of log output.
    """
    stripped_line = line.strip()

    # 1. Repetitive Token Compression
    # This is effective for test cases like "0 0 0 0 0 0..."
    tokens = stripped_line.split()
    if len(tokens) > MIN_REPETITIONS * 2:
        # Find the most common token
        token_counts = Counter(tokens)
        most_common, count = token_counts.most_common(1)[0]

        # Check if it's dominant and not too long (to avoid matching complex strings)
        if count > len(tokens) * 0.7 and len(most_common) < MAX_TOKEN_LENGTH:
            # Check if the pattern is a simple repetition
            # e.g., "0 0 0 0", not "0 1 0 2 0 3"
            is_simple_repetition = all(t == most_common for t in tokens)
            if is_simple_repetition:
                return f"\t[Compressed: Token '{most_common}' repeated {len(tokens)} times]\n"

    # 2. Long, Non-Repetitive Line Truncation (e.g., HTML)
    # This catches long, complex strings that the first method misses.
    if len(line) > TRUNCATION_LENGTH:
        start = line[:200]
        end = line[-200:]
        return f"{start}\n... [Line Truncated, Original Length: {len(line)}] ...\n{end}\n"

    # 3. Return the original line if no compression was applied
    return line

def process_log_file(input_path: str):
    """
    Reads a raw log file, processes it, and writes to a new compressed file.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    # Create a name for the output file
    dir_name, file_name = os.path.split(input_path)
    output_path = os.path.join(dir_name, f"processed_{file_name}")

    print(f"Reading from '{input_path}'...")
    print(f"Writing compressed log to '{output_path}'...")

    lines_processed = 0
    lines_written = 0
    try:
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:

            is_in_artifact_block = False
            for line in infile:
                lines_processed += 1

                # Preserve headers and important log lines
                if line.startswith("===") or "---" in line or "ERROR" in line or "SUCCESS" in line:
                    outfile.write(line)
                    lines_written += 1
                    is_in_artifact_block = "ARTIFACTS AFTER" in line
                    continue

                # If we are in a verbose artifact block, apply compression
                if is_in_artifact_block:
                    compressed = compress_line(line)
                    # Only write if the line was changed or is short
                    if compressed != line or len(line) < 200:
                         outfile.write(compressed)
                         lines_written += 1
                else:
                    # For general logs, just write them as is
                    outfile.write(line)
                    lines_written += 1

    except Exception as e:
        print(f"\nAn error occurred during processing: {e}")

    print("\nProcessing complete.")
    print(f"Total lines read: {lines_processed}")
    print(f"Total lines written: {lines_written} (Reduction: {lines_processed - lines_written})")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_logs.py <path_to_raw_log_file>")
        sys.exit(1)
    
    log_file_path = sys.argv[1]
    process_log_file(log_file_path)

