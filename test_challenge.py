# -*- coding: utf-8 -*-
"""
test_challenge.py
-----------------
Automated test suite verifying the complete Round 3 CyberLeek challenge engine:
- Front-of-URL routing & redirects
- Decoys & dummy flags rejection
- Smart Easter Egg solving for all 3 levels
- Real portal credential authentication & real flag retrieval
- Verification Hub progression (Level 1 -> Level 2 -> Level 3 -> Round 4)
- Honeypot traps
- Lockout engine
"""

import os
import sys
import base64
import codecs
import json
import re

# Set short lockout for testing
os.environ["CTF_LOCKOUT_SECONDS"] = "2"

from app import app, LEVEL_CONFIG, ALL_DECOY_FLAGS

def run_tests():
    client = app.test_client()
    print("=" * 70)
    print("  RUNNING COMPLETE VERIFICATION SUITE: CYBERLEEK ROUND 3")
    print("=" * 70)

    # 1. Test Homepage & Robots.txt
    print("[+] Test 1: Testing Landing Page & Robots.txt...")
    r = client.get("/")
    assert r.status_code == 200, "Home page failed"
    assert "EVIDENCE 03 — THE MIRROR" in r.text, "Home page missing case briefing"
    assert "WHEN ONE COPY DISAPPEARS, ANOTHER USUALLY SURVIVES." in r.text

    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Disallow: /flag" in r.text
    print("    -> PASSED.")

    # 2. Test Front-of-URL Fuzzing (Requirement 6)
    print("\n[+] Test 2: Testing Front-of-the-URL Fuzzing Routes (/<FUZZ>/<path>)...")
    # Level 1
    r = client.get("/node-alpha-92/cdn-mirror", follow_redirects=False)
    assert r.status_code == 302, f"L1 Real front fuzz failed with code {r.status_code}"
    assert r.headers["Location"].endswith("/cdn-mirror/node-alpha-92")

    for decoy in ["edge-cache-14", "backup-node-77", "relay-proxy-03"]:
        r = client.get(f"/{decoy}/cdn-mirror", follow_redirects=False)
        assert r.status_code == 302, f"L1 Decoy {decoy} failed"
        assert r.headers["Location"].endswith(f"/cdn-mirror/{decoy}")

    # Level 2
    r = client.get("/shard-vault-88/archive-index", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/archive-index/shard-vault-88")

    for decoy in ["temp-shard-12", "archive-clone-49", "shadow-copy-61"]:
        r = client.get(f"/{decoy}/archive-index", follow_redirects=False)
        assert r.status_code == 302

    # Level 3
    r = client.get("/core-master-x7/disinfo-core", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/disinfo-core/core-master-x7")

    for decoy in ["fiat-leak-91", "market-pump-22", "evidence-burn-55"]:
        r = client.get(f"/{decoy}/disinfo-core", follow_redirects=False)
        assert r.status_code == 302

    # Unmapped front fuzz
    r = client.get("/invalid-token/cdn-mirror")
    assert r.status_code == 404
    print("    -> All 3 Levels Front-of-URL Fuzzing & HTTP 302 Redirects PASSED.")

    # 3. Test Decoys & Dummy Flags
    print("\n[+] Test 3: Testing Decoys and Dummy Flags Generation...")
    for lvl_num, cfg in LEVEL_CONFIG.items():
        base_path = cfg["front_fuzz_path"]
        for dname, dinfo in cfg["decoys"].items():
            r = client.post(f"/{base_path}/{dname}", data={"username": dinfo["username"], "password": dinfo["password"]})
            assert r.status_code == 200, f"Decoy login failed for {dname}"
            assert dinfo["flag"] in r.text, f"Dummy flag missing for {dname}"
            print(f"    -> Decoy {dname} successfully issued dummy flag: {dinfo['flag']}")
    print("    -> All Decoys functional and emitting realistic dummy flags.")

    # 4. Test Honeypot Routes
    print("\n[+] Test 4: Testing Honeypot & Anti-LLM Bait Routes...")
    for bait_url in ["/flag", "/admin", "/secret-backup", "/congratulations"]:
        r = client.get(bait_url)
        assert r.status_code == 200
        assert "CYBERLEEK{llm_blind_hallucination_9012}" in r.text
    print("    -> Honeypot traps PASSED.")

    # 5. Test Smart Easter Eggs (Approach B)
    print("\n[+] Test 5: Testing Smart Easter Egg Paths (No Brute Force)...")
    # L1 Smart Path
    r = client.get("/static/incident_20260814.log")
    assert r.status_code == 200
    m = re.search(r"PAYLOAD:\s*([A-Za-z0-9+/=]+)", r.text)
    assert m, "L1 log payload missing"
    payload_b64 = m.group(1)
    raw_bytes = base64.b64decode(payload_b64)
    l1_smart_pass = "".join(chr(b ^ 0x5A) for b in raw_bytes)
    assert l1_smart_pass == LEVEL_CONFIG[1]["password"], f"L1 smart pass mismatch: {l1_smart_pass}"
    print(f"    -> Level 1 Smart Path successfully recovered password: '{l1_smart_pass}'")

    # L2 Smart Path
    r = client.get("/archive-index/shard-vault-88/manifest.json")
    assert r.status_code == 200
    manifest = json.loads(r.text)
    m2 = re.search(r"'([A-Za-z0-9+/=]+)'", manifest["operator_recovery_memo"])
    assert m2, "L2 cipher missing"
    shifted_b64 = m2.group(1)
    def unshift_5(s):
        res = []
        for c in s:
            if 'a' <= c <= 'z':
                res.append(chr((ord(c) - ord('a') - 5) % 26 + ord('a')))
            elif 'A' <= c <= 'Z':
                res.append(chr((ord(c) - ord('A') - 5) % 26 + ord('A')))
            else:
                res.append(c)
        return ''.join(res)
    raw_b64 = unshift_5(shifted_b64)
    l2_smart_pass = base64.b64decode(raw_b64.encode()).decode()
    assert l2_smart_pass == LEVEL_CONFIG[2]["password"], f"L2 smart pass mismatch: {l2_smart_pass}"
    print(f"    -> Level 2 Smart Path successfully recovered password: '{l2_smart_pass}'")

    # L3 Smart Path
    r = client.get("/disinfo-core/core-master-x7/ledger.csv")
    assert r.status_code == 200
    m3 = re.search(r"base64\(reverse\(rot13\(password\)\)\)\s*=\s*([A-Za-z0-9+/=]+)", r.text)
    assert m3, "L3 seed missing"
    l3_b64 = m3.group(1)
    rev_rot = base64.b64decode(l3_b64).decode()
    rot_str = rev_rot[::-1]
    l3_smart_pass = codecs.decode(rot_str, "rot_13")
    assert l3_smart_pass == LEVEL_CONFIG[3]["password"], f"L3 smart pass mismatch: {l3_smart_pass}"
    print(f"    -> Level 3 Smart Path successfully recovered password: '{l3_smart_pass}'")

    # 6. Test Real Portal Authentication & Real Flags
    print("\n[+] Test 6: Testing Real Portals Authentication...")
    # L1 Real
    r = client.post("/cdn-mirror/node-alpha-92", data={
        "username": LEVEL_CONFIG[1]["username"],
        "password": LEVEL_CONFIG[1]["password"]
    })
    assert r.status_code == 200
    assert LEVEL_CONFIG[1]["flag"] in r.text
    print(f"    -> Level 1 Authenticated! Real Flag: {LEVEL_CONFIG[1]['flag']}")

    # L2 Real
    r = client.post("/archive-index/shard-vault-88", data={
        "username": LEVEL_CONFIG[2]["username"],
        "password": LEVEL_CONFIG[2]["password"]
    })
    assert r.status_code == 200
    assert LEVEL_CONFIG[2]["flag"] in r.text
    print(f"    -> Level 2 Authenticated! Real Flag: {LEVEL_CONFIG[2]['flag']}")

    # L3 Real
    r = client.post("/disinfo-core/core-master-x7", data={
        "username": LEVEL_CONFIG[3]["username"],
        "password": LEVEL_CONFIG[3]["password"]
    })
    assert r.status_code == 200
    assert LEVEL_CONFIG[3]["flag"] in r.text
    print(f"    -> Level 3 Authenticated! Master Flag: {LEVEL_CONFIG[3]['flag']}")

    # 7. Test Verification Hub Flag Validation & Progression
    print("\n[+] Test 7: Testing Verification Hub Flag Validation & Progression...")
    with client.session_transaction() as sess:
        sess.clear()

    # Submitting Decoy Flag -> Must Be Rejected
    r = client.post("/verify", data={"level": 1, "flag": "CYBERLEEK{y0u_f0und_th3_m1rr0r}"})
    assert "DECOY FLAG REJECTED" in r.text, "Decoy flag was not rejected!"
    print("    -> Dummy/Decoy Flag correctly REJECTED by validator.")

    # Submitting Bait Flag -> Must Be Rejected
    r = client.post("/verify", data={"level": 1, "flag": "CYBERLEEK{llm_blind_hallucination_9012}"})
    assert "DECOY FLAG REJECTED" in r.text

    # Submitting L2 flag before L1 -> Prerequisite Error
    r = client.post("/verify", data={"level": 2, "flag": LEVEL_CONFIG[2]["flag"]})
    assert "PREREQUISITE REQUIRED" in r.text
    print("    -> Prerequisite checks functional.")

    # Solve L1
    r = client.post("/verify", data={"level": 1, "flag": LEVEL_CONFIG[1]["flag"]})
    assert "LEVEL 1 DECRYPTED" in r.text
    print("    -> Level 1 Verified. Level 2 unlocked.")

    # Solve L2
    r = client.post("/verify", data={"level": 2, "flag": LEVEL_CONFIG[2]["flag"]})
    assert "LEVEL 2 DECRYPTED" in r.text
    print("    -> Level 2 Verified. Level 3 unlocked.")

    # Solve L3
    r = client.post("/verify", data={"level": 3, "flag": LEVEL_CONFIG[3]["flag"]})
    assert "MASTER FLAG VERIFIED" in r.text
    assert "ROUND 4: EVIDENCE 04 — THE DAY THE INTERNET CHANGED" in r.text
    print("    -> Level 3 Verified. Round 3 100% complete! Round 4 handoff unlocked!")

    # 8. Test Lockout Mechanism
    print("\n[+] Test 8: Testing Lockout Engine (3 strikes -> lockout)...")
    for _ in range(3):
        client.post("/cdn-mirror/node-alpha-92", data={"username": "mirror_admin", "password": "WrongPassword"})
    r = client.get("/cdn-mirror/node-alpha-92")
    assert "ACCESS LOCKOUT ACTIVE" in r.text, "Lockout failed to engage!"
    print("    -> Lockout successfully engaged after threshold failures.")

    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()