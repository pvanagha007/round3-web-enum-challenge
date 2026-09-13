"""
Round 3 - Web Enumeration CTF Challenge (escalated / hardened version)
Chain: ffuf (find MULTIPLE hidden portals, only one is real) -> cross-test
credentials found in a leaked log against the RIGHT portal -> Hydra brute
force as the fallback -> flag. Full of decoys on purpose.

Run locally:
    pip install flask --break-system-packages
    python3 app.py
App runs on http://127.0.0.1:5000
"""

from flask import Flask, request, render_template_string
import time

app = Flask(__name__)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
HIDDEN_PATH = "internal-portal-x92"     # the ONE real portal
VALID_USERNAME = "dev_admin"
VALID_PASSWORD = "yT7g#BCK!BQ4"
MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 90

RAW_TOKEN = "jdwkhekdjbefh"
TARGET_DOMAIN = "roundthree.ctf"
FLAG = f"CTF{{{RAW_TOKEN}_{TARGET_DOMAIN}}}"          # the REAL flag

# --- decoy portals: also findable via ffuf, also have working logins, but
# every credential/flag they produce is FAKE. Each has its own lockout too,
# so testing wrong guesses against them costs real time, same as the real one.
DECOY_PORTALS = {
    "staging-portal-y44": {
        "username": "staging_admin",
        "password": "Staging123!",
        "flag": "CTF{av0dkfjwplqz_roundthree.ctf}",   # looks legit, is NOT the answer
    },
    "legacy-admin-q17": {
        "username": "legacy_admin",
        "password": "Legacy2020!",
        "flag": "CTF{mzxcvbnqwerty_roundthree.ctf}",
    },
    "backup-access-z8": {
        "username": "backup_user",
        "password": "Backup2021!",
        "flag": "CTF{qplsxrjhtdyfu_roundthree.ctf}",
    },
}

# base64 payloads found in the leaked log. Two are dead-end decoys that
# match the decoy portals above (so if you try them on the REAL portal they
# just fail, and if you try them on a decoy portal you get a FAKE flag that
# looks completely legitimate). The third needs an EXTRA step -- decode,
# then reverse -- before it matches the real portal's password.
LOG_PAYLOAD_DECOY_1 = "U3RhZ2luZzEyMyE="          # -> "Staging123!" (decoy portal only)
LOG_PAYLOAD_DECOY_2 = "TGVnYWN5MjAyMCE="          # -> "Legacy2020!" (decoy portal only)
LOG_PAYLOAD_REAL    = "NFFCIUtDQiNnN1R5"          # -> decode, THEN reverse -> real password

# in-memory lockout trackers, one dict per portal path
attempts_by_portal = {HIDDEN_PATH: {}, **{p: {} for p in DECOY_PORTALS}}

# ---------------------------------------------------------------------------
# HOMEPAGE
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
# None of the real or decoy portal paths are listed here on purpose --
# ffuf against the wordlist is the only discovery route for all of them.

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
  {% if show_js %}<script src="/static/app.js"></script>{% endif %}
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
[2024-01-03 02:14:02] INFO  auth_svc: on-call rotated 3 temp creds during incident-2024-0103, all logged below (should not be here, ticket OPS-441 filed)
[2024-01-03 02:14:02] DEBUG auth_svc: rotation payload A (base64): {LOG_PAYLOAD_DECOY_1}
[2024-01-03 02:14:05] DEBUG auth_svc: rotation payload B (base64): {LOG_PAYLOAD_DECOY_2}
[2024-01-03 02:14:09] DEBUG auth_svc: rotation payload C (base64, note: encoder double-processed this one per OPS-441, may need extra decode pass): {LOG_PAYLOAD_REAL}
[2024-01-03 02:19:33] INFO  portal_svc: session cleanup complete
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head><title>Welcome</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:80px auto;">
  <h2>Welcome, {{ user }}.</h2>
  <p>Flag: <code>{{ flag }}</code></p>
</body>
</html>
"""

# obvious "lazy guess" bait for anyone who skips enumeration and just tries
# well-known paths (or asks an LLM to "just try /flag")
BAIT_FLAG = "CTF{nyfwexkqzblm_roundthree.ctf}"
BAIT_HTML = f"""
<!DOCTYPE html>
<html><head><title>Congratulations?</title></head>
<body style="font-family:sans-serif;max-width:500px;margin:80px auto;">
<h2>Nice try.</h2>
<p>Flag: <code>{BAIT_FLAG}</code></p>
</body></html>
"""


def _check_lockout(portal_key, ip):
    now = time.time()
    record = attempts_by_portal[portal_key].get(ip, {"count": 0, "locked_until": 0})
    locked = now < record["locked_until"]
    wait = int(record["locked_until"] - now) if locked else 0
    return record, locked, wait


def _register_failure(portal_key, ip, record):
    now = time.time()
    record["count"] += 1
    if record["count"] >= MAX_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_SECONDS
        record["count"] = 0
    attempts_by_portal[portal_key][ip] = record
    return record["locked_until"] > now


def _handle_portal(portal_key, valid_username, valid_password, flag_value, show_js=False):
    ip = request.remote_addr
    record, locked, wait = _check_lockout(portal_key, ip)
    error = None

    if request.method == "POST" and not locked:
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == valid_username and password == valid_password:
            attempts_by_portal[portal_key].pop(ip, None)
            return render_template_string(SUCCESS_HTML, flag=flag_value, user=valid_username)
        else:
            now_locked = _register_failure(portal_key, ip, record)
            if now_locked:
                _, locked, wait = _check_lockout(portal_key, ip)
            error = "Invalid credentials."

    return render_template_string(LOGIN_HTML, locked=locked, wait=wait, error=error, show_js=show_js)


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


# lazy-guess bait -- looks like a win, isn't
@app.route("/flag")
@app.route("/congratulations")
def bait():
    return BAIT_HTML


@app.route(f"/{HIDDEN_PATH}", methods=["GET", "POST"])
def real_portal():
    return _handle_portal(HIDDEN_PATH, VALID_USERNAME, VALID_PASSWORD, FLAG, show_js=True)


def _make_decoy_route(path, info):
    def handler():
        return _handle_portal(path, info["username"], info["password"], info["flag"], show_js=False)
    handler.__name__ = f"decoy_{path}"
    return handler


for _path, _info in DECOY_PORTALS.items():
    app.add_url_rule(f"/{_path}", view_func=_make_decoy_route(_path, _info), methods=["GET", "POST"])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
