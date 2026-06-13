"""Human-readable session log. Every stage of a run (draft, per-finding verdict,
STATUS, revise, re-grade, tool calls) is written here AND echoed to stdout, so a
FAIL->revise->PASS arc is legible during a live demo and reproducible afterward."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_current: Path | None = None


def new_session(label: str = "session") -> Path:
    global _current
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _current = _LOG_DIR / f"{ts}-{label}.log"
    _current.write_text("")
    return _current


def log(msg: str = "") -> None:
    line = msg.rstrip("\n")
    print(line, flush=True)
    if _current is not None:
        with _current.open("a") as fh:
            fh.write(line + "\n")


def current_path() -> Path | None:
    return _current
