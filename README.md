# Round 3 — Web Enumeration (ffuf + Hydra)

## What this round teaches
1. **Directory discovery with ffuf** — finding a page nobody linked to.
2. **Credential brute-forcing with Hydra** — cracking a login, while respecting
   a lockout (so blind spraying punishes you).
3. Flags in this round use a **prepended** format: `CTF{token_domain}` where the
   random token comes FIRST, not last.

Participants are only given: the running URL, and (optionally) the two wordlist
files if your event is offline / you don't want them downloading SecLists.

---

## Part A — Get it running locally (today, for your demo)

### 1. Install dependencies
```bash
pip install flask --break-system-packages
```

### 2. Run the app
```bash
cd round3-challenge
python3 app.py
```
It will start on `http://127.0.0.1:5000`. Visit it in a browser — you'll see a
normal-looking logistics company homepage. That's the whole point: nothing
looks obviously "CTF" about it.

### 3. Install ffuf and Hydra (if not already installed)
```bash
# ffuf
sudo apt install ffuf        # Debian/Ubuntu
# or: go install github.com/ffuf/ffuf/v2@latest

# hydra
sudo apt install hydra
```

---

## Part B — Solve it yourself (do this before the demo so you know it works)

**Important context first:** ffuf will find FOUR hidden paths, not one —
`internal-portal-x92` (real) plus three decoys (`staging-portal-y44`,
`legacy-admin-q17`, `backup-access-z8`). Every decoy has its own working
login and returns a completely convincing, correctly-formatted flag that is
**wrong**. This is intentional.

### Step 1 — Discover ALL hidden paths with ffuf
```bash
ffuf -u http://127.0.0.1:5000/FUZZ -w wordlists/ffuf_directories.txt -mc 200
```
You'll get four hits back. Nothing in the ffuf output tells you which one is
real — that's deliberate. There's also a `/flag` and `/congratulations`
lazy-guess bait route that returns yet another fake flag immediately, for
anyone (or any LLM) that skips enumeration and just tries obvious paths.

### Step 2 — The leaked log (found via source-code digging, not ffuf)
View-source the REAL portal (`/internal-portal-x92`) → notice `<script src="/static/app.js">`
→ open `/static/app.js` → comment points to `/static/debug.log` → open it.
The decoy portals do NOT have this script tag, so this trail only exists off
the real one — a further signal for a careful participant, though nothing
tells them that explicitly.

The log contains THREE base64 payloads:
- Payload A decodes to `Staging123!` — this is the DECOY portal's real
  password. Try it there and you'll "successfully" log in and get a flag.
  It is not the answer.
- Payload B decodes to `Legacy2020!` — same story, works on the OTHER decoy
  portal, also not the answer.
- Payload C decodes to `4QB!KCB#g7Ty` — this is NOT a working password as-is.
  It needs one more step: **reverse the string** → `yT7g#BCK!BQ4` → THIS
  works, but only on the real portal (`internal-portal-x92`).

So even the "smart" path has a built-in trap: two of the three leaked
credentials work immediately and hand back a real-looking flag, actively
rewarding participants for stopping early and submitting the wrong one.
Only the third, extra-decoded one is real.

### Step 3 — Hydra fallback (if the log trail isn't found)
Same as before — brute force the REAL portal specifically:
```bash
hydra -l dev_admin -P wordlists/hydra_passwords.txt \
  -t 1 -W 3 \
  127.0.0.1 -s 5000 http-post-form \
  "/internal-portal-x92:username=^USER^&password=^PASS^:Invalid credentials"
```
Real password at line 100 of 130 → ~33 lockout cycles × 90s ≈ 50 min, same as
before. Note Hydra pointed at a DECOY portal's path will also "succeed" if
run against its own themed password — but Hydra has no way of knowing which
portal is correct either, so running it against all four costs real extra
time too (each has its own independent lockout).

### Step 4 — Log in and grab the REAL flag
```
http://127.0.0.1:5000/internal-portal-x92
```
Username: `dev_admin`, Password: `yT7g#BCK!BQ4`
```
CTF{jdwkhekdjbefh_roundthree.ctf}
```
Any flag starting `CTF{av0dkfjwplqz...}`, `CTF{mzxcvbnqwerty...}`,
`CTF{qplsxrjhtdyfu...}`, or `CTF{nyfwexkqzblm...}` is a decoy/bait — if your
event's flag-checker (CTFd or similar) is set up with only the real flag as
correct, submitting any of these will just show up as wrong, which is
expected and part of the round.

CTF{jdwkhekdjbefh_roundthree.ctf}
```
Note the token (`jdwkhekdjbefh`) is at the **front**, exactly as your seniors
asked for.

---

## Part C — Tuning difficulty (this is how you control the "1hr+" target)

Everything below lives at the top of `app.py`:

| Variable | What it controls | To make it HARDER |
|---|---|---|
| `HIDDEN_PATH` | the ffuf target | make it less like the wordlist entry, or bump ffuf wordlist to 2000+ decoys |
| `wordlists/ffuf_directories.txt` size | how long ffuf takes | more decoy lines = longer scan time |
| `MAX_ATTEMPTS` / `LOCKOUT_SECONDS` | brute-force pain | lower `MAX_ATTEMPTS` (e.g. 3) and raise `LOCKOUT_SECONDS` (e.g. 300) forces participants to be *precise* with their password list instead of spraying |
| `wordlists/hydra_passwords.txt` | password search space | more decoys, spread further from obvious guesses |
| Homepage hints | how easy it is to build a good password list | remove/obscure the "Harbor" branding clues to force more guessing |

**As currently configured** (`MAX_ATTEMPTS=3`, `LOCKOUT_SECONDS=240`, real
password at line ~40 of a 70-line list, ffuf target buried in a 1200-line
list): expect roughly 45–70 minutes total — a mix of a few minutes of real
ffuf scan time plus ~50 minutes of enforced lockout waiting during Hydra.
This time cost comes from the server's throttle, not from hidden clues, which
is deliberate: it can't be shortcut by asking an LLM to "just guess the
password" the way a themed password could be.

To push it further past 1hr, or bring it back down if it's too brutal:
- Raise/lower `LOCKOUT_SECONDS` — this is your main dial, it scales almost linearly with total solve time.
- Move the real password further into (or earlier in) `hydra_passwords.txt` — later position = more lockout cycles.
- Raise/lower `MAX_ATTEMPTS` — fewer attempts before lockout = more total lockouts over the same wordlist.

Re-run the `random.seed(...)` generation script (ask me and I'll regenerate)
with bigger decoy counts once you're happy with the balance.

---

## Part D — Git workflow (do this once app.py works)
```bash
git clone https://github.com/MRebeccaF/round-3.git
cd round-3
git checkout -b round3-additions
# copy app.py, wordlists/, README.md into this repo
git add .
git commit -m "Add ffuf/Hydra enumeration challenge with lockout"
git push origin round3-additions
# then open a PR into master, or merge locally if you have access
```

## Part E — Demo checklist for tomorrow
- [ ] `python3 app.py` running, homepage loads
- [ ] Run through Part B yourself end-to-end once, timed
- [ ] Have both wordlists ready to hand to participants (or confirm they can
      pull SecLists if it's an online event)
- [ ] Explain the flag format explicitly in the rules (`token_domain`, token first)
- [ ] Mention the lockout in the rules — "brute force is allowed, but the
      server will throttle you if you're not careful" is a fair warning, not
      a spoiler