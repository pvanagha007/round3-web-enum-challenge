"""
Round 3 - Web Enumeration CTF Challenge
Chain: ffuf (find hidden portal) -> Hydra (crack login, with lockout) -> flag

Run locally:
    pip install flask --break-system-packages
    python3 app.py
App runs on http://127.0.0.1:5000
"""

from flask import Flask, request, render_template_string, redirect, url_for
import time

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CONFIG - tune these to control difficulty / total solve time
# ---------------------------------------------------------------------------
HIDDEN_PATH = "internal-portal-x92"     # the directory ffuf must discover
VALID_USERNAME = "dev_admin"            # hinted at via HTML comment on homepage
VALID_PASSWORD = "yT7g#BCK!BQ4"         # random -- not guessable from clues, only via wordlist OR the hidden log trail
MAX_ATTEMPTS = 3                        # failed attempts before lockout
LOCKOUT_SECONDS = 90                    # 90s lockout every 3rd wrong attempt

# base64 of VALID_PASSWORD, buried in a fake incident log -- the "smart shortcut"
# path for anyone who actually reads source code two hops deep instead of
# brute-forcing. See /static/app.js -> mentions /static/debug.log -> contains this.
ENCODED_PASSWORD_HINT = "eVQ3ZyNCQ0shQlE0"

RAW_TOKEN = "jdwkhekdjbefh"             # the "found" token
TARGET_DOMAIN = "roundthree.ctf"        # fixed suffix
FLAG = f"CTF{{{RAW_TOKEN}_{TARGET_DOMAIN}}}"   # prepended format -> token FIRST

# in-memory attempt tracker: { ip: {"count": int, "locked_until": float} }
attempts = {}

# ---------------------------------------------------------------------------
# HOMEPAGE - looks like a normal small business site, nothing obviously wrong
# ---------------------------------------------------------------------------
HOME_HTML = """
<!DOCTYPE html>
<html>
<head><title>Harbor Logistics Co.</title></head>
<body style="font-family:sans-serif;max-width:700px;margin:60px auto;">
  <h1>Harbor Logistics Co.</h1>
  <p>Reliable freight solutions since 2003.</p>
  <p>Contact us at info@harborlogistics.example</p>
  <!-- TODO: remove test account before launch -- dev_admin still active on staging portal -->
  <footer><small>&copy; 2024 Harbor Logistics Co.</small></footer>
</body>
</html>
"""

ROBOTS_TXT = """User-agent: *
Disallow: /old-site
Disallow: /tmp-backup
Disallow: /admin
Disallow: /staging-portal
"""
# The real HIDDEN_PATH is deliberately NOT listed here anymore --
# ffuf against the full wordlist is meant to be the only discovery route.

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Staff Portal</title></head>
<body style="font-family:sans-serif;max-width:400px;margin:80px auto;">
  <h2>Harbor Logistics - Staff Portal</h2>
  {% if locked %}
    <p style="color:red;">Too many failed attempts. Try again in {{ wait }}s.</p>
  {% else %}
    <form method="POST">
      <input name="username" placeholder="username" style="width:100%;margin-bottom:8px;"><br>
      <input name="password" type="password" placeholder="password" style="width:100%;margin-bottom:8px;"><br>
      <button type="submit">Log in</button>
    </form>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
  {% endif %}
  <script src="/static/app.js"></script>
</body>
</html>
"""

APP_JS = """// Harbor Logistics staff portal - login handler (placeholder, no real logic here)
console.log("portal loaded");
// TODO: verbose auth logging was left on after the Jan incident, ops never
// cleaned it up -- see /static/debug.log if you need to check what happened
// during the credential rotation. Should probably delete this file too.
"""

DEBUG_LOG = f"""[2024-01-03 02:11:04] INFO  portal_svc: starting session cleanup
[2024-01-03 02:11:09] INFO  portal_svc: 14 stale sessions purged
[2024-01-03 02:13:47] WARN  auth_svc: repeated auth failures from 10.0.4.19, monitoring
[2024-01-03 02:14:02] INFO  auth_svc: on-call rotated temp cred per incident-2024-0103
[2024-01-03 02:14:02] DEBUG auth_svc: rotation payload (base64, remove before prod): {ENCODED_PASSWORD_HINT}
[2024-01-03 02:14:11] WARN  auth_svc: verbose debug logging still enabled, ticket OPS-441 filed
[2024-01-03 02:19:33] INFO  portal_svc: session cleanup complete
"""


SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Welcome</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:80px auto;">
  <h2>Welcome, dev_admin.</h2>
  <p>Flag: <code>{{ flag }}</code></p>
</body>
</html>
"""


@app.route("/")
def home():
    return HOME_HTML


@app.route("/robots.txt")
def robots():
    return ROBOTS_TXT, 200, {"Content-Type": "text/plain"}


@app.route("/static/app.js")
def app_js():
    return APP_JS, 200, {"Content-Type": "application/javascript"}


@app.route("/static/debug.log")
def debug_log():
    return DEBUG_LOG, 200, {"Content-Type": "text/plain"}


@app.route(f"/{HIDDEN_PATH}", methods=["GET", "POST"])
def portal():
    ip = request.remote_addr
    now = time.time()
    record = attempts.get(ip, {"count": 0, "locked_until": 0})

    locked = now < record["locked_until"]
    wait = int(record["locked_until"] - now) if locked else 0
    error = None

    if request.method == "POST" and not locked:
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == VALID_USERNAME and password == VALID_PASSWORD:
            attempts.pop(ip, None)
            return render_template_string(SUCCESS_HTML, flag=FLAG)
        else:
            record["count"] += 1
            if record["count"] >= MAX_ATTEMPTS:
                record["locked_until"] = now + LOCKOUT_SECONDS
                record["count"] = 0
                locked = True
                wait = LOCKOUT_SECONDS
            attempts[ip] = record
            error = "Invalid credentials."

    return render_template_string(LOGIN_HTML, locked=locked, wait=wait, error=error)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
