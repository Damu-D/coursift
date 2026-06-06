"""
Memory consolidation — the "sleep cycle" for your knowledge graph.

Implements ideas from 2026 frontier research:
  - ReMe (Remember Me, Refine Me): multi-faceted distillation + utility-based
    refinement — keep valid memories, prune outdated ones.
  - Graph-based memory evolution: "analogous to human memory consolidation during
    sleep — organize recent experiences, abstract general rules, forget trivia."

`coursift consolidate` clusters raw failure lessons into higher-order INSIGHTS,
deduplicates near-identical concepts, and prunes trivial nodes — so the graph
gets *wiser* over time instead of just *bigger*.

100% local, no API.
"""

from collections import Counter, defaultdict

from coursift.graph import load_graph, save_graph
from coursift.embed import tokenize


# Recurring failure themes → an abstracted, preventative insight.
THEME_RULES = [
    (("error", "exit", "code", "command", "failed", "bash"),
     "Commands have failed here before — verify paths/flags and check the working directory first."),
    (("import", "module", "not", "found", "modulenotfound"),
     "Import/module errors recurred — confirm the package is installed in the active environment before importing."),
    (("revert", "undo", "rollback", "broke", "broken"),
     "Changes were reverted here — make smaller, verifiable edits and confirm before moving on."),
    (("type", "typescript", "ts", "tsx", "any"),
     "Type errors recurred — check types against the real definitions, not assumptions."),
    (("test", "failing", "fails", "assertion"),
     "Tests broke here before — run the test suite after changes in this area."),
    (("port", "address", "use", "eaddrinuse", "server"),
     "Port/server conflicts happened before — check for an already-running process."),
    (("env", "key", "secret", "variable", "missing"),
     "Missing env vars caused failures — confirm required env variables are set."),
]


def _theme_for(text: str) -> str | None:
    toks = set(tokenize(text))
    best, best_hits = None, 0
    for keywords, insight in THEME_RULES:
        hits = len(toks & set(keywords))
        if hits > best_hits:
            best, best_hits = insight, hits
    return best if best_hits >= 2 else None


def consolidate(prune_trivial: bool = True) -> dict:
    """Distill lessons into insights, dedupe concepts, prune trivia."""
    graph = load_graph()
    if not graph:
        return {"status": "no_graph"}

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # 1) Distill: cluster lessons by abstracted theme, per project
    lessons = [n for n in nodes if n.get("kind") == "lesson"]
    theme_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for l in lessons:
        text = f"{l.get('label','')} {l.get('context','')}"
        theme = _theme_for(text)
        if theme:
            theme_groups[(l.get("project", "?"), theme)].append(l)

    insight_nodes = []
    insight_edges = []
    for (project, insight), group in theme_groups.items():
        if len(group) < 2:
            continue  # need recurrence to be an "insight"
        iid = f"insight::{project}::{abs(hash(insight)) % 10**8}"
        insight_nodes.append({
            "id": iid,
            "label": insight,
            "kind": "insight",
            "project": project,
            "file": "",
            "evidence_count": len(group),
            "distilled_from": len(group),
        })
        for l in group:
            insight_edges.append({"source": iid, "target": l["id"], "relation": "abstracts"})

    # 2) Dedupe concepts: merge concept nodes with the same normalized label
    concept_map: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        if n.get("kind") == "concept":
            concept_map[n.get("label", "").strip().lower()].append(n)
    merged_concepts = 0
    keep_ids = set()
    remap: dict[str, str] = {}
    for label, group in concept_map.items():
        canonical = group[0]["id"]
        keep_ids.add(canonical)
        for dup in group[1:]:
            remap[dup["id"]] = canonical
            merged_concepts += 1

    # 3) Prune trivial: concept nodes that appear only once and are very short
    pruned = 0
    if prune_trivial:
        degree: Counter = Counter()
        for e in edges:
            degree[e["source"]] += 1
            degree[e["target"]] += 1

    new_nodes = []
    for n in nodes:
        nid = n["id"]
        if nid in remap:
            continue  # merged away
        if prune_trivial and n.get("kind") == "concept":
            if degree[nid] <= 1 and len(n.get("label", "")) <= 3:
                pruned += 1
                continue
        new_nodes.append(n)
    new_nodes.extend(insight_nodes)

    # rewrite edges through the concept remap, drop edges to pruned nodes
    kept_node_ids = {n["id"] for n in new_nodes}
    new_edges = []
    for e in edges:
        s = remap.get(e["source"], e["source"])
        t = remap.get(e["target"], e["target"])
        if s in kept_node_ids and t in kept_node_ids:
            new_edges.append({**e, "source": s, "target": t})
    new_edges.extend(insight_edges)

    graph["nodes"] = new_nodes
    graph["edges"] = new_edges
    graph["stats"]["total_nodes"] = len(new_nodes)
    graph["stats"]["total_edges"] = len(new_edges)
    save_graph(graph)

    return {
        "status": "ok",
        "insights_created": len(insight_nodes),
        "concepts_merged": merged_concepts,
        "trivia_pruned": pruned,
        "insights": [
            {"project": n["project"], "insight": n["label"], "evidence": n["evidence_count"]}
            for n in insight_nodes
        ],
    }
