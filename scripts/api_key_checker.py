#!/usr/bin/env python3
"""
api_key_checker.py
------------------
Checks availability and status of all GEMINI_API_KEYS and GROQ_API_KEYS
from the .env file. Runs all checks in parallel for speed.

Usage:
    python api_key_checker.py
"""

import os
import time
import json
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def box(text, colour=CYAN):
    w = len(text) + 4
    return f"{colour}{'─'*w}\n  {text}  \n{'─'*w}{RESET}"

# ── GEMINI ────────────────────────────────────────────────────────────────────

def check_gemini_key(idx: int, key: str) -> dict:
    """Send a minimal 1-token ping to the Gemini API using the new google-genai SDK."""
    short = f"...{key[-8:]}"
    result = {"idx": idx + 1, "short": short, "key": key, "service": "GEMINI"}
    t0 = time.perf_counter()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say OK",
            config=types.GenerateContentConfig(max_output_tokens=5),
        )
        elapsed = time.perf_counter() - t0
        text = resp.text.strip() if resp.text else ""
        if text:
            result.update(status="✅  AVAILABLE", ok=True,
                          latency_ms=int(elapsed * 1000), detail=text)
        else:
            result.update(status="⚠️   BLOCKED / NO OUTPUT", ok=False,
                          latency_ms=int(elapsed * 1000), detail="empty response")
    except Exception as e:
        elapsed = time.perf_counter() - t0
        err = str(e)
        err_low = err.lower()
        if "api key not valid" in err_low or "permission_denied" in err_low or "invalid api key" in err_low:
            tag = "❌  INVALID KEY"
        elif "429" in err or "resource_exhausted" in err_low or "quota" in err_low:
            tag = "🔴  RATE LIMITED / QUOTA"
        elif "billing" in err_low:
            tag = "💳  BILLING ISSUE"
        elif "403" in err:
            tag = "🔒  FORBIDDEN (403)"
        else:
            tag = "⚫  ERROR"
        result.update(status=tag, ok=False,
                      latency_ms=int(elapsed * 1000), detail=err[:120])
    return result


# ── GROQ ──────────────────────────────────────────────────────────────────────

def check_groq_key(idx: int, key: str) -> dict:
    """Send a minimal 1-token ping to the Groq API and report status."""
    short = f"...{key[-8:]}"
    result = {"idx": idx + 1, "short": short, "key": key, "service": "GROQ"}
    t0 = time.perf_counter()
    try:
        from groq import Groq, RateLimitError, AuthenticationError

        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say OK"}],
            model="llama-3.1-8b-instant",   # smallest/fastest model for ping
            max_tokens=5,
        )
        elapsed = time.perf_counter() - t0
        content = resp.choices[0].message.content.strip() if resp.choices else ""
        tokens  = resp.usage.total_tokens if resp.usage else 0
        result.update(status="✅  AVAILABLE", ok=True,
                      latency_ms=int(elapsed * 1000),
                      detail=f"reply='{content}'  tokens_used={tokens}")
    except Exception as e:
        elapsed = time.perf_counter() - t0
        err = str(e)
        if "invalid_api_key" in err.lower() or "authentication" in err.lower() or "401" in err:
            tag = "❌  INVALID KEY"
        elif "rate_limit" in err.lower() or "429" in err or "rate limit" in err.lower():
            tag = "🔴  RATE LIMITED"
        elif "quota" in err.lower():
            tag = "🔴  QUOTA EXCEEDED"
        else:
            tag = "⚫  ERROR"
        result.update(status=tag, ok=False,
                      latency_ms=int(elapsed * 1000), detail=err[:120])
    return result


# ── PRINTING ──────────────────────────────────────────────────────────────────

def print_results(results: list, service: str):
    colour = CYAN if service == "GEMINI" else YELLOW
    print(f"\n{box(f'  {service} API KEYS  ', colour)}\n")

    available = [r for r in results if r.get("ok")]
    unavailable = [r for r in results if not r.get("ok")]

    # Sort by index
    for r in sorted(results, key=lambda x: x["idx"]):
        ok = r.get("ok", False)
        status_col = GREEN if ok else RED
        latency = r.get("latency_ms", "?")
        detail = r.get("detail", "")
        print(f"  [{r['idx']:>2}] {status_col}{r['status']}{RESET}  "
              f"{DIM}Key:{RESET} {r['short']}  "
              f"{DIM}Latency:{RESET} {latency}ms  "
              f"{DIM}Info:{RESET} {detail[:80]}")

    print(f"\n  {BOLD}Summary:{RESET} "
          f"{GREEN}{len(available)} available{RESET} / "
          f"{RED}{len(unavailable)} unavailable{RESET} "
          f"out of {len(results)} keys\n")
    return available, unavailable


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'='*70}")
    print(f"  PROJECT SYNAPSE — API KEY STATUS CHECKER")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}{RESET}\n")

    # --- Load keys ---
    gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "")
    groq_keys_raw   = os.getenv("GROQ_API_KEYS", "")

    gemini_keys = [k.strip() for k in gemini_keys_raw.split(",") if k.strip()]
    groq_keys   = [k.strip() for k in groq_keys_raw.split(",")   if k.strip()]

    if not gemini_keys:
        print(f"{RED}⚠  No GEMINI_API_KEYS found in .env{RESET}")
    if not groq_keys:
        print(f"{RED}⚠  No GROQ_API_KEYS found in .env{RESET}")

    print(f"  Found {BOLD}{len(gemini_keys)}{RESET} Gemini keys and "
          f"{BOLD}{len(groq_keys)}{RESET} Groq keys — checking in parallel...\n")

    # --- Run checks in parallel ---
    gemini_results = []
    groq_results   = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        gemini_futures = {pool.submit(check_gemini_key, i, k): i
                         for i, k in enumerate(gemini_keys)}
        groq_futures   = {pool.submit(check_groq_key,   i, k): i
                         for i, k in enumerate(groq_keys)}

        for f in concurrent.futures.as_completed(gemini_futures):
            gemini_results.append(f.result())
        for f in concurrent.futures.as_completed(groq_futures):
            groq_results.append(f.result())

    # --- Print results ---
    gem_ok, gem_bad = print_results(gemini_results, "GEMINI")
    grq_ok, grq_bad = print_results(groq_results,   "GROQ")

    # --- Final summary ---
    print(f"{BOLD}{'='*70}")
    print("  OVERALL SUMMARY")
    print(f"{'='*70}{RESET}")
    total_ok  = len(gem_ok)  + len(grq_ok)
    total_bad = len(gem_bad) + len(grq_bad)
    total     = total_ok + total_bad
    print(f"\n  Gemini : {GREEN}{len(gem_ok):>2} ✅{RESET}  /  {RED}{len(gem_bad):>2} ❌{RESET}  (of {len(gemini_keys)})")
    print(f"  Groq   : {GREEN}{len(grq_ok):>2} ✅{RESET}  /  {RED}{len(grq_bad):>2} ❌{RESET}  (of {len(groq_keys)})")
    print(f"\n  {'PIPELINE STATUS: '}", end="")
    if gem_ok and grq_ok:
        print(f"{GREEN}{BOLD}🟢 FULLY OPERATIONAL — both Gemini and Groq have viable keys{RESET}")
    elif gem_ok:
        print(f"{YELLOW}{BOLD}🟡 PARTIAL — Gemini OK, all Groq keys failed{RESET}")
    elif grq_ok:
        print(f"{YELLOW}{BOLD}🟡 PARTIAL — Groq OK, all Gemini keys failed{RESET}")
    else:
        print(f"{RED}{BOLD}🔴 CRITICAL — no working keys for either service{RESET}")
    print(f"\n{'='*70}\n")

    # --- Save JSON report ---
    report = {
        "timestamp": datetime.now().isoformat(),
        "gemini": [{"idx": r["idx"], "short": r["short"],
                    "status": r["status"], "ok": r["ok"],
                    "latency_ms": r.get("latency_ms"), "detail": r.get("detail", "")}
                   for r in sorted(gemini_results, key=lambda x: x["idx"])],
        "groq":   [{"idx": r["idx"], "short": r["short"],
                    "status": r["status"], "ok": r["ok"],
                    "latency_ms": r.get("latency_ms"), "detail": r.get("detail", "")}
                   for r in sorted(groq_results,   key=lambda x: x["idx"])],
    }
    out_path = "key_checker_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  {DIM}Full report saved → {out_path}{RESET}\n")


if __name__ == "__main__":
    main()
