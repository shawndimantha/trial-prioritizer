"""Grounding layer (G1). A custom ClinicalTrials.gov v2 tool for structured trial
data, plus Anthropic server-side web_search / web_fetch for FDA posture and
published trial results. The same tool list is handed to BOTH builder and
verifier — live retrieval is what makes the verifier meaningful (CLAUDE.md)."""

from __future__ import annotations

import json

import httpx

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Custom client-side tool.
CTGOV_TOOL = {
    "name": "clinicaltrials_lookup",
    "description": (
        "Look up REAL ClinicalTrials.gov records via the official v2 API. "
        "Pass `nct_id` to fetch one study (planned vs actual enrollment, status, "
        "phase, why-stopped, primary outcomes, and results when posted), or pass "
        "`query`/`condition` to search comparable trials. Use this to ground any "
        "claim about trial enrollment, design, status, or outcomes — never recall "
        "NCT IDs or numbers from memory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nct_id": {"type": "string", "description": "e.g. NCT03068468"},
            "query": {"type": "string", "description": "free-text terms, e.g. 'tau antibody'"},
            "condition": {
                "type": "string",
                "description": "condition filter; defaults to Progressive Supranuclear Palsy",
            },
        },
        "required": [],
    },
}

# Anthropic server-side tools (run on Anthropic's side; no client dispatch).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}
WEB_FETCH_TOOL = {"type": "web_fetch_20260209", "name": "web_fetch"}

TOOLS = [CTGOV_TOOL, WEB_SEARCH_TOOL, WEB_FETCH_TOOL]


def _summarize(study: dict, full: bool = False) -> dict:
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    design = ps.get("designModule", {})
    enr = design.get("enrollmentInfo", {})
    cond = ps.get("conditionsModule", {})
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})

    summary = {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "overall_status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "phase": design.get("phases"),
        "enrollment_count": enr.get("count"),
        "enrollment_type": enr.get("type"),  # ACTUAL vs ESTIMATED
        "conditions": cond.get("conditions"),
        "interventions": [
            {"type": i.get("type"), "name": i.get("name")}
            for i in arms.get("interventions", [])
        ],
        "primary_outcomes": [
            {"measure": o.get("measure"), "timeFrame": o.get("timeFrame")}
            for o in outcomes.get("primaryOutcomes", [])
        ],
        "has_results": "resultsSection" in study,
    }

    if full and "resultsSection" in study:
        rs = study["resultsSection"]
        om = rs.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
        summary["results_outcome_measures"] = [
            {"title": m.get("title"), "type": m.get("type"), "description": m.get("description")}
            for m in om[:8]
        ]
    return summary


def search_studies(query: str | None = None,
                   condition: str | None = "Progressive Supranuclear Palsy",
                   page_size: int = 10) -> list[dict]:
    params: dict = {"pageSize": page_size, "countTotal": "true"}
    if condition:
        params["query.cond"] = condition
    if query:
        params["query.term"] = query
    r = httpx.get(CTGOV_BASE, params=params, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    return [_summarize(s) for s in data.get("studies", [])]


def get_study(nct_id: str) -> dict:
    r = httpx.get(f"{CTGOV_BASE}/{nct_id}", timeout=30.0)
    if r.status_code == 404:
        return {"error": f"No ClinicalTrials.gov record found for {nct_id}"}
    r.raise_for_status()
    return _summarize(r.json(), full=True)


def dispatch_tool(name: str, tool_input: dict) -> str:
    """Execute a client-side tool call. Server-side web tools never reach here."""
    if name == "clinicaltrials_lookup":
        try:
            if tool_input.get("nct_id"):
                result = get_study(tool_input["nct_id"])
            else:
                result = {
                    "studies": search_studies(
                        query=tool_input.get("query"),
                        condition=tool_input.get("condition", "Progressive Supranuclear Palsy"),
                    )
                }
            return json.dumps(result)
        except Exception as exc:  # surface retrieval failure to the model, don't crash the loop
            return json.dumps({"error": f"clinicaltrials_lookup failed: {exc}"})
    return json.dumps({"error": f"unknown client-side tool: {name}"})
