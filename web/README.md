# web/ — Trial Pre-Mortem replay + deploy

Frontend-only. Owns the public page that **replays** a pre-mortem run (the
kill → revise → greenlight arc) as the engine produced it. It does **not** modify
the engine; it reads a persisted run JSON.

## Run locally

```bash
cd web
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PORT=8000 python app.py          # http://localhost:8000
```

Endpoints:
- `GET /`          — landing (Task A) / replay page (Task B)
- `GET /health`    — host readiness: `ANTHROPIC_API_KEY` present? CT.gov reachable?
- `GET /run.json`  — the run being replayed (newest `runs/*.json`, else `sample_run.json`)

## Deploy (Railway)

Build context is **this `web/` directory only** (keeps all frontend work isolated
from the engine, per branch rules). Deploy from inside `web/`:

```bash
cd web
railway login            # if not already authed
railway init             # once, to create/link a project+service
railway up               # build + deploy (uses Procfile)
railway domain           # mint / show the public URL
railway variables --set ANTHROPIC_API_KEY=sk-...   # set host env var
```

`Procfile` → `gunicorn app:app`. Railway/Nixpacks auto-detects Python from
`requirements.txt`.

## Data contract

`sample_run.json` is the fixture. Its inner `finding` / `verdict` objects match
the engine's pydantic shapes exactly (`premortem/schemas.py`). The outer envelope
(`timeline`, `greenlight`, `memory_appended`) wraps them for replay — see the
`note` field in the fixture for how a real engine `Result` maps in.
