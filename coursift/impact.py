"""
Blast Radius / Change Impact analysis.

Solves (2026 problem):
  "AI agents start from zero and modify requested components without checking
  what depends on them — they don't know what depends on the code they're
  changing." Result: late-stage rollbacks and ripple-effect breakage.

`coursift impact <symbol>` walks the graph's reverse edges to show everything
that (transitively) depends on a symbol/file — BEFORE you change it. Coursift's
cross-project graph means the blast radius can span repositories.

100% local, no API.
"""

from collections import deque

from coursift.graph import load_graph


def _find_targets(nodes: list[dict], symbol: str) -> list[dict]:
    s = symbol.strip().lower()
    return [
        n for n in nodes
        if n.get("label", "").lower() == s
        and n.get("kind") in ("function", "class", "file")
    ]


def blast_radius(symbol: str, max_depth: int = 3) -> dict:
    """Compute transitive dependents (who breaks if `symbol` changes)."""
    graph = load_graph()
    if not graph:
        return {"status": "no_graph"}

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_by_id = {n["id"]: n for n in nodes}

    targets = _find_targets(nodes, symbol)
    if not targets:
        return {"status": "not_found", "symbol": symbol}

    # reverse adjacency: target -> [sources that depend on it]
    dependents: dict[str, list[str]] = {}
    for e in edges:
        # "A imports B", "A calls B", "A defines B" → A depends on B
        dependents.setdefault(e["target"], []).append(e["source"])

    impacted: dict[str, int] = {}   # node_id -> depth
    queue = deque((t["id"], 0) for t in targets)
    seen = {t["id"] for t in targets}

    while queue:
        nid, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for dep in dependents.get(nid, []):
            if dep not in seen:
                seen.add(dep)
                impacted[dep] = depth + 1
                queue.append((dep, depth + 1))

    # summarize
    impacted_nodes = [
        {**node_by_id[nid], "depth": d}
        for nid, d in impacted.items() if nid in node_by_id
    ]
    by_project: dict[str, int] = {}
    for n in impacted_nodes:
        by_project[n.get("project", "?")] = by_project.get(n.get("project", "?"), 0) + 1

    risk = "LOW"
    total = len(impacted_nodes)
    if total > 40 or len(by_project) > 1:
        risk = "HIGH"
    elif total > 10:
        risk = "MEDIUM"

    return {
        "status": "ok",
        "symbol": symbol,
        "targets": [{"project": t["project"], "file": t.get("file"), "kind": t["kind"]} for t in targets],
        "total_impacted": total,
        "by_project": by_project,
        "cross_project": len(by_project) > 1,
        "risk": risk,
        "top_impacted": sorted(
            impacted_nodes, key=lambda n: n["depth"]
        )[:15],
    }
