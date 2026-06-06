"""
Cross-project semantic clone detection.

Solves (2026 problem):
  "Embeddings for semantic duplicate detection beyond keyword matching, enabling
  cross-repository search." Duplicated logic across your repos is invisible until
  you maintain the same bug in three places.

`coursift duplicates` compares function/class bodies across ALL projects using
token-set Jaccard similarity, and flags near-duplicates — candidates to extract
into a shared package.

100% local, no API.
"""

from collections import defaultdict
from pathlib import Path

from coursift.graph import load_graph
from coursift.embed import jaccard


def find_duplicates(threshold: float = 0.6, cross_project_only: bool = False) -> list[dict]:
    graph = load_graph()
    if not graph:
        return []

    units = [
        n for n in graph.get("nodes", [])
        if n.get("kind") in ("function", "class") and len(n.get("tokens", [])) >= 4
    ]

    # Block by shared tokens to avoid O(n^2) over everything:
    # only compare units that share at least one token.
    token_index: dict[str, list[int]] = defaultdict(list)
    for i, u in enumerate(units):
        for t in u.get("tokens", []):
            token_index[t].append(i)

    seen_pairs: set[tuple[int, int]] = set()
    results: list[dict] = []

    for i, u in enumerate(units):
        candidates: set[int] = set()
        for t in u.get("tokens", []):
            candidates.update(token_index[t])
        candidates.discard(i)

        for j in candidates:
            pair = (i, j) if i < j else (j, i)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            v = units[j]
            # skip same file
            if u.get("file") == v.get("file") and u.get("label") == v.get("label"):
                continue
            if cross_project_only and u.get("project") == v.get("project"):
                continue

            sim = jaccard(u.get("tokens", []), v.get("tokens", []))
            if sim >= threshold:
                results.append({
                    "similarity": round(sim, 2),
                    "a": {"label": u.get("label"), "project": u.get("project"),
                          "file": u.get("file"), "line": u.get("line", 0)},
                    "b": {"label": v.get("label"), "project": v.get("project"),
                          "file": v.get("file"), "line": v.get("line", 0)},
                    "cross_project": u.get("project") != v.get("project"),
                    "same_name": u.get("label") == v.get("label"),
                })

    results.sort(key=lambda r: (r["cross_project"], r["similarity"]), reverse=True)
    return results


def summarize(results: list[dict]) -> dict:
    cross = [r for r in results if r["cross_project"]]
    return {
        "total": len(results),
        "cross_project": len(cross),
        "extraction_candidates": [
            f"{r['a']['label']} ({r['a']['project']}) ≈ {r['b']['label']} ({r['b']['project']})"
            for r in cross[:10]
        ],
    }
