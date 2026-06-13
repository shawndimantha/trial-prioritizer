"""SEAM 1 — the model-agnostic call site.

Every model call in the harness goes through here, keyed by *role* rather than a
hardcoded model string. Swapping a model later (e.g. pointing the verifier at a
longer-horizon model) is a one-line edit to ROLE_MODELS — no refactor. This is
the "capability dial" made real rather than a slide (see CLAUDE.md).
"""

from __future__ import annotations

import anthropic
from dotenv import load_dotenv

# Load ANTHROPIC_API_KEY (and anything else) from a local .env if present.
# .env is gitignored — keep secrets there, never in source.
load_dotenv()

# role -> model. Flip a value here to change which model plays a role.
ROLE_MODELS: dict[str, str] = {
    "builder": "claude-opus-4-8",
    "verifier": "claude-opus-4-8",
    "planner": "claude-opus-4-8",
}

MAX_TOKENS = 16000  # non-streaming ceiling that stays under SDK HTTP timeouts

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    """Lazy singleton. Resolves ANTHROPIC_API_KEY from the environment."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _text(content) -> str:
    return "".join(b.text for b in content if getattr(b, "type", None) == "text")


def run_tool_loop(role, system, user, tools, dispatch_fn, max_turns=12, on_event=None):
    """Manual agentic loop. Runs the model with `tools` until it stops calling
    them, dispatching client-side tools via `dispatch_fn`. Server-side tools
    (web_search / web_fetch) resolve on Anthropic's side and surface as
    `pause_turn`, which we continue past by re-sending.

    Returns (final_text, messages). `messages` is the full transcript — useful
    for inspecting that the verifier saw no builder context (an invariant).
    """
    msgs = [{"role": "user", "content": user}]
    resp = None
    for _ in range(max_turns):
        resp = client().messages.create(
            model=ROLE_MODELS[role],
            max_tokens=MAX_TOKENS,
            system=system,
            messages=msgs,
            tools=tools,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        )
        msgs.append({"role": "assistant", "content": resp.content})
        if on_event:
            on_event(role, resp)

        if resp.stop_reason == "tool_use":
            results = []
            for b in resp.content:
                if getattr(b, "type", None) == "tool_use":
                    out = dispatch_fn(b.name, b.input)
                    results.append(
                        {"type": "tool_result", "tool_use_id": b.id, "content": out}
                    )
            msgs.append({"role": "user", "content": results})
            continue

        if resp.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration cap; re-send to resume.
            continue

        break

    return (_text(resp.content) if resp else ""), msgs


def parse_model(role, system, user, schema):
    """One-shot structured output. No tools — used to convert an evidence
    dossier into a validated Pydantic object."""
    resp = client().messages.parse(
        model=ROLE_MODELS[role],
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
        thinking={"type": "adaptive"},
    )
    return resp.parsed_output
