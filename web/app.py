"""Trial Pre-Mortem — replay web app.

Owns ONLY the frontend/deploy. It does NOT import or run the engine here; it
replays a persisted run JSON the engine produced. (An optional live-run button
is wired in a later task and shells out to the engine; replay is the default.)

Task A scope: prove the deploy path is real before any UI —
  GET  /          minimal landing page
  GET  /health    JSON: is ANTHROPIC_API_KEY present in the host env, and is
                  ClinicalTrials.gov reachable from the host's egress?
  GET  /run.json  the run being replayed (fixture today; real run later)
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
# Replay source: a real persisted run if present, else the fixture.
RUNS_DIR = WEB_DIR / "runs"
FIXTURE = WEB_DIR / "sample_run.json"

# A live retrieval the engine actually performs — proves CT.gov egress works.
CTGOV_PROBE = (
    "https://clinicaltrials.gov/api/v2/studies/NCT03068468"
    "?fields=NCTId,BriefTitle,OverallStatus"
)

app = Flask(__name__, static_folder=None)


def _active_run_path() -> Path:
    """Newest persisted real run if one exists, otherwise the fixture."""
    if RUNS_DIR.is_dir():
        runs = sorted(RUNS_DIR.glob("*.json"))
        if runs:
            return runs[-1]
    return FIXTURE


@app.get("/health")
def health():
    """Surface NOW whether the host can do what a real run needs:
    an API key in env, and outbound reach to ClinicalTrials.gov."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    ctgov = {"reachable": False, "status": None, "ms": None, "sample": None, "error": None}
    started = time.monotonic()
    try:
        req = urllib.request.Request(CTGOV_PROBE, headers={"User-Agent": "premortem-healthcheck"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(2000).decode("utf-8", "replace")
            ctgov["status"] = resp.status
            ctgov["reachable"] = resp.status == 200
            try:
                ctgov["sample"] = json.loads(body).get("protocolSection", {}).get(
                    "identificationModule", {}
                ).get("nctId")
            except Exception:
                ctgov["sample"] = body[:120]
    except Exception as exc:  # noqa: BLE001 — we want to REPORT any egress failure
        ctgov["error"] = f"{type(exc).__name__}: {exc}"
    ctgov["ms"] = round((time.monotonic() - started) * 1000)

    run_path = _active_run_path()
    return jsonify(
        {
            "ok": bool(key) and ctgov["reachable"],
            "anthropic_key_present": bool(key),
            "anthropic_key_len": len(key),  # length only — never the secret
            "ctgov": ctgov,
            "active_run": run_path.name,
            "active_run_is_fixture": run_path == FIXTURE,
            "python": os.environ.get("PYTHON_VERSION", ""),
        }
    )


@app.get("/run.json")
def run_json():
    path = _active_run_path()
    return send_from_directory(path.parent, path.name, mimetype="application/json")


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=True)
