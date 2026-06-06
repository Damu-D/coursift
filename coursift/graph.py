"""
Graph builder — merges nodes/edges from multiple projects + sessions into one graph.
Detects cross-project patterns and shared dependencies.
"""

import json
from collections import Counter
from pathlib import Path
from dataclasses import asdict

from coursift.config import GRAPH_FILE
from coursift.scanner import Node, Edge


def build_graph(
    all_nodes: list[Node],
    all_edges: list[Edge],
    session_nodes: list[dict],
    session_edges: list[dict],
) -> dict:
    """
    Merge everything into a unified graph dict.
    Detects cross-project shared imports/patterns.
    """
    nodes_dict: dict[str, dict] = {}
    edges_list: list[dict] = []

    # Code nodes from scanner
    for node in all_nodes:
        d = asdict(node)
        nodes_dict[node.id] = d

    # Session nodes
    for snode in session_nodes:
        nid = snode["id"]
        if nid not in nodes_dict:
            nodes_dict[nid] = snode

    # Code edges
    for edge in all_edges:
        edges_list.append(asdict(edge))

    # Session edges
    for sedge in session_edges:
        edges_list.append(sedge)

    # ---- Cross-project detection ----
    # Find imports that appear in 2+ projects and link them
    import_labels: dict[str, list[str]] = {}  # label -> [node_ids]
    for nid, node in nodes_dict.items():
        if node.get("kind") == "import":
            label = node.get("label", "")
            import_labels.setdefault(label, []).append(nid)

    cross_project_edges = []
    for label, nids in import_labels.items():
        projects = {nodes_dict[nid]["project"] for nid in nids if nid in nodes_dict}
        if len(projects) > 1:
            # Mark these nodes as cross-project
            for nid in nids:
                if nid in nodes_dict:
                    nodes_dict[nid]["cross_project"] = True
                    nodes_dict[nid]["shared_by"] = list(projects)
            # Add cross-project edges between the first two occurrences
            for i in range(len(nids) - 1):
                cross_project_edges.append({
                    "source": nids[i],
                    "target": nids[i + 1],
                    "relation": "shared_dependency",
                })

    edges_list.extend(cross_project_edges)

    # ---- God nodes (most connected) ----
    degree: Counter = Counter()
    for edge in edges_list:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1

    top_10 = [nid for nid, _ in degree.most_common(10)]
    for nid in top_10:
        if nid in nodes_dict:
            nodes_dict[nid]["god_node"] = True

    graph = {
        "version": "0.1.0",
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "stats": {
            "total_nodes": len(nodes_dict),
            "total_edges": len(edges_list),
            "cross_project_links": len(cross_project_edges),
            "projects": list({n.get("project", "") for n in nodes_dict.values() if n.get("project")}),
        },
    }
    return graph


def save_graph(graph: dict) -> Path:
    GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with GRAPH_FILE.open("w") as f:
        json.dump(graph, f, indent=2)
    return GRAPH_FILE


def load_graph() -> dict | None:
    if not GRAPH_FILE.exists():
        return None
    with GRAPH_FILE.open() as f:
        return json.load(f)


def graph_summary(graph: dict) -> str:
    stats = graph.get("stats", {})
    projects = stats.get("projects", [])
    return (
        f"{stats.get('total_nodes', 0)} nodes · "
        f"{stats.get('total_edges', 0)} edges · "
        f"{stats.get('cross_project_links', 0)} cross-project links · "
        f"{len(projects)} project(s): {', '.join(projects)}"
    )
