"""
Query interface — answers natural language questions about the graph using Claude.
"""

import json
import os
from pathlib import Path

from coursift.graph import load_graph

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False


def _graph_context(graph: dict, max_nodes: int = 80) -> str:
    """Convert graph to a compact text representation for the prompt."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    stats = graph.get("stats", {})

    lines = [
        f"Projects: {', '.join(stats.get('projects', []))}",
        f"Nodes: {stats.get('total_nodes')} | Edges: {stats.get('total_edges')} | Cross-project: {stats.get('cross_project_links')}",
        "",
        "Key nodes (god nodes / most connected):",
    ]

    god_nodes = [n for n in nodes if n.get("god_node")][:15]
    for n in god_nodes:
        doc = f" — {n['docstring'][:80]}" if n.get("docstring") else ""
        lines.append(f"  [{n['kind']}] {n['label']} ({n['project']}){doc}")

    lines.append("\nCross-project shared dependencies:")
    shared = [n for n in nodes if n.get("cross_project")][:10]
    for n in shared:
        lines.append(f"  {n['label']} shared by: {', '.join(n.get('shared_by', []))}")

    lines.append("\nSession decisions:")
    session_nodes = [n for n in nodes if n.get("kind") == "session"][:5]
    for s in session_nodes:
        for dec in s.get("decisions", [])[:3]:
            lines.append(f"  [{s['project']}] {dec}")

    lines.append("\nSample nodes by project:")
    by_project: dict[str, list] = {}
    for n in nodes:
        proj = n.get("project", "unknown")
        by_project.setdefault(proj, []).append(n)

    shown = 0
    for proj, proj_nodes in by_project.items():
        for n in proj_nodes[:8]:
            if shown >= max_nodes:
                break
            if n.get("kind") in ("function", "class"):
                lines.append(f"  [{proj}] {n['kind']} {n['label']} @ {Path(n.get('file','')).name}:{n.get('line',0)}")
                shown += 1

    return "\n".join(lines)


def query_graph(question: str) -> str:
    """Answer a natural language question about the multi-project graph."""
    if not _HAS_ANTHROPIC:
        return "Error: anthropic package not installed. Run: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set. Export it in your shell."

    graph = load_graph()
    if not graph:
        return "No graph found. Run `coursift build` first."

    context = _graph_context(graph)

    client = anthropic.Anthropic(api_key=api_key)
    system = (
        "You are Coursift, a knowledge graph assistant. "
        "You have access to a multi-project knowledge graph that spans the user's code, "
        "Claude Code sessions, decisions, and architectural patterns. "
        "Answer questions accurately and concisely based on the graph data provided. "
        "If the graph doesn't have enough information, say so clearly."
    )

    prompt = f"""Here is the current state of the knowledge graph:

{context}

User question: {question}

Answer based on the graph data above. Be specific — mention file names, function names,
and project names when relevant. If this is about a pattern that appears across projects,
highlight the cross-project connection."""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
