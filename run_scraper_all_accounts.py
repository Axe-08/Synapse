#!/usr/bin/env python3
"""
run_scraper_all_accounts.py
----------------------------
Runs the debug_scrapper.py pipeline for every CF account in .env,
overriding CF_HANDLE and CF_PASSWORD via subprocess environment variables.

Each account gets its own browser session (separate subprocess).
Results are printed as they come in.

Usage:
    venv/bin/python3 run_scraper_all_accounts.py
"""

import os, re, sys, subprocess, time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

PYTHON = os.path.join(os.path.dirname(__file__), "venv", "bin", "python3")
SCRIPT = os.path.join(os.path.dirname(__file__), "debug_scrapper.py")


def parse_accounts() -> list[dict]:
    """Parse all CF_HANDLE / CF_PASSWORD pairs from .env (active + commented)."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    accounts = []
    seen = set()
    pending_handle = None
    with open(env_path) as f:
        for line in f:
            raw = line.strip()
            is_commented = raw.startswith("#")
            stripped = raw.lstrip("#").strip()
            mh = re.match(r'CF_HANDLE\s*=\s*["\']?([^\s"\']+)["\']?', stripped)
            mp = re.match(r'CF_PASSWORD\s*=\s*["\']?([^\s"\']+)["\']?', stripped)
            if mh:
                pending_handle = {"handle": mh.group(1), "commented": is_commented}
            elif mp and pending_handle:
                h = pending_handle["handle"]
                if h.lower() not in seen:
                    seen.add(h.lower())
                    accounts.append({
                        "handle":   h,
                        "password": mp.group(1),
                        "active":   not pending_handle["commented"],
                    })
                pending_handle = None
    return accounts


def reset_chrome_profile():
    """Delete the chrome_profile directory so the next run starts fresh."""
    profile_dir = os.path.join(os.path.dirname(__file__), "chrome_profile")
    if os.path.exists(profile_dir):
        import shutil
        shutil.rmtree(profile_dir)
        print(f"  {DIM}  → chrome_profile/ cleared{RESET}")
    # Also kill any stale Chrome/chromedriver processes
    os.system("pkill -f 'undetected_chromedriver' 2>/dev/null; pkill -f 'chrome' 2>/dev/null; sleep 1")


def run_for_account(account: dict, idx: int, total: int) -> dict:
    """Run debug_scrapper.py as a subprocess with overridden CF credentials."""
    h, pw = account["handle"], account["password"]
    tag = f"{GREEN}[ACTIVE]{RESET}" if account["active"] else f"{DIM}[commented]{RESET}"

    print(f"\n{'='*72}")
    print(f"  [{idx}/{total}] {BOLD}{h}{RESET}  {tag}")
    print(f"{'='*72}")

    # Clear the chrome profile so this account must log in fresh
    reset_chrome_profile()

    # Build env: inherit everything, override CF credentials
    env = os.environ.copy()
    env["CF_HANDLE"]   = h
    env["CF_PASSWORD"] = pw

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [PYTHON, SCRIPT],
            env=env,
            cwd=os.path.dirname(__file__),
            capture_output=False,   # let output stream live to terminal
            timeout=300,            # 5 min max per account
        )
        elapsed = time.perf_counter() - t0
        ok = proc.returncode == 0
        return {"handle": h, "ok": ok, "elapsed": elapsed,
                "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        print(f"\n{RED}⏱  TIMEOUT after {elapsed:.0f}s for {h}{RESET}")
        return {"handle": h, "ok": False, "elapsed": elapsed, "returncode": -1,
                "error": "TIMEOUT"}
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"\n{RED}⚫  ERROR for {h}: {e}{RESET}")
        return {"handle": h, "ok": False, "elapsed": elapsed, "returncode": -1,
                "error": str(e)}


def main():
    print(f"\n{BOLD}{'='*72}")
    print(f"  PROJECT SYNAPSE — FULL SCRAPER TEST — ALL CF ACCOUNTS")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*72}{RESET}\n")

    accounts = parse_accounts()
    print(f"  Found {BOLD}{len(accounts)}{RESET} CF accounts.\n")
    for i, a in enumerate(accounts, 1):
        tag = f"{GREEN}[ACTIVE]{RESET}" if a["active"] else f"{DIM}[commented]{RESET}"
        print(f"    {i}. {a['handle']:<25} {tag}")

    print(f"\n  {YELLOW}Running debug_scrapper.py once per account (sequential).{RESET}")
    print(f"  {DIM}Each run opens a browser, logs in, scrapes problem 2066B, then closes.{RESET}\n")

    results = []
    for i, account in enumerate(accounts, 1):
        result = run_for_account(account, i, len(accounts))
        results.append(result)

    # ── Final summary ──────────────────────────────────────────────────────────
    print(f"\n\n{BOLD}{'='*72}")
    print("  FINAL SUMMARY")
    print(f"{'='*72}{RESET}\n")
    print(f"  {'Handle':<25} {'Result':<12} {'Time'}")
    print(f"  {'─'*25} {'─'*11} {'─'*8}")
    for r in results:
        if r["ok"]:
            status = f"{GREEN}✅ PASS{RESET}"
        elif r.get("error") == "TIMEOUT":
            status = f"{YELLOW}⏱  TIMEOUT{RESET}"
        else:
            status = f"{RED}❌ FAIL (rc={r['returncode']}){RESET}"
        print(f"  {r['handle']:<25} {status:<20} {r['elapsed']:.1f}s")

    passed = sum(1 for r in results if r["ok"])
    print(f"\n  {GREEN}{passed}/{len(results)} accounts passed the full scraper pipeline.{RESET}\n")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
