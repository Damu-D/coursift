"""
Cost observability — token spend attribution across projects.

Solves (2026 problem):
  "AI agents consume 5-30x more tokens per task; only 39% of orgs can attribute
  AI spend." The standard metric is shifting from cost-per-token to
  cost-per-task, and attribution must tie cost to specific conversations.

`coursift cost` parses the token-usage telemetry already in your Claude session
logs and rolls it up per project — so you can see where your spend actually goes.

100% local, no API. Prices are estimates (clearly labelled).
"""

import json
from collections import defaultdict

from coursift.sessions import CLAUDE_PROJECTS_DIR

# Approximate public list prices, USD per 1M tokens. ESTIMATES — adjust as needed.
PRICING = {
    "opus":   {"in": 15.0, "out": 75.0, "cache_read": 1.5,  "cache_write": 18.75},
    "sonnet": {"in": 3.0,  "out": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "haiku":  {"in": 1.0,  "out": 5.0,  "cache_read": 0.10, "cache_write": 1.25},
}


def _price_for(model: str) -> dict:
    m = (model or "").lower()
    if "opus" in m:
        return PRICING["opus"]
    if "haiku" in m:
        return PRICING["haiku"]
    return PRICING["sonnet"]  # default/fallback


def _cost_of(usage: dict, model: str) -> float:
    p = _price_for(model)
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    cr = usage.get("cache_read_input_tokens", 0)
    cw = usage.get("cache_creation_input_tokens", 0)
    return (
        inp * p["in"] + out * p["out"]
        + cr * p["cache_read"] + cw * p["cache_write"]
    ) / 1_000_000


def analyze_cost() -> dict:
    if not CLAUDE_PROJECTS_DIR.exists():
        return {"status": "no_sessions"}

    per_project = defaultdict(lambda: {
        "cost": 0.0, "input": 0, "output": 0, "cache_read": 0,
        "cache_write": 0, "messages": 0, "sessions": 0,
    })
    model_usage = defaultdict(float)

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        name = project_dir.name.split("-")[-1] or project_dir.name
        for session_file in project_dir.glob("*.jsonl"):
            per_project[name]["sessions"] += 1
            try:
                with session_file.open(encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = d.get("message", {})
                        if not isinstance(msg, dict):
                            continue
                        usage = msg.get("usage")
                        if not usage:
                            continue
                        model = msg.get("model", "")
                        c = _cost_of(usage, model)
                        agg = per_project[name]
                        agg["cost"] += c
                        agg["input"] += usage.get("input_tokens", 0)
                        agg["output"] += usage.get("output_tokens", 0)
                        agg["cache_read"] += usage.get("cache_read_input_tokens", 0)
                        agg["cache_write"] += usage.get("cache_creation_input_tokens", 0)
                        agg["messages"] += 1
                        model_usage[model] += c
            except Exception:
                continue

    total = sum(p["cost"] for p in per_project.values())
    return {
        "status": "ok",
        "total_cost": round(total, 2),
        "by_project": {
            k: {**v, "cost": round(v["cost"], 2)}
            for k, v in sorted(per_project.items(), key=lambda x: -x[1]["cost"])
        },
        "by_model": {k: round(v, 2) for k, v in sorted(model_usage.items(), key=lambda x: -x[1])},
        "note": "Estimates from public list prices; cache reads are heavily discounted.",
    }
