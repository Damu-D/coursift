"""
Context Pack builder — the anti-context-rot, anti-cost engine.

Solves (2026 problems):
  - Context rot: agents degrade as the window fills with noise.
  - "Lost in the middle": important info buried in long context is ignored.
  - Cost: brute-force token expansion is financially unviable.

Instead of dumping whole files into the model, Coursift returns a tight,
token-budgeted, relevance-ranked subgraph — GraphRAG-style grounded context.
This runs locally with NO API call.
"""

import re
from difflib import SequenceMatcher

from coursift.graph import load_graph


def _tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


def _relevance(node: dict, terms: list[str]) -> float:
    """Score a node against query terms (label + docstring + file)."""
    haystack = " ".join([
        node.get("label", ""),
        node.get("docstring", ""),
        node.get("file", ""),
        " ".join(node.get("concepts", []) or []),
    ]).lower()

    score = 0.0
    for term in terms:
        if term in haystack:
            score += 2.0
        else:
            # fuzzy partial credit
            best = max(
                (SequenceMatcher(None, term, word).ratio()
                 for word in re.findall(r"\w+", haystack)),
                default=0.0,
            )
            if best > 0.8:
                score += best
    # boost god nodes & cross-project nodes — they carry more signal
    if node.get("god_node"):
        score += 1.0
    if node.get("cross_project"):
        score += 0.5
    return score


def build_context_pack(question: str, max_tokens: int = 2000) -> str:
    """
    Produce a token-budgeted, grounded context pack for a question.
    Pulls the most relevant nodes + their 1-hop neighbors (GraphRAG anchor).
    """
    graph = load_graph()
    if not graph:
        return "No graph found. Run `coursift build` first."

    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])
    terms = [t.lower() for t in re.findall(r"\w+", question) if len(t) > 2]

    # Rank nodes by relevance
    scored = sorted(
        ((nid, _relevance(n, terms)) for nid, n in nodes.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    anchors = [nid for nid, s in scored if s > 0][:12]

    # Pull 1-hop neighbors of anchors (the GraphRAG "entity anchor" step)
    neighbor_ids: set[str] = set(anchors)
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for e in edges:
        adjacency.setdefault(e["source"], []).append((e["target"], e["relation"]))
        adjacency.setdefault(e["target"], []).append((e["source"], e["relation"]))
    for a in anchors:
        for nbr, _rel in adjacency.get(a, [])[:5]:
            neighbor_ids.add(nbr)

    # Pack into a token budget
    lines = [f"# Context pack for: {question}", ""]
    used = _tokens("\n".join(lines))

    # Group by project for readability
    by_project: dict[str, list[dict]] = {}
    for nid in neighbor_ids:
        n = nodes.get(nid)
        if n:
            by_project.setdefault(n.get("project", "unknown"), []).append(n)

    for project, pnodes in by_project.items():
        header = f"\n## {project}"
        if used + _tokens(header) > max_tokens:
            break
        lines.append(header)
        used += _tokens(header)
        # anchors first, then neighbors
        pnodes.sort(key=lambda n: (n["id"] not in anchors, n.get("kind", "")))
        for n in pnodes:
            loc = f"{n.get('file','')}:{n.get('line',0)}" if n.get("file") else ""
            doc = f" — {n['docstring'][:120]}" if n.get("docstring") else ""
            tag = " ⭐" if n.get("god_node") else (" ⬡" if n.get("cross_project") else "")
            entry = f"- [{n.get('kind','')}] **{n.get('label','')}**{tag} `{loc}`{doc}"
            t = _tokens(entry)
            if used + t > max_tokens:
                lines.append(f"  …(truncated at {max_tokens} token budget)")
                return "\n".join(lines)
            lines.append(entry)
            used += t

    # Add any decisions from sessions matching the query
    decisions = []
    for n in nodes.values():
        if n.get("kind") == "session":
            for dec in n.get("decisions", []):
                if any(t in dec.lower() for t in terms):
                    decisions.append((n.get("project", ""), dec))
    if decisions and used < max_tokens:
        lines.append("\n## Relevant decisions (from Claude sessions)")
        for proj, dec in decisions[:5]:
            entry = f"- [{proj}] {dec}"
            if used + _tokens(entry) > max_tokens:
                break
            lines.append(entry)
            used += _tokens(entry)

    lines.append(f"\n_~{used} tokens · budget {max_tokens} · grounded from graph (no hallucination)_")
    return "\n".join(lines)
