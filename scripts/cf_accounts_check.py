#!/usr/bin/env python3
"""
cf_accounts_check.py
--------------------
Tests all Codeforces accounts from .env using a single browser session.

For each handle/password pair:
  1. Validates handle by visiting CF profile page via browser (bypasses CF API 404)
  2. Tests login to verify credentials

Run: venv/bin/python3 cf_accounts_check.py
"""

import os, re, time
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

# ── Parse accounts ────────────────────────────────────────────────────────────

def parse_accounts() -> list[dict]:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    accounts = []
    seen = set()
    pending_handle = None
    with open(env_path) as f:
        for line in f:
            raw = line.strip()
            # Strip leading comment chars for matching, but track if commented
            is_commented = raw.startswith("#")
            stripped = raw.lstrip("#").strip()

            mh = re.match(r'CF_HANDLE\s*=\s*["\']?([^\s"\']+)["\']?', stripped)
            mp = re.match(r'CF_PASSWORD\s*=\s*["\']?([^\s"\']+)["\']?', stripped)

            if mh:
                pending_handle = {"handle": mh.group(1), "commented": is_commented}
            elif mp and pending_handle:
                handle = pending_handle["handle"]
                if handle.lower() not in seen:
                    seen.add(handle.lower())
                    accounts.append({
                        "handle": handle,
                        "password": mp.group(1),
                        "active": not pending_handle["commented"],
                    })
                pending_handle = None

    return accounts


# ── Validate handle via browser profile page ──────────────────────────────────

def check_handle_browser(handle: str, driver) -> dict:
    """Visit the CF profile page and scrape user info."""
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        url = f"https://codeforces.com/profile/{handle}"
        driver.get(url)
        time.sleep(2)

        page = driver.page_source
        if "not found" in page.lower() and "user" in page.lower():
            return {"valid": False, "error": "Profile page: user not found"}
        if "404" in driver.title:
            return {"valid": False, "error": "404 page"}

        # Scrape rating
        rating_match = re.search(r'title="[^"]*">(\d+)</span>', page) or \
                       re.search(r'class="user-rank[^>]*>.*?(\d+)', page, re.DOTALL)
        rating_els = re.findall(r'"userRating":(\d+)', page) or \
                     re.findall(r'class="[^"]*rating-\w+[^"]*"[^>]*>(\d+)<', page)

        rank_match = re.search(r'class="[^"]*user-rank[^"]*">\s*<span[^>]*>\s*([^<]+)</span>', page)
        rank = rank_match.group(1).strip() if rank_match else "n/a"

        # Try to get rating from page text
        rating = rating_els[0] if rating_els else "unrated"

        # Simpler: look for the bold rating number in the top section
        bold_rating = re.search(r'<span class=".*?(?:red|orange|violet|blue|cyan|green|gray)-text[^"]*"[^>]*>(\d+)</span>', page)
        if bold_rating:
            rating = bold_rating.group(1)

        # Last online
        last_online_match = re.search(r'title="([^"]+)"[^>]*>\s*Last visit', page) or \
                            re.search(r'Last visit.*?title="([^"]+)"', page)
        last_online = last_online_match.group(1) if last_online_match else "unknown"

        return {
            "valid": True,
            "rating": rating,
            "rank": rank,
            "last_online": last_online,
            "url": url,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)[:80]}


# ── Login test ────────────────────────────────────────────────────────────────

def check_login_browser(handle: str, password: str, driver) -> dict:
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # Logout first if needed
        driver.get("https://codeforces.com/")
        time.sleep(2)
        if "logout" in driver.page_source.lower():
            driver.get("https://codeforces.com/logout")
            time.sleep(2)

        driver.get("https://codeforces.com/enter")
        time.sleep(3)

        # Wait for Cloudflare to pass
        for _ in range(10):
            if "verification" in driver.title.lower() or \
               "just a moment" in driver.title.lower():
                time.sleep(2)
            else:
                break

        page = driver.page_source
        if "handleOrEmail" not in page:
            # Still on challenge page or redirected
            return {"ok": None, "detail": f"Login form unavailable — {driver.title[:40]}"}

        wait = WebDriverWait(driver, 15)
        handle_field = wait.until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
        handle_field.clear()
        handle_field.send_keys(handle)

        pass_field = driver.find_element(By.ID, "password")
        pass_field.clear()
        pass_field.send_keys(password)

        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        time.sleep(4)

        page_after = driver.page_source.lower()
        if "logout" in page_after and handle.lower() in page_after:
            return {"ok": True, "detail": "✅ Login SUCCESS"}
        elif "logout" in page_after:
            return {"ok": True, "detail": "✅ Login SUCCESS (logged in as someone)"}
        elif "invalid" in page_after or "wrong" in page_after:
            return {"ok": False, "detail": "❌ Wrong credentials"}
        else:
            return {"ok": False, "detail": f"❌ Unknown result — {driver.title[:40]}"}
    except Exception as e:
        return {"ok": False, "detail": f"❌ Error: {str(e)[:80]}"}


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'='*70}")
    print(f"  PROJECT SYNAPSE — CF ACCOUNTS HEALTH CHECK")
    print(f"  Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}{RESET}\n")

    accounts = parse_accounts()
    print(f"  Found {BOLD}{len(accounts)}{RESET} CF accounts in .env:\n")
    for i, a in enumerate(accounts, 1):
        tag = f"{GREEN}[ACTIVE]{RESET}" if a["active"] else f"{DIM}[commented]{RESET}"
        print(f"    {i}. {a['handle']:<22} {tag}")

    print(f"\n  {DIM}Launching browser (single session for all tests)...{RESET}\n")

    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    chrome_profile = os.path.join(os.path.dirname(__file__), "chrome_profile")
    options.add_argument(f"--user-data-dir={chrome_profile}")

    driver = uc.Chrome(options=options, headless=True)
    print(f"  {GREEN}Browser launched.{RESET}\n")

    results = []
    try:
        print(f"{CYAN}{'─'*70}")
        print("  TESTING ALL ACCOUNTS (profile check + login per account)")
        print(f"{'─'*70}{RESET}\n")

        for i, a in enumerate(accounts, 1):
            h, pw = a["handle"], a["password"]
            print(f"  [{i}/{len(accounts)}] {BOLD}{h}{RESET}")

            # Profile check
            print(f"         Profile check ... ", end="", flush=True)
            profile = check_handle_browser(h, driver)
            if profile["valid"]:
                print(f"{GREEN}✅ VALID{RESET}  rating={profile['rating']}  rank={profile['rank']}  last_online={profile['last_online']}")
            else:
                print(f"{RED}❌ INVALID — {profile.get('error','')}{RESET}")

            # Login check
            print(f"         Login test    ... ", end="", flush=True)
            t0 = time.perf_counter()
            login = check_login_browser(h, pw, driver)
            ms = int((time.perf_counter() - t0) * 1000)
            col = GREEN if login["ok"] else (YELLOW if login["ok"] is None else RED)
            print(f"{col}{login['detail']}{RESET}  {DIM}({ms}ms){RESET}\n")

            results.append({**a, "profile": profile, "login": login})
            time.sleep(1)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"{BOLD}{'='*70}")
    print("  FINAL SUMMARY")
    print(f"{'='*70}{RESET}\n")
    print(f"  {'#':<3} {'Handle':<22} {'Profile':<10} {'Login':<32} {'Rating'}")
    print(f"  {'─'*3} {'─'*22} {'─'*9} {'─'*31} {'─'*8}")
    for i, r in enumerate(results, 1):
        p_ok = r["profile"]["valid"]
        l_ok = r["login"]["ok"]
        p_col = GREEN if p_ok else RED
        l_col = GREEN if l_ok else (YELLOW if l_ok is None else RED)
        p_str = f"{p_col}✅ valid{RESET}" if p_ok else f"{RED}❌ invalid{RESET}"
        l_str = f"{l_col}{r['login']['detail'][:28]}{RESET}"
        rating = r["profile"].get("rating", "?") if p_ok else "—"
        active = f"{GREEN}●{RESET}" if r["active"] else f"{DIM}○{RESET}"
        print(f"  {active} {r['handle']:<22} {p_str:<18} {l_str:<40} {rating}")

    valid = sum(1 for r in results if r["profile"]["valid"])
    logged = sum(1 for r in results if r["login"]["ok"])
    print(f"\n  Valid handles : {GREEN}{valid}/{len(results)}{RESET}")
    print(f"  Successful logins : {GREEN}{logged}/{len(results)}{RESET}\n")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
