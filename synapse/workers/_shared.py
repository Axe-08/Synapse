# synapse/workers/_shared.py
"""
Shared helpers and constants used across worker modules.
"""
import logging
import json
import time
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from typing import List, Optional, Dict, Any

import synapse.database as db
from synapse.key_manager import KeyManager
from config import (
    MAX_ANALYSIS_RETRIES,
    MAX_IMPLEMENTATION_RETRIES,
    MAX_RESCRAPING_ATTEMPTS,
    INITIAL_CALIBRATION_TOLERANCE_FACTOR,
    N_REFERENCE_SOLUTIONS,
    MIN_VIABLE_ORACLES,
    VJS_COMPILATION_TIMEOUT,
)

# Maximum number of page loads before a browser instance is retired
MAX_BROWSER_USES: int = 25


def _voter(outputs: List[str]) -> Optional[str]:
    """
    Determines the majority consensus from a list of outputs.
    Returns the winning output only if it has a strict majority (> 50%).
    Returns None on a hung jury.
    """
    if not outputs:
        return None
    counts = Counter(outputs)
    most_common, count = counts.most_common(1)[0]
    if count > len(outputs) / 2:
        return most_common
    return None


def _score_code_quality(code: str) -> int:
    """
    Calculates a simple quality heuristic for a C++ solution.
    A lower score means cleaner, more standard code (preferred for analysis).
    """
    score = 0
    score += code.count("#define") * 5
    score += code.count("#include")
    score += code.count("scanf") * 2
    score += code.count("printf") * 2
    return score
