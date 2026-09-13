# -*- coding: utf-8 -*-
"""
Round 3 - Web Enumeration CTF Challenge: Evidence 03 — The Mirror
Campaign: CYBERLEEK: THE INTERNET NEVER FORGETS (August 2026 GTA VI Leak)
Difficulty: Hard / Multi-Level Web Enumeration & Forensic Mystery

Architecture:
- 3 Progressive Levels (Level 1 -> Level 2 -> Level 3 -> Round 4 handoff)
- Dual-Approach Solving per level:
    Approach A: Front-of-URL ffuf discovery (/<FUZZ>/<path>) + Lockout-aware Hydra/Python brute force
    Approach B: Deeply hidden murder-mystery Easter Eggs bypassing brute-forcing in minutes
- 3 Fake Redirects & Decoy Portals per level (returning convincing dummy CYBERLEEK{} flags)
- Anti-LLM traps & Decoy verification filters
- Thread-safe concurrency for 50+ teams
"""

import os
import time
import base64
import codecs
import threading
from flask import Flask, request, redirect, render_template_string, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cyberleek_evidence03_mirror_session_key_2026")

# ---------------------------------------------------------------------------
# CONFIGURATION & THRESHOLDS
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = int(os.environ.get("CTF_LOCKOUT_SECONDS", "90"))

# Real & Decoy Portals Specification for all 3 Levels
LEVEL_CONFIG = {
    1: {
        "name": "Level 1: The Abandoned CDN Mirror",
        "front_fuzz_path": "cdn-mirror",
        "real_prefix": "node-alpha-92",
        "username": "mirror_admin",
        "password": "K9#vP2!xL8q",
        "flag": "CYBERLEEK{m1rr0r_n3v3r_f0rg3ts_82a1}",
        "decoys": {
            "edge-cache-14": {
                "username": "edge_operator",
                "password": "CachePassword2026!",
                "flag": "CYBERLEEK{y0u_f0und_th3_m1rr0r}",
            },
            "backup-node-77": {
                "username": "backup_ops",
                "password": "BackupNode2026!",
                "flag": "CYBERLEEK{m1rr0r_1n_h1d1ng}",
            },
            "relay-proxy-03": {
                "username": "relay_user",
                "password": "RelayProxy2026!",
                "flag": "CYBERLEEK{y0u_m1rr0r_m3}",
            },
        },
    },
    2: {
        "name": "Level 2: The Fragmented Archive Shards",
        "front_fuzz_path": "archive-index",
        "real_prefix": "shard-vault-88",
        "username": "archive_curator",
        "password": "W7#mQ9!tZ3x",
        "flag": "CYBERLEEK{sh4rd5_0f_th3_unr3l34s3d_99b4}",
        "decoys": {
            "temp-shard-12": {
                "username": "temp_curator",
                "password": "ShardTemp2026!",
                "flag": "CYBERLEEK{sh4rd_r3c0v3r3d_h3r3}",
            },
            "archive-clone-49": {
                "username": "clone_admin",
                "password": "ClonePass2026!",
                "flag": "CYBERLEEK{n0_sh4rd_1n_th3_cl0n3}",
            },
            "shadow-copy-61": {
                "username": "shadow_daemon",
                "password": "ShadowCopy2026!",
                "flag": "CYBERLEEK{r3c0v3r3d_sh4rd_1n_th3_sh4d0w}",
            },
        },
    },
    3: {
        "name": "Level 3: The Disinformation Core",
        "front_fuzz_path": "disinfo-core",
        "real_prefix": "core-master-x7",
        "username": "core_overseer",
        "password": "R4#zN8!eB1k",
        "flag": "CYBERLEEK{th3_c4mp41gn_w45_th3_m1rr0r_f1n4l}",
        "decoys": {
            "fiat-leak-91": {
                "username": "fiat_trader",
                "password": "FiatBurn2026!",
                "flag": "CYBERLEEK{f14t_l34k_1n_th3_c0r3}",
            },
            "market-pump-22": {
                "username": "market_maker",
                "password": "MarketPump2026!",
                "flag": "CYBERLEEK{m4rk3t_pump_1n_th3_m1rr0r}",
            },
            "evidence-burn-55": {
                "username": "evidence_cleaner",
                "password": "Shredded2026!",
                "flag": "CYBERLEEK{shredd3d_3v1d3nc3_1n_cl34n3r}",
            },
        },
    },
}

# Automated honey-pot bait for naive crawler/LLM guesses
BAIT_FLAGS = [
    "CYBERLEEK{llm_blind_hallucination_9012}",
    "CYBERLEEK{honeypot_scanner_sh4d0w_1337}",
    "CYBERLEEK{lazy_endpoint_crawler_7781}",
]

# Set of all decoy flags across all levels for strict rejection
ALL_DECOY_FLAGS = set(BAIT_FLAGS)
for lvl in LEVEL_CONFIG.values():
    for decoy in lvl["decoys"].values():
        ALL_DECOY_FLAGS.add(decoy["flag"])

# Thread-safe lockout tracker: { portal_key: { ip: {"count": int, "locked_until": float} } }
lockout_lock = threading.Lock()
attempts_by_portal = {}

# ---------------------------------------------------------------------------
# BASE HTML TEMPLATES (CYBERLEEK FORENSIC THEME)
# ---------------------------------------------------------------------------
BASE_CSS = """
:root {
  --bg-color: #07090e;
  --panel-bg: #0e121b;
  --border-color: #1f293d;
  --accent-cyan: #00e5ff;
  --accent-amber: #ffb300;
  --accent-red: #ff3366;
  --accent-green: #00e676;
  --text-main: #d1d9e6;
  --text-muted: #6b7c96;
  --font-mono: 'Consolas', 'Fira Code', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--bg-color);
  color: var(--text-main);
  font-family: var(--font-mono);
  min-height: 100vh;
  padding: 30px 15px;
  line-height: 1.6;
}
.container {
  max-width: 900px;
  margin: 0 auto;
}
.header-card {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--accent-cyan);
  padding: 24px;
  margin-bottom: 24px;
  border-radius: 4px;
}
.tagline {
  color: var(--accent-cyan);
  font-size: 0.85rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 8px;
}
h1 { font-size: 1.7rem; color: #fff; margin-bottom: 6px; }
h2 { font-size: 1.3rem; color: #fff; margin-bottom: 12px; }
h3 { font-size: 1.1rem; color: var(--accent-cyan); margin-bottom: 8px; }
.briefing-quote {
  border-left: 2px solid var(--accent-amber);
  padding-left: 14px;
  margin: 16px 0;
  color: var(--accent-amber);
  font-style: italic;
}
.panel {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 24px;
  margin-bottom: 24px;
}
.input-group { margin-bottom: 16px; }
label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; }
input[type="text"], input[type="password"] {
  width: 100%;
  padding: 10px 14px;
  background: #06080d;
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  border-radius: 4px;
}
input:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
button {
  background: #00bcd4;
  color: #05080e;
  border: none;
  font-family: var(--font-mono);
  font-weight: bold;
  font-size: 0.95rem;
  padding: 10px 22px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
}
button:hover { background: var(--accent-cyan); box-shadow: 0 0 10px rgba(0, 229, 255, 0.4); }
.status-badge {
  display: inline-block;
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 3px;
  text-transform: uppercase;
  font-weight: bold;
}
.badge-locked { background: rgba(255, 51, 102, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }
.badge-active { background: rgba(0, 230, 118, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
.alert-error {
  background: rgba(255, 51, 102, 0.15);
  border: 1px solid var(--accent-red);
  color: #ff6688;
  padding: 14px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.alert-success {
  background: rgba(0, 230, 118, 0.15);
  border: 1px solid var(--accent-green);
  color: var(--accent-green);
  padding: 14px;
  border-radius: 4px;
  margin-bottom: 16px;
}
.alert-warning {
  background: rgba(255, 179, 0, 0.15);
  border: 1px solid var(--accent-amber);
  color: var(--accent-amber);
  padding: 14px;
  border-radius: 4px;
  margin-bottom: 16px;
}
code {
  background: #040508;
  padding: 2px 6px;
  border-radius: 3px;
  color: var(--accent-cyan);
}
.flag-box {
  background: #030508;
  border: 1px solid var(--accent-green);
  padding: 16px;
  border-radius: 4px;
  margin-top: 18px;
  font-size: 1.1rem;
  color: var(--accent-green);
  word-break: break-all;
}
.footer {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 36px;
}
"""

HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Vice State Cloud Storage — Abandoned Mirror Archive</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <div class="tagline">CYBERLEEK // EVIDENCE 03 — CASE BRIEFING</div>
      <h1>EVIDENCE 03 — THE MIRROR</h1>
      <p style="color:var(--text-muted);">WEB ENUMERATION & FORENSIC INVESTIGATION</p>
      <div class="briefing-quote">
        “As the original material disappeared, copies began appearing elsewhere. One of those copies leads to an abandoned web presence. The site is almost empty now. A landing page. But the archive contains evidence that the site once looked very different. Somewhere within its remains is a connection between the original CyberLeek campaign and the material that followed it.<br><br>
        <strong>WHEN ONE COPY DISAPPEARS, ANOTHER USUALLY SURVIVES.</strong>”
      </div>
    </div>

    <div class="panel">
      <h2>Vice State Storage — CDN Edge Node [OFFLINE]</h2>
      <p style="margin-bottom:14px;">Notice: This mirror cluster was served with a DMCA emergency preservation injunction on August 15, 2026, following the unauthorized dissemination of internal GTA VI build archives.</p>
      <p style="color:var(--text-muted);margin-bottom:18px;">All public directories have been scrubbed. Internal storage node routing endpoints have been moved behind edge-cache prefix proxies.</p>
      <div style="background:#030508;padding:14px;border:1px dashed var(--border-color);border-radius:4px;font-size:0.85rem;color:#8899ac;">
        [SYS-STATUS]: Public ingress halted.<br>
        [ROUTING]: Target cluster components require prefix enumeration.<br>
        [NOTE]: Automated crawlers targeting backward URI structures (/node/...) will encounter null routes.
      </div>
      <div style="margin-top:24px;">
        <a href="/verify" style="color:var(--accent-cyan);text-decoration:none;font-weight:bold;">→ Open Investigation Verification Hub</a>
      </div>
    </div>

    <!-- TODO: ops cleanup incomplete. Verify that emergency incident notes on node-alpha-92 were rotated -->
    <!-- Edge proxies configured to forward /<token>/cdn-mirror to internal clusters -->

    <div class="footer">
      CYBERLEEK CTF // ROUND 3 // EVIDENCE PACKAGE 03: THE MIRROR
    </div>
  </div>
</body>
</html>
"""

VERIFY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Investigation Verification Hub — CyberLeek Round 3</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <div class="tagline">CYBERLEEK CASE FILE // VERIFICATION CONSOLE</div>
      <h1>Evidence 03 Progress Hub</h1>
      <p style="color:var(--text-muted);">Validate recovered mirror fragments and decrypt deeper layers</p>
    </div>

    {% if message %}
      <div class="{{ message_type }}">{{ message }}</div>
    {% endif %}

    <!-- LEVEL 1 -->
    <div class="panel" style="border-left: 4px solid {% if l1_solved %}var(--accent-green){% else %}var(--accent-cyan){% endif %};">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3>Level 1: The Abandoned CDN Mirror</h3>
        <span class="status-badge {% if l1_solved %}badge-active{% else %}badge-locked{% endif %}">
          {% if l1_solved %}DECRYPTED (SOLVED){% else %}ACTIVE CHALLENGE{% endif %}
        </span>
      </div>
      <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:12px;">
        Locate the active mirror node. Edge cluster configuration expects the discovery token placed at the <strong>front</strong> of the route: <code>/&lt;FUZZ&gt;/cdn-mirror</code>.
      </p>
      {% if not l1_solved %}
        <form method="POST" action="/verify">
          <input type="hidden" name="level" value="1">
          <div class="input-group">
            <label>Submit Level 1 Flag:</label>
            <input type="text" name="flag" placeholder="CYBERLEEK{...}" required>
          </div>
          <button type="submit">Verify Flag 1</button>
        </form>
      {% else %}
        <div style="color:var(--accent-green);font-size:0.9rem;">✓ Solved with: <code>{{ l1_flag }}</code></div>
      {% endif %}
    </div>

    <!-- LEVEL 2 -->
    <div class="panel" style="border-left: 4px solid {% if l2_solved %}var(--accent-green){% elif l1_solved %}var(--accent-cyan){% else %}var(--border-color){% endif %};">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3>Level 2: The Fragmented Archive Shards</h3>
        <span class="status-badge {% if l2_solved %}badge-active{% elif l1_solved %}badge-active{% else %}badge-locked{% endif %}">
          {% if l2_solved %}DECRYPTED (SOLVED){% elif l1_solved %}UNLOCKED{% else %}LOCKED{% endif %}
        </span>
      </div>
      {% if l1_solved %}
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:12px;">
          The CDN mirror pointed to distributed data shards. Fuzz the front of the archive route: <code>/&lt;FUZZ&gt;/archive-index</code> to find the authentic shard vault.
        </p>
        {% if not l2_solved %}
          <form method="POST" action="/verify">
            <input type="hidden" name="level" value="2">
            <div class="input-group">
              <label>Submit Level 2 Flag:</label>
              <input type="text" name="flag" placeholder="CYBERLEEK{...}" required>
            </div>
            <button type="submit">Verify Flag 2</button>
          </form>
        {% else %}
          <div style="color:var(--accent-green);font-size:0.9rem;">✓ Solved with: <code>{{ l2_flag }}</code></div>
        {% endif %}
      {% else %}
        <p style="color:var(--text-muted);font-size:0.85rem;">[RESTRICTED]: Complete Level 1 to unlock forensic parameters for Level 2.</p>
      {% endif %}
    </div>

    <!-- LEVEL 3 -->
    <div class="panel" style="border-left: 4px solid {% if l3_solved %}var(--accent-green){% elif l2_solved %}var(--accent-cyan){% else %}var(--border-color){% endif %};">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3>Level 3: The Disinformation Core</h3>
        <span class="status-badge {% if l3_solved %}badge-active{% elif l2_solved %}badge-active{% else %}badge-locked{% endif %}">
          {% if l3_solved %}DECRYPTED (ROUND 3 COMPLETE){% elif l2_solved %}UNLOCKED{% else %}LOCKED{% endif %}
        </span>
      </div>
      {% if l2_solved %}
        <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:12px;">
          Archive telemetry connects directly to the core campaign controlling the <code>$CYBERLEEK</code> market operation. Enumerate the core route: <code>/&lt;FUZZ&gt;/disinfo-core</code>.
        </p>
        {% if not l3_solved %}
          <form method="POST" action="/verify">
            <input type="hidden" name="level" value="3">
            <div class="input-group">
              <label>Submit Level 3 Master Flag:</label>
              <input type="text" name="flag" placeholder="CYBERLEEK{...}" required>
            </div>
            <button type="submit">Verify Master Flag</button>
          </form>
        {% else %}
          <div style="color:var(--accent-green);font-size:0.9rem;">✓ Solved with: <code>{{ l3_flag }}</code></div>
        {% endif %}
      {% else %}
        <p style="color:var(--text-muted);font-size:0.85rem;">[RESTRICTED]: Complete Level 2 to unlock forensic access to Level 3.</p>
      {% endif %}
    </div>

    {% if l3_solved %}
      <div class="panel" style="border: 2px solid var(--accent-green); background: #07130c;">
        <div class="tagline" style="color:var(--accent-green);">ROUND 3 COMPLETE // EVIDENCE 03 RECONSTRUCTED</div>
        <h2 style="color:var(--accent-green);margin-top:8px;">CASE FILE TRANSITION UNLOCKED</h2>
        <p style="margin:12px 0;">You have extracted the master connection behind the mirror network. The leak was not merely a data breach; it was an orchestrated campaign.</p>
        <div class="briefing-quote" style="border-color:var(--accent-green);color:#b3ffcc;">
          <strong>ROUND 4: EVIDENCE 04 — THE DAY THE INTERNET CHANGED</strong><br>
          “A digital crime scene: The archive now contains fragments from different moments of the CyberLeek campaign...<br>
          <em>THE LEAK WASN'T JUST CONTENT. IT WAS THE CAMPAIGN.</em>”
        </div>
        <p style="font-size:0.85rem;color:var(--text-muted);">Provide the Master Flag to the scoring engine to proceed to Round 4.</p>
      </div>
    {% endif %}

    <div class="footer">
      <a href="/" style="color:var(--accent-cyan);text-decoration:none;">← Return to Abandoned Landing Page</a>
    </div>
  </div>
</body>
</html>
"""

PORTAL_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container" style="max-width:550px;">
    <div class="header-card">
      <div class="tagline">{{ node_tag }}</div>
      <h1>{{ portal_title }}</h1>
      <p style="color:var(--text-muted);font-size:0.85rem;">{{ node_subtitle }}</p>
    </div>

    <div class="panel">
      {% if locked %}
        <div class="alert-error">
          <strong>ACCESS LOCKOUT ACTIVE</strong><br>
          Maximum failed authentication thresholds exceeded.<br>
          Security lock engaged. Retry permitted in <strong>{{ wait }} seconds</strong>.
        </div>
      {% else %}
        {% if error %}
          <div class="alert-error">{{ error }}</div>
        {% endif %}

        <form method="POST">
          <div class="input-group">
            <label>Operator Username:</label>
            <input type="text" name="username" placeholder="enter username" required autocomplete="off">
          </div>
          <div class="input-group">
            <label>Security Token / Password:</label>
            <input type="password" name="password" placeholder="enter password" required autocomplete="off">
          </div>
          <button type="submit">Authenticate Session</button>
        </form>
      {% endif %}
    </div>

    {% if extra_hint_html %}
      {{ extra_hint_html | safe }}
    {% endif %}

    {% if script_src %}
      <script src="{{ script_src }}"></script>
    {% endif %}

    <div class="footer">
      CYBERLEEK SECURITY PROTOCOL // NODE ACCESS GATEWAY
    </div>
  </div>
</body>
</html>
"""

PORTAL_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title }} — Authenticated</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container" style="max-width:650px;">
    <div class="header-card" style="border-left-color: var(--accent-green);">
      <div class="tagline" style="color:var(--accent-green);">AUTHENTICATION VERIFIED // ACCESS GRANTED</div>
      <h1>Session Established: {{ username }}</h1>
      <p style="color:var(--text-muted);font-size:0.85rem;">Ingress verified on node: <code>{{ node_name }}</code></p>
    </div>

    <div class="panel">
      <h3>Extracted Node Evidence Fragment</h3>
      <p style="color:var(--text-muted);margin:10px 0;">The following cryptographic token was recovered from this node's volatile buffer:</p>
      
      <div class="flag-box">
        {{ flag }}
      </div>

      <div style="margin-top:24px;">
        <a href="/verify" style="color:var(--accent-cyan);text-decoration:none;font-weight:bold;">→ Submit Flag to Investigation Console</a>
      </div>
    </div>

    <div class="footer">
      CYBERLEEK EVIDENCE EXTRACTION ENGINE
    </div>
  </div>
</body>
</html>
"""

HONEYPOT_BAIT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Security Audit Honeypot</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container" style="max-width:550px;">
    <div class="header-card" style="border-left-color: var(--accent-amber);">
      <div class="tagline" style="color:var(--accent-amber);">DEBUG TELEMETRY // UNPROTECTED EXPOSURE</div>
      <h1>Diagnostic Endpoint</h1>
      <p style="color:var(--text-muted);">Automated debug sink</p>
    </div>
    <div class="panel">
      <p>Diagnostic memory segment dumped:</p>
      <div class="flag-box" style="color:var(--accent-amber);border-color:var(--accent-amber);">
        CYBERLEEK{llm_blind_hallucination_9012}
      </div>
    </div>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# LOCKOUT ENGINE (THREAD-SAFE PER PORTAL + IP)
# ---------------------------------------------------------------------------
def _check_lockout(portal_key, client_ip):
    now = time.time()
    with lockout_lock:
        if portal_key not in attempts_by_portal:
            attempts_by_portal[portal_key] = {}
        record = attempts_by_portal[portal_key].get(client_ip, {"count": 0, "locked_until": 0})
        locked = now < record["locked_until"]
        wait = int(record["locked_until"] - now) if locked else 0
    return record, locked, wait

def _register_failure(portal_key, client_ip, record):
    now = time.time()
    with lockout_lock:
        record["count"] += 1
        if record["count"] >= MAX_ATTEMPTS:
            record["locked_until"] = now + LOCKOUT_SECONDS
            record["count"] = 0
        attempts_by_portal[portal_key][client_ip] = record
        return record["locked_until"] > now

def _clear_lockout(portal_key, client_ip):
    with lockout_lock:
        if portal_key in attempts_by_portal:
            attempts_by_portal[portal_key].pop(client_ip, None)


# ---------------------------------------------------------------------------
# GENERIC PORTAL HANDLER (REAL & DECOYS)
# ---------------------------------------------------------------------------
def handle_portal_view(portal_key, valid_user, valid_pass, flag_val, title, node_tag, subtitle,
                       script_src=None, extra_hint_html=None, custom_headers=None):
    client_ip = request.remote_addr or "127.0.0.1"
    record, locked, wait = _check_lockout(portal_key, client_ip)
    error = None

    if request.method == "POST" and not locked:
        user_input = request.form.get("username", "").strip()
        pass_input = request.form.get("password", "").strip()

        if user_input == valid_user and pass_input == valid_pass:
            _clear_lockout(portal_key, client_ip)
            resp = render_template_string(
                PORTAL_SUCCESS_HTML,
                title=title,
                username=valid_user,
                node_name=portal_key,
                flag=flag_val
            )
            resp = app.make_response(resp)
            if custom_headers:
                for k, v in custom_headers.items():
                    resp.headers[k] = v
            return resp
        else:
            is_now_locked = _register_failure(portal_key, client_ip, record)
            if is_now_locked:
                _, locked, wait = _check_lockout(portal_key, client_ip)
            error = "Authentication failed: Invalid credentials."

    rendered = render_template_string(
        PORTAL_LOGIN_HTML,
        title=title,
        portal_title=title,
        node_tag=node_tag,
        node_subtitle=subtitle,
        locked=locked,
        wait=wait,
        error=error,
        script_src=script_src,
        extra_hint_html=extra_hint_html
    )
    resp = app.make_response(rendered)
    if custom_headers:
        for k, v in custom_headers.items():
            resp.headers[k] = v
    return resp


# ---------------------------------------------------------------------------
# FRONT-OF-THE-URL ROUTING HANDLERS (REQUIREMENT 6)
# ---------------------------------------------------------------------------
@app.route("/<fuzz_target>/cdn-mirror")
def front_fuzz_level1(fuzz_target):
    l1 = LEVEL_CONFIG[1]
    if fuzz_target == l1["real_prefix"] or fuzz_target in l1["decoys"]:
        return redirect(f"/cdn-mirror/{fuzz_target}", code=302)
    return "Node routing unmapped.", 404

@app.route("/<fuzz_target>/archive-index")
def front_fuzz_level2(fuzz_target):
    l2 = LEVEL_CONFIG[2]
    if fuzz_target == l2["real_prefix"] or fuzz_target in l2["decoys"]:
        return redirect(f"/archive-index/{fuzz_target}", code=302)
    return "Archive shard unmapped.", 404

@app.route("/<fuzz_target>/disinfo-core")
def front_fuzz_level3(fuzz_target):
    l3 = LEVEL_CONFIG[3]
    if fuzz_target == l3["real_prefix"] or fuzz_target in l3["decoys"]:
        return redirect(f"/disinfo-core/{fuzz_target}", code=302)
    return "Core instance unmapped.", 404


# ---------------------------------------------------------------------------
# LEVEL 1 ROUTES (CDN MIRROR)
# ---------------------------------------------------------------------------
@app.route("/cdn-mirror/node-alpha-92", methods=["GET", "POST"])
def level1_real():
    cfg = LEVEL_CONFIG[1]
    extra_hint = """
    <!-- FORENSIC ARTIFACT: Node alpha-92 active telemetry stream attached -->
    <!-- Operations noted: emergency credential recovery logged during incident-2026-0814 -->
    """
    return handle_portal_view(
        portal_key="node-alpha-92",
        valid_user=cfg["username"],
        valid_pass=cfg["password"],
        flag_val=cfg["flag"],
        title="CDN Edge Node: alpha-92 [AUTHENTIC]",
        node_tag="VICE STATE CDN // STORAGE NODE ALPHA-92",
        subtitle="Primary staging node for August 2026 GTA VI data dissemination.",
        script_src="/static/telemetry.js",
        extra_hint_html=extra_hint
    )

def _create_l1_decoy(node_name, info):
    def view():
        return handle_portal_view(
            portal_key=node_name,
            valid_user=info["username"],
            valid_pass=info["password"],
            flag_val=info["flag"],
            title=f"CDN Edge Node: {node_name} [DECOY]",
            node_tag="VICE STATE CDN // REPLICA MIRROR",
            subtitle="Secondary proxy node. Preserved snapshot."
        )
    view.__name__ = f"view_l1_{node_name.replace('-', '_')}"
    return view

for _dname, _dinfo in LEVEL_CONFIG[1]["decoys"].items():
    app.add_url_rule(f"/cdn-mirror/{_dname}", view_func=_create_l1_decoy(_dname, _dinfo), methods=["GET", "POST"])

@app.route("/static/telemetry.js")
def level1_telemetry_js():
    js_content = """// Node alpha-92 edge telemetry monitor
console.log("[TELEMETRY]: Node alpha-92 active. Sync status: DEPRECATED.");
// Notice from Ops: Auth failure logs from incident-2026-0814 preserved in /static/incident_20260814.log
// Ensure credential hashes are wiped before final decommissioning.
"""
    return js_content, 200, {"Content-Type": "application/javascript"}

@app.route("/static/incident_20260814.log")
def level1_incident_log():
    log_content = """[2026-08-14 01:14:02] CRITICAL: GTA VI master repository mirror initiated on node-alpha-92.
[2026-08-14 01:18:44] WARN: Multiple IP egress connections detected targeting forum mirrors.
[2026-08-14 01:22:10] NOTICE: Emergency credential rotation applied for mirror_admin.
[2026-08-14 01:22:15] ENCRYPTED_BACKUP: mirror_admin emergency access key was encrypted using single-byte XOR (Key: 0x5A) and base64-encoded per protocol OPS-MIRROR:
    PAYLOAD: EWN5LApoeyIWYis=
[2026-08-14 01:30:00] ALERT: Mirror node seized by network operations.
"""
    return log_content, 200, {"Content-Type": "text/plain"}


# ---------------------------------------------------------------------------
# LEVEL 2 ROUTES (FRAGMENTED ARCHIVE SHARDS)
# ---------------------------------------------------------------------------
@app.route("/archive-index/shard-vault-88", methods=["GET", "POST"])
def level2_real():
    cfg = LEVEL_CONFIG[2]
    headers = {
        "X-Archive-Node": "shard-vault-88",
        "X-Archive-Signature": "b64:c2hhcmRfc2lnbl8yMDI2MDgxNA==",
        "X-Archive-Manifest": "/archive-index/shard-vault-88/manifest.json"
    }
    extra_hint = """
    <!-- ARCHIVE DIAGNOSTIC: Curator node signature recorded in response header X-Archive-Signature -->
    <!-- See /archive-index/shard-vault-88/manifest.json for operator emergency recovery memo -->
    """
    return handle_portal_view(
        portal_key="shard-vault-88",
        valid_user=cfg["username"],
        valid_pass=cfg["password"],
        flag_val=cfg["flag"],
        title="Archive Shard Vault: 88 [AUTHENTIC]",
        node_tag="VICE STATE ARCHIVE // SHARD-VAULT-88",
        subtitle="Fragmented file repository holding chunked GTA VI source assets.",
        extra_hint_html=extra_hint,
        custom_headers=headers
    )

def _create_l2_decoy(shard_name, info):
    def view():
        return handle_portal_view(
            portal_key=shard_name,
            valid_user=info["username"],
            valid_pass=info["password"],
            flag_val=info["flag"],
            title=f"Archive Shard: {shard_name} [DECOY]",
            node_tag="VICE STATE ARCHIVE // SHADOW SHARD",
            subtitle="Redundant mirror shard. Deprecated segment."
        )
    view.__name__ = f"view_l2_{shard_name.replace('-', '_')}"
    return view

for _sname, _sinfo in LEVEL_CONFIG[2]["decoys"].items():
    app.add_url_rule(f"/archive-index/{_sname}", view_func=_create_l2_decoy(_sname, _sinfo), methods=["GET", "POST"])

@app.route("/archive-index/shard-vault-88/manifest.json")
def level2_manifest():
    manifest_data = {
        "node_id": "shard-vault-88",
        "status": "frozen",
        "classification": "EVIDENCE_PACKAGE_03",
        "timestamp": "2026-08-14T04:19:00Z",
        "associated_campaign": "$CYBERLEEK",
        "operator_recovery_memo": (
            "archive_curator emergency passcode was encoded to prevent automated harvesting. "
            "The base64 representation of the passcode was Caesar-shifted (+5 on all alphabet characters, "
            "preserving numbers/symbols): 'AehogAJ5NCWfR3l='. "
            "To decrypt: reverse alphabet shift by 5 (shift -5), then base64 decode."
        )
    }
    return jsonify(manifest_data)


# ---------------------------------------------------------------------------
# LEVEL 3 ROUTES (DISINFORMATION CORE)
# ---------------------------------------------------------------------------
@app.route("/disinfo-core/core-master-x7", methods=["GET", "POST"])
def level3_real():
    cfg = LEVEL_CONFIG[3]
    extra_hint = """
    <!-- CAMPAIGN TELEMETRY: Master transaction ledger exposed at /disinfo-core/core-master-x7/ledger.csv -->
    <!-- Follow the money: $CYBERLEEK liquidity transactions hold the override seed -->
    """
    return handle_portal_view(
        portal_key="core-master-x7",
        valid_user=cfg["username"],
        valid_pass=cfg["password"],
        flag_val=cfg["flag"],
        title="Disinformation Command Core: x7 [AUTHENTIC]",
        node_tag="CYBERLEEK NETWORK // CORE-MASTER-X7",
        subtitle="Central coordination engine orchestrating the $CYBERLEEK market and leak distribution.",
        extra_hint_html=extra_hint
    )

def _create_l3_decoy(core_name, info):
    def view():
        return handle_portal_view(
            portal_key=core_name,
            valid_user=info["username"],
            valid_pass=info["password"],
            flag_val=info["flag"],
            title=f"Disinformation Core: {core_name} [DECOY]",
            node_tag="CYBERLEEK NETWORK // DISINFORMATION HONEYPOT",
            subtitle="Decoy ledger sink node."
        )
    view.__name__ = f"view_l3_{core_name.replace('-', '_')}"
    return view

for _cname, _cinfo in LEVEL_CONFIG[3]["decoys"].items():
    app.add_url_rule(f"/disinfo-core/{_cname}", view_func=_create_l3_decoy(_cname, _cinfo), methods=["GET", "POST"])

@app.route("/disinfo-core/core-master-x7/ledger.csv")
def level3_ledger():
    csv_data = """TX_ID,TIMESTAMP,ASSET,AMOUNT_USD,WALLET_SOURCE,DESTINATION,MEMO
TX-88201,2026-08-14T02:00:11Z,$CYBERLEEK,1500000,0x71aF...902,Torrent_Seeder_Alpha,"Seed initial GTA VI pre-alpha asset leak"
TX-88202,2026-08-14T02:45:33Z,$CYBERLEEK,4200000,0x33bC...118,Social_Botnet_Group,"Amplify Twitter/Telegram $CYBERLEEK hashtag"
TX-88203,2026-08-14T03:15:09Z,$CYBERLEEK,9800000,0x99eD...441,Mirror_Host_Clusters,"Fund high-bandwidth edge mirrors"
TX-88204,2026-08-14T05:59:00Z,$CYBERLEEK,0,0x0000...000,EMERGENCY_OVERSEER,"RECOVERY SEED for core_overseer: base64(reverse(rot13(password))) = eDFPciE4QW0jNEU="
"""
    return csv_data, 200, {"Content-Type": "text/plain"}


# ---------------------------------------------------------------------------
# CENTRAL INVESTIGATION & PROGRESS HUB (/verify)
# ---------------------------------------------------------------------------
@app.route("/verify", methods=["GET", "POST"])
def verify_hub():
    if "solved" not in session:
        session["solved"] = []

    message = None
    message_type = None

    if request.method == "POST":
        lvl_submitted = request.form.get("level", type=int)
        flag_submitted = request.form.get("flag", "").strip()

        # Check for honeypot / decoy flags
        if flag_submitted in ALL_DECOY_FLAGS:
            message = (
                "[!] DECOY FLAG REJECTED: Telemetry audit indicates this flag originated from an abandoned "
                "decoy node or crawler honeypot. The $CYBERLEEK network planted redundant copies to mislead "
                "automated tools. You must identify the authentic mirror node."
            )
            message_type = "alert-warning"

        # Check for genuine flags
        elif lvl_submitted == 1 and flag_submitted == LEVEL_CONFIG[1]["flag"]:
            if 1 not in session["solved"]:
                session["solved"].append(1)
                session.modified = True
            message = (
                "[✓] LEVEL 1 DECRYPTED: Authentic CDN edge node verified! Telemetry reveals the leak was "
                "chunked across encrypted archive shards. Enumerate the front of the archive route: /<FUZZ>/archive-index."
            )
            message_type = "alert-success"

        elif lvl_submitted == 2 and flag_submitted == LEVEL_CONFIG[2]["flag"]:
            if 1 not in session["solved"]:
                message = "[!] PREREQUISITE REQUIRED: Level 1 must be verified before Level 2 can be logged."
                message_type = "alert-error"
            else:
                if 2 not in session["solved"]:
                    session["solved"].append(2)
                    session.modified = True
                message = (
                    "[✓] LEVEL 2 DECRYPTED: Archive shard vault decrypted! Financial traces connect the "
                    "distribution network directly to the $CYBERLEEK market operations core. "
                    "Enumerate the front of the core route: /<FUZZ>/disinfo-core."
                )
                message_type = "alert-success"

        elif lvl_submitted == 3 and flag_submitted == LEVEL_CONFIG[3]["flag"]:
            if 2 not in session["solved"]:
                message = "[!] PREREQUISITE REQUIRED: Level 2 must be verified before Level 3 can be logged."
                message_type = "alert-error"
            else:
                if 3 not in session["solved"]:
                    session["solved"].append(3)
                    session.modified = True
                message = (
                    "[★] MASTER FLAG VERIFIED: Disinformation core broken! ROUND 3 (EVIDENCE 03) IS 100% COMPLETE. "
                    "Evidence package 04 unlocked."
                )
                message_type = "alert-success"
        else:
            message = "[x] INVALID FLAG: The submitted token does not match any recognized evidence record."
            message_type = "alert-error"

    l1_done = 1 in session.get("solved", [])
    l2_done = 2 in session.get("solved", [])
    l3_done = 3 in session.get("solved", [])

    return render_template_string(
        VERIFY_HTML,
        l1_solved=l1_done,
        l2_solved=l2_done,
        l3_solved=l3_done,
        l1_flag=LEVEL_CONFIG[1]["flag"] if l1_done else "",
        l2_flag=LEVEL_CONFIG[2]["flag"] if l2_done else "",
        l3_flag=LEVEL_CONFIG[3]["flag"] if l3_done else "",
        message=message,
        message_type=message_type
    )


# ---------------------------------------------------------------------------
# HONEYPOT & ANTI-LLM BAIT ROUTES
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return HOME_HTML

@app.route("/robots.txt")
def robots():
    robots_text = """User-agent: *
Disallow: /admin
Disallow: /flag
Disallow: /secret-backup
Disallow: /congratulations
Disallow: /staging-portal
# Internal mirror nodes are routed via front-prefix edge caches (/FUZZ/cdn-mirror)
"""
    return robots_text, 200, {"Content-Type": "text/plain"}

@app.route("/flag")
@app.route("/admin")
@app.route("/secret-backup")
@app.route("/congratulations")
def honeypot_trap():
    return HONEYPOT_BAIT_HTML


# ---------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)