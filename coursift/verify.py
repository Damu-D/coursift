"""Check whether a symbol exists in the graph; suggest close matches if not."""

from difflib import SequenceMatcher

from coursift.graph import load_graph


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def verify_symbol(symbol: str) -> dict:
    """
    Check whether a symbol (function/class/file) exists in the graph.
    Returns a structured result dict.
    """
    graph = load_graph()
    if not graph:
        return {"status": "no_graph", "message": "Run `coursift build` first."}

    nodes = graph.get("nodes", [])
    target = symbol.strip()

    exact = [
        n for n in nodes
        if n.get("label", "").lower() == target.lower()
        and n.get("kind") in ("function", "class", "file")
    ]

    if exact:
        return {
            "status": "found",
            "symbol": target,
            "matches": [
                {
                    "kind": n.get("kind"),
                    "project": n.get("project"),
                    "file": n.get("file"),
                    "line": n.get("line", 0),
                    "doc": n.get("docstring", ""),
                }
                for n in exact
            ],
        }

    # Not found — find closest real matches so the agent can self-correct
    candidates = [
        (n, _similar(target, n.get("label", "")))
        for n in nodes
        if n.get("kind") in ("function", "class", "file")
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    suggestions = [
        {
            "label": n.get("label"),
            "kind": n.get("kind"),
            "project": n.get("project"),
            "file": n.get("file"),
            "similarity": round(sim, 2),
        }
        for n, sim in candidates[:5]
        if sim > 0.5
    ]

    return {
        "status": "not_found",
        "symbol": target,
        "warning": "This symbol does NOT exist in any indexed project. "
                   "If an AI suggested it, it may be hallucinated.",
        "suggestions": suggestions,
    }
