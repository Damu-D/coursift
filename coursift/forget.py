"""
Selective forgetting — the competency every 2026 memory system fails at.

Research finding: across long-context memory benchmarks, "most systems fail
conspicuously on selective forgetting." Uncontrolled memory accumulation drives
context rot and 65% of enterprise AI failures.

Coursift can prune stale memory by age, and decays the influence of old session
nodes so the graph stays sharp instead of bloating forever.

Local, no API.
"""

import time

from coursift.graph import load_graph, save_graph


def _parse_age(spec: str) -> float:
    """Parse '90d', '12h', '4w' into seconds."""
    spec = spec.strip().lower()
    units = {"d": 86400, "h": 3600, "w": 604800, "m": 2592000}
    unit = spec[-1]
    if unit not in units:
        raise ValueError("Use a suffix: d (days), h (hours), w (weeks), m (months)")
    return float(spec[:-1]) * units[unit]


def forget_older_than(spec: str) -> dict:
    """Remove session/concept memory nodes older than the given age."""
    graph = load_graph()
    if not graph:
        return {"status": "no_graph"}

    cutoff = time.time() - _parse_age(spec)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    kept_nodes = []
    removed_ids = set()
    for n in nodes:
        if n.get("kind") in ("session", "concept"):
            ts = n.get("timestamp")
            try:
                if ts and float(ts) < cutoff:
                    removed_ids.add(n["id"])
                    continue
            except (ValueError, TypeError):
                pass
        kept_nodes.append(n)

    kept_edges = [
        e for e in edges
        if e["source"] not in removed_ids and e["target"] not in removed_ids
    ]

    graph["nodes"] = kept_nodes
    graph["edges"] = kept_edges
    graph["stats"]["total_nodes"] = len(kept_nodes)
    graph["stats"]["total_edges"] = len(kept_edges)
    save_graph(graph)

    return {
        "status": "ok",
        "removed": len(removed_ids),
        "remaining": len(kept_nodes),
        "older_than": spec,
    }


def apply_decay(graph: dict, half_life_days: float = 30.0) -> dict:
    """
    Add a 'recency' weight (0-1) to session/concept nodes so retrieval can
    favor fresh memory. Does not delete — just down-weights old nodes.
    """
    now = time.time()
    half_life = half_life_days * 86400
    for n in graph.get("nodes", []):
        if n.get("kind") in ("session", "concept") and n.get("timestamp"):
            try:
                age = now - float(n["timestamp"])
                n["recency"] = round(0.5 ** (age / half_life), 3)
            except (ValueError, TypeError):
                n["recency"] = 1.0
    return graph
