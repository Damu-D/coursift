"""Blast-radius analysis: transitive dependents of a symbol before you change it."""

from collections import deque

from coursift.graph import load_graph


def _find_targets(nodes: list[dict], symbol: str, scope: set[str] | None) -> list[dict]:
    from coursift.scope import in_scope
    s = symbol.strip().lower()
    return [
        n for n in nodes
        if n.get("label", "").lower() == s
        and n.get("kind") in ("function", "class", "file")
        and in_scope(n, scope)
    ]


def blast_radius(symbol: str, max_depth: int = 3, scope: set[str] | None = None) -> dict:
    """Compute transitive dependents (who breaks if `symbol` changes).

    `scope` limits which project's symbol is the target (None = all). Dependents
    are still followed across projects, since cross-project impact is meaningful.
    """
    graph = load_graph()
    if not graph:
        return {"status": "no_graph"}

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_by_id = {n["id"]: n for n in nodes}

    targets = _find_targets(nodes, symbol, scope)
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
