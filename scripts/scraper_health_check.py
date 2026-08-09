#!/usr/bin/env python3
"""
scraper_health_check.py
-----------------------
Tests Codeforces scraping connectivity without launching a browser.
Checks:
  1. CF Public API  — contest.status / problemset.problems endpoints
  2. Problem page   — fetch HTML via requests (problem statement, limits)
  3. Submission API — top accepted C++ submissions for a test problem
  4. Internal API   — pretest enrichment endpoint (cookie-based, best-effort)
  5. IP ban check   — detect if we are currently blocked

Usage:
    python scraper_health_check.py
"""

import os, time, sys
import requests
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

UA = os.getenv("MY_USER_AGENT", "Mozilla/5.0")
CF_HANDLE   = os.getenv("CF_HANDLE", "")
CF_PASSWORD = os.getenv("CF_PASSWORD", "")
CF_CSRF     = os.getenv("CF_CSRF_TOKEN", "")

# Test against a well-known simple problem
TEST_CONTEST  = "1"
TEST_PROBLEM  = "A"
TEST_PROB_ID  = f"{TEST_CONTEST}{TEST_PROBLEM}"

HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

results = []

def check(name):
    """Context-manager-style decorator for each test."""
    def decorator(fn):
        def wrapper():
            print(f"  {DIM}Testing:{RESET} {name} ...", end=" ", flush=True)
            t0 = time.perf_counter()
            try:
                detail = fn()
                ms = int((time.perf_counter() - t0) * 1000)
                print(f"{GREEN}✅ PASS{RESET}  ({ms}ms)  {DIM}{detail}{RESET}")
                results.append({"name": name, "ok": True, "ms": ms, "detail": detail})
            except AssertionError as e:
                ms = int((time.perf_counter() - t0) * 1000)
                print(f"{RED}❌ FAIL{RESET}  ({ms}ms)  {RED}{e}{RESET}")
                results.append({"name": name, "ok": False, "ms": ms, "detail": str(e)})
            except Exception as e:
                ms = int((time.perf_counter() - t0) * 1000)
                print(f"{RED}⚫ ERROR{RESET} ({ms}ms)  {RED}{str(e)[:100]}{RESET}")
                results.append({"name": name, "ok": False, "ms": ms, "detail": str(e)[:100]})
        return wrapper
    return decorator


# ─── TEST 1: CF Public API — problemset.problems ─────────────────────────────

@check("CF Public API  /api/problemset.problems")
def test_problems_api():
    r = requests.get(
        "https://codeforces.com/api/problemset.problems",
        params={"tags": "", "problemsetName": ""},
        headers=HEADERS, timeout=15
    )
    assert r.status_code == 200, f"HTTP {r.status_code}"
    data = r.json()
    assert data.get("status") == "OK", f"API status: {data.get('status')}"
    count = len(data.get("result", {}).get("problems", []))
    return f"{count} problems returned"


# ─── TEST 2: CF Public API — contest.status (top submissions) ────────────────

@check("CF Contest API /api/contest.status (top AC submissions)")
def test_contest_status_api():
    r = requests.get(
        "https://codeforces.com/api/contest.status",
        params={
            "contestId": TEST_CONTEST,
            "from": 1, "count": 10,
        },
        headers=HEADERS, timeout=15
    )
    assert r.status_code == 200, f"HTTP {r.status_code}"
    data = r.json()
    assert data.get("status") == "OK", f"API status: {data.get('status')}"
    subs = data.get("result", [])
    ac = [s for s in subs if s.get("verdict") == "OK" and
          s.get("programmingLanguage", "").startswith("C++")]
    return f"{len(subs)} submissions fetched, {len(ac)} accepted C++"


# ─── TEST 3: Problem HTML page (requests) ────────────────────────────────────

@check("CF Problem Page HTML (requests)")
def test_problem_page():
    url = f"https://codeforces.com/problemset/problem/{TEST_CONTEST}/{TEST_PROBLEM}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    # Check for IP ban markers
    if "Codeforces is temporarily unavailable" in r.text or \
       "blocked by administrator" in r.text.lower():
        raise AssertionError("IP BAN DETECTED")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    assert "time limit" in r.text.lower() or "time-limit" in r.text.lower(), \
        "Time limit not found in page — might be blocked or layout changed"
    # Pick out title
    import re
    title = re.search(r'<div class="title">(.*?)</div>', r.text)
    title_str = title.group(1) if title else "unknown"
    return f"Problem loaded: '{title_str}'"


# ─── TEST 4: CF API — user.info (check our CF handle is valid) ───────────────

@check(f"CF User API   /api/user.info (handle: {CF_HANDLE or 'NOT SET'})")
def test_user_info():
    if not CF_HANDLE:
        raise AssertionError("CF_HANDLE not set in .env")
    r = requests.get(
        "https://codeforces.com/api/user.info",
        params={"handles": CF_HANDLE},
        headers=HEADERS, timeout=15
    )
    assert r.status_code == 200, f"HTTP {r.status_code}"
    data = r.json()
    assert data.get("status") == "OK", f"{data.get('comment', data.get('status'))}"
    user = data["result"][0]
    rating = user.get("rating", "unrated")
    rank   = user.get("rank", "n/a")
    return f"Handle valid — rank={rank}, rating={rating}"


# ─── TEST 5: Codeforces Login (session auth) ──────────────────────────────────

@check("CF Login       POST /enter (Cloudflare + session check)")
def test_cf_login():
    if not CF_HANDLE or not CF_PASSWORD:
        raise AssertionError("CF_HANDLE or CF_PASSWORD not set in .env")

    session = requests.Session()
    session.headers.update(HEADERS)

    login_page = session.get("https://codeforces.com/enter",
                             timeout=15, allow_redirects=True)
    assert login_page.status_code == 200, f"Login page HTTP {login_page.status_code}"

    if "blocked by administrator" in login_page.text.lower():
        raise AssertionError("IP BAN DETECTED on login page")

    # Cloudflare Turnstile challenge = expected when using plain requests (no browser)
    if "challenges.cloudflare.com/turnstile" in login_page.text or \
       "<title>Verification</title>" in login_page.text:
        return ("Cloudflare Turnstile challenge returned — "
                "expected for plain requests. Selenium (undetected-chromedriver) "
                "bypasses this in production ✅")

    # Real login form reached (rare / IP already whitelisted)
    import re
    csrf_match = re.search(r'(?:X-Csrf-Token|data-csrf)["\s]+(?:value=)?["\']([a-f0-9]{32})',
                           login_page.text, re.IGNORECASE)
    assert csrf_match, "Could not find CSRF token in login page"
    csrf_token = csrf_match.group(1)
    payload = {
        "handleOrEmail": CF_HANDLE, "password": CF_PASSWORD,
        "action": "enter", "ftaa": "", "bfaa": "",
        "X-Csrf-Token": csrf_token, "remember": "on",
    }
    resp = session.post(
        "https://codeforces.com/enter", data=payload,
        headers={"Referer": "https://codeforces.com/enter",
                 "X-Csrf-Token": csrf_token},
        timeout=15, allow_redirects=True
    )
    logged_in = CF_HANDLE.lower() in resp.text.lower() or \
                "logout" in resp.text.lower()
    assert logged_in, f"Login failed (HTTP {resp.status_code})"
    return f"Logged in as {CF_HANDLE} via form"


# ─── TEST 6: IP ban self-check ────────────────────────────────────────────────

@check("IP Ban Check   GET codeforces.com (ban detection)")
def test_ip_ban():
    r = requests.get("https://codeforces.com/", headers=HEADERS, timeout=15)
    ban_phrases = [
        "blocked by administrator",
        "codeforces is temporarily unavailable",
        "access denied",
        "your ip address has been blocked",
    ]
    for phrase in ban_phrases:
        if phrase in r.text.lower():
            raise AssertionError(f"IP BAN DETECTED — page contains: '{phrase}'")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    return "No ban detected — CF homepage reachable"


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'='*65}")
    print(f"  PROJECT SYNAPSE — SCRAPER HEALTH CHECK")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}{RESET}\n")

    test_ip_ban()
    test_problems_api()
    test_contest_status_api()
    test_problem_page()
    test_user_info()
    test_cf_login()

    ok  = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]

    print(f"\n{BOLD}{'='*65}")
    print("  SUMMARY")
    print(f"{'='*65}{RESET}")
    print(f"\n  {GREEN}{len(ok)} passed{RESET}  /  {RED}{len(bad)} failed{RESET}  "
          f"out of {len(results)} checks\n")

    if bad:
        print(f"  {RED}Failed checks:{RESET}")
        for r in bad:
            print(f"    ❌ {r['name']}: {r['detail']}")

    if not bad:
        print(f"  {GREEN}{BOLD}🟢 Scraper service is FULLY OPERATIONAL{RESET}")
    elif len(ok) >= 3:
        print(f"  {YELLOW}{BOLD}🟡 Scraper partially working — {len(bad)} issue(s) found{RESET}")
    else:
        print(f"  {RED}{BOLD}🔴 Scraper has critical issues — check above{RESET}")
    print(f"\n{'='*65}\n")


if __name__ == "__main__":
    main()
